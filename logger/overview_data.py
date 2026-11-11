"""Bounded, read-only history snapshots for the multi-device overview."""
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

from .viewer_data import normalize_data, read_database

HISTORY_WINDOW = timedelta(minutes=30)
MAX_HISTORY_ROWS = 5000
DATABASE_TIMEOUT_SECONDS = 0.5


def overview_time():
    return datetime.now(ZoneInfo("Europe/Zurich")).replace(tzinfo=None)


def load_overview_history(database, end):
    """Read recent IDs only; never create a missing database or write to one."""
    database = Path(database)
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro",
                                 uri=True, timeout=DATABASE_TIMEOUT_SECONDS)) as db:
        db.execute("BEGIN")
        last_id = db.execute("SELECT COALESCE(MAX(id),0) FROM measurements").fetchone()[0]
        frame = normalize_data(read_database(db, max(0, last_id - MAX_HISTORY_ROWS)))
    return frame[frame["timestamp"].between(end - HISTORY_WINDOW, end)]
