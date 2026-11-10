import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from itd.db import add_object, add_project, connect, initialize
from itd.resources import CATEGORIES, add_resource, add_scheme, quantity


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "itd.db"
        initialize(self.path)
        with connect(self.path) as connection:
            obj = add_object(connection, "Объект")
            self.project = add_project(connection, object_id=obj, section_code="СПС",
                                       code="ТЕСТ-СПС", name="СПС")

    def test_serials_stay_in_one_position_and_actual_is_unknown(self):
        with connect(self.path) as connection:
            add_resource(connection, project_id=self.project, name="Извещатель", unit="шт.",
                         category=CATEGORIES[1], qty_proj=10, serial_numbers=["001", "002"])
            rows = connection.execute("SELECT * FROM resources").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["serial_num"], "001\n002")
            self.assertEqual(rows[0]["qty_proj"], 10)
            self.assertIsNone(rows[0]["qty_fact"])

    def test_invalid_quantities_and_missing_project_are_rejected(self):
        for value in (-1, float("nan"), float("inf"), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                quantity(value, "количество")
        with connect(self.path) as connection, self.assertRaises(sqlite3.IntegrityError):
            add_resource(connection, project_id=9999, name="Кабель", unit="м", category=CATEGORIES[3])

    def test_actual_may_exceed_design_without_overwriting_it(self):
        with connect(self.path) as connection:
            add_resource(connection, project_id=self.project, name="Кабель", unit="м",
                         category=CATEGORIES[3], qty_proj=100, qty_fact=110)
            row = connection.execute("SELECT qty_proj, qty_fact FROM resources").fetchone()
            self.assertEqual(tuple(row), (100, 110))

    def test_scheme_uses_id_without_inventory_code(self):
        with connect(self.path) as connection:
            scheme_id = add_scheme(connection, project_id=self.project, num="1",
                                   name="Схема прокладки", sheets_count=2)
            row = connection.execute("SELECT * FROM schemes WHERE id=?", (scheme_id,)).fetchone()
            self.assertNotIn("in_code", row.keys())
            self.assertEqual(row["sheets_count"], 2)
            with self.assertRaises(ValueError):
                add_scheme(connection, project_id=self.project, num="2", name="Схема", sheets_count=0)

    def test_cli_add_and_filter_resources(self):
        result = subprocess.run(
            [sys.executable, "-m", "itd", "--db", str(self.path), "resource-add",
             "--project-id", str(self.project), "--name", "Извещатель", "--unit", "шт.",
             "--category", CATEGORIES[1],
             "--qty-proj", "2", "--serial", "001", "--serial", "002"],
            capture_output=True, text=True, check=True,
        )
        resource_id = json.loads(result.stdout)["id"]
        listing = subprocess.run(
            [sys.executable, "-m", "itd", "--db", str(self.path), "list", "resources",
             "--project-id", str(self.project)],
            capture_output=True, text=True, check=True,
        )
        rows = json.loads(listing.stdout)
        self.assertEqual(rows[0]["id"], resource_id)
        self.assertEqual(rows[0]["serial_num"], "001\n002")

    def test_category_is_strict_in_api_and_database(self):
        with connect(self.path) as connection:
            with self.assertRaises(ValueError):
                add_resource(connection, project_id=self.project, name="Ресурс", unit="шт.", category="ЗИП")
            for category in (None, "ЗИП", ""):
                with self.subTest(category=category), self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO resources (project_id, name, unit, category) VALUES (?, ?, ?, ?)",
                        (self.project, "Ресурс", "шт.", category),
                    )

    def test_category_migration_preserves_valid_existing_rows(self):
        old_path = Path(self.temp.name) / "old.db"
        from unittest.mock import patch
        from itd.db import MIGRATIONS
        old_migrations = Path(self.temp.name) / "old-migrations"
        old_migrations.mkdir()
        for name in ("001_objects_projects.sql", "002_resources_schemes.sql"):
            (old_migrations / name).write_bytes((MIGRATIONS / name).read_bytes())
        with patch("itd.db.MIGRATIONS", old_migrations):
            initialize(old_path)
        with connect(old_path) as connection:
            obj = add_object(connection, "Объект")
            project = add_project(connection, object_id=obj, section_code="СПС", code="ТЕСТ", name="СПС")
            resource = add_resource(connection, project_id=project, name="Кабель", unit="м",
                                    category=CATEGORIES[3], qty_fact=0)
        initialize(old_path)
        with connect(old_path) as connection:
            row = connection.execute("SELECT * FROM resources WHERE id=?", (resource,)).fetchone()
            self.assertEqual(row["category"], CATEGORIES[3])
            self.assertEqual(row["qty_fact"], 0)


if __name__ == "__main__":
    unittest.main()
