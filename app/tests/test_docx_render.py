import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from itd.docx_render import render_docx


HAS_DOCXTPL = all(importlib.util.find_spec(module) is not None
                 for module in ("docxtpl", "docx", "jinja2"))


@unittest.skipUnless(HAS_DOCXTPL, "Нужны зависимости requirements.txt")
class DocxRenderTests(unittest.TestCase):
    def test_sp77_passport_keeps_grid_with_empty_and_long_legacy_values(self):
        from docx import Document
        root = Path(__file__).resolve().parents[2]
        template = root / 'app/templates/СП 77.13330.2016/СП_77_А_19_УЧАСТОК.docx'
        fields = json.loads((root / 'app/forms/СП 77.13330.2016/СП_77_А_19_УЧАСТОК.fields.json').read_text())
        original = Document(template)
        self.assertEqual(len(original.tables), 1)
        grid = original.tables[0]._tbl.tblGrid.xml
        for long in (False, True):
            context = {f['key']: [] if f['kind'] == 'table' else '' for f in fields}
            if long:
                context['t0_r7_c1'] = 'Длинное название объекта ' * 15
                context['rows_0_18'] = [{f'c{i}': str(i) for i in range(1, 8)}]
            output = Path(self.temp.name) / f'passport-{long}.docx'
            render_docx(template, context, output)
            result = Document(output)
            self.assertEqual(len(result.tables), 1)
            self.assertFalse(result.tables[0].autofit)
            self.assertEqual(result.tables[0]._tbl.tblGrid.xml, grid)
            if long:
                self.assertIn(context['t0_r7_c1'], '\n'.join(p.text for p in result.paragraphs))
            self.assertNotIn('{%', '\n'.join(p.text for p in result.paragraphs))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.template = Path(self.temp.name) / "template.docx"
        self.output = Path(self.temp.name) / "output.docx"

    def test_repeating_rows_and_xml_characters(self):
        from docx import Document
        document = Document()
        document.add_paragraph("Объект {{ object_name }}")
        table = document.add_table(rows=4, cols=2)
        table.cell(0, 0).text = "Наименование"
        table.cell(0, 1).text = "Заводской номер"
        table.cell(1, 0).text = "{%tr for item in materials %}"
        table.cell(2, 0).text = "{{ item.name }}"
        table.cell(2, 1).text = "{{ item.serial }}"
        table.cell(3, 0).text = "{%tr endfor %}"
        document.save(self.template)
        render_docx(self.template, {
            "object_name": "Объект <1> & 2",
            "materials": [{"name": "Прибор А", "serial": "001"},
                          {"name": "Прибор Б", "serial": "002"}],
        }, self.output)
        result = Document(self.output)
        self.assertEqual(result.paragraphs[0].text, "Объект Объект <1> & 2")
        self.assertEqual(len(result.tables[0].rows), 3)
        self.assertEqual(result.tables[0].cell(2, 1).text, "002")

    def test_missing_value_fails_without_creating_output(self):
        from docx import Document
        from jinja2 import UndefinedError
        document = Document()
        document.add_paragraph("Город {{ city }}")
        document.save(self.template)
        with self.assertRaises(UndefinedError):
            render_docx(self.template, {}, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_output_and_template_are_preserved(self):
        from docx import Document
        document = Document()
        document.add_paragraph("{{ city }}")
        document.save(self.template)
        template_bytes = self.template.read_bytes()
        self.output.write_bytes(b"previous version")
        with self.assertRaises(FileExistsError):
            render_docx(self.template, {"city": "Казань"}, self.output)
        self.assertEqual(self.output.read_bytes(), b"previous version")
        with self.assertRaises(ValueError):
            render_docx(self.template, {"city": "Казань"}, self.template)
        self.assertEqual(self.template.read_bytes(), template_bytes)


if __name__ == "__main__":
    unittest.main()
