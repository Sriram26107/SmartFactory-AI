"""Persistent, read-only factory operations workflows.

Telemetry may open alerts, create maintenance tasks and flag production impact.
No commands are ever sent to industrial equipment.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from smartfactory.live.telemetry import validate, condition_status

DEFAULT_DB = Path('smartfactory_workflows.db')


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def connect(path=None):
    db = sqlite3.connect(str(path or DEFAULT_DB), timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA busy_timeout=20000')
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS incidents (
      id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT NOT NULL,
      severity TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Open',
      opened_at TEXT NOT NULL, updated_at TEXT NOT NULL, resolved_at TEXT,
      reading_json TEXT NOT NULL, source TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS ix_incident_open ON incidents(machine_id,status);
    CREATE TABLE IF NOT EXISTS maintenance_tasks (
      id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id INTEGER UNIQUE,
      machine_id TEXT NOT NULL, task_type TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'Open', created_at TEXT NOT NULL,
      closed_at TEXT, note TEXT NOT NULL DEFAULT '',
      FOREIGN KEY(incident_id) REFERENCES incidents(id));
    CREATE TABLE IF NOT EXISTS production_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT NOT NULL,
      work_order TEXT NOT NULL, event_time TEXT NOT NULL,
      planned_minutes REAL NOT NULL, runtime_minutes REAL NOT NULL,
      ideal_cycle_seconds REAL NOT NULL, total_units INTEGER NOT NULL,
      good_units INTEGER NOT NULL);
    ''')
    db.commit()
    return db


def process_telemetry(payload, source='mqtt', path=None):
    """Idempotent for repeated abnormal readings while incident remains open.

    An incident is not auto-closed by a normal reading; an operator must review it.
    """
    reading = validate(payload)
    severity = condition_status(reading['temperature_c'], reading['vibration_mm_s'])
    if severity == 'Normal':
        return {'severity': severity, 'incident_id': None, 'created': False}
    now = _now()
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute('''SELECT id,severity FROM incidents
            WHERE machine_id=? AND status='Open' ORDER BY id DESC LIMIT 1''',
            (reading['machine_id'],)).fetchone()
        if existing:
            # Escalate Watch -> High, but never downgrade an active incident.
            new_severity = 'High' if 'High' in (existing['severity'], severity) else 'Watch'
            db.execute('''UPDATE incidents SET severity=?,updated_at=?,reading_json=? WHERE id=?''',
                       (new_severity, now, json.dumps(reading), existing['id']))
            return {'severity': new_severity, 'incident_id': existing['id'], 'created': False}
        cursor = db.execute('''INSERT INTO incidents
            (machine_id,severity,status,opened_at,updated_at,reading_json,source)
            VALUES (?,?,'Open',?,?,?,?)''',
            (reading['machine_id'],severity,now,now,json.dumps(reading),source))
        incident_id = cursor.lastrowid
        db.execute('''INSERT INTO maintenance_tasks
            (incident_id,machine_id,task_type,status,created_at,note)
            VALUES (?,?,?,'Open',?,?)''',
            (incident_id,reading['machine_id'],'Inspect machine condition',now,
             'Automatically created from a threshold alert; technician review required.'))
    return {'severity': severity, 'incident_id': incident_id, 'created': True}


def list_incidents(path=None, status=None):
    with connect(path) as db:
        if status:
            rows = db.execute('SELECT * FROM incidents WHERE status=? ORDER BY id DESC',(status,)).fetchall()
        else:
            rows = db.execute('SELECT * FROM incidents ORDER BY id DESC').fetchall()
    return [dict(row) for row in rows]


def list_tasks(path=None):
    with connect(path) as db:
        rows = db.execute('SELECT * FROM maintenance_tasks ORDER BY id DESC').fetchall()
    return [dict(row) for row in rows]


def resolve_incident(incident_id, note, path=None):
    if not str(note).strip():
        raise ValueError('A resolution note is required')
    now = _now()
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        incident = db.execute('SELECT id,status FROM incidents WHERE id=?',(incident_id,)).fetchone()
        if incident is None or incident['status'] != 'Open':
            raise ValueError('Incident is missing or already resolved')
        db.execute("UPDATE incidents SET status='Resolved',resolved_at=?,updated_at=? WHERE id=?",(now,now,incident_id))
        db.execute("UPDATE maintenance_tasks SET status='Closed',closed_at=?,note=? WHERE incident_id=?",(now,note.strip(),incident_id))


def add_production_event(machine_id, work_order, planned_minutes, runtime_minutes,
                         ideal_cycle_seconds, total_units, good_units, path=None):
    if not machine_id or not work_order:
        raise ValueError('Machine and work order are required')
    if planned_minutes <= 0 or runtime_minutes < 0 or runtime_minutes > planned_minutes:
        raise ValueError('Invalid planned/runtime minutes')
    if ideal_cycle_seconds <= 0 or total_units < 0 or not 0 <= good_units <= total_units:
        raise ValueError('Invalid cycle time or counts')
    if ideal_cycle_seconds * total_units > runtime_minutes * 60 + 1e-7:
        raise ValueError('Ideal production time cannot exceed runtime')
    with connect(path) as db:
        db.execute('''INSERT INTO production_events
          (machine_id,work_order,event_time,planned_minutes,runtime_minutes,
           ideal_cycle_seconds,total_units,good_units) VALUES (?,?,?,?,?,?,?,?)''',
           (machine_id,work_order,_now(),planned_minutes,runtime_minutes,
            ideal_cycle_seconds,total_units,good_units))


def production_summary(path=None):
    with connect(path) as db:
        rows = [dict(r) for r in db.execute('SELECT * FROM production_events ORDER BY id DESC')]
    if not rows:
        return {'events': [], 'oee': None, 'reason': 'No measured production events'}
    planned = sum(r['planned_minutes'] for r in rows)
    runtime = sum(r['runtime_minutes'] for r in rows)
    ideal = sum(r['ideal_cycle_seconds'] * r['total_units'] / 60 for r in rows)
    units = sum(r['total_units'] for r in rows)
    good = sum(r['good_units'] for r in rows)
    availability = runtime/planned if planned else 0
    performance = ideal/runtime if runtime else 0
    quality = good/units if units else 0
    return {'events': rows, 'oee': {
        'availability_percent': round(availability*100,2),
        'performance_percent': round(performance*100,2),
        'quality_percent': round(quality*100,2),
        'oee_percent': round(availability*performance*quality*100,2),
        'good_units': good, 'total_units': units}}


def production_impact(path=None):
    """Flag potential production impact, not actual machine downtime."""
    incidents = list_incidents(path, 'Open')
    machines = sorted({r['machine_id'] for r in incidents})
    return {'machines_needing_review': machines,
            'open_incidents': len(incidents),
            'note': 'Potential production impact only; no downtime is inferred or commanded.'}
