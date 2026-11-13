"""Локальный HTTP-интерфейс ИТД без дополнительных зависимостей и API модели."""
from __future__ import annotations

import argparse
import base64
import binascii
import errno
from contextlib import closing, contextmanager, nullcontext
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import hmac
import logging
import mimetypes
from pathlib import Path
import secrets
import sqlite3
import tempfile
from threading import RLock
from urllib.parse import parse_qs, urlsplit
import webbrowser

from .db import MIGRATIONS, connect, initialize
from .accounts import Accounts, SessionExpired
from .paths import ROOT, database_workspace, default_database, default_templates, itd_root, previous_itd_roots
from .workspace import DOC_ROLES, ROLES, rows, save_entry, save_workspace, snapshot

ASSETS = Path(__file__).parent / 'web_assets'
DB_LOG = logging.getLogger('itd.db')
AI_LOG = logging.getLogger('itd.ai')
VIEWER_EXPORTS = {'/api/download', '/api/original', '/api/package', '/api/configuration'}
MAX_BODY = 48 * 1024 * 1024


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
            if (version or 0) < latest:
                folder = path.parent / 'backups'
                folder.mkdir(exist_ok=True)
                backup = folder / f'before-web-{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}.db'
                with closing(sqlite3.connect(backup)) as target:
                    source.backup(target)
    initialize(path)
    return backup


def bootstrap(c):
    from .resources import CATEGORIES
    active = c.execute('SELECT project_id FROM agent_state WHERE id=1').fetchone()
    return {'objects': rows(c, 'SELECT id,name,display_name FROM objects ORDER BY id'),
            'projects': rows(c, 'SELECT id,object_id,name,code FROM projects ORDER BY id'),
            'active_project_id': active[0] if active else None,
            'roles': ROLES, 'document_roles': DOC_ROLES,'categories':CATEGORIES}


