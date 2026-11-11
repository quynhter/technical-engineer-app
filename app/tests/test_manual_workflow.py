import contextlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from itd.db import initialize,connect,add_object,add_project
from itd.resources import add_resource,CATEGORIES
from itd.acts import register_form,add_act,set_resources,build_context
from itd.workspace import save_entry
from itd.manual import execute,bind_entries,context,source_issues


class ManualTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'itd.db';initialize(self.db)
        with connect(self.db) as c:
            self.obj=add_object(c,'Полное название объекта')
            self.pid=add_project(c,object_id=self.obj,section_code='ТЕСТ',code='ТЕСТ',name='Раздел')
            self.other=add_project(c,object_id=self.obj,section_code='ДРУГ',code='ДРУГ',name='Другой раздел')
            self.rid=add_resource(c,project_id=self.pid,name='Кабель',category=CATEGORIES[3],unit='м',qty_proj=100)
            register_form(c,code='TEST',name='Акт',fields=[])
            self.aid=add_act(c,project_id=self.pid,act_type='TEST');set_resources(c,self.aid,[self.rid])

    def supply(self,c,**overrides):
        return execute(c,self.pid,'supply-add',dict(resource_id=self.rid,source_key='накладная1/строка1',source='Накладная 1, стр. 1',status='accepted',quantity=15,**overrides))

    def test_supply_idempotence_balance_and_independent_fact(self):
        with connect(self.db) as c:
            s=self.supply(c);self.assertEqual(self.supply(c)['id'],s['id'])
            execute(c,self.pid,'allocate',dict(act_id=self.aid,supply_id=s['id'],quantity=10,expected={'quantity':None}))
            second=add_act(c,project_id=self.pid,act_type='TEST');set_resources(c,second,[self.rid])
        with self.assertRaisesRegex(ValueError,'остаток'),connect(self.db) as c:
            execute(c,self.pid,'allocate',dict(act_id=second,supply_id=s['id'],quantity=6,expected={'quantity':None}))
        with connect(self.db) as c:
            execute(c,self.pid,'allocate',dict(act_id=second,supply_id=s['id'],quantity=5,expected={'quantity':None}))
            view=context(c,self.pid)
            self.assertEqual(view['supplies'][0]['remaining'],0)
            self.assertIsNone(c.execute('SELECT qty_fact FROM resources WHERE id=?',(self.rid,)).fetchone()[0])
            self.assertEqual(c.execute('SELECT count(*) FROM work_facts').fetchone()[0],0)
            print_context = build_context(c,self.aid)['context']
            model = print_context.pop('_template_context')
            self.assertEqual(print_context, {})
            self.assertEqual(model['form'], {})
        with self.assertRaisesRegex(ValueError,'Ожидаемые'),connect(self.db) as c:
            execute(c,self.pid,'allocate',dict(act_id=self.aid,supply_id=s['id'],quantity=9,expected={'quantity':None}))

    def test_rejected_supply_scopes_and_unknown_quantity(self):
        with connect(self.db) as c:
            s=execute(c,self.pid,'supply-add',dict(resource_id=self.rid,source_key='строка',source='Источник',status='rejected',quantity=None))
            self.assertIsNone(context(c,self.pid)['supplies'][0]['remaining'])
        for pid in (self.pid,self.other):
            with self.assertRaises(ValueError),connect(self.db) as c:
                execute(c,pid,'allocate',dict(act_id=self.aid,supply_id=s['id'],quantity=1,expected={'quantity':None}))
        with connect(self.db) as c:
            execute(c,self.pid,'supply-set',dict(id=s['id'],status='accepted',note='Подтверждение',expected={'revision':1}))
            execute(c,self.pid,'allocate',dict(act_id=self.aid,supply_id=s['id'],quantity=1,expected={'quantity':None}))
            execute(c,self.pid,'supply-set',dict(id=s['id'],status='rejected',note='Обнаружено несоответствие',expected={'revision':2}))
            self.assertEqual(source_issues(c,self.aid)[0]['code'],'act_material_invalid')
            with self.assertRaisesRegex(ValueError,'поставки'):build_context(c,self.aid,draft=False)

    def test_entry_revision_stale_final_and_explicit_source_review(self):
        with connect(self.db) as c:
            e=save_entry(c,self.pid,dict(kind='work',title='Прокладка',resource_id=self.rid,work_type='cable',work_fields={'line_number':'КЛ-1'}))
            bind_entries(c,self.aid,[e['id']]);self.assertEqual(source_issues(c,self.aid),[])
            before=context(c,self.pid)['sources']
            e=dict(c.execute('SELECT * FROM workspace_entries WHERE id=?',(e['id'],)).fetchone());e['work_fields']=json.loads(e['work_fields'])
        with self.assertRaisesRegex(ValueError,'основание'),connect(self.db) as c:
            save_entry(c,self.pid,{**e,'title':'Изменено'})
        with connect(self.db) as c:
            save_entry(c,self.pid,{**e,'title':'Изменено','change_reason':'Уточнение по источнику'})
            self.assertEqual(source_issues(c,self.aid)[0]['code'],'entry_source_changed')
            with self.assertRaises(ValueError):build_context(c,self.aid,draft=False)
            execute(c,self.pid,'sources-review',dict(act_id=self.aid,reason='Состав и содержание акта повторно сверены',expected=before))
            self.assertEqual(source_issues(c,self.aid),[])
            execute(c,self.pid,'act-composition',dict(act_id=self.aid,resources=[],schemes=[],expected={'resources':[self.rid],'schemes':[]}))
            self.assertEqual(source_issues(c,self.aid)[0]['code'],'entry_resource_missing')
            with self.assertRaises(ValueError):build_context(c,self.aid,draft=False)

    def test_live_journal_mapping_preserves_unknown_and_no_fact_side_effects(self):
        with connect(self.db) as c:
            register_form(c,code='J',name='Журнал',form_group='statement',fields=[{'key':'rows','kind':'table','value':None,'required':True,'fields':[
                {'key':'text','kind':'reference','source':'item.text','required':True},
                {'key':'q','kind':'reference','source':'item.q','required':False}]}])
            j=execute(c,self.pid,'journal-add',dict(act_type='J',entry_kind='work',work_type='cable',table_key='rows',mapping={'text':'entry.work_fields.line_number','q':'entry.quantity'}))['act_id']
            save_entry(c,self.pid,dict(kind='work',title='Прокладка',work_type='cable',work_fields={'line_number':'КЛ-1'}))
            save_entry(c,self.pid,dict(kind='work',title='Иные работы',work_type='general'))
            ctx=build_context(c,j)['context']['rows']
            self.assertEqual(ctx,[{'text':'КЛ-1','q':''}])
            save_entry(c,self.pid,dict(kind='work',title='Прокладка 2',work_type='cable',quantity=0,work_fields={'line_number':'КЛ-2'}))
            self.assertEqual(build_context(c,j)['context']['rows'][1]['q'],0)
            self.assertEqual(c.execute('SELECT count(*) FROM work_facts').fetchone()[0],0)

    def test_designer_units_periods_and_display_name_do_not_change_official_name(self):
        with connect(self.db) as c:
            org=execute(c,self.pid,'designer-add',{'name':'Разработчик'})['id']
            u=execute(c,self.pid,'unit-add',{'name':'Корпус 1','genplan_num':'1'})['id']
            execute(c,self.pid,'update',{'entity':'projects','id':self.pid,'changes':{'unit_id':u},'expected':{'unit_id':None}})
            execute(c,self.pid,'period-set',{'org_id':org,'active_from':'2026-10-01','active_to':None,'basis':'Договор'})
            execute(c,self.pid,'update',{'entity':'objects','id':self.obj,'changes':{'display_name':'Коротко'},'expected':{'display_name':None}})
            self.assertEqual(c.execute('SELECT name FROM objects WHERE id=?',(self.obj,)).fetchone()[0],'Полное название объекта')
            period=context(c,self.pid)['periods'][0]
        with self.assertRaises(ValueError),connect(self.db) as c:
            execute(c,self.pid,'period-set',{'org_id':org,'active_from':'2026-11-01','active_to':'2026-10-01','basis':'Договор','expected':{'revision':period['revision']}})
        with self.assertRaises(ValueError),connect(self.db) as c:
            execute(c,self.other,'update',{'entity':'resources','id':self.rid,'changes':{'name':'Чужое'},'expected':{'name':'Кабель'}})

    def test_catalog_connection_preserves_registered_form(self):
        with connect(self.db) as c:
            execute(c,self.pid,'form-connect',{'code':'И_1_13_07_18'})
        with self.assertRaisesRegex(ValueError,'уже зарегистрирована'),connect(self.db) as c:
            execute(c,self.pid,'form-connect',{'code':'И_1_13_07_18'})

    def test_composition_conflicts_scope_and_supply_diagnostics(self):
        with connect(self.db) as c:
            supply=self.supply(c)
            execute(c,self.pid,'allocate',dict(act_id=self.aid,supply_id=supply['id'],quantity=5,expected={'quantity':None}))
            execute(c,self.pid,'act-composition',dict(act_id=self.aid,resources=[],schemes=[],expected={'resources':[self.rid],'schemes':[]}))
            self.assertEqual(source_issues(c,self.aid)[0]['code'],'act_material_invalid')
        with self.assertRaisesRegex(ValueError,'уже изменён'),connect(self.db) as c:
            execute(c,self.pid,'act-composition',dict(act_id=self.aid,resources=[self.rid],schemes=[],expected={'resources':[self.rid],'schemes':[]}))
        with self.assertRaises(ValueError),connect(self.db) as c:
            execute(c,self.other,'act-composition',dict(act_id=self.aid,resources=[],schemes=[],expected={'resources':[],'schemes':[]}))

    def test_http_original_integrity_scope_and_static_script(self):
        from itd.web import WorkspaceServer
        from itd.archive import import_file,link_file,archived_path
        original=Path(self.tmp.name)/'исходник.txt';original.write_bytes(b'original bytes')
        with connect(self.db) as c:
            aid=import_file(c,archive_root=self.db.parent/'archive',source=original,doc_type='other',title='Источник')['id']
            link_file(c,attachment_id=aid,entity='project',entity_id=self.pid)
            storage=c.execute('SELECT storage_path FROM attachments WHERE id=?',(aid,)).fetchone()[0]
        server = WorkspaceServer(('127.0.0.1',0),self.db)
        _, initial_code = server.prepare()
        session = server.accounts.login(initial_code)["session"]
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        def get(path):
            try:
                with urlopen(Request(server.origin+path,headers={'X-ITD-Token':session})) as response:return response.status,response.read()
            except HTTPError as e:
                with e:return e.code,e.read()
        self.assertEqual(get('/api/original?project_id='+str(self.pid)+'&attachment_id='+str(aid)),(200,b'original bytes'))
        self.assertEqual(get('/api/original?project_id='+str(self.other)+'&attachment_id='+str(aid))[0],400)
        archived_path(self.db.parent/'archive',storage).write_bytes(b'corrupt')
        self.assertEqual(get('/api/original?project_id='+str(self.pid)+'&attachment_id='+str(aid))[0],400)
        status,html=get('/');self.assertEqual(status,200)
        self.assertLess(html.index(b'/manual.js'),html.index(b'/app.js'))
        self.assertEqual(get('/manual.js')[0],200)
        self.assertEqual(get('/api/package?project_id='+str(self.pid))[0],400)

    def test_cli_uses_same_supply_service(self):
        from itd.__main__ import main
        source=Path(self.tmp.name)/'supply.json'
        source.write_text(json.dumps(dict(resource_id=self.rid,source_key='cli1',source='Источник CLI',status='pending',quantity=None)),encoding='utf-8')
        out=io.StringIO()
        with contextlib.redirect_stdout(out):main(['--db',str(self.db),'workspace-action','--project-id',str(self.pid),'--action','supply-add','--data',str(source)])
        saved=json.loads(out.getvalue())
        with connect(self.db) as c:self.assertEqual(context(c,self.pid)['supplies'][0]['id'],saved['id'])

    def test_http_new_operations_preview_and_rollback(self):
        from itd.web import WorkspaceServer
        server = WorkspaceServer(('127.0.0.1',0),self.db)
        _, initial_code = server.prepare()
        session = server.accounts.login(initial_code)["session"]
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        def request(path,data=None):
            req=Request(server.origin+path,headers={'X-ITD-Token':session,'Content-Type':'application/json'},data=json.dumps(data).encode() if data is not None else None)
            try:
                with urlopen(req) as resp:return resp.status,json.loads(resp.read())
            except HTTPError as e:
                with e:return e.code,json.loads(e.read())
        status,data=request('/api/action',{'project_id':self.pid,'action':'supply-add','data':dict(resource_id=self.rid,source_key='web1',source='Источник веб',status='accepted',quantity=10)})
        self.assertEqual(status,200,data)
        status,view=request('/api/project?project_id='+str(self.pid))
        self.assertEqual(status,200,view);self.assertEqual(view['manual']['supplies'][0]['id'],data['id'])
        status,preview=request(f'/api/context?project_id={self.pid}&act_id={self.aid}')
        self.assertEqual(status,200,preview);self.assertEqual(preview['source_issues'],[])
        self.assertEqual(request(f'/api/context?project_id={self.other}&act_id={self.aid}')[0],400)
        self.assertEqual(request('/api/review',{'project_id':self.pid,'act_id':self.aid,'note':'Без подтверждения'})[0],400)


if __name__=='__main__':unittest.main()
