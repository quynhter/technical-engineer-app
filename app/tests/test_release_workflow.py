"""Пользовательские сценарии 0.0.2: история, аварии, выдача, переносимость."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from zipfile import ZipFile
from unittest.mock import patch

from itd.db import initialize, connect, add_object, add_project
from itd.acts import add_act, register_form, review_act
from itd.managed import generate_managed, statement_managed
from itd.releases import (move_release, recover, verify_releases, list_releases,
                          export_package, reconcile, publish)
from itd.layout import path_component, check_path
from itd.fields import resolve_fields
from itd.changes import update_record
from itd.registry import registry_rows
from itd.specification import import_specification
from itd.archive import import_file


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='itd-test-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.db=self.root/'itd.db'
        initialize(self.db)
        self.templates=self.root/'templates'; self.templates.mkdir()
        from docx import Document
        doc=Document(); doc.add_paragraph('Акт {{ city }}'); doc.save(self.templates/'ТЕСТ.docx')
        with connect(self.db) as c:
            o=add_object(c,'Тестовый объект')
            self.project=add_project(c,object_id=o,section_code='ЭОМ',code='ТЕСТ',name='Электрика',city='Казань')
            register_form(c,code='ТЕСТ',name='Акт проверки оборудования',fields=[{'key':'city','kind':'reference','source':'project.city','required':True}])
            self.act=add_act(c,project_id=self.project,act_type='ТЕСТ')

    def emit(self, c, **kwargs):
        return generate_managed(c,act_id=self.act,templates_dir=self.templates,**kwargs)

    def test_repeat_keeps_history_and_zip_contains_exact_selected_bytes(self):
        with connect(self.db) as c:
            first=self.emit(c)
            old_hash=list_releases(c)[0]['sha256']
            second=self.emit(c)
            self.assertTrue(publish(c,second['release_id'],second['output'])['selected'])
            self.assertEqual(Path(first['output']).name,'01_ЭОМ.docx')
            self.assertEqual(first['output'],second['output'])
            rows=list_releases(c)
            self.assertEqual([r['selected'] for r in rows],[0,1])
            self.assertIn('История выпусков',rows[0]['path'])
            self.assertEqual(rows[0]['sha256'],old_hash)
            self.assertTrue(verify_releases(c)['ok'])
            layout=Path(second['output']).parents[2]
            (layout/'03_Акты'/'чужой.docx').write_bytes(b'unknown')
            (layout/'qa.png').write_bytes(b'qa')
            package=export_package(c,self.project,self.root/'Комплект.zip')
            with ZipFile(package['output']) as z:
                docs=[p for p in z.namelist() if p.endswith('.docx')]
                self.assertEqual(docs,['03_Акты/Черновики/01_ЭОМ.docx'])
                self.assertEqual(z.read(docs[0]),Path(second['output']).read_bytes())
            self.assertTrue((layout/'.itd-project.json').is_file())
            self.assertEqual((layout/'03_Акты'/'чужой.docx').read_bytes(),b'unknown')

    def test_crash_after_file_move_is_recovered_from_fresh_connection(self):
        with connect(self.db) as c:
            result=self.emit(c)
            target=self.root/'Выдача'/'Акт оборудования.docx'
            def crash():raise RuntimeError('power loss')
            with self.assertRaisesRegex(RuntimeError,'power loss'):
                move_release(c,result['release_id'],target,after_file_operation=crash)
        with connect(self.db) as c:
            report=verify_releases(c)
            self.assertFalse(report['ok'])
            self.assertEqual(len(report['unfinished_operations']),1)
            op=report['unfinished_operations'][0]['id']
            self.assertEqual(recover(c,op)['state'],'done')
            self.assertEqual(recover(c,op)['state'],'done')
            self.assertTrue(verify_releases(c)['ok'])
            self.assertEqual(move_release(c,result['release_id'],target)['state'],'unchanged')
            self.assertEqual(c.execute('SELECT act_num FROM acts').fetchone()[0],'01/ЭОМ')

    def test_collision_hash_missing_and_marker_are_protected(self):
        with connect(self.db) as c:
            result=self.emit(c);rid=result['release_id'];path=Path(result['output'])
            for target in (path.parent.parent/'.itd-project.json',self.root/'archive'/'test.docx',self.root/'templates'/'test.docx'):
                with self.assertRaises((ValueError,FileExistsError)):
                    move_release(c,rid,target)
            occupied=self.root/'Занято.docx';occupied.write_bytes(b'user')
            with self.assertRaises(FileExistsError):move_release(c,rid,occupied)
            path.write_bytes(b'tampered')
            with self.assertRaises(ValueError):move_release(c,rid,self.root/'Новое.docx')
            self.assertEqual(verify_releases(c)['releases'][0]['status'],'hash_mismatch')
            path.unlink()
            self.assertEqual(verify_releases(c)['releases'][0]['status'],'missing')

    def test_copy_project_retains_managed_relative_paths(self):
        with connect(self.db) as c:
            self.emit(c);self.emit(c)
        copied=self.root/'Копия';copied.mkdir()
        shutil.copy2(self.db,copied/'itd.db')
        shutil.copytree(self.root/'ИТД',copied/'ИТД')
        shutil.copytree(self.root/'История выпусков',copied/'История выпусков')
        with connect(copied/'itd.db') as c:
            self.assertTrue(verify_releases(c)['ok'])
            self.assertTrue(all(Path(r['current_path']).is_relative_to(copied) for r in list_releases(c)))

    def test_reconciliation_is_explicit_and_rejects_stale_plan(self):
        with connect(self.db) as c:
            result=self.emit(c);row=list_releases(c)[0]
            new=self.root/'Перенесённый акт.docx';Path(row['current_path']).rename(new)
            plan=[{'release_id':row['id'],'old_path':row['path'],'new_path':str(new),'sha256':row['sha256']}]
            self.assertFalse(reconcile(c,plan)['applied'])
            self.assertFalse(verify_releases(c)['ok'])
            reconcile(c,plan,apply=True)
            self.assertTrue(verify_releases(c)['ok'])
            with self.assertRaises(ValueError):reconcile(c,plan,apply=True)

    def test_conflicting_clean_names_get_document_suffix_and_full_title_is_preserved(self):
        with connect(self.db) as c:
            update_record(c,entity='acts',record_id=self.act,changes={'filename_title':'Общее/имя'})
            first=self.emit(c)
            other=add_act(c,project_id=self.project,act_type='ТЕСТ')
            update_record(c,entity='acts',record_id=other,changes={'filename_title':'Общее:имя'})
            second=generate_managed(c,act_id=other,templates_dir=self.templates)
            self.assertNotEqual(first['output'],second['output'])
            self.assertIn('документ',Path(second['output']).stem)
            self.assertEqual(list_releases(c)[1]['title'],'Акт проверки оборудования')
            self.assertTrue(verify_releases(c)['ok'])

    def test_xlsx_registered_as_statement_and_print_sheets_remain_unknown(self):
        with connect(self.db) as c:
            result=statement_managed(c,project_id=self.project)
            self.assertEqual(Path(result['output']).name,'Общая ведомость ресурсов ЭОМ.xlsx')
            rows=registry_rows(c,self.project)
            self.assertFalse(any(row['entity']=='release' for row in rows))
            update_record(c,entity='releases',record_id=result['release_id'],changes={'sheets_count':2})
            self.assertEqual(list_releases(c)[0]['sheets_count'],2)

    def test_static_claims_require_review_and_review_expires_after_data_change(self):
        from docx import Document
        doc=Document();doc.add_paragraph('Работы выполнены в {{ city }}');doc.save(self.templates/'ТЕСТ.docx')
        with connect(self.db) as c:
            with self.assertRaisesRegex(ValueError,'act-review'):self.emit(c,draft=False)
            review_act(c,self.act,self.templates,'Утверждение проверено пользователем')
            result=self.emit(c,draft=False)
            doc=Document(result['output'])
            self.assertFalse(any('ЧЕРНОВИК' in p.text for section in doc.sections for p in section.footer.paragraphs))
            update_record(c,entity='projects',record_id=self.project,changes={'city':'Самара'})
            with self.assertRaisesRegex(ValueError,'act-review'):self.emit(c,draft=False)

    def test_draft_uses_dash_for_missing_value_and_preserves_footer(self):
        from docx import Document
        path = self.templates / 'ТЕСТ.docx'
        doc = Document(path)
        doc.sections[0].footer.paragraphs[0].text = 'Колонтитул бланка'
        doc.save(path)
        template = path.read_bytes()
        with connect(self.db) as c:
            update_record(c, entity='projects', record_id=self.project, changes={'city': ''})
            result = self.emit(c)
        doc = Document(result['output'])
        self.assertEqual(doc.paragraphs[0].text, 'Акт —')
        self.assertEqual([p.text for p in doc.sections[0].footer.paragraphs], ['Колонтитул бланка'])
        with ZipFile(result['output']) as archive:
            self.assertNotIn('word/footer2.xml', archive.namelist())
        self.assertEqual(path.read_bytes(), template)

    def test_pending_rows_persist_and_resume_without_overwriting_user_corrections(self):
        source=self.root/'source.pdf';source.write_bytes(b'%PDF test')
        with connect(self.db) as c:
            attachment=import_file(c,archive_root=self.root/'archive',source=source,doc_type='rd',title='Тест')['id']
            item={'source_key':'p2-row3','page':2,'sheet':'1','locator':'строка 3','verified':False,'questions':[{'field':'unit','question':'Уточнить единицу'}],
                  'resource':{'name':'Ресурс','unit':'шт.','category':'Приборы и средства автоматизации'}}
            import_specification(c,project_id=self.project,attachment_id=attachment,items=[item])
        with connect(self.db) as c:
            pending=json.loads(c.execute('SELECT item_json FROM specification_pending').fetchone()[0])
            self.assertEqual(pending['page'],2)
            pending['verified']=True
            report=import_specification(c,project_id=self.project,attachment_id=attachment,items=[pending])
            rid=report['imported'][0]
            update_record(c,entity='resources',record_id=rid,changes={'name':'Исправлено пользователем'})
            self.assertEqual(import_specification(c,project_id=self.project,attachment_id=attachment,items=[pending])['duplicates'],[rid])
            self.assertEqual(c.execute('SELECT status FROM specification_pending').fetchone()[0],'resolved')
            self.assertEqual(c.execute('SELECT name FROM resources').fetchone()[0],'Исправлено пользователем')
            self.assertIsNone(c.execute('SELECT qty_fact FROM resources').fetchone()[0])

    def test_safe_names_bytes_reserved_collision_and_path_length(self):
        self.assertEqual(path_component('CON'),'_CON')
        self.assertNotEqual(path_component('Я'*200),path_component('Я'*199+'А'))
        self.assertLessEqual(len(path_component('Я'*200).encode()),180)
        self.assertEqual(path_component('Акт/Блок:*?'),'Акт_Блок___')
        with self.assertRaises(ValueError):check_path('/tmp/'+'Я'*250+'/test.docx')
        with self.assertRaises(ValueError):check_path('/tmp/NUL/test.docx')

    def test_short_gaps_optional_hidden_and_not_applicable_are_distinct(self):
        details=[]
        fields=[{'key':'required','kind':'literal','value':None,'required':True,'label':'Измерение'},
                {'key':'optional','kind':'literal','value':None},
                {'key':'number','kind':'reference','source':'act.act_num','state':'hidden'},
                {'key':'na','kind':'literal','required':True,'state':'not_applicable','reason':'Согласовано для этого акта'}]
        context,missing=resolve_fields(fields,{},diagnostics=details)
        self.assertEqual(context,{'required':'[УТОЧНИТЬ]','optional':'','number':'','na':''})
        self.assertEqual(missing,['required'])
        self.assertEqual(details[0]['label'],'Измерение')
        self.assertEqual({d['state'] for d in details},{'missing','optional_empty','hidden','not_applicable'})


class PdfSelectionTests(unittest.TestCase):
    def test_ranges_rotation_resume_and_hash_separation(self):
        from pypdf import PdfWriter
        from itd.readers import read_document, page_selection
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'test.pdf';writer=PdfWriter()
            for i in range(5):writer.add_blank_page(200,300)
            writer.pages[2].rotate(90)
            with source.open('wb') as h:writer.write(h)
            result=read_document(source,pages='1,3-4',scan_dir=root/'images',dpi=72)
            self.assertEqual([p['page'] for p in result['parts']],[1,3,4])
            self.assertEqual(result['pdf_page_count'],5)
            self.assertEqual(result['parts'][1]['rotation'],90)
            image=Path(result['parts'][0]['image']);mtime=image.stat().st_mtime_ns
            read_document(source,pages='1',scan_dir=root/'images',dpi=72)
            self.assertEqual(image.stat().st_mtime_ns,mtime)
            other=read_document(source,pages='1',scan_dir=root/'images',dpi=100)
            self.assertNotEqual(other['parts'][0]['image'],str(image))
            image.write_bytes(b'changed')
            with self.assertRaises(ValueError):read_document(source,pages='1',scan_dir=root/'images',dpi=72)
            for selection in ('0','6','4-2','x','1-3-4'):
                with self.assertRaises(ValueError):page_selection(selection,5)
