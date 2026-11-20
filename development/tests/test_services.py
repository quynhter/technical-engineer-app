"""Service authorization, read boundaries, safe audit and migration compatibility."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from itd.db import initialize, connect, add_object, add_project
from itd.services.context import Actor, ServiceContext, current_actor
from itd.services.operations import execute_cli, execute_web
from itd.services.permissions import (CLI_COMMANDS, WEB_READS, WEB_POSTS, WORKSPACE_ACTIONS,
                                      cli_policy, web_policy, require)
from itd.services.queries import query_web


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='itd-services-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ctx = ServiceContext(database=self.root / 'test.db', root=self.root / 'ИТД')
        initialize(self.ctx.database)
        with connect(self.ctx.database) as c:
            oid = add_object(c, 'Тестовый объект')
            self.pid = add_project(c, object_id=oid, section_code='ЭОМ', code='TEST', name='Тест')

    def actor(self, role, source='web'):
        return Actor(user_id=73, role=role, source=source,
                     on_behalf_of=73 if source in ('assistant', 'mcp', 'cli-agent') else None)

    def dump(self):
        with closing(sqlite3.connect(self.ctx.database)) as c:
            return '\n'.join(c.iterdump())

    def test_role_matrix_for_every_declared_cli_and_http_operation(self):
        for command in CLI_COMMANDS:
            args = SimpleNamespace(command=command, apply=False, action='context')
            policy = cli_policy(args)
            for role in ('viewer', 'editor', 'admin'):
                actor = self.actor(role)
                with self.subTest(command=command, role=role):
                    if {'viewer': 0, 'editor': 1, 'admin': 2}[role] >= {'viewer': 0, 'editor': 1, 'admin': 2}[policy.role]:
                        require(actor, policy.role)
                    else:
                        with self.assertRaises(PermissionError):
                            execute_cli(self.ctx, actor, args)
        for route in set(WEB_READS) | WEB_POSTS:
            read = route in WEB_READS
            policy = web_policy(route, {'action': 'context'}, read=read)
            for role in ('viewer', 'editor', 'admin'):
                actor = self.actor(role)
                with self.subTest(route=route, role=role):
                    if {'viewer': 0, 'editor': 1, 'admin': 2}[role] >= {'viewer': 0, 'editor': 1, 'admin': 2}[policy.role]:
                        require(actor, policy.role)
                    else:
                        with self.assertRaises(PermissionError):
                            if read:
                                query_web(self.ctx, actor, route, {})
                            else:
                                execute_web(self.ctx, actor, route, {'action': 'context'})

    def test_read_services_preserve_every_business_table(self):
        before = self.dump()
        self.assertTrue(query_web(self.ctx, self.actor('viewer'), '/api/bootstrap', {})['objects'])
        result = execute_cli(self.ctx, self.actor('viewer', 'cli'),
                             SimpleNamespace(command='list', entity='objects', project_id=None))
        self.assertEqual(len(result), 1)
        self.assertEqual(before, self.dump())

    def test_cli_and_web_actions_share_actor_permissions(self):
        before = self.dump()
        for source in ('web', 'cli', 'cli-agent', 'mcp', 'assistant'):
            actor = self.actor('viewer', source)
            with self.assertRaises(PermissionError):
                execute_web(self.ctx, actor, '/api/action',
                            {'project_id': self.pid, 'action': 'resource-add',
                             'data': {'role': 'admin'}})
        self.assertEqual(before, self.dump())
        request = {'project_id': self.pid, 'action': 'context', 'data': {}}
        self.assertIn('supplies', execute_web(self.ctx, self.actor('viewer'), '/api/action', request))

    def test_service_audit_has_actor_and_no_payload_or_personal_data(self):
        secret = 'private-name-and-document-content'
        result = execute_cli(self.ctx, self.actor('editor', 'cli-agent'),
                             SimpleNamespace(command='object-add', name=secret))
        self.assertGreater(result['id'], 0)
        with connect(self.ctx.database) as c:
            rows = [dict(row) for row in c.execute('SELECT * FROM audit_events')]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['actor_id'], '73')
        self.assertEqual(rows[0]['on_behalf_of'], '73')
        self.assertEqual(rows[0]['source'], 'cli-agent')
        self.assertEqual(rows[0]['actor_role'], 'editor')
        self.assertEqual(rows[0]['result'], 'success')
        self.assertEqual(rows[0]['entity'], 'objects')
        self.assertEqual(rows[0]['entity_id'], result['id'])
        self.assertNotIn(secret, json.dumps(rows))
        self.assertIsNone(rows[0]['after_json'])
        self.assertIsNone(current_actor.get())

    def test_context_controls_database_and_actor_does_not_leak_after_failure(self):
        other = self.root / 'must-not-exist.db'
        execute_cli(self.ctx, self.actor('editor', 'cli'),
                    SimpleNamespace(command='object-add', name='Объект', db=other))
        self.assertFalse(other.exists())
        before = self.dump()
        with self.assertRaises(ValueError):
            execute_cli(self.ctx, self.actor('editor', 'cli'),
                        SimpleNamespace(command='object-add', name=''))
        self.assertEqual(before, self.dump())
        self.assertIsNone(current_actor.get())

    def test_migration_023_upgrades_022_without_rewriting_history(self):
        from itd.db import MIGRATIONS
        path = self.root / 'older.db'
        with closing(sqlite3.connect(path)) as c:
            c.execute('CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL)')
            for migration in sorted(MIGRATIONS.glob('*.sql')):
                if int(migration.name[:3]) >= 23:
                    continue
                c.executescript(migration.read_text())
                c.execute('INSERT INTO schema_migrations VALUES(?,?)',
                          (int(migration.name[:3]), migration.name))
                c.commit()
            c.execute("INSERT INTO audit_events(operation,after_json) VALUES('historic','{}')")
            c.commit()
        initialize(path)
        initialize(path)
        with connect(path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM audit_events').fetchone()[0], 1)
            self.assertIsNone(c.execute('SELECT actor_id FROM audit_events').fetchone()[0])
            self.assertEqual(c.execute('SELECT max(version) FROM schema_migrations').fetchone()[0], 23)

    def test_unknown_operations_and_missing_agent_delegation_are_rejected(self):
        with self.assertRaises(ValueError):
            execute_cli(self.ctx, self.actor('admin'), SimpleNamespace(command='raw-sql'))
        with self.assertRaises(ValueError):
            Actor(user_id=73, role='editor', source='assistant')
        with self.assertRaises(ValueError):
            Actor(user_id=73, role='owner', source='web')
        with self.assertRaises(ValueError):
            execute_cli(self.ctx, self.actor('admin'),
                        SimpleNamespace(command='list', entity='objects UNION SELECT 1', project_id=None))
        with self.assertRaises(PermissionError):
            execute_cli(self.ctx, self.actor('viewer'),
                        SimpleNamespace(command='list', entity='audit_events', project_id=None))

    def test_each_mutating_workspace_action_rejects_viewer_before_payload_io(self):
        reads = {'context', 'delete-preview', 'resource-import-preview'}
        for action in set(WORKSPACE_ACTIONS) - reads:
            with self.subTest(action=action), self.assertRaises(PermissionError):
                execute_cli(self.ctx, self.actor('viewer', 'cli'),
                            SimpleNamespace(command='workspace-action', action=action,
                                            project_id=self.pid, data=self.root / 'missing.json'))

    def test_account_mutations_require_admin_and_do_not_call_storage_on_denial(self):
        from itd.services.accounts import execute
        from unittest.mock import Mock
        accounts = Mock(path=self.root / 'accounts.sqlite3')
        for name in ('list', 'create', 'role', 'delete', 'rotate-user'):
            with self.subTest(operation=name), self.assertRaises(PermissionError):
                execute(accounts, self.actor('editor'), name, {'role': 'admin'})
        self.assertEqual(accounts.mock_calls, [])

    def test_transports_have_no_business_sql_and_services_have_no_http_imports(self):
        import ast
        root = Path(__file__).resolve().parents[2] / 'app/itd'
        for name in ('web.py', '__main__.py'):
            tree = ast.parse((root / name).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ('execute', 'executescript'):
                    self.assertIsInstance(node.args[0], ast.Constant)
                    self.assertTrue('schema_migrations' in node.args[0].value or 'sqlite_master' in node.args[0].value)
        for path in (root / 'services').glob('*.py'):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or '').startswith(('http', 'itd.web')))

    def test_knowledge_status_rejects_corrupt_binary_without_opening_business_db(self):
        from itd.services import knowledge as service
        from itd.integrity import manifest_entries
        import hashlib
        root = self.root / 'ai/knowledge'
        root.mkdir(parents=True)
        pdf = root / 'original.pdf'
        pdf.write_bytes(b'%PDF-original')
        expected = hashlib.sha256(pdf.read_bytes()).hexdigest()
        (self.root / 'ai/knowledge-integrity.sha256').write_text(expected + '  ai/knowledge/original.pdf\n')
        pdf.write_bytes(b'%PDF-corrupted')
        database = self.root / 'never-created.db'
        with patch.object(service, 'ROOT', self.root), patch.object(service.knowledge, 'default_root', return_value=root):
            with self.assertRaisesRegex(ValueError, 'целостность'):
                execute_cli(ServiceContext(database=database), self.actor('viewer', 'cli'),
                            SimpleNamespace(command='knowledge-status', root=root))
        self.assertFalse(database.exists())

    def test_existing_export_audit_upgrades_without_business_writes(self):
        from itd.read_audit import record
        from itd.services.context import scope
        sidecar = Path(str(self.ctx.database) + '.audit.sqlite3')
        with closing(sqlite3.connect(sidecar)) as c:
            c.execute('''CREATE TABLE read_events(id INTEGER PRIMARY KEY,created_at TEXT,
                operation TEXT NOT NULL,project_id INTEGER NOT NULL,release_ids TEXT NOT NULL,
                source TEXT NOT NULL,user_id INTEGER)''')
            c.execute("INSERT INTO read_events VALUES(1,'old','package-export',1,'[]','cli',NULL)")
            c.commit()
        before = self.dump()
        with scope(self.ctx, self.actor('editor', 'assistant')):
            record(self.ctx.database, 'package-export', project_id=self.pid, release_ids=[],
                   source='assistant', user_id=73)
        self.assertEqual(before, self.dump())
        with closing(sqlite3.connect(sidecar)) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM read_events').fetchone()[0], 2)
            self.assertEqual(c.execute('SELECT actor_id,actor_role,on_behalf_of,result FROM read_events WHERE id=2').fetchone(),
                             ('73', 'editor', '73', 'success'))


if __name__ == '__main__':
    unittest.main()
