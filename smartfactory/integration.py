"""Shared source-aware data layer for the 12 SmartFactory modules.

Connected mode never silently falls back to demo records.
CSV files are staged, validated, then atomically replaced in a local SQLite database.
"""
import io
import os
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd
from smartfactory.data.demo import load_data
from smartfactory.live.telemetry import recent_readings, latest_by_machine

ROOT = Path(os.getenv('SMARTFACTORY_DATA_DB', 'smartfactory_integrated.db')).expanduser().resolve()
SCHEMAS = {
    'machines': ('machine_id','line','type'),
    'orders': ('work_order','product','quantity','priority','hours','status','line'),
    'quality': ('serial_number','work_order','result','defect'),
    'inventory': ('part','on_hand','reorder_point','daily_demand','lead_days'),
    'deliveries': ('delivery','destination','distance_km','priority','due_hours'),
    'energy': ('timestamp','facility','consumption_kwh','renewable_kwh'),
    'bom': ('product','component','units_per_product'),
    'requirements': ('requirement_id','product','requirement','verification'),
    'service': ('machine_id','service_type','status'),
}
NUMERIC = {
    'orders': ('quantity','priority','hours'),
    'inventory': ('on_hand','reorder_point','daily_demand','lead_days'),
    'deliveries': ('distance_km','priority','due_hours'),
    'energy': ('consumption_kwh','renewable_kwh'),
    'bom': ('units_per_product',),
}
IDENTIFIER = re.compile(r'^[a-z_]+$')

def connect(path=None):
    db=sqlite3.connect(str(path or ROOT), timeout=20)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA busy_timeout=20000')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('''CREATE TABLE IF NOT EXISTS source_status (
        dataset TEXT PRIMARY KEY, updated_at TEXT NOT NULL, row_count INTEGER NOT NULL,
        origin TEXT NOT NULL)''')
    db.commit()
    return db

def validate_frame(name, frame):
    if name not in SCHEMAS:
        raise ValueError('Unsupported dataset')
    if not isinstance(frame,pd.DataFrame):
        raise ValueError('Expected CSV table')
    missing=set(SCHEMAS[name])-set(frame.columns)
    if missing:
        raise ValueError(f'Missing columns: {", ".join(sorted(missing))}')
    clean=frame.loc[:,SCHEMAS[name]].copy()
    if clean.empty:
        raise ValueError('Empty dataset is not accepted; use Clear to disconnect')
    if clean.isna().any().any():
        raise ValueError('Required columns cannot contain empty values')
    for col in NUMERIC.get(name,()):
        clean[col]=pd.to_numeric(clean[col],errors='raise')
        if not pd.Series(clean[col]).map(lambda x: pd.notna(x) and abs(float(x)) < 1e12).all():
            raise ValueError(f'Invalid numeric values in {col}')
    if name=='energy':
        clean['timestamp']=pd.to_datetime(clean['timestamp'],utc=True,errors='raise').dt.strftime('%Y-%m-%dT%H:%M:%S%z')
    if name=='quality' and not clean['result'].isin(['Pass','Fail']).all():
        raise ValueError('Quality result must be Pass or Fail')
    if name=='inventory' and (clean['daily_demand']<=0).any():
        raise ValueError('daily_demand must be greater than zero')
    return clean

def import_frame(name, frame, origin='csv', path=None):
    clean=validate_frame(name,frame)
    if not IDENTIFIER.fullmatch(name):
        raise ValueError('Invalid dataset name')
    now=datetime.now(timezone.utc).isoformat(timespec='seconds')
    with connect(path) as db:
        # Validate everything before modifying the existing dataset.
        db.execute('BEGIN IMMEDIATE')
        db.execute(f'DROP TABLE IF EXISTS "dataset_{name}"')
        cols=', '.join(f'"{col}" {"REAL" if col in NUMERIC.get(name,()) else "TEXT"}' for col in SCHEMAS[name])
        db.execute(f'CREATE TABLE "dataset_{name}" ({cols})')
        placeholders=','.join('?' for _ in SCHEMAS[name])
        db.executemany(f'INSERT INTO "dataset_{name}" VALUES ({placeholders})',
                       [tuple(None if pd.isna(v) else v for v in row) for row in clean.itertuples(index=False,name=None)])
        db.execute('INSERT OR REPLACE INTO source_status VALUES (?,?,?,?)',
                   (name,now,len(clean),str(origin)[:100]))
    return len(clean)

def import_csv(name, content, path=None):
    if len(content)>8_000_000:
        raise ValueError('CSV must be under 8 MB')
    return import_frame(name,pd.read_csv(io.BytesIO(content)),path=path)

def clear_dataset(name,path=None):
    if name not in SCHEMAS:
        raise ValueError('Unsupported dataset')
    with connect(path) as db:
        db.execute(f'DROP TABLE IF EXISTS "dataset_{name}"')
        db.execute('DELETE FROM source_status WHERE dataset=?',(name,))

def source_status(path=None):
    with connect(path) as db:
        return {r['dataset']:dict(r) for r in db.execute('SELECT * FROM source_status')}

def load_connected(path=None):
    status=source_status(path)
    out={}
    with connect(path) as db:
        for name in SCHEMAS:
            if name in status:
                out[name]=pd.read_sql_query(f'SELECT * FROM "dataset_{name}"',db)
            else:
                out[name]=None
    readings=recent_readings(5000)
    # Only actual MQTT readings count as connected machine telemetry.
    live=[r for r in readings if r['source'] in ('mqtt','api','opcua','modbus')]
    out['sensors']=pd.DataFrame(live) if live else None
    if out['sensors'] is not None:
        out['sensors']['timestamp']=pd.to_datetime(out['sensors']['received_at'],utc=True)
        out['sensors']['energy_kwh']=pd.NA  # Power (kW) is not energy (kWh).
        out['sensors']['runtime_hours']=pd.NA
    return out

def load_factory(mode='Simulation'):
    if mode=='Simulation':
        return load_data(),{name:'Simulation' for name in (*SCHEMAS,'sensors')}
    if mode!='Connected':
        raise ValueError('Unknown data mode')
    datasets=load_connected()
    status=source_status()
    origins={name:(status[name]['origin'] if name in status else 'Disconnected') for name in SCHEMAS}
    origins['sensors']='Live telemetry' if datasets['sensors'] is not None else 'Disconnected'
    return datasets,origins

def connected_latest(max_age_seconds=60):
    now=datetime.now(timezone.utc)
    rows=[r for r in latest_by_machine() if r['source'] in ('mqtt','api','opcua','modbus')]
    for r in rows:
        dt=datetime.fromisoformat(r['received_at'])
        age=(now-dt).total_seconds()
        r['age_seconds']=round(age,1)
        r['connection']='Live' if 0<=age<=max_age_seconds else 'Stale'
    return rows

def connection_summary(mode,datasets,origins):
    return [{'dataset':name,'status':('Simulation' if mode=='Simulation' else ('Connected' if datasets.get(name) is not None else 'Disconnected')),
             'source':origins.get(name,'Disconnected'),
             'rows':len(datasets[name]) if datasets.get(name) is not None else 0}
            for name in (*SCHEMAS,'sensors')]
