"""Регрессии этапа 0.4: только временные БД, настоящие DOCX и HTTP."""
import base64
from contextlib import closing, redirect_stdout, redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile

from docx import Document
from itd import document_versions, resource_import
from itd.__main__ import main
from itd.acts import add_act, register_form
from itd.db import initialize, connect, add_object, add_project
from itd.managed import generate_managed
from itd.releases import build_package, export_package
from itd.web import create_server


class ReadBoundaryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.db = self.root/'itd.db'
        initialize(self.db)
        self.templates = self.root/'templates'
        self.templates.mkdir()
        doc = Document(); doc.add_paragraph('Учебный акт {{ city }}')
        doc.save(self.templates/'READ04.docx')
        with connect(self.db) as c:
            oid = add_object(c, 'Учебный объект')
            self.pid = add_project(c, object_id=oid, section_code='ЭОМ', code='РД', name='Раздел', city='Город')
            register_form(c, code='READ04', name='Учебный акт', fields=[{'key':'city','kind':'reference','source':'project.city'}])
            self.aid = add_act(c, project_id=self.pid, act_type='READ04')

    def dump(self):
        with closing(sqlite3.connect(self.db)) as c:
            return '\n'.join(c.iterdump())

    def emit(self):
        with connect(self.db) as c:
            return generate_managed(c, act_id=self.aid, templates_dir=self.templates)

    def cli(self, *args, fail=False):
        with patch.object(sys, 'argv', ['itd', '--agent', '--db', str(self.db), '--itd-root', str(self.root/'ИТД'), *args]), redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
            if fail:
                with self.assertRaises(SystemExit) as error:
                    main()
                self.assertEqual(error.exception.code, 1)
            else:
                main()
                return json.loads(out.getvalue())

    def start(self):
        self.server = create_server(self.db, 0)
        self.addCleanup(self.server.server_close)
        _, code = self.server.prepare()
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.admin = self.http('/api/login', data={'code':code})[2]['session']

    def http(self, route, token='', data=None):
        req = Request(self.server.origin+route, headers={'X-ITD-Token':token, 'Content-Type':'application/json'},
                      data=None if data is None else json.dumps(data).encode())
        try:
            response = urlopen(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            mime = response.headers.get_content_type()
            body = response.read()
            return response.code, mime, json.loads(body) if mime == 'application/json' else body

    def role(self, role):
        result = self.http('/api/admin/create', self.admin, {'first_name':'Тест', 'last_name':'Тест', 'role':role})[2]
        return self.http('/api/login', data={'code':result['code']})[2]['session']

    def stage(self):
        with connect(self.db) as c:
            return resource_import.stage(c, self.pid, {'filename':'fixture.csv', 'content':base64.b64encode('Имя;Ед\nКабель;м\n'.encode()).decode()})

    def test_package_builder_and_wrapper_leave_business_dump_unchanged(self):
        self.emit(); before = self.dump()
        with connect(self.db) as c:
            c.execute('PRAGMA query_only = ON')
            build_package(c, self.pid, self.root/'pure.zip')
            self.assertFalse(Path(str(self.db)+'.audit.sqlite3').exists())
            export_package(c, self.pid, self.root/'audited.zip')
        self.assertEqual(before, self.dump())
        with closing(sqlite3.connect(str(self.db)+'.audit.sqlite3')) as c:
            self.assertEqual(c.execute('SELECT operation,source FROM read_events').fetchall(), [('package-export','cli')])

    def test_package_http_roles_hashes_repeats_and_failed_audit(self):
        self.emit(); self.start()
        editor, viewer = self.role('editor'), self.role('viewer')
        before = self.dump()
        for token in (self.admin, editor, editor):
            status, mime, body = self.http(f'/api/package?project_id={self.pid}', token)
            self.assertEqual((status,mime), (200,'application/zip'), body)
            with ZipFile(io.BytesIO(body)) as z:
                manifest = json.loads(z.read('manifest.json'))
                for item in manifest['releases']:
                    self.assertEqual(hashlib.sha256(z.read(item['file'])).hexdigest(), item['sha256'])
                    with connect(self.db) as c:
                        self.assertEqual(item['sha256'], c.execute('SELECT sha256 FROM releases WHERE id=?',(item['release_id'],)).fetchone()[0])
            self.assertEqual(before, self.dump())
        self.assertEqual(self.http(f'/api/package?project_id={self.pid}',viewer)[0],403)
        audit = Path(str(self.db)+'.audit.sqlite3')
        with closing(sqlite3.connect(audit)) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM read_events').fetchone()[0],3)
        audit.unlink(); audit.mkdir()
        status, mime, body = self.http(f'/api/package?project_id={self.pid}',editor)
        self.assertEqual((status,mime),(400,'application/json'))
        self.assertEqual(before, self.dump())

    def test_package_http_empty_and_corrupt_files_return_no_zip(self):
        self.start()
        route = f'/api/package?project_id={self.pid}'
        before = self.dump()
        self.assertEqual(self.http(route,self.admin)[2]['error'],'Не выбраны выпуски для выдачи')
        self.assertEqual(before,self.dump())
        release = self.emit()
        from itd.archive import import_file, link_file, archived_path
        source=self.root/'original.pdf';source.write_bytes(b'fixture original')
        with connect(self.db) as c:
            item=import_file(c,archive_root=self.root/'archive',source=source,doc_type='quality',title='Fixture')
            link_file(c,attachment_id=item['id'],entity='project',entity_id=self.pid)
            row=c.execute('SELECT storage_path FROM attachments WHERE id=?',(item['id'],)).fetchone()
        original=archived_path(self.root/'archive',row[0])
        before=self.dump()
        for path in (original,Path(release['output'])):
            saved=path.read_bytes();path.write_bytes(b'corrupt')
            self.assertEqual(self.http(route,self.admin)[:2],(400,'application/json'))
            self.assertEqual(before,self.dump());path.write_bytes(saved)
        self.assertFalse(Path(str(self.db)+'.audit.sqlite3').exists())

    def test_cli_reads_modes_errors_and_agent_log(self):
        self.emit(); staged=self.stage()
        from itd.titles import add_title
        with connect(self.db) as c:
            title=add_title(c,self.pid,{'year':2026})['act_id']
        empty=self.root/'relocations.json';empty.write_text('[]')
        cases=[['release-list','--project-id',str(self.pid)], ['release-verify','--project-id',str(self.pid)],
               ['project-context','--project-id',str(self.pid)], ['title-config','--act-id',str(title),'--output',str(self.root/'title.json')],
               ['release-reconcile','--from-relocations','--data',str(empty)],
               ['package-export','--project-id',str(self.pid),'--output',str(self.root/'cli.zip')]]
        for action, data in [('context',{}),('resource-import-preview',{'import_id':staged['import_id']}),('delete-preview',{'entity':'acts','id':self.aid})]:
            path=self.root/(action+'.json');path.write_text(json.dumps(data))
            cases.append(['workspace-action','--project-id',str(self.pid),'--action',action,'--data',str(path)])
        with self.assertLogs('itd.ai',level='INFO') as logs:
            for args in cases:
                with self.subTest(command=args[0]):
                    before=self.dump(); self.cli(*args); self.assertEqual(before,self.dump())
        self.assertEqual(len(logs.output),2*len(cases))
        self.assertTrue(all('Агент запустил команду' in line or 'завершена' in line for line in logs.output))
        self.assertFalse(any('import_id' in line or 'fixture' in line or 'arguments' in line for line in logs.output))
        bad=self.root/'bad.json';bad.write_text('{"import_id":"missing"}')
        before=self.dump()
        self.cli('workspace-action','--project-id',str(self.pid),'--action','resource-import-preview','--data',str(bad),fail=True)
        self.assertEqual(before,self.dump())
        card=self.root/'card.json';card.write_text(json.dumps({'act_id':self.aid}))
        self.cli('workspace-action','--project-id',str(self.pid),'--action','document-version-ensure','--data',str(card))
        self.assertNotEqual(before,self.dump())
        with connect(self.db) as c:
            self.assertGreater(c.execute("SELECT count(*) FROM audit_events WHERE operation='workspace-action'").fetchone()[0],0)

    def test_version_list_empty_stale_and_explicit_ensure(self):
        self.start(); viewer=self.role('viewer')
        data={'project_id':self.pid,'act_id':self.aid}
        with patch('itd.web.default_templates',return_value=self.templates):
            before=self.dump()
            self.assertEqual(self.http('/api/versions/list',self.admin,data)[2]['versions'],[])
            self.assertEqual(before,self.dump())
            first=self.http('/api/versions/ensure',self.admin,data)[2]['versions']
            self.assertEqual(len(first),1)
            before=self.dump()
            self.assertEqual(self.http('/api/versions/ensure',self.admin,data)[2]['versions'],first)
            self.assertEqual(before,self.dump())
            with connect(self.db) as c:
                c.execute('UPDATE acts SET filename_title=? WHERE id=?',('Изменённое название',self.aid))
            before=self.dump()
            self.assertEqual(self.http('/api/versions/list',self.admin,data)[2]['versions'],first)
            self.assertEqual(before,self.dump())
            self.assertEqual(self.http('/api/versions/ensure',viewer,data)[0],403)

    def test_import_stage_is_only_queue_write_and_preview_is_stable(self):
        self.start();editor=self.role('editor');viewer=self.role('viewer')
        payload={'project_id':self.pid,'filename':'fixture.csv','content':base64.b64encode(b'Name;Unit\nCable;m\n').decode()}
        before=self.dump()
        self.assertEqual(self.http('/api/resource-import/stage',viewer,payload)[0],403)
        self.assertEqual(before,self.dump())
        with connect(self.db) as c:
            counts={r[0]:c.execute(f'SELECT count(*) FROM "{r[0]}"').fetchone()[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        staged=self.http('/api/resource-import/stage',editor,payload)[2]
        with connect(self.db) as c:
            delta={name:c.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]-count for name,count in counts.items()}
        self.assertEqual({k:v for k,v in delta.items() if v},{'resource_imports':1,'audit_events':1})
        with connect(self.db) as c:
            event = dict(c.execute('SELECT * FROM audit_events ORDER BY id DESC LIMIT 1').fetchone())
        self.assertEqual(event['operation'], '/api/resource-import/stage')
        self.assertEqual(event['actor_role'], 'editor')
        self.assertEqual(event['source'], 'web')
        self.assertEqual(event['result'], 'success')
        self.assertIsNone(event['before_json'])
        self.assertIsNone(event['after_json'])
        self.assertNotIn(payload['content'], json.dumps(event))
        self.assertNotIn(payload['filename'], json.dumps(event))
        before=self.dump(); data={'project_id':self.pid,'import_id':staged['import_id']}
        one=self.http('/api/resource-import/preview',editor,data)
        self.assertEqual(one,self.http('/api/resource-import/preview',editor,data))
        self.assertEqual(before,self.dump())
        self.assertEqual(one[0],200)
        # Closing the editor sends no commit: resources and supplies remain empty.
        with connect(self.db) as c:
            for table in ('resources','supplies','resource_import_rows'):
                self.assertEqual(c.execute(f'SELECT count(*) FROM {table}').fetchone()[0],0)

    def test_http_file_recovery_requires_confirmation_and_editor(self):
        self.start();editor=self.role('editor');viewer=self.role('viewer')
        with connect(self.db) as c:
            c.execute("INSERT INTO file_operations(id,state,moves_json) VALUES(?,'pending','[]')",('c'*32,))
        data={'project_id':self.pid};before=self.dump()
        self.assertEqual(self.http('/api/files/plan',editor,data)[0],400)
        self.assertEqual(self.http('/api/files/recover',viewer,{**data,'confirmed':True})[0],403)
        self.assertEqual(self.http('/api/files/recover',editor,data)[0],400)
        self.assertEqual(self.http('/api/files/plan',editor,{'project_id':self.pid+999})[0],400)
        self.assertEqual(before,self.dump())
        self.assertEqual(self.http('/api/files/recover',editor,{**data,'confirmed':True})[0],200)
        self.assertEqual(self.http('/api/files/plan',editor,data)[0],200)

    def test_reconcile_dry_run_is_read_but_apply_keeps_write_audit(self):
        release=self.emit()
        source=Path(release['output']);target=source.with_name('Согласованный путь.docx')
        source.rename(target)
        with connect(self.db) as c:
            row=c.execute('SELECT * FROM releases WHERE id=?',(release['release_id'],)).fetchone()
            plan=[{'release_id':row['id'],'old_path':row['path'],'new_path':str(target),'sha256':row['sha256']}]
        path=self.root/'plan.json';path.write_text(json.dumps(plan))
        before=self.dump()
        self.assertFalse(self.cli('release-reconcile','--data',str(path))['applied'])
        self.assertEqual(before,self.dump())
        self.assertTrue(self.cli('release-reconcile','--data',str(path),'--apply')['applied'])
        self.assertNotEqual(before,self.dump())
        with connect(self.db) as c:
            self.assertGreater(c.execute("SELECT count(*) FROM audit_events WHERE operation='release-reconcile'").fetchone()[0],0)
