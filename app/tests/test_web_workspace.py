import base64
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from itd.acts import register_form
from itd.db import connect, initialize
from itd.web import WorkspaceServer, prepare_database, project_data
from itd.workspace import save_entry, save_workspace, snapshot


class WorkspaceFixture:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'itd.db'
        initialize(self.path)

    def payload(self):
        return {'object': {'name': 'Полное название объекта, этап 2', 'construction_type': 'Реконструкция', 'city': 'Нижний Новгород',
                           'work_start': '2026-10-01', 'control_self': 1},
                'participants': [{'full_name': 'Застройщик', 'roles': ['developer'], 'document_roles': ['customer'],
                                  'inn': '0012345678', 'postal_code': '000123', 'email': 'a@example.test',
                                  'representatives': [{'last_name': 'Иванов', 'first_name': 'Иван', 'middle_name': 'Иванович',
                                      'position': 'Инженер', 'authority_type': 'Приказ', 'authority_num': '001',
                                      'authority_date': '2026-10-01', 'document_roles': ['customer_control']}]}],
                'projects': [{'section_code': 'СПС', 'code': 'РД-01-СПС', 'name': 'Сигнализация', 'form_set': 'СП 77.13330.2016'}]}

    def create(self):
        with connect(self.path) as c:
            return save_workspace(c, self.payload())


