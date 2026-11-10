"""Учетные записи локального веб-приложения, отдельно от данных ИТД."""
import hashlib
from pathlib import Path
import re
import secrets
import sqlite3
from threading import RLock
from time import monotonic
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
        self.sessions = {}
        self.session_lock = RLock()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return closing(connection)

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(mode=0o600, exist_ok=True)
        with self.connect() as c, c:
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
            """)
            c.execute('BEGIN IMMEDIATE')
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
        for token, (_, created, used) in list(self.sessions.items()):
            if now - created >= SESSION_LIFETIME or now - used >= SESSION_IDLE:
                self.sessions.pop(token, None)

    def session(self, user_id):
        now = monotonic()
        with self.session_lock:
            self._prune_sessions(now)
            owned = [token for token, value in self.sessions.items() if value[0] == user_id]
            for token in owned[:max(0, len(owned) - MAX_USER_SESSIONS + 1)]:
                self.sessions.pop(token, None)
            token = secrets.token_urlsafe(32)
            self.sessions[token] = (user_id, now, now)
        return token

    def discard_session(self, token):
        with self.session_lock:
            self.sessions.pop(token, None)

    def clear_sessions(self):
        with self.session_lock:
            self.sessions.clear()

    def login(self, key):
        with self.connect() as c:
            row = c.execute('SELECT id FROM users WHERE code_hash=?', (key_digest(key),)).fetchone()
        if row is None:
            raise PermissionError('Код входа недействителен')
        return {'session': self.session(row['id']), 'user': self.get(row['id'])}

    def authenticate(self, token, *, touch=True):
        now = monotonic()
        with self.session_lock:
            self._prune_sessions(now)
            session = self.sessions.get(token)
            if session is None:
                raise SessionExpired('Сеанс завершён. Войдите по коду доступа')
            user_id, created, used = session
            if touch:
                self.sessions[token] = (user_id, created, now)
        return self.get(user_id)

    def revoke(self, user_id):
        with self.session_lock:
            for token, value in list(self.sessions.items()):
                if value[0] == user_id:
                    self.sessions.pop(token, None)

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
