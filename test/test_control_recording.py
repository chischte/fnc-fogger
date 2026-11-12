import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from logger import logger
from logger.measurement_recording import MeasurementRecorder


class ControlRecordingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db = logger.connect(Path(self.directory.name) / "device.db")
        self.addCleanup(self.db.close)
        self.payload = {
            "measurement": {"boot_id": 1, "sequence": 2, "uptime_ms": 10000},
            "control": {"reason": "manual", "enabled": False,
                        "manual": {"active": True, "fogger_percent": 40},
                        "fan": {"rpm": 3060, "pwm_percent": 60},
                        "fogger": {"on": False},
                        "setpoints": {"co2_ppm": 1000, "humidity_rh": 90}}}

    def test_manual_changes_are_recorded_even_when_sensor_sample_is_unchanged(self):
        recorder = MeasurementRecorder(self.db)
        now = datetime(2026, 11, 12, 12, tzinfo=timezone.utc)
        self.assertEqual(recorder.record_live(self.payload, now), 1)
        self.payload["control"]["manual"]["fogger_percent"] = 50
        self.assertEqual(recorder.record_live(self.payload, now + timedelta(seconds=5)), 0)
        rows = self.db.execute("""SELECT received_at,mode,fan_rpm,fan_pwm_percent,
            fogger_percent,fogger_on,controller_enabled,co2_setpoint_ppm,humidity_setpoint_rh
            FROM control_samples ORDER BY id""").fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][1:], ("manual", 3060, 60, 40, 0, 0, 1000, 90))
        self.assertEqual(rows[1][4], 50)
        self.assertNotEqual(rows[0][0], rows[1][0])

    def test_backfill_does_not_invent_historical_control_and_unknown_rpm_stays_null(self):
        recorder = MeasurementRecorder(self.db)
        self.payload["control"]["fan"]["rpm"] = None
        recorder.record_live(self.payload)
        recorder.record_buffer([self.payload["measurement"]])
        self.assertEqual(self.db.execute("SELECT count(*) FROM control_samples").fetchone()[0], 1)
        rpm, raw = self.db.execute("SELECT fan_rpm,control_json FROM control_samples").fetchone()
        self.assertIsNone(rpm)
        self.assertEqual(json.loads(raw), self.payload["control"])

    def test_legacy_payload_does_not_create_fake_zero_outputs(self):
        logger.insert(self.db, self.payload["measurement"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM control_samples").fetchone()[0], 0)

    def test_explicit_duty_preserves_command_instead_of_rounded_pulse_ratio(self):
        self.payload["control"]["manual"]["active"] = False
        self.payload["control"]["fogger"] = {
            "on": True, "duty_percent": 3, "on_time_s": 0.1, "off_time_s": 3.233}
        logger.insert(self.db, self.payload)
        self.assertEqual(self.db.execute("SELECT fogger_percent FROM control_samples").fetchone()[0], 3)

    def test_single_device_logger_also_records_control_without_changing_insert_result(self):
        self.assertTrue(logger.insert(self.db, self.payload))
        self.assertFalse(logger.insert(self.db, self.payload))
        self.assertEqual(self.db.execute("SELECT count(*) FROM control_samples").fetchone()[0], 2)

    def test_nonmanual_fogger_duty_uses_timing_and_missing_duty_stays_unknown(self):
        self.payload["control"]["manual"]["active"] = False
        self.payload["control"]["fogger"] = {"on": True, "on_time_s": 0.1, "off_time_s": 0.1}
        logger.insert(self.db, self.payload)
        self.payload["control"]["fogger"] = {"on": True}
        logger.insert(self.db, self.payload)
        self.assertEqual(self.db.execute(
            "SELECT fogger_percent FROM control_samples ORDER BY id").fetchall(), [(50,), (None,)])


if __name__ == "__main__":
    unittest.main()
