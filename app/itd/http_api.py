"""FastAPI transport over the shared workspace and role-checked services."""
import asyncio
import binascii
import json
import logging
import mimetypes
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, quote

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from .accounts import SessionExpired
from .paths import default_templates, itd_root, previous_itd_roots
from .services.context import Actor, ServiceContext, WorkspaceActionInput
from .services.operations import execute_web
from .services.permissions import WEB_POSTS, WEB_READS, require
from .services.queries import FileResult, query_web
from .services.accounts import execute as account_operation

LOG = logging.getLogger('itd.db')
ASSETS = Path(__file__).parent / 'web_assets'
MAX_BODY = 48 * 1024 * 1024
ASSET_NAMES = {'index.html', 'design.js', 'design.css', 'design-LICENSE.txt', 'logo.svg',
               'favicon.svg', 'deletion.js', 'tables.js', 'account.js', 'configuration.js',
               'document-versions.js', 'field-functions.js', 'act-fields.js', 'journals.js',
               'resources.js', 'ojr-ui.js', 'dialogs.js', 'app.js', 'knowledge.js',
               'knowledge-markdown.js', 'manual.js', 'ui.js', 'style.css',
               'open-sans-regular.ttf', 'open-sans-semibold.ttf', 'open-sans-bold.ttf',
               'open-sans-LICENSE.txt'}
SECURITY_HEADERS = {
    'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
}


def check_site(request):
    address = request.scope.get('server')
    if not address:
        raise PermissionError('Недопустимый адрес сервера')
    host = f'{address[0]}:{address[1]}'
    if request.headers.getlist('host') != [host]:
        raise PermissionError('Недопустимый адрес сервера')
    origin = request.headers.get('origin')
    if origin and origin != request.url.scheme + '://' + host:
        raise PermissionError('Запрос с другого сайта отклонён')


def error_response(request, message, status, code, **details):
    error = {'code': code, 'message': message} if request.url.path.startswith('/api/v1/') else message
    return JSONResponse({'error': error, **details}, status_code=status, headers=SECURITY_HEADERS)


def failure(request, error):
    if isinstance(error, PermissionError):
        return error_response(request, str(error), 403,
                              'session_expired' if isinstance(error, SessionExpired) else 'forbidden',
                              session_expired=isinstance(error, SessionExpired))
    if isinstance(error, (ValueError, KeyError, TypeError, sqlite3.Error, OSError, binascii.Error)):
        details = {key: getattr(error, key) for key in ('fields', 'journal_dates') if hasattr(error, key)}
        return error_response(request, str(error), 400, 'invalid_input', **details)
    LOG.error('Необработанная ошибка HTTP API')
    return error_response(request, 'Операция не завершена. Проверьте данные и доступность файлов.', 500, 'internal_error')


def authenticate(state, token, *, touch=True):
    user = state.accounts.authenticate(token, touch=touch)
    return {**user, 'workspace_id': state.workspace_id}


def context(state, database):
    return ServiceContext(database=database, root=itd_root.get(),
                          previous_roots=tuple(previous_itd_roots.get()),
                          templates=getattr(state, 'templates', None) or default_templates(),
                          settings={'plan_secret': state.plan_secret})


def dispatch(state, route, query, data, token):
    write = data is not None
    with state.workspace_scope(write=write) as database:
        if route == '/api/login' and write:
            result = state.accounts.login(data.get('code'))
            result['user']['workspace_id'] = state.workspace_id
            state.accounts.discard_session(token)
            return result
        user = authenticate(state, token, touch=route != '/api/status' and 'poll' not in query)
        actor = Actor(user_id=user['id'], role=user['role'], source='web')
        ctx = context(state, database)
        if not write:
            if route == '/api/account':
                return user
            if route == '/api/admin':
                return {'settings': state.settings(), 'users': account_operation(state.accounts, actor, 'list', {})}
            return query_web(ctx, actor, route, query,
                             revision=state.revision(database) if route == '/api/project' else None)
        if route == '/api/logout':
            state.accounts.discard_session(token)
            return {'ok': True}
        if route == '/api/account/profile':
            return account_operation(state.accounts, actor, 'profile', data)
        if route == '/api/account/rotate':
            return account_operation(state.accounts, actor, 'rotate-self', data)
        if route.startswith('/api/admin/'):
            require(actor, 'admin')
            operation = route.rsplit('/', 1)[-1]
            if operation == 'settings':
                return state.configure(data, actor.user_id)
            if operation in ('create', 'role', 'delete', 'rotate'):
                return account_operation(state.accounts, actor, 'rotate-user' if operation == 'rotate' else operation, data)
            raise ValueError('Неизвестная операция с пользователями')
        return execute_web(ctx, actor, route, data)


