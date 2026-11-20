"""Official MCP Streamable HTTP SDK; explicit immutable workspace, Bearer only."""
import argparse
import json
import logging
from pathlib import Path

from mcp import types
from mcp.server.lowlevel import Server
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from .accounts import Accounts
from .services.context import Actor, ServiceContext
from .tools import available, invoke, versions


def create_app(ctx, accounts, *, host='127.0.0.1'):
    """Neither creates nor migrates databases. Authentication is repeated per request/call."""
    logging.getLogger('mcp').setLevel(logging.CRITICAL)
    if not ctx.database.is_file() or not accounts.path.is_file():
        raise ValueError('MCP требует существующие БД и хранилище аккаунтов')
    def actor(request):
        headers = request.headers.getlist('authorization')
        parts = headers[0].split() if len(headers) == 1 else []
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise PermissionError('Bearer required')
        user = accounts.authenticate_token(parts[1])
        return Actor(user_id=user['id'], role=user['role'], source='mcp', on_behalf_of=user['id'])

    async def list_tools(context, params):
        principal = await run_in_threadpool(actor, context.request)
        try:
            meta = await run_in_threadpool(versions, ctx)
        except Exception:
            return types.ListToolsResult(tools=[], _meta={'error': 'knowledge_unavailable',
                'knowledge_version': 'unavailable', 'skills_version': 'unavailable'})
        return types.ListToolsResult(tools=[types.Tool(
            name=tool.name, description=tool.description, inputSchema=tool.schema(),
            annotations=types.ToolAnnotations(readOnlyHint=tool.access == 'read',
                                             destructiveHint=tool.access == 'write',
                                             openWorldHint=False)) for tool in available(principal)], _meta=meta)

    async def call_tool(context, params):
        principal = await run_in_threadpool(actor, context.request)
        try:
            result = await run_in_threadpool(invoke, ctx, principal, params.name, params.arguments or {})
        except Exception:
            # In particular, never return business data if the sidecar is unavailable.
            result = {'error': {'code': 'audit_unavailable', 'message': 'Не удалось записать аудит чтения.'},
                      'knowledge_version': 'unavailable', 'skills_version': 'unavailable'}
        return types.CallToolResult(content=[types.TextContent(type='text', text=json.dumps(result, ensure_ascii=False))],
                                    structuredContent=result, isError='error' in result)

    server = Server('itd-read-tools', version='1', on_list_tools=list_tools, on_call_tool=call_tool)
    transport = server.streamable_http_app(stateless_http=True, json_response=True, host=host,
                                           max_request_body_size=64 * 1024)

    class BearerOnly:
        def __init__(self, app):
            self.app = app
            self.state = app.state

        async def __call__(self, scope, receive, send):
            if scope['type'] == 'http':
                from starlette.requests import Request
                try:
                    await run_in_threadpool(actor, Request(scope))
                except PermissionError:
                    await JSONResponse({'error': 'Требуется действующий токен API.'}, status_code=401,
                                       headers={'WWW-Authenticate': 'Bearer', 'Cache-Control': 'no-store'})(scope, receive, send)
                    return
            await self.app(scope, receive, send)

    return BearerOnly(transport)


def main(argv=None):
    parser = argparse.ArgumentParser(description='ИТД: MCP по HTTP, только чтение; БД фиксируется при запуске.')
    parser.add_argument('--agent', action='store_true', help='Записать запуск агента в logs/ai.log')
    parser.add_argument('--db', type=Path, required=True, help='Абсолютный путь существующей БД')
    parser.add_argument('--accounts', type=Path, required=True, help='Абсолютный путь существующей БД аккаунтов')
    parser.add_argument('--itd-root', type=Path, required=True, help='Абсолютный путь дерева ИТД')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args(argv)
    for path in (args.db, args.accounts, args.itd_root):
        if not path.is_absolute() or not path.exists():
            parser.error('Укажите существующие абсолютные пути')
    if not args.db.is_file() or not args.accounts.is_file() or not args.itd_root.is_dir():
        parser.error('Проверьте типы БД и папки ИТД')
    ctx = ServiceContext(database=args.db.resolve(), root=args.itd_root.resolve())
    # Fail before listening if protected sources are missing/corrupted/LFS pointers.
    versions(ctx)
    if args.agent:
        from .logging_setup import configure
        from .paths import ROOT
        configure(ROOT / 'logs')
        logging.getLogger('itd.ai').info('Агент запустил команду mcp-server')
    # SDK/protocol diagnostics must never log request bodies or exception payloads.
    logging.getLogger('mcp').setLevel(logging.CRITICAL)
    import uvicorn
    uvicorn.run(create_app(ctx, Accounts(args.accounts.resolve()), host=args.host),
                host=args.host, port=args.port, access_log=False)


if __name__ == '__main__':
    main()
