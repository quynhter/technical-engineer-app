"""Учетные записи локального веб-приложения, отдельно от данных ИТД."""
import hashlib
from pathlib import Path
import re
import secrets
import sqlite3
from threading import RLock
from time import time as monotonic  # Compatibility clock name; persistent sessions use epoch seconds.
from contextlib import closing

ROLES = ('admin', 'editor', 'viewer')
KEY_PATTERN = re.compile(r'[A-Za-z0-9_-]{43}')
PUBLIC_FIELDS = 'id, first_name, last_name, role'
SESSION_LIFETIME = 8 * 60 * 60
SESSION_IDLE = 30 * 60
MAX_USER_SESSIONS = 10


class SessionExpired(PermissionError):
    pass


def key_digest(key):
    if not isinstance(key, str) or not KEY_PATTERN.fullmatch(key):
        raise PermissionError('Код входа недействителен')
    return hashlib.sha256(key.encode('ascii')).hexdigest()


def names(data):
    result = []
    for field in ('first_name', 'last_name'):
        value = data.get(field)
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 80:
            raise ValueError('Заполните имя и фамилию (до 80 символов)')
        result.append(value.strip())
    return tuple(result)


class Accounts:
    def __init__(self, path):
        self.path = Path(path)
        self.session_lock = RLock()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        return closing(connection)

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(mode=0o600, exist_ok=True)
        with self.connect() as c, c:
            c.execute('PRAGMA journal_mode=WAL')
            c.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin','editor','viewer')),
                    code_hash TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    database_path TEXT NOT NULL,
                    itd_root TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS document_roots (
                    database_path TEXT NOT NULL,
                    path TEXT NOT NULL,
                    PRIMARY KEY (database_path, path)
                );
                CREATE TABLE IF NOT EXISTS account_schema_migrations (
                    version INTEGER PRIMARY KEY, name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY CHECK(length(token_hash)=64),
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at REAL NOT NULL, used_at REAL NOT NULL,
                    expires_at REAL NOT NULL, idle_expires_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
            """)
            c.execute('BEGIN IMMEDIATE')
            c.execute("INSERT OR IGNORE INTO account_schema_migrations VALUES(1,'persistent_sessions')")
            if c.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                return None
            key = secrets.token_urlsafe(32)
            c.execute('INSERT INTO users(first_name,last_name,role,code_hash) VALUES (?,?,?,?)',
                      ('Администратор', 'ИТД', 'admin', key_digest(key)))
            return key

    def get(self, user_id):
        with self.connect() as c:
            row = c.execute(f'SELECT {PUBLIC_FIELDS} FROM users WHERE id=?', (user_id,)).fetchone()
            if row is None:
                raise PermissionError('Пользователь удалён')
            return dict(row)

    def _prune_sessions(self, now):
        with self.connect() as c, c:
            c.execute('DELETE FROM sessions WHERE expires_at<=? OR idle_expires_at<=?', (now, now))

    @property
    def sessions(self):
        """Read-only compatibility snapshot: only hashes, never recoverable tokens."""
        with self.connect() as c:
            return {r['token_hash']: (r['user_id'], r['created_at'], r['used_at'])
                    for r in c.execute('SELECT * FROM sessions')}

    def session(self, user_id):
        now = monotonic()
        with self.session_lock, self.connect() as c, c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('DELETE FROM sessions WHERE expires_at<=? OR idle_expires_at<=?', (now, now))
            count = c.execute('SELECT count(*) FROM sessions WHERE user_id=?', (user_id,)).fetchone()[0]
            if count >= MAX_USER_SESSIONS:
                c.execute('DELETE FROM sessions WHERE token_hash IN (SELECT token_hash FROM sessions WHERE user_id=? ORDER BY created_at,rowid LIMIT ?)',
                          (user_id, count - MAX_USER_SESSIONS + 1))
            token = secrets.token_urlsafe(32)
            c.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)',
                      (key_digest(token), user_id, now, now, now + SESSION_LIFETIME, now + SESSION_IDLE))
        return token

    def discard_session(self, token):
        if not isinstance(token, str) or not KEY_PATTERN.fullmatch(token):
            return
        with self.session_lock, self.connect() as c, c:
            c.execute('DELETE FROM sessions WHERE token_hash=?', (key_digest(token),))

    def clear_sessions(self):
        with self.session_lock, self.connect() as c, c:
            c.execute('DELETE FROM sessions')

    def login(self, key):
        with self.connect() as c:
            row = c.execute('SELECT id FROM users WHERE code_hash=?', (key_digest(key),)).fetchone()
        if row is None:
            raise PermissionError('Код входа недействителен')
        return {'session': self.session(row['id']), 'user': self.get(row['id'])}

    def authenticate(self, token, *, touch=True):
        now = monotonic()
        if not isinstance(token, str) or not KEY_PATTERN.fullmatch(token):
            raise SessionExpired('Сеанс завершён. Войдите по коду доступа')
        with self.session_lock, self.connect() as c, c:
            if touch:
                c.execute('BEGIN IMMEDIATE')
            session = c.execute('SELECT * FROM sessions WHERE token_hash=? AND expires_at>? AND idle_expires_at>?',
                                (key_digest(token), now, now)).fetchone()
            if session is None:
                raise SessionExpired('Сеанс завершён. Войдите по коду доступа')
            user_id = session['user_id']
            if touch:
                c.execute('UPDATE sessions SET used_at=?,idle_expires_at=? WHERE token_hash=?',
                          (now, now + SESSION_IDLE, key_digest(token)))
        return self.get(user_id)

    def revoke(self, user_id):
        with self.session_lock, self.connect() as c, c:
            c.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))

    def list(self):
        with self.connect() as c:
            return [dict(row) for row in c.execute(f'SELECT {PUBLIC_FIELDS} FROM users ORDER BY last_name,first_name,id')]

    def save_profile(self, user_id, data):
        with self.connect() as c, c:
            c.execute('UPDATE users SET first_name=?,last_name=? WHERE id=?', (*names(data), user_id))
        return self.get(user_id)

    def create(self, data):
        role = data.get('role')
        if role not in ROLES:
            raise ValueError('Выберите роль пользователя')
        key = secrets.token_urlsafe(32)
        with self.connect() as c, c:
            user_id = c.execute('INSERT INTO users(first_name,last_name,role,code_hash) VALUES (?,?,?,?)',
                                (*names(data), role, key_digest(key))).lastrowid
        return {'user': self.get(user_id), 'code': key}

    def manage(self, operation, actor, data):
        target = data.get('id')
        if type(target) is not int:
            raise ValueError('Выберите пользователя')
        if operation == 'rotate':
            return self.rotate(target, actor)
        with self.connect() as c, c:
            c.execute('BEGIN IMMEDIATE')
            user = c.execute('SELECT role FROM users WHERE id=?', (target,)).fetchone()
            if user is None:
                raise ValueError('Пользователь не найден')
            if target == actor:
                raise ValueError('Для смены собственной роли или удаления обратитесь к другому администратору')
            if operation == 'delete':
                c.execute('DELETE FROM users WHERE id=?', (target,))
            elif operation == 'role':
                role = data.get('role')
                if role not in ROLES:
                    raise ValueError('Выберите роль пользователя')
                c.execute('UPDATE users SET role=? WHERE id=?', (role, target))
            else:
                raise ValueError('Неизвестное действие с пользователем')
        self.revoke(target)
        return {'ok': True}

    def rotate(self, user_id, actor):
        key = secrets.token_urlsafe(32)
        with self.connect() as c, c:
            if not c.execute('UPDATE users SET code_hash=? WHERE id=?', (key_digest(key), user_id)).rowcount:
                raise ValueError('Пользователь не найден')
        self.revoke(user_id)
        result = {'code': key}
        if actor == user_id:
            result['session'] = self.session(user_id)
        return result

    def settings(self):
        with self.connect() as c:
            row = c.execute('SELECT database_path,itd_root FROM settings WHERE id=1').fetchone()
            return dict(row) if row else None

    def roots(self, database):
        with self.connect() as c:
            return tuple(Path(row[0]) for row in c.execute(
                'SELECT path FROM document_roots WHERE database_path=?', (str(database),)))

    def _check_root(self, c, database, itd_root):
        for row in c.execute('SELECT path FROM document_roots WHERE database_path<>?', (str(database),)):
            other = Path(row[0])
            if itd_root.is_relative_to(other) or other.is_relative_to(itd_root):
                raise ValueError('Эта папка пересекается с деревом другой БД. Выберите отдельную папку ИТД')

    def check_root(self, database, itd_root):
        with self.connect() as c:
            self._check_root(c, database, itd_root)

    def record_root(self, c, database, itd_root):
        self._check_root(c, database, itd_root)
        c.execute('INSERT OR IGNORE INTO document_roots VALUES(?,?)', (str(database), str(itd_root)))

    def remember_root(self, database, itd_root):
        with self.connect() as c, c:
            c.execute('BEGIN IMMEDIATE')
            self.record_root(c, database, itd_root)

    def save_settings(self, database, itd_root):
        with self.connect() as c, c:
            c.execute('BEGIN IMMEDIATE')
            self.record_root(c, database, itd_root)
            c.execute('INSERT OR REPLACE INTO settings VALUES(1,?,?)', (str(database), str(itd_root)))
