import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from itd.db import initialize, connect, add_object, add_project
from itd.acts import add_act, register_form
from itd.doctor import diagnose
from itd.releases import move_release, recover, verify_releases, plan_relocations
from itd.managed import generate_managed
import test_release_workflow as fixtures


class UpgradeTests(unittest.TestCase):
    def test_migration_keeps_legacy_generation_and_does_not_touch_its_file(self):
        from itd import db
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);migrations=root/'migrations';migrations.mkdir();path=root/'old.db'
            for p in db.MIGRATIONS.glob('*.sql'):
                if int(p.name[:3])<=8:shutil.copy2(p,migrations/p.name)
            with patch.object(db,'MIGRATIONS',migrations):initialize(path)
            output=root/'Прежний выпуск.docx';output.write_bytes(b'legacy-content')
            from itd.archive import digest
            with connect(path) as c:
                o=add_object(c,'Учебный объект');p=add_project(c,object_id=o,section_code='СПС',code='ТЕСТ',name='Учебный раздел')
                c.execute("INSERT INTO document_types(code,name,fields) VALUES('ТЕСТ','Акт','[]')")
                a=add_act(c,project_id=p,act_type='ТЕСТ')
                c.execute("INSERT INTO generated_documents(act_id,output_path,sha256,mode,context_json,template_sha256) VALUES(?,?,?,'draft','{}',?)",(a,str(output),digest(output),'0'*64))
            initialize(path)
            with connect(path) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM releases').fetchone()[0],1)
                self.assertTrue(verify_releases(c)['ok'])
                self.assertEqual(c.execute('SELECT selected FROM releases').fetchone()[0],1)
                self.assertEqual(c.execute('SELECT act_num FROM acts').fetchone()[0],'01/СПС')
                self.assertEqual(output.read_bytes(),b'legacy-content')
            copied=root/'copy';copied.mkdir()
            shutil.copy2(path,copied/'itd.db')
            shutil.copy2(output,copied/output.name)
            from itd.releases import reconcile
            with connect(copied/'itd.db') as c:
                row=c.execute('SELECT * FROM releases').fetchone()
                plan=[{'release_id':row['id'],'old_path':row['path'],'new_path':str(copied/output.name),'sha256':row['sha256']}]
                reconcile(c,plan,apply=True)
                self.assertTrue(verify_releases(c)['ok'])
                self.assertEqual(c.execute('SELECT path FROM releases').fetchone()[0],output.name)
                self.assertTrue(output.is_file())

    def test_doctor_distinguishes_library_incompatibility_and_tests_file_readers(self):
        with patch('itd.doctor.convert_docx',side_effect=RuntimeError('CURL_OPENSSL_4 not found')):
            report=diagnose()
        self.assertEqual(report['status'],'partial')
        self.assertEqual(report['checks']['docx_to_pdf']['reason'],'incompatible_library')
        for name in ('sqlite','pdf_read','pdf_images','docx_generate_read','xlsx_generate_read'):
            self.assertEqual(report['checks'][name]['status'],'ready')
        self.assertIn('executable',report)
        self.assertEqual(report['modules']['pypdf']['import'],'ok')


class CrashTests(unittest.TestCase):
    def setUp(self):
        # Только подготовка фикстуры: не наследуем и не дублируем все тесты.
        fixtures.ReleaseWorkflowTests.setUp(self)
    emit=fixtures.ReleaseWorkflowTests.emit

    def test_interrupted_link_unlink_is_recovered_without_deleting_unrelated_files(self):
        import os
        with connect(self.db) as c:
            result=self.emit(c)
            target=self.root/'Отдельная выдача'/'Акт.docx'
            real_link=os.link
            def linked_then_crashed(source,destination):
                real_link(source,destination)
                raise RuntimeError('crash before unlink')
            with patch('itd.releases.os.link',side_effect=linked_then_crashed):
                with self.assertRaises(RuntimeError):move_release(c,result['release_id'],target)
            self.assertTrue(Path(result['output']).is_file())
            self.assertTrue(target.is_file())
            op=c.execute("SELECT id FROM release_operations WHERE state='prepared'").fetchone()[0]
            recover(c,op)
            self.assertFalse(Path(result['output']).exists())
            self.assertTrue(verify_releases(c)['ok'])

    def test_unknown_user_file_blocks_publication_before_archiving_current(self):
        with connect(self.db) as c:
            current=self.emit(c)
            occupied=self.root/'Пользовательский акт.docx';occupied.write_bytes(b'user')
            with self.assertRaises(FileExistsError):self.emit(c,output=occupied)
            self.assertTrue(Path(current['output']).is_file())
            self.assertEqual(occupied.read_bytes(),b'user')
            selected=c.execute('SELECT id FROM releases WHERE selected=1').fetchone()[0]
            self.assertEqual(selected,current['release_id'])

    def test_move_rejects_symlinks_and_changed_recovery_destination(self):
        with connect(self.db) as c:
            result=self.emit(c)
            outside=self.root/'outside';outside.mkdir()
            link=self.root/'linked';link.symlink_to(outside,target_is_directory=True)
            with self.assertRaises(ValueError):move_release(c,result['release_id'],link/'Акт.docx')
            target=self.root/'Восстановление.docx'
            with patch('itd.releases.os.link',side_effect=OSError('disk error')):
                with self.assertRaises(OSError):move_release(c,result['release_id'],target)
            op=c.execute("SELECT id FROM release_operations WHERE state='prepared'").fetchone()[0]
            target.write_bytes(b'user')
            with self.assertRaises(ValueError):recover(c,op)
            self.assertEqual(target.read_bytes(),b'user')
            self.assertTrue(Path(result['output']).is_file())

    def test_legacy_movement_plan_excludes_markers_and_unknown_files(self):
        with connect(self.db) as c:
            self.emit(c)
            row=c.execute('SELECT * FROM releases').fetchone()
            from itd.releases import actual_path
            original=str(actual_path(c,row['path']));history=self.root/'История.docx'
            movements=[{'original_path':original,'history_path':str(history),'sha256':row['sha256']},
                       {'original_path':str(self.root/'.itd-project.json'),'history_path':'elsewhere','sha256':'a'*64}]
            report=plan_relocations(c,movements)
            self.assertEqual(len(report['plan']),1)
            self.assertEqual(len(report['ignored']),1)
            self.assertFalse(report['applied'])
