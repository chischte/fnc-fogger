import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from logger import logger
from logger.background import BackgroundLogger, DeviceRecorder
from logger.background_process import healthy
from logger.lance_registry import Lance, LanceRegistry
from logger.measurement_recording import MeasurementRecorder
from logger.process_lock import ProcessLock


def sample(sequence, boot=10, temperature=25):
    return {"boot_id": boot, "sequence": sequence, "uptime_ms": sequence*5000,
            "co2": 1000+sequence, "boxtemp": temperature, "humidity": 80}


class BackgroundLoggerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.lance = Lance("b81f3f27ca14", "test.local", 80)
        self.database = self.directory / "measurements.db"

    def tearDown(self):
        self.temp.cleanup()

    def test_backfill_preserves_measurement_times_and_deduplicates(self):
        now = datetime(2026, 11, 11, 12, tzinfo=timezone.utc)
        with closing(logger.connect(self.database)) as db:
            recorder = MeasurementRecorder(db)
            self.assertEqual(recorder.record_live(sample(100), now), 1)
            self.assertEqual(recorder.record_buffer([sample(98), sample(99), sample(100)], now), 2)
            times = dict(db.execute("SELECT sequence,device_time FROM measurements"))
            self.assertEqual(datetime.fromisoformat(times[98]), now-timedelta(seconds=10))
            self.assertEqual(datetime.fromisoformat(times[100]), now)
            recorder = MeasurementRecorder(db)
            recorder.record_live(sample(101), now+timedelta(seconds=20))
            actual = db.execute("SELECT device_time FROM measurements WHERE sequence=101").fetchone()[0]
            self.assertEqual(datetime.fromisoformat(actual), now+timedelta(seconds=5))

    def test_existing_live_history_anchors_recovery_and_unknown_boot_is_not_fabricated(self):
        with closing(logger.connect(self.database)) as db:
            logger.insert(db, sample(10))
            db.execute("UPDATE measurements SET received_at='2026-11-10T20:00:00+01:00'")
            db.commit()
            recorder = MeasurementRecorder(db)
            self.assertEqual(recorder.record_buffer([sample(8), sample(1, boot=99)]), 1)
            value = db.execute("SELECT device_time FROM measurements WHERE sequence=8").fetchone()[0]
            self.assertEqual(datetime.fromisoformat(value).isoformat(), '2026-11-10T19:59:50+01:00')

    def test_device_identity_mismatch_never_writes_samples(self):
        worker = DeviceRecorder(self.lance, self.database)
        with closing(logger.connect(self.database)) as db:
            recorder = MeasurementRecorder(db)
            with patch("logger.background.logger.fetch_json", return_value={
                    "device_id": "aaaaaaaaaaaa", "measurement": sample(1)}):
                with self.assertRaisesRegex(ValueError, "identity"):
                    worker.sample(recorder)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM measurements').fetchone()[0], 0)

    def test_recorder_collects_and_recovers_without_a_viewer(self):
        worker = DeviceRecorder(self.lance, self.database)
        with closing(logger.connect(self.database)) as db:
            recorder = MeasurementRecorder(db)
            with patch("logger.background.logger.fetch_json", return_value={
                    "device_id": self.lance.device_id, "measurement": sample(3)}), \
                    patch("logger.background.logger.fetch_backlog", return_value=iter([sample(1), sample(2), sample(3)])):
                worker.sample(recorder)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM measurements').fetchone()[0], 3)
            self.assertTrue(worker.status()["online"])
            self.assertEqual(worker.status()["recovered_last"], 2)
            self.assertFalse(worker.needs_backfill)

    def test_backfill_failure_keeps_live_recording_and_retries(self):
        worker = DeviceRecorder(self.lance, self.database)
        with closing(logger.connect(self.database)) as db:
            recorder = MeasurementRecorder(db)
            with patch("logger.background.logger.fetch_json", return_value={
                    "device_id": self.lance.device_id, "measurement": sample(3)}), \
                    patch("logger.background.logger.fetch_backlog", side_effect=OSError("timeout")):
                worker.sample(recorder)
            self.assertTrue(worker.status()["online"])
            self.assertTrue(worker.needs_backfill)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM measurements').fetchone()[0], 1)

    def test_only_one_process_lock_and_lock_released_after_close(self):
        first = ProcessLock(self.directory / 'background.lock')
        second = ProcessLock(self.directory / 'background.lock')
        self.assertTrue(first.acquire())
        self.assertFalse(second.acquire())
        first.close()
        self.assertTrue(second.acquire())
        second.close()

    def test_service_tracks_all_registered_devices_and_removal(self):
        registry = LanceRegistry(self.directory)
        registry.remember(self.lance)
        registry.remember(Lance('aaaaaaaaaaaa', 'second.local', 80))
        service = BackgroundLogger(self.directory)
        with patch('logger.background.DeviceRecorder') as factory:
            def create(lance, database):
                from unittest.mock import MagicMock
                worker = MagicMock()
                worker.lance = lance
                worker.thread.is_alive.return_value = True
                worker.status.return_value = {'online': True}
                return worker
            factory.side_effect = create
            service.sync_devices()
            self.assertEqual(len(service.workers), 2)
            registry.remove(self.lance.device_id)
            service.sync_devices()
            service.workers[self.lance.device_id].stop_event.set.assert_called()
            service.write_status()
            self.assertTrue(healthy(self.directory))
            data = json.loads((self.directory/'background-status.json').read_text())
            self.assertEqual(len(data['devices']), 2)
            service.workers[self.lance.device_id].thread.is_alive.return_value = False
            service.sync_devices()
            self.assertEqual(len(service.workers), 1)

    def test_stale_heartbeat_is_not_healthy(self):
        (self.directory/'background-status.json').write_text(json.dumps({
            'updated_at':(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()}))
        self.assertFalse(healthy(self.directory))
