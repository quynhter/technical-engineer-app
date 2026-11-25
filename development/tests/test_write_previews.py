"""Write proposals through the real catalogue and transports, using disposable data."""
import asyncio
import base64
from contextlib import closing
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from docx import Document
from fastapi.testclient import TestClient
from openpyxl import Workbook

from itd import db, tools
from itd.assistant_runtime import Runtime
from itd.http_api import create_app
from itd.mcp_server import create_app as mcp_app
from itd.read_audit import sidecar_path
from itd.server_state import WorkspaceState
from itd.services import previews
from itd.services.context import Actor, ServiceContext, accounts_namespace
from itd.resources import CATEGORIES


PROFILE = {'protocol': 'chat', 'base_url': 'http://127.0.0.1:1/v1', 'api_key': 'fixture'}
VERSIONS = {'knowledge_version': 'test-knowledge', 'skills_version': 'test-skills',
            'index_status': 'missing'}
ENDPOINT = '/api/v1/write-previews'


def file(name, data):
    return {'name': name, 'content': base64.b64encode(data).decode('ascii')}


class WritePreviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='itd-proposals-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.state = WorkspaceState(self.root / 'test.db')
        self.state.templates = self.root / 'templates'
        self.state.templates.mkdir()
        self.state.prepare()
        self.database = self.state.database
        self.ctx = ServiceContext(database=self.database, templates=self.state.templates,
                                  accounts_namespace=accounts_namespace(self.state.accounts.path))
        with db.connect(self.database) as c:
            oid = db.add_object(c, 'Учебный объект')
            self.pid = db.add_project(c, object_id=oid, section_code='ЭОМ', code='P', name='Раздел РД')
            self.other_pid = db.add_project(c, object_id=oid, section_code='СС', code='Q', name='Соседний раздел')
        self.uid, self.headers = self.account('editor')
        self.viewer_id, self.viewer_headers = self.account('viewer')
        self.other_id, self.other_headers = self.account('editor')
        self.assistant = Actor(source='assistant', role='editor', user_id=self.uid, on_behalf_of=self.uid)
        self.web = Actor(source='web', role='editor', user_id=self.uid)
        for target in ('itd.tools.versions', 'itd.mcp_server.versions'):
            mock = patch(target, return_value=VERSIONS)
            mock.start()
            self.addCleanup(mock.stop)
        self.client = TestClient(create_app(self.state), base_url='http://127.0.0.1:8080')
        self.addCleanup(self.client.close)

    def account(self, role):
        result = self.state.accounts.create({'role': role, 'first_name': 'Тест', 'last_name': 'РД'})
        return result['user']['id'], {'X-ITD-Token': self.state.accounts.login(result['code'])['session']}

    def dump(self):
        with previews.read_only(self.database) as c:
            return tuple(c.iterdump())

    def propose(self, name='resources', rows=None, **extra):
        packet = {'project_id': self.pid, **extra}
        if name != 'specification':
            packet['rows'] = rows if rows is not None else [self.resource('Позиция 1')]
        result = tools.invoke(self.ctx, self.assistant if name != 'specification' else
                              self.assistant.model_copy(update={'source': 'mcp'}),
                              'preview-' + name, packet)
        self.assertIn('data', result)
        self.assertTrue(result['data']['dry_run'])
        return result['data']

    def resource(self, name):
        return {'operation': 'add', 'name': name, 'unit': 'шт', 'category': CATEGORIES[0]}

    def view(self, proposal, *, headers=None, project_id=None):
        return self.client.get(ENDPOINT, headers=headers or self.headers,
                               params={'project_id': project_id or proposal['project_id'],
                                       'preview_id': proposal['preview_id']})

    def confirmation(self, proposal):
        response = self.view(proposal)
        self.assertEqual(response.status_code, 200, response.text)
        return {key: response.json()[key] for key in ('preview_id', 'project_id', 'preview_hash')}

    def apply(self, proposal, *, headers=None, **overrides):
        return self.client.post(ENDPOINT + '/apply', headers=headers or self.headers,
                                json={**self.confirmation(proposal), **overrides})

    def test_assistant_prepares_a_document_with_a_selected_template_record(self):
        from itd.acts import build_context
        from itd.participants import add_organization
        from itd.services.documents import mutate

        document = Document()
        document.add_paragraph('{{ company }}')
        buffer = BytesIO()
        document.save(buffer)
        original = file('Шаблон.docx', buffer.getvalue())
        expression = '{{ $db.organizations.full_name }}, ИНН: {{ $db.organizations.inn }}'
        field = {'key': 'company', 'kind': 'literal', 'expression': True, 'value': expression}
        with db.connect(self.database) as c:
            oid = c.execute('SELECT object_id FROM projects WHERE id=?', (self.pid,)).fetchone()[0]
            org = add_organization(c, full_name='Строймонтаж', inn='7700000053')
            c.execute('INSERT INTO object_participants(object_id,org_id,role_key) VALUES (?,?,?)',
                      (oid, org, 'contractor'))
            code = mutate(c, '/api/templates/save', {
                'project_id': self.pid, 'name': 'Шаблон', 'original_name': original['name'],
                'form_set': 'СП', 'content': original['content'], 'fields': [field],
            }, self.ctx)['code']

        result = tools.invoke(self.ctx, self.assistant, 'project-records', {'project_id': self.pid})
        source = next(item['source'] for item in result['data']['binding_sources']
                      if item['group'] == 'Организации' and item['value'] == '7700000053')
        identity = source.split('.')[2]
        proposal = self.propose('documents', [{
            'operation': 'add', 'act_type': code,
            'fields': [{**field, 'value': expression.replace('organizations.', f'organizations.{identity}.')}],
        }])
        self.assertTrue(proposal['applicable'], proposal['checks'])
        self.assertEqual(self.apply(proposal).status_code, 200)
        with db.connect(self.database) as c:
            aid = c.execute('SELECT id FROM acts WHERE act_type=?', (code,)).fetchone()[0]
            self.assertEqual(build_context(c, aid, draft=False)['context']['company'],
                             'Строймонтаж, ИНН: 7700000053')

    def test_preview_keeps_db_bytes_and_rows_and_web_applies_exactly_once(self):
        before = self.dump(), hashlib.sha256(self.database.read_bytes()).digest()
        prepared = self.propose(rows=[self.resource('Первый'), self.resource('Второй')])
        self.assertTrue(prepared['applicable'])
        self.assertEqual([x['action'] for x in prepared['changes']], ['insert', 'insert'])
        self.assertNotIn('preview_hash', prepared)
        self.assertEqual(before, (self.dump(), hashlib.sha256(self.database.read_bytes()).digest()))
        proposed = self.client.get(ENDPOINT, params={'project_id': self.pid}, headers=self.headers).json()
        self.assertEqual([x['preview_id'] for x in proposed['previews']], [prepared['preview_id']])
        self.assertEqual(self.apply(prepared).status_code, 200)
        repeated = self.apply(prepared)
        self.assertEqual(repeated.status_code, 400)
        self.assertEqual(repeated.json()['error']['code'], 'preview_conflict')
        self.assertIn('уже применён', repeated.text)
        with db.connect(self.database) as c:
            self.assertEqual([r[0] for r in c.execute('SELECT name FROM resources ORDER BY id')], ['Первый', 'Второй'])
            receipt = c.execute('SELECT * FROM audit_events WHERE preview_id=?',
                                (prepared['preview_id'],)).fetchall()
            self.assertEqual(len(receipt), 1)
            self.assertEqual((receipt[0]['source'], receipt[0]['actor_id']), ('web', str(self.uid)))
            self.assertEqual({key: receipt[0][key] for key in VERSIONS}, VERSIONS)
        with previews.read_only(sidecar_path(self.database)) as c:
            made, rejected = c.execute('SELECT * FROM read_events ORDER BY id').fetchall()
            self.assertEqual((made['source'], made['result'], made['preview_id']),
                             ('assistant', 'success', prepared['preview_id']))
            self.assertEqual((rejected['source'], rejected['result']), ('web', 'rejected'))
            self.assertEqual({key: made[key] for key in VERSIONS}, VERSIONS)

    def test_preview_list_excludes_receipts_before_limiting_results(self):
        draft = self.propose()
        identities = [f'{i:032x}' for i in range(1, 101)]
        path = previews.proposal_path(self.database)
        with closing(sqlite3.connect(path)) as c, c:
            c.executemany('''INSERT INTO write_previews
                SELECT ?, namespace, owner, project_id, expires_at+1, hash, payload, view
                FROM write_previews WHERE id=?''', ((identity, draft['preview_id']) for identity in identities))
        with db.connect(self.database) as c:
            c.executemany("INSERT INTO audit_events(operation,preview_id) VALUES('fixture',?)",
                          ((identity,) for identity in identities))
        response = self.client.get(ENDPOINT, params={'project_id': self.pid}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([p['preview_id'] for p in response.json()['previews']], [draft['preview_id']])
        self.assertNotIn('changes', response.json()['previews'][0])

    def test_bindings_hash_expiry_and_stale_changes(self):
        draft = self.propose()
        self.assertEqual(self.view(draft, headers=self.other_headers).status_code, 400)
        self.assertEqual(self.view(draft, headers=self.viewer_headers).status_code, 403)
        self.assertEqual(self.view(draft, project_id=self.other_pid).status_code, 400)
        self.assertEqual(self.apply(draft, headers=self.other_headers).status_code, 400)
        self.assertEqual(self.apply(draft, project_id=self.other_pid).status_code, 400)
        self.assertIn('Хеш предпросмотра', self.apply(draft, preview_hash='0'*64).text)
        with patch.object(previews, 'TTL', -1):
            expired = self.propose()
        self.assertIn('Срок предпросмотра истёк', self.apply(expired).text)

        other = self.root / 'other.db'
        with previews.read_only(self.database) as src, closing(sqlite3.connect(other)) as target:
            src.backup(target)
        other_ctx = self.ctx.model_copy(update={'database': other})
        with self.assertRaisesRegex(ValueError, 'недоступен'):
            previews.apply(other_ctx, self.web, self.confirmation(draft))
        with db.connect(self.database) as c:
            c.execute('UPDATE projects SET name=? WHERE id=?', ('Поздняя правка', self.pid))
        response = self.apply(draft)
        self.assertIn('Данные изменились', response.text)
        with db.connect(self.database) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM resources').fetchone()[0], 0)

    def test_batch_and_receipt_roll_back_on_second_row_and_audit_failure(self):
        proposed = self.propose(rows=[self.resource('Первая'), self.resource('Сбой')])
        with db.connect(self.database) as c:
            c.execute("""CREATE TRIGGER test_fail_row BEFORE INSERT ON resources WHEN new.name='Сбой'
                BEGIN SELECT RAISE(ABORT, 'fixture'); END""")
        before = self.dump()
        self.assertEqual(self.apply(proposed).status_code, 400)
        self.assertEqual(self.dump(), before)
        with db.connect(self.database) as c:
            c.execute('DROP TRIGGER test_fail_row')
            c.execute("""CREATE TRIGGER test_fail_audit BEFORE INSERT ON audit_events WHEN new.preview_id IS NOT NULL
                BEGIN SELECT RAISE(ABORT, 'fixture'); END""")
        before = self.dump()
        self.assertEqual(self.apply(proposed).status_code, 400)
        self.assertEqual(self.dump(), before)
        with db.connect(self.database) as c:
            c.execute('DROP TRIGGER test_fail_audit')
        self.assertEqual(self.apply(proposed).status_code, 200)

    def test_preview_audit_failure_rolls_back_proposal_storage(self):
        before = self.dump()
        with patch('itd.tools.record', side_effect=OSError('private audit failure')):
            with self.assertRaises(OSError):
                self.propose()
        self.assertEqual(self.dump(), before)
        result = self.client.get(ENDPOINT, headers=self.headers, params={'project_id': self.pid})
        self.assertEqual(result.json(), {'previews': []})

    def test_batch_validation_shows_good_and_invalid_rows_without_permission_to_apply(self):
        draft = self.propose('schemes', [{'operation': 'add', 'num': '1', 'name': 'Разрез'},
                                          {'operation': 'edit', 'id': 5678, 'changes': {'name': 'нет'}}])
        self.assertFalse(draft['applicable'])
        self.assertEqual([check['status'] for check in draft['checks']], ['ok', 'error'])
        self.assertEqual(draft['changes'][0]['table'], 'schemes')
        self.assertEqual(self.apply(draft).status_code, 400)
        self.assertNotIn('Разрез', '\n'.join(self.dump()))

    def test_real_catalogue_cannot_use_confirmation_arguments_for_assistant_or_mcp(self):
        draft = self.propose()
        confirmation = self.confirmation(draft)
        before = self.dump()
        for source in ('assistant', 'mcp'):
            actor = self.assistant.model_copy(update={'source': source})
            with self.assertRaises(PermissionError):
                previews.apply(self.ctx, actor, confirmation)
            for tool in tools.available(actor):
                with self.subTest(source=source, tool=tool.name):
                    self.assertIn('error', tools.invoke(self.ctx, actor, tool.name, confirmation))
                    if tool.access == 'write':
                        self.assertEqual(tool.role, 'editor')
                        self.assertIs(tool.schema()['additionalProperties'], False)
        self.assertEqual(self.dump(), before)
        self.assertFalse(self.view(draft).json()['applied'])

    def test_mcp_editor_preview_web_session_only_and_token_rechecks(self):
        token = self.state.accounts.create_token(self.uid, {'name': 'MCP', 'expires_at': time.time()+3600})
        headers = {'Authorization': 'Bearer ' + token['token'],
                   'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-06-18'}
        packet = {'name': 'preview-resources',
                  'arguments': {'project_id': self.pid, 'rows': [self.resource('Из MCP')]}}
        with TestClient(mcp_app(self.ctx, self.state.accounts), base_url='http://127.0.0.1:8766') as client:
            def rpc(method, params=None, *, auth=headers):
                return client.post('/mcp', headers=auth,
                                   json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})
            listed = rpc('tools/list').json()['result']['tools']
            self.assertEqual({row['name'] for row in listed}, {tool.name for tool in tools.available(self.assistant)})
            draft = rpc('tools/call', packet).json()['result']['structuredContent']['data']
            self.assertEqual(draft['source'], 'mcp')
            confirmation = self.confirmation(draft)
            self.assertTrue(rpc('tools/call', {'name': 'apply-preview', 'arguments': confirmation})
                            .json()['result']['isError'])
            self.assertTrue(rpc('tools/call', {'name': 'preview-resources', 'arguments': confirmation})
                            .json()['result']['isError'])
            self.assertEqual(self.client.post(ENDPOINT+'/apply', headers=headers, json=confirmation).status_code, 403)
            self.assertFalse(self.view(draft).json()['applied'])
            with self.state.accounts.connect() as c, c:
                c.execute("UPDATE users SET role='viewer' WHERE id=?", (self.uid,))
            self.assertNotIn('preview-resources', {t['name'] for t in rpc('tools/list').json()['result']['tools']})
            self.assertEqual(rpc('tools/call', packet).json()['result']['structuredContent']['error']['code'],
                             'forbidden')
            with self.state.accounts.connect() as c, c:
                c.execute("UPDATE users SET role='editor' WHERE id=?", (self.uid,))
            self.state.accounts.revoke_token(token['id'])
            self.assertEqual(rpc('tools/call', packet).status_code, 401)
        self.assertEqual(self.apply(draft).status_code, 200)

    def test_assistant_attachment_uses_its_own_chat_and_never_applies(self):
        runtime = Runtime(self.state.accounts)
        root = Actor(source='web', role='admin', user_id=1)
        aid = runtime.chats.save(root, {'name': 'Инженер', 'provider': 'test', 'model': 'test'},
                                 {'test': PROFILE})['id']
        source = 'Позиция;Наименование;Ед. изм.;Количество;Документ\n1;Кабель;м;2,5;РД ЭОМ'.encode()
        before = self.dump()
        round_tools = []

        async def provider(profile, model, system, messages, permitted):
            round_tools.append([tool.name for tool in permitted])
            if len(round_tools) == 1:
                metadata = json.loads(messages[-1]['content'].split('):\n', 1)[-1])[0]
                self.assertNotIn('content', metadata)
                self.assertEqual(metadata['sha256'], hashlib.sha256(source).hexdigest())
                yield 'call', {'name': 'preview-specification', 'id': 'tool-1',
                               'arguments': {'project_id': self.pid,
                                             'attachment': {'attachment_id': metadata['id']},
                                             'category': CATEGORIES[0]}}
            elif len(round_tools) == 2:
                draft = json.loads(messages[-1]['content'])['data']
                self.assertTrue(draft['applicable'])
                yield 'call', {'name': 'apply-preview', 'id': 'tool-2',
                               'arguments': {'project_id': self.pid, 'preview_id': draft['preview_id']}}
            else:
                self.assertIn('error', json.loads(messages[-1]['content']))
                yield 'delta', 'Откройте предпросмотр'

        async def run():
            thread = runtime.chats.create(self.ctx, self.assistant,
                                          {'assistant_id': aid, 'project_id': self.pid})
            with patch('itd.llm.profiles', return_value={'test': PROFILE}), patch('itd.llm.stream', provider):
                out = await runtime.start(self.ctx, self.assistant,
                    {'thread_id': thread['id'], 'text': '', 'request_key': 'key',
                     'attachments': [{'name': 'spec.csv', 'data': file('spec.csv', source)['content']}]},
                    lambda: self.assistant)
                await runtime.tasks[out['message_id']]
            return runtime.chats.history(self.ctx, self.assistant, thread['id'])['messages'][-1]

        message = asyncio.run(run())
        self.assertEqual(message['status'], 'complete', message)
        self.assertNotIn('apply-preview', round_tools[0])
        self.assertIn('preview-specification', round_tools[0])
        draft = message['tool_calls'][0]['result']['data']
        self.assertEqual(draft['specification']['rows'][0]['quantity'], 2.5)
        self.assertIn('error', message['tool_calls'][1]['result'])
        self.assertEqual(before, self.dump())
        self.assertFalse((self.root/'archive').exists())
        self.assertEqual(self.apply(draft).status_code, 200)

    def test_bad_attachments_and_size_limits_are_rejected(self):
        from itd.assistant_files import MAX_BYTES, MAX_TEXT, read_attachments
        actor = self.assistant.model_copy(update={'source': 'mcp'})
        cases = [('not.pdf', b'%PDF-1.6\ninvalid'), ('cp1251.txt', b'\xff'),
                 ('large.txt', b'x'*(MAX_BYTES+1)), ('text.txt', b'x'*(MAX_TEXT+1))]
        for name, blob in cases:
            with self.subTest(name=name):
                packet = file(name, blob)
                result = tools.invoke(self.ctx, actor, 'preview-specification',
                                      {'project_id': self.pid, 'attachment': packet})
                self.assertIn('error', result)
                with self.assertRaises(ValueError):
                    read_attachments([{'name': name, 'data': packet['content']}])
        self.assertFalse(previews.proposal_path(self.database).exists())

    def test_xlsx_preserves_positions_pending_rows_and_original_sha256(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Спецификация'
        sheet.append(['Поз.', 'Наименование', 'Ед. изм.', 'Количество', 'Норма'])
        sheet.append(['1', 'Кабель', 'м', 12.5, 'РД ЭОМ'])
        sheet.append(['2', 'Крепление', 'шт', None, None])
        raw = BytesIO()
        workbook.save(raw)
        workbook.close()
        original = raw.getvalue()
        proposed = self.propose('specification', attachment=file('spec.xlsx', original), category=CATEGORIES[0])
        view = proposed['specification']
        self.assertEqual(view['file']['sha256'], hashlib.sha256(original).hexdigest())
        first, second = view['rows']
        self.assertEqual((first['sheet'], first['quantity'], first['reference']),
                         ('Спецификация', 12.5, 'РД ЭОМ'))
        self.assertIn('количество', second['missing'])
        self.assertIn('Строка не добавится', proposed['warnings'][0]['message'])
        self.assertFalse((self.root/'archive').exists())
        with patch('itd.services.previews.record_applied', side_effect=sqlite3.OperationalError('sqlite')):
            self.assertEqual(self.apply(proposed).status_code, 400)
        self.assertFalse(list((self.root/'archive').rglob('*.xlsx')))
        self.assertFalse(list((self.root/'storage').glob('*')))
        self.assertEqual(self.apply(proposed).status_code, 200)
        with db.connect(self.database) as c:
            self.assertEqual(tuple(c.execute('SELECT spec_num,name,qty_proj,note FROM resources').fetchone()),
                             ('1', 'Кабель', 12.5, 'РД ЭОМ'))
            self.assertEqual(c.execute('SELECT count(*) FROM resources').fetchone()[0], 1)
            self.assertEqual(c.execute("SELECT count(*) FROM specification_pending WHERE status='pending'").fetchone()[0], 1)
            attachment = c.execute('SELECT * FROM attachments').fetchone()
            self.assertEqual(attachment['sha256'], view['file']['sha256'])
            self.assertEqual((self.root/'archive'/attachment['storage_path']).read_bytes(), original)
        with previews.read_only(sidecar_path(self.database)) as c:
            self.assertNotIn('Крепление', '\n'.join(c.iterdump()))

    def test_cable_record_and_uploaded_template_reuse_native_forms(self):
        work = self.propose('cable-works', [{'operation': 'save', 'title': 'Прокладка',
                            'work_fields': {'mark': 'ВВГ', 'line_number': 'Л-1'}, 'entry_date': '2026-11-25'}])
        self.assertTrue(work['applicable'], work)
        self.assertEqual(self.apply(work).status_code, 200)
        with db.connect(self.database) as c:
            self.assertEqual(c.execute('SELECT work_type FROM workspace_entries').fetchone()[0], 'cable')
        document = Document()
        document.add_paragraph('Работы {{ location }}')
        output = BytesIO()
        document.save(output)
        template = self.propose('document-templates', [{'operation': 'add', 'name': 'Бланк', 'form_set': 'Комплект',
                                'file': file('form.docx', output.getvalue())}])
        self.assertTrue(template['applicable'], template)
        self.assertEqual(list(self.state.templates.iterdir()), [])
        with patch('itd.services.previews.record_applied', side_effect=sqlite3.OperationalError('sqlite')):
            self.assertEqual(self.apply(template).status_code, 400)
        self.assertEqual(list(self.state.templates.iterdir()), [])
        response = self.apply(template)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(next(self.state.templates.iterdir()).read_bytes(), output.getvalue())

    def test_journal_dates_and_quality_link_are_the_same_changes_as_native_forms(self):
        from itd.resources import add_resource
        with db.connect(self.database) as c:
            rid = add_resource(c, project_id=self.pid, name='Ресурс', unit='м', category=CATEGORIES[3])
            c.execute("UPDATE projects SET smr_start='2026-11-25' WHERE id=?", (self.pid,))
        source = self.propose('source-files', [{'operation': 'add', 'doc_type': 'quality',
                                               'file': file('certificate.txt', b'fixture certificate')}])
        self.assertEqual(self.apply(source).status_code, 200)
        with db.connect(self.database) as c:
            attachment = c.execute('SELECT id FROM attachments').fetchone()[0]
        review = self.propose('quality-reviews', [{'operation': 'add', 'resource_id': rid,
                              'attachment_id': attachment, 'status': 'matches', 'checked_by': 'Проверяющий',
                              'checked_date': '2026-11-24', 'source': 'Документ качества', 'note': 'Сверено'}])
        self.assertTrue(review['applicable'], review)
        self.assertEqual({item['table'] for item in review['changes']}, {'resource_attachments', 'quality_reviews'})
        self.assertEqual(self.apply(review).status_code, 200)
        incoming = self.propose('incoming-control', [{'operation': 'save', 'date': '2026-11-24',
                                  'resources': [{'resource_id': rid, 'result': 'accepted', 'quantity': 1}]}])
        self.assertTrue(incoming['applicable'], incoming)
        self.assertEqual(incoming['warnings'][0]['dates'][0]['after'], '2026-11-24')
        self.assertEqual(self.apply(incoming).status_code, 200)
        with db.connect(self.database) as c:
            self.assertEqual(c.execute('SELECT smr_start FROM projects WHERE id=?', (self.pid,)).fetchone()[0],
                             '2026-11-24')
            self.assertEqual(c.execute("SELECT kind FROM workspace_entries").fetchone()[0], 'incoming')

    def test_delivery_proposal_rechecks_original_bytes_and_can_be_reprepared(self):
        from itd.releases import register_release
        original = self.root/'final.docx'
        original.write_bytes(b'correct release')
        with db.connect(self.database) as c:
            rid = register_release(c, project_id=self.pid, kind='docx', title='Выпуск', path=original, mode='final')
        packet = [{'operation': 'add', 'release_id': rid, 'recipient': 'Получатель',
                   'event_date': '2026-11-24', 'source': 'Письмо', 'note': 'Передано'}]
        draft = self.propose('deliveries', packet)
        self.assertTrue(draft['applicable'], draft)
        original.write_bytes(b'changed release')
        self.assertEqual(self.apply(draft).status_code, 400)
        with db.connect(self.database) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM deliveries').fetchone()[0], 0)
        original.write_bytes(b'correct release')
        now = self.propose('deliveries', packet)
        self.assertEqual(self.apply(now).status_code, 200)
        with db.connect(self.database) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM delivery_events').fetchone()[0], 1)


class WritePreviewMigrationTests(unittest.TestCase):
    def test_025_upgrade_preserves_024_records_and_enforces_unique_receipt(self):
        with tempfile.TemporaryDirectory(prefix='itd-migration-025-') as folder:
            root = Path(folder)
            old_migrations = root/'migrations'
            old_migrations.mkdir()
            for migration in db.MIGRATIONS.glob('*.sql'):
                if int(migration.name[:3]) <= 24:
                    shutil.copyfile(migration, old_migrations/migration.name)
            database = root/'legacy.db'
            with patch.object(db, 'MIGRATIONS', old_migrations):
                db.initialize(database)
            with db.connect(database) as c:
                oid = db.add_object(c, 'Старый объект')
                c.execute("INSERT INTO audit_events(operation,entity,entity_id) VALUES('legacy','objects',?)", (oid,))
                self.assertEqual(c.execute('SELECT max(version) FROM schema_migrations').fetchone()[0], 24)
            db.initialize(database)
            db.initialize(database)
            with db.connect(database) as c:
                self.assertIsNotNone(c.execute('SELECT 1 FROM schema_migrations WHERE version=25').fetchone())
                self.assertEqual(c.execute('SELECT name FROM objects').fetchone()[0], 'Старый объект')
                self.assertEqual(tuple(c.execute('SELECT operation,preview_id FROM audit_events').fetchone()),
                                 ('legacy', None))
                c.execute("INSERT INTO audit_events(operation,preview_id) VALUES('apply','receipt')")
                with self.assertRaises(sqlite3.IntegrityError):
                    c.execute("INSERT INTO audit_events(operation,preview_id) VALUES('apply','receipt')")
