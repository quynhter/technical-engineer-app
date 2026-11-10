import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

from itd.acts import add_act, build_context, generate, register_form, set_resources
from itd.db import add_object, add_project, connect, initialize
from itd.fields import resolve_fields, validate_fields
from itd.layout import GROUPS, create_layout, path_component
from itd.resources import CATEGORIES, add_resource


class ActTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "itd.db"
        initialize(self.path)
        self.fields = [{"key": "city", "kind": "reference", "source": "project.city", "required": True}]
        with connect(self.path) as connection:
            obj = add_object(connection, "Объект1")
            self.project = add_project(connection, object_id=obj, section_code="СПС", code="ТЕСТ", name="СПС")
            self.other = add_project(connection, object_id=obj, section_code="АОВ", code="ТЕСТ-АОВ", name="АОВ")
            register_form(connection, code="ТЕСТ", name="Тестовая форма", fields=self.fields)

    def test_numbering_is_per_project_and_shared_between_types(self):
        with connect(self.path) as connection:
            register_form(connection, code="ДРУГОЙ", name="Другая форма", fields=[])
            add_act(connection, project_id=self.project, act_type="ТЕСТ")
            add_act(connection, project_id=self.project, act_type="ДРУГОЙ")
            add_act(connection, project_id=self.other, act_type="ТЕСТ")
            numbers = [row[0] for row in connection.execute("SELECT act_num FROM acts ORDER BY id")]
            self.assertEqual(numbers, ["01/СПС", "02/СПС", "01/АОВ"])

    def test_current_database_is_used_and_final_rejects_missing(self):
        with connect(self.path) as connection:
            act = add_act(connection, project_id=self.project, act_type="ТЕСТ")
            prepared = build_context(connection, act)
            self.assertEqual(prepared["missing"], ["city"])
            self.assertIn("УТОЧНИТЬ", prepared["context"]["city"])
            with self.assertRaises(ValueError):
                build_context(connection, act, draft=False)
            connection.execute("UPDATE projects SET city='Казань' WHERE id=?", (self.project,))
            self.assertEqual(build_context(connection, act, draft=False)["context"]["city"], "Казань")
            self.assertNotIn("act_num", build_context(connection, act)["context"])
            connection.execute("UPDATE projects SET city='Самара' WHERE id=?", (self.project,))
            self.assertEqual(build_context(connection, act)["context"]["city"], "Самара")

    def test_resources_keep_explicit_order_and_cannot_cross_projects(self):
        with connect(self.path) as connection:
            act = add_act(connection, project_id=self.project, act_type="ТЕСТ")
            first = add_resource(connection, project_id=self.project, name="Первый", unit="шт.", category=CATEGORIES[1])
            second = add_resource(connection, project_id=self.project, name="Второй", unit="шт.", category=CATEGORIES[1])
            other = add_resource(connection, project_id=self.other, name="Чужой", unit="шт.", category=CATEGORIES[1])
            set_resources(connection, act, [second, first])
            with self.assertRaises(sqlite3.IntegrityError):
                set_resources(connection, act, [other])
            actual = [row[0] for row in connection.execute(
                "SELECT resource_id FROM act_resources WHERE act_id=? ORDER BY ordinal", (act,))]
            self.assertEqual(actual, [second, first])
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE resources SET project_id=? WHERE id=?", (self.other, first))

    def test_dates_and_individual_overrides(self):
        with connect(self.path) as connection:
            register_form(connection, code="ДАТЫ", name="Даты", fields=[
                {"key": "signed", "kind": "reference", "source": "act.date_signed", "format": "date_ru"},
                {"key": "month", "kind": "reference", "source": "act.date_signed", "format": "month_genitive_ru"},
                {"key": "started", "kind": "reference", "source": "project.smr_start", "format": "date_ru"},
            ])
            connection.execute("UPDATE projects SET smr_start='2026-05-27' WHERE id=?", (self.project,))
            act = add_act(connection, project_id=self.project, act_type="ДАТЫ", date_signed="2026-10-26", fields=[
                {"key": "started", "kind": "literal", "value_type": "date", "value": "2026-05-29", "format": "date_ru"},
            ])
            context = build_context(connection, act)["context"]
            self.assertEqual(context, {"signed": "26.10.2026", "month": "октября", "started": "29.05.2026"})

    def test_act_creation_respects_outer_transaction_rollback(self):
        with self.assertRaises(RuntimeError):
            with connect(self.path) as connection:
                add_act(connection, project_id=self.project, act_type="ТЕСТ")
                raise RuntimeError("abort")
        with connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM acts").fetchone()[0], 0)

    def test_layout_and_name_collision(self):
        with connect(self.path) as connection:
            result = create_layout(connection, self.project, self.root / "ИТД")
            self.assertTrue(all((Path(result["directory"]) / group).is_dir() for group in GROUPS))
            create_layout(connection, self.project, self.root / "ИТД")
            another_object = add_object(connection, "Объект1")
            project = add_project(connection, object_id=another_object, section_code="СПС", code="X", name="X")
            with self.assertRaises(ValueError):
                create_layout(connection, project, self.root / "ИТД")
        self.assertEqual(path_component("CON"), "_CON")
        self.assertEqual(path_component("СПС/АОВ"), "СПС_АОВ")

    @unittest.skipUnless(importlib.util.find_spec("docxtpl") and importlib.util.find_spec("docx"), "Нужен docxtpl")
    def test_database_to_docx_end_to_end(self):
        from docx import Document
        document = Document()
        document.add_paragraph("Город {{ city }}")
        document.save(self.root / "ТЕСТ.docx")
        with connect(self.path) as connection:
            act = add_act(connection, project_id=self.project, act_type="ТЕСТ")
            with self.assertRaises(ValueError):
                generate(connection, act_id=act, templates_dir=self.root, output=self.root / "blocked.docx", draft=False)
            self.assertFalse((self.root / "blocked.docx").exists())
            connection.execute("UPDATE projects SET city='Казань' WHERE id=?", (self.project,))
            generate(connection, act_id=act, templates_dir=self.root, output=self.root / "result.docx", draft=False)
            self.assertEqual(Document(self.root / "result.docx").paragraphs[0].text, "Город Казань")


class FieldTests(unittest.TestCase):
    def test_zero_is_present_and_required_table_values_are_checked(self):
        fields = [{"key": "rows", "kind": "table", "source": "resources", "required": True, "fields": [
            {"key": "qty", "kind": "reference", "source": "item.qty", "required": True},
        ]}]
        context, missing = resolve_fields(fields, {"resources": [{"qty": 0}]}, draft=False)
        self.assertEqual(context["rows"][0]["qty"], 0)
        self.assertEqual(missing, [])
        with self.assertRaises(ValueError):
            resolve_fields(fields, {"resources": [{}]}, draft=False)

    def test_code_and_unknown_operations_are_not_executed(self):
        for field in (
            {"key": "x", "kind": "sql", "source": "DROP TABLE acts"},
            {"key": "x", "kind": "reference", "source": "project.__class__()"},
        ):
            with self.assertRaises(ValueError):
                validate_fields([field])


if __name__ == "__main__":
    unittest.main()
