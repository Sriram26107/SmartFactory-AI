import os
from sqlalchemy import create_engine, text

def get_engine():
    """PostgreSQL if DATABASE_URL is set; otherwise persistent local SQLite."""
    url=os.getenv('DATABASE_URL','sqlite:///smartfactory.db')
    return create_engine(url,pool_pre_ping=True)

def initialize_db(engine):
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE IF NOT EXISTS factory_events (id INTEGER PRIMARY KEY, machine_id VARCHAR(32) NOT NULL, event_type VARCHAR(100) NOT NULL, note TEXT)'))

def add_event(engine,machine_id,event_type,note=''):
    with engine.begin() as conn:
        conn.execute(text('INSERT INTO factory_events (machine_id,event_type,note) VALUES (:m,:e,:n)'),{'m':machine_id,'e':event_type,'n':note})

def list_events(engine):
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text('SELECT machine_id,event_type,note FROM factory_events ORDER BY id DESC LIMIT 100')).mappings()]
