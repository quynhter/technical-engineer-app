import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from itd.acts import add_act, generate, register_form, set_resources
from itd.db import add_object, add_project, connect, initialize
from itd.participants import add_organization, add_signatory, assign
from itd.readers import read_document
from itd.resources import CATEGORIES, add_resource
from itd.statement import export_statement


ROOT = Path(__file__).resolve().parents[2]
available = lambda name: importlib.util.find_spec(name) is not None


class ReaderTemplateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    @unittest.skipUnless(available("pypdf"), "Нужен pypdf")
    def test_pdf_without_text_requires_visual_review(self):
        from pypdf import PdfWriter
        source = self.root / "scan.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(source)
        result = read_document(source)
        self.assertEqual(result["parts"][0]["page"], 1)
        self.assertTrue(result["parts"][0]["needs_visual_review"])

    @unittest.skipUnless(available("docx"), "Нужен python-docx")
    def test_docx_reader_preserves_paragraph_table_order(self):
        from docx import Document
        source = self.root / "spec.docx"
        document = Document()
        document.add_paragraph("Заголовок")
        document.add_table(rows=1, cols=1).cell(0, 0).text = "Позиция"
        document.add_paragraph("Примечание")
        document.save(source)
        parts = read_document(source)["parts"]
        self.assertEqual(parts[0]["text"], "Заголовок")
        self.assertEqual(parts[1]["rows"], [["Позиция"]])
        self.assertEqual(parts[2]["text"], "Примечание")

    @unittest.skipUnless(available("openpyxl"), "Нужен openpyxl для окружения без XLSX-движка Codex")
    def test_portable_export_preserves_types_and_literal_formula_text(self):
        from openpyxl import load_workbook
        db = self.root / "itd.db"
        initialize(db)
        with connect(db) as connection:
            obj = add_object(connection, "Объект")
            project = add_project(connection, object_id=obj, section_code="СПС", code="ТЕСТ", name="СПС")
            add_resource(connection, project_id=project, name="=1+1", unit="шт.", spec_num="001",
                         category=CATEGORIES[1], serial_numbers=["0001"], qty_proj=0)
            with patch.dict(os.environ, {"ITD_NODE": "", "ITD_NODE_MODULES": ""}):
                result = export_statement(connection, project_id=project, output=self.root / "statement.xlsx")
        self.assertEqual(result["engine"], "openpyxl")
        book = load_workbook(self.root / "statement.xlsx")
        try:
            sheet = book.active
            self.assertEqual(sheet["A8"].value, "001")
            self.assertEqual(sheet["C8"].value, "=1+1")
            self.assertEqual(sheet["C8"].data_type, "s")
            self.assertEqual(sheet["E8"].value, "0001")
            self.assertEqual(sheet["G8"].value, 0)
            self.assertIsNone(sheet["H8"].value)
            self.assertEqual(sheet["B3"].value, "Объект")
            self.assertEqual(sheet["B4"].value, "СПС (ТЕСТ)")
            self.assertEqual(sheet["A2"].value, "Ведомость оборудования и материалов")
            self.assertEqual(sheet.max_column, 9)
            self.assertEqual([sheet.cell(7, i).value for i in range(1, 10)], list(range(1, 10)))
            self.assertEqual(sheet.freeze_panes, "A8")
        finally:
            book.close()

    @unittest.skipUnless(available("docxtpl") and available("docx"), "Нужен docxtpl")
    def test_actual_prepared_statement_template_generates_from_database(self):
        from docx import Document
        db = self.root / "itd.db"
        initialize(db)
        with connect(db) as connection:
            obj = add_object(connection, "Учебный объект")
            project = add_project(connection, object_id=obj, section_code="СПС", code="ТЕСТ", name="СПС", city="Казань")
            org = add_organization(connection, full_name="Учебная организация", short_name="ООО Тест")
            signer = add_signatory(connection, org_id=org, fio="Иванов И. И.", position="Инженер")
            for role in ("recipient", "consignor"):
                assign(connection, entity="signatory", entity_id=signer, role_key=role, object_id=obj)
            resource = add_resource(connection, project_id=project, name="Прибор", type_mark="ТЕСТ", unit="шт.",
                                    spec_num="1", category=CATEGORIES[1])
            fields = json.loads((ROOT / "app/forms/СП_77_А_21.fields.json").read_text(encoding="utf-8"))
            register_form(connection, code="СП_77_А_21", name="Ведомость", fields=fields, form_group="statement")
            act = add_act(connection, project_id=project, act_type="СП_77_А_21", date_signed="2026-10-26")
            set_resources(connection, act, [resource])
            output = self.root / "statement.docx"
            generate(connection, act_id=act, templates_dir=ROOT / "app/templates", output=output, draft=False)
            doc = Document(output)
            text = "\n".join(p.text for p in doc.paragraphs)
            self.assertIn("Казань", text)
            self.assertEqual(doc.tables[0].cell(2, 2).text, "Прибор")
            self.assertEqual(connection.execute("SELECT mode FROM generated_documents").fetchone()[0], "final")


if __name__ == "__main__":
    unittest.main()
