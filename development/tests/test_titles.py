import json
import tempfile
import unittest
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

from itd.acts import build_context, generate, register_form
from itd.changes import update_record
from itd.db import add_object, add_project, connect, initialize
from itd.managed import generate_managed
from itd.participants import add_organization, assign
from itd.paths import default_templates
from itd.releases import export_package, verify_releases
from itd.titles import CODE, FONTS, add_title, default_fields, export_config, settings


class TitleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="Титульники с пробелами ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "itd.db"
        initialize(self.db)
        with connect(self.db) as c:
            self.obj = add_object(c, 'Школа & корпус <А> "Вторая очередь"')
            self.project = add_project(c, object_id=self.obj, section_code="СПС", code="РД-01", name="Пожарная сигнализация", city="Казань")
            org = add_organization(c, full_name='ООО «Строй & Монтаж»')
            assign(c, entity="organization", entity_id=org, role_key="Подрядчик", object_id=self.obj)

    def add(self, c, **options):
        return add_title(c, self.project, {"year": 2026, **options})["act_id"]

    def test_legacy_roundtrip_and_conflicts_do_not_change_business_data(self):
        with connect(self.db) as c:
            a = self.add(c, copies=2.0, volumes=3.0, font_index=1)
            config = export_config(c, a)
            b = add_title(c, self.project, config)["act_id"]
            first = build_context(c, a)['context']
            second = build_context(c, b)['context']
            first_model = first.pop('_template_context')
            second_model = second.pop('_template_context')
            self.assertEqual(first, second)
            self.assertEqual(first_model['object'], second_model['object'])
            self.assertNotEqual(first_model['document']['number'], second_model['document']['number'])
            config["object"] = "Другое название"
            with self.assertRaisesRegex(ValueError, "object"):
                add_title(c, self.project, config)
            self.assertEqual(c.execute("SELECT count(*) FROM acts").fetchone()[0], 2)
            self.assertEqual(c.execute("SELECT name FROM objects").fetchone()[0], 'Школа & корпус <А> "Вторая очередь"')

    def test_all_pairs_order_and_single_volume_no_label(self):
        with connect(self.db) as c:
            a = self.add(c, copies=2, volumes=2)
            pages = build_context(c, a)["context"]["pages"]
            self.assertEqual([(p["duplicates"], p["volumes_info"]) for p in pages],
                             [("Оригинал", "Том 1 из 2"), ("Оригинал", "Том 2 из 2"),
                              ("2 экз.", "Том 1 из 2"), ("2 экз.", "Том 2 из 2")])
            b = self.add(c)
            self.assertEqual(build_context(c, b)["context"]["pages"], [{"duplicates": "Оригинал", "volumes_info": ""}])

    def test_invalid_and_ambiguous_settings(self):
        for changes in ({"copies": 0}, {"copies": True}, {"volumes": 1.1}, {"volumes": 51},
                        {"year": 2101}, {"year": float("nan")}, {"font_index": 2},
                        {"font": "Unknown"}, {"font": "Arial", "font_index": 1},
                        {"labels": "false"}, {"typo": 1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                settings(changes)

    def test_missing_year_draft_and_final(self):
        with connect(self.db) as c:
            a = add_title(c, self.project, {})["act_id"]
            self.assertIn("year", build_context(c, a)["missing"])
            self.assertIsNone(export_config(c, a)["year"])
            with self.assertRaisesRegex(ValueError, "year"):
                build_context(c, a, draft=False)

    def test_custom_roles_and_project_override(self):
        with connect(self.db) as c:
            org = add_organization(c, full_name="Другой подрядчик")
            assign(c, entity="organization", entity_id=org, role_key="builder", project_id=self.project)
            a = self.add(c, roles={"sub_contractor": "builder"}, sub_contractor="Другой подрядчик")
            self.assertEqual(build_context(c, a)["context"]["contractors_info"], "Другой подрядчик")
            self.assertEqual(export_config(c, a)["roles"]["sub_contractor"], "builder")

    def test_registered_form_not_overwritten(self):
        with connect(self.db) as c:
            register_form(c, code=CODE, name="Моя форма", fields=[])
            with self.assertRaisesRegex(ValueError, "настроена иначе"):
                self.add(c)
            self.assertEqual(c.execute("SELECT fields FROM document_types WHERE code=?", (CODE,)).fetchone()[0], "[]")

    def test_settings_are_revalidated_after_record_update(self):
        with connect(self.db) as c:
            a = self.add(c)
            update_record(c, entity="acts", record_id=a, changes={"fields": [{"key": "copies", "kind": "literal", "value": -1}]})
            with self.assertRaisesRegex(ValueError, "copies"):
                build_context(c, a)

    def test_cli_legacy_config_unicode_paths_and_no_overwrite(self):
        config = self.root / "Настройки титула.json"
        config.write_text(json.dumps({"year": 2026.0, "copies": 2.0, "volumes": 1.0, "font_index": 0}))
        prefix = [sys.executable, "-m", "itd", "--db", str(self.db)]
        created = subprocess.run(prefix + ["title-add", "--project-id", str(self.project), "--data", str(config)], capture_output=True, text=True, check=True)
        act_id = json.loads(created.stdout)["act_id"]
        saved = self.root / "Экспорт настроек.json"
        args = prefix + ["title-config", "--act-id", str(act_id), "--output", str(saved)]
        subprocess.run(args, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(saved.read_text())["copies"], 2)
        before = saved.read_bytes()
        repeated = subprocess.run(args, capture_output=True, text=True)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual(saved.read_bytes(), before)
