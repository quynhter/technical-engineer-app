import sqlite3
import tempfile
import unittest
from pathlib import Path

from itd.archive import archived_path, import_file, link_file
from itd.db import add_object, add_project, connect, initialize
from itd.fields import resolve_fields
from itd.participants import add_organization, add_signatory, assign, participants_context


class ArchiveParticipantTests(unittest.TestCase):
    def test_company_print_roles_are_russian_and_keep_assignment_keys(self):
        with connect(self.path) as connection:
            org = add_organization(connection, full_name='Полная организация', short_name='ООО Пример')
            for role in ('customer', 'technical_customer', 'installer', 'custom_role'):
                assign(connection, entity='organization', entity_id=org,
                       role_key=role, object_id=self.obj)
            companies = participants_context(connection, self.project)['companies']
            names = {c['role_key']: c['role'] for c in companies}
            self.assertEqual(names, {'customer': 'Заказчик', 'technical_customer': 'Технический заказчик',
                                    'installer': 'Монтажная организация', 'custom_role': 'custom_role'})
            self.assertTrue(all(c['name'] == 'ООО Пример' for c in companies))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "itd.db"
        self.archive = self.root / "archive"
        initialize(self.path)
        with connect(self.path) as connection:
            self.obj = add_object(connection, "Объект")
            self.project = add_project(connection, object_id=self.obj, section_code="СПС", code="ТЕСТ", name="СПС")
            self.other = add_project(connection, object_id=self.obj, section_code="АОВ", code="ТЕСТ-АОВ", name="АОВ")

    def test_project_source_folders_keep_originals_and_do_not_overwrite(self):
        from itd.archive import publish_project_file
        source=self.root/'Исходник.pdf';source.write_bytes(b'original RD')
        with connect(self.path) as c:
            item=import_file(c,archive_root=self.archive,source=source,doc_type='rd',title='РД')
            location=publish_project_file(c,attachment_id=item['id'],project_id=self.project,archive_root=self.archive)
            target=self.root/location
            self.assertEqual(target,self.root/'ИТД'/'Объект'/'СПС'/'Рабочая документация'/'Исходник.pdf')
            self.assertEqual(target.read_bytes(),b'original RD')
            self.assertEqual(publish_project_file(c,attachment_id=item['id'],project_id=self.project,archive_root=self.archive),location)
            self.assertEqual(len(list(target.parent.iterdir())),1)
            target.write_bytes(b'user edited file')
            second=self.root/publish_project_file(c,attachment_id=item['id'],project_id=self.project,archive_root=self.archive)
            self.assertNotEqual(second,target)
            self.assertEqual(target.read_bytes(),b'user edited file')
            self.assertEqual(second.read_bytes(),b'original RD')
            self.assertEqual(source.read_bytes(),b'original RD')
            other=self.root/publish_project_file(c,attachment_id=item['id'],project_id=self.other,archive_root=self.archive)
            self.assertIn('АОВ',other.parts)
            source.write_bytes(b'contract')
            contract=import_file(c,archive_root=self.archive,source=source,doc_type='other',title='Договор')
            original=self.root/publish_project_file(c,attachment_id=contract['id'],project_id=self.project,archive_root=self.archive)
            self.assertEqual(original.parent.name,'Исходные файлы')
            self.assertFalse((self.root/'ИТД'/'Объект'/'СПС'/'06_РД').exists())

    def test_project_source_folder_rejects_escape_and_corrupt_archive(self):
        from itd.archive import publish_project_file
        from itd.layout import project_directory
        source=self.root/'source.pdf';source.write_bytes(b'safe')
        with connect(self.path) as c:
            item=import_file(c,archive_root=self.archive,source=source,doc_type='rd',title='РД')
            folder=project_directory(c,self.project,self.root/'ИТД')
            outside=self.root/'outside';outside.mkdir()
            (folder/'Рабочая документация').symlink_to(outside,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'вне корня'):
                publish_project_file(c,attachment_id=item['id'],project_id=self.project,archive_root=self.archive)
            self.assertEqual(list(outside.iterdir()),[])
            stored=c.execute('SELECT storage_path FROM attachments WHERE id=?',(item['id'],)).fetchone()[0]
            (self.archive/stored).write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'повреждена'):
                publish_project_file(c,attachment_id=item['id'],project_id=self.other,archive_root=self.archive)

    def test_source_root_symlink_cannot_escape_workspace(self):
        from itd.archive import publish_project_file
        external=tempfile.TemporaryDirectory();self.addCleanup(external.cleanup)
        (self.root/'ИТД').symlink_to(external.name,target_is_directory=True)
        source=self.root/'safe.pdf';source.write_bytes(b'safe')
        with connect(self.path) as c:
            item=import_file(c,archive_root=self.archive,source=source,doc_type='rd',title='РД')
            with self.assertRaisesRegex(ValueError,'Ссылка вместо корня ИТД'):
                publish_project_file(c,attachment_id=item['id'],project_id=self.project,archive_root=self.archive)
        self.assertEqual(list(Path(external.name).iterdir()),[])

    def test_long_source_filename_keeps_revision_and_extension(self):
        from itd.archive import publish_project_file
        source=self.root/('Документация_'+'а'*90+' — редакция 17.pdf');source.write_bytes(b'long name')
        with connect(self.path) as c:
            item=import_file(c,archive_root=self.archive,source=source,doc_type='rd',title='РД')
            target=self.root/publish_project_file(c,attachment_id=item['id'],project_id=self.project,archive_root=self.archive)
            self.assertTrue(target.name.endswith('редакция 17.pdf'))
            self.assertLessEqual(len(target.name.encode('utf-8')),180)
            self.assertEqual(c.execute('SELECT original_name FROM attachments WHERE id=?',(item['id'],)).fetchone()[0],source.name)
            self.assertEqual(target.read_bytes(),b'long name')

    def test_archive_deduplicates_preserves_source_and_checks_integrity(self):
        source = self.root / "Приказ.pdf"
        source.write_bytes(b"test original")
        with connect(self.path) as connection:
            first = import_file(connection, archive_root=self.archive, source=source, doc_type="order", title="Приказ")
            second = import_file(connection, archive_root=self.archive, source=source, doc_type="order", title="Другое название")
            self.assertEqual(first["id"], second["id"])
            self.assertTrue(second["duplicate"])
            self.assertEqual(source.read_bytes(), b"test original")
            row = connection.execute("SELECT * FROM attachments WHERE id=?", (first["id"],)).fetchone()
            archived_path(self.archive, row["storage_path"]).write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                import_file(connection, archive_root=self.archive, source=source, doc_type="order", title="Приказ")

    def test_reimport_recovers_missing_original_and_keeps_metadata(self):
        source=self.root/'Приказ.txt';source.write_bytes(b'original')
        with connect(self.path) as c:
            first=import_file(c,archive_root=self.archive,source=source,doc_type='order',title='Исходный приказ')
            row=c.execute('SELECT * FROM attachments WHERE id=?',(first['id'],)).fetchone()
            stored=archived_path(self.archive,row['storage_path']);stored.unlink()
            result=import_file(c,archive_root=self.archive,source=source,doc_type='other',title='Другое название')
            self.assertEqual(result['id'],first['id'])
            self.assertEqual(stored.read_bytes(),b'original')
            after=c.execute('SELECT * FROM attachments WHERE id=?',(first['id'],)).fetchone()
            self.assertEqual(dict(row),dict(after))

    def test_long_source_name_is_shortened_to_available_path_budget(self):
        from itd.archive import publish_project_file
        from itd.layout import check_path
        source=self.root/('Длинное название приказа '*5+'.txt');source.write_bytes(b'original')
        with connect(self.path) as c:
            item=import_file(c,archive_root=self.archive,source=source,doc_type='order',title='Приказ')
            target=self.root/publish_project_file(c,attachment_id=item['id'],project_id=self.project,archive_root=self.archive)
            check_path(target)
            self.assertEqual(target.read_bytes(),b'original')
            self.assertTrue(target.name.endswith('.txt'))

    def test_one_file_links_to_multiple_projects(self):
        source = self.root / "Паспорт.pdf"
        source.write_bytes(b"passport")
        with connect(self.path) as connection:
            attachment = import_file(connection, archive_root=self.archive, source=source, doc_type="passport", title="Паспорт")["id"]
            for project in (self.project, self.other):
                link_file(connection, attachment_id=attachment, entity="project", entity_id=project)
            self.assertEqual(connection.execute("SELECT count(*) FROM project_attachments").fetchone()[0], 2)
            with self.assertRaises(sqlite3.IntegrityError):
                link_file(connection, attachment_id=attachment, entity="project", entity_id=999)
        with self.assertRaises(ValueError):
            archived_path(self.archive, "../outside.pdf")

    def test_assignments_inherit_and_project_overrides_only_its_scope(self):
        with connect(self.path) as connection:
            org = add_organization(connection, full_name="Организация", short_name="ООО Тест")
            first = add_signatory(connection, org_id=org, fio="Иванов Иван Иванович", position="Инженер", nrs_id="123",
                                   last_name="Иванов", first_name="Иван", middle_name="Иванович")
            second = add_signatory(connection, org_id=org, fio="Петров Пётр Петрович", position="Начальник")
            assign(connection, entity="organization", entity_id=org, role_key="заказчик", object_id=self.obj)
            assign(connection, entity="signatory", entity_id=first, role_key="recipient", object_id=self.obj)
            assign(connection, entity="signatory", entity_id=second, role_key="recipient", project_id=self.project)
            self.assertEqual(participants_context(connection, self.project)["signatories"]["recipient"]["id"], second)
            inherited = participants_context(connection, self.other)
            self.assertEqual(inherited["signatories"]["recipient"]["id"], first)
            self.assertEqual(inherited["signatories"]["recipient"]["fio_short"], "Иванов И. И.")
            connection.execute("UPDATE signatories SET status='Отозван' WHERE id=?", (second,))
            self.assertIsNone(participants_context(connection, self.project)["signatories"]["recipient"])

    def test_signatory_presentations_and_required_nrs(self):
        roots = {"signatories": {"recipient": {"fio": "Иванов И. И.", "position": "Инженер",
                  "nrs_id": "123", "organization": {"short_name": "ООО Тест"}}}}
        fields = [{"key": "signed_by", "kind": "signatory", "role": "recipient",
                   "presentation": "position_org_fio_nrs", "required": True}]
        context, _ = resolve_fields(fields, roots, draft=False)
        self.assertEqual(context["signed_by"], "Инженер ООО Тест Иванов И. И., номер в НРС №123")
        roots["signatories"]["recipient"]["nrs_id"] = None
        with self.assertRaises(ValueError):
            resolve_fields(fields, roots, draft=False)
        draft, missing = resolve_fields(fields, roots)
        self.assertIn("УТОЧНИТЬ", draft["signed_by"])
        self.assertTrue(missing)


if __name__ == "__main__":
    unittest.main()
