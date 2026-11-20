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
from ipaddress import IPv4Address
import logging
import mimetypes
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
from threading import RLock
from urllib.parse import parse_qs, urlsplit
import webbrowser

from .db import MIGRATIONS, connect, initialize
from .accounts import Accounts, SessionExpired
from .http_origin import public_origin, request_origin
from .paths import ROOT, database_workspace, default_database, default_templates, itd_root, previous_itd_roots
from .services.projections import bootstrap, project_data
from .services.context import Actor, ServiceContext
from .services.permissions import require

from .server_state import WorkspaceState, prepare_database

ASSETS = Path(__file__).parent / 'web_assets'
DB_LOG = logging.getLogger('itd.db')
AI_LOG = logging.getLogger('itd.ai')
VIEWER_EXPORTS = {'/api/download', '/api/original', '/api/package', '/api/configuration'}
MAX_BODY = 48 * 1024 * 1024









class WorkspaceServer(WorkspaceState, ThreadingHTTPServer):
    """Compatibility listener; production serve() hands its bound socket to ASGI."""
    daemon_threads = True

    def __init__(self, address, database):
        WorkspaceState.__init__(self, database)
        ThreadingHTTPServer.__init__(self, address, Handler)



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

    def check_host(self):
        # Адрес интерфейса, принявшего соединение, известен ОС, а не клиенту.
        # Это поддерживает все интерфейсы без доверия произвольному Host/DNS.
        address, port = self.connection.getsockname()[:2]
        host = f'{address}:{port}'
        return request_origin(self.headers.get_all('Host'), host, 'http',
                              getattr(self.server, 'public_origin', None))

    def check_origin(self):
        expected_origin = self.check_host()
        origin = self.headers.get('Origin')
        if origin and origin != expected_origin:
            raise PermissionError('Запрос с другого сайта отклонён')
    def authenticate(self):
        self.check_origin()
        url = urlsplit(self.path)
        touch = url.path != '/api/status' and 'poll' not in parse_qs(url.query)
        authorization = self.headers.get_all('Authorization')
        method = self.server.accounts.authenticate
        token = self.headers.get('X-ITD-Token', '')
        if authorization:
            parts = authorization[0].split()
            if len(authorization) != 1 or len(parts) != 2 or parts[0].lower() != 'bearer':
                raise SessionExpired('Токен недействителен или отозван')
            token = parts[1]
            method = self.server.accounts.authenticate_token
        return {**method(token, touch=touch),
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

    def service_context(self):
        return ServiceContext(database=getattr(self, 'database', self.server.database),
                              root=itd_root.get(), previous_roots=tuple(previous_itd_roots.get()),
                              templates=default_templates(), settings={'plan_secret': self.server.plan_secret})

    @staticmethod
    def service_actor(user):
        return Actor(user_id=user['id'], role=user['role'], source='web')

    def get_route(self):
        try:
            url = urlsplit(self.path)
            if url.path in ('/', '/design.js', '/design.css', '/design-LICENSE.txt', '/logo.svg', '/favicon.svg', '/deletion.js', '/tables.js', '/account.js', '/configuration.js', '/document-versions.js', '/field-functions.js', '/act-fields.js', '/journals.js', '/resources.js', '/ojr-ui.js', '/dialogs.js', '/app.js', '/knowledge.js', '/knowledge-markdown.js', '/manual.js', '/ui.js', '/style.css', '/open-sans-regular.ttf', '/open-sans-semibold.ttf', '/open-sans-bold.ttf', '/open-sans-LICENSE.txt'):
                self.check_host()
                path = ASSETS / ('index.html' if url.path == '/' else url.path[1:])
                self.send_bytes(path.read_bytes(), mimetypes.guess_type(path)[0] + '; charset=utf-8')
                return
            user = self.authenticate()
            if url.path in ('/api/account/tokens', '/api/admin/tokens'):
                from .services.accounts import execute
                self.send_json(execute(self.server.accounts, self.service_actor(user),
                                       'token-list-all' if url.path == '/api/admin/tokens' else 'token-list', {}))
                return
            if url.path == '/api/account':
                self.send_json(user)
                return
            if url.path == '/api/admin':
                from .services.accounts import execute
                users = execute(self.server.accounts, self.service_actor(user), 'list', {})
                self.send_json({'settings': self.server.settings(), 'users': users})
                return
            from .services.permissions import WEB_READS
            if url.path not in WEB_READS:
                self.send_json({'error': 'Страница не найдена'}, 404)
                return
            from .services.queries import query_web, FileResult
            query = parse_qs(url.query, keep_blank_values=True)
            result = query_web(self.service_context(), self.service_actor(user), url.path, query,
                               revision=self.server.revision(self.database) if url.path == '/api/project' else None)
            if url.path == '/api/knowledge':
                AI_LOG.info('Локальная база знаний, пользователь %s', user['id'])
            if isinstance(result, FileResult):
                self.send_bytes(result.content, result.mime, filename=result.filename)
            else:
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
        if route in ('/api/account/tokens/create', '/api/account/tokens/revoke', '/api/admin/tokens/revoke'):
            from .services.accounts import execute
            operation = ('token-create' if route.endswith('/create') else
                         'token-revoke-any' if route.startswith('/api/admin/') else 'token-revoke')
            return execute(accounts, self.service_actor(user), operation, data)
        if route == '/api/logout':
            accounts.discard_session(token)
            return {'ok': True}
        if route == '/api/account/profile':
            from .services.accounts import execute
            return execute(accounts, self.service_actor(user), 'profile', data)
        if route == '/api/account/rotate':
            from .services.accounts import execute
            return execute(accounts, self.service_actor(user), 'rotate-self', data)
        if route.startswith('/api/admin/'):
            require(self.service_actor(user), 'admin')
            operation = route.rsplit('/', 1)[-1]
            if operation == 'settings':
                return self.server.configure(data, user_id)
            if operation == 'create':
                from .services.accounts import execute
                return execute(accounts, self.service_actor(user), 'create', data)
            if operation not in ('role', 'delete', 'rotate'):
                raise ValueError('Неизвестная операция с пользователями')
            from .services.accounts import execute
            return execute(accounts, self.service_actor(user), 'rotate-user' if operation == 'rotate' else operation, data)
        from .services.operations import execute_web
        return execute_web(self.service_context(), self.service_actor(user), route, data)

    def mutate(self, c, route, data):
        # Compatibility for trusted in-process callers; requests use execute_web.
        from .services.operations import legacy_mutate
        server = getattr(self, 'server', None)
        return legacy_mutate(c, route, data, getattr(server, 'database', None), default_templates())

    def download(self, c, project_id, release_id):
        from .services.queries import download
        result = download(c, project_id, release_id)
        self.send_bytes(result.content, result.mime, filename=result.filename)


def create_server(database, port=None, host='127.0.0.1'):
    """По умолчанию допускаем свободный порт; явный выбор не подменяем."""
    requested_port = 8765 if port is None else port
    try:
        host = str(IPv4Address(host))
    except ValueError as error:
        raise ValueError('Укажите IPv4-адрес для --host; 0.0.0.0 — все сетевые интерфейсы') from error
    if not 0 <= requested_port <= 65535:
        raise ValueError('Порт должен быть от 0 до 65535; 0 — выбрать свободный порт')
    try:
        return WorkspaceServer((host, requested_port), database)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        if port is not None:
            raise ValueError(
                f'Порт {requested_port} уже занят. Если форма этой папки уже работает, '
                'откройте её прежнюю ссылку. Для другого сервера укажите '
                '--port 0 (свободный порт) или другой --port.'
            ) from error
        print('Порт 8765 уже занят; выбираем свободный порт. '
              'Если форма этой папки уже работает, используйте её прежнюю ссылку.', flush=True)
        return WorkspaceServer((host, 0), database)


def serve(database, port=None, open_browser=True, host='127.0.0.1', public_url=None):
    configured_origin = public_origin(public_url)
    # Сначала занимаем порт: не создаём и не обновляем БД при конфликте.
    server = create_server(database, port, host)
    server.public_origin = configured_origin
    try:
        from .logging_setup import configure
        configure(ROOT / 'logs')
        backup, code = server.prepare()
        url = (configured_origin or server.origin) + '/' + ('#' + code if code else '')
        print(f'Локальная форма ИТД: {url}', flush=True)
        if host == '0.0.0.0':
            print(f'Доступ по сети: http://<IPv4-адрес этого компьютера>:{server.server_port}/ '
                  '(вход по индивидуальному коду пользователя).', flush=True)
        if backup:
            print(f'Резервная копия перед обновлением: {backup}', flush=True)
        print('Остановить сервер: Ctrl+C. Данные сохраняются кнопкой в форме.', flush=True)
        if open_browser:
            webbrowser.open(url)
        import uvicorn
        from .http_api import create_app
        application = create_app(server)
        config = uvicorn.Config(application, access_log=False, log_level='warning',
                                host=server.server_address[0], port=server.server_port)
        uvicorn.Server(config).run(sockets=[server.socket])
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description='Локальная форма ИТД')
    parser.add_argument('--db', type=Path, default=default_database())
    parser.add_argument('--port', type=int, default=None, help='Порт (по умолчанию 8765 или свободный); 0 — свободный')
    network = parser.add_mutually_exclusive_group()
    network.add_argument('--host', default='127.0.0.1', help='IPv4-адрес сервера; 0.0.0.0 — доступ по сети')
    network.add_argument('--public', dest='host', action='store_const', const='0.0.0.0',
                         help='Разрешить подключения на всех сетевых интерфейсах')
    parser.add_argument('--public-origin', default=os.environ.get('ITD_PUBLIC_ORIGIN'),
                        help='Внешний http(s)://адрес[:порт] для Docker/прокси; также ITD_PUBLIC_ORIGIN')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    try:
        serve(args.db, args.port, not args.no_browser, host=args.host, public_url=args.public_origin)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f'Ошибка: {error}\n')


if __name__ == '__main__':
    main()