def project_data(c, project_id):
    from .participants import participants_context
    from .workflow import workflow_context, report
    project = c.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
    if project is None:
        raise ValueError('Раздел не найден')
    from .registry import registry_rows
    result = {'project': dict(project), 'registry': registry_rows(c, project_id, detailed=True)}
    for table in ('resources', 'schemes', 'acts', 'workspace_entries', 'releases'):
        result[table] = rows(c, f'SELECT * FROM {table} WHERE project_id=? ORDER BY id', (project_id,))
    result['attachments'] = rows(c, '''SELECT a.* FROM attachments a WHERE a.id IN (
        SELECT attachment_id FROM project_attachments WHERE project_id=?
        UNION SELECT ra.attachment_id FROM resource_attachments ra JOIN resources r ON r.id=ra.resource_id WHERE r.project_id=?
        UNION SELECT aa.attachment_id FROM act_attachments aa JOIN acts a ON a.id=aa.act_id WHERE a.project_id=?
        UNION SELECT sa.attachment_id FROM scheme_attachments sa JOIN schemes s ON s.id=sa.scheme_id WHERE s.project_id=?
        UNION SELECT attachment_id FROM object_attachments WHERE object_id=?
        ) ORDER BY a.id''', (project_id, project_id, project_id, project_id, project['object_id']))
    result['forms'] = rows(c, 'SELECT * FROM document_types ORDER BY name')
    from .file_manager import source_files
    result['source_files']=source_files(c,project_id)
    result['project_attachment_ids'] = [r[0] for r in c.execute('SELECT attachment_id FROM project_attachments WHERE project_id=?', (project_id,))]
    for form in result['forms']:
        form['fields'] = json.loads(form['fields'])
    result['participants'] = participants_context(c, project_id)
    result['form_roots'] = {'project': dict(project),
        'object': dict(c.execute('SELECT * FROM objects WHERE id=?', (project['object_id'],)).fetchone()),
        **result['participants']}
    from .field_ui import describe_fields
    from .form_defaults import apply_form_defaults, documentation_context,field_bindings,document_project
    result['form_roots']['project'] = document_project(dict(project), result['form_roots']['object'])
    result['form_roots']['project_documentation'] = documentation_context(c, dict(project), result['participants']['organizations'])
    result['form_bindings']=field_bindings()
    from .form_defaults import date_groups
    result['date_groups'] = date_groups()
    from .document_versions import candidates
    from .act_participants import organization_candidates
    result['participant_choices']={'people':candidates(c,project_id),'organizations':organization_candidates(c,project_id)}
    for form in result['forms']:
        form['fields']=apply_form_defaults(form['code'],form['fields'])
        form['ui_fields'] = describe_fields(apply_form_defaults(form['code'], form['fields']))
    result['workflow'] = workflow_context(c, project_id)
    result['check'] = report(c, project_id)
    result['quality_reviews'] = rows(c, 'SELECT q.* FROM quality_reviews q JOIN resources r ON r.id=q.resource_id WHERE r.project_id=? ORDER BY q.id', (project_id,))
    result['delivery_events'] = rows(c, 'SELECT e.* FROM delivery_events e JOIN deliveries d ON d.id=e.delivery_id WHERE d.project_id=? ORDER BY e.id', (project_id,))
    result['pending'] = rows(c, "SELECT * FROM specification_pending WHERE project_id=? AND status='pending' ORDER BY id", (project_id,))
    result['act_facts'] = rows(c, 'SELECT af.* FROM act_facts af JOIN acts a ON a.id=af.act_id WHERE a.project_id=? ORDER BY af.act_id,af.fact_id', (project_id,))
    result['resource_attachments'] = rows(c, 'SELECT ra.* FROM resource_attachments ra JOIN resources r ON r.id=ra.resource_id WHERE r.project_id=? ORDER BY ra.resource_id,ra.attachment_id', (project_id,))
    from .manual import context
    result['manual']=context(c,project_id)
    from .journals import journal_data
    result['journals'] = journal_data(c, project_id)
    from .ojr import participant_ids
    result['form_roots']['participant_ids'] = participant_ids(result['journals']['directory'])
    from .inventory import balances,work_materials
    result['inventory']=balances(c,project_id)
    result['work_materials']=work_materials(c,project_id)
    result['act_originals']=rows(c,'SELECT DISTINCT f.* FROM act_attachments x JOIN attachments f ON f.id=x.attachment_id JOIN acts a ON a.id=x.act_id WHERE a.project_id=? AND a.is_active=1',(project_id,))
    result['act_signatories']=rows(c,'SELECT s.* FROM act_signatories s JOIN acts a ON a.id=s.act_id WHERE a.project_id=?',(project_id,))
    result['act_statuses']=rows(c,'SELECT s.* FROM act_execution_status s JOIN acts a ON a.id=s.act_id WHERE a.project_id=?',(project_id,))
    people={p['id']:p for p in result['journals']['directory']['people']}
    for entry in result['workspace_entries']:
        person=people.get(entry.get('responsible_id'))
        if person: entry['responsible_display']=person['position']+' · '+person['fio']

    from .form_catalog import catalog, available_forms
    result['catalog']=catalog()
    result['available_forms']=available_forms(c,project_id)
    result['act_resources']=rows(c,'SELECT ar.* FROM act_resources ar JOIN acts a ON a.id=ar.act_id WHERE a.project_id=? ORDER BY ar.ordinal',(project_id,))
    result['act_schemes']=rows(c,'SELECT s.* FROM act_schemes s JOIN acts a ON a.id=s.act_id WHERE a.project_id=? ORDER BY s.ordinal',(project_id,))
    from .ojr import act_work_description
    for act in result['acts']:
        act['work_description']=act_work_description(c,act['id'])
        act['fields_json']=act['fields']
        act['fields']=json.loads(act['fields'])
    return result


class WorkspaceServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, database):
        self.database = Path(database).resolve()
        self.plan_secret = secrets.token_urlsafe(32)
        self.accounts = Accounts(self.database.with_name(self.database.name + '.accounts.sqlite3'))
        self.lock = RLock()
        self.state_lock = RLock()
        self.workspace_id = secrets.token_urlsafe(24)
        self.itd_root = None
        super().__init__(address, Handler)

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
        backup = prepare_database(self.database)
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
               (ROOT / 'app', ROOT / 'skills', ROOT / 'db', ROOT / 'logs', ROOT / '.git',
                database.parent / 'archive', database.parent / 'work', database.parent / 'backups')):
            raise ValueError('Выберите отдельную папку ИТД вне служебных каталогов')
        if database.is_relative_to(folder):
            raise ValueError('БД должна находиться за пределами папки ИТД')
        check_path(folder)
        if self.settings() == {'database_path': str(database), 'itd_root': str(folder)}:
            return {'settings': self.settings()}
        self.accounts.check_root(database, folder)
        with connect(self.database) as c:
            if c.execute("SELECT 1 FROM file_operations WHERE state='pending'").fetchone():
                raise ValueError('Сначала завершите восстановление операции с исходными файлами')
            if c.execute("SELECT 1 FROM release_operations WHERE state='prepared'").fetchone():
                raise ValueError('Сначала завершите восстановление выпуска документа')
        prepare_database(database)
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
        return f'http://127.0.0.1:{self.server_port}'


