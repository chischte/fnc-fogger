"""Persist observed actuators and setpoints independently of sensor deduplication."""
import json

SCHEMA = """
CREATE TABLE IF NOT EXISTS control_samples(
 id INTEGER PRIMARY KEY, received_at TEXT NOT NULL,
 boot_id INTEGER, measurement_sequence INTEGER,
 mode TEXT, controller_enabled INTEGER, manual_active INTEGER,
 fan_rpm REAL, fan_pwm_percent REAL, fogger_percent REAL, fogger_on INTEGER,
 co2_setpoint_ppm REAL, humidity_setpoint_rh REAL, control_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_control_samples_received ON control_samples(received_at);
CREATE TABLE IF NOT EXISTS humidity_calibrations(
 revision INTEGER PRIMARY KEY, received_at TEXT NOT NULL,
 reference_rh REAL NOT NULL, sht_raw_rh REAL NOT NULL, scd_raw_rh REAL NOT NULL,
 sht_offset_rh REAL NOT NULL, scd_offset_rh REAL NOT NULL, duration_ms INTEGER NOT NULL,
 reference_kind TEXT NOT NULL DEFAULT 'assumed_saturation');
"""


def _boolean(value):
    return int(value) if isinstance(value, bool) else None


def _fogger_percent(control):
    duty = control.get("fogger", {}).get("duty_percent")
    if isinstance(duty, (int, float)) and not isinstance(duty, bool) and 0 <= duty <= 100:
        return duty
    manual = control.get("manual", {})
    if manual.get("active") is True:
        return manual.get("fogger_percent")
    fogger = control.get("fogger", {})
    on = fogger.get("on_time_s")
    off = fogger.get("off_time_s")
    if isinstance(on, (int, float)) and isinstance(off, (int, float)):
        if on >= 0 and off >= 0 and on + off > 0:
            return 100 * on / (on + off)
    if on == 0 and fogger.get("on") is False:
        return 0
    return None


def record_control(db, payload, received_at):
    control = payload.get("control")
    if not isinstance(control, dict) or not control:
        return
    measurement = payload.get("measurement", {})
    calibration = control.get("humidity_calibration", {})
    if calibration.get("revision", 0) > 0:
        db.execute("""INSERT OR IGNORE INTO humidity_calibrations
            (revision,received_at,reference_rh,sht_raw_rh,scd_raw_rh,sht_offset_rh,scd_offset_rh,duration_ms,reference_kind)
            VALUES(?,?,?,?,?,?,?,?,?)""", (
                calibration["revision"], received_at, calibration["assumed_reference_rh"],
                calibration["sht_raw_rh"], calibration["scd_raw_rh"],
                calibration["sht_offset_rh"], calibration["scd_offset_rh"], calibration["duration_ms"],
                calibration.get("reference_kind", "assumed_saturation")))
    manual = control.get("manual", {})
    fan = control.get("fan", {})
    setpoints = control.get("setpoints", {})
    # Control is observed now; the referenced sensor sample can be older.
    db.execute("""INSERT INTO control_samples(
        received_at,boot_id,measurement_sequence,mode,controller_enabled,manual_active,
        fan_rpm,fan_pwm_percent,fogger_percent,fogger_on,
        co2_setpoint_ppm,humidity_setpoint_rh,control_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            received_at, measurement.get("boot_id"), measurement.get("sequence"),
            control.get("reason"), _boolean(control.get("enabled")),
            _boolean(manual.get("active")), fan.get("rpm"), fan.get("pwm_percent"),
            _fogger_percent(control), _boolean(control.get("fogger", {}).get("on")),
            setpoints.get("co2_ppm"), setpoints.get("humidity_rh"),
            json.dumps(control, separators=(",", ":"), allow_nan=False)))
