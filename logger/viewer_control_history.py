"""Read recorded PI telemetry without changing live controller state."""
import json
import math
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from matplotlib import dates as mdates

from .control_data import actuator_telemetry

PI_COLUMNS = tuple(f"{channel}_{term}" for channel in ("humidity", "co2")
                   for term in ("p", "i", "sum"))
MAX_CONTINUOUS_GAP_SECONDS = 15
DISPLAY_TIMEZONE = ZoneInfo("Europe/Zurich")


def recorded_sample(row):
    identifier, received_at, boot_id, raw = row
    try:
        timestamp = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    try:
        control = json.loads(raw)
    except (TypeError, ValueError):
        control = {}
    if not isinstance(control, dict):
        control = {}
    enabled = control.get("enabled") is True
    fault = control.get("fault") is True
    parameters = control.get("parameters", {})
    sample = {"id": identifier, "timestamp": timestamp.astimezone(DISPLAY_TIMEZONE).replace(tzinfo=None),
              "boot_id": boot_id, "gap": False, "enabled": enabled, "fault": fault,
              "fogger_enabled": control.get("fogger_enabled", True),
              "actuators": actuator_telemetry(control),
              "parameters": parameters if isinstance(parameters, dict) else {}}
    for column in PI_COLUMNS:
        channel, term = column.split("_")
        terms = control.get(channel, {})
        value = terms.get(term) if isinstance(terms, dict) else None
        valid = enabled and not fault and isinstance(value, (int, float)) and not isinstance(value, bool)
        if channel == "humidity" and not sample["fogger_enabled"]:
            valid = False
        sample[column] = float(value) if valid and math.isfinite(value) else float("nan")
    return sample


class ControlHistoryCache:
    def __init__(self):
        self._path = None
        self._last_id = 0
        self._frame = pd.DataFrame()
        self.revision = 0

    def load(self, database):
        path = Path(database).resolve()
        if not path.exists():
            return None
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='control_samples'").fetchone():
                return None
            maximum = db.execute("SELECT COALESCE(MAX(id),0) FROM control_samples").fetchone()[0]
            if self._path != path or maximum < self._last_id:
                self._path = path
                self._last_id = 0
                self._frame = pd.DataFrame()
                self.revision += 1
            if maximum == self._last_id:
                return self._frame
            rows = db.execute("SELECT id,received_at,boot_id,control_json FROM control_samples WHERE id>? AND id<=? ORDER BY id",
                              (self._last_id, maximum)).fetchall()
        samples = []
        previous = self._frame.iloc[-1] if not self._frame.empty else None
        for row in rows:
            sample = recorded_sample(row)
            if sample is None:
                continue
            if previous is not None and (sample["boot_id"] != previous["boot_id"] or
                    (sample["timestamp"] - previous["timestamp"]).total_seconds() > MAX_CONTINUOUS_GAP_SECONDS):
                gap = dict(sample, gap=True, timestamp=sample["timestamp"] - pd.Timedelta(microseconds=1))
                gap.update({column: float("nan") for column in PI_COLUMNS})
                samples.append(gap)
            samples.append(sample)
            previous = sample
        if samples:
            addition = pd.DataFrame(samples)
            self._frame = addition if self._frame.empty else pd.concat([self._frame, addition], ignore_index=True)
            self._frame.sort_values(["timestamp", "id"], inplace=True, ignore_index=True)
        self._last_id = maximum
        self.revision += 1
        return self._frame

    def window(self, database, limits):
        frame = self.load(database)
        if frame is None:
            return None
        selected = frame
        if limits is not None and not frame.empty:
            dates = mdates.date2num(frame["timestamp"].to_numpy())
            selected = frame.loc[(dates >= limits[0]) & (dates <= limits[1])]
        observed = selected.loc[~selected["gap"]] if not selected.empty else selected
        state = {"online": False, "enabled": False, "samples": [], "parameters": {}}
        if not observed.empty:
            latest = observed.iloc[-1]
            state.update(online=True, enabled=bool(latest["enabled"]), fault=bool(latest["fault"]),
                         actuators=latest["actuators"], parameters=latest["parameters"],
                         fogger_enabled=latest["fogger_enabled"],
                         samples=[{column: latest[column] for column in PI_COLUMNS}])
        return selected, state