class Handler(BaseHTTPRequestHandler):
    timeout = 30

    def log_message(self, fmt, *args):
        # URL и токен сессии не попадают в журнал HTTP.
        pass

    def send_bytes(self, body, mime='application/json; charset=utf-8', status=200, filename=None):
        if getattr(self, '_defer_response', False):
            self._response = (body, mime, status, filename)
            return
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if filename:
            from urllib.parse import quote
            self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(filename))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, value, status=200):
        self.send_bytes(json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), status=status)

    def check_origin(self):
        if self.headers.get('Host') != urlsplit(self.server.origin).netloc:
            raise PermissionError('Недопустимый адрес сервера')
        origin = self.headers.get('Origin')
        if origin and origin != self.server.origin:
            raise PermissionError('Запрос с другого сайта отклонён')
    def authenticate(self):
        self.check_origin()
        url = urlsplit(self.path)
        touch = url.path != '/api/status' and 'poll' not in parse_qs(url.query)
        return {**self.server.accounts.authenticate(self.headers.get('X-ITD-Token', ''), touch=touch),
                'workspace_id': self.server.workspace_id}

    def do_GET(self):
        # Release the read transaction before a slow client receives the response.
        self._defer_response = True
        self._response = None
        try:
            with self.server.workspace_scope(write=False) as database:
                self.database = database
                self.get_route()
        except Exception:
            DB_LOG.error('Необработанная ошибка чтения ИТД')
            self.send_json({'error': 'Не удалось прочитать сведения. Повторите загрузку.'}, 500)
        finally:
            self._defer_response = False
        if self._response:
            self.send_bytes(*self._response)

    def get_route(self):
        try:
            url = urlsplit(self.path)
            if url.path in ('/', '/design.js', '/design.css', '/design-LICENSE.txt', '/logo.svg', '/favicon.svg', '/deletion.js', '/tables.js', '/account.js', '/configuration.js', '/document-versions.js', '/act-fields.js', '/journals.js', '/resources.js', '/ojr-ui.js', '/dialogs.js', '/app.js', '/knowledge.js', '/knowledge-markdown.js', '/manual.js', '/ui.js', '/style.css', '/open-sans-regular.ttf', '/open-sans-semibold.ttf', '/open-sans-bold.ttf', '/open-sans-LICENSE.txt'):
                if self.headers.get('Host') != urlsplit(self.server.origin).netloc:
                    raise PermissionError('Недопустимый адрес сервера')
                path = ASSETS / ('index.html' if url.path == '/' else url.path[1:])
                self.send_bytes(path.read_bytes(), mimetypes.guess_type(path)[0] + '; charset=utf-8')
                return
            user = self.authenticate()
            if url.path == '/api/account':
                self.send_json(user)
                return
            if url.path == '/api/admin':
                if user['role'] != 'admin':
                    raise PermissionError('Требуется роль администратора')
                self.send_json({'settings': self.server.settings(), 'users': self.server.accounts.list()})
                return
            if user['role'] == 'viewer' and url.path in VIEWER_EXPORTS:
                raise PermissionError('Наблюдателю доступен просмотр сведений')
            query = parse_qs(url.query, keep_blank_values=True)
            if url.path == '/api/knowledge':
                from .knowledge import default_root, default_index, search, show, status
                root, index = default_root(), default_index(self.database)
                if 'id' in query:
                    result = show(root, index, query['id'][0])
                elif 'query' in query:
                    result = search(root, index, query['query'][0],
                                    corpus=query.get('corpus', [None])[0],
                                    kind=query.get('kind', [None])[0], limit=20)
                else:
                    result = status(root, index)
                AI_LOG.info('Локальная база знаний, пользователь %s', user['id'])
                self.send_json(result)
                return
            with connect(self.database) as c:
                c.execute('PRAGMA query_only = ON')
                if url.path == '/api/status':
                    c.execute('SELECT id FROM objects LIMIT 1').fetchone()
                    result={'database':'ready','agent':{'mode':'external_chat','activity':'unknown'}}
                elif url.path == '/api/bootstrap':
                    result = bootstrap(c)
                elif url.path == '/api/configuration':
                    from .configuration import export_configuration
                    result=export_configuration(c,int(query['object_id'][0]),query['scope'][0])
                elif url.path == '/api/workspace':
                    result = snapshot(c, int(query['object_id'][0])) if 'object_id' in query else snapshot(c)
                elif url.path == '/api/project':
                    revision = self.server.revision(self.database)
                    pid = int(query['project_id'][0])
                    if not c.execute('SELECT 1 FROM projects WHERE id=?', (pid,)).fetchone():
                        raise ValueError('Раздел не найден')
                    if query.get('revision', [None])[0] == revision:
                        result = {'unchanged': True, '_revision': revision}
                    else:
                        result = project_data(c, int(query['project_id'][0]))
                        result['_revision'] = revision
                elif url.path == '/api/download':
                    self.download(c, int(query['project_id'][0]), int(query['release_id'][0]))
                    return
                elif url.path == '/api/context':
                    from .acts import build_context, find_template, template_claims
                    aid=int(query['act_id'][0]);pid=int(query['project_id'][0])
                    from .workflow import same_project
                    same_project(c,'acts',aid,pid)
                    result=build_context(c,aid,draft=True)
                    from .document_preview import preview_fields
                    result['form_name'],result['preview_fields']=preview_fields(c,aid)
                    from .manual import source_issues
                    result['source_issues']=source_issues(c,aid)
                    try:
                        template=find_template(default_templates(),result['act_type'])
                        result['static_claims']=template_claims(template)
                        from .archive import digest
                        from .acts import context_digest
                        review=c.execute('SELECT * FROM final_reviews WHERE act_id=?',(aid,)).fetchone()
                        result['review_current']=bool(review and review['template_sha256']==digest(template)
                            and review['context_sha256']==context_digest(result['context']))
                    except ValueError as error: result['template_error']=str(error)
                elif url.path == '/api/original':
                    from .archive import archived_path,digest
                    pid=int(query['project_id'][0]);aid=int(query['attachment_id'][0])
                    originals=project_data(c,pid)['attachments']
                    item=next((a for a in originals if a['id']==aid),None)
                    if item is None: raise ValueError('Оригинал не связан с разделом')
                    path=archived_path(self.database.parent/'archive',item['storage_path'])
                    if not path.is_file() or digest(path)!=item['sha256']: raise ValueError('Целостность оригинала не подтверждена')
                    self.send_bytes(path.read_bytes(),'application/octet-stream',filename=item['original_name']);return
                elif url.path == '/api/package':
                    from .releases import export_package
                    pid=int(query['project_id'][0])
                    with tempfile.TemporaryDirectory(prefix='itd-package-') as folder:
                        target=Path(folder)/'ИТД.zip'
                        export_package(c,pid,target,include_originals=True)
                        self.send_bytes(target.read_bytes(),'application/zip',filename='ИТД.zip');return
                else:
                    self.send_json({'error': 'Страница не найдена'}, 404)
                    return
            self.send_json(result)
        except PermissionError as error:
            self.send_json({'error': str(error), 'session_expired': isinstance(error, SessionExpired)}, 403)
        except (ValueError, KeyError, sqlite3.Error, OSError) as error:
            self.send_json({'error': str(error), **({'fields':error.fields} if hasattr(error,'fields') else {})}, 400)

    def do_POST(self):
        try:
            self.check_origin()
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Требуется application/json')
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_BODY:
                raise ValueError('Допустимый размер запроса — до 48 МБ')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('Требуется объект JSON')
            route=urlsplit(self.path).path
            with self.server.workspace_scope():
                result = self.post_route(route, data)
            self.send_json(result)
        except PermissionError as error:
            self.send_json({'error': str(error), 'session_expired': isinstance(error, SessionExpired)}, 403)
        except (ValueError, KeyError, TypeError, sqlite3.Error, binascii.Error, OSError) as error:
            details = {key: getattr(error, key) for key in ('fields', 'journal_dates') if hasattr(error, key)}
            self.send_json({'error': str(error), **details}, 400)
        except Exception:
            DB_LOG.error('Необработанная ошибка операции ИТД')
            self.send_json({'error': 'Операция не завершена. Проверьте данные и доступность файлов.'}, 500)

    def post_route(self, route, data):
        accounts = self.server.accounts
        token = self.headers.get('X-ITD-Token', '')
        if route == '/api/login':
            result = accounts.login(data.get('code'))
            result['user']['workspace_id'] = self.server.workspace_id
            accounts.discard_session(token)
            return result
        user = self.authenticate()
        user_id = user['id']
        if route == '/api/logout':
            accounts.discard_session(token)
            return {'ok': True}
        if route == '/api/account/profile':
            return accounts.save_profile(user_id, data)
        if route == '/api/account/rotate':
            return accounts.rotate(user_id, user_id)
        if route.startswith('/api/admin/'):
            if user['role'] != 'admin':
                raise PermissionError('Требуется роль администратора')
            operation = route.rsplit('/', 1)[-1]
            if operation == 'settings':
                return self.server.configure(data, user_id)
            if operation == 'create':
                return accounts.create(data)
            return accounts.manage(operation, user_id, data)
        context_only = route == '/api/action' and data.get('action') == 'context'
        if user['role'] == 'viewer' and not context_only:
            raise PermissionError('Наблюдателю доступен просмотр сведений')
        if route in ('/api/files/plan', '/api/files/apply'):
            from .file_manager import make_plan, apply_plan
            if route.endswith('/plan'):
                result = make_plan(self.server.database, data.get('project_id'), data.get('purpose', 'check'),
                                   data.get('attachment_id'), self.server.plan_secret)
            else:
                result = apply_plan(self.server.database, data.get('plan'), data.get('token'),
                                    data.get('types', {}), self.server.plan_secret)
        else:
            with connect(self.server.database) as c:
                if context_only:
                    c.execute('PRAGMA query_only = ON')
                result = self.mutate(c, route, data)
        if not context_only:
            DB_LOG.info('Операция БД %s, пользователь %s', route, user_id)
        return result

    def mutate(self, c, route, data):
        if route == '/api/configuration/preview':
            from .configuration import prepare_import
            return prepare_import(c,data.get('object_id'),data.get('scope'),data.get('document'))
        if route == '/api/save':
            return save_workspace(c, data)
        pid = data.get('project_id')
        if not c.execute('SELECT 1 FROM projects WHERE id=?', (pid,)).fetchone():
            raise ValueError('Сначала сохраните и выберите раздел РД')
        if route.startswith('/api/versions/'):
            from . import document_versions as versions
            aid=data.get('act_id')
            if route=='/api/versions/list':
                from .act_participants import organization_candidates
                from .acts import find_template
                from .field_ui import table_headers
                from .form_defaults import FIELD_CONTINUATIONS
                from .workflow import same_project
                act = same_project(c, 'acts', aid, pid)
                try:
                    template = find_template(default_templates(), act['act_type'])
                except ValueError:
                    headers = {}
                else:
                    headers = table_headers(template)
                return {'versions':versions.ensure(c,pid,aid),'candidates':versions.candidates(c,pid),
                        'required_roles':versions.required_roles(c,aid),'organization_candidates':organization_candidates(c,pid),
                        'table_headers':headers, 'field_continuations':FIELD_CONTINUATIONS.get(act['act_type'], {})}
            if route=='/api/versions/create': return {'versions':versions.create(c,pid,aid,data.get('expected'))}
            if route=='/api/versions/save': return {'versions':versions.save(c,pid,data)}
            raise ValueError('Неизвестное действие с версиями')
        if route.startswith('/api/resource-import/'):
            from . import resource_import
            operation=route.rsplit('/',1)[-1]
            if operation=='stage': return resource_import.stage(c,pid,data)
            if operation=='preview': return resource_import.inspect(c,pid,data)
            if operation=='commit': return resource_import.commit(c,pid,data,self.server.database.parent/'archive')
            raise ValueError('Неизвестная операция импорта')
        if route == '/api/ojr-title':
            from .ojr import save_title
            return save_title(c,pid,data)
        if route == '/api/activate':
            c.execute('INSERT INTO agent_state VALUES(1,?) ON CONFLICT(id) DO UPDATE SET project_id=excluded.project_id', (pid,))
            return {'project_id': pid}
        if route == '/api/upload':
            from .archive import import_file, link_file
            name = data.get('name', '')
            if not name or '/' in name or '\\' in name or name in ('.', '..'):
                raise ValueError('Недопустимое имя файла')
            doc_type = data.get('doc_type', 'rd')
            with tempfile.TemporaryDirectory(prefix='itd-upload-') as folder:
                source = Path(folder) / name
                source.write_bytes(base64.b64decode(data['content'], validate=True))
                result = import_file(c, archive_root=self.server.database.parent / 'archive', source=source,
                                     doc_type=doc_type, title=data.get('title') or name)
                # Хеш-дубликат с другим типом не должен становиться иной категорией оригинала.
                stored = c.execute('SELECT * FROM attachments WHERE id=?', (result['id'],)).fetchone()
                from .archive import file_type
                expected_type='quality' if doc_type in ('certificate','passport') else doc_type
                if file_type(stored) != expected_type:
                    raise ValueError('Этот оригинал уже зарегистрирован с другим типом; уточните его назначение')
                link_file(c, attachment_id=result['id'], entity='project', entity_id=pid)
                from .archive import publish_project_file
                result['project_path'] = publish_project_file(c,attachment_id=result['id'],project_id=pid,archive_root=self.server.database.parent/'archive')
                result['sha256'] = stored['sha256']
                return result
        if route == '/api/incoming-day':
            from .incoming import save_incoming_day
            return save_incoming_day(c, pid, data['day'], self.server.database.parent / 'archive')
        if route == '/api/entry':
            return save_entry(c, pid, data['entry'])
        if route == '/api/action':
            from .manual import execute
            return execute(c,pid,data['action'],data.get('data',{}))
        if route == '/api/review':
            from .acts import review_act
            from .workflow import same_project
            same_project(c,'acts',data['act_id'],pid)
            if data.get('confirmed') is not True: raise ValueError('Нужно явное подтверждение деловых утверждений')
            return review_act(c,data['act_id'],default_templates(),data['note'])
        if route == '/api/fact':
            from .workflow import add_fact
            return add_fact(c, pid, data['fact'])
        if route == '/api/work-fact':
            from .workflow import add_fact_from_work
            return add_fact_from_work(c, pid, data['fact'])
        if route == '/api/fact-status':
            from .workflow import same_project, set_fact_status
            same_project(c, 'work_facts', data['fact_id'], pid)
            return set_fact_status(c, data['fact_id'], data['changes'], data['expected'])
        if route == '/api/quality':
            from .workflow import add_quality_review, same_project
            from .archive import link_file
            review = data['review']
            same_project(c, 'resources', review['resource_id'], pid)
            if not c.execute('''SELECT 1 FROM project_attachments WHERE project_id=? AND attachment_id=?
                UNION SELECT 1 FROM resource_attachments WHERE resource_id=? AND attachment_id=?''',
                (pid, review['attachment_id'], review['resource_id'], review['attachment_id'])).fetchone():
                raise ValueError('Документ качества не связан с разделом')
            # Явный выбор пары ресурс/документ и результат сверки — одна транзакция.
            link_file(c, attachment_id=review['attachment_id'], entity='resource', entity_id=review['resource_id'])
            return add_quality_review(c, pid, review)
        if route == '/api/act':
            from .acts import add_act, set_resources, set_schemes
            entry_ids = data.get('entry_ids', [])
            for eid in entry_ids:
                if not c.execute("SELECT 1 FROM workspace_entries WHERE id=? AND project_id=? AND kind='work' AND act_id IS NULL", (eid, pid)).fetchone():
                    raise ValueError('Работа уже связана с актом либо относится к другому разделу')
            from .fields import formatted
            for field in data.get('fields', []):
                if field.get('kind') == 'literal' and field.get('value') not in (None, ''):
                    formatted(field['value'], field)
            for removal in data.get('resource_removals', []):
                eid = removal['id']
                if eid not in entry_ids:
                    raise ValueError('Материалы можно убрать только из выбранной записи ОЖР')
                entry = dict(c.execute('SELECT * FROM workspace_entries WHERE id=?', (eid,)).fetchone())
                removed = set(removal['resource_ids'])
                if removed.intersection(data.get('resource_ids', [])):
                    raise ValueError('Материал одновременно выбран и снят')
                entry['revision'] = removal['revision']
                entry['materials'] = [dict(row) for row in c.execute(
                    'SELECT resource_id, quantity FROM work_materials WHERE entry_id=?', (eid,))
                    if row['resource_id'] not in removed]
                if entry['resource_id'] in removed:
                    entry.update(resource_id=None, quantity=None, unit=None)
                save_entry(c, pid, entry, sync_dates=False)
            from .form_catalog import ensure_act_form
            ensure_act_form(c, pid, data['act_type'])
            fields=data.get('fields', [])
            form_fields=json.loads(c.execute('SELECT fields FROM document_types WHERE code=?',(data['act_type'],)).fetchone()[0])
            description=next((f for f in form_fields if f['key']=='work_description'),None)
            if entry_ids and description and not any(f['key']=='work_description' and f.get('value') not in (None,'') for f in fields):
                fields=[f for f in fields if f['key']!='work_description']+[{'key':'work_description','kind':'reference','source':'work_summary.description','required':description.get('required',False)}]
            act_id = add_act(c, project_id=pid, act_type=data['act_type'], date_signed=data.get('date_signed') or None, fields=fields)
            set_resources(c, act_id, data.get('resource_ids', []))
            set_schemes(c, act_id, data.get('scheme_ids', []))
            from .workflow import link_facts
            link_facts(c, act_id, data.get('fact_ids', []))
            resources = set(data.get('resource_ids', []))
            from .manual import bind_entries
            from .fields import merge_fields, uses_resource_sources
            from .form_defaults import apply_form_defaults
            effective = apply_form_defaults(data['act_type'], merge_fields(form_fields, fields))
            work_only = data.get('work_only') is True and not uses_resource_sources(effective)
            bind_entries(c,act_id,entry_ids,work_only=work_only)
            # Списание уже произошло в работе. Акт получает те же факты.
            facts=set(data.get('fact_ids',[]))
            for eid in ([] if work_only else entry_ids):
                facts.update(r[0] for r in c.execute('SELECT fact_id FROM work_materials WHERE entry_id=?',(eid,)))
            link_facts(c,act_id,list(facts))
            if 'organizations' in data:
                from .act_participants import set_organizations
                set_organizations(c,pid,act_id,data['organizations'])
            if 'signatories' in data:
                from .ojr import set_act_people
                set_act_people(c,pid,act_id,data['signatories'])
            if data.get('attachment_id'):
                from .archive import link_file
                from .document_versions import ensure
                attachment_id=data['attachment_id']
                if not c.execute('SELECT 1 FROM project_attachments WHERE project_id=? AND attachment_id=?',(pid,attachment_id)).fetchone(): raise ValueError('Документ не принадлежит разделу')
                link_file(c,attachment_id=attachment_id,entity='act',entity_id=act_id)
                version=ensure(c,pid,act_id)[-1]
                c.execute('UPDATE document_versions SET attachment_id=? WHERE id=?',(attachment_id,version['id']))
            return {'act_id': act_id}
        if route == '/api/generate':
            act = c.execute('SELECT id FROM acts WHERE id=? AND project_id=?', (data.get('act_id'), pid)).fetchone()
            if not act:
                raise ValueError('Акт не принадлежит разделу')
            from .managed import generate_managed
            # Веб-интерфейс выпускает черновик; финал проходит штатную содержательную проверку.
            return generate_managed(c, act_id=act[0], templates_dir=default_templates(), draft=not data.get('final',False))
        if route == '/api/registry/export':
            from .acts import add_act
            from .form_catalog import connect_form
            from .managed import generate_managed
            code = 'РЕЕСТР_ИТД'
            if not c.execute('SELECT 1 FROM document_types WHERE code=?', (code,)).fetchone():
                connect_form(c, code)
            registry = c.execute(
                'SELECT id FROM acts WHERE project_id=? AND act_type=? AND is_active=1 ORDER BY id DESC LIMIT 1',
                (pid, code)).fetchone()
            act_id = registry[0] if registry else add_act(c, project_id=pid, act_type=code)
            return generate_managed(c, act_id=act_id, templates_dir=default_templates(), draft=True)
        if route == '/api/statement':
            from .managed import statement_managed
            return statement_managed(c, project_id=pid)
        raise ValueError('Неизвестная операция')

    def download(self, c, project_id, release_id):
        from .archive import digest
        from .releases import workspace
        release = c.execute("SELECT * FROM releases WHERE id=? AND project_id=?", (release_id, project_id)).fetchone()
        if release is None:
            raise ValueError('Опубликованный выпуск не найден')
        # Только выбранный зарегистрированный файл; пути из HTTP не используются.
        path = Path(release['path'])
        if not path.is_absolute():
            path = workspace(c) / path
        if not path.is_file() or digest(path) != release['sha256']:
            raise ValueError('Проверка целостности выпуска не пройдена')
        self.send_bytes(path.read_bytes(), 'application/octet-stream', filename=path.name)


