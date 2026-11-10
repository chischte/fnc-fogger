"""Persist live and buffered samples with boot-relative measurement times."""
import logging
from datetime import datetime, timedelta, timezone

from . import logger

LOG = logging.getLogger(__name__)
INSERT_SQL = (f"INSERT OR IGNORE INTO measurements({','.join(logger.FIELDS)}) "
              f"VALUES({','.join('?' for _ in logger.FIELDS)})")


class MeasurementRecorder:
    def __init__(self, database):
        self.database = database
        self.database.execute("""CREATE TABLE IF NOT EXISTS measurement_clocks(
            boot_id INTEGER PRIMARY KEY, boot_time TEXT NOT NULL)""")
        self.database.commit()
        self.clocks = {}

    def _clock(self, boot_id):
        if boot_id in self.clocks:
            return self.clocks[boot_id]
        row = self.database.execute(
            "SELECT boot_time FROM measurement_clocks WHERE boot_id=?", (boot_id,)).fetchone()
        if row:
            clock = datetime.fromisoformat(row[0])
        else:
            row = self.database.execute("""SELECT COALESCE(device_time,received_at),uptime_ms
                FROM measurements WHERE boot_id=? ORDER BY id LIMIT 1""", (boot_id,)).fetchone()
            if row is None:
                return None
            clock = datetime.fromisoformat(row[0]) - timedelta(milliseconds=row[1])
            self._save_clock(boot_id, clock)
        self.clocks[boot_id] = clock
        return clock

    def _save_clock(self, boot_id, clock):
        self.database.execute("INSERT OR IGNORE INTO measurement_clocks VALUES(?,?)",
                              (boot_id, clock.isoformat()))
        self.clocks[boot_id] = clock

    def record_live(self, payload, received_at=None):
        record = payload.get("measurement", payload)
        received_at = received_at or datetime.now(timezone.utc)
        boot_id = int(record["boot_id"])
        if self._clock(boot_id) is None:
            self._save_clock(boot_id, received_at - timedelta(milliseconds=record["uptime_ms"]))
        return self.record_buffer([record], received_at)

    def record_buffer(self, records, received_at=None):
        received_at = received_at or datetime.now(timezone.utc)
        inserted = 0
        unknown = 0
        with self.database:
            for payload in records:
                record = payload.get("measurement", payload)
                clock = self._clock(int(record["boot_id"]))
                if clock is None:
                    unknown += 1
                    continue
                row = logger.normalize(record)
                row["received_at"] = received_at.isoformat(timespec="seconds")
                row["device_time"] = (clock + timedelta(milliseconds=record["uptime_ms"])).isoformat(timespec="milliseconds")
                before = self.database.total_changes
                self.database.execute(INSERT_SQL, tuple(row[key] for key in logger.FIELDS))
                inserted += self.database.total_changes - before
        if unknown:
            LOG.warning("Skipped %s buffered samples without a known boot clock", unknown)
        return inserted
