"""Аудит выдачи без записи в деловую БД, без содержимого документов и путей."""
from contextlib import closing
import json
import sqlite3
from pathlib import Path


def record(database, operation, *, project_id, release_ids, source, user_id=None):
    from .services.context import current_actor
    actor = current_actor.get()
    path = Path(str(Path(database).resolve()) + '.audit.sqlite3')
    with closing(sqlite3.connect(path)) as c, c:
        c.execute('''CREATE TABLE IF NOT EXISTS read_events (
            id INTEGER PRIMARY KEY, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            operation TEXT NOT NULL, project_id INTEGER NOT NULL,
            release_ids TEXT NOT NULL, source TEXT NOT NULL, user_id INTEGER,
            actor_id TEXT, actor_role TEXT, on_behalf_of TEXT, result TEXT)''')
        # Upgrade existing sidecars in place, without touching the business database.
        columns = {row[1] for row in c.execute('PRAGMA table_info(read_events)')}
        for name in ('actor_id', 'actor_role', 'on_behalf_of', 'result'):
            if name not in columns:
                c.execute(f'ALTER TABLE read_events ADD COLUMN {name} TEXT')
        c.execute('''INSERT INTO read_events
            (operation,project_id,release_ids,source,user_id,actor_id,actor_role,on_behalf_of,result)
            VALUES(?,?,?,?,?,?,?,?,?)''',
                  (operation, project_id, json.dumps(release_ids), source, user_id,
                   str(actor.user_id) if actor else None, actor.role if actor else None,
                   str(actor.on_behalf_of) if actor and actor.on_behalf_of is not None else None,
                   'success'))