def create_server(database, port=None):
    """По умолчанию допускаем свободный порт; явный выбор не подменяем."""
    requested_port = 8765 if port is None else port
    if not 0 <= requested_port <= 65535:
        raise ValueError('Порт должен быть от 0 до 65535; 0 — выбрать свободный порт')
    try:
        return WorkspaceServer(('127.0.0.1', requested_port), database)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        if port is not None:
            raise ValueError(
                f'Порт {requested_port} уже занят. Если форма этой папки уже работает, '
                'откройте её прежнюю ссылку. Для другого сервера укажите '
                '--port 0 (свободный порт) или другой --port.'
            ) from error
        print('Порт 8765 уже занят; выбираем свободный локальный порт. '
              'Если форма этой папки уже работает, используйте её прежнюю ссылку.', flush=True)
        return WorkspaceServer(('127.0.0.1', 0), database)


def serve(database, port=None, open_browser=True):
    # Сначала занимаем порт: не создаём и не обновляем БД при конфликте.
    server = create_server(database, port)
    try:
        from .logging_setup import configure
        configure(ROOT / 'logs')
        backup, code = server.prepare()
        url = server.origin + '/' + ('#' + code if code else '')
        print(f'Локальная форма ИТД: {url}', flush=True)
        if backup:
            print(f'Резервная копия перед обновлением: {backup}', flush=True)
        print('Остановить сервер: Ctrl+C. Данные сохраняются кнопкой в форме.', flush=True)
        if open_browser:
            webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description='Локальная форма ИТД')
    parser.add_argument('--db', type=Path, default=default_database())
    parser.add_argument('--port', type=int, default=None, help='Порт (по умолчанию 8765 или свободный); 0 — свободный')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    try:
        serve(args.db, args.port, not args.no_browser)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f'Ошибка: {error}\n')


if __name__ == '__main__':
    main()
