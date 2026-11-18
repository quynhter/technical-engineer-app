"""FastAPI and persistent sessions, exclusively temporary workspaces."""
import asyncio
from contextlib import closing
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from urllib.parse import unquote
from unittest.mock import patch
from zipfile import ZipFile

from fastapi.testclient import TestClient

from itd.accounts import Accounts, SessionExpired, MAX_USER_SESSIONS
from itd.db import connect, initialize, add_object, add_project
from itd.http_api import create_app, workspace_events
from itd.server_state import WorkspaceState


class HttpApiTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='itd-asgi-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = WorkspaceState(self.root / 'test.db')
        _, self.code = self.state.prepare()
        self.client = TestClient(create_app(self.state), base_url='http://127.0.0.1:8765')
        self.addCleanup(self.client.close)
        response = self.client.post('/api/v1/login', json={'code': self.code})
        self.assertEqual(response.status_code, 200, response.text)
        self.token = response.json()['session']
        self.headers = {'X-ITD-Token': self.token}

    def dump(self):
        with closing(sqlite3.connect(self.state.database)) as c:
            return '\n'.join(c.iterdump())

    def test_v1_and_legacy_routes_share_services_and_reads_preserve_business_db(self):
        before = self.dump()
        old = self.client.get('/api/bootstrap', headers=self.headers)
        new = self.client.get('/api/v1/bootstrap', headers=self.headers)
        self.assertEqual(old.json(), new.json())
        self.assertEqual(new.status_code, 200)
        self.assertEqual(before, self.dump())
        self.assertEqual(new.headers['cache-control'], 'no-store')
        self.assertEqual(self.client.get('/api/v1/openapi.json', headers=self.headers).status_code, 200)

    def test_roles_origin_host_validation_and_structured_errors(self):
        denied = self.client.get('/api/v1/bootstrap')
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()['error']['code'], 'session_expired')
        self.assertIsInstance(self.client.get('/api/bootstrap').json()['error'], str)
        user = self.state.accounts.create({'first_name': 'Тест', 'last_name': 'Тест', 'role': 'viewer'})
        viewer = self.state.accounts.login(user['code'])['session']
        response = self.client.post('/api/v1/save', headers={'X-ITD-Token': viewer}, json={})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'forbidden')
        for headers in ({**self.headers, 'Origin': 'http://evil.test'}, {**self.headers, 'Host': 'evil.test'}):
            self.assertEqual(self.client.get('/api/v1/bootstrap', headers=headers).status_code, 403)
        self.assertEqual(self.client.get('/../../AGENTS.md', headers=self.headers).status_code, 404)

    def test_sessions_survive_new_instances_and_only_hashes_are_stored(self):
        other = Accounts(self.state.accounts.path)
        other.initialize()
        self.assertEqual(other.authenticate(self.token)['role'], 'admin')
        with other.connect() as c:
            rows = [dict(r) for r in c.execute('SELECT * FROM sessions')]
        self.assertNotIn(self.token, json.dumps(rows))
        self.assertIn(hashlib.sha256(self.token.encode()).hexdigest(), {r['token_hash'] for r in rows})
        new_state = WorkspaceState(self.state.database)
        new_state.prepare()
        with TestClient(create_app(new_state), base_url='http://127.0.0.1:8765') as client:
            self.assertEqual(client.get('/api/v1/account', headers=self.headers).status_code, 200)
        other.discard_session(self.token)
        self.assertEqual(self.client.get('/api/v1/account', headers=self.headers).status_code, 403)

    def test_session_limit_and_revocation_work_across_instances(self):
        tokens = [self.state.accounts.session(1) for _ in range(MAX_USER_SESSIONS + 1)]
        other = Accounts(self.state.accounts.path)
        with other.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM sessions WHERE user_id=1').fetchone()[0], MAX_USER_SESSIONS)
        with self.assertRaises(SessionExpired):
            other.authenticate(tokens[0])
        other.revoke(1)
        with self.assertRaises(SessionExpired):
            self.state.accounts.authenticate(tokens[-1])

    def test_wal_is_enabled_during_preparation_and_read_factory_does_not_migrate(self):
        for path in (self.state.database, self.state.accounts.path):
            with closing(sqlite3.connect(path)) as c:
                self.assertEqual(c.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
        path = self.root / 'not-created.db'
        create_app(WorkspaceState(path))
        self.assertFalse(path.exists())

    def test_json_body_errors_and_unauthenticated_events(self):
        for body in ('[]', '{broken'):
            response = self.client.post('/api/v1/save', headers={**self.headers, 'Content-Type': 'application/json'}, content=body)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error']['code'], 'invalid_input')
        self.assertEqual(self.client.get('/api/v1/events').status_code, 403)

    def test_events_are_cancelable_and_stop_after_revocation(self):
        async def run():
            stream = workspace_events(self.state, self.token, interval=0)
            self.assertTrue((await anext(stream)).startswith('event: workspace\n'))
            self.state.accounts.discard_session(self.token)
            self.assertIn('session-expired', await anext(stream))
            with self.assertRaises(StopAsyncIteration):
                await anext(stream)
            other = workspace_events(self.state, self.state.accounts.session(1), interval=0)
            await anext(other)
            await other.aclose()
        asyncio.run(run())

    def test_v1_docx_zip_names_integrity_roles_and_audit_failure(self):
        from docx import Document
        from itd.acts import register_form, add_act
        templates = self.root / 'templates'
        templates.mkdir()
        document = Document()
        document.add_paragraph('Тестовый документ {{ city }}')
        document.save(templates / 'API_TEST.docx')
        self.state.templates = templates
        with connect(self.state.database) as c:
            oid = add_object(c, 'Тестовый объект')
            pid = add_project(c, object_id=oid, section_code='ЭОМ', code='API', name='Раздел', city='Город')
            register_form(c, code='API_TEST', name='Тестовый акт', fields=[{'key':'city','kind':'reference','source':'project.city'}])
            aid = add_act(c, project_id=pid, act_type='API_TEST')
        generated = self.client.post('/api/v1/generate', headers=self.headers, json={'project_id':pid,'act_id':aid})
        self.assertEqual(generated.status_code, 200, generated.text)
        release_id = generated.json()['release_id']
        with connect(self.state.database) as c:
            release = dict(c.execute('SELECT * FROM releases WHERE id=?', (release_id,)).fetchone())
        before = self.dump()
        direct = self.client.get(f'/api/v1/download?project_id={pid}&release_id={release_id}', headers=self.headers)
        self.assertEqual(direct.status_code, 200)
        name = Path(release['path']).name
        self.assertTrue(unquote(direct.headers['content-disposition']).endswith(name))
        for _ in range(2):
            package = self.client.get(f'/api/v1/package?project_id={pid}', headers=self.headers)
            self.assertEqual(package.status_code, 200, package.text if package.status_code != 200 else '')
            with ZipFile(io.BytesIO(package.content)) as archive:
                manifest = json.loads(archive.read('manifest.json'))
                item = next(row for row in manifest['releases'] if row['release_id'] == release_id)
                self.assertEqual(Path(item['file']).name, name)
                self.assertEqual(archive.read(item['file']), direct.content)
                self.assertEqual(hashlib.sha256(direct.content).hexdigest(), item['sha256'])
            self.assertEqual(self.dump(), before)
        viewer = self.state.accounts.create({'first_name':'Тест','last_name':'Тест','role':'viewer'})
        viewer_token = self.state.accounts.login(viewer['code'])['session']
        self.assertEqual(self.client.get(f'/api/v1/package?project_id={pid}', headers={'X-ITD-Token':viewer_token}).status_code, 403)
        sidecar = Path(str(self.state.database) + '.audit.sqlite3')
        with closing(sqlite3.connect(sidecar)) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM read_events').fetchone()[0], 2)
        sidecar.unlink()
        sidecar.mkdir()
        rejected = self.client.get(f'/api/v1/package?project_id={pid}', headers=self.headers)
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(rejected.headers['content-type'], 'application/json')
        self.assertEqual(self.dump(), before)

    def test_v1_database_switch_revokes_old_sessions_and_uses_new_context(self):
        old_path = self.state.database
        old_dump = self.dump()
        other = self.root / 'alternate' / 'other.db'
        other.parent.mkdir()
        initialize(other)
        with connect(other) as c:
            oid = add_object(c, 'Другая тестовая БД')
            pid = add_project(c, object_id=oid, section_code='ЭОМ', code='OTHER', name='Другой раздел')
        response = self.client.post('/api/v1/admin/settings', headers=self.headers,
                                    json={'database_path':str(other), 'itd_root':str(self.root/'other-tree')})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get('/api/v1/bootstrap', headers=self.headers).status_code, 403)
        headers = {'X-ITD-Token': response.json()['session']}
        self.assertEqual(self.client.get('/api/v1/bootstrap', headers=headers).json()['objects'][0]['name'], 'Другая тестовая БД')
        self.assertEqual(self.client.post('/api/v1/activate', headers=headers, json={'project_id':pid}).status_code, 200)
        with closing(sqlite3.connect(old_path)) as c:
            self.assertEqual('\n'.join(c.iterdump()), old_dump)
        with connect(other) as c:
            self.assertEqual(c.execute('SELECT project_id FROM agent_state').fetchone()[0], pid)

    def test_api_body_limit_is_enforced_before_dispatch(self):
        with patch('itd.http_api.MAX_BODY', 8):
            response = self.client.post('/api/v1/save', headers=self.headers, json={'value':'too long'})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()['error']['code'], 'body_too_large')


if __name__ == '__main__':
    unittest.main()
