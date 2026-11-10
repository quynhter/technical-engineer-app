import base64
import json
from pathlib import Path
import unittest

from test_web_workspace import WorkspaceFixture
from itd.db import connect,add_project
from itd.workspace import save_entry
from itd.resources import add_resource,CATEGORIES
from itd.manual import execute,bind_entries
from itd.inventory import balances
from itd.ojr import roster,save_special,special_rows,set_act_people,sign_act
from itd.journals import journal_data
from itd.acts import register_form,add_act,set_resources
from itd import resource_import as imports


class ResourceOjrTests(WorkspaceFixture,unittest.TestCase):
    def setUp(self):
        super().setUp()
        s=self.create();self.pid=s['projects'][0]['id'];self.oid=s['object']['id']
        self.person=s['participants'][0]['representatives'][0]['id'];self.org=s['participants'][0]['id']
        with connect(self.path) as c:
            self.rid=add_resource(c,project_id=self.pid,name='Кабель',unit='м',category=CATEGORIES[3],qty_proj=100)
            self.staff=save_entry(c,self.pid,dict(kind='journal',title='Исполнитель',work_fields={'journal_section':'1','person_id':self.person,'org_id':self.org,'start_date':'2026-01-01','end_date':'2026-12-31'}))
            self.supply=execute(c,self.pid,'supply-add',dict(resource_id=self.rid,source_key='receipt1',quantity=10,unit='м',source='Накладная',status='accepted'))

    def test_delivered_and_controlled_use_exact_latest_supply_decision(self):
        with connect(self.path) as c:
            def current(): return balances(c,self.pid)[0]
            self.assertEqual(current()['delivered'],10)
            self.assertEqual(current()['control_accepted'],0)
            self.assertEqual(current()['awaiting_control'],1)
            # A resource-level check cannot accept a particular delivery.
            save_entry(c,self.pid,dict(kind='incoming',title='Контроль',resource_id=self.rid,
                                      work_fields={'incoming_result':'accepted'}))
            self.assertEqual(current()['control_accepted'],0)
            control=save_entry(c,self.pid,dict(kind='incoming',title='Контроль партии',resource_id=self.rid,
                work_fields={'supply_id':self.supply['id'],'incoming_result':'accepted'}))
            self.assertEqual(current()['control_accepted'],10)
            self.assertEqual(current()['awaiting_control'],0)
            # Repeated checks do not increase accepted quantity.
            newer=save_entry(c,self.pid,dict(kind='incoming',title='Повторный контроль',resource_id=self.rid,
                work_fields={'supply_id':self.supply['id'],'incoming_result':'pending'}))
            self.assertEqual(current()['control_accepted'],0)
            self.assertEqual(current()['awaiting_control'],1)
            save_entry(c,self.pid,{**newer,'work_fields':{'supply_id':self.supply['id'],'incoming_result':'rejected'}})
            self.assertEqual(current()['control_rejected'],1)
            self.assertEqual(current()['awaiting_control'],0)
            # Existing stock accounting and the independently entered fact are unchanged.
            self.assertEqual(current()['received'],10)
            self.assertIsNone(current()['qty_fact'])

    def test_delivery_unknown_quantity_is_not_zero_and_void_is_excluded(self):
        with connect(self.path) as c:
            unknown=execute(c,self.pid,'supply-add',dict(resource_id=self.rid,source_key='unknown',
                quantity=None,unit='м',source='Источник',status='pending'))
            balance=balances(c,self.pid)[0]
            self.assertIsNone(balance['delivered'])
            self.assertEqual(balance['control_accepted'],0)
            execute(c,self.pid,'supply-set',dict(id=unknown['id'],status='void',note='Ошибочная запись',
                expected={'revision':unknown['revision']}))
            self.assertEqual(balances(c,self.pid)[0]['delivered'],10)

    def entry(self,quantity=3,**changes):
        return dict(kind='work',title='Прокладка кабеля',details='Этаж 2, оси А–Б',entry_date='2026-11-02',responsible_id=self.person,
                    materials=[{'resource_id':self.rid,'quantity':quantity}],**changes)

    def test_work_material_creates_one_fact_without_allocating_stock(self):
        with connect(self.path) as c:
            e=save_entry(c,self.pid,self.entry())
            m=dict(c.execute('SELECT * FROM work_materials').fetchone())
            self.assertEqual(balances(c,self.pid)[0]['remaining'],10)
            fact=c.execute('SELECT status,work_entry_id,start_date,end_date FROM work_facts WHERE id=?',(m['fact_id'],)).fetchone()
            self.assertEqual(tuple(fact),('confirmed',e['id'],e['entry_date'],e['entry_date']))
            self.assertEqual(c.execute('SELECT count(*) FROM work_material_allocations').fetchone()[0],0)
            save_entry(c,self.pid,{**e,'materials':[{'resource_id':self.rid,'quantity':3}]})
            self.assertEqual(c.execute('SELECT count(*) FROM work_facts').fetchone()[0],1)
            self.assertEqual(balances(c,self.pid)[0]['consumed'],3)
            self.assertIsNone(c.execute('SELECT qty_fact FROM resources WHERE id=?',(self.rid,)).fetchone()[0])

    def test_edit_replaces_fact_with_history(self):
        with connect(self.path) as c:
            e=save_entry(c,self.pid,self.entry())
            old=c.execute('SELECT fact_id FROM work_materials').fetchone()[0]
            e=save_entry(c,self.pid,{**e,'materials':[{'resource_id':self.rid,'quantity':5}]})
            self.assertEqual(balances(c,self.pid)[0]['remaining'],10)
            self.assertEqual(c.execute('SELECT status FROM work_facts WHERE id=?',(old,)).fetchone()[0],'void')
            save_entry(c,self.pid,{**e,'materials':[]})
            self.assertEqual(balances(c,self.pid)[0]['remaining'],10)
            self.assertEqual(c.execute("SELECT count(*) FROM work_facts WHERE status='confirmed'").fetchone()[0],0)

    def test_exceeding_receipts_is_allowed_but_stale_and_foreign_entries_are_rejected(self):
        with connect(self.path) as c:
            e=save_entry(c,self.pid,self.entry())
            newer=save_entry(c,self.pid,{**e,'materials':[{'resource_id':self.rid,'quantity':12}]})
            self.assertEqual(balances(c,self.pid)[0]['consumed'],12)
            with self.assertRaises(ValueError): save_entry(c,self.pid,{**e,'materials':[]})
            other=add_project(c,object_id=self.oid,section_code='ЭОМ',code='ЭОМ',name='Другой раздел')
            with self.assertRaises(ValueError): save_entry(c,other,self.entry())
            self.assertEqual(balances(c,self.pid)[0]['remaining'],10)
            self.assertGreater(newer['revision'],e['revision'])

    def test_legacy_act_reservation_does_not_limit_work(self):
        with connect(self.path) as c:
            execute(c,self.pid,'supply-add',dict(resource_id=self.rid,source_key='unconfirmed',quantity=100,unit='м',source='Источник',status='pending'))
            execute(c,self.pid,'supply-add',dict(resource_id=self.rid,source_key='unknown',quantity=None,unit='м',source='Источник',status='accepted'))
            register_form(c,code='A',name='Акт',fields=[])
            aid=add_act(c,project_id=self.pid,act_type='A');set_resources(c,aid,[self.rid])
            execute(c,self.pid,'allocate',dict(act_id=aid,supply_id=self.supply['id'],quantity=4,expected={'quantity':None}))
            save_entry(c,self.pid,self.entry(7))
            self.assertIsNone(balances(c,self.pid)[0]['remaining'])
            self.assertEqual(balances(c,self.pid)[0]['consumed'],7)
            self.assertEqual(balances(c,self.pid)[0]['reserved'],4)

    def test_act_uses_same_fact_without_allocating_stock(self):
        from itd.web import Handler
        with connect(self.path) as c:
            e=save_entry(c,self.pid,self.entry())
            register_form(c,code='A',name='Акт',fields=[])
            handler=object.__new__(Handler)
            result=handler.mutate(c,'/api/act',dict(project_id=self.pid,act_type='A',entry_ids=[e['id']],resource_ids=[self.rid]))
            self.assertEqual(c.execute('SELECT count(*) FROM act_facts WHERE act_id=?',(result['act_id'],)).fetchone()[0],1)
            self.assertEqual(balances(c,self.pid)[0]['remaining'],10)
            self.assertEqual(c.execute('SELECT count(*) FROM work_material_allocations').fetchone()[0],0)

    def test_manual_web_fact_requires_work_and_derives_its_source(self):
        from itd.web import Handler
        handler=object.__new__(Handler)
        with connect(self.path) as c:
            work=save_entry(c,self.pid,{**self.entry(),'materials':[]})
            fact=dict(resource_id=self.rid,source_key='web:test',status='pending',quantity=2,work_entry_id=None)
            with self.assertRaisesRegex(ValueError,'ОЖР'):
                handler.mutate(c,'/api/work-fact',dict(project_id=self.pid,fact=fact))
            fact['work_entry_id']=work['id']
            result=handler.mutate(c,'/api/work-fact',dict(project_id=self.pid,fact=fact))
            self.assertEqual(result['work_entry_id'],work['id'])
            self.assertEqual(result['source'],f"Запись ОЖР № {work['id']}")
            self.assertEqual(result['end_date'],work['entry_date'])
            self.assertIsNone(result.get('attachment_id'))

    def test_executor_requires_roster_and_period_and_uses_current_identity(self):
        with connect(self.path) as c:
            with self.assertRaises(ValueError):save_entry(c,self.pid,{**self.entry(),'entry_date':'2025-01-01'})
            c.execute("UPDATE signatories SET status='Отозван' WHERE id=?",(self.person,))
            self.assertEqual(roster(c,self.pid),[])
            with self.assertRaises(ValueError):save_entry(c,self.pid,self.entry())

    def test_special_journal_is_same_record_in_both_views_and_scope_safe(self):
        other=self.create()['projects'][0]['id']
        with connect(self.path) as c:
            j=save_special(c,self.pid,dict(name='Журнал бетонных работ',issued_date='2026-10-01',keeper_id=self.person))
            self.assertEqual(journal_data(c,self.pid)['special'][0]['id'],j['id'])
            save_special(c,self.pid,{**j,'transfer_date':'2026-11-02'})
            self.assertEqual(special_rows(c,self.pid)[0]['transfer_date'],'2026-11-02')
            with self.assertRaises(ValueError): save_special(c,self.pid,{**j,'name':'Устаревшая правка'})
            with self.assertRaises(ValueError): save_special(c,other,{**j,'name':'Чужой объект'})
            self.assertEqual(special_rows(c,other),[])

    def test_only_signed_acts_enter_section_five_and_capture_signers(self):
        with connect(self.path) as c:
            register_form(c,code='A',name='АОСР',fields=[{'key':'builder','kind':'signatory','role':'builder','required':True}])
            aid=add_act(c,project_id=self.pid,act_type='A',date_signed='2026-11-01')
            self.assertEqual(journal_data(c,self.pid)['sections']['5'],[])
            set_act_people(c,self.pid,aid,{'builder':self.person})
            value=sign_act(c,self.pid,dict(act_id=aid,state='signed',signed_date='2026-11-02',work_description='Прокладка в осях А–Б',basis='Подписанный экземпляр получен',expected_revision=0))
            row=journal_data(c,self.pid)['sections']['5'][0]
            self.assertEqual(row['work_description'],'Прокладка в осях А–Б')
            self.assertEqual(row['signed_by'][0]['id'],self.person)
            c.execute("UPDATE signatories SET fio='Уточнённое ФИО' WHERE id=?",(self.person,))
            self.assertNotEqual(journal_data(c,self.pid)['sections']['5'][0]['signed_by'][0]['fio'],'Уточнённое ФИО')
            with self.assertRaises(ValueError):set_resources(c,aid,[self.rid])
            sign_act(c,self.pid,dict(act_id=aid,state='draft',basis='Исправление',expected_revision=value['revision']))
            self.assertEqual(journal_data(c,self.pid)['sections']['5'],[])

    def test_failed_signing_rolls_back_signatory_selection(self):
        with connect(self.path) as c:
            register_form(c,code='A',name='Акт',fields=[])
            aid=add_act(c,project_id=self.pid,act_type='A')
            with self.assertRaises(ValueError):
                sign_act(c,self.pid,dict(act_id=aid,state='signed',signed_date=None,work_description='Монтаж',basis='Основание',expected_revision=0,signatories={'builder':self.person}))
            self.assertEqual(c.execute('SELECT count(*) FROM act_signatories WHERE act_id=?',(aid,)).fetchone()[0],0)
            self.assertEqual(c.execute('SELECT count(*) FROM act_execution_status').fetchone()[0],0)

    def test_rejected_legacy_allocation_is_visible_as_a_conflict(self):
        from itd.inventory import material_issues
        with connect(self.path) as c:
            e=save_entry(c,self.pid,self.entry())
            c.execute('INSERT INTO work_material_allocations VALUES(?,?,?,?)',(e['id'],self.rid,self.supply['id'],3))
            execute(c,self.pid,'supply-set',dict(id=self.supply['id'],status='rejected',note='Подтверждённый возврат',expected={'revision':1}))
            self.assertEqual(material_issues(c,self.pid)[0]['entry_id'],e['id'])
            self.assertEqual(balances(c,self.pid)[0]['remaining'],-3)

    def test_minstroy_form_roles_include_work_performer_and_are_roster_filtered(self):
        from itd.form_catalog import ensure_act_form
        with connect(self.path) as c:
            code='МИНСТРОЙ_344_АОСР'
            ensure_act_form(c,self.pid,code)
            aid=add_act(c,project_id=self.pid,act_type=code)
            roles=('builder','builder_control','customer_control','designer','work_performer')
            set_act_people(c,self.pid,aid,{role:self.person for role in roles})
            result=sign_act(c,self.pid,dict(act_id=aid,state='signed',signed_date='2026-11-02',work_description='Скрытая прокладка',basis='Подтверждение подписания',expected_revision=0))
            self.assertEqual(result['state'],'signed')
            self.assertEqual(len(json.loads(result['signers_json'])),5)

    def test_act_signatory_comes_from_participant_role_and_respects_revocation(self):
        from itd.acts import build_context
        with connect(self.path) as c:
            register_form(c,code='A',name='Акт',fields=[{'key':'controller','kind':'signatory','role':'customer_control','required':True}])
            aid=add_act(c,project_id=self.pid,act_type='A')
            self.assertNotIn('controller',build_context(c,aid)['missing'])
            c.execute('DELETE FROM workspace_entries WHERE id=?',(self.staff['id'],))
            self.assertNotIn('controller',build_context(c,aid)['missing'])
            c.execute("UPDATE signatories SET status='Отозван' WHERE id=?",(self.person,))
            self.assertIn('controller',build_context(c,aid)['missing'])

    def import_stage(self,c,text):
        return imports.stage(c,self.pid,{'filename':'ведомость.csv','content':base64.b64encode(text.encode('utf-8-sig')).decode()})

    def test_csv_mapping_preview_commit_unknown_fact_and_dedup(self):
        with connect(self.path) as c:
            staged=self.import_stage(c,'Позиция;Материал;Ед;Проект;Приход\n001;Датчик;шт.;5;2,5\n002;Извещатель;шт.;0;0\n')
            data=dict(import_id=staged['import_id'],sheet='CSV',header_row=1,mapping={'spec_num':0,'name':1,'unit':2,'qty_proj':3,'qty_received':4},defaults={'category':CATEGORIES[1]})
            preview=imports.inspect(c,self.pid,data)
            self.assertTrue(preview['valid']);self.assertEqual(c.execute('SELECT count(*) FROM resources').fetchone()[0],1)
            result=imports.commit(c,self.pid,{**data,'preview_token':preview['preview_token'],'confirm_receipts':True},self.path.parent/'archive')
            self.assertEqual(result['imported'],2)
            rows=c.execute('SELECT * FROM resources WHERE id IN (?,?)',tuple(result['resource_ids'])).fetchall()
            self.assertEqual(rows[0]['spec_num'],'001');self.assertIsNone(rows[0]['qty_fact']);self.assertEqual(rows[1]['qty_proj'],0)
            again=imports.inspect(c,self.pid,data)
            result2=imports.commit(c,self.pid,{**data,'preview_token':again['preview_token'],'confirm_receipts':True},self.path.parent/'archive')
            self.assertEqual(result2['imported'],0)
            self.assertEqual(c.execute('SELECT count(*) FROM supplies').fetchone()[0],3)

    def test_import_rejects_invalid_rows_formulas_stale_preview_and_missing_receipt_confirmation(self):
        with connect(self.path) as c:
            staged=self.import_stage(c,'Имя;Ед;Приход\nДатчик;шт.;2\n=HYPERLINK("http://example.test");шт.;-1\n')
            data=dict(import_id=staged['import_id'],sheet='CSV',header_row=1,mapping={'name':0,'unit':1,'qty_received':2},defaults={'category':CATEGORIES[1]})
            preview=imports.inspect(c,self.pid,data);self.assertFalse(preview['valid'])
            with self.assertRaises(ValueError):imports.commit(c,self.pid,{**data,'preview_token':preview['preview_token'],'confirm_receipts':True},self.path.parent/'archive')
            self.assertEqual(c.execute('SELECT count(*) FROM resources').fetchone()[0],1)
            good=self.import_stage(c,'Имя;Ед;Приход\nДатчик;шт.;2\n');data['import_id']=good['import_id'];preview=imports.inspect(c,self.pid,data)
            with self.assertRaises(ValueError):imports.commit(c,self.pid,{**data,'preview_token':preview['preview_token']},self.path.parent/'archive')
            with self.assertRaises(ValueError):imports.commit(c,self.pid,{**data,'preview_token':'stale','confirm_receipts':True},self.path.parent/'archive')


    def test_category_mapping_and_missing_category_default(self):
        with connect(self.path) as c:
            staged=self.import_stage(c,'Обозначение;Наименование;Ед;Проект\nКабели;Кабель;м;380\n;Консоль;шт.;10\n')
            data=dict(import_id=staged['import_id'],sheet='CSV',header_row=1,mapping={'category':0,'name':1,'unit':2,'qty_proj':3})
            bad=imports.inspect(c,self.pid,data)
            self.assertFalse(bad['valid'])
            self.assertEqual(bad['category_values'],['Кабели'])
            data.update(category_map={'Кабели':CATEGORIES[3]},defaults={'category':CATEGORIES[2]})
            good=imports.inspect(c,self.pid,data)
            self.assertTrue(good['valid'])
            result=imports.commit(c,self.pid,{**data,'preview_token':good['preview_token']},self.path.parent/'archive')
            self.assertEqual(result['imported'],2)
            for rid in result['resource_ids']:
                resource=c.execute('SELECT qty_fact FROM resources WHERE id=?',(rid,)).fetchone()
                self.assertIsNone(resource['qty_fact'])
            self.assertEqual(c.execute('SELECT count(*) FROM supplies WHERE resource_id IN (?,?)',result['resource_ids']).fetchone()[0],0)
            with self.assertRaises(ValueError):imports.inspect(c,self.pid,{**data,'category_map':{'Кабели':'несуществующая'}})


