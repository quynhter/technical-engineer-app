"""Сводка ОЖР: даты, несколько представителей и границы разделов."""
import unittest
import shutil
from unittest.mock import patch

from test_web_workspace import WorkspaceFixture
from itd.db import connect, add_project
from itd.workspace import save_workspace, save_entry
from itd.participants import add_signatory, assign, participants_context
from itd.manual import execute
from itd.journals import journal_data
from itd.web import project_data


class IdReviewTests(WorkspaceFixture, unittest.TestCase):
    def test_migration_preserves_assignments_and_creates_backup(self):
        from itd import db
        from itd.web import prepare_database
        old_migrations = self.path.parent / 'old-migrations'
        old_migrations.mkdir()
        for migration in db.MIGRATIONS.glob('*.sql'):
            if int(migration.name[:3]) <= 16:
                shutil.copy2(migration, old_migrations / migration.name)
        legacy = self.path.parent / 'legacy.db'
        with patch.object(db, 'MIGRATIONS', old_migrations):
            db.initialize(legacy)
        with connect(legacy) as c:
            saved = save_workspace(c, self.payload())
            before = [tuple(r) for r in c.execute('SELECT * FROM signatory_assignments')]
        backup = prepare_database(legacy)
        self.assertTrue(backup.is_file())
        with connect(backup) as c:
            self.assertEqual(c.execute('SELECT max(version) FROM schema_migrations').fetchone()[0],16)
        with connect(legacy) as c:
            self.assertEqual(before,[tuple(r) for r in c.execute('SELECT * FROM signatory_assignments')])
            org = saved['participants'][0]
            person = add_signatory(c,org_id=org['id'],fio='Второй представитель',position='Инженер')
            assign(c,entity='signatory',entity_id=person,role_key='customer_control',object_id=saved['object']['id'],multiple=True)
            self.assertEqual(c.execute('SELECT count(*) FROM signatory_assignments').fetchone()[0],2)

    def test_title_dates_follow_all_sections_and_keep_object_source(self):
        saved = self.create()
        oid, pid = saved['object']['id'], saved['projects'][0]['id']
        with connect(self.path) as c:
            other = self.create()['projects'][0]['id']
            second = add_project(c, object_id=oid, section_code='ЭОМ', code='ЭОМ', name='Электрика')
            c.execute('UPDATE projects SET smr_start=?,smr_end=? WHERE id=?', ('2026-04-01','2026-06-01',pid))
            c.execute('UPDATE projects SET smr_start=?,pnr_end=? WHERE id=?', ('2026-03-01','2026-09-01',second))
            c.execute('UPDATE projects SET smr_start=?,pnr_end=? WHERE id=?', ('2020-01-01','2030-01-01',other))
            self.assertEqual(journal_data(c,pid)['construction_dates'], {'start':'2026-03-01','end':'2026-09-01'})
            c.execute('UPDATE projects SET smr_start=NULL,pnr_end=NULL WHERE id=?', (second,))
            self.assertEqual(journal_data(c,pid)['construction_dates'], {'start':'2026-04-01','end':'2026-06-01'})
            c.execute('UPDATE projects SET smr_start=NULL,smr_end=NULL WHERE id=?', (pid,))
            self.assertEqual(journal_data(c,pid)['construction_dates'], {'start':'2026-10-01','end':None})
            self.assertEqual(c.execute('SELECT work_start FROM objects WHERE id=?',(oid,)).fetchone()[0], '2026-10-01')

    def test_shared_roles_organizations_and_project_assignments(self):
        saved = self.create()
        pid = saved['projects'][0]['id']
        org = saved['participants'][0]
        first = org['representatives'][0]['id']
        with connect(self.path) as c:
            second = add_signatory(c, org_id=org['id'], fio='Петров Пётр', position='Инженер')
            data = dict(entity='signatory', entity_id=second, role='customer_control', scope='project', mode='add', expected={'entity_ids':[]})
            execute(c,pid,'assign',data)
            data.update(entity_id=first,expected={'entity_ids':[second]})
            execute(c,pid,'assign',data)
            view = journal_data(c,pid)
            rows = [r for r in view['title_assignments'] if r['role_key']=='customer_control']
            self.assertEqual(len(rows),3)
            self.assertTrue(all(r['organization']['id']==org['id'] for r in rows))
            self.assertIsNone(participants_context(c,pid)['signatories']['customer_control'])
            with self.assertRaisesRegex(ValueError,'изменено'):
                execute(c,pid,'assign',data)
            data.update(mode='remove',expected={'entity_ids':[second,first]})
            execute(c,pid,'assign',data)
            self.assertEqual(participants_context(c,pid)['signatories']['customer_control']['id'],second)
            # Общее назначение сохраняется при изменении назначения раздела.
            self.assertEqual(c.execute('SELECT signatory_id FROM signatory_assignments WHERE object_id=?',(saved['object']['id'],)).fetchone()[0],first)

    def test_work_tab_is_project_scoped_but_ojr_contains_all_object_sections(self):
        saved = self.create()
        pid, oid = saved['projects'][0]['id'], saved['object']['id']
        with connect(self.path) as c:
            second = add_project(c, object_id=oid, section_code='ЭОМ', code='ЭОМ', name='Электрика')
            own = save_entry(c,pid,dict(kind='work',title='Работа СПС'))
            shared = save_entry(c,second,dict(kind='work',title='Работа ЭОМ'))
            data = project_data(c,pid)
            self.assertEqual([e['id'] for e in data['workspace_entries']], [own['id']])
            self.assertEqual({e['id'] for e in data['journals']['sections']['3']}, {own['id'],shared['id']})


if __name__ == '__main__':
    unittest.main()
