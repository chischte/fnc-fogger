"""Collect a selected lance without blocking the viewer's event loop."""
import queue
import threading
from contextlib import closing

from . import logger


class LanceCollector:
    def __init__(self, lance, database):
        self.lance = lance
        self.database = database
        self.stop_event = threading.Event()
        self.messages = queue.Queue()
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
                        payload = logger.fetch_json(self.lance.url + "/api/current")
                        if self.stop_event.is_set():
                            break
                        logger.insert(db, payload)
                        self.messages.put("Verbunden")
                    except Exception as error:
                        self.messages.put(f"Verbindung unterbrochen: {error}")
                    self.stop_event.wait(logger.POLL_INTERVAL)
        except Exception as error:
            self.messages.put(f"Datenerfassung fehlgeschlagen: {error}")

    def latest_status(self):
        latest = None
        while True:
            try:
                latest = self.messages.get_nowait()
            except queue.Empty:
                return latest
