"""Общие источники журналов, границы объектов и живые связи."""
import json
import unittest

from test_web_workspace import WorkspaceFixture
from itd.db import connect, add_project
from itd.workspace import save_entry
from itd.journals import journal_data
from itd.resources import add_resource, CATEGORIES
from itd.manual import execute


class JournalTests(WorkspaceFixture, unittest.TestCase):
    def test_object_sections_live_edit_isolation_and_legacy(self):
        saved = self.create()
        pid = saved['projects'][0]['id']
        other = self.create()['projects'][0]['id']
        with connect(self.path) as c:
            second = add_project(c, object_id=saved['object']['id'], section_code='ЭОМ', code='РД-ЭОМ', name='Электрика')
            entry = save_entry(c, second, {'kind':'work','title':'Монтаж кабеля'})
            save_entry(c, other, {'kind':'work','title':'Другой объект'})
            legacy = save_entry(c, pid, {'kind':'journal','title':'Старая запись'})
            control = save_entry(c, pid, {'kind':'journal','title':'Осмотр','work_fields':{'journal_section':'4','deadline':'2026-11-10'}})
            view = journal_data(c, pid)
            self.assertEqual([e['id'] for e in view['sections']['3']], [entry['id']])
            self.assertEqual([e['id'] for e in view['legacy']], [legacy['id']])
            self.assertEqual(view['sections']['4'][0]['id'], control['id'])
            save_entry(c, second, {**entry, 'title':'Уточнённый монтаж'})
            self.assertEqual(journal_data(c, pid)['sections']['3'][0]['title'], 'Уточнённый монтаж')
            self.assertEqual(c.execute('SELECT count(*) FROM work_facts').fetchone()[0], 0)
            self.assertEqual(c.execute('SELECT count(*) FROM workspace_entries').fetchone()[0], 4)
            with self.assertRaises(ValueError):
                save_entry(c, pid, {**legacy, 'kind':'work'})
            for fields in ({'journal_section':'3'}, {'journal_section':'5'}, {'journal_section':'4','deadline':'2026-02-30'}):
                with self.assertRaises(ValueError):
                    save_entry(c, pid, {'kind':'journal','title':'Ошибка','work_fields':fields})

    def test_document_and_connected_journal_lists_track_current_object(self):
        from itd.acts import register_form, add_act
        s = self.create()
        pid = s['projects'][0]['id']
        other = self.create()['projects'][0]['id']
        with connect(self.path) as c:
            second = add_project(c,object_id=s['object']['id'],section_code='ЭОМ',code='РД-ЭОМ',name='Электрика')
            register_form(c,code='J',name='Журнал',form_group='statement',fields=[
                {'key':'rows','kind':'table','value':[],'fields':[{'key':'text','kind':'reference','source':'row.text'}]}])
            aid = execute(c,second,'journal-add',dict(act_type='J',entry_kind='work',table_key='rows',mapping={'text':'entry.title'}))['act_id']
            add_act(c,project_id=other,act_type='J')
            view = journal_data(c,pid)
            self.assertEqual(view['sections']['5'],[])
            self.assertEqual([a['id'] for a in view['draft_documents']],[aid])
            self.assertEqual([a['act_id'] for a in view['connected']],[aid])
            c.execute('UPDATE acts SET date_signed=? WHERE id=?',('2026-11-02',aid))
            self.assertEqual(journal_data(c,pid)['sections']['5'],[])  # Дата не означает подтверждение подписания.
            c.execute('UPDATE acts SET is_active=0 WHERE id=?',(aid,))
            self.assertEqual(journal_data(c,pid)['sections']['5'],[])
            self.assertEqual(journal_data(c,pid)['connected'],[])

    def test_staff_references_are_live_and_do_not_overwrite_manual_values(self):
        s = self.create()
        pid = s['projects'][0]['id']
        org = s['participants'][0]
        person = org['representatives'][0]
        with connect(self.path) as c:
            save_entry(c, pid, {'kind':'journal','title':'Персонал','work_fields':{'journal_section':'1',
                'org_id':org['id'],'person_id':person['id'],'organization':'Ручное значение'}})
            c.execute('UPDATE organizations SET full_name=? WHERE id=?', ('Уточнённая организация', org['id']))
            e = journal_data(c, pid)['sections']['1'][0]
            self.assertEqual(e['resolved_fields']['organization'], 'Уточнённая организация')
            self.assertEqual(e['work_fields']['organization'], 'Ручное значение')
            self.assertIn(person['fio'], e['resolved_fields']['person'])

    def test_incoming_supply_quality_links_and_no_fact_side_effect(self):
        s = self.create()
        pid = s['projects'][0]['id']
        other = self.create()['projects'][0]['id']
        with connect(self.path) as c:
            rid = add_resource(c,project_id=pid,name='Датчик',unit='шт.',category=CATEGORIES[1])
            rid2 = add_resource(c,project_id=pid,name='Иной датчик',unit='шт.',category=CATEGORIES[1])
            sup = execute(c,pid,'supply-add',dict(resource_id=rid,source_key='s1',unit='шт.',quantity=2,
                supplier='Поставщик',source='Накладная',status='pending'))
            from itd.archive import import_file, link_file
            from itd.workflow import add_quality_review
            source = self.path.parent / 'passport.txt'
            source.write_text('Паспорт')
            attachment = import_file(c,archive_root=self.path.parent/'archive',source=source,doc_type='passport',title='Паспорт')
            link_file(c,attachment_id=attachment['id'],entity='resource',entity_id=rid)
            review = add_quality_review(c,pid,dict(resource_id=rid,attachment_id=attachment['id'],status='uncertain',
                checked_by='Инженер',checked_date='2026-11-02',source='Паспорт',note='Марка требует уточнения'))
            entry = save_entry(c,pid,{'kind':'incoming','title':'Поставка','resource_id':rid,
                'work_fields':{'supply_id':sup['id'],'quality_review_id':review['id'],'visual_result':'Осмотр выполнен','laboratory_decision':None}})
            row = journal_data(c,pid)['incoming'][0]
            self.assertEqual(row['supply']['quantity'],2)
            self.assertEqual(row['quality_review']['status'],'uncertain')
            self.assertTrue(row['quality_review']['is_current'])
            c.execute('UPDATE resources SET serial_num=? WHERE id=?',('001',rid))
            self.assertFalse(journal_data(c,pid)['incoming'][0]['quality_review']['is_current'])
            self.assertIsNone(row['quantity'])
            c.execute('UPDATE supplies SET supplier=? WHERE id=?',('Новый поставщик',sup['id']))
            self.assertEqual(journal_data(c,pid)['incoming'][0]['supply']['supplier'],'Новый поставщик')
            for project,resource in ((pid,rid2),(other,rid)):
                with self.assertRaises(ValueError):
                    save_entry(c,project,{'kind':'incoming','title':'Ошибка','resource_id':resource,'work_fields':{'supply_id':sup['id']}})
            with self.assertRaises(ValueError):
                save_entry(c,pid,{**entry,'work_fields':{'quality_review_id':999}})
            self.assertIsNone(c.execute('SELECT qty_fact FROM resources WHERE id=?',(rid,)).fetchone()[0])
            self.assertEqual(c.execute('SELECT count(*) FROM work_facts').fetchone()[0],0)


    def test_incoming_supply_queue_uses_explicit_result_and_exact_supply(self):
        s=self.create();pid=s['projects'][0]['id']
        with connect(self.path) as c:
            rid=add_resource(c,project_id=pid,name='Кабель',unit='м',category=CATEGORIES[3])
            def supply(key,status='accepted'):
                return execute(c,pid,'supply-add',dict(resource_id=rid,source_key=key,quantity=10,unit='м',source='Накладная',status=status))
            first=supply('first');second=supply('second');rejected=supply('reject','rejected')
            def queue():return {r['id']:r for r in journal_data(c,pid)['incoming_queue']}
            self.assertEqual(queue()[first['id']]['control_status'],'not_checked')
            # Проверка материала без ссылки на партию не закрывает обе поставки.
            save_entry(c,pid,dict(kind='incoming',resource_id=rid,title='Ручная проверка',work_fields={'incoming_result':'accepted'}))
            self.assertEqual(queue()[second['id']]['control_status'],'not_checked')
            entry=save_entry(c,pid,dict(kind='incoming',resource_id=rid,title='Проверка первой партии',work_fields={'supply_id':first['id'],'document_result':'Проверено'}))
            self.assertEqual(queue()[first['id']]['control_status'],'in_progress')
            self.assertEqual(queue()[first['id']]['entry_id'],entry['id'])
            entry=save_entry(c,pid,{**entry,'work_fields':{'supply_id':first['id'],'incoming_result':'accepted'}})
            self.assertNotIn(first['id'],queue())
            # Новая незавершённая проверка той же поставки вновь требует внимания.
            newer=save_entry(c,pid,dict(kind='incoming',resource_id=rid,title='Повторная проверка',work_fields={'supply_id':first['id']}))
            self.assertEqual(queue()[first['id']]['entry_id'],newer['id'])
            save_entry(c,pid,{**newer,'work_fields':{'supply_id':first['id'],'incoming_result':'rejected'}})
            self.assertEqual(queue()[first['id']]['control_status'],'rejected')
            self.assertEqual(queue()[rejected['id']]['control_status'],'rejected')
            self.assertEqual(c.execute('SELECT status FROM supplies WHERE id=?',(first['id'],)).fetchone()[0],'accepted')
            pending=supply('awaiting-acceptance','pending')
            save_entry(c,pid,dict(kind='incoming',title='Контроль без приёмки',resource_id=rid,
                work_fields={'supply_id':pending['id'],'incoming_result':'accepted'}))
            self.assertEqual(queue()[pending['id']]['control_status'],'awaiting_receipt')
            execute(c,pid,'supply-set',dict(id=second['id'],status='void',note='Ошибочная поставка',expected={'revision':second['revision']}))
            self.assertNotIn(second['id'],queue())
            for kind,result in [('incoming','bad'),('work','accepted')]:
                with self.assertRaises(ValueError):save_entry(c,pid,dict(kind=kind,title='Ошибка',work_fields={'incoming_result':result}))


if __name__ == '__main__':
    unittest.main()
