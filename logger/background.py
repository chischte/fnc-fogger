"""Record every registered device independently of any viewer window."""
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import threading
import time
import urllib.request
from contextlib import closing
from datetime import datetime, timezone

from . import logger
from .lance_registry import LanceRegistry
from .measurement_recording import MeasurementRecorder
from .process_lock import ProcessLock

LOG = logging.getLogger(__name__)
BACKFILL_RETRY_SECONDS = 60
SUPERVISOR_INTERVAL_SECONDS = 10


class DeviceRecorder:
    def __init__(self, lance, database):
        self.lance = lance
        self.database = database
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, name=lance.device_id, daemon=True)
        self._lock = threading.Lock()
        self._status = {"online": False, "last_success": None, "error": "Starting"}
        self.needs_backfill = True
        self.last_backfill_attempt = float("-inf")
        self.previous = None

    def status(self):
        with self._lock:
            return dict(self._status, worker_alive=self.thread.is_alive())

    def _update_status(self, **values):
        with self._lock:
            self._status.update(values)

    def sample(self, recorder):
        payload = logger.fetch_json(self.lance.url + "/api/current")
        if payload.get("device_id") != self.lance.device_id:
            raise ValueError("Device identity mismatch; refusing to record into this database")
        received_at = datetime.now(timezone.utc)
        record = payload["measurement"]
        current = (record["boot_id"], record["sequence"])
        if self.previous and (current[0] != self.previous[0] or current[1] > self.previous[1] + 1):
            self.needs_backfill = True
        recorder.record_live(payload, received_at)
        self.previous = current
        self._update_status(online=True, last_success=received_at.isoformat(timespec="seconds"),
                            error=None, boot_id=current[0], sequence=current[1])
        self._backfill(recorder)

    def _backfill(self, recorder):
        now = time.monotonic()
        if not self.needs_backfill or now - self.last_backfill_attempt < BACKFILL_RETRY_SECONDS:
            return
        self.last_backfill_attempt = now
        try:
            rows = list(logger.fetch_backlog(self.lance.url + "/api/backlog"))
            count = recorder.record_buffer(rows)
            self.needs_backfill = False
            self._update_status(last_backfill=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                backfill_error=None, recovered_last=count)
            LOG.info("%s: recovered %s buffered samples", self.lance.device_id, count)
        except Exception as error:
            self._update_status(backfill_error=str(error))
            LOG.warning("%s: backfill failed: %s", self.lance.device_id, error)

    def run(self):
        try:
            with closing(logger.connect(self.database)) as database:
                if self.database.name == "measurements.db":
                    logger.import_csv(database, self.database.with_suffix(".csv"))
                recorder = MeasurementRecorder(database)
                self.previous = database.execute(
                    "SELECT boot_id,sequence FROM measurements ORDER BY id DESC LIMIT 1").fetchone()
                while not self.stop_event.is_set():
                    started = time.monotonic()
                    was_online = self.status()["online"]
                    try:
                        self.sample(recorder)
                        if not was_online:
                            LOG.info("%s: online", self.lance.device_id)
                    except Exception as error:
                        self.needs_backfill = True
                        self._update_status(online=False, error=str(error))
                        if was_online or self.status().get("last_error") != str(error):
                            LOG.warning("%s: collection failed: %s", self.lance.device_id, error)
                        self._update_status(last_error=str(error))
                    self.stop_event.wait(max(0, logger.POLL_INTERVAL - (time.monotonic() - started)))
        except Exception:
            LOG.exception("%s: recorder worker stopped unexpectedly", self.lance.device_id)


class BackgroundLogger:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.registry = LanceRegistry(self.directory)
        self.workers = {}
        self.stop_event = threading.Event()

    def sync_devices(self):
        devices = {device.device_id: device for device in self.registry.list()}
        for device_id, worker in list(self.workers.items()):
            device = devices.get(device_id)
            changed = device is None or device.url != worker.lance.url
            if changed:
                worker.stop_event.set()
            if not worker.thread.is_alive():
                self.workers.pop(device_id)
        for device_id, device in devices.items():
            if device_id not in self.workers:
                worker = DeviceRecorder(device, self.registry.measurement_path(device))
                self.workers[device_id] = worker
                worker.thread.start()

    def write_status(self):
        payload = {"pid": os.getpid(), "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "devices": {key: worker.status() for key, worker in self.workers.items()}}
        path = self.directory / "background-status.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(path)

    def run(self):
        LOG.info("Background logger started, PID %s", os.getpid())
        try:
            while not self.stop_event.is_set():
                self.sync_devices()
                self.write_status()
                self.stop_event.wait(SUPERVISOR_INTERVAL_SECONDS)
        finally:
            for worker in self.workers.values():
                worker.stop_event.set()
            for worker in self.workers.values():
                worker.thread.join(timeout=35)
            LOG.info("Background logger stopped")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).parent / "data")
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    lock = ProcessLock(args.directory / "background.lock")
    if not lock.acquire():
        return
    handler = RotatingFileHandler(args.directory / "background.log", maxBytes=1024*1024,
                                  backupCount=4, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler],
                        format="%(asctime)s %(levelname)s %(message)s")
    # Device endpoints are local; a system HTTP proxy must not intercept them.
    urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))
    service = BackgroundLogger(args.directory)
    for name in ("SIGINT", "SIGTERM"):
        signal.signal(getattr(signal, name), lambda *_: service.stop_event.set())
    try:
        service.run()
    finally:
        lock.close()


if __name__ == "__main__":
    main()
