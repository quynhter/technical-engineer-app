import importlib.util
import tempfile
import unittest
from pathlib import Path

from itd.docx_render import render_docx


HAS_DOCXTPL = all(importlib.util.find_spec(module) is not None
                 for module in ("docxtpl", "docx", "jinja2"))


@unittest.skipUnless(HAS_DOCXTPL, "Нужны зависимости requirements.txt")
class DocxRenderTests(unittest.TestCase):
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
