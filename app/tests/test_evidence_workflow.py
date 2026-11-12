import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from itd import db
from itd.db import add_object, add_project, connect, initialize
from itd.resources import add_resource, CATEGORIES
from itd.archive import import_file, link_file
from itd.acts import add_act, register_form, set_resources, build_context
from itd.changes import update_record
from itd.releases import register_release
from itd.specification import import_specification
from itd.revision_compare import compare
from itd import workflow as w
from itd.__main__ import main


class EvidenceWorkflowTests(unittest.TestCase):
    def test_transfer_and_measurements_do_not_claim_mounted_quantities(self):
        with connect(self.path) as c:
            for code in ('СП_77_А_3','СП_77_А_16'):
                register_form(c,code=code,name=code,fields=[])
                aid=add_act(c,project_id=self.pid,act_type=code,date_signed='2026-01-01')
                set_resources(c,aid,[self.rid])
            report=w.report(c,self.pid)
            missing=[issue['act_id'] for issue in report['findings'] if issue['code']=='act_facts_missing']
            self.assertEqual(missing,[self.act])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root/'itd.db'
        initialize(self.path)
        with connect(self.path) as c:
            obj = add_object(c,'Тестовый объект')
            self.pid = add_project(c,object_id=obj,section_code='СПС',code='РД-1',name='Сигнализация')
            self.other = add_project(c,object_id=obj,section_code='АОВ',code='РД-2',name='Автоматизация')
            self.rid = add_resource(c,project_id=self.pid,name='Извещатель',unit='шт.',category=CATEGORIES[1],qty_proj=12,type_mark='ИП',serial_numbers=['001','002'])
            register_form(c,code='ТЕСТ',name='Тестовый акт',fields=[])
            self.act = add_act(c,project_id=self.pid,act_type='ТЕСТ',date_signed='2026-10-28')
            set_resources(c,self.act,[self.rid])

    def attachment(self,c,kind='rd',name='Источник'):
        path = self.root/(name+'.bin'); path.write_bytes(name.encode())
        aid = import_file(c,archive_root=self.root/'archive',source=path,doc_type=kind,title=name)['id']
        link_file(c,attachment_id=aid,entity='project',entity_id=self.pid)
        return aid

    def fact(self,**overrides):
        return dict(resource_id=self.rid,source_key='report:1/row:1',location='Помещение 105',
                    work_description='Монтаж',quantity=5,source='Сообщение пользователя 29.10.2026',
                    reported_by='Мастер Иванов',status='confirmed',end_date='2026-10-29',**overrides)

    def release(self,c,name='Акт.docx',mode='final',pid=None):
        path = self.root/name; path.write_bytes(name.encode())
        return register_release(c,project_id=pid or self.pid,act_id=self.act if pid is None else None,kind='docx',title=name,path=path,mode=mode)

    def test_facts_are_idempotent_do_not_overwrite_total_and_unknown_stays_unknown(self):
        with connect(self.path) as c:
            f = w.add_fact(c,self.pid,self.fact())
            self.assertTrue(w.add_fact(c,self.pid,self.fact())['duplicate'])
            self.assertIsNone(w.fact_summary(c,self.pid)[0]['qty_fact'])
            d=self.fact(); d.update(source_key='report:2',quantity=None)
            w.add_fact(c,self.pid,d)
            summary=w.fact_summary(c,self.pid)[0]
            self.assertIsNone(summary['confirmed_total'])
            self.assertEqual(len(summary['confirmed_ids']),2)
            w.set_fact_status(c,2,{'status':'void','reason':'Дубликат сведений'},{'status':'confirmed'})
            self.assertEqual(w.fact_summary(c,self.pid)[0]['confirmed_total'],5)
            with self.assertRaises(ValueError): w.add_fact(c,self.pid,{**self.fact(),'quantity':6})
            self.assertEqual(c.execute('SELECT COUNT(*) FROM work_facts').fetchone()[0],2)
            self.assertEqual(f['unit'],'шт.')

    def test_fact_validation_rejects_wrong_scope_dates_unit_and_invalid_quantity(self):
        with connect(self.path) as c:
            for change in ({'unit':'м'},{'quantity':float('nan')},{'quantity':True},{'start_date':'2026-10-30'}, {'end_date':'2026-02-30'},{'source':''},{'resource_id':True}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    w.add_fact(c,self.pid,{**self.fact(),**change})
            with self.assertRaises(ValueError): w.add_fact(c,self.other,self.fact())
            aid=self.attachment(c)
            w.add_fact(c,self.pid,{**self.fact(),'attachment_id':aid})

    def test_fact_confirmation_void_and_act_links_remain_diagnosable(self):
        with connect(self.path) as c:
            d={**self.fact(),'status':'pending'}; f=w.add_fact(c,self.pid,d)
            with self.assertRaises(ValueError): w.link_facts(c,self.act,[f['id']])
            w.set_fact_status(c,f['id'],{'status':'confirmed','reason':'Подтверждение пользователя 29.10.2026'},{'status':'pending'})
            with self.assertRaises(ValueError): w.set_fact_status(c,f['id'],{'status':'void','reason':'ошибка'},{'status':'pending'})
            w.link_facts(c,self.act,[f['id']])
            codes={i['code'] for i in w.report(c,self.pid)['findings']}
            self.assertIn('act_signed_before_work_end',codes)
            w.set_fact_status(c,f['id'],{'status':'void','reason':'Неверные сведения'},{'status':'confirmed'})
            self.assertIn('act_fact_not_confirmed',{i['code'] for i in w.report(c,self.pid)['findings']})

    def test_confirmed_facts_can_feed_an_explicit_form_table(self):
        with connect(self.path) as c:
            f=w.add_fact(c,self.pid,self.fact()); w.link_facts(c,self.act,[f['id']])
            update_record(c,entity='acts',record_id=self.act,changes={'fields':[{'key':'work','kind':'table','source':'facts','fields':[{'key':'place','kind':'reference','source':'item.location','required':True}]}]})
            self.assertEqual(build_context(c,self.act)['context']['work'],[{'place':'Помещение 105'}])
            w.set_fact_status(c,f['id'],{'status':'void','reason':'Ошибка'},{'status':'confirmed'})
            self.assertNotEqual(build_context(c,self.act)['context']['work'],[{'place':'Помещение 105'}])

    def test_matrix_is_explicit_preserves_nonapplicability_and_requires_matching_targets(self):
        with connect(self.path) as c:
            self.assertFalse(w.matrix(c,self.pid)['configured'])
            data={'title':'Акт монтажа','work_scope':'Помещение 105','basis':'Согласованный перечень пользователя','kind':'act','act_type':'ТЕСТ'}
            req=w.add_requirement(c,self.pid,data)
            self.assertEqual(w.matrix(c,self.pid)['requirements'][0]['availability'],'missing')
            w.set_requirement(c,req['id'],{'act_id':self.act},{'act_id':None})
            self.assertEqual(w.matrix(c,self.pid)['requirements'][0]['availability'],'prepared')
            with self.assertRaises(ValueError): w.add_requirement(c,self.other,{**data,'act_id':self.act})
            with self.assertRaises(ValueError): w.set_requirement(c,req['id'],{'state':'not_applicable'},{'state':'required'})
            w.set_requirement(c,req['id'],{'state':'not_applicable','reason':'Работы исключены пользователем'},{'state':'required'})
            self.assertEqual(w.matrix(c,self.pid)['requirements'][0]['availability'],'not_applicable')

    def test_generic_quality_file_participates_in_checks_and_statement(self):
        from itd.statement import statement_data
        with connect(self.path) as c:
            aid=self.attachment(c,'quality','Документ качества')
            link_file(c,attachment_id=aid,entity='resource',entity_id=self.rid)
            self.assertIn('quality_unreviewed',{f['code'] for f in w.report(c,self.pid)['findings']})
            w.add_quality_review(c,self.pid,{'resource_id':self.rid,'attachment_id':aid,'status':'matches','checked_by':'Пользователь','checked_date':'2026-10-29','source':'Документ, стр. 1','note':'Сверено'})
            self.assertNotIn('quality_unreviewed',{f['code'] for f in w.report(c,self.pid)['findings']})
            self.assertIn('Документ качества',str(statement_data(c,self.pid)))

    def test_quality_presence_is_not_review_and_review_becomes_stale_after_resource_change(self):
        with connect(self.path) as c:
            aid=self.attachment(c,'passport','Паспорт')
            link_file(c,attachment_id=aid,entity='resource',entity_id=self.rid)
            codes=lambda: {i['code'] for i in w.report(c,self.pid)['findings']}
            self.assertIn('quality_unreviewed',codes())
            w.add_quality_review(c,self.pid,{'resource_id':self.rid,'attachment_id':aid,'status':'matches','checked_by':'Пользователь','checked_date':'2026-10-29','source':'Паспорт, стр. 1','note':'Марка ИП, заводские номера 001 и 002 сверены'})
            self.assertNotIn('quality_unreviewed',codes())
            self.assertNotIn('quality_stale',codes())
            update_record(c,entity='resources',record_id=self.rid,changes={'type_mark':'ИП-другой'})
            self.assertIn('quality_stale',codes())

    def item(self,qty=12,key='page:1/row:1',position='1'):
        return {'source_key':key,'verified':True,'resource':{'spec_num':position,'name':'Извещатель','type_mark':'ИП','category':CATEGORIES[1],'unit':'шт.','qty_proj':qty}}

    def test_compare_versions_preserves_user_edits_and_reports_impacted_acts(self):
        with connect(self.path) as c:
            old=self.attachment(c,name='РД старое'); new=self.attachment(c,name='РД новое')
            item=self.item(); imported=import_specification(c,project_id=self.pid,attachment_id=old,items=[item])['imported'][0]
            set_resources(c,self.act,[self.rid,imported])
            update_record(c,entity='resources',record_id=imported,changes={'name':'Правка пользователя','qty_fact':10})
            events=c.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0]
            diff=compare(c,self.pid,old,new,[item],[self.item(15,'page:2/row:9')],complete=True)
            self.assertEqual(diff['changed'][0]['changes']['qty_proj'],{'old':12.,'new':15.})
            self.assertEqual(diff['changed'][0]['act_ids'],[self.act])
            self.assertFalse(diff['applied'])
            self.assertEqual(c.execute('SELECT name,qty_fact FROM resources WHERE id=?',(imported,)).fetchone()[:],('Правка пользователя',10))
            self.assertEqual(events,c.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0])

    def test_compare_duplicates_and_uncertainty_are_never_silently_matched(self):
        with connect(self.path) as c:
            old=self.attachment(c,name='РД1'); new=self.attachment(c,name='РД2')
            diff=compare(c,self.pid,old,new,[self.item()],[{'source_key':'unknown','verified':False}],complete=True)
            self.assertFalse(diff['removed_candidates'][0]['reliable'])
            diff=compare(c,self.pid,old,new,[self.item()],[self.item(),self.item(key='second')])
            self.assertEqual(len(diff['ambiguous']),1)
            self.assertFalse(diff['added'])
            with self.assertRaises(ValueError): compare(c,self.pid,old,new,[self.item()],[self.item(),self.item()])

    def delivery_data(self,rid):
        return {'release_id':rid,'recipient':'Технический заказчик','event_date':'2026-10-29','source':'Письмо 12','note':'Передан на проверку'}

    def event(self,status,**changes):
        return {'status':status,'event_date':'2026-10-29','source':'Письмо 13','note':'Подтверждено пользователем',**changes}

    def test_delivery_lifecycle_tracks_each_remark_and_exact_release_with_history(self):
        with connect(self.path) as c:
            rid=self.release(c); delivery=w.add_delivery(c,self.pid,self.delivery_data(rid)); did=delivery['id']
            w.set_delivery(c,did,self.event('remarks'),{'revision':1})
            remark=w.add_remark(c,did,{'description':'Уточнить дату','source':'Лист замечаний, п. 1'})
            with self.assertRaises(ValueError): w.set_delivery(c,did,self.event('corrected'),{'revision':2})
            new=self.release(c,'Исправленный.docx')
            w.resolve_remark(c,remark['id'],{'resolution':'Дата уточнена по отчёту мастера','resolution_source':'Отчёт 29.10','resolution_date':'2026-10-29','resolution_release_id':new},{'status':'open'})
            w.set_delivery(c,did,self.event('corrected',release_id=new),{'revision':2})
            w.set_delivery(c,did,self.event('sent'),{'revision':3})
            w.set_delivery(c,did,self.event('accepted'),{'revision':4})
            events=c.execute('SELECT status,release_id FROM delivery_events WHERE delivery_id=? ORDER BY revision',(did,)).fetchall()
            self.assertEqual([r[0] for r in events],['sent','remarks','corrected','sent','accepted'])
            self.assertEqual([r[1] for r in events],[rid,rid,new,new,new])
            self.assertEqual(w.workflow_context(c,self.pid)['deliveries'][0]['status'],'accepted')

    def test_delivery_rejects_draft_tampered_file_wrong_scope_stale_state_and_backdated_events(self):
        with connect(self.path) as c:
            draft=self.release(c,'Черновик.docx','draft')
            with self.assertRaises(ValueError): w.add_delivery(c,self.pid,self.delivery_data(draft))
            wrong=self.release(c,'Другой.docx',pid=self.other)
            with self.assertRaises(ValueError): w.add_delivery(c,self.pid,self.delivery_data(wrong))
            rid=self.release(c); d=w.add_delivery(c,self.pid,self.delivery_data(rid))
            with self.assertRaises(ValueError): w.set_delivery(c,d['id'],self.event('accepted'),{'revision':2})
            with self.assertRaises(ValueError): w.set_delivery(c,d['id'],self.event('accepted',event_date='2026-10-28'),{'revision':1})
            (self.root/'Акт.docx').write_bytes(b'tampered')
            with self.assertRaises(ValueError): w.set_delivery(c,d['id'],self.event('accepted'),{'revision':1})

    def test_cli_reports_and_json_file_paths_do_not_overwrite_or_change_database(self):
        with connect(self.path) as c: before=c.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0]
        output=self.root/'отчёт с пробелами.json'
        argv=['--db',str(self.path),'project-check','--project-id',str(self.pid),'--output',str(output)]
        with contextlib.redirect_stdout(io.StringIO()): main(argv)
        self.assertEqual(json.loads(output.read_text())['project_id'],self.pid)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit): main(argv)
        with connect(self.path) as c: self.assertEqual(before,c.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0])
        bad=self.root/'bad.json'; bad.write_text('{broken')
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(['--db',str(self.path),'fact-add','--project-id',str(self.pid),'--data',str(bad)])
        with connect(self.path) as c: self.assertEqual(c.execute('SELECT COUNT(*) FROM work_facts').fetchone()[0],0)

    def test_migration_from_007_preserves_business_data_and_old_releases(self):
        legacy=self.root/'legacy.db'; migrations=self.root/'old'; migrations.mkdir()
        for p in db.MIGRATIONS.glob('*.sql'):
            if int(p.name[:3])<=10: shutil.copy2(p,migrations/p.name)
        with patch.object(db,'MIGRATIONS',migrations): initialize(legacy)
        with connect(legacy) as c:
            oid=add_object(c,'Полное прежнее название'); pid=add_project(c,object_id=oid,section_code='СПС',code='Старый',name='Раздел')
            add_resource(c,project_id=pid,name='Кабель',unit='м',category=CATEGORIES[3],qty_proj=100,qty_fact=None)
            before=[tuple(r) for r in c.execute('SELECT * FROM resources')]
            original=self.root/'legacy-release.xlsx'; original.write_bytes(b'unchanged legacy release')
            release_id=register_release(c,project_id=pid,kind='xlsx',title='Прежняя ведомость',path=original,mode='final')
            release_before=dict(c.execute('SELECT * FROM releases WHERE id=?',(release_id,)).fetchone())
        initialize(legacy); initialize(legacy)
        with connect(legacy) as c:
            self.assertEqual(before,[tuple(r) for r in c.execute('SELECT * FROM resources')])
            self.assertEqual(c.execute('SELECT name FROM objects').fetchone()[0],'Полное прежнее название')
            self.assertEqual(c.execute('SELECT COUNT(*) FROM work_facts').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0],21)
            self.assertEqual(dict(c.execute('SELECT * FROM releases WHERE id=?',(release_id,)).fetchone()),release_before)
            self.assertEqual(original.read_bytes(),b'unchanged legacy release')

    def test_cli_add_fact_confirm_and_compare_from_files(self):
        data=self.root/'факт мастера.json'; data.write_text(json.dumps({**self.fact(),'status':'pending'},ensure_ascii=False))
        def cli(*args):
            output=io.StringIO()
            with contextlib.redirect_stdout(output): main(['--db',str(self.path),*args])
            return json.loads(output.getvalue())
        fact=cli('fact-add','--project-id',str(self.pid),'--data',str(data))
        before=self.root/'before.json'; before.write_text('{"status":"pending"}')
        change=self.root/'change.json'; change.write_text('{"status":"confirmed","reason":"Confirmed by user"}')
        cli('fact-set','--fact-id',str(fact['id']),'--data',str(change),'--expected',str(before))
        self.assertEqual(cli('fact-summary','--project-id',str(self.pid))[0]['confirmed_total'],5)
        with connect(self.path) as c:
            old=self.attachment(c,name='CLI старая РД'); new=self.attachment(c,name='CLI новая РД')
        oldfile=self.root/'old.json'; oldfile.write_text(json.dumps([self.item()]))
        newfile=self.root/'new.json'; newfile.write_text(json.dumps([self.item(15)]))
        diff=cli('spec-compare','--project-id',str(self.pid),'--old-attachment-id',str(old),'--new-attachment-id',str(new),'--old-data',str(oldfile),'--data',str(newfile),'--complete')
        self.assertEqual(diff['changed'][0]['changes']['qty_proj']['new'],15)

    def test_report_detects_selected_release_stale_after_data_edit(self):
        with connect(self.path) as c:
            fields=[{'key':'name','kind':'reference','source':'object.name','required':True}]
            update_record(c,entity='acts',record_id=self.act,changes={'fields':fields})
            context=build_context(c,self.act)['context']
            path=self.root/'old.docx'; path.write_bytes(b'old')
            gid=c.execute("INSERT INTO generated_documents(act_id,output_path,sha256,mode,context_json,template_sha256) VALUES(?,?,?,'final',?,?)",(self.act,str(path),'a'*64,json.dumps(context),'b'*64)).lastrowid
            rid=register_release(c,project_id=self.pid,act_id=self.act,generated_id=gid,kind='docx',title='Акт',path=path,mode='final')
            c.execute('UPDATE releases SET selected=1 WHERE id=?',(rid,))
            obj=c.execute('SELECT object_id FROM projects WHERE id=?',(self.pid,)).fetchone()[0]
            update_record(c,entity='objects',record_id=obj,changes={'name':'Полное изменённое название'})
            findings=w.report(c,self.pid)['findings']
            self.assertIn('release_context_changed',{f['code'] for f in findings})


if __name__=='__main__': unittest.main()