class XlsxImportTests(WorkspaceFixture,unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.pid=self.create()["projects"][0]["id"]
    # Один дополнительный путь чтения; остальные бизнес-сценарии выполняются базовым классом.
    def test_xlsx_sheet_selection_and_text_positions(self):
        import io,zipfile
        content={
            '[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
            '_rels/.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
            'xl/workbook.xml':'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Материалы" sheetId="1" r:id="rId1"/></sheets></workbook>',
            'xl/_rels/workbook.xml.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
            'xl/worksheets/sheet1.xml':'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Позиция</t></is></c><c r="B1" t="inlineStr"><is><t>Материал</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>0007</t></is></c><c r="B2" t="inlineStr"><is><t>Датчик</t></is></c></row></sheetData></worksheet>'}
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w') as z:
            for name,text in content.items():z.writestr(name,text)
        with connect(self.path) as c:
            staged=imports.stage(c,self.pid,dict(filename='Ведомость.xlsx',content=base64.b64encode(output.getvalue()).decode()))
            data=dict(import_id=staged['import_id'],sheet='Материалы',header_row=1,mapping={'spec_num':0,'name':1},defaults={'unit':'шт.','category':CATEGORIES[1]})
            view=imports.inspect(c,self.pid,data)
            self.assertTrue(view['valid']);self.assertEqual(view['rows'][0]['values']['spec_num'],'0007')
            result=imports.commit(c,self.pid,{**data,'preview_token':view['preview_token']},self.path.parent/'archive')
            self.assertEqual(result['imported'],1)
            self.assertEqual(c.execute('SELECT locator FROM resource_sources').fetchone()[0],'Строка 2')

if __name__=='__main__':unittest.main()
