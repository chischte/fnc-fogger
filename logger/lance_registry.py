"""Persistent device labels and isolated measurement database assignments."""
import re
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Lance:
    device_id: str
    hostname: str
    port: int
    name: str = ""
    location: str = ""
    database_name: str = ""
    firmware: str = ""
    hardware_profile: str = ""
    build_id: str = ""
    last_seen: str = ""

    @property
    def url(self):
        return f"http://{self.hostname}:{self.port}"

    @property
    def label(self):
        return self.name or f"Lance {self.device_id[-6:]}"


class LanceRegistry:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "lances.db"
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS lances(
                device_id TEXT PRIMARY KEY, hostname TEXT NOT NULL,
                port INTEGER NOT NULL, name TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL DEFAULT '', database_name TEXT NOT NULL UNIQUE)""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(lances)")}
            for column in ("firmware", "hardware_profile", "build_id", "last_seen"):
                if column not in columns:
                    db.execute(f"ALTER TABLE lances ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
            if "removed" not in columns:
                db.execute("ALTER TABLE lances ADD COLUMN removed INTEGER NOT NULL DEFAULT 0")
            db.execute("""CREATE TABLE IF NOT EXISTS firmware_updates(
                id INTEGER PRIMARY KEY, device_id TEXT NOT NULL, recorded_at TEXT NOT NULL,
                version TEXT NOT NULL, build_id TEXT NOT NULL, hardware_profile TEXT NOT NULL,
                sha256 TEXT NOT NULL, phase TEXT NOT NULL, detail TEXT NOT NULL)""")

    @contextmanager
    def _connect(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            with db:
                yield db

    def list(self):
        with self._connect() as db:
            return [Lance(*row) for row in db.execute(
                "SELECT device_id,hostname,port,name,location,database_name,"
                "firmware,hardware_profile,build_id,last_seen "
                "FROM lances WHERE removed=0 ORDER BY name,device_id")]

    def remember(self, lance, sensor_serial=None, status=None):
        if not re.fullmatch(r"[0-9a-f]{12}", lance.device_id):
            raise ValueError("Invalid lance device ID")
        with self._connect() as db:
            existing = db.execute("SELECT database_name FROM lances WHERE device_id=?",
                                  (lance.device_id,)).fetchone()
            database_name = existing[0] if existing else f"devices/{lance.device_id}.db"
            legacy_assigned = db.execute(
                "SELECT 1 FROM lances WHERE database_name='measurements.db'").fetchone()
            if not existing and not legacy_assigned and self._matches_legacy(sensor_serial):
                database_name = "measurements.db"
            db.execute("""INSERT INTO lances(device_id,hostname,port,database_name)
                VALUES(?,?,?,?) ON CONFLICT(device_id) DO UPDATE SET
                hostname=excluded.hostname,port=excluded.port,removed=0""",
                       (lance.device_id, lance.hostname, lance.port, database_name))
            if status is not None:
                db.execute("""UPDATE lances SET firmware=?,hardware_profile=?,build_id=?,last_seen=?
                    WHERE device_id=?""", (
                    status.get("firmware", ""), status.get("hardware_profile", ""),
                    status.get("build_id", ""), datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    lance.device_id))
        return next(item for item in self.list() if item.device_id == lance.device_id)

    def _matches_legacy(self, sensor_serial):
        path = self.directory / "measurements.db"
        if not path.exists():
            return False
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            columns = {row[1] for row in db.execute("PRAGMA table_info(measurements)")}
            if "scd_serial" not in columns or not sensor_serial:
                return False
            row = db.execute("SELECT scd_serial FROM measurements WHERE scd_serial IS NOT NULL "
                             "ORDER BY id DESC LIMIT 1").fetchone()
            return row is not None and row[0] == sensor_serial

    def save_labels(self, device_id, name, location):
        with self._connect() as db:
            db.execute("UPDATE lances SET name=?,location=? WHERE device_id=?",
                       (name.strip(), location.strip(), device_id))

    def measurement_path(self, lance):
        return self.directory / lance.database_name

    def remove(self, device_id):
        # Keep the database assignment so historical measurements cannot be reassigned.
        with self._connect() as db:
            db.execute("UPDATE lances SET removed=1 WHERE device_id=?", (device_id,))

    def record_update(self, device_id, image, phase, detail=""):
        with self._connect() as db:
            db.execute("""INSERT INTO firmware_updates(
                device_id,recorded_at,version,build_id,hardware_profile,sha256,phase,detail)
                VALUES(?,?,?,?,?,?,?,?)""", (
                device_id, datetime.now(timezone.utc).isoformat(timespec="seconds"),
                image.version, image.build_id, image.profile, image.sha256, phase, detail))
