import json
from pathlib import Path
import shutil
import subprocess
import unittest
from zipfile import ZipFile

from test_web_workspace import WorkspaceFixture
from itd.db import connect
from itd.acts import add_act, register_form, set_resources, build_context
from itd.resources import add_resource, CATEGORIES
from itd.workflow import add_fact, set_fact_status
from itd.managed import generate_managed
from itd.changes import update_record
from itd.statement import statement_data
from itd import document_versions


class ReactiveDocumentTests(WorkspaceFixture,unittest.TestCase):
    def setUp(self):
        super().setUp();state=self.create();self.pid=state['projects'][0]['id']
        self.templates=Path(self.tmp.name)/'templates';self.templates.mkdir()
        from docx import Document
        doc=Document();doc.add_paragraph('Количество: {{ rows[0].quantity }}');doc.save(self.templates/'REACTIVE.docx')
        with connect(self.path) as c:
            self.rid=add_resource(c,project_id=self.pid,name='Кабель',unit='м',category=CATEGORIES[3])
            register_form(c,code='REACTIVE',name='Очень длинное название формы '*20,form_group='statement',fields=[
                {'key':'rows','kind':'table','source':'resources','fields':[{'key':'quantity','kind':'reference','source':'item.qty_fact'}]}])
            self.aid=add_act(c,project_id=self.pid,act_type='REACTIVE');set_resources(c,self.aid,[self.rid])

    def fact(self,c,key,quantity,status='confirmed'):
        return add_fact(c,self.pid,{'resource_id':self.rid,'source_key':key,'location':'Этаж',
            'work_description':'Монтаж','quantity':quantity,'unit':'м','source':'ОЖР','reported_by':'Мастер','status':status})['id']

    def test_new_docx_after_fact_reads_live_quantity_keeps_historical_release(self):
        with connect(self.path) as c:
            old=generate_managed(c,act_id=self.aid,templates_dir=self.templates)
            self.assertEqual(Path(old['output']).name,'01_СПС.docx')
            self.fact(c,'first',4);self.fact(c,'pending',100,'pending');self.fact(c,'zero',0)
            new=generate_managed(c,act_id=self.aid,templates_dir=self.templates)
            with ZipFile(new['output']) as doc:self.assertIn('Количество: 4',doc.read('word/document.xml').decode())
            versions=document_versions.versions(c,self.pid,self.aid)
            self.assertEqual(len(versions),2)
            old_context=json.loads(c.execute('SELECT context_json FROM generated_documents WHERE id=(SELECT generated_id FROM releases WHERE id=?)',(old['release_id'],)).fetchone()[0])
            self.assertEqual(old_context['rows'][0]['quantity'],'')
            self.assertEqual(versions[-1]['snapshot']['rows'][0]['quantity'],4)
            self.assertEqual(statement_data(c,self.pid)['rows'][0][7],4)
            self.assertIsNone(c.execute('SELECT qty_fact FROM resources WHERE id=?',(self.rid,)).fetchone()[0])

    def test_next_version_omits_deleted_signer_keeps_historical_copy(self):
        from itd.ojr import set_act_people
        from itd import deletion
        with connect(self.path) as c:
            person=c.execute('SELECT id FROM signatories LIMIT 1').fetchone()[0]
            set_act_people(c,self.pid,self.aid,{'customer_control':person})
            generate_managed(c,act_id=self.aid,templates_dir=self.templates)
            current=document_versions.versions(c,self.pid,self.aid)[-1]
            plan=deletion.preview(c,self.pid,'signatories',person)
            deletion.apply(c,self.pid,'signatories',person,plan['token'])
            versions=document_versions.create(c,self.pid,self.aid,{'id':current['id'],'revision':current['revision']})
            self.assertEqual(versions[0]['signers'][0]['person_id'],person)
            self.assertEqual(versions[-1]['signers'],[])

    def test_void_unknown_zero_and_manual_total_have_consistent_semantics(self):
        with connect(self.path) as c:
            f=self.fact(c,'first',0)
            self.assertEqual(statement_data(c,self.pid)['rows'][0][7],0)
            unknown=self.fact(c,'unknown',None)
            self.assertEqual(build_context(c,self.aid)['context']['rows'][0]['quantity'],'')
            set_fact_status(c,unknown,{'status':'void','reason':'Ошибка'},{'status':'confirmed'})
            self.assertEqual(build_context(c,self.aid)['context']['rows'][0]['quantity'],0)
            c.execute('UPDATE resources SET qty_fact=12 WHERE id=?',(self.rid,))
            self.assertEqual(statement_data(c,self.pid)['rows'][0][7],12)

    def test_filename_symbols_and_length_are_normalized_on_card_save(self):
        with connect(self.path) as c:
            version=document_versions.ensure(c,self.pid,self.aid)[-1]
            value='Номер/раздел: "имя"?*|\\'+('Длинный текст '*60)
            data={'act_id':self.aid,'id':version['id'],'revision':version['revision'],
                  'card':{**version['card'],'filename_title':value},'signers':[]}
            saved=document_versions.save(c,self.pid,data)[-1]
            title=saved['card']['filename_title']
            self.assertLessEqual(len(title.encode()),160)
            self.assertFalse(set('<>:"/\\|?*')&set(title))
            result=generate_managed(c,act_id=self.aid,templates_dir=self.templates)
            self.assertTrue(Path(result['output']).is_file())


class ReactiveDownloadJsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Нужен Node')
    def test_latest_draft_refreshes_but_historical_and_signed_download_exact_file(self):
        source=(Path(__file__).parents[1]/'itd/web_assets/document-versions.js').read_text()
        source=source[source.index('async function downloadDocumentVersion('):source.index('function versionTables(')]
        script=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const calls=[],ctx={documentVersionState:{aid:1,selected:2,versions:[{id:1,release_id:10},{id:2,release_id:20}]},formDirty:false,
 pdata:{act_statuses:[]},projectId:1,downloadRelease:async id=>calls.push(['download',id]),
 api:async()=>{calls.push(['generate']);return {release_id:30}},loadProject:async()=>{},render:()=>{},openDocumentVersions:async()=>{}};
vm.runInNewContext(SOURCE,ctx);
(async()=>{
 await ctx.downloadDocumentVersion();assert.deepEqual(calls,[['generate'],['download',30]]);
 calls.length=0;ctx.documentVersionState.selected=1;
 await ctx.downloadDocumentVersion();assert.deepEqual(calls,[['download',10]]);
 calls.length=0;ctx.documentVersionState.selected=2;ctx.pdata.act_statuses=[{act_id:1,state:'signed'}];
 await ctx.downloadDocumentVersion();assert.deepEqual(calls,[['download',20]]);
})().catch(e=>{console.error(e);process.exitCode=1});
'''.replace('SOURCE',json.dumps(source))
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
