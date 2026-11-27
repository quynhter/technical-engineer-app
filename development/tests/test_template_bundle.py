import base64
from collections import Counter
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from docx import Document

from itd.custom_templates import list_templates, template_operation
from itd.db import MIGRATIONS, connect, initialize
from itd.server_state import WorkspaceState
from itd.services.template_bundle import read_bundle


ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / 'app/templates/itd-forms.zip'


class TemplateBundleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.state = WorkspaceState(self.directory / 'new.db')
        self.state.template_bundle = BUNDLE
        self.state.templates = self.directory / 'app/templates'

    def test_first_start_restart_and_restore_missing_file(self):
        backup, admin_code = self.state.prepare()
        self.assertIsNone(backup)
        self.assertTrue(admin_code)
        native, _ = read_bundle(BUNDLE)
        self.assertEqual(len(native), 5)
        for location, data in native:
            self.assertEqual((self.directory / 'app' / location).read_bytes(), data)
            self.assertEqual((ROOT / 'app' / location).read_bytes(), data)

        with connect(self.state.database) as db:
            initial = list_templates(db)
            self.assertEqual(Counter(item['form_set'] for item in initial),
                             {'И 1.13-07': 25, 'Приказ Минстроя №344_пр': 5, 'СП 77.13330.2016': 5})
            self.assertEqual(db.execute('SELECT count(*) FROM projects').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM acts').fetchone()[0], 0)
        for item in initial:
            template = self.state.templates / (item['code'] + '.docx')
            self.assertTrue(template.is_file())
            for section in Document(template).sections:
                if (round(section.page_width.mm), round(section.page_height.mm)) == (210, 297):
                    with self.subTest(template=item['original_name']):
                        self.assertEqual(round(section.top_margin.mm), 10)
                        self.assertEqual(round(section.bottom_margin.mm), 10)
                        self.assertEqual(round(section.left_margin.mm), 15)
                        self.assertEqual(round(section.right_margin.mm), 15)
        path = self.state.templates / (initial[0]['code'] + '.docx')
        original = path.read_bytes()
        path.unlink()
        self.state.prepare()
        self.assertEqual(path.read_bytes(), original)
        with connect(self.state.database) as db:
            self.assertEqual(list_templates(db), initial)
            events = db.execute("SELECT source FROM audit_events WHERE operation='install-template-bundle'").fetchall()
            self.assertEqual([row['source'] for row in events], ['background'])

    def test_switch_to_older_db_preserves_existing_and_deleted_templates(self):
        self.state.prepare()
        old = self.directory / 'old.db'
        migrations = self.directory / 'migrations'
        migrations.mkdir()
        for migration in MIGRATIONS.glob('[0-9][0-9][0-9]_*.sql'):
            if int(migration.name[:3]) <= 26:
                (migrations / migration.name).write_bytes(migration.read_bytes())
        with patch('itd.db.MIGRATIONS', migrations):
            initialize(old)
        _, items = read_bundle(BUNDLE)
        (existing, content), (removed, removed_content) = items[:2]
        with connect(old) as db:
            customized = template_operation(db, 'save', {**existing, 'name': 'Моя форма',
                'content': base64.b64encode(content).decode()}, self.state.templates)['code']
            deleted = template_operation(db, 'save', {**removed,
                'content': base64.b64encode(removed_content).decode()}, self.state.templates)['code']
            template_operation(db, 'delete', {'code': deleted, 'revision': 1}, self.state.templates)

        initial_db = self.state.database
        self.state.configure({'database_path': str(old), 'itd_root': str(self.directory / 'old-ITD')}, 1)
        self.assertEqual(self.state.database, old)
        self.assertEqual(len(list((self.directory / 'backups').glob('*.db'))), 1)
        with connect(initial_db) as db:
            initial_codes = {item['code'] for item in list_templates(db)}
        with connect(old) as db:
            active = list_templates(db)
            codes = {item['code'] for item in active}
            self.assertEqual(len(active), 34)
            self.assertEqual(initial_codes & codes, set())
            self.assertEqual([item['name'] for item in active if item['code'] == customized], ['Моя форма'])
            self.assertNotIn(deleted, codes)
            self.assertEqual(db.execute('SELECT count(*) FROM bundled_document_templates').fetchone()[0], 35)
            template_operation(db, 'save', {**existing, 'name': 'Моя форма', 'code': customized,
                'revision': 1, 'original_name': 'Переименованная.docx'}, self.state.templates)
        self.state.prepare()
        self.assertEqual((self.state.templates / (customized + '.docx')).read_bytes(), content)
        self.assertFalse((self.state.templates / (deleted + '.docx')).exists())
        with connect(old) as db:
            active = list_templates(db)
            self.assertEqual({item['code'] for item in active}, codes)
            self.assertEqual([item['original_name'] for item in active if item['code'] == customized],
                             ['Переименованная.docx'])
