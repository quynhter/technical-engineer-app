"""Regression cases found in the role/state/security audit."""
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from itd.accounts import Accounts, SessionExpired, SESSION_IDLE, SESSION_LIFETIME, MAX_USER_SESSIONS
from itd.resource_import import sheets, table

ASSETS=Path(__file__).parents[1]/'itd/web_assets'


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.accounts=Accounts(Path(self.folder.name)/'accounts.db')
        self.code=self.accounts.initialize()

    def test_idle_polling_does_not_extend_session_and_activity_does(self):
        with patch('itd.accounts.monotonic',return_value=0): token=self.accounts.login(self.code)['session']
        with patch('itd.accounts.monotonic',return_value=SESSION_IDLE-1): self.accounts.authenticate(token,touch=False)
        with patch('itd.accounts.monotonic',return_value=SESSION_IDLE):
            with self.assertRaises(SessionExpired): self.accounts.authenticate(token)
        with patch('itd.accounts.monotonic',return_value=0): token=self.accounts.login(self.code)['session']
        with patch('itd.accounts.monotonic',return_value=SESSION_IDLE-1): self.accounts.authenticate(token)
        with patch('itd.accounts.monotonic',return_value=SESSION_IDLE+1): self.accounts.authenticate(token)

    def test_absolute_expiry_and_session_limit(self):
        with patch('itd.accounts.monotonic',return_value=0): tokens=[self.accounts.login(self.code)['session'] for _ in range(MAX_USER_SESSIONS+1)]
        self.assertNotIn(tokens[0],self.accounts.sessions)
        token=tokens[-1]
        for now in range(1000,SESSION_LIFETIME,1000):
            with patch('itd.accounts.monotonic',return_value=now): self.accounts.authenticate(token)
        with patch('itd.accounts.monotonic',return_value=SESSION_LIFETIME):
            with self.assertRaises(SessionExpired): self.accounts.authenticate(token)


class ImportLimitsTests(unittest.TestCase):
    def book(self, reference='CW1', dimension='A1:A1'):
        from openpyxl import Workbook
        book=Workbook();book.active['A1']='Название';book.active['A2']='Кабель'
        raw=io.BytesIO();book.save(raw);book.close()
        output=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw.getvalue())) as src,zipfile.ZipFile(output,'w') as dst:
            for name in src.namelist():
                content=src.read(name)
                if name=='xl/worksheets/sheet1.xml':
                    content=content.replace(b'A1:A2',dimension.encode()).replace(b'r="A2"',f'r="{reference}"'.encode())
                dst.writestr(name,content)
        return output.getvalue()

    def test_sparse_wide_workbook_rejected_before_openpyxl(self):
        content=self.book()
        with patch('openpyxl.load_workbook',side_effect=AssertionError('Must reject before loading')):
            with self.assertRaisesRegex(ValueError,'100 колонок'): sheets(content,'test.xlsx')
            with self.assertRaisesRegex(ValueError,'100 колонок'): table(content,'test.xlsx','Sheet',1)

    def test_sparse_tall_workbook_rejected(self):
        with self.assertRaisesRegex(ValueError,'Слишком много'): sheets(self.book('A1048576'),'test.xlsx')

    def test_wide_csv_rejected_before_accumulating_rows(self):
        with self.assertRaisesRegex(ValueError,'100 колонок'): table((','.join(['a']*101)+'\n').encode(),'test.csv','CSV',1)


@unittest.skipUnless(shutil.which('node'),'Нужен Node')
class BrowserStateTests(unittest.TestCase):
    def run_js(self, source, setup, checks):
        script="const vm=require('node:vm'),assert=require('node:assert/strict');\n"+setup+"\nvm.runInNewContext("+json.dumps(source)+",ctx);\n(async()=>{\n"+checks+"\n})().catch(e=>{console.error(e);process.exitCode=1});"
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_project_failure_and_activation_failure_preserve_state(self):
        source=(ASSETS/'app.js').read_text();source=source[source.index('async function loadProject('):source.index('async function loadObject(')]
        self.run_js(source,"""
let restored=0;const select={value:'2',dispatchEvent(){}};
const ctx={projectId:1,pdata:{project:{id:1}},editEntry:{id:7},selectedEntries:new Set([7]),currentUser:{role:'editor'},closeAgentHelp(){},tableLoading:()=>()=>restored++,Event:class{},$:()=>select,api:async()=>{throw Error('offline')}};
""","""
await assert.rejects(ctx.loadProject(2));assert.equal(ctx.projectId,1);assert.equal(ctx.pdata.project.id,1);assert(ctx.selectedEntries.has(7));assert.equal(select.value,1);assert.equal(restored,1);
ctx.api=async path=>{if(path==='/api/activate')throw Error('denied');return {project:{id:2}}};
await assert.rejects(ctx.loadProject(2,true));assert.equal(ctx.projectId,1);assert.equal(ctx.pdata.project.id,1);
ctx.api=async()=>({project:{id:2}});await ctx.loadProject(2);assert.equal(ctx.projectId,2);assert.equal(ctx.pdata.project.id,2);assert.equal(ctx.selectedEntries.size,0);
""")

    def test_action_preserves_existing_disabled_state_and_new_buttons(self):
        source=(ASSETS/'app.js').read_text();source=source[source.index('async function action('):source.index('function get(',source.index('async function action('))]
        self.run_js(source,"""
const old={disabled:true,isConnected:true,closest:()=>false},enabled={disabled:false,isConnected:true,closest:()=>false},fresh={disabled:true,isConnected:true,closest:()=>false};let buttons=[old,enabled];
const ctx={busy:false,notice(){},syncPreviewActions(){},document:{querySelectorAll:()=>buttons}};
""","""
await ctx.action(async()=>{assert(enabled.disabled);buttons.push(fresh);});assert(old.disabled);assert(!enabled.disabled);assert(fresh.disabled);assert(!ctx.busy);
""")

    def test_expired_session_preserves_unsaved_input(self):
        source=(ASSETS/'account.js').read_text();source=source[source.index('function suspendWorkspace('):source.index('function leaveWorkspace(')]
        self.run_js(source,"""
const button={hidden:true};const ctx={sessionSuspended:false,currentUser:{id:1},dirty:true,formDirty:true,token:'test',keepSession(){},$:()=>button,document:{querySelectorAll:()=>[button]},notice(){}};
""","""
ctx.suspendWorkspace();assert(ctx.dirty);assert(ctx.formDirty);assert(ctx.sessionSuspended);assert.equal(button.hidden,false);
""")

    def test_table_sort_numbers_dates_and_long_text(self):
        source=(ASSETS/'tables.js').read_text();source=source[:source.index('function enhanceDataTable(')]
        self.run_js(source,'const ctx={};',"""
assert(ctx.compareTableValues('2,5','10,2','number')<0);
assert(ctx.compareTableValues('31.12.2025','01.01.2026','date')<0);
assert(ctx.compareTableValues('Кабель 2','Кабель 10','text')<0);
""")

    def test_write_timeout_reports_unknown_outcome_without_retry(self):
        source=(ASSETS/'app.js').read_text();source=source[source.index('async function api('):source.index('function notice(')]
        self.run_js(source,"""
let calls=0;const ctx={sessionSuspended:false,token:'test',AbortSignal:{timeout:ms=>ms},fetch:async()=>{calls++;throw Object.assign(Error('timeout'),{name:'TimeoutError'});}};
""","""
await assert.rejects(ctx.api('/api/entry',{title:'test'}),/Результат операции неизвестен/);assert.equal(calls,1);
""")
