"""Человекочитаемый ввод акта: типы значений и живые ссылки на карточки."""
from pathlib import Path
import shutil
import subprocess
import unittest

from itd.field_ui import describe_fields, human_label, input_type


class ActInputTests(unittest.TestCase):
    def test_role_labels_and_unambiguous_legacy_types(self):
        self.assertEqual(human_label({'key':'customer_name','label':'customer: наименование'}), 'Заказчик: наименование')
        self.assertEqual(human_label({'label':'builder_org: ИНН'}), 'Лицо, осуществляющее строительство: ИНН')
        self.assertEqual(input_type({'label':'Количество листов, раздел 1'}), 'number')
        self.assertEqual(input_type({'label':'дата прибытия на площадку'}), 'date')
        self.assertEqual(input_type({'label':'заводской номер , дата выпуска'}), 'text')
        self.assertEqual(input_type({'label':'Количество и наименование оборудования'}), 'text')
        original=[{'key':'amount','kind':'literal','value_type':'number','label':'Количество'}]
        self.assertEqual(describe_fields(original)[0]['input_type'], 'number')
        self.assertNotIn('input_type',original[0])

    def test_labels_remove_parentheses_and_capitalize_without_changing_acronyms(self):
        self.assertEqual(human_label({'label':'(наименование генподрядчика)'}),'Наименование генподрядчика')
        self.assertEqual(human_label({'label':'представитель (должность, Ф.И.О.)'}),'Представитель должность, Ф.И.О.')
        self.assertEqual(human_label({'label':'1. количество (шт.)'}),'1. Количество шт.')
        self.assertEqual(human_label({'label':'заказчик: ИНН'}),'Заказчик: ИНН')
        self.assertEqual(input_type({'label':'наименование фирмы, дата'}),'text')
        self.assertEqual(input_type({'label':'будет поставлено заказчиком (дата)'}),'date')

    @unittest.skipUnless(shutil.which('node'), 'Нужен Node')
    def test_form_render_types_serialization_and_live_sources(self):
        source=(Path(__file__).parents[1]/'itd/web_assets/act-fields.js').read_text()
        versions=(Path(__file__).parents[1]/'itd/web_assets/document-versions.js').read_text()
        table_functions=versions[versions.index('function versionTableColumns('):versions.index('async function downloadDocumentVersion(')]+versions[versions.index('function versionTables('):]
        script=r'''
const assert=require('node:assert/strict');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let html='',signed='2026-10-31';
const host={set innerHTML(v){html=v;}};
const $=s=>s==='#act-fields'?host:s.includes('date_signed')?{value:signed}:null;
const cleanFieldLabel=v=>String(v??'').replace(/[()]/g,'').trim();
const meta={document_roles:{customer:'Заказчик'}};
const definitions=[
 {key:'copies_count',kind:'literal',label:'Количество экземпляров',input_type:'number',value_type:'number',required:true},
 {key:'work_start',kind:'literal',label:'Начало работ',input_type:'date',value_type:'date',format:'date_ru'},
 {key:'customer_name',kind:'reference',label:'Заказчик: наименование',source:'organizations.customer.full_name'},
 {key:'day',kind:'reference',label:'День подписания',source:'act.date_signed',format:'day_2digits'}
];
const def={code:'TEST',fields:definitions,ui_fields:definitions};
TABLE_FUNCTIONS
const decorateSelects=()=>{};
const pdata={form_roots:{object:{},project:{},organizations:{customer:{full_name:'<Заказчик>'}}},resources:[],schemes:[],
 workspace_entries:[{id:7,resource_id:12},{id:8,resource_id:null}],workflow:{fact_records:[{id:4,resource_id:13}]}};
const actForms=()=>[def];
SOURCE
renderActFields('TEST');
assert.ok(html.includes('type="number"'));
assert.ok(html.includes('type="date"'));
assert.ok(!html.includes('Из БД:'));
assert.ok(!html.includes('act.date_signed'));
assert.ok(html.includes('&lt;Заказчик&gt;'));
assert.ok(!html.includes('data-act-field="customer_name"'));
assert.equal(actAutomaticValue(definitions[3],actInputRoots()),'31');
signed='2026-11-02';
assert.equal(actAutomaticValue(definitions[3],actInputRoots()),'02');
assert.equal(actAutomaticValue({kind:'reference',source:'object.name'},{}),'Не заполнено — уточните исходные сведения');
const fakeForm={querySelectorAll:selector=>selector==='[data-version-table]'?[]:[{dataset:{actField:'copies_count'},value:'0'},{dataset:{actField:'work_start'},value:'2026-10-30'}]};
const fields=collectActFields(fakeForm,def);
assert.equal(fields[0].value,0);
assert.equal(typeof fields[0].value,'number');
assert.equal(fields[1].value,'2026-10-30');
assert.equal(fields[1].format,'date_ru');
assert.deepEqual([...linkedActResourceIds([7,8],[4])],[12,13]);
definitions.push({key:'readings',label:'Измерения',kind:'table',value:null,fields:[
 {key:'pressure',label:'Давление',kind:'reference',source:'item.pressure',input_type:'number'},
 {key:'note',label:'Примечание',kind:'reference',source:'item.note'}]});
renderActFields('TEST');
assert.match(html,/data-version-table="readings"/);
assert.match(html,/Добавить строку/);
const row={querySelectorAll:()=>[
 {dataset:{tableColumn:'pressure'},type:'number',value:'0'},
 {dataset:{tableColumn:'note'},type:'text',value:'<Проверено>'}]};
const table={dataset:{versionTable:'readings'},querySelectorAll:()=>[row]};
const creationForm={querySelectorAll:selector=>selector==='[data-version-table]'?[table]:[]};
const saved=collectActFields(creationForm,def);
assert.equal(saved[0].value[0].pressure,0);
assert.equal(saved[0].value[0].note,'<Проверено>');
assert.ok(!('source' in saved[0]));
const rendered=versionTables(saved,{},false);
assert.match(rendered,/value="0"/);
assert.match(rendered,/&lt;Проверено&gt;/);
const automatic={...saved[0],source:'resources'};delete automatic.value;
assert.equal(versionTables([automatic],{},false),'');
'''.replace('SOURCE',source).replace('TABLE_FUNCTIONS',table_functions)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
