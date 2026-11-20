"""Viewer-only live telemetry and commands; persistent recording is independent."""
import json
import queue
import threading
import time
import urllib.parse
import urllib.request

from . import logger
from .control_data import ControlMonitor, Setpoints, ManualOutputs
from .cyclic_mist import CyclicMistSettings


class LanceCollector:
    def __init__(self, lance, database):
        self.lance = lance
        self.database = database
        self.stop_event = threading.Event()
        self.command_event = threading.Event()
        self.messages = queue.Queue()
        self.commands = queue.Queue(maxsize=1)
        self.command_results = queue.Queue()
        self.manual_commands = queue.Queue(maxsize=1)
        self.manual_results = queue.Queue()
        self.automatic_commands = queue.Queue(maxsize=1)
        self.automatic_results = queue.Queue()
        self.cyclic_mist_commands = queue.Queue(maxsize=1)
        self.cyclic_mist_results = queue.Queue()
        self._manual_lease = None
        self._manual_renewed_at = 0
        self.control = ControlMonitor(database)
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.command_event.set()

    def _run(self):
        while not self.stop_event.is_set():
            self.command_event.clear()
            try:
                self._send_pending_manual()
                self._send_pending_automatic()
                self._send_pending_setpoints()
                self._send_pending_cyclic_mist()
                payload = logger.fetch_json(self.lance.url + "/api/current")
                if self.stop_event.is_set():
                    break
                if payload.get("device_id") != self.lance.device_id:
                    raise ValueError("Device identity mismatch")
                self.control.ingest(payload)
                self.messages.put("Connected")
            except Exception as error:
                self._manual_lease = None
                self.control.disconnected(f"Offline: {error}")
                self.messages.put(f"Disconnected: {error}")
            if not self.stop_event.is_set():
                self.command_event.wait(logger.POLL_INTERVAL)

    def latest_status(self):
        latest = None
        while True:
            try:
                latest = self.messages.get_nowait()
            except queue.Empty:
                return latest

    def submit_setpoints(self, setpoints):
        state = self.control.snapshot()
        if not state["online"] or not state["supported"]:
            raise ValueError("Lance offline or setpoint interface unavailable.")
        try:
            self.commands.put_nowait(setpoints)
            self.command_event.set()
        except queue.Full as error:
            raise ValueError("A setpoint transfer is already pending.") from error

    def _send_pending_setpoints(self):
        try:
            setpoints = self.commands.get_nowait()
        except queue.Empty:
            return
        try:
            encoded = urllib.parse.urlencode({"co2_ppm": setpoints.co2_ppm,
                                              "humidity_rh": setpoints.humidity_rh}).encode("ascii")
            request = urllib.request.Request(self.lance.url + "/api/control/setpoints", data=encoded,
                                             headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(request, timeout=8) as response:
                control = json.load(response)
            if (control.get("persisted") is not True or
                    control.get("settings_supported") is not True or
                    Setpoints.from_payload(control["setpoints"]) != setpoints):
                raise ValueError("Device did not confirm persistent setpoint storage.")
            self.control.ingest({"control": control})
            self.command_results.put((True, "Saved on the device and in SQLite."))
        except Exception as error:
            self.command_results.put((False, f"Unconfirmed: {error}. Check device values again."))

    def submit_cyclic_mist(self, values):
        state = self.control.snapshot()
        if (not isinstance(values, CyclicMistSettings) or not state["online"]
                or not state["cyclic_mist"].get("supported")
                or (values.enabled and (not state["enabled"] or state.get("fault"))
                    and not state["cyclic_mist"].get("enabled"))):
            raise ValueError("Cyclic mist requires an online device with supported automatic mode.")
        self._clear_commands(self.cyclic_mist_commands)
        self.cyclic_mist_commands.put_nowait(values)
        self.command_event.set()

    def _send_pending_cyclic_mist(self):
        try:
            values = self.cyclic_mist_commands.get_nowait()
        except queue.Empty:
            return
        try:
            request = urllib.request.Request(
                self.lance.url + "/api/control/cyclic-mist",
                data=urllib.parse.urlencode(values.fields()).encode("ascii"),
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(request, timeout=8) as response:
                control = json.load(response)
            confirmed = control.get("cyclic_mist", {})
            if not confirmed.get("supported") or CyclicMistSettings.from_payload(confirmed) != values:
                raise ValueError("Device did not confirm cyclic mist settings.")
            self.control.ingest({"control": control})
            self.cyclic_mist_results.put((True, "Cyclic mist saved on device.", values))
        except Exception as error:
            self.cyclic_mist_results.put((False, f"Cyclic mist unconfirmed: {error}", values))

    def submit_manual(self, values):
        state = self.control.snapshot()
        if not state["online"] or not state["manual_supported"]:
            raise ValueError("Manual Mode unavailable: device offline or firmware update required.")
        if values.fogger_percent and not state["fogger_enabled"]:
            raise ValueError("Fogger disabled during ventilation commissioning.")
        self._clear_commands(self.automatic_commands)
        try:
            self.manual_commands.put_nowait(values)
        except queue.Full:
            # Keep only the latest slider position while a request is in flight.
            try:
                self.manual_commands.get_nowait()
            except queue.Empty:
                pass
            self.manual_commands.put_nowait(values)
        self.command_event.set()

    @staticmethod
    def _clear_commands(commands):
        while True:
            try:
                commands.get_nowait()
            except queue.Empty:
                return

    def submit_automatic(self, enabled):
        state = self.control.snapshot()
        if not isinstance(enabled, bool) or not state["online"] or not state["automatic_supported"]:
            raise ValueError("PI control unavailable: device offline or firmware update required.")
        self._clear_commands(self.manual_commands)
        self._clear_commands(self.automatic_commands)
        self._manual_lease = None
        self.automatic_commands.put_nowait(enabled)
        self.command_event.set()

    def submit_pi_reset(self):
        state = self.control.snapshot()
        if not state["online"] or not state["enabled"] or not state["pi_reset_supported"]:
            raise ValueError("PI reset unavailable: automatic mode and firmware 3.5.5 required.")
        self._clear_commands(self.automatic_commands)
        self.automatic_commands.put_nowait("reset")
        self.command_event.set()

    def submit_exit_emergency(self):
        state = self.control.snapshot()
        if not state["online"] or not state["enabled"] or not state["exit_emergency_supported"]:
            raise ValueError("Emergency exit unavailable: automatic mode and firmware update required.")
        self._clear_commands(self.automatic_commands)
        self.automatic_commands.put_nowait("exit_emergency")
        self.command_event.set()

    def _send_pending_automatic(self):
        try:
            enabled = self.automatic_commands.get_nowait()
        except queue.Empty:
            return
        if enabled in ("calibration-start", "calibration-cancel"):
            self._send_calibration(enabled.removeprefix("calibration-"))
            return
        try:
            reset = enabled == "reset"
            exit_emergency = enabled == "exit_emergency"
            previous_reset = self.control.snapshot()["pi_reset_count"]
            if reset or exit_emergency:
                fields = {enabled: 1}
            else:
                fields = {"enabled": int(enabled)}
            encoded = urllib.parse.urlencode(fields).encode("ascii")
            request = urllib.request.Request(self.lance.url + "/api/control/automatic", data=encoded,
                                             headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(request, timeout=8) as response:
                control = json.load(response)
            expected_enabled = True if reset or exit_emergency else enabled
            if control.get("automatic_supported") is not True or control.get("enabled") is not expected_enabled:
                raise ValueError("Device did not confirm PI mode.")
            if reset and control.get("pi_reset_count") != previous_reset + 1:
                raise ValueError("Device did not confirm PI integral reset.")
            if exit_emergency and (control.get("exit_emergency_supported") is not True
                                   or control.get("fault") is True
                                   or control.get("humidity_emergency", {}).get("active") is True
                                   or control.get("emergency_ventilation", {}).get("active") is True):
                raise ValueError("Device did not confirm emergency exit.")
            self.control.ingest({"control": control})
            message = "PI integrals reset." if reset else "PI control started." if enabled else "PI stopped."
            if exit_emergency:
                message = "Emergency exited; PI integrals retained."
            self.automatic_results.put((True, message))
        except Exception as error:
            self.automatic_results.put((False, f"PI command unconfirmed: {error}. Check device state."))

    def submit_calibration(self, cancel=False):
        state = self.control.snapshot()
        if not state["online"] or not state["calibration"].get("supported"):
            raise ValueError("Humidity reference requires firmware 3.5.6 and an online device.")
        self._clear_commands(self.automatic_commands)
        self._clear_commands(self.manual_commands)
        self._manual_lease = None
        self.automatic_commands.put_nowait("calibration-cancel" if cancel else "calibration-start")
        self.command_event.set()

    def _send_calibration(self, action):
        try:
            request = urllib.request.Request(self.lance.url + "/api/control/humidity-calibration",
                                             data=urllib.parse.urlencode({"action": action}).encode())
            with urllib.request.urlopen(request, timeout=8) as response:
                control = json.load(response)
            expected = action == "start"
            if control.get("humidity_calibration", {}).get("running") is not expected:
                raise ValueError("Device did not confirm humidity reference state.")
            self.control.ingest({"control": control})
            self.manual_results.put((True, "15-minute assumed-100% reference running." if expected else "Reference cancelled; PI resumed."))
        except Exception as error:
            self.manual_results.put((False, f"Humidity reference unconfirmed: {error}"))

    def _send_pending_manual(self):
        try:
            values = self.manual_commands.get_nowait()
            explicit = True
        except queue.Empty:
            values = self._manual_lease
            explicit = False
        if values is None:
            return
        if not explicit and time.monotonic() - self._manual_renewed_at >= 20:
            self._manual_lease = None
            self.manual_results.put((False, "Manual connection interrupted. Switch On again to resume."))
            return
        try:
            fields = values.fields()
            if not explicit:
                fields["mode"] = "renew"
            encoded = urllib.parse.urlencode(fields).encode("ascii")
            request = urllib.request.Request(self.lance.url + "/api/control/manual", data=encoded,
                                             headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(request, timeout=8) as response:
                control = json.load(response)
            manual = control.get("manual", {})
            expected_enabled = not values.active and control.get("automatic_default") is True
            if (manual.get("supported") is not True or control.get("enabled") is not expected_enabled
                    or ManualOutputs.from_payload(manual) != values):
                raise ValueError("Device did not confirm requested manual/PI mode.")
            self.control.ingest({"control": control})
            needs_renewal = manual.get("lease_ms", 30000) != 0
            self._manual_lease = values if values.active and needs_renewal else None
            self._manual_renewed_at = time.monotonic()
            if explicit:
                self.manual_results.put((True, "Manual outputs confirmed."))
        except Exception as error:
            self._manual_lease = None
            timeout = self.control.snapshot()["manual_timeout_ms"]
            consequence = ("Outputs remain active while device Wi-Fi is connected; check device state."
                           if timeout == 0 else "Outputs expire within 30 s without renewal.")
            self.manual_results.put((False, f"Manual command unconfirmed: {error}. {consequence}"))
