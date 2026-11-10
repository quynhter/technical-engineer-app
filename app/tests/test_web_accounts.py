import base64
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from itd.db import add_object, add_project, connect, initialize
from itd.web import create_server


class WebAccountTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.database = self.root / 'instance' / 'itd.db'
        self.start()
        self.admin = self.login(self.code)

    def start(self):
        self.server = create_server(self.database, 0)
        self.addCleanup(self.server.server_close)
        _, self.code = self.server.prepare()
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.shutdown)

    def request(self, route, session='', data=None, status=200):
        request = Request(self.server.origin + '/api/' + route,
                          headers={'X-ITD-Token': session, 'Content-Type': 'application/json'},
                          data=json.dumps(data).encode() if data is not None else None)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            result = json.load(response)
            self.assertEqual(response.code, status, result.get('error'))
            return result

    def login(self, code):
        return self.request('login', data={'code': code})['session']

    def add_user(self, role):
        result = self.request('admin/create', self.admin, {'first_name': 'Иван', 'last_name': 'Иванов', 'role': role})
        return result['user']['id'], result['code']

    def test_roles_enforced_at_the_http_boundary(self):
        _, code = self.add_user('viewer')
        viewer = self.login(code)
        self.assertEqual(self.request('account', viewer)['role'], 'viewer')
        self.request('bootstrap', viewer)
        self.request('account/profile', viewer, {'first_name': 'Пётр', 'last_name': 'Иванов'})
        self.request('admin', viewer, status=403)
        for route in ('save', 'entry', 'statement', 'generate', 'activate', 'files/plan', 'versions/list'):
            with self.subTest(route=route):
                self.request(route, viewer, {}, status=403)
        for route in ('download', 'original', 'package', 'configuration'):
            self.request(route, viewer, status=403)

        _, code = self.add_user('editor')
        editor = self.login(code)
        self.request('admin/settings', editor, {}, status=403)
        self.request('admin/create', editor, {}, status=403)
        saved = self.request('save', editor, {'object': {'name': 'Тестовый объект'}, 'participants': [], 'projects': []})
        self.assertEqual(saved['object']['name'], 'Тестовый объект')
        self.assertEqual(self.request('bootstrap', viewer)['objects'][0]['name'], 'Тестовый объект')

    def test_login_logout_rotation_and_role_changes_revoke_sessions(self):
        user_id, code = self.add_user('viewer')
        first, second = self.login(code), self.login(code)
        self.request('logout', first, {})
        self.request('account', first, status=403)
        self.request('account', second)
        updated = self.request('account/rotate', second, {})
        self.request('account', second, status=403)
        self.request('login', data={'code': code}, status=403)
        self.assertEqual(self.request('account', updated['session'])['id'], user_id)
        self.request('admin/role', self.admin, {'id': user_id, 'role': 'editor'})
        self.request('account', updated['session'], status=403)
        edited = self.login(updated['code'])
        self.assertEqual(self.request('account', edited)['role'], 'editor')
        fresh = self.request('admin/rotate', self.admin, {'id': user_id})
        self.request('account', edited, status=403)
        new_session = self.login(fresh['code'])
        self.request('admin/delete', self.admin, {'id': user_id})
        self.request('account', new_session, status=403)
        self.request('login', data={'code': fresh['code']}, status=403)
        self.request('admin/delete', self.admin, {'id': self.request('account', self.admin)['id']}, status=400)

    def test_switch_database_and_external_itd_root_then_restart(self):
        _, editor_code = self.add_user('editor')
        old_editor = self.login(editor_code)
        old_admin_code = self.code
        alternate = self.root / 'test' / 'sample.db'
        alternate.parent.mkdir()
        initialize(alternate)
        with connect(alternate) as conn:
            object_id = add_object(conn, 'Тестовый объект')
            project_id = add_project(conn, object_id=object_id, section_code='ТЕСТ', code='001', name='Раздел')
        docs = self.root / 'Документы'
        settings = {'database_path': str(alternate), 'itd_root': str(docs)}
        self.request('admin/settings', self.admin, {**settings, 'database_path': str(self.root / 'missing.db')}, status=400)
        self.assertEqual(self.request('bootstrap', self.admin)['objects'], [])
        initial_root = self.request('admin', self.admin)['settings']['itd_root']
        self.request('admin/settings', self.admin, {**settings, 'itd_root': initial_root}, status=400)
        switched = self.request('admin/settings', self.admin, settings)
        self.request('bootstrap', self.admin, status=403)
        self.request('bootstrap', old_editor, status=403)
        self.assertEqual(self.request('bootstrap', switched['session'])['objects'][0]['name'], 'Тестовый объект')
        editor = self.login(editor_code)
        original = self.request('upload', editor, {'project_id': project_id, 'name': 'source.pdf',
                                                  'content': base64.b64encode(b'test pdf').decode()})
        self.assertTrue(Path(original['project_path']).is_relative_to(docs))
        self.assertTrue(Path(original['project_path']).is_file())
        report = self.request('files/plan', editor, {'project_id': project_id})
        self.assertEqual(report['plan']['actions'], [])
        result = self.request('statement', editor, {'project_id': project_id})
        self.assertTrue(Path(result['output']).is_relative_to(docs))
        self.assertTrue(Path(result['output']).is_file())
        self.server.shutdown()
        self.server.server_close()
        self.start()
        self.assertIsNone(self.code)
        admin = self.login(old_admin_code)
        self.assertEqual(self.request('admin', admin)['settings'], settings)
        self.assertEqual(self.request('account', self.login(editor_code))['role'], 'editor')
        self.assertTrue(Path(result['output']).is_file())
        second_root = self.root / 'Новое дерево'
        self.request('admin/settings', admin, {**settings, 'itd_root': str(second_root)})
        editor = self.login(editor_code)
        self.assertEqual(self.request('files/plan', editor, {'project_id': project_id})['plan']['actions'], [])
        self.assertTrue(Path(original['project_path']).is_file())
        new_statement = self.request('statement', editor, {'project_id': project_id})
        self.assertTrue(Path(new_statement['output']).is_relative_to(second_root))

    def test_reads_remain_available_while_writer_holds_workspace_lock(self):
        # Request runs in another thread while this thread owns the write lock.
        with self.server.workspace_scope():
            self.assertEqual(self.request('status', self.admin)['database'], 'ready')
            self.assertEqual(self.request('account', self.admin)['role'], 'admin')

    def test_project_revision_skips_unchanged_data_and_detects_external_write(self):
        with connect(self.database) as c:
            oid=add_object(c, 'Revision test')
            pid=add_project(c, object_id=oid, section_code='ЭОМ', code='REV', name='Revision')
        first=self.request('project?project_id='+str(pid),self.admin)
        revision=first['_revision']
        unchanged=self.request(f'project?project_id={pid}&revision={revision}&poll=1',self.admin)
        self.assertTrue(unchanged['unchanged'])
        self.assertNotIn('resources',unchanged)
        with connect(self.database) as c:
            c.execute('UPDATE projects SET name=? WHERE id=?',('Updated',pid))
        changed=self.request(f'project?project_id={pid}&revision={revision}&poll=1',self.admin)
        self.assertEqual(changed['project']['name'],'Updated')
        self.assertNotEqual(changed['_revision'],revision)

    def test_expired_session_response_is_distinct_from_role_denial(self):
        self.server.accounts.clear_sessions()
        expired=self.request('account',self.admin,status=403)
        self.assertTrue(expired['session_expired'])
        self.admin=self.login(self.code)
        _,code=self.add_user('viewer')
        denied=self.request('admin',self.login(code),status=403)
        self.assertFalse(denied['session_expired'])

    def test_slow_response_does_not_keep_sqlite_read_transaction(self):
        from concurrent.futures import ThreadPoolExecutor
        from unittest.mock import patch
        from itd.web import Handler
        with connect(self.database) as c:
            oid=add_object(c,'Slow response')
            pid=add_project(c,object_id=oid,section_code='ЭОМ',code='SLOW',name='Slow')
        entered=threading.Event();release=threading.Event()
        original=Handler.send_bytes
        def slow(handler,*args,**kwargs):
            if handler.path.startswith('/api/project?') and not getattr(handler,'_defer_response',False):
                entered.set()
                release.wait(5)
            return original(handler,*args,**kwargs)
        def write():
            with connect(self.database) as c:
                c.execute('UPDATE objects SET name=? WHERE id=?',('Updated while downloading',oid))
        with patch.object(Handler,'send_bytes',slow),ThreadPoolExecutor(max_workers=2) as pool:
            response=pool.submit(self.request,f'project?project_id={pid}',self.admin)
            try:
                self.assertTrue(entered.wait(2))
                pool.submit(write).result(timeout=2)
            finally:
                release.set()
            self.assertEqual(response.result()['project']['id'],pid)
