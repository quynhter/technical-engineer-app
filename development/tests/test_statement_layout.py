"""Пользовательский XLSX: шапка, расширение таблицы и пустой раздел."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from copy import copy
from unittest.mock import patch

from openpyxl import load_workbook

from itd.db import add_object, add_project, connect, initialize
from itd.resources import CATEGORIES, add_resource
from itd.statement import TEMPLATE, export_statement


class StatementLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "itd.db"
        initialize(self.db)

    def check_export(self, node=None, node_modules=None, empty=False):
        before = hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()
        name = ("=Полное наименование объекта, корпус и адрес " + "продолжение наименования " * 30).strip()
        with connect(self.db) as connection:
            obj = add_object(connection, name)
            project = add_project(connection, object_id=obj, section_code="СПС", code="РД-001",
                                  name="Система пожарной сигнализации")
            if not empty:
                for index in range(3):
                    add_resource(connection, project_id=project, name="=1+1" if index == 0 else "Длинное название " * 25,
                                 category=CATEGORIES[1], spec_num=f"00{index}", unit="шт.",
                                 serial_numbers=["0007", "0008"], qty_proj=0 if index == 0 else 2.5)
            with patch.dict(os.environ, {"ITD_NODE": "", "ITD_NODE_MODULES": ""}):
                result = export_statement(connection, project_id=project, output=self.root / "result.xlsx",
                                          node=node, node_modules=node_modules)
        self.assertEqual(hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(), before)
        self.assertEqual(result["rows"], 0 if empty else 3)
        book = load_workbook(result["output"])
        source = load_workbook(TEMPLATE)
        try:
            sheet = book.active
            self.assertEqual(sheet["B3"].value, name)
            self.assertEqual(sheet["B3"].data_type, "s")
            self.assertEqual(sheet["B4"].value, "Система пожарной сигнализации (РД-001)")
            self.assertGreater(sheet.row_dimensions[3].height, 21)
            self.assertEqual(sheet.max_column, 9)
            self.assertEqual(set(str(r) for r in sheet.merged_cells), {"A2:I2", "B3:I3", "B4:I4"})
            self.assertEqual(sheet.freeze_panes, "A8")
            self.assertEqual([sheet.cell(6, col).value for col in range(1, 10)],
                             [source.active.cell(6, col).value for col in range(1, 10)])
            if empty:
                self.assertEqual(sheet["C8"].value, "Ресурсы пока не внесены")
                self.assertIsNone(sheet["G8"].value)
            else:
                self.assertEqual(sheet["C8"].value, "=1+1")
                self.assertEqual(sheet["C8"].data_type, "s")
                self.assertEqual(sheet["A8"].value, "000")
                self.assertIn("0007", sheet["E8"].value)
                self.assertEqual(sheet["G8"].value, 0)
                self.assertIsNone(sheet["H8"].value)
                self.assertEqual(sheet["G10"].value, 2.5)
                self.assertGreater(sheet.row_dimensions[10].height, 28)
                for col in range(1, 10):
                    self.assertEqual(copy(sheet.cell(10, col).border), copy(sheet.cell(8, col).border))
                    self.assertEqual(sheet.cell(10, col).fill.patternType, source.active.cell(8, col).fill.patternType)
        finally:
            book.close()
            source.close()

    def test_long_values_and_extended_body_preserve_template(self):
        self.check_export()

    def test_empty_section_keeps_headers_and_no_fictitious_quantities(self):
        self.check_export(empty=True)

    @unittest.skipUnless(os.environ.get("ITD_TEST_NODE") and os.environ.get("ITD_TEST_NODE_MODULES"),
                         "Для интеграционной проверки задайте ITD_TEST_NODE и ITD_TEST_NODE_MODULES")
    def test_artifact_engine_uses_same_template_and_literal_values(self):
        self.check_export(node=os.environ["ITD_TEST_NODE"], node_modules=os.environ["ITD_TEST_NODE_MODULES"])

    @unittest.skipUnless(os.environ.get("ITD_TEST_NODE") and os.environ.get("ITD_TEST_NODE_MODULES"),
                         "Для интеграционной проверки задайте ITD_TEST_NODE и ITD_TEST_NODE_MODULES")
    def test_artifact_engine_empty_section(self):
        self.check_export(node=os.environ["ITD_TEST_NODE"], node_modules=os.environ["ITD_TEST_NODE_MODULES"], empty=True)
