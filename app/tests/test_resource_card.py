"""Единая карточка: точные связи, независимые количества и атомарные исправления."""
import unittest

from test_web_workspace import WorkspaceFixture
from itd.db import connect, add_project
from itd.resources import add_resource, CATEGORIES
from itd.manual import execute
from itd.resource_card import save_card
from itd.workflow import add_fact
from itd.workspace import save_entry
from itd.journals import journal_data


class ResourceCardTests(WorkspaceFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.saved = self.create()
        self.pid = self.saved['projects'][0]['id']
        with connect(self.path) as c:
            self.rid = add_resource(c,project_id=self.pid,name='Кабель',unit='м',category=CATEGORIES[3],qty_proj=100)

    def packet(self,c,**changes):
        return dict(id=self.rid,expected=dict(c.execute('SELECT * FROM resources WHERE id=?',(self.rid,)).fetchone()),
                    changes=changes,supplies=[],facts=[])

    def supply(self,**changes):
        return dict(batch_num='Партия 1',supply_date='2026-10-01',quantity=10,unit='м',supplier='Поставщик',source='Накладная',attachment_id=None,status='accepted',note=None,**changes)

    def fact(self):
        return dict(location='Этаж 1',work_description='Монтаж',quantity=3,unit='м',start_date=None,end_date='2026-10-02',reported_by='Прораб',source='Сообщение пользователя',attachment_id=None,status='pending')

    def test_single_save_adds_receipt_and_fact_once_without_deriving_totals(self):
        with connect(self.path) as c:
            d=self.packet(c,name='Кабель уточнённый')
            d['supplies']=[dict(values=self.supply(),source_key='receipt-1')]
            d['facts']=[dict(values=self.fact(),source_key='fact-1')]
            execute(c,self.pid,'resource-card-save',d)
            resource=dict(c.execute('SELECT * FROM resources WHERE id=?',(self.rid,)).fetchone())
            self.assertEqual(resource['name'],'Кабель уточнённый')
            self.assertIsNone(resource['qty_fact'])
            self.assertEqual(resource['qty_proj'],100)
            self.assertEqual(c.execute('SELECT quantity FROM supplies').fetchone()[0],10)
            self.assertEqual(c.execute('SELECT quantity FROM work_facts').fetchone()[0],3)
            self.assertEqual(c.execute('SELECT count(*) FROM work_material_allocations').fetchone()[0],0)
            d=self.packet(c)
            d['supplies']=[dict(values=self.supply(),source_key='receipt-1')]
            d['facts']=[dict(values=self.fact(),source_key='fact-1')]
            save_card(c,self.pid,d)
            self.assertEqual(c.execute('SELECT count(*) FROM supplies').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT count(*) FROM work_facts').fetchone()[0],1)

    def test_invalid_last_block_rolls_back_resource_receipts_and_audit(self):
        with connect(self.path) as c:
            d=self.packet(c,qty_fact=0)
            d['supplies']=[dict(values=self.supply(),source_key='receipt-1')]
            d['facts']=[dict(values={**self.fact(),'end_date':'2026-99-99'},source_key='bad-fact')]
            audit=c.execute('SELECT count(*) FROM audit_events').fetchone()[0]
            with self.assertRaises(ValueError):save_card(c,self.pid,d)
            self.assertIsNone(c.execute('SELECT qty_fact FROM resources WHERE id=?',(self.rid,)).fetchone()[0])
            self.assertEqual(c.execute('SELECT count(*) FROM supplies').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT count(*) FROM audit_events').fetchone()[0],audit)

    def test_receipt_edit_uses_revision_and_rejects_foreign_resource(self):
        with connect(self.path) as c:
            receipt=execute(c,self.pid,'supply-add',dict(self.supply(),resource_id=self.rid,source_key='receipt-1'))
            values={**self.supply(),'quantity':15,'supply_date':'2026-09-30'}
            packet=dict(id=receipt['id'],values=values,expected=receipt,reason='Исправлена накладная')
            d=self.packet(c);d['supplies']=[packet]
            save_card(c,self.pid,d)
            self.assertEqual(c.execute('SELECT quantity FROM supplies').fetchone()[0],15)
            with self.assertRaisesRegex(ValueError,'изменена'):save_card(c,self.pid,d)
            other=add_resource(c,project_id=self.pid,name='Другой',unit='м',category=CATEGORIES[3])
            d=self.packet(c);d['id']=other;d['expected']=dict(c.execute('SELECT * FROM resources WHERE id=?',(other,)).fetchone())
            packet['expected']=dict(c.execute('SELECT * FROM supplies').fetchone());d['supplies']=[packet]
            with self.assertRaisesRegex(ValueError,'другому ресурсу'):save_card(c,self.pid,d)

    def test_fact_correction_keeps_original_and_updates_explicit_total_only(self):
        with connect(self.path) as c:
            old=add_fact(c,self.pid,dict(self.fact(),resource_id=self.rid,source_key='fact-1'))
            d=self.packet(c,qty_fact=4)
            d['facts']=[dict(id=old['id'],values={**self.fact(),'quantity':4,'status':'confirmed'},expected=old,reason='Уточнён замер',source_key='correction-1')]
            save_card(c,self.pid,d)
            facts=[dict(r) for r in c.execute('SELECT * FROM work_facts ORDER BY id')]
            self.assertEqual([f['status'] for f in facts],['void','confirmed'])
            self.assertEqual([f['quantity'] for f in facts],[3,4])
            self.assertEqual(facts[0]['void_reason'],'Уточнён замер')
            self.assertEqual(c.execute('SELECT qty_fact FROM resources WHERE id=?',(self.rid,)).fetchone()[0],4)

    def test_work_fact_requires_original_work_and_leaves_receipt_independent(self):
        with connect(self.path) as c:
            org=self.saved['participants'][0];person=org['representatives'][0]['id']
            save_entry(c,self.pid,dict(kind='journal',title='Инженер',work_fields={'journal_section':'1','person_id':person}))
            receipt=execute(c,self.pid,'supply-add',dict(self.supply(),resource_id=self.rid,source_key='receipt-1'))
            save_entry(c,self.pid,dict(kind='work',title='Монтаж',details='Этаж 1',entry_date='2026-10-02',responsible_id=person,materials=[dict(resource_id=self.rid,quantity=3)]))
            fact=dict(c.execute('SELECT * FROM work_facts').fetchone())
            d=self.packet(c);d['facts']=[dict(id=fact['id'],values={**self.fact(),'quantity':5},expected=fact,reason='Изменить',source_key='bad-correction')]
            with self.assertRaisesRegex(ValueError,'исходную запись'):save_card(c,self.pid,d)
            d=self.packet(c);d['supplies']=[dict(id=receipt['id'],values={**self.supply(),'quantity':2},expected=receipt,reason='Уточнение')]
            save_card(c,self.pid,d)
            self.assertEqual(c.execute('SELECT quantity FROM supplies').fetchone()[0],2)

    def test_automatic_journals_appear_after_first_entry_without_writes(self):
        foreign=self.create()['projects'][0]['id']
        with connect(self.path) as c:
            self.assertEqual(journal_data(c,self.pid)['automatic'],[])
            other=add_project(c,object_id=self.saved['object']['id'],section_code='ЭОМ',code='ЭОМ',name='Электрика')
            save_entry(c,foreign,dict(kind='work',title='Не этот объект'))
            self.assertEqual(journal_data(c,self.pid)['automatic'],[])
            save_entry(c,other,dict(kind='incoming',title='Проверка ЭОМ'))
            rows=journal_data(c,self.pid)['automatic']
            self.assertEqual([(r['kind'],r['project_id'],r['count']) for r in rows],[('incoming',other,1)])
            save_entry(c,self.pid,dict(kind='work',title='Монтаж'))
            save_entry(c,self.pid,dict(kind='work',title='Монтаж 2'))
            audit=c.execute('SELECT count(*) FROM audit_events').fetchone()[0]
            rows=journal_data(c,self.pid)['automatic']
            self.assertEqual([(r['kind'],r['count']) for r in rows],[('ojr',2),('incoming',1)])
            self.assertEqual(journal_data(c,self.pid)['automatic'],rows)
            self.assertEqual(c.execute('SELECT count(*) FROM audit_events').fetchone()[0],audit)
            self.assertEqual(c.execute('SELECT count(*) FROM special_journals').fetchone()[0],0)


if __name__=='__main__':unittest.main()
