import json
import unittest
from unittest.mock import patch

from test_web_workspace import WorkspaceFixture
from itd.db import connect, add_object, add_project
from itd.resources import add_resource, CATEGORIES
from itd.acts import add_act, register_form
from itd.workspace import save_entry
from itd.workflow import add_fact
from itd import deletion


class DeletionTests(WorkspaceFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        state=self.create();self.pid=state['projects'][0]['id'];self.oid=state['object']['id']
        self.person=state['participants'][0]['representatives'][0]['id']
        with connect(self.path) as c:
            self.rid=add_resource(c,project_id=self.pid,name='Кабель',unit='м',category=CATEGORIES[3])
            self.entry=save_entry(c,self.pid,{'kind':'work','title':'Монтаж','resource_id':self.rid})['id']
            self.fact=add_fact(c,self.pid,{'resource_id':self.rid,'source_key':'test-fact','location':'Этаж',
                'work_description':'Монтаж','source':'ОЖР','reported_by':'Мастер','status':'confirmed',
                'quantity':3,'unit':'м','work_entry_id':self.entry})['id']
            register_form(c,code='DELETE_TEST',name='Документ',fields=[])
            self.act=add_act(c,project_id=self.pid,act_type='DELETE_TEST')
            c.execute('INSERT INTO act_resources VALUES (?,?,?)',(self.act,self.rid,1))
            c.execute('INSERT INTO act_facts VALUES (?,?)',(self.act,self.fact))

    def delete(self,c,table,identity):
        plan=deletion.preview(c,self.pid,table,identity)
        deletion.apply(c,self.pid,table,identity,plan['token'])
        self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())
        return plan

    def test_fact_deletes_required_composite_children_and_keeps_document(self):
        with connect(self.path) as c:
            c.execute('INSERT INTO work_materials(entry_id,resource_id,quantity,fact_id,unit) VALUES (?,?,?,?,?)',
                      (self.entry,self.rid,3,self.fact,'м'))
            supply=c.execute("INSERT INTO supplies(project_id,resource_id,source_key,quantity,unit,status,source) VALUES (?,?,'s',5,'м','accepted','Накладная')",(self.pid,self.rid)).lastrowid
            c.execute('INSERT INTO work_material_allocations VALUES (?,?,?,?)',(self.entry,self.rid,supply,3))
            plan=self.delete(c,'work_facts',self.fact)
            self.assertTrue({'work_facts','work_materials','work_material_allocations','act_facts'}<={i['table'] for i in plan['items'] if i['action']=='delete'})
            self.assertTrue(c.execute('SELECT 1 FROM acts WHERE id=?',(self.act,)).fetchone())
            self.assertTrue(c.execute('SELECT 1 FROM supplies WHERE id=?',(supply,)).fetchone())

    def test_work_deletion_clears_optional_fact_link(self):
        with connect(self.path) as c:
            self.delete(c,'workspace_entries',self.entry)
            self.assertIsNone(c.execute('SELECT work_entry_id FROM work_facts WHERE id=?',(self.fact,)).fetchone()[0])

    def test_resource_deletes_facts_and_links_clears_optional_journal_resource(self):
        with connect(self.path) as c:
            plan=self.delete(c,'resources',self.rid)
            self.assertFalse(c.execute('SELECT 1 FROM work_facts').fetchone())
            self.assertIsNone(c.execute('SELECT resource_id FROM workspace_entries WHERE id=?',(self.entry,)).fetchone()[0])
            self.assertTrue(c.execute('SELECT 1 FROM acts WHERE id=?',(self.act,)).fetchone())
            self.assertGreater(plan['clear_count'],0)

    def test_json_person_required_deletes_roster_and_clears_optional_responsible(self):
        with connect(self.path) as c:
            roster=save_entry(c,self.pid,{'kind':'journal','title':'Работник','work_fields':{'journal_section':'1','person_id':self.person}})['id']
            c.execute('UPDATE workspace_entries SET responsible_id=? WHERE id=?',(self.person,self.entry))
            self.delete(c,'signatories',self.person)
            self.assertFalse(c.execute('SELECT 1 FROM workspace_entries WHERE id=?',(roster,)).fetchone())
            self.assertIsNone(c.execute('SELECT responsible_id FROM workspace_entries WHERE id=?',(self.entry,)).fetchone()[0])

    def test_json_optional_supply_link_is_cleared(self):
        with connect(self.path) as c:
            supply=c.execute("INSERT INTO supplies(project_id,resource_id,source_key,quantity,unit,status,source) VALUES (?,?,'s',5,'м','accepted','Накладная')",(self.pid,self.rid)).lastrowid
            entry=save_entry(c,self.pid,{'kind':'incoming','title':'Контроль','resource_id':self.rid,'work_fields':{'supply_id':supply}})['id']
            self.delete(c,'supplies',supply)
            fields=json.loads(c.execute('SELECT work_fields FROM workspace_entries WHERE id=?',(entry,)).fetchone()[0])
            self.assertIsNone(fields['supply_id'])

    def test_changed_values_or_dependencies_require_new_confirmation(self):
        with connect(self.path) as c:
            plan=deletion.preview(c,self.pid,'work_facts',self.fact)
            c.execute('UPDATE work_facts SET quantity=7 WHERE id=?',(self.fact,))
            with self.assertRaisesRegex(ValueError,'изменились'):
                deletion.apply(c,self.pid,'work_facts',self.fact,plan['token'])
            self.assertEqual(c.execute('SELECT quantity FROM work_facts WHERE id=?',(self.fact,)).fetchone()[0],7)

    def test_other_database_rejects_confirmation(self):
        other=self.path.with_name('other.db')
        with connect(self.path) as c:
            plan=deletion.preview(c,self.pid,'work_facts',self.fact)
            import sqlite3
            target=sqlite3.connect(other)
            # backup uses a separate reader because fixture changes are already committed.
            source=sqlite3.connect(self.path);source.backup(target);source.close();target.close()
        with connect(other) as c:
            with self.assertRaisesRegex(ValueError,'изменились'):
                deletion.apply(c,self.pid,'work_facts',self.fact,plan['token'])

    def test_failure_rolls_back_every_change(self):
        with connect(self.path) as c:
            plan=deletion.preview(c,self.pid,'resources',self.rid)
            with patch('itd.deletion.log_event',side_effect=ValueError('Ошибка записи журнала')):
                with self.assertRaises(ValueError):deletion.apply(c,self.pid,'resources',self.rid,plan['token'])
            self.assertTrue(c.execute('SELECT 1 FROM resources WHERE id=?',(self.rid,)).fetchone())
            self.assertEqual(c.execute('SELECT resource_id FROM workspace_entries WHERE id=?',(self.entry,)).fetchone()[0],self.rid)

    def test_foreign_object_and_service_tables_are_rejected(self):
        with connect(self.path) as c:
            oid=add_object(c,'Другой объект')
            pid=add_project(c,object_id=oid,section_code='ДР',code='ДР',name='Другой')
            rid=add_resource(c,project_id=pid,name='Другой ресурс',unit='шт',category=CATEGORIES[0])
            with self.assertRaises(ValueError):deletion.preview(c,self.pid,'resources',rid)
            with self.assertRaises(ValueError):deletion.preview(c,self.pid,'audit_events',1)
            with self.assertRaises(ValueError):deletion.preview(c,self.pid,'resources; DROP TABLE resources',1)

    def test_object_deletes_complete_hierarchy_with_scope_assignments(self):
        with connect(self.path) as c:
            plan=self.delete(c,'objects',self.oid)
            self.assertFalse(c.execute('SELECT 1 FROM projects WHERE id=?',(self.pid,)).fetchone())
            self.assertTrue(c.execute('SELECT 1 FROM signatories WHERE id=?',(self.person,)).fetchone())
            self.assertTrue(any(i.get('scope') for i in plan['items']))

    def test_explicit_required_document_field_cascades_optional_field_clears(self):
        with connect(self.path) as c:
            required=[{'key':'person','kind':'reference','source':f'Representative.{self.person}.Name','required':True}]
            optional=[{**required[0],'required':False}]
            c.execute('UPDATE acts SET fields=? WHERE id=?',(json.dumps(required),self.act))
            another=add_act(c,project_id=self.pid,act_type='DELETE_TEST',fields=optional)
            self.delete(c,'signatories',self.person)
            self.assertFalse(c.execute('SELECT 1 FROM acts WHERE id=?',(self.act,)).fetchone())
            field=json.loads(c.execute('SELECT fields FROM acts WHERE id=?',(another,)).fetchone()[0])[0]
            self.assertIsNone(field['value']);self.assertNotIn('source',field)