class WorkspaceTests(WorkspaceFixture, unittest.TestCase):
    def test_sro_certificate_roundtrip_edit_validation_and_document_context(self):
        from itd.changes import update_record
        from itd.participants import participants_context
        data = self.payload()
        data['participants'][0].update(sro_certificate_num='00017/СРО', sro_certificate_date='2026-10-01')
        with connect(self.path) as c:
            saved = save_workspace(c, data)
        org = saved['participants'][0]
        self.assertEqual(org['sro_certificate_num'], '00017/СРО')
        self.assertEqual(org['sro_certificate_date'], '2026-10-01')
        with connect(self.path) as c:
            context = participants_context(c, saved['projects'][0]['id'])
            self.assertEqual(context['organizations']['customer']['sro_certificate_num'], '00017/СРО')
            update_record(c, entity='organizations', record_id=org['id'],
                          changes={'sro_certificate_date': '2026-10-02'},
                          expected={'sro_certificate_date': '2026-10-01'})
        with self.assertRaises(ValueError), connect(self.path) as c:
            update_record(c, entity='organizations', record_id=org['id'],
                          changes={'sro_certificate_date': '2026-02-30'})
        with self.assertRaises(ValueError), connect(self.path) as c:
            save_workspace(c, saved)
        with connect(self.path) as c:
            saved = snapshot(c, saved['object']['id'])
            self.assertEqual(saved['participants'][0]['sro_certificate_date'], '2026-10-02')
            saved['participants'][0].update(sro_certificate_num='', sro_certificate_date='')
            cleared = save_workspace(c, saved)['participants'][0]
            self.assertIsNone(cleared['sro_certificate_num'])
            self.assertIsNone(cleared['sro_certificate_date'])

    def test_sro_upgrade_keeps_existing_requisites_and_backup(self):
        from unittest.mock import patch
        from itd.db import MIGRATIONS
        folder = Path(self.tmp.name) / 'before-sro'
        folder.mkdir()
        for migration in MIGRATIONS.glob('*.sql'):
            if int(migration.name[:3]) < 15:
                (folder / migration.name).write_bytes(migration.read_bytes())
        legacy = Path(self.tmp.name) / 'legacy-sro.db'
        with patch('itd.db.MIGRATIONS', folder):
            initialize(legacy)
        with connect(legacy) as c:
            c.execute("INSERT INTO organizations(full_name,sro_info,sro_inn) VALUES('Организация','Прежняя СРО','0012345678')")
        backup = prepare_database(legacy)
        self.assertTrue(backup.is_file())
        with connect(legacy) as c:
            org = dict(c.execute('SELECT * FROM organizations').fetchone())
            self.assertEqual(org['sro_info'], 'Прежняя СРО')
            self.assertEqual(org['sro_inn'], '0012345678')
            self.assertIsNone(org['sro_certificate_num'])
            self.assertIsNone(org['sro_certificate_date'])
        with connect(backup) as c:
            self.assertEqual(c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0], 14)
        self.assertIsNone(prepare_database(legacy))

    def test_required_fields_are_aggregated_and_have_ui_paths(self):
        from itd.workspace import validate_workspace_required,WorkspaceValidationError
        data={'object':{'name':'  '},'participants':[{'full_name':None,'representatives':[{'position':''}]}],
              'projects':[{'section_code':'ЭОМ','code':'','name':''}]}
        with self.assertRaises(WorkspaceValidationError) as result:validate_workspace_required(data)
        error=result.exception
        self.assertTrue(str(error).startswith('Пожалуйста, заполните поля:'))
        self.assertEqual(error.fields[0],{'path':'object.name','label':'Полное наименование объекта'})
        self.assertEqual(len(error.fields),6)
        validate_workspace_required({'object':{'name':'Объект'},'participants':[{'full_name':'Организация','representatives':[{'last_name':'Иванов','position':'Инженер'}]}]})

    def test_roundtrip_full_fields_and_no_invented_fact_or_dates(self):
        s = self.create()
        self.assertEqual(s['object']['city'], 'Нижний Новгород')
        self.assertIsNone(s['projects'][0]['city'])
        self.assertEqual(s['participants'][0]['inn'], '0012345678')
        self.assertEqual(s['participants'][0]['postal_code'], '000123')
        r = s['participants'][0]['representatives'][0]
        self.assertEqual(r['fio'], 'Иванов Иван Иванович')
        self.assertEqual(r['order_doc'], 'Приказ № 001 от 2026-10-01')
        self.assertIsNone(s['projects'][0]['smr_start'])
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM resources').fetchone()[0], 0)
            self.assertEqual(snapshot(c, s['object']['id']), s)

    def test_edit_keeps_ids_and_stale_form_cannot_overwrite(self):
        s = self.create()
        stale = json.loads(json.dumps(s))
        s['object']['address'] = 'Новый адрес'
        s['object']['city'] = 'Москва'
        with connect(self.path) as c:
            updated = save_workspace(c, s)
        self.assertEqual(updated['projects'][0]['id'], s['projects'][0]['id'])
        self.assertEqual(updated['object']['city'], 'Москва')
        stale['object']['address'] = 'Старый адрес'
        with self.assertRaisesRegex(ValueError, 'уже изменены'), connect(self.path) as c:
            save_workspace(c, stale)
        with connect(self.path) as c:
            self.assertEqual(snapshot(c, s['object']['id'])['object']['address'], 'Новый адрес')

    def test_legacy_authority_and_distinct_participant_type_are_preserved(self):
        p = self.payload()
        rep = p['participants'][0]['representatives'][0]
        for key in ('authority_type', 'authority_num', 'authority_date'):
            rep.pop(key)
        rep['order_doc'] = 'Доверенность № 17 от 01.10.2026'
        with connect(self.path) as c:
            s = save_workspace(c, p)
        self.assertEqual(s['participants'][0]['roles'], ['developer'])
        self.assertEqual(s['participants'][0]['document_roles'], ['customer'])
        s['participants'][0]['representatives'][0]['first_name'] = 'Пётр'
        with connect(self.path) as c:
            updated = save_workspace(c, s)
        rep = updated['participants'][0]['representatives'][0]
        self.assertEqual(rep['fio'], 'Иванов Пётр Иванович')
        self.assertEqual(rep['order_doc'], 'Доверенность № 17 от 01.10.2026')

    def test_invalid_late_participant_rolls_back_entire_form(self):
        s = self.payload()
        s['participants'][0]['representatives'][0]['authority_date'] = '2026-02-30'
        with self.assertRaises(ValueError), connect(self.path) as c:
            save_workspace(c, s)
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM objects').fetchone()[0], 0)

    def test_foreign_org_and_project_ids_rejected(self):
        a = self.create()
        b = self.create()
        a['participants'][0]['id'] = b['participants'][0]['id']
        with self.assertRaises(ValueError), connect(self.path) as c:
            save_workspace(c, a)
        a = self.create()
        a['projects'][0]['id'] = b['projects'][0]['id']
        with self.assertRaises(ValueError), connect(self.path) as c:
            save_workspace(c, a)

    def test_unknown_and_reversed_dates_rejected(self):
        for bad in ('2026-99-99', '2026-09-01'):
            p = self.payload()
            p['object']['work_end'] = bad
            with self.assertRaises(ValueError), connect(self.path) as c:
                save_workspace(c, p)

    def test_two_reps_keep_their_shared_role_without_implicit_signer(self):
        s = self.payload()
        rep = dict(s['participants'][0]['representatives'][0])
        s['participants'][0]['representatives'].append(rep)
        with connect(self.path) as c:
            saved = save_workspace(c, s)
            reps = saved['participants'][0]['representatives']
            self.assertEqual(len(reps), 2)
            self.assertTrue(all(r['document_roles'] == ['customer_control'] for r in reps))
            from itd.participants import participants_context
            context = participants_context(c, saved['projects'][0]['id'])
            self.assertIsNone(context['signatories']['customer_control'])
            self.assertEqual(len(context['signatory_candidates']['customer_control']), 2)
            saved = save_workspace(c, saved)
            saved['participants'][0]['representatives'][0]['document_roles'] = []
            saved = save_workspace(c, saved)
            self.assertEqual(participants_context(c, saved['projects'][0]['id'])['signatories']['customer_control']['id'], reps[1]['id'])

    def test_journal_revision_and_no_fact_side_effect(self):
        s = self.create()
        pid = s['projects'][0]['id']
        with connect(self.path) as c:
            entry = save_entry(c, pid, {'kind': 'work', 'title': 'Монтаж', 'quantity': None})
        with connect(self.path) as c:
            updated = save_entry(c, pid, {**entry, 'title': 'Монтаж оборудования'})
            self.assertEqual(updated['revision'], 2)
        with self.assertRaises(ValueError), connect(self.path) as c:
            save_entry(c, pid, {**entry, 'title': 'Старая правка'})
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM work_facts').fetchone()[0], 0)

    def test_upgrade_backup_preserves_old_data(self):
        # Воспроизводим БД до новой миграции, не меняя уже применённый SQL.
        old = Path(self.tmp.name) / 'old.db'
        from unittest.mock import patch
        from itd.db import MIGRATIONS
        folder = Path(self.tmp.name) / 'migrations'
        folder.mkdir()
        for f in MIGRATIONS.glob('*.sql'):
            if int(f.name[:3]) < 12:
                (folder / f.name).write_bytes(f.read_bytes())
        with patch('itd.db.MIGRATIONS', folder):
            initialize(old)
        with sqlite3.connect(old) as c:
            c.execute("INSERT INTO objects(name) VALUES('Исходный объект')")
        backup = prepare_database(old)
        self.assertTrue(backup.is_file())
        with sqlite3.connect(backup) as c:
            self.assertEqual(c.execute('SELECT max(version) FROM schema_migrations').fetchone()[0], 11)
        with connect(old) as c:
            self.assertEqual(c.execute('SELECT name FROM objects').fetchone()[0], 'Исходный объект')
        self.assertIsNone(prepare_database(old))

    def test_section_dates_are_separate_and_invalid_partial_edit_rolls_back(self):
        p = self.payload()
        p['object']['construction_type'] = 'Строительство'
        p['projects'][0].update(smr_start='2026-10-02', smr_end='2026-10-10', pnr_start='2026-10-11')
        with connect(self.path) as c:
            s = save_workspace(c, p)
        self.assertEqual(s['projects'][0]['smr_start'], '2026-10-02')
        self.assertEqual(s['object']['work_start'], '2026-10-01')
        self.assertIsNone(s['projects'][0]['pnr_end'])
        s['projects'][0]['smr_start'] = '2026-10-12'
        with self.assertRaisesRegex(ValueError, 'позже'), connect(self.path) as c:
            save_workspace(c, s)
        with connect(self.path) as c:
            self.assertEqual(snapshot(c, s['object']['id'])['projects'][0]['smr_start'], '2026-10-02')


