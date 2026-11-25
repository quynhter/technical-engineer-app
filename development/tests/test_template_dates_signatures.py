import json
from pathlib import Path
from itd.acts import find_template
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
