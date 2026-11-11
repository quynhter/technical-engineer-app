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
    def test_insulation_creation_headers_for_new_and_registered_forms(self):
        from copy import deepcopy
        from itd.form_catalog import available_forms

        code = 'СП_77_А_16'
        expected = ['№ п/п', 'Маркировка провода (кабеля) по чертежу, N позиции',
                    'Марка провода (кабеля)', 'Кол-во и сечение жил, мм2',
                    'Сопротивление изоляции МОм / между проводами (жилами)',
                    'Сопротивление изоляции МОм / относи-тельно земли', 'Примечание']

        def columns(form):
            return next(f for f in form['fields'] if f['key'] == 'rows_0_33')['fields']

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'test.db'
            initialize(db)
            with connect(db) as conn:
                obj = add_object(conn, 'Проверочный объект')
                project = add_project(conn, object_id=obj, section_code='АТХ', code='ТЕСТ', name='Автоматизация')
                new = next(f for f in available_forms(conn, project) if f['code'] == code)
                self.assertEqual([c['label'] for c in columns(new)], expected)
                old = deepcopy(new['fields'])
                table = next(f for f in old if f['key'] == 'rows_0_33')
                for index in (0, 1, 2, 3, 6):
                    table['fields'][index]['label'] = f'Графа {index + 1}'
                table['fields'][2]['label'] = 'Моя марка кабеля'
                table['value'] = [{'c1': '1', 'c3': 'КВВГ'}]
                register_form(conn, code=code, name='Протокол', fields=old)
                stored = conn.execute('SELECT fields FROM document_types WHERE code=?', (code,)).fetchone()[0]
                registered = next(f for f in available_forms(conn, project) if f['code'] == code)
                expected[2] = 'Моя марка кабеля'
                self.assertEqual([c['label'] for c in columns(registered)], expected)
                ui_table = next(f for f in registered['ui_fields'] if f['key'] == 'rows_0_33')
                self.assertFalse(any(c['label'].startswith('Графа ') for c in ui_table['fields']))
                repaired = next(f for f in registered['fields'] if f['key'] == 'rows_0_33')
                self.assertEqual(repaired['value'], table['value'])
                self.assertEqual([{k: v for k, v in c.items() if k != 'label'} for c in repaired['fields']],
                                 [{k: v for k, v in c.items() if k != 'label'} for c in table['fields']])
                self.assertEqual(conn.execute('SELECT fields FROM document_types WHERE code=?', (code,)).fetchone()[0], stored)

    def test_insulation_protocol_headers_follow_the_seven_data_columns(self):
        from itd.field_ui import table_headers

        template = ROOT / 'app/templates/СП 77.13330.2016/СП_77_А_16.docx'
        headers = table_headers(template)
        self.assertEqual(len(headers['rows_0_22'][0]), 7)
        upper, lower = headers['rows_0_33']
        self.assertEqual(sum(cell['span'] for cell in upper), 7)
        self.assertEqual(upper[0], {'label': '№ п/п', 'span': 1, 'rowspan': 2})
        self.assertEqual(upper[4], {'label': 'Сопротивление изоляции МОм', 'span': 2, 'rowspan': 1})
        self.assertEqual([cell['label'] for cell in lower],
                         ['между проводами (жилами)', 'относи-тельно земли'])

    def test_sp77_added_forms_keep_individual_content_and_signed_date(self):
        folder = ROOT / 'app/forms/СП 77.13330.2016'
        permit = json.loads((folder / 'СП_77_А_20.fields.json').read_text())
        defects = [f for f in permit if f['key'].startswith('t2_r')]
        self.assertEqual([f['required'] for f in defects], [True, False, False])
        self.assertTrue(all(f['kind'] == 'literal' and f['value'] is None for f in defects))
        suspension = json.loads((folder / 'СП_77_А_24.fields.json').read_text())
        dates = [f for f in suspension if f['key'].startswith('p32_')]
        values, missing = resolve_fields(dates, {'act': {'date_signed': '2026-10-29'}}, draft=False)
        self.assertEqual(values, {'p32_1': '29', 'p32_2': 'октября', 'p32_3': '2026'})
        self.assertFalse(missing)
        rows = next(f for f in suspension if f['kind'] == 'table')
        self.assertIsNone(rows['value'])
        self.assertNotIn('source', rows)

    def test_344_work_dates_and_decision_are_individual(self):
        folder = ROOT / 'app/forms/Приказ Минстроя №344_пр'
        for code in ('АОСР', 'АООК', 'АОУСИТО'):
            fields = json.loads((folder / f'МИНСТРОЙ_344_{code}.fields.json').read_text())
            dates = [f for f in fields if f['key'] in ('work_start', 'work_end')]
            roots = {'project': {'smr_start': '2026-01-01', 'smr_end': '2026-12-31'}}
            context, missing = resolve_fields(dates, roots)
            self.assertEqual(set(missing), {'work_start', 'work_end'})
            self.assertNotIn('01.01.2026', context['work_start'])
            overrides = [dict(f, value='2026-10-20') for f in dates]
            context, missing = resolve_fields(merge_fields(dates, overrides), roots, draft=False)
            self.assertEqual(context['work_start'], '20.10.2026')
        fields = json.loads((folder / 'МИНСТРОЙ_344_АООК.fields.json').read_text())
        decision = [f for f in fields if f['key'] == 'decision']
        self.assertEqual(len(decision), 1)
        with self.assertRaisesRegex(ValueError, 'decision'):
            resolve_fields(decision, {}, draft=False)

    def test_344_control_roles_are_distinct_and_missing_person_blocks_final(self):
        fields = json.loads((ROOT / 'app/forms/Приказ Минстроя №344_пр/МИНСТРОЙ_344_АОСР.fields.json').read_text())
        controls = [f for f in fields if f['key'] in ('customer_control_details', 'builder_control_details')]
        people = {
            'customer_control': {'position': 'Инженер', 'fio_short': 'Иванов И. И.', 'order_doc': 'Приказ № 1'},
            'builder_control': {'position': 'Инженер', 'fio_short': 'Петров П. П.', 'order_doc': 'Приказ № 2'},
        }
        context, _ = resolve_fields(controls, {'signatories': people}, draft=False)
        self.assertIn('Иванов И. И.', context['customer_control_details'])
        self.assertIn('Петров П. П.', context['builder_control_details'])
        people['builder_control'] = None
        with self.assertRaisesRegex(ValueError, 'builder_control_details'):
            resolve_fields(controls, {'signatories': people}, draft=False)

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
        catalog = json.loads((ROOT / 'app/templates/catalog.json').read_text())
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
        catalog = json.loads((ROOT / 'app/templates/catalog.json').read_text())
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

    def test_excel_forms_are_editable_and_keep_merged_grid(self):
        from docx import Document
        from openpyxl import load_workbook
        from docx.oxml.ns import qn
        catalog = json.loads((ROOT / 'app/templates/catalog.json').read_text())
        excel = [f for f in catalog if f['source'].endswith('.xlsx')]
        self.assertEqual(len(excel), 16)
        for form in excel:
            with self.subTest(code=form['code']):
                doc = Document(ROOT / form['template'])
                reflowed = form['code'].startswith('СП_77_')
                if reflowed:
                    self.assertGreater(len(doc.paragraphs), 1)
                    for table in doc.tables:
                        self.assertFalse(table.autofit)
                    if any(f['kind'] == 'table' for f in json.loads((ROOT / form['fields']).read_text())):
                        self.assertTrue(doc.tables)
                elif SOURCE_DIR:
                    sheet = load_workbook(source_path(form)).active
                    self.assertEqual(len(doc.tables[0].columns), sheet.max_column)
                if not reflowed:
                    self.assertTrue(doc.tables[0]._tbl.xpath('.//w:gridSpan'))
                self.assertEqual(len(doc.inline_shapes), 0)
                section = doc.sections[0]
                if SOURCE_DIR:
                    sheet = load_workbook(source_path(form)).active
                    self.assertEqual(section.page_width > section.page_height, sheet.page_setup.orientation == 'landscape')
                fields = json.loads((ROOT / form['fields']).read_text())
                self.assertTrue(fields)
                for field in fields:
                    self.assertNotIn(field.get('source'), ('project.smr_start', 'project.smr_end', 'project.pnr_start', 'project.pnr_end'))

    def test_layout_border_override_does_not_turn_spacers_into_input_fields(self):
        from lxml import etree
        spec = importlib.util.spec_from_file_location('prepare_sp', ROOT / 'app/scripts/prepare_sp_templates.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        paragraph = etree.fromstring(b'<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:pPr><w:rPr><w:rFonts w:ascii="Arial"/><w:sz w:val="18"/></w:rPr></w:pPr></w:p>')
        builder.put(paragraph, '{{ value }}')
        self.assertEqual(paragraph.xpath('./w:r/w:rPr/w:sz/@w:val', namespaces=builder.NS), ['18'])
        fields = json.loads((ROOT / 'app/forms/СП 40-102-2000/СП_40_102_2000_Е.fields.json').read_text())
        keys = {f['key'] for f in fields}
        self.assertIn('t0_r0_c1', keys)  # Recipient's underlined answer slot.
        self.assertNotIn('t0_r1_c0', keys)  # Unbordered spacer beside its caption.
        fields = json.loads((ROOT / 'app/forms/СП 42-101-2003/СП_42_101_2003_Т.fields.json').read_text())
        self.assertTrue(any(f['kind'] == 'table' for f in fields))  # Real inherited grid.
