"""Предпросмотр сохраняет семантику полей и ограничения окончательного DOCX."""
from pathlib import Path
import shutil
import subprocess
import unittest

class DocumentPreviewJsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Нужен Node')
    def test_readable_groups_empty_sources_escaping_and_final_gate(self):
        source=(Path(__file__).parents[1]/'itd/web_assets/manual.js').read_text()
        source=source[source.index('function previewFieldLabel'):source.index('async function previewAct')]
        script=r'''
const assert=require('node:assert/strict');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const card=(title,body)=>title+body;
const findingNames={entry_source_changed:'Рабочая запись изменилась'};
SOURCE
const v={act_num:'01/СПС',form_name:'Проверка',context:{t0_r0_c1:'<script>',rows:[{c1:0}]},preview_fields:[
 {key:'t0_r0_c1',label:'Номер барабана',group:'Содержание акта'},
 {key:'rows',label:'Результаты',kind:'table',group:'Таблицы и перечни',columns:[{key:'c1',label:'Затухание'}]}
],source_issues:[],missing:[],static_claims:[]};
let html=previewActHtml(1,v),visible=html.split('<details class="technical-detail">')[0];
assert.ok(visible.includes('Изменений в связанных источниках не найдено.'));
assert.ok(visible.includes('Затухание'));
assert.ok(visible.includes('&lt;script&gt;'));
assert.ok(!visible.includes('t0_r0_c1'));
assert.ok(visible.includes('>0</span>'));
assert.ok(visible.includes('data-final="1" data-preview-blocked="false"'));
assert.ok(previewActHtml(1,{...v,static_claims:['Работы выполнены']}).includes('data-final="1" data-preview-blocked="true"'));
assert.ok(previewActHtml(1,{...v,static_claims:['Работы выполнены'],review_current:true}).includes('data-final="1" data-preview-blocked="false"'));
assert.ok(previewActHtml(1,{...v,missing:['t0_r0_c1'],source_issues:[{code:'entry_source_changed',entry_id:5}]}).includes('data-final="1" data-preview-blocked="true"'));
assert.equal(previewMissingLabel('rows[1].c1',v.preview_fields),'Результаты · строка 1 · Затухание');
'''.replace('SOURCE',source)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
