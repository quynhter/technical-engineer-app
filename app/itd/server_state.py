"""Shared workspace lifecycle and locks; no network listener or HTTP dependencies."""
from contextlib import closing,contextmanager,nullcontext
from datetime import datetime
import hashlib,hmac,logging,secrets,sqlite3
from pathlib import Path
from threading import RLock
from .accounts import Accounts
from .db import MIGRATIONS,connect,initialize
from .paths import ROOT,database_workspace,itd_root,previous_itd_roots
from .services.context import Actor,ServiceContext
DB_LOG=logging.getLogger('itd.db')

def prepare_database(path):
    """Обновление с SQLite backup до миграции; ни одна деловая запись не создаётся."""
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    latest = max(int(p.name[:3]) for p in MIGRATIONS.glob('[0-9][0-9][0-9]_*.sql'))
    if path.exists():
        with closing(sqlite3.connect(path)) as source:
            table = source.execute("SELECT 1 FROM sqlite_master WHERE name='schema_migrations'").fetchone()
            version = source.execute('SELECT max(version) FROM schema_migrations').fetchone()[0] if table else 0
            mode = source.execute('PRAGMA journal_mode').fetchone()[0]
            if (version or 0) < latest or mode.lower() != 'wal':
                folder = path.parent / 'backups'
                folder.mkdir(exist_ok=True)
                backup = folder / f'before-web-{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}.db'
                with closing(sqlite3.connect(backup)) as target:
                    source.backup(target)
    initialize(path)
    return backup


class WorkspaceState:
    daemon_threads = True
    template_bundle = None
    templates = None

    def __init__(self, database):
        self.database = Path(database).resolve()
        self.plan_secret = secrets.token_urlsafe(32)
        self.accounts = Accounts(self.database.with_name(self.database.name + '.accounts.sqlite3'))
        self.lock = RLock()
        self.state_lock = RLock()
        self.workspace_id = secrets.token_urlsafe(24)
        self.itd_root = None

    def prepare_workspace_database(self, database):
        backup = prepare_database(database)
        if self.template_bundle is not None:
            from .services.template_bundle import install_bundle
            install_bundle(database, self.template_bundle, self.templates)
        return backup

    def prepare(self):
        # Настройки и аккаунты остаются доступны при смене деловой БД.
        existing_accounts = self.accounts.path.exists()
        code = self.accounts.initialize() if existing_accounts else None
        settings = self.accounts.settings() if existing_accounts else None
        if settings:
            self.database = Path(settings['database_path'])
            self.itd_root = Path(settings['itd_root'])
            if not self.database.is_file():
                raise ValueError('Выбранная БД недоступна. Проверьте путь: ' + str(self.database))
        backup = self.prepare_workspace_database(self.database)
        if not existing_accounts:
            code = self.accounts.initialize()
        self.accounts.remember_root(self.database, Path(self.settings()['itd_root']))
        DB_LOG.info('База ИТД подготовлена')
        return backup, code

    def settings(self):
        return {'database_path': str(self.database),
                'itd_root': str(self.itd_root or database_workspace(self.database) / 'ИТД')}

    def configure(self, data, user_id):
        from .layout import check_path
        explicit_folder = 'itd_root' in data
        if not explicit_folder:
            value = data.get('database_path')
            if isinstance(value,str) and Path(value.strip()).expanduser().is_absolute():
                database = Path(value.strip()).expanduser().resolve()
                if database == self.database:
                    return {'settings':self.settings()}
                data = {**data,'itd_root':str(database_workspace(database)/'ИТД')}
        paths = []
        for name in ('database_path', 'itd_root'):
            value = data.get(name)
            if not isinstance(value, str) or not value.strip() or not Path(value.strip()).expanduser().is_absolute():
                raise ValueError('Укажите абсолютные пути к БД и папке ИТД')
            paths.append(Path(value.strip()).expanduser().resolve())
        database, folder = paths
        if database.suffix.lower() != '.db' or not database.is_file():
            raise ValueError('Укажите существующий файл с расширением .db')
        if not folder.is_dir() and (folder.exists() or not folder.parent.is_dir()):
            raise ValueError('Укажите папку ИТД или новую папку в существующем каталоге')
        if any(folder == path or folder.is_relative_to(path) for path in
               (ROOT / 'app', ROOT / 'ai/skills', ROOT / 'db', ROOT / 'logs', ROOT / '.git',
                database.parent / 'archive', database.parent / 'work', database.parent / 'backups')):
            raise ValueError('Выберите отдельную папку ИТД вне служебных каталогов')
        if database.is_relative_to(folder):
            raise ValueError('БД должна находиться за пределами папки ИТД')
        check_path(folder)
        if self.settings() == {'database_path': str(database), 'itd_root': str(folder)}:
            return {'settings': self.settings()}
        self.accounts.check_root(database, folder)
        from .services.queries import check_workspace_switch
        user = self.accounts.get(user_id)
        check_workspace_switch(ServiceContext(database=self.database),
                               Actor(user_id=user_id, role=user['role'], source='web'))
        self.prepare_workspace_database(database)
        if explicit_folder:
            folder.mkdir(exist_ok=True)
        self.accounts.save_settings(database, folder)
        with self.state_lock:
            self.database, self.itd_root = database, folder
            self.workspace_id = secrets.token_urlsafe(24)
            self.accounts.clear_sessions()
        self.plan_secret = secrets.token_urlsafe(32)
        DB_LOG.info('Изменены пути к БД или папке ИТД пользователем %s', user_id)
        return {'settings': self.settings(), 'session': self.accounts.session(user_id)}

    @contextmanager
    def workspace_scope(self, *, write=True):
        # Serialize mutations, but keep read-only requests and downloads independent.
        with self.lock if write else nullcontext():
            with self.state_lock:
                database, root = self.database, self.itd_root
            roots = previous_itd_roots.set(self.accounts.roots(database) if self.accounts.path.exists() else ())
            marker = itd_root.set(root)
            try:
                yield database
            finally:
                itd_root.reset(marker)
                previous_itd_roots.reset(roots)

    def revision(self, database):
        # Include WAL for databases edited by external clients. Do not expose paths.
        stats = []
        for path in (database, Path(str(database) + '-wal')):
            try:
                stat = path.stat()
                stats.append((stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns))
            except FileNotFoundError:
                stats.append(None)
        return hmac.new(self.plan_secret.encode(), repr(stats).encode(), hashlib.sha256).hexdigest()

    @property
    def origin(self):
        host = self.server_address[0]
        return f'http://{"127.0.0.1" if host == "0.0.0.0" else host}:{self.server_port}'