async def workspace_events(state, token, *, interval=1):
    """No transaction or workspace lock is held while waiting for a client."""
    previous = None
    while True:
        try:
            await run_in_threadpool(state.accounts.authenticate, token, touch=False)
        except PermissionError:
            yield 'event: session-expired\ndata: {"code":"session_expired"}\n\n'
            return
        with state.state_lock:
            value = {'revision': state.revision(state.database), 'workspace_id': state.workspace_id}
        if value != previous:
            yield 'event: workspace\ndata: ' + json.dumps(value) + '\n\n'
            previous = value
        else:
            yield ': heartbeat\n\n'
        await asyncio.sleep(interval)


def create_app(state):
    """Accept a prepared shared workspace; importing/factory calls do not migrate DBs."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.workspace = state

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return error_response(request, 'Страница не найдена' if error.status_code == 404 else str(error.detail),
                              error.status_code, 'not_found' if error.status_code == 404 else 'http_error')

    def endpoint(route, post=False):
        async def handle(request: Request):
            try:
                check_site(request)
                data = None
                if post:
                    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
                        raise ValueError('Требуется application/json')
                    size = 0
                    chunks = []
                    async for chunk in request.stream():
                        size += len(chunk)
                        if size > MAX_BODY:
                            return error_response(request, 'Допустимый размер запроса — до 48 МБ', 413, 'body_too_large')
                        chunks.append(chunk)
                    data = json.loads(b''.join(chunks))
                    if not isinstance(data, dict):
                        raise ValueError('Требуется объект JSON')
                result = await run_in_threadpool(dispatch, state, route,
                                                parse_qs(request.url.query, keep_blank_values=True),
                                                data, request.headers.get('x-itd-token', ''))
                if isinstance(result, FileResult):
                    return Response(result.content, media_type=result.mime,
                                    headers={**SECURITY_HEADERS, 'Content-Disposition': "attachment; filename*=UTF-8''" + quote(result.filename)})
                return JSONResponse(result, headers=SECURITY_HEADERS)
            except Exception as error:
                return failure(request, error)
        return handle

    reads = set(WEB_READS) | {'/api/account', '/api/admin'}
    posts = set(WEB_POSTS) | {'/api/login', '/api/logout', '/api/account/profile', '/api/account/rotate',
                            '/api/admin/settings', '/api/admin/create', '/api/admin/role', '/api/admin/delete', '/api/admin/rotate'}
    for post, routes in ((False, reads), (True, posts)):
        for route in sorted(routes):
            for prefix in ('/api/', '/api/v1/'):
                path = route.replace('/api/', prefix, 1)
                schema = WorkspaceActionInput.model_json_schema() if route == '/api/action' else {'type': 'object', 'additionalProperties': True}
                extra = {'requestBody': {'required': True, 'content': {'application/json': {'schema': schema}}}} if post else None
                app.add_api_route(path, endpoint(route, post), methods=['POST' if post else 'GET'],
                                  name=('post_' if post else 'get_') + path.replace('/', '_'),
                                  include_in_schema=prefix == '/api/v1/', openapi_extra=extra)

    @app.get('/api/v1/events')
    async def events(request: Request):
        try:
            check_site(request)
            token = request.headers.get('x-itd-token', '')
            await run_in_threadpool(state.accounts.authenticate, token, touch=False)
            return StreamingResponse(workspace_events(state, token), media_type='text/event-stream',
                                     headers={**SECURITY_HEADERS, 'X-Accel-Buffering': 'no'})
        except Exception as error:
            return failure(request, error)

    @app.get('/api/v1/openapi.json', include_in_schema=False)
    async def api_schema(request: Request):
        try:
            check_site(request)
            await run_in_threadpool(state.accounts.authenticate, request.headers.get('x-itd-token', ''), touch=False)
            return JSONResponse(app.openapi(), headers=SECURITY_HEADERS)
        except Exception as error:
            return failure(request, error)

    @app.get('/{asset:path}', include_in_schema=False)
    def static(request: Request, asset: str):
        try:
            check_site(request)
            name = asset or 'index.html'
            if name not in ASSET_NAMES:
                return error_response(request, 'Страница не найдена', 404, 'not_found')
            return Response((ASSETS / name).read_bytes(), media_type=mimetypes.guess_type(name)[0] or 'application/octet-stream',
                            headers=SECURITY_HEADERS)
        except Exception as error:
            return failure(request, error)

    return app