class DocumentCityTests(WorkspaceFixture, unittest.TestCase):
    def test_city_falls_back_to_object_in_editor_and_docx_without_changing_project(self):
        from itd.form_catalog import connect_form
        from itd.acts import add_act, build_context
        saved = self.create()
        pid = saved['projects'][0]['id']
        with connect(self.path) as c:
            connect_form(c, 'СП_77_А_21')
            aid = add_act(c, project_id=pid, act_type='СП_77_А_21')
            self.assertEqual(project_data(c, pid)['form_roots']['project']['city'], 'Нижний Новгород')
            self.assertEqual(build_context(c, aid)['context']['city'], 'Нижний Новгород')
            self.assertIsNone(c.execute('SELECT city FROM projects WHERE id=?', (pid,)).fetchone()[0])
            c.execute('UPDATE projects SET city=? WHERE id=?', ('Казань', pid))
            self.assertEqual(project_data(c, pid)['form_roots']['project']['city'], 'Казань')
            self.assertEqual(build_context(c, aid)['context']['city'], 'Казань')


class HttpTests(WorkspaceFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.server = WorkspaceServer(('127.0.0.1', 0), self.path)
        _, initial_code = self.server.prepare()
        self.session = self.server.accounts.login(initial_code)["session"]
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def test_delete_preview_conflict_and_apply_use_test_database_only(self):
        from itd.resources import add_resource, CATEGORIES
        state=self.create();pid=state['projects'][0]['id']
        with connect(self.path) as c:
            rid=add_resource(c,project_id=pid,name='Удаляемый ресурс',unit='шт',category=CATEGORIES[0])
        packet={'project_id':pid,'action':'delete-preview','data':{'entity':'resources','id':rid}}
        status,body=self.request('/api/action',packet)
        self.assertEqual(status,200)
        plan=json.loads(body)
        with connect(self.path) as c:c.execute('UPDATE resources SET note=? WHERE id=?',('Изменилось',rid))
        packet['action']='delete-apply';packet['data']['token']=plan['token']
        self.assertEqual(self.request('/api/action',packet)[0],400)
        packet['action']='delete-preview';packet['data'].pop('token')
        plan=json.loads(self.request('/api/action',packet)[1])
        packet['action']='delete-apply';packet['data']['token']=plan['token']
        status,body=self.request('/api/action',packet)
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['deleted'],1)
        with connect(self.path) as c:
            self.assertFalse(c.execute('SELECT 1 FROM resources WHERE id=?',(rid,)).fetchone())
            self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchone())

    def test_preview_labels_overrides_tables_and_review_state(self):
        saved = self.create()
        pid = saved['projects'][0]['id']
        from itd.acts import add_act
        with connect(self.path) as c:
            register_form(c, code='СП_77_А_4', name='Проверка кабеля', fields=[
                {'key':'t0_r0_c1','label':'Номер барабана','kind':'literal','required':True,'value':None},
                {'key':'date_0_3','label':'Дата проверки','kind':'reference','source':'act.date_signed','format':'day_2digits'},
                {'key':'rows','label':'Результаты {{ t0_r0_c1 }}','kind':'table','value':None,
                 'fields':[{'key':'c1','label':'Затухание','kind':'reference','source':'item.c1'}]}])
            aid=add_act(c, project_id=pid, act_type='СП_77_А_4', fields=[
                {'key':'t0_r0_c1','kind':'literal','required':True,'value':'0001'}])
        status, body = self.request(f'/api/context?project_id={pid}&act_id={aid}')
        self.assertEqual(status, 200)
        value=json.loads(body)
        self.assertEqual(value['context']['t0_r0_c1'], '0001')
        self.assertEqual(value['preview_fields'][0]['label'], 'Номер барабана')
        self.assertEqual(value['preview_fields'][1]['group'], 'Номер и даты')
        self.assertEqual(value['preview_fields'][2]['label'], 'Результаты')
        self.assertEqual(value['preview_fields'][2]['columns'][0]['label'], 'Затухание')
        self.assertEqual(value['source_issues'], [])
        self.assertFalse(value['review_current'])
        from itd.acts import review_act
        from itd.paths import default_templates
        with connect(self.path) as c:
            review_act(c, aid, default_templates(), 'Тестовая сверка источников')
        _, body = self.request(f'/api/context?project_id={pid}&act_id={aid}')
        self.assertTrue(json.loads(body)['review_current'])
        from itd.changes import update_record
        with connect(self.path) as c:
            update_record(c, entity='acts', record_id=aid,
                          changes={'date_signed': '2026-10-31'}, expected={'date_signed': None})
        _, body = self.request(f'/api/context?project_id={pid}&act_id={aid}')
        self.assertFalse(json.loads(body)['review_current'])
        self.assertEqual(self.request(f'/api/context?project_id={pid+100}&act_id={aid}')[0],400)


    def test_catalog_selection_connects_only_chosen_form_and_preserves_customization(self):
        saved = self.create()
        pid = saved['projects'][0]['id']
        status, body = self.request(f'/api/project?project_id={pid}')
        self.assertEqual(status, 200)
        forms = json.loads(body)['available_forms']
        self.assertTrue(any(f['code'] == 'СП_77_А_4' and f['choice_group'] == 'Комплект раздела' for f in forms))
        self.assertTrue(any(f['code'] == 'И_1_13_07_02' and f['choice_group'] == 'Другие комплекты форм' for f in forms))
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM document_types').fetchone()[0], 0)
        payload = {'project_id':pid, 'act_type':'СП_77_А_4'}
        # Ошибка состава откатывает и регистрацию формы, и создание акта.
        self.assertEqual(self.request('/api/act', {**payload, 'resource_ids':[999999]})[0], 400)
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM document_types').fetchone()[0], 0)
        status, body = self.request('/api/act', payload)
        self.assertEqual(status, 200, body)
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM document_types').fetchone()[0], 1)
            register_form(c, code='СП_77_А_4', name='Согласованное название', fields=[])
        self.assertEqual(self.request('/api/act', payload)[0], 200)
        with connect(self.path) as c:
            row = c.execute('SELECT name,fields FROM document_types WHERE code=?', ('СП_77_А_4',)).fetchone()
            self.assertEqual(row['name'], 'Согласованное название')
            self.assertEqual(json.loads(row['fields']), [])
        self.assertEqual(self.request('/api/act', {**payload, 'act_type':'И_1_13_07_02'})[0], 200)
        self.assertEqual(self.request('/api/act', {**payload, 'act_type':'НЕСУЩЕСТВУЮЩАЯ'})[0], 400)

    def test_create_statement_protocol_and_preserved_a21_from_other_form_sets(self):
        from itd.form_catalog import catalog
        saved = self.create()
        pid = saved['projects'][0]['id']
        _, body = self.request(f'/api/project?project_id={pid}')
        available = json.loads(body)['available_forms']
        self.assertEqual({f['code'] for f in available}, {f['code'] for f in catalog()})
        for code in ('И_1_13_07_03', 'И_1_13_07_15', 'СП_77_А_21'):
            form = next(f for f in available if f['code'] == code)
            self.assertTrue(form['guidance']['url'].startswith('https://id-prosto.ru/examples/'))
            fields = []
            table = next((f for f in form['fields'] if f['kind'] == 'table' and not f.get('source')), None)
            if table:
                values = {f['source'].split('.')[1]: 'Тестовое значение'
                          for f in table['fields'] if f.get('source', '').startswith('item.')}
                fields = [{**table, 'value': [values]}]
            status, body = self.request('/api/act', {'project_id': pid, 'act_type': code, 'fields': fields})
            self.assertEqual(status, 200, body)
            aid = json.loads(body)['act_id']
            status, body = self.request('/api/generate', {'project_id': pid, 'act_id': aid})
            self.assertEqual(status, 200, body)
            release = json.loads(body)
            self.assertTrue(Path(release['output']).is_file())
            with connect(self.path) as c:
                stored = json.loads(c.execute('SELECT fields FROM acts WHERE id=?', (aid,)).fetchone()[0])
                self.assertEqual(stored, fields)
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM document_types').fetchone()[0], 3)

    def request(self, path, data=None, token=True, origin=None, host=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['X-ITD-Token'] = self.session
        if origin:
            headers['Origin'] = origin
        if host:
            headers['Host'] = host
        req = Request(self.server.origin + path, headers=headers, data=json.dumps(data).encode() if data is not None else None)
        try:
            with urlopen(req) as r:
                return r.status, r.read()
        except HTTPError as e:
            with e:
                return e.code, e.read()

    def test_status_and_structured_missing_fields(self):
        self.assertEqual(self.request('/api/status',token=False)[0],403)
        status,body=self.request('/api/status')
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body),{'database':'ready','agent':{'mode':'external_chat','activity':'unknown'}})
        status,body=self.request('/api/save',{'object':{},'participants':[],'projects':[]})
        self.assertEqual(status,400)
        result=json.loads(body)
        self.assertEqual(result['error'],'Пожалуйста, заполните поле «Полное наименование объекта».')
        self.assertEqual(result['fields'][0]['path'],'object.name')
        self.assertEqual(self.request('/ui.js')[0],200)
        self.assertEqual(self.request('/dialogs.js',token=False)[0],200)
        self.assertEqual(self.request('/act-fields.js',token=False)[0],200)
        for name in ('regular','semibold','bold'):
            status,font=self.request('/open-sans-'+name+'.ttf')
            self.assertEqual(status,200)
            self.assertTrue(font.startswith(b'\x00\x01\x00\x00'))
        self.assertEqual(self.request('/open-sans-LICENSE.txt')[0],200)


    def test_access_token_origin_host_and_static_routes(self):
        self.assertEqual(self.request('/api/bootstrap', token=False)[0], 403)
        self.assertEqual(self.request('/api/bootstrap', origin='https://example.test')[0], 403)
        self.assertEqual(self.request('/api/bootstrap', host='evil.test')[0], 403)
        self.assertEqual(self.request('/api/bootstrap')[0], 200)
        self.assertEqual(self.request('/')[0], 200)
        self.assertEqual(self.request('/journals.js')[0], 200)
        self.assertEqual(self.request('/../../AGENTS.md')[0], 404)

    def test_file_upload_duplicate_and_path_validation(self):
        s = self.create()
        data = {'project_id': s['projects'][0]['id'], 'name': 'РД.pdf', 'doc_type': 'rd',
                'content': base64.b64encode(b'%PDF test-original').decode()}
        status, body = self.request('/api/upload', data)
        self.assertEqual(status, 200, body)
        first = json.loads(body)
        target=self.path.parent/first['project_path']
        self.assertEqual(target.parent.name,'Рабочая документация')
        self.assertEqual(target.read_bytes(),b'%PDF test-original')
        self.assertEqual(self.request('/api/upload', data)[0], 200)
        self.assertEqual(len(list(target.parent.iterdir())),1)
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM attachments').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM project_attachments').fetchone()[0], 1)
            self.assertEqual(len(first['sha256']), 64)
        for name in ('../escape.pdf', 'a/b', 'a\\b', '..'):
            self.assertEqual(self.request('/api/upload', {**data, 'name': name})[0], 400)
        self.assertEqual(self.request('/api/upload', {**data, 'doc_type': 'passport'})[0], 400)

    def test_source_file_types_plan_and_apply_use_separate_transactions(self):
        saved=self.create();pid=saved['projects'][0]['id']
        for kind in ('contract','quality'):
            status,body=self.request('/api/upload',{'project_id':pid,'name':kind+'.pdf','doc_type':kind,'content':base64.b64encode(kind.encode()).decode()})
            self.assertEqual(status,200,body)
        with connect(self.path) as c:
            files=project_data(c,pid)['source_files']
            self.assertEqual({f['file_kind'] for f in files},{'contract','quality'})
        aid=files[0]['id']
        status,body=self.request('/api/files/plan',{'project_id':pid,'purpose':'delete','attachment_id':aid})
        self.assertEqual(status,200,body);plan=json.loads(body)
        self.assertEqual(self.request('/api/files/apply',{**plan,'token':'forged'})[0],400)
        status,body=self.request('/api/files/apply',plan)
        self.assertEqual(status,200,body)
        with connect(self.path) as c:
            self.assertIsNone(c.execute('SELECT * FROM attachments WHERE id=?',(aid,)).fetchone())
            self.assertEqual(len(project_data(c,pid)['source_files']),1)

    def test_create_act_binds_work_and_rejects_second_binding(self):
        s = self.create()
        pid = s['projects'][0]['id']
        with connect(self.path) as c:
            register_form(c, code='TEST', name='Тестовая форма', fields=[])
            entry = save_entry(c, pid, {'kind': 'work', 'title': 'Прокладка'})
        data = {'project_id': pid, 'act_type': 'TEST', 'entry_ids': [entry['id']]}
        self.assertEqual(self.request('/api/act', data)[0], 200)
        self.assertEqual(self.request('/api/act', data)[0], 400)
        with connect(self.path) as c:
            self.assertEqual(len(project_data(c, pid)['acts']), 1)

    def test_hidden_work_act_from_work_entries_with_typed_inputs(self):
        saved = self.create()
        pid = saved['projects'][0]['id']
        rid = self.resource(pid)
        with connect(self.path) as c:
            entry = save_entry(c, pid, {'kind':'work','title':'Скрытая прокладка кабеля',
                'entry_date':'2026-10-29','details':'Участок 1, до закрытия отделкой',
                'resource_id':rid,'quantity':2,'unit':'шт.'})
        payload = {'project_id':pid,'act_type':'МИНСТРОЙ_344_АОСР','entry_ids':[entry['id']],
                   'resource_ids':[rid],'date_signed':'2026-10-31','fields':[
                       {'key':'copies_count','kind':'literal','value_type':'number','value':2},
                       {'key':'work_start','kind':'literal','value_type':'date','format':'date_ru','value':'2026-10-29'},
                       {'key':'work_end','kind':'literal','value_type':'date','format':'date_ru','value':'2026-10-30'}]}
        invalid = {**payload,'fields':[{'key':'copies_count','kind':'literal','value_type':'number','value':'2'}]}
        self.assertEqual(self.request('/api/act', invalid)[0],400)
        status, body = self.request('/api/act', payload)
        self.assertEqual(status,200,body)
        aid = json.loads(body)['act_id']
        status, body = self.request(f'/api/context?project_id={pid}&act_id={aid}')
        self.assertEqual(status,200)
        value = json.loads(body)
        self.assertEqual(value['context']['copies_count'],2)
        self.assertEqual(value['context']['work_start'],'29.10.2026')
        self.assertEqual(value['context']['work_end'],'30.10.2026')
        self.assertEqual(value['source_issues'],[])
        self.assertEqual(value['context']['customer_name'],'Застройщик')
        fields = value['preview_fields']
        self.assertEqual(next(f['label'] for f in fields if f['key']=='customer_name'),'Заказчик: наименование')
        # Реквизиты остаются ссылками: последующая правка карточки попадёт в DOCX.
        from itd.changes import update_record
        org_id = saved['participants'][0]['id']
        with connect(self.path) as c:
            update_record(c,entity='organizations',record_id=org_id,
                          changes={'full_name':'Уточнённый заказчик'},expected={'full_name':'Застройщик'})
            self.assertEqual(c.execute('SELECT act_id FROM workspace_entries WHERE id=?',(entry['id'],)).fetchone()[0],aid)
            self.assertIsNone(c.execute('SELECT qty_fact FROM resources WHERE id=?',(rid,)).fetchone()[0])
        _, body = self.request(f'/api/context?project_id={pid}&act_id={aid}')
        self.assertEqual(json.loads(body)['context']['customer_name'],'Уточнённый заказчик')
        self.assertEqual(self.request('/api/generate', {'project_id':pid,'act_id':aid})[0],200)
        self.assertEqual(self.request('/api/act', payload)[0],400)

    def test_aosr_address_documentation_defaults_stay_live_and_preserve_individual_text(self):
        from itd.acts import add_act, build_context
        from itd.form_catalog import ensure_act_form
        from itd.participants import add_organization, assign
        from itd.changes import update_record
        saved = self.create()
        pid = saved['projects'][0]['id']
        oid = saved['object']['id']
        with connect(self.path) as c:
            update_record(c,entity='objects',record_id=oid,changes={'address':'Тестовый адрес, корпус 2'})
            designer = add_organization(c, full_name='Проектная организация объекта')
            assign(c,entity='organization',entity_id=designer,role_key='designer',object_id=oid)
            ensure_act_form(c,pid,'МИНСТРОЙ_344_АОСР')
            aid = add_act(c,project_id=pid,act_type='МИНСТРОЙ_344_АОСР')
        status, body = self.request(f'/api/project?project_id={pid}')
        self.assertEqual(status,200)
        view = json.loads(body)
        form = next(f for f in view['available_forms'] if f['code']=='МИНСТРОЙ_344_АОСР')
        ui = {f['key']:f for f in form['ui_fields']}
        self.assertEqual(ui['object_address']['source'],'object.address')
        self.assertEqual(ui['design_documents']['source'],'project_documentation.description')
        self.assertEqual(view['form_roots']['project_documentation']['description'],'РД-01-СПС, Проектная организация объекта')
        with connect(self.path) as c:
            # Для уже подключённой формы базовые поля остаются в исходном виде.
            stored = json.loads(c.execute('SELECT fields FROM document_types WHERE code=?',('МИНСТРОЙ_344_АОСР',)).fetchone()[0])
            self.assertEqual(next(f for f in stored if f['key']=='object_address')['kind'],'literal')
            context = build_context(c,aid)['context']
            self.assertEqual(context['object_address'],'Тестовый адрес, корпус 2')
            self.assertEqual(context['design_documents'],'РД-01-СПС, Проектная организация объекта')
            section_designer = add_organization(c, full_name='Разработчик выбранного раздела')
            assign(c,entity='organization',entity_id=section_designer,role_key='designer',project_id=pid)
            update_record(c,entity='projects',record_id=pid,changes={'designer_org_id':section_designer,'code':'РД-02-СПС'})
            update_record(c,entity='objects',record_id=oid,changes={'address':'Уточнённый адрес'})
            current = build_context(c,aid)['context']
            self.assertEqual(current['object_address'],'Уточнённый адрес')
            self.assertEqual(current['design_documents'],'РД-02-СПС, Разработчик выбранного раздела')
            manual = add_act(c,project_id=pid,act_type='МИНСТРОЙ_344_АОСР',fields=[
                {'key':'object_address','kind':'literal','value':'Индивидуальный строительный адрес'},
                {'key':'design_documents','kind':'literal','value':'РД-02-СПС, листы 3–5, уточнение'}])
            explicit = build_context(c,manual)['context']
            self.assertEqual(explicit['object_address'],'Индивидуальный строительный адрес')
            self.assertEqual(explicit['design_documents'],'РД-02-СПС, листы 3–5, уточнение')
            update_record(c,entity='projects',record_id=pid,changes={'designer_org_id':None})
            # При отсутствии назначенной организации описание не считается полным.
            c.execute('DELETE FROM organization_assignments WHERE org_id IN (?,?)',(designer,section_designer))
            incomplete = build_context(c,aid)
            self.assertIn('design_documents',incomplete['missing'])

    def resource(self, pid):
        from itd.resources import CATEGORIES, add_resource
        with connect(self.path) as c:
            return add_resource(c, project_id=pid, name='Датчик', unit='шт.', category=CATEGORIES[1], qty_proj=3)

    def test_http_fact_cli_check_act_link_and_cross_project_rejection(self):
        s = self.create()
        pid = s['projects'][0]['id']
        rid = self.resource(pid)
        fact = dict(resource_id=rid, source_key='отчёт-1/строка-1', location='этаж 2', work_description='Монтаж',
                    quantity=2, source='Подтверждение пользователя', reported_by='Мастер', status='confirmed', end_date='2026-10-10')
        status, body = self.request('/api/fact', {'project_id': pid, 'fact': fact})
        self.assertEqual(status, 200, body)
        fid = json.loads(body)['id']
        self.assertEqual(self.request('/api/fact', {'project_id': pid, 'fact': fact})[0], 200)
        other = self.create()['projects'][0]['id']
        self.assertEqual(self.request('/api/fact', {'project_id': other, 'fact': fact})[0], 400)
        with connect(self.path) as c:
            from itd.workflow import fact_summary, report
            self.assertEqual(fact_summary(c, pid)[0]['confirmed_total'], 2)
            self.assertIsNone(fact_summary(c, pid)[0]['qty_fact'])
            self.assertEqual(len(c.execute('SELECT * FROM work_facts').fetchall()), 1)
            register_form(c, code='TEST', name='Акт', fields=[])
            entry = save_entry(c, pid, {'kind': 'work', 'title': 'Монтаж', 'resource_id': rid})
        act = {'project_id': pid, 'act_type': 'TEST', 'entry_ids': [entry['id']], 'fact_ids': [fid]}
        self.assertEqual(self.request('/api/act', act)[0], 400)
        status, body = self.request('/api/act', {**act, 'resource_ids': [rid]})
        self.assertEqual(status, 200, body)
        aid = json.loads(body)['act_id']
        status, body = self.request('/api/project?project_id='+str(pid))
        self.assertEqual(status, 200, body)
        view = json.loads(body)
        self.assertEqual(view['act_facts'], [{'act_id': aid, 'fact_id': fid}])
        with connect(self.path) as c:
            self.assertEqual(view['check'], report(c, pid))
            self.assertEqual(len(view['acts']), 1)  # Неудачная попытка полностью откатилась.
        self.assertEqual(self.request('/api/fact-status', {'project_id': other, 'fact_id': fid,
            'changes': {'status': 'void', 'reason': 'Ошибка'}, 'expected': {'status': 'confirmed'}})[0], 400)

    def test_quality_link_review_invalidation_and_cli_sources_visible_in_web(self):
        pid = self.create()['projects'][0]['id']
        rid = self.resource(pid)
        status, body = self.request('/api/upload', {'project_id': pid, 'name': 'passport.txt', 'doc_type': 'passport',
            'content': base64.b64encode(b'original passport').decode()})
        self.assertEqual(status, 200, body)
        att = json.loads(body)['id']
        review = dict(resource_id=rid, attachment_id=att, status='matches', checked_by='Инженер',
                      checked_date='2026-10-20', source='Паспорт, стр. 1', note='Сверены марка и номер, партия неизвестна')
        self.assertEqual(self.request('/api/quality', {'project_id': pid, 'review': {**review, 'checked_date': None}})[0], 400)
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM resource_attachments').fetchone()[0], 0)
        self.assertEqual(self.request('/api/quality', {'project_id': pid, 'review': review})[0], 200)
        with connect(self.path) as c:
            from itd.changes import update_record
            from itd.workflow import add_requirement
            add_requirement(c, pid, dict(title='Паспорт', work_scope='Датчик', basis='Согласованный перечень', kind='attachment', attachment_type='passport', attachment_id=att))
            c.execute('DELETE FROM project_attachments WHERE attachment_id=?', (att,))
            update_record(c, entity='resources', record_id=rid, changes={'serial_num': '001'}, expected={'serial_num': None})
        status, body = self.request('/api/project?project_id='+str(pid))
        self.assertEqual(status, 200, body)
        view = json.loads(body)
        self.assertEqual(view['attachments'][0]['id'], att)  # Связь только с ресурсом через CLI.
        self.assertEqual(len(view['quality_reviews']), 1)
        self.assertEqual(view['workflow']['matrix']['requirements'][0]['title'], 'Паспорт')
        self.assertIn('quality_stale', [f['code'] for f in view['check']['findings']])
        self.assertEqual(self.request('/api/quality', {'project_id': pid, 'review': review})[0], 200)

    def test_download_requires_selected_integrity_checked_release(self):
        s = self.create()
        pid = s['projects'][0]['id']
        target = Path(self.tmp.name) / 'test.docx'
        target.write_bytes(b'original')
        from itd.releases import register_release
        with connect(self.path) as c:
            rid = register_release(c, project_id=pid, kind='xlsx', title='Ведомость', path=target, mode='final')
            c.execute('UPDATE releases SET selected=1 WHERE id=?', (rid,))
        route = f'/api/download?project_id={pid}&release_id={rid}'
        self.assertEqual(self.request(route), (200, b'original'))
        target.write_bytes(b'changed')
        self.assertEqual(self.request(route)[0], 400)
        self.assertEqual(self.request(f'/api/download?project_id=999&release_id={rid}')[0], 400)

    def test_draft_generation_and_statement_use_managed_releases(self):
        s = self.create()
        pid = s['projects'][0]['id']
        from docx import Document
        template = Path(self.tmp.name) / 'templates'
        template.mkdir()
        doc = Document()
        doc.add_paragraph('{{ object_name }}')
        doc.save(template / 'TEST.docx')
        with connect(self.path) as c:
            register_form(c, code='TEST', name='Акт', fields=[
                {'key': 'object_name', 'kind': 'reference', 'source': 'object.name', 'required': True}])
        status, body = self.request('/api/act', {'project_id': pid, 'act_type': 'TEST'})
        self.assertEqual(status, 200, body)
        act_id = json.loads(body)['act_id']
        from unittest.mock import patch
        with patch('itd.web.default_templates', return_value=template):
            status, body = self.request('/api/generate', {'project_id': pid, 'act_id': act_id})
        self.assertEqual(status, 200, body)
        rid = json.loads(body)['release_id']
        self.assertEqual(self.request(f'/api/download?project_id={pid}&release_id={rid}')[0], 200)
        status, body = self.request('/api/statement', {'project_id': pid})
        self.assertEqual(status, 200, body)
        with connect(self.path) as c:
            releases = project_data(c, pid)['releases']
            self.assertEqual([r['kind'] for r in releases], ['docx', 'xlsx'])
            self.assertEqual(releases[0]['mode'], 'draft')


if __name__ == '__main__':
    unittest.main()
