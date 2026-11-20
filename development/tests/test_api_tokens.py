"""API token security contracts, using disposable accounts and business databases."""
import asyncio
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from time import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from itd.accounts import Accounts, SessionExpired
from itd.http_api import create_app, workspace_events
from itd.server_state import WorkspaceState


class ApiTokenTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='itd-token-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = WorkspaceState(self.root / 'test.db')
        _, code = self.state.prepare()
        self.client = TestClient(create_app(self.state), base_url='http://127.0.0.1:8765')
        self.addCleanup(self.client.close)
        self.admin = {'X-ITD-Token': self.state.accounts.login(code)['session']}

    def user(self, role):
        result = self.state.accounts.create({'first_name':'Тест','last_name':'Тест','role':role})
        return result['user']['id'], {'X-ITD-Token': self.state.accounts.login(result['code'])['session']}

    def issue(self, headers):
        response = self.client.post('/api/v1/account/tokens/create', headers=headers,
                                    json={'name':'Интеграция', 'expires_at':time()+3600, 'user_id':1, 'role':'admin'})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        return result['id'], result['token'], {'Authorization':'Bearer '+result['token']}

    def test_viewer_reads_but_cannot_write_and_reads_preserve_business_database(self):
        uid, session = self.user('viewer')
        _, _, headers = self.issue(session)
        with sqlite3.connect(self.state.database) as c:
            before = list(c.iterdump())
        self.assertEqual(self.client.get('/api/v1/bootstrap', headers=headers).status_code, 200)
        self.assertEqual(self.client.post('/api/v1/save', headers=headers, json={}).status_code, 403)
        self.assertEqual(self.client.get('/api/v1/account', headers=headers).json()['id'], uid)
        with sqlite3.connect(self.state.database) as c:
            self.assertEqual(before, list(c.iterdump()))

    def test_one_time_secret_not_in_database_lists_or_logs(self):
        with self.assertLogs('itd.db', level='INFO') as logs:
            tid, secret, headers = self.issue(self.admin)
            self.client.get('/api/v1/bootstrap', headers=headers)
            self.client.post('/api/v1/account/tokens/revoke', headers=self.admin, json={'id':tid})
        self.assertNotIn(secret, '\n'.join(logs.output))
        for endpoint in ('/api/v1/account/tokens', '/api/v1/admin/tokens'):
            rows = self.client.get(endpoint, headers=self.admin).json()
            self.assertNotIn(secret, json.dumps(rows))
            self.assertNotIn('token_hash', rows[0])
        with self.state.accounts.connect() as c:
            dump = '\n'.join(c.iterdump())
            self.assertNotIn(secret, dump)
            self.assertIn(hashlib.sha256(secret.encode()).hexdigest(), dump)
            row = c.execute('SELECT * FROM api_tokens WHERE id=?', (tid,)).fetchone()
            self.assertIsNotNone(row['last_used_at'])
            self.assertIsNotNone(row['revoked_at'])
        for file in self.root.rglob('*'):
            if file.is_file():
                self.assertNotIn(secret.encode(), file.read_bytes(), str(file))

    def test_revocation_expiry_deleted_user_and_role_change(self):
        uid, session = self.user('editor')
        tid, secret, headers = self.issue(session)
        self.assertEqual(self.client.post('/api/v1/admin/tokens/revoke', headers=self.admin, json={'id':tid}).status_code, 200)
        self.assertEqual(self.client.get('/api/v1/account', headers=headers).status_code, 403)
        _, secret, headers = self.issue(session)
        with patch('itd.accounts.monotonic', return_value=time()+7200):
            self.assertEqual(self.client.get('/api/v1/account', headers=headers).status_code, 403)
        self.assertEqual(self.client.post('/api/v1/admin/role', headers=self.admin, json={'id':uid,'role':'viewer'}).status_code, 200)
        self.assertEqual(self.client.post('/api/v1/save', headers=headers, json={}).status_code, 403)
        self.assertEqual(self.client.get('/api/v1/account', headers=headers).status_code, 403)
        # A fresh token for this current viewer still cannot write.
        fresh = self.state.accounts.create_token(uid, {'name':'Новый', 'expires_at':time()+3600})
        headers = {'Authorization':'Bearer '+fresh['token']}
        self.assertEqual(self.client.post('/api/v1/save', headers=headers, json={}).status_code, 403)
        self.assertEqual(self.client.post('/api/v1/admin/delete', headers=self.admin, json={'id':uid}).status_code, 200)
        self.assertEqual(self.client.get('/api/v1/account', headers=headers).status_code, 403)
        self.assertEqual(self.state.accounts.list_tokens(uid), [])

    def test_current_role_is_read_each_request_and_payload_does_not_escalate(self):
        from itd.db import connect, add_object, add_project
        with connect(self.state.database) as c:
            oid = add_object(c, 'Тестовый объект')
            pid = add_project(c, object_id=oid, section_code='ЭОМ', code='TOKEN', name='Тестовый раздел')
        uid, session = self.user('editor')
        _, _, headers = self.issue(session)
        self.assertEqual(self.client.post('/api/v1/activate', headers=headers, json={'project_id':pid}).status_code, 200)
        # Out-of-band role update verifies lookup independently of explicit revocation.
        with self.state.accounts.connect() as c, c:
            c.execute("UPDATE users SET role='viewer' WHERE id=?", (uid,))
        self.assertEqual(self.client.get('/api/v1/account', headers=headers).json()['role'], 'viewer')
        self.assertEqual(self.client.post('/api/v1/save', headers=headers, json={'role':'admin'}).status_code, 403)
        self.assertEqual(self.client.post('/api/v1/activate', headers=headers, json={'project_id':pid}).status_code, 403)

    def test_only_owner_or_admin_can_list_and_revoke(self):
        _, first = self.user('viewer')
        _, second = self.user('editor')
        tid, _, _ = self.issue(first)
        self.assertEqual(self.client.get('/api/v1/account/tokens', headers=second).json(), [])
        self.assertEqual(self.client.get('/api/v1/admin/tokens', headers=second).status_code, 403)
        self.assertEqual(self.client.post('/api/v1/account/tokens/revoke', headers=second, json={'id':tid}).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/admin/tokens/revoke', headers=second, json={'id':tid}).status_code, 403)
        self.assertEqual(self.client.post('/api/v1/account/tokens/revoke', headers=first, json={'id':tid}).status_code, 200)

    def test_invalid_bearer_never_falls_back_to_session_and_credentials_are_separate(self):
        _, secret, headers = self.issue(self.admin)
        for authorization in ('Bearer bad', 'Basic abc', 'Bearer', 'Bearer a b'):
            self.assertEqual(self.client.get('/api/v1/account', headers={**self.admin,'Authorization':authorization}).status_code, 403)
        self.assertEqual(self.client.get('/api/v1/account', headers={'X-ITD-Token':secret}).status_code, 403)
        self.assertEqual(self.client.get('/api/v1/account', headers={'Authorization':'Bearer '+self.admin['X-ITD-Token']}).status_code, 403)
        self.assertEqual(self.client.get('/api/v1/openapi.json', headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/api/account', headers=headers).status_code, 200)

    def test_events_stop_after_token_revocation(self):
        tid, secret, _ = self.issue(self.admin)
        async def run():
            stream = workspace_events(self.state, secret, bearer=True, interval=0)
            self.assertIn('event: workspace', await anext(stream))
            self.state.accounts.revoke_token(tid)
            self.assertIn('session-expired', await anext(stream))
            await stream.aclose()
        asyncio.run(run())

    def test_validation_and_persistence(self):
        for data in ({}, {'name':'','expires_at':time()+1000}, {'name':'a'*81,'expires_at':time()+1000},
                     {'name':'a','expires_at':time()-1}, {'name':'a','expires_at':True}):
            self.assertEqual(self.client.post('/api/v1/account/tokens/create', headers=self.admin, json=data).status_code, 400)
        _, secret, _ = self.issue(self.admin)
        other = Accounts(self.state.accounts.path)
        other.initialize()
        self.assertEqual(other.authenticate_token(secret)['role'], 'admin')

    def test_migrates_previous_account_schema_without_changing_users_or_sessions(self):
        for sessions in (False, True):
            with self.subTest(sessions=sessions):
                path = self.root / ('old-'+str(sessions)+'.db')
                a = Accounts(path)
                a.initialize()
                existing = a.session(1)
                before = a.get(1)
                with a.connect() as c, c:
                    c.execute('DROP TABLE api_tokens')
                    c.execute('DELETE FROM account_schema_migrations WHERE version=2')
                    if not sessions:
                        c.execute('DROP TABLE sessions')
                        c.execute('DROP TABLE account_schema_migrations')
                a.initialize()
                a.initialize()
                self.assertEqual(before, a.get(1))
                if sessions:
                    self.assertEqual(a.authenticate(existing)['id'], 1)
                with a.connect() as c:
                    self.assertEqual(c.execute('SELECT version FROM account_schema_migrations ORDER BY version').fetchall()[1][0], 2)
                    self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
                issued = a.create_token(1, {'name':'Миграция','expires_at':time()+3600})
                self.assertEqual(a.authenticate_token(issued['token'])['id'], 1)
