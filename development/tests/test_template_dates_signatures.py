import json
from pathlib import Path
import tempfile
import unittest

from docx import Document
from itd.fields import resolve_fields
from itd.form_defaults import apply_form_defaults, date_groups
from itd.form_catalog import catalog, catalog_fields
from itd.docx_render import render_docx
from itd.template_objects import build_template_context, CONTEXT_KEY

ROOT = Path(__file__).resolve().parents[2]


class TemplateDatesSignaturesTests(unittest.TestCase):
    def fields(self, code):
        return catalog_fields(next(f for f in catalog() if f['code'] == code))

    def test_section_installation_dates_are_live_and_manual_overrides_survive(self):
        code = 'СП_77_А_5'
        fields = apply_form_defaults(code, self.fields(code))
        fields = [f for f in fields if f.get('date_group')]
        for start in ('2025-01-02', '2026-11-13'):
            values, gaps = resolve_fields(fields, {'project': {'smr_start': start, 'smr_end': '2026-11-14'}}, draft=False)
            self.assertEqual(values['t4_r0_c2'], start[-2:])
            self.assertEqual(values['t4_r0_c6'], start[:4])
            self.assertFalse(gaps)
        fields[0] = {**fields[0], 'kind': 'literal', 'value': '2024-02-29'}
        fields = apply_form_defaults(code, fields)
        values, _ = resolve_fields(fields, {'project': {'smr_end': '2026-11-14'}}, draft=False)
        self.assertEqual([values[k] for k in ('t4_r0_c2', 't4_r0_c4', 't4_r0_c6')], ['29', 'февраля', '2024'])

    def test_each_split_date_has_one_calendar_input_and_prints_all_parts(self):
        for code, groups in date_groups().items():
            fields = apply_form_defaults(code, self.fields(code))
            self.assertEqual(fields, apply_form_defaults(code, fields), code)
            for group in groups:
                keys = group['parts']
                selected = [f for f in fields if f['key'] in keys.values()]
                self.assertEqual(len(selected), 3, code)
                for f in selected:
                    self.assertNotIn(f['label'], ('"', '20'))
                    if f['key'] == keys['day']:
                        f.update(kind='literal', value='2024-02-29')
                selected = apply_form_defaults(code, selected)
                values, _ = resolve_fields(selected, {}, draft=False)
                self.assertEqual([values[keys[p]] for p in ('day','month','year')], ['29','февраля','2024'], code)

    def test_legacy_split_values_and_hidden_states_are_preserved(self):
        code = 'СП_77_А_5'
        fields = self.fields(code)
        for f in fields:
            if f['key'] in ('t4_r0_c2', 't4_r0_c4', 't4_r0_c6'):
                f['value'] = {'t4_r0_c2':'07', 't4_r0_c4':'мая', 't4_r0_c6':'2025'}[f['key']]
        fields = apply_form_defaults(code, fields)
        values, _ = resolve_fields(fields, {})
        self.assertEqual([values[k] for k in ('t4_r0_c2','t4_r0_c4','t4_r0_c6')], ['07','мая','2025'])

    def test_other_people_use_each_of_the_three_reference_layouts(self):
        people = [{'role':f'Иное лицо {i}', 'position':'Инженер', 'organization':'ООО Тест',
                   'fio':f'Тестов Т. {i}.', 'authority':'Приказ № 12'} for i in range(1,4)]
        with tempfile.TemporaryDirectory() as tmp:
            for code in ('СП_77_А_3','СП_77_А_5','МИНСТРОЙ_344_АОСР'):
                fields = self.fields(code)
                values, _ = resolve_fields(apply_form_defaults(code, fields), {}, draft=True)
                model = build_template_context(code, values, fields=fields)
                output = Path(tmp)/(code+'.docx')
                render_docx(next((ROOT/'app/templates').rglob(code+'.docx')),
                            {**values, CONTEXT_KEY:model, '_additional_signatories':people}, output, draft=True)
                doc = Document(output)
                text = '\n'.join(p.text for p in doc.paragraphs) + '\n' + '\n'.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
                for person in people:
                    self.assertEqual(text.count(person['role']), 1, code)
                    self.assertIn(person['fio'], text)
                self.assertIn('Приказ № 12', text)
                self.assertNotIn('{{', text)

    def test_signature_in_full_page_grid_does_not_duplicate_document_rows(self):
        from itd.signature_layout import append_signatories
        doc = Document()
        table = doc.add_table(rows=8, cols=2)
        table.cell(0, 0).text = 'Уникальная строка измерений'
        table.cell(6, 0).text = 'Представитель заказчика'
        table.cell(7, 0).text = '(подпись)'
        append_signatories(doc, [{'role':'Иное лицо 1', 'fio':'Тестов Т. Т.'}])
        self.assertEqual(len(doc.tables), 2)
        self.assertEqual(len(doc.tables[1].rows), 2)
        self.assertNotIn('Уникальная строка измерений', doc.tables[1]._tbl.xml)

    def test_complete_year_does_not_repeat_printed_century(self):
        code = 'СП_42_101_2003_Р'
        fields = apply_form_defaults(code, self.fields(code))
        for f in fields:
            if f.get('date_group') == f['key']:
                f.update(kind='literal', value='2024-02-29')
        fields = apply_form_defaults(code, fields)
        values, _ = resolve_fields(fields, {}, draft=True)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'out.docx'
            render_docx(next((ROOT/'app/templates').rglob(code+'.docx')),
                        {**values, CONTEXT_KEY:build_template_context(code, values, fields=fields)}, output, draft=True)
            from docx.oxml.ns import qn
            text = ''.join(t.text or '' for t in Document(output)._element.iter(qn('w:t')))
            self.assertIn('2024', text)
            self.assertNotIn('202024', ''.join(text.split()))
