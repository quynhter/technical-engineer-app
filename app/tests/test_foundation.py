import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from itd.db import add_object, add_project, calendar_date, connect, initialize


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "itd.db"
        initialize(self.path)

    def project(self, connection, object_id, **values):
        return add_project(connection, object_id=object_id, section_code="СПС",
                           code="ТЕСТ-СПС", name="Пожарная сигнализация", **values)

    def test_section_uniqueness_is_scoped_to_object(self):
        with connect(self.path) as connection:
            first = add_object(connection, "Объект1")
            second = add_object(connection, "Объект2")
            self.project(connection, first)
            self.project(connection, second)
            with self.assertRaises(sqlite3.IntegrityError):
                self.project(connection, first)

    def test_foreign_keys_and_restrict_deletion(self):
        with connect(self.path) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                self.project(connection, 999)
            obj = add_object(connection, "Объект")
            self.project(connection, obj)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM objects WHERE id = ?", (obj,))

    def test_dates_are_valid_and_unknown_stays_null(self):
        for invalid in ("2026-02-29", "2026-13-01", "20260527", "2026-5-27", ""):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                calendar_date(invalid)
        self.assertEqual(calendar_date("2024-02-29"), "2024-02-29")
        with connect(self.path) as connection:
            obj = add_object(connection, "Объект")
            with self.assertRaises(ValueError):
                self.project(connection, obj, smr_start="2026-06-01", smr_end="2026-05-01")
            self.project(connection, obj)
            row = connection.execute("SELECT smr_start, pnr_end FROM projects").fetchone()
            self.assertEqual(tuple(row), (None, None))

    def test_init_is_repeatable_and_preserves_data(self):
        with connect(self.path) as connection:
            add_object(connection, "Объект")
        initialize(self.path)
        with connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM objects").fetchone()[0], 1)

    def test_legacy_schema_is_not_silently_modified(self):
        path = Path(self.temp.name) / "legacy.db"
        with connect(path) as connection:
            connection.execute("CREATE TABLE projects (code TEXT)")
        with self.assertRaises(ValueError):
            initialize(path)

    def test_failed_migration_rolls_back_schema_and_version(self):
        migrations = Path(self.temp.name) / "migrations"
        migrations.mkdir()
        (migrations / "999_broken.sql").write_text(
            "CREATE TABLE transient_table (id INTEGER);\nINVALID SQL;\n", encoding="utf-8"
        )
        with patch("itd.db.MIGRATIONS", migrations), self.assertRaises(sqlite3.Error):
            initialize(self.path)
        with connect(self.path) as connection:
            self.assertIsNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE name='transient_table'"
            ).fetchone())
            self.assertIsNone(connection.execute(
                "SELECT version FROM schema_migrations WHERE version=999"
            ).fetchone())


if __name__ == "__main__":
    unittest.main()
