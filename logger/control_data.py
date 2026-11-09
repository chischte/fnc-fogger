"""Confirmed setpoints in SQLite; regulator telemetry stays in bounded RAM."""
import math
import sqlite3
import threading
from collections import deque
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

MAX_CO2_PPM = 20000
MIN_HUMIDITY_RH = 70
MAX_HUMIDITY_RH = 100
MAX_CONTROL_SAMPLES = 2160


def actuator_telemetry(control):
    values = {}
    for section, field in (("fan", "rpm"), ("fogger", "on_time_s"), ("fogger", "off_time_s")):
        source = control.get(section)
        value = source.get(field) if isinstance(source, dict) else None
        values[field] = (float(value) if isinstance(value, (int, float))
                         and not isinstance(value, bool) and math.isfinite(value)
                         and value >= 0 else None)
    return values


def telemetry_sample(control):
    sample = {"timestamp": datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Zurich")).replace(tzinfo=None)}
    for channel in ("humidity", "co2"):
        values = control.get(channel, {})
        for term in ("p", "i", "sum"):
            value = values.get(term)
            sample[f"{channel}_{term}"] = (
                float(value) if isinstance(value, (int, float)) and
                math.isfinite(value) and -100 <= value <= 100 else float("nan"))
    return sample


@dataclass(frozen=True)
class Setpoints:
    co2_ppm: float
    humidity_rh: float

    def __post_init__(self):
        if not (math.isfinite(self.co2_ppm) and 0 <= self.co2_ppm <= MAX_CO2_PPM
                and math.isfinite(self.humidity_rh) and MIN_HUMIDITY_RH <= self.humidity_rh <= MAX_HUMIDITY_RH):
            raise ValueError("CO2: 0–20000 ppm; humidity: 70–100 %RH. Enter finite numbers only.")
        object.__setattr__(self, "co2_ppm", round(self.co2_ppm, 1))
        object.__setattr__(self, "humidity_rh", round(self.humidity_rh, 1))

    @classmethod
    def from_payload(cls, payload):
        return cls(float(payload["co2_ppm"]), float(payload["humidity_rh"]))


class SetpointRepository:
    def __init__(self, database):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.database, timeout=10)) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS control_setpoints(
                id INTEGER PRIMARY KEY CHECK(id=1), co2_ppm REAL NOT NULL,
                humidity_rh REAL NOT NULL, confirmed_at TEXT NOT NULL)""")

    def load(self):
        with closing(sqlite3.connect(self.database, timeout=10)) as db:
            row = db.execute("SELECT co2_ppm,humidity_rh FROM control_setpoints WHERE id=1").fetchone()
        return Setpoints(*row) if row else None

    def save(self, setpoints):
        if self.load() == setpoints:
            return
        with closing(sqlite3.connect(self.database, timeout=10)) as db, db:
            db.execute("""INSERT INTO control_setpoints VALUES(1,?,?,?)
                ON CONFLICT(id) DO UPDATE SET co2_ppm=excluded.co2_ppm,
                humidity_rh=excluded.humidity_rh,confirmed_at=excluded.confirmed_at""",
                       (setpoints.co2_ppm, setpoints.humidity_rh,
                        datetime.now(timezone.utc).isoformat()))


class ControlMonitor:
    def __init__(self, database):
        self.repository = SetpointRepository(database)
        self._lock = threading.Lock()
        self._setpoints = self.repository.load()
        self._supported = False
        self._online = False
        self._enabled = False
        self._persisted = False
        self._samples = deque(maxlen=MAX_CONTROL_SAMPLES)
        self._last_sample = None
        self._last_boot = None
        self._message = "Waiting for the lance."
        self._actuators = actuator_telemetry({})

    def ingest(self, payload):
        control = payload.get("control")
        if not isinstance(control, dict) or control.get("version") != 1:
            with self._lock:
                self._online = True
                self._supported = False
                self._enabled = False
                self._actuators = actuator_telemetry({})
                self._message = "Firmware update required to save setpoints."
            return
        setpoints = Setpoints.from_payload(control["setpoints"])
        persisted = control.get("persisted") is True
        if persisted:
            self.repository.save(setpoints)
        measurement = payload.get("measurement", {})
        sample_id = (measurement.get("boot_id"), measurement.get("sequence"))
        sample = telemetry_sample(control)
        with self._lock:
            self._setpoints = setpoints
            self._supported = control.get("settings_supported") is True
            self._persisted = persisted
            self._online = True
            self._enabled = control.get("enabled") is True
            self._actuators = actuator_telemetry(control)
            self._message = "Controller active" if self._enabled else "Controller not configured – outputs inactive."
            if not persisted:
                self._message += " Setpoints are factory defaults."
            has_measurement = sample_id[0] is not None and sample_id[1] is not None
            if has_measurement and self._last_boot is not None and self._last_boot != sample_id[0]:
                self._samples.clear()
            if has_measurement and sample_id != self._last_sample:
                self._samples.append(sample)
                self._last_sample = sample_id
                self._last_boot = sample_id[0]

    def disconnected(self, message):
        with self._lock:
            self._online = False
            self._actuators = actuator_telemetry({})
            self._message = message

    def snapshot(self):
        with self._lock:
            return {"setpoints": self._setpoints, "supported": self._supported,
                    "online": self._online, "enabled": self._enabled,
                    "persisted": self._persisted, "samples": list(self._samples),
                    "actuators": dict(self._actuators),
                    "message": self._message}
