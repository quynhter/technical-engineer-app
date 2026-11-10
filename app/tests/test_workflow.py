import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from itd.acts import add_act, register_form
from itd.archive import import_file, link_file
from itd.changes import update_record
from itd.db import add_object, add_project, connect, initialize
from itd.registry import registry_rows
from itd.resources import CATEGORIES, add_resource
from itd.specification import import_specification
from itd.statement import statement_data


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "itd.db"
        initialize(self.path)
        with connect(self.path) as connection:
            self.obj = add_object(connection, "Объект")
            self.project = add_project(connection, object_id=self.obj, section_code="СПС", code="ТЕСТ", name="СПС")

    def attachment(self, connection, kind, name, date=None):
        source = self.root / (name + ".pdf")
        source.write_bytes(name.encode())
        result = import_file(connection, archive_root=self.root / "archive", source=source,
                             doc_type=kind, title=name, doc_date=date)
        link_file(connection, attachment_id=result["id"], entity="project", entity_id=self.project)
        return result["id"]

    def test_registry_self_first_and_undated_documents_last(self):
        with connect(self.path) as connection:
            register_form(connection, code="РЕЕСТР", name="Реестр ИТД", fields=[], form_group="registry")
            registry = add_act(connection, project_id=self.project, act_type="РЕЕСТР", date_signed="2026-10-26")
            register_form(connection, code="АКТ", name="Акт", fields=[])
            add_act(connection, project_id=self.project, act_type="АКТ", date_signed="2026-09-01")
            self.attachment(connection, "rd", "РД", "2026-01-01")
            self.attachment(connection, "order", "Приказ", "2026-01-02")
            self.attachment(connection, "certificate", "Без даты")
            rows = registry_rows(connection, self.project, registry_act_id=registry)
            self.assertEqual([row["name"] for row in rows], ["Реестр ИТД", "Рабочая документация «ТЕСТ»", "Приказ", "Акт", "Без даты"])
            self.assertEqual(rows[3]["number"], "")
            self.assertIn("Дата не указана", rows[-1]["note"])
            with self.assertRaises(ValueError):
                registry_rows(connection, self.project, registry_act_id=registry + 1)

    def test_registry_dates_live_journals_and_excludes_import_source(self):
        from itd.workspace import save_entry
        with connect(self.path) as c:
            source = self.attachment(c, 'other', 'Книга1.xlsx')
            c.execute("INSERT INTO resource_imports VALUES (?, ?, ?, ?, ?, ?)",
                      ('import', self.project, 'Книга1.xlsx', 'sha', b'xlsx', source))
            self.attachment(c, 'rd', 'исходное имя', '2026-01-01')
            save_entry(c, self.project, dict(kind='work', work_type='cable', title='Монтаж', entry_date='2026-01-02'))
            save_entry(c, self.project, dict(kind='incoming', title='Контроль', entry_date='2026-01-03'))
            rows = registry_rows(c, self.project, detailed=True)
            self.assertEqual([r['date'] for r in rows],
                             ['2026-01-01', '2026-01-02', '2026-01-02', '2026-01-03'])
            self.assertEqual({r['id'] for r in rows if r['entity']=='journal'}, {'ojr', 'incoming', 'cable'})
            self.assertEqual(c.execute('SELECT title FROM attachments WHERE id=?', (source,)).fetchone()[0],
                             'Книга1.xlsx')

    def test_journal_date_confirmation_is_atomic_and_end_extends_automatically(self):
        from itd.workspace import JournalDatesConfirmation, save_entry
        with connect(self.path) as c:
            c.execute("UPDATE objects SET work_start='2026-10-02', work_end='2026-10-05' WHERE id=?", (self.obj,))
            c.execute("UPDATE projects SET smr_start='2026-10-03', smr_end='2026-10-06' WHERE id=?", (self.project,))
            entry = dict(kind='incoming', title='Контроль', entry_date='2026-10-01')
            with self.assertRaises(JournalDatesConfirmation) as caught:
                save_entry(c, self.project, entry)
            self.assertEqual(c.execute('SELECT count(*) FROM workspace_entries').fetchone()[0], 0)
            self.assertEqual(len(caught.exception.journal_dates), 2)
            save_entry(c, self.project, {**entry, 'journal_dates_confirmation': caught.exception.journal_dates})
            save_entry(c, self.project, {**entry, 'entry_date': '2026-10-10'})
            self.assertEqual(tuple(c.execute('SELECT work_start, work_end FROM objects WHERE id=?', (self.obj,)).fetchone()),
                             ('2026-10-01', '2026-10-10'))
            self.assertEqual(tuple(c.execute('SELECT smr_start, smr_end FROM projects WHERE id=?', (self.project,)).fetchone()),
                             ('2026-10-01', '2026-10-10'))
            journal = save_entry(c, self.project, dict(kind='journal', title='Осмотр', entry_date='2026-10-02',
                work_fields={'journal_section':'4', 'issued_date':'2026-01-01', 'transfer_date':'2027-01-01'}))
            self.assertEqual(json.loads(journal['work_fields']), {'journal_section':'4'})
            self.assertEqual(tuple(c.execute('SELECT smr_start, smr_end FROM projects WHERE id=?', (self.project,)).fetchone()),
                             ('2026-10-01', '2026-10-10'))

    def test_incoming_day_saves_distinct_resources_and_their_document_types(self):
        from base64 import b64encode
        from itd.incoming import save_incoming_day
        from itd.workflow import report
        with connect(self.path) as c:
            ids = [add_resource(c, project_id=self.project, name=name, unit='шт.', category=CATEGORIES[0])
                   for name in ('Ресурс 1', 'Ресурс 2')]
            first = dict(resource_id=ids[0], result='accepted', quantity=1, document_type='passport',
                         file={'name': 'Паспорт.pdf', 'content': b64encode(b'passport').decode()})
            second = dict(resource_id=ids[1], result='pending')
            day = {'date': '2026-10-01', 'resources': [first, first]}
            with self.assertRaisesRegex(ValueError, 'повторяется'):
                save_incoming_day(c, self.project, day, self.root / 'archive')
            self.assertEqual(c.execute('SELECT count(*) FROM attachments').fetchone()[0], 0)
            day['resources'] = [first, second]
            entries = save_incoming_day(c, self.project, day, self.root / 'archive')['entries']
            self.assertEqual([row['resource_id'] for row in entries], ids)
            self.assertEqual(json.loads(entries[0]['work_fields'])['incoming_document_type'], 'passport')
            self.assertIsNotNone(entries[0]['attachment_id'])
            self.assertIsNone(entries[1]['attachment_id'])
            self.assertTrue(any(f['code']=='quality_unreviewed' for f in report(c, self.project)['findings']))
            with self.assertRaisesRegex(ValueError, 'уже записан'):
                save_incoming_day(c, self.project, day, self.root / 'archive')
            saved = entries[0]
            day['resources'] = [dict(resource_id=ids[0], id=saved['id'], revision=saved['revision'],
                result='accepted', review={'status':'matches', 'checked_by':'Инженер', 'note':'Сверена маркировка'})]
            checked = save_incoming_day(c, self.project, day, self.root / 'archive')['entries'][0]
            self.assertTrue(json.loads(checked['work_fields'])['quality_review_id'])
            self.assertFalse(any(f['code']=='quality_unreviewed' for f in report(c, self.project)['findings']))

    def test_edits_keep_audit_and_reject_stale_expected_data(self):
        with connect(self.path) as connection:
            update_record(connection, entity="projects", record_id=self.project, changes={"city": "Казань"}, expected={"city": None})
            with self.assertRaises(ValueError):
                update_record(connection, entity="projects", record_id=self.project, changes={"city": "Самара"}, expected={"city": None})
            event = connection.execute("SELECT * FROM audit_events").fetchone()
            self.assertIsNone(json.loads(event["before_json"])["city"])
            self.assertEqual(json.loads(event["after_json"])["city"], "Казань")

    def test_spec_import_is_idempotent_preserves_user_edits_and_skips_uncertain(self):
        with connect(self.path) as connection:
            source = self.attachment(connection, "rd", "Спецификация")
            item = {"source_key": "page:1/row:1", "page": 1, "verified": True,
                    "resource": {"name": "Кабель", "spec_num": "1", "category": CATEGORIES[3], "unit": "м", "qty_proj": 100}}
            report = import_specification(connection, project_id=self.project, attachment_id=source,
                                           items=[item, {"source_key": "page:1/row:2", "verified": False}])
            resource = report["imported"][0]
            self.assertEqual(report["pending"], ["page:1/row:2"])
            update_record(connection, entity="resources", record_id=resource, changes={"qty_fact": 90})
            repeat = import_specification(connection, project_id=self.project, attachment_id=source, items=[item])
            self.assertEqual(repeat["duplicates"], [resource])
            self.assertEqual(connection.execute("SELECT qty_fact FROM resources WHERE id=?", (resource,)).fetchone()[0], 90)
            self.assertEqual(connection.execute("SELECT page FROM resource_sources").fetchone()[0], 1)

    def test_statement_preserves_zero_unknown_and_quality_links(self):
        with connect(self.path) as connection:
            resource = add_resource(connection, project_id=self.project, name="Кабель", unit="м", category=CATEGORIES[3], qty_proj=0)
            passport = self.attachment(connection, "passport", "Паспорт", "2026-01-01")
            link_file(connection, attachment_id=passport, entity="resource", entity_id=resource)
            row = statement_data(connection, self.project)["rows"][0]
            self.assertEqual(row[6], 0)
            self.assertIsNone(row[7])
            self.assertIn("Паспорт", row[8])

    def test_backup_command_produces_readable_copy_without_overwriting(self):
        target = self.root / "backup.db"
        command = [sys.executable, "-m", "itd", "--db", str(self.path), "backup", "--output", str(target)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        with connect(target) as connection:
            self.assertEqual(connection.execute("SELECT name FROM objects").fetchone()[0], "Объект")
        second = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertNotEqual(second.returncode, 0)


if __name__ == "__main__":
    unittest.main()
