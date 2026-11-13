"""Общий путь выбора/перетаскивания и ограничения загрузок."""
from pathlib import Path
import shutil
import subprocess
import unittest

ASSETS=Path(__file__).parents[1]/'itd/web_assets'

@unittest.skipUnless(shutil.which('node'),'Нужен Node')
class FileUploadJsTests(unittest.TestCase):
    def test_drop_dispatches_the_same_change_event_and_rejects_invalid_input(self):
        source=(ASSETS/'ui.js').read_text()
        source=source[source.index('function uploadZone('):source.index('// Поиск не меняет')]
        script=r'''
const assert=require('node:assert/strict'),handlers={};
const document={addEventListener:(name,fn)=>{(handlers[name]??=[]).push(fn)},getElementById:()=>input};
const esc=String,icon=()=>'',errors=[];const notice=s=>errors.push(s);
const events=[];const input={multiple:false,accept:'.xlsx,.csv',dataset:{maxMb:'8'},dispatchEvent:e=>events.push(e)};
class DataTransfer{constructor(){this.files=[];this.items={add:file=>this.files.push(file)}}}
FUNCTIONS
const zone={dataset:{uploadTarget:'sheet'},classList:{add(){},remove(){}},contains:()=>false};
const file={name:'ведомость.xlsx',size:15};
const drop=files=>handlers.drop[0]({target:{closest:()=>zone},dataTransfer:{types:['Files'],files,items:[]},preventDefault(){}});
drop([file]);assert.equal(events.length,1);assert.equal(events[0].type,'change');assert.deepEqual(input.files,[file]);
drop([file,file]);assert.equal(events.length,1);assert.match(errors.pop(),/один файл/);
drop([{name:'а.pdf',size:15}]);assert.equal(events.length,1);assert.match(errors.pop(),/Допустимы/);
drop([{name:'а.csv',size:9*1024*1024}]);assert.equal(events.length,1);assert.match(errors.pop(),/большой/);
input.multiple=true;input.accept='';input.dataset.maxMb='32';drop([file,{name:'РД.pdf',size:30}]);assert.equal(events.length,2);
assert.match(uploadZone('source','Добавить',{multiple:true}),/data-upload-target="source"/);
assert.match(uploadZone('sheet','Выбрать',{maxMB:8,accept:'.xlsx,.csv'}),/data-max-mb="8"/);
'''.replace('FUNCTIONS',source)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_dynamic_dialog_close_buttons_follow_the_shared_close_guard(self):
        source=(ASSETS/'dialogs.js').read_text()
        script=r'''
const assert=require('node:assert/strict');let allowed=false,closed=0;const listeners={};
const dialog={open:true,querySelector:()=>({textContent:''}),addEventListener:(name,fn)=>listeners[name]=fn,close(){closed++;this.open=false}};
const document={getElementById:()=>dialog},window={};
FUNCTIONS
createWorkspaceDialog('editor',{beforeClose:()=>allowed});
const event={target:{closest:()=>({closest:()=>dialog})}};
listeners.click(event);assert.equal(closed,0);
allowed=true;listeners.click(event);assert.equal(closed,1);
'''.replace('FUNCTIONS',source)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
