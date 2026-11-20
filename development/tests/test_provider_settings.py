"""Browser configuration authorizes administrators and never returns saved secrets."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from itd import llm
from itd.http_api import create_app
from itd.server_state import WorkspaceState
from itd.services import providers
from itd.services.context import Actor


class ProviderSettingsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.state = WorkspaceState(Path(temp.name) / 'test.db')
        self.state.prepare()
        self.path = providers.config_path(self.state.accounts)
        self.admin = Actor(user_id=1, role='admin', source='assistant', on_behalf_of=1)
        self.data = dict(name='local-test', protocol='chat', base_url='http://127.0.0.1:11434/v1',
                         api_key='fixture-only-secret', allow_anonymous=False)

    def test_save_reload_replace_and_private_permissions(self):
        with patch.dict(os.environ, {}, clear=True):
            providers.save(self.admin, self.path, self.data)
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(llm.profiles(self.path)['local-test']['api_key'], self.data['api_key'])
            self.assertNotIn(self.data['api_key'], json.dumps(providers.settings(self.admin, self.path)))
            providers.save(self.admin, self.path, {**self.data, 'api_key': '', 'base_url': 'http://localhost:11434/v1'})
            self.assertEqual(llm.profiles(self.path)['local-test']['api_key'], self.data['api_key'])
            providers.save(self.admin, self.path, {**self.data, 'api_key': 'replacement-key'})
            self.assertEqual(llm.profiles(self.path)['local-test']['api_key'], 'replacement-key')
            before = self.path.read_bytes()
            with patch('itd.services.providers.os.replace', side_effect=OSError('disk')):
                with self.assertRaises(OSError):
                    providers.save(self.admin, self.path, self.data)
            self.assertEqual(self.path.read_bytes(), before)
            self.assertFalse(list(self.path.parent.glob('.llm-*')))

    def test_browser_flow_persists_provider_then_assistant_without_restart(self):
        admin = {'X-ITD-Token': self.state.accounts.session(1)}
        with patch.dict(os.environ, {}, clear=True), TestClient(create_app(self.state), base_url='http://127.0.0.1:8765') as client:
            saved = client.post('/api/v1/assistant/provider', headers=admin, json=self.data)
            self.assertEqual(saved.status_code, 200, saved.text)
            config = client.get('/api/v1/assistant/admin', headers=admin)
            self.assertEqual(config.status_code, 200)
            self.assertIn('local-test', config.json()['providers'])
            self.assertNotIn(self.data['api_key'], config.text)
            response = client.post('/api/v1/assistant/config', headers=admin,
                                   json=dict(name='Инженер', provider='local-test', model='fixture'))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(client.get('/api/v1/assistants', headers=admin).json()[0]['name'], 'Инженер')
        # A new application instance reads the saved configuration.
        with TestClient(create_app(self.state), base_url='http://127.0.0.1:8765') as client:
            self.assertEqual(len(client.get('/api/v1/assistants', headers=admin).json()), 1)

    def test_credentials_are_isolated_between_account_stores_in_the_same_directory(self):
        from itd.accounts import Accounts
        other = Accounts(self.state.accounts.path.with_name('other.accounts.sqlite3'))
        with patch.dict(os.environ, {}, clear=True):
            providers.save(self.admin, self.path, self.data)
            self.assertNotEqual(self.path, providers.config_path(other))
            self.assertNotIn('local-test', llm.profiles(providers.config_path(other)))

    def test_roles_and_invalid_input_cannot_write_or_leak(self):
        editor = self.state.accounts.create(dict(first_name='Тест', last_name='Редактор', role='editor'))
        viewer = self.state.accounts.create(dict(first_name='Тест', last_name='Наблюдатель', role='viewer'))
        with TestClient(create_app(self.state), base_url='http://127.0.0.1:8765') as client:
            for user in (editor, viewer):
                headers = {'X-ITD-Token': self.state.accounts.login(user['code'])['session']}
                response = client.post('/api/v1/assistant/provider', headers=headers, json=self.data)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn(self.data['api_key'], response.text)
            self.assertFalse(self.path.exists())
            for changes in ({'base_url': 'https://user:password@example.test'}, {'api_key': 'secret\nvalue'},
                            {'protocol': 'unknown'}, {'name': '../escape'}, {'api_key': ''}):
                response = client.post('/api/v1/assistant/provider', headers={'X-ITD-Token': self.state.accounts.session(1)},
                                       json={**self.data, **changes})
                self.assertEqual(response.status_code, 400)
                self.assertNotIn(self.data['api_key'], response.text)
            self.assertFalse(self.path.exists())
