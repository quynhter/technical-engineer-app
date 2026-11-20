"""Read-only tools and official HTTP transport, exclusively disposable databases."""
from dataclasses import replace
from contextlib import closing, contextmanager
import asyncio
import json
from pathlib import Path
import sqlite3
import socket
import threading
import tempfile
import subprocess
import sys
from time import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from itd.accounts import Accounts
from itd.db import initialize, connect, add_object, add_project
from itd import knowledge, tools
from itd.mcp_server import create_app
from itd.services.context import Actor, ServiceContext
from itd.services.operations import execute_cli


@contextmanager
def database_connection(path):
    with closing(sqlite3.connect(path)) as c, c:
        yield c


class ToolTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='itd-mcp-')
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.database = self.folder / 'test.db'
        initialize(self.database)
        with connect(self.database) as c:
            oid = add_object(c, 'Учебный объект')
            self.pid = add_project(c, object_id=oid, section_code='ЭОМ', code='MCP', name='Учебный раздел')
        self.ctx = ServiceContext(database=self.database, root=self.folder / 'ИТД')
        root = self.folder / 'knowledge'
        (root / 'test').mkdir(parents=True)
        (root / 'test' / 'sample.md').write_text(
            '---\ndoc_id: "TEST"\nclause: "1"\nwork_types: []\nitd_forms: []\nkeywords: []\n---\nУчебная проверка кабеля.\n')
        self.addCleanup(patch.stopall)
        patch('itd.knowledge.default_root', return_value=root).start()
        self.knowledge_root = root
        knowledge.build_index(root, knowledge.default_index(self.database))
        self.viewer = Actor(user_id=12, role='viewer', source='mcp', on_behalf_of=12)
        self.accounts = Accounts(self.folder / 'accounts.sqlite3')
        self.accounts.initialize()
        user = self.accounts.create({'first_name':'Тест','last_name':'Тест','role':'viewer'})
        self.uid = user['user']['id']
        self.session = self.accounts.login(user['code'])['session']
        self.token = self.accounts.create_token(self.uid, {'name':'MCP', 'expires_at':time()+3600})
        self.headers = {'Authorization': 'Bearer ' + self.token['token'],
                        'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version':'2025-06-18'}

    def client(self):
        client = TestClient(create_app(self.ctx, self.accounts), base_url='http://127.0.0.1:8766')
        self.addCleanup(client.close)
        return client

    def rpc(self, client, method, params=None, headers=None):
        return client.post('/mcp', headers=self.headers if headers is None else headers,
                           json={'jsonrpc':'2.0','id':1,'method':method,'params':params or {}})

    def dump(self):
        with database_connection(self.database) as c:
            return '\n'.join(c.iterdump())

    def test_all_read_tools_preserve_entire_database_and_share_versions(self):
        before = self.dump()
        expected = knowledge.status(self.knowledge_root, knowledge.default_index(self.database))['fingerprint']
        hit = knowledge.search(self.knowledge_root, knowledge.default_index(self.database), 'кабел')['hits'][0]['id']
        for tool in tools.available(self.viewer):
            args = {'project_id':self.pid} if tool.input is tools.ProjectInput else (
                {'id':hit} if tool.input is tools.ShowInput else {})
            result = tools.invoke(self.ctx, self.viewer, tool.name, args)
            self.assertNotIn('error', result, (tool.name, result))
            self.assertEqual(result['knowledge_version'], expected)
            self.assertEqual(result['skills_version'], tools.skills_version())
        self.assertEqual(before, self.dump())
        with database_connection(str(self.database)+'.audit.sqlite3') as c:
            rows = c.execute('SELECT source,actor_role,on_behalf_of,knowledge_version,skills_version,result FROM read_events').fetchall()
        self.assertEqual(len(rows), len(tools.TOOLS))
        self.assertTrue(all(row == ('mcp','viewer','12',expected,tools.skills_version(),'success') for row in rows))

    def test_search_show_exact_cli_payloads_and_fts5(self):
        args = tools.SearchInput(query='кабел', limit=10)
        expected = execute_cli(self.ctx, self.viewer, SimpleNamespace(command='knowledge-search', root=self.knowledge_root, **args.model_dump()))
        result = tools.invoke(self.ctx, self.viewer, 'knowledge-search', args.model_dump())
        self.assertEqual(result['data'], expected)
        eid = expected['hits'][0]['id']
        expected = execute_cli(self.ctx, self.viewer, SimpleNamespace(command='knowledge-show', root=self.knowledge_root, id=eid))
        self.assertEqual(tools.invoke(self.ctx, self.viewer, 'knowledge-show', {'id':eid})['data'], expected)
        with database_connection(knowledge.default_index(self.database)) as c:
            self.assertIn('fts5', c.execute("SELECT sql FROM sqlite_master WHERE name='knowledge_fts'").fetchone()[0])

    def test_no_paths_actor_override_or_unknown_arguments(self):
        for tool in tools.TOOLS:
            self.assertFalse({'db','database','root','accounts','role','user_id'} & tool.schema()['properties'].keys())
        for args in ({'db':str(self.folder/'other.db')}, {'role':'admin'}, {'query':{'private':'secret'}}, {'limit':True}):
            self.assertIn('error', tools.invoke(self.ctx, self.viewer, 'knowledge-search', args))
        self.assertFalse((self.folder/'other.db').exists())

    def test_role_and_allowlist_enforced_even_on_direct_invocation(self):
        fake = replace(tools.TOOLS[0], name='test-write', access='write', role='editor')
        with patch.object(tools, 'TOOLS', (*tools.TOOLS, fake)):
            self.assertNotIn(fake, tools.available(self.viewer))
            self.assertIn(fake, tools.available(self.viewer.model_copy(update={'role':'editor'})))
            self.assertEqual(tools.invoke(self.ctx, self.viewer, fake.name, {})['error']['code'], 'forbidden')
        self.assertEqual(tools.invoke(self.ctx, self.viewer, 'objects-list', {}, allowed=[])['error']['code'], 'forbidden')
        self.assertIn('error', tools.invoke(self.ctx, self.viewer, 'unknown-secret', {}))

    def test_audit_failure_never_returns_data(self):
        with patch('itd.tools.record', side_effect=OSError('unavailable')):
            with self.assertRaises(OSError):
                tools.invoke(self.ctx, self.viewer, 'objects-list', {})

    def test_old_sidecar_upgraded_without_business_changes(self):
        with database_connection(str(self.database)+'.audit.sqlite3') as c:
            c.execute('CREATE TABLE read_events (id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP, operation TEXT NOT NULL, project_id INTEGER NOT NULL, release_ids TEXT NOT NULL, source TEXT NOT NULL, user_id INTEGER)')
            c.execute("INSERT INTO read_events(operation,project_id,release_ids,source) VALUES('package-download',1,'[]','web')")
        before = self.dump()
        self.assertIn('data', tools.invoke(self.ctx, self.viewer, 'objects-list', {}))
        with database_connection(str(self.database)+'.audit.sqlite3') as c:
            self.assertEqual(c.execute('SELECT count(*) FROM read_events').fetchone()[0], 2)
        self.assertEqual(before, self.dump())

    def test_corrupt_knowledge_fails_closed(self):
        with patch('itd.tools.knowledge_execute', side_effect=ValueError('corrupt')):
            response = tools.invoke(self.ctx, self.viewer, 'objects-list', {})
        self.assertIn('error', response)
        self.assertNotIn('data', response)

    def test_http_initialization_listing_and_call(self):
        before = self.dump()
        with self.client() as c:
            init = self.rpc(c, 'initialize', {'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'test','version':'1'}})
            self.assertEqual(init.status_code, 200, init.text)
            listing = self.rpc(c, 'tools/list')
            self.assertEqual(listing.status_code, 200, listing.text)
            self.assertEqual({t['name'] for t in listing.json()['result']['tools']}, {t.name for t in tools.TOOLS})
            result = self.rpc(c, 'tools/call', {'name':'objects-list','arguments':{}})
            self.assertEqual(result.status_code, 200, result.text)
            payload = result.json()['result']['structuredContent']
            self.assertEqual(payload['data'][0]['name'], 'Учебный объект')
            self.assertIn('skills_version', payload)
        self.assertEqual(before, self.dump())

    def test_http_requires_bearer_never_accepts_session(self):
        with self.client() as c:
            for headers in ({}, {'X-ITD-Token':self.session}, {'Authorization':'Bearer '+self.session},
                            {'Authorization':'Basic '+self.token['token']}, {'Authorization':'Bearer invalid'}):
                self.assertEqual(self.rpc(c, 'tools/list', headers=headers).status_code, 401)
            self.assertEqual(c.get('/mcp', headers={}).status_code, 401)

    def test_http_viewer_neither_lists_nor_calls_write_tools(self):
        fake = replace(tools.TOOLS[0], name='test-write', access='write', role='editor')
        before = self.dump()
        with patch.object(tools, 'TOOLS', (*tools.TOOLS, fake)), self.client() as c:
            listing = self.rpc(c, 'tools/list').json()['result']['tools']
            self.assertNotIn(fake.name, {t['name'] for t in listing})
            result = self.rpc(c, 'tools/call', {'name':fake.name,'arguments':{}}).json()['result']
            self.assertTrue(result['isError'])
            self.assertEqual(result['structuredContent']['error']['code'], 'forbidden')
        self.assertEqual(before, self.dump())
        with database_connection(str(self.database)+'.audit.sqlite3') as c:
            self.assertEqual(c.execute('SELECT result FROM read_events').fetchone()[0], 'denied')

    def test_cli_help_creates_no_database(self):
        target = self.folder / 'never-created.db'
        result = subprocess.run([sys.executable,'-m','itd.mcp_server','--agent','--db',str(target),'--help'],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        for flag in ('--agent','--db','--accounts','--itd-root'):
            self.assertIn(flag, result.stdout)
        self.assertFalse(target.exists())

    def test_http_revoked_expired_and_current_role(self):
        with self.client() as c:
            self.assertEqual(self.rpc(c, 'tools/list').status_code, 200)
            with self.accounts.connect() as db, db:
                db.execute("UPDATE users SET role='editor' WHERE id=?", (self.uid,))
            response = self.rpc(c, 'tools/call', {'name':'objects-list','arguments':{}})
            self.assertFalse(response.json()['result']['isError'])
            with database_connection(str(self.database)+'.audit.sqlite3') as db:
                self.assertEqual(db.execute('SELECT actor_role FROM read_events ORDER BY id DESC LIMIT 1').fetchone()[0], 'editor')
            with patch('itd.accounts.monotonic', return_value=time()+7200):
                self.assertEqual(self.rpc(c, 'tools/list').status_code, 401)
            self.accounts.revoke_token(self.token['id'])
            self.assertEqual(self.rpc(c, 'tools/list').status_code, 401)

    def test_http_errors_and_logs_do_not_leak_payloads_or_secrets(self):
        with self.client() as c, self.assertLogs('itd.db', level='INFO') as logs:
            self.rpc(c, 'tools/call', {'name':'objects-list','arguments':{}})
            result = self.rpc(c, 'tools/call', {'name':'knowledge-search','arguments':{'query':{'private':'sensitive-document'}}})
            self.assertTrue(result.json()['result']['isError'])
            with patch('itd.tools.record', side_effect=OSError('sensitive-path')):
                failed = self.rpc(c, 'tools/call', {'name':'objects-list','arguments':{}})
            self.assertEqual(failed.json()['result']['structuredContent']['error']['code'], 'audit_unavailable')
        combined = '\n'.join(logs.output) + result.text + failed.text
        self.assertNotIn('sensitive-document', combined)
        self.assertNotIn('sensitive-path', combined)
        self.assertNotIn(self.token['token'], combined)
        with database_connection(str(self.database)+'.audit.sqlite3') as db:
            audit = '\n'.join(db.iterdump())
        self.assertNotIn('sensitive-document', audit)
        self.assertNotIn(self.token['token'], audit)

    def test_http_rejects_other_host_and_origin(self):
        with self.client() as c:
            for extra in ({'Host':'attacker.example'}, {'Origin':'https://attacker.example'}):
                response = self.rpc(c, 'tools/list', headers={**self.headers, **extra})
                self.assertIn(response.status_code, (400, 403, 421))

    def test_fixed_database_ignores_web_settings(self):
        other = self.folder / 'other.db'
        initialize(other)
        self.accounts.save_settings(other, self.folder / 'other-root')
        result = tools.invoke(self.ctx, self.viewer, 'objects-list', {})
        self.assertEqual(result['data'][0]['name'], 'Учебный объект')
        self.assertFalse(Path(str(other)+'.audit.sqlite3').exists())

    def test_official_client_over_real_loopback_http(self):
        import httpx2
        import uvicorn
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        before = self.dump()
        sock = socket.socket()
        self.addCleanup(sock.close)
        sock.bind(('127.0.0.1', 0))
        address = f'http://127.0.0.1:{sock.getsockname()[1]}/mcp'
        server = uvicorn.Server(uvicorn.Config(create_app(self.ctx, self.accounts), access_log=False, log_level='critical'))
        thread = threading.Thread(target=server.run, kwargs={'sockets':[sock]}, daemon=True)
        thread.start()
        try:
            async def run():
                async with asyncio.timeout(10):
                    while not server.started:
                        await asyncio.sleep(0.01)
                async with httpx2.AsyncClient(headers={'Authorization':self.headers['Authorization']}, timeout=10) as http:
                    async with streamable_http_client(address, http_client=http) as (read, write):
                        async with ClientSession(read, write, read_timeout_seconds=10) as session:
                            await session.initialize()
                            listing = await session.list_tools()
                            self.assertEqual({t.name for t in listing.tools}, {t.name for t in tools.TOOLS})
                            result = await session.call_tool('objects-list', {})
                            self.assertFalse(result.is_error)
                            self.assertEqual(result.structured_content['data'][0]['name'], 'Учебный объект')
            asyncio.run(run())
        finally:
            server.should_exit = True
            thread.join(timeout=10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(before, self.dump())


if __name__ == '__main__':
    unittest.main()
