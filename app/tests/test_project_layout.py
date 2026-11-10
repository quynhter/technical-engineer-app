"""Размещение 0.0.3: данные, корень ИТД и переносимость выпуска."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from itd.db import connect
from itd.managed import generate_managed, statement_managed
from itd.releases import export_package, list_releases, publish, verify_releases, workspace
from itd.paths import default_templates
import test_release_workflow as fixtures

ROOT = Path(__file__).resolve().parents[2]


class ProjectLayoutTests(unittest.TestCase):
    def setUp(self):
        fixtures.ReleaseWorkflowTests.setUp(self)
        (self.root/'db').mkdir()
        self.db=self.db.rename(self.root/'db/itd.db')

    emit=fixtures.ReleaseWorkflowTests.emit

    def test_draft_final_draft_history_zip_and_root_remain_consistent(self):
        with connect(self.db) as c:
            self.assertEqual(workspace(c), self.root)
            first=self.emit(c)
            self.assertIn('/03_Акты/Черновики/', first['output'])
            second=self.emit(c,draft=False)
            self.assertIn('/03_Акты/Выдача/', second['output'])
            third=self.emit(c)
            self.assertEqual(third['output'],first['output'])
            rows=list_releases(c)
            self.assertTrue(all(r['path'].startswith('db/История выпусков/') for r in rows[:-1]))
            self.assertTrue(verify_releases(c)['ok'])
            package=export_package(c,self.project,self.root/'ИТД/Комплект.zip')
            with ZipFile(package['output']) as z:
                self.assertIn('03_Акты/Черновики/01_ЭОМ.docx',z.namelist())
            self.assertFalse((self.root/'db/work/.itd-staging').exists())
            self.assertFalse((self.root/'Выпуски в подготовке').exists())
            self.assertFalse((self.root/'db/ИТД').exists())
            self.assertFalse((self.root/'История выпусков').exists())
        copied=self.root/'copy'
        shutil.copytree(self.root/'db',copied/'db')
        shutil.copytree(self.root/'ИТД',copied/'ИТД')
        with connect(copied/'db/itd.db') as c:
            self.assertTrue(verify_releases(c)['ok'])

    def test_failed_publication_preserves_staging_and_can_resume(self):
        occupied=self.root/'ИТД/Занято.docx'
        occupied.parent.mkdir();occupied.write_bytes(b'user-content')
        with connect(self.db) as c:
            with self.assertRaises(FileExistsError):self.emit(c,output=occupied)
            row=list_releases(c)[0]
            staging=Path(row['current_path'])
            self.assertTrue(staging.is_file())
            self.assertTrue(staging.is_relative_to(self.root/'db/work/.itd-staging'))
            target=self.root/'ИТД/Продолженный выпуск.docx'
            publish(c,row['id'],target)
            self.assertTrue(verify_releases(c)['ok'])
            self.assertEqual(occupied.read_bytes(),b'user-content')
            self.assertFalse(staging.exists())
            self.assertFalse(staging.parent.exists())

    def test_explicit_output_xlsx_and_service_directory_protection(self):
        from itd.releases import move_release
        with connect(self.db) as c:
            explicit=self.root/'ИТД/Свое имя.docx'
            result=self.emit(c,output=explicit)
            self.assertEqual(Path(result['output']),explicit)
            for destination in ('app/templates/Подмена.docx','misc/Подмена.docx',
                                'db/archive/Подмена.docx','db/backups/Подмена.docx'):
                with self.subTest(destination=destination),self.assertRaises(ValueError):
                    move_release(c,result['release_id'],destination)
            xlsx=statement_managed(c,project_id=self.project)
            self.assertTrue(Path(xlsx['output']).is_relative_to(self.root/'ИТД'))
            self.assertFalse((self.root/'db/work/.itd-staging').exists())

    def test_fresh_cli_initializes_data_from_project_root_and_imports_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            shutil.copytree(ROOT/'app/itd',root/'app/itd',ignore=shutil.ignore_patterns('__pycache__'))
            (root/'app/templates').mkdir()
            def cli(*args):
                result=subprocess.run([sys.executable,'-m','app.itd',*args],cwd=root,
                                      capture_output=True,text=True,check=True)
                return json.loads(result.stdout)
            self.assertEqual(cli('init')['db'],str(root/'db/itd.db'))
            self.assertFalse((root/'itd.db').exists())
            original=root/'source.pdf';original.write_bytes(b'original-content')
            result=cli('file-add','--file',str(original),'--type','rd','--title','Источник')
            self.assertIsNotNone(result['id'])
            self.assertEqual(len(list((root/'db/archive').rglob('*.pdf'))),1)
            legacy=root/'legacy.db'
            cli('--db',str(legacy),'init')
            self.assertTrue(legacy.is_file())

    def test_catalog_and_default_templates_resolve_after_move(self):
        with patch('pathlib.Path.cwd',return_value=self.root):
            self.assertEqual(default_templates(),ROOT/'app/templates')
        for form in json.loads((ROOT/'app/templates/catalog.json').read_text()):
            for key in ('template','fields'):
                with self.subTest(form=form['code'],key=key):
                    self.assertTrue((ROOT/form[key]).is_file())
