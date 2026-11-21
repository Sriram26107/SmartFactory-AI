"""Validation and persistent storage for real-time telemetry."""
import math
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("SMARTFACTORY_LIVE_DB", "smartfactory_live.db")).expanduser().resolve()
MACHINE_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")

def connect(path=None):
    db = sqlite3.connect(str(path or DB_PATH), timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=20000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        received_at TEXT NOT NULL,
        machine_id TEXT NOT NULL,
        temperature_c REAL NOT NULL,
        vibration_mm_s REAL NOT NULL,
        pressure_bar REAL,
        energy_kw REAL,
        source TEXT NOT NULL
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS ix_telemetry_machine ON telemetry(machine_id,id)")
    db.commit()
    return db

def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("Telemetry must be a JSON object")
    mid = payload.get("machine_id")
    if not isinstance(mid, str) or not MACHINE_ID.fullmatch(mid):
        raise ValueError("Invalid machine_id")
    result = {"machine_id": mid}
    for key in ("temperature_c", "vibration_mm_s"):
        if key not in payload or isinstance(payload[key], bool):
            raise ValueError(f"Missing or invalid {key}")
        try:
            val = float(payload[key])
        except (ValueError, TypeError):
            raise ValueError(f"Invalid {key}") from None
        if not math.isfinite(val):
            raise ValueError(f"Non-finite {key}")
        result[key] = val
    for key in ("pressure_bar", "energy_kw"):
        val = payload.get(key)
        if val is None:
            result[key] = None
        else:
            if isinstance(val, bool):
                raise ValueError(f"Invalid {key}")
            try:
                val = float(val)
            except (TypeError, ValueError):
                raise ValueError(f"Invalid {key}") from None
            if not math.isfinite(val):
                raise ValueError(f"Non-finite {key}")
            result[key] = val
    return result

def save_reading(payload, source="mqtt", path=None):
    data = validate(payload)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect(path) as db:
        db.execute("""INSERT INTO telemetry
            (received_at,machine_id,temperature_c,vibration_mm_s,pressure_bar,energy_kw,source)
            VALUES (:received_at,:machine_id,:temperature_c,:vibration_mm_s,:pressure_bar,:energy_kw,:source)""",
            {**data, "received_at": timestamp, "source": source})
    return data

def recent_readings(limit=300, path=None):
    with connect(path) as db:
        rows = db.execute("SELECT * FROM telemetry ORDER BY id DESC LIMIT ?", (min(max(int(limit), 1), 5000),)).fetchall()
    return [dict(r) for r in reversed(rows)]

def latest_by_machine(path=None):
    with connect(path) as db:
        rows = db.execute("""SELECT t.* FROM telemetry t
            JOIN (SELECT machine_id, MAX(id) AS max_id FROM telemetry GROUP BY machine_id) latest
            ON t.machine_id=latest.machine_id AND t.id=latest.max_id
            ORDER BY t.machine_id""").fetchall()
    return [dict(r) for r in rows]

def condition_status(temperature_c, vibration_mm_s):
    # Illustrative thresholds only; configure and validate for actual equipment.
    if temperature_c >= 85 or vibration_mm_s >= 7:
        return "High"
    if temperature_c >= 70 or vibration_mm_s >= 4.5:
        return "Watch"
    return "Normal"
