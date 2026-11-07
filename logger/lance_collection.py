"""Collect a selected lance without blocking the viewer's event loop."""
import json
import queue
import threading
import urllib.parse
import urllib.request
from contextlib import closing

from . import logger
from .control_data import ControlMonitor, Setpoints


class LanceCollector:
    def __init__(self, lance, database):
        self.lance = lance
        self.database = database
        self.stop_event = threading.Event()
        self.messages = queue.Queue()
        self.commands = queue.Queue(maxsize=1)
        self.command_results = queue.Queue()
        self.control = ControlMonitor(database)
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def _run(self):
        try:
            with closing(logger.connect(self.database)) as db:
                while not self.stop_event.is_set():
                    try:
                        self._send_pending_setpoints()
                        payload = logger.fetch_json(self.lance.url + "/api/current")
                        if self.stop_event.is_set():
                            break
                        logger.insert(db, payload)
                        self.control.ingest(payload)
                        self.messages.put("Connected")
                    except Exception as error:
                        self.control.disconnected(f"Offline: {error}")
                        self.messages.put(f"Disconnected: {error}")
                    self.stop_event.wait(logger.POLL_INTERVAL)
        except Exception as error:
            self.messages.put(f"Data collection failed: {error}")

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
