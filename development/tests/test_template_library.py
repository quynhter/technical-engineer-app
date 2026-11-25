import os
"""Библиотека форм, поиск в подпапках и индивидуальные таблицы."""
import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from itd.acts import find_template, register_form, add_act, generate
from itd.db import initialize, connect, add_object, add_project
from itd.fields import resolve_fields
from itd.fields import merge_fields

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = os.environ.get('ITD_FORM_SOURCE_DIR')


def source_path(form):
    return Path(SOURCE_DIR) / Path(form['source']).relative_to('misc/downloads/Исходные формы документов')



class TemplateLibraryTests(unittest.TestCase):
    def test_nested_lookup_rejects_ambiguity_and_outside_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'И 1.13-07').mkdir()
            template = root / 'И 1.13-07/ТЕСТ.docx'
            template.write_bytes(b'template')
            self.assertEqual(find_template(root, 'ТЕСТ'), template)
            (root / 'ТЕСТ.docx').write_bytes(b'duplicate')
            with self.assertRaisesRegex(ValueError, 'Несколько'):
                find_template(root, 'ТЕСТ')
            with self.assertRaisesRegex(ValueError, 'не найден'):
                find_template(root, 'НЕТ')
            with self.assertRaises(ValueError):
                find_template(root, '../ТЕСТ')
            (root / 'external').mkdir()
            (root / 'external/ССЫЛКА.docx').symlink_to('/etc/hosts')
            with self.assertRaisesRegex(ValueError, 'не найден'):
                find_template(root, 'ССЫЛКА')

    def test_manual_table_checks_each_row_and_preserves_zero(self):
        fields = [{'key': 'measurements', 'kind': 'table', 'value': [{'pressure': 0}],
                   'required': True, 'fields': [
                       {'key': 'pressure', 'kind': 'reference', 'source': 'item.pressure', 'required': True}]}]
        self.assertEqual(resolve_fields(fields, {}, draft=False)[0]['measurements'], [{'pressure': 0}])
        fields[0]['value'] = [{}]
        with self.assertRaisesRegex(ValueError, r'measurements\[1\].pressure'):
            resolve_fields(fields, {}, draft=False)
        fields[0]['value'] = None
        self.assertIn('УТОЧНИТЬ', resolve_fields(fields, {})[0]['measurements'][0]['pressure'])
        fields[0]['source'] = 'resources'
        with self.assertRaisesRegex(ValueError, 'source или value'):
            resolve_fields(fields, {})

    @unittest.skipUnless(importlib.util.find_spec('docxtpl'), 'Нужен docxtpl')
    def test_every_downloaded_form_generates_a_draft_from_database(self):
        from docx import Document
        catalog = [f for f in json.loads((ROOT / 'app/forms/catalog.json').read_text()) if f.get('source')]
        if SOURCE_DIR:
            sources = [p for p in Path(SOURCE_DIR).rglob('*')
                       if p.suffix in ('.docx', '.xlsx')]
            # Exact duplicate downloads share a template. A.21 predates the source
            # library and deliberately keeps its existing registration contract.
            represented = {form['source_sha256'] for form in catalog}
            preserved = next(p for p in sources if p.name == 'Ведомость смонтированных технических средств автоматизации.docx')
            represented.add(hashlib.sha256(preserved.read_bytes()).hexdigest())
            self.assertEqual(represented, {hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'test.db'
            initialize(db)
            with connect(db) as conn:
                obj = add_object(conn, 'Проверочный объект')
                project = add_project(conn, object_id=obj, section_code='ЭОМ', code='ТЕСТ-ЭОМ', name='Электрооборудование')
                for form in catalog:
                    with self.subTest(form=form['code']):
                        fields = json.loads((ROOT / form['fields']).read_text())
                        register_form(conn, code=form['code'], name=form['name'], fields=fields, form_group=form['group'])
                        act = add_act(conn, project_id=project, act_type=form['code'])
                        output = Path(tmp) / (form['code'] + '.docx')
                        generate(conn, act_id=act, templates_dir=ROOT / 'app/templates', output=output)
                        doc = Document(output)
                        if form['code'] == 'И_1_13_07_22':
                            # В фиксированной таблице опор сохраняются все пять
                            # колонок и корректные вертикальные объединения.
                            self.assertEqual(len(doc.tables[1].columns), 5)
                            self.assertEqual(len(doc.tables[1].rows[4].cells), 5)
                            self.assertIn('Промежуточные', doc.tables[1].cell(4, 0).text)
                        text = '\n'.join(p.text for p in doc.paragraphs)
                        text += '\n'.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
                        for section in doc.sections:
                            for kind in ('header', 'first_page_header', 'even_page_header',
                                         'footer', 'first_page_footer', 'even_page_footer'):
                                text += '\n'.join(p.text for p in getattr(section, kind).paragraphs)
                        self.assertNotIn('{{', text)
                        self.assertNotIn('{%', text)
                        self.assertNotIn('[УТОЧНИТЬ]', text)
                        self.assertIn('—', text)

    def test_catalog_provenance_unique_codes_and_preserved_docx_parts(self):
        from zipfile import ZipFile
        catalog = [f for f in json.loads((ROOT / 'app/forms/catalog.json').read_text()) if f.get('source')]
        self.assertEqual(len(catalog), len({f['code'] for f in catalog}))
        for form in catalog:
            self.assertRegex(form['source_sha256'], r'^[0-9a-f]{64}$')
            if not SOURCE_DIR:
                continue
            source = source_path(form)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), form['source_sha256'])
            if not form.get('set', '').startswith('СП ') or source.suffix != '.docx':
                continue
            with self.subTest(code=form['code']), ZipFile(source) as original, ZipFile(ROOT / form['template']) as prepared:
                self.assertEqual(original.namelist(), prepared.namelist())
                for name in original.namelist():
                    if name != 'word/document.xml':
                        self.assertEqual(original.read(name), prepared.read(name), name)
