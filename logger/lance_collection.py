"""Viewer-only live telemetry and commands; persistent recording is independent."""
import json
import queue
import threading
import time
import urllib.parse
import urllib.request

from . import logger
from .control_data import ControlMonitor, Setpoints, ManualOutputs


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
                self._send_pending_setpoints()
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

    def submit_manual(self, values):
        state = self.control.snapshot()
        if not state["online"] or not state["manual_supported"]:
            raise ValueError("Manual Mode unavailable: device offline or firmware update required.")
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
            if (manual.get("supported") is not True or control.get("enabled") is not False
                    or ManualOutputs.from_payload(manual) != values):
                raise ValueError("Device did not confirm manual outputs with PI disabled.")
            self.control.ingest({"control": control})
            self._manual_lease = values if values.active else None
            self._manual_renewed_at = time.monotonic()
            if explicit:
                self.manual_results.put((True, "Manual outputs confirmed."))
        except Exception as error:
            self._manual_lease = None
            self.manual_results.put((False, f"Manual command unconfirmed: {error}. Outputs expire within 30 s."))
