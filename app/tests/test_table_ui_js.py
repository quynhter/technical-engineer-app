"""Типы ячеек, пустые строки и доступ к действиям через карточку."""
from pathlib import Path
import shutil
import subprocess
import unittest

ASSETS=Path(__file__).parents[1]/'itd/web_assets'

@unittest.skipUnless(shutil.which('node'),'Нужен Node')
class TableUiJsTests(unittest.TestCase):
    def run_js(self,script):
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_filler_is_idempotent_and_empty_row_spans_all_columns(self):
        source=(ASSETS/'ui.js').read_text()
        funcs=source[source.index('function addTableFiller('):source.index('function decorateDataTables(')]
        self.run_js(r'''
const assert=require('node:assert/strict');
function cell(span=1,empty=false){return {colSpan:span,dataset:{},classList:{contains:c=>empty&&c==='empty'},setAttribute(){},remove(){this.owner.cells.splice(this.owner.cells.indexOf(this),1)}};}
function row(cells){const r={cells,append(c){c.owner=r;cells.push(c)}};cells.forEach(c=>c.owner=r);return r;}
const document={createElement:()=>cell()};
const header=row([cell(),cell()]),normal=row([cell(),cell()]),empty=row([cell(2,true)]),group=row([cell(2)]);
const table={tHead:{rows:[header]},tBodies:[{rows:[normal,empty,group]}],querySelectorAll:()=>[header,normal,empty,group].flatMap(r=>r.cells).filter(c=>'tableFill' in c.dataset)};
FUNCTIONS
for(let i=0;i<3;i++){
 addTableFiller(table);assert.equal(header.cells.length,3);assert.equal(normal.cells.length,3);
 assert.equal(empty.cells.length,1);assert.equal(empty.cells[0].colSpan,3);assert.equal(group.cells[0].colSpan,3);
}
// A fresh body after filtering still uses the original data-column count.
const fresh=row([cell(2,true)]);table.tBodies[0].rows=[fresh];addTableFiller(table);assert.equal(fresh.cells[0].colSpan,3);
'''.replace('FUNCTIONS',funcs))

    def test_empty_and_group_cells_never_receive_truncation(self):
        source=(ASSETS/'ui.js').read_text()
        funcs=source[source.index('function tableCellLabels('):source.index('let smartSequence=')]
        self.run_js(r'''
const assert=require('node:assert/strict');let touched=0;
const empty={colSpan:1,matches:()=>true},group={colSpan:5,matches:()=>false};
const table={querySelectorAll:()=>[empty,group]};
const middleLabel=()=>touched++;
FUNCTIONS
tableCellLabels(table);assert.equal(touched,0);
'''.replace('FUNCTIONS',funcs))

    def test_numbers_dates_and_column_types_have_consistent_display(self):
        source=(ASSETS/'ui.js').read_text()
        funcs=source[source.index('function displayTableDate('):source.index('function addTableFiller(')]
        self.run_js(funcs+r'''
const assert=require('node:assert/strict');
assert.equal(displayTableDate('2026-11-03'),'03.11.2026');
assert.equal(formatTableNumber(12.34567),'12,346');assert.equal(formatTableNumber(12),'12');
assert.equal(formatTableNumber(0),'0');assert.equal(formatTableNumber(null),null);
assert.equal(tableColumnType('Смонтировано'),'number');assert.equal(tableColumnType('Дата подписания'),'date');
assert.equal(tableColumnType('Наименование'),'text');assert.equal(tableColumnType('Выбор'),'check');
''')

    def test_duplicate_is_in_work_card_and_source_actions_are_in_file_card(self):
        app=(ASSETS/'app.js').read_text();ojr=(ASSETS/'ojr-ui.js').read_text()
        body=app[app.index('function entryBody('):app.index('function input(')]
        self.assertNotIn('data-copy-entry',body);self.assertNotIn('<th>Действия',body)
        self.assertIn('data-copy-entry="${e.id}"',ojr[ojr.index('function workEntryEditor('):ojr.index('function actRoles(')])
        source=app[app.index('function sourceFilesPage('):app.index('function openSourceFileCard(')]
        self.assertIn('data-file-card',source);self.assertNotIn('data-file-delete',source)
        card=app[app.index('function openSourceFileCard('):app.index('let filePlan=')]
        self.assertIn('data-file-delete',card);self.assertIn('data-original',card)
        journals=app[app.index('function journalsPage('):app.index('function resourceSelect(')]
        self.assertNotIn('specialRegistryPage()',journals)

    def test_shared_table_includes_filler_before_dom_observers_run(self):
        source=(ASSETS/'journals.js').read_text()
        function=source[source.index('function journalTable('):source.index('function journalValue(')]
        self.run_js(r'''
const assert=require('node:assert/strict'),esc=String;
FUNCTION
const filled=journalTable(['Название','Статус'],[['Документ','Черновик'],['Другой','Готов']]);
assert.equal((filled.match(/<th class="table-fill" data-table-fill/g)||[]).length,1);
assert.equal((filled.match(/<td class="table-fill" data-table-fill/g)||[]).length,2);
const empty=journalTable(['Название','Статус'],[]);
assert.match(empty,/colspan="3" class="empty"/);
assert.equal((empty.match(/data-table-fill/g)||[]).length,1);
'''.replace('FUNCTION',function))

    def test_sorting_keeps_date_groups_and_preferences_survive_reload(self):
        source=(ASSETS/'tables.js').read_text()
        helpers=source[source.index('const tablePreferenceKey'):source.index('function enhanceDataTable(')]
        apply=source[source.index('function applyDataTable('):]
        ui=(ASSETS/'ui.js').read_text()
        column=ui[ui.index('function tableColumnType('):ui.index('function addTableFiller(')]
        self.run_js(column+helpers+apply+r'''
const assert=require('node:assert/strict');
const stored={};
globalThis.localStorage={getItem:k=>k in stored?stored[k]:null,setItem:(k,v)=>{stored[k]=String(v);}};
const cell=text=>({textContent:text,dataset:{},cloneNode(){return {textContent:text,querySelectorAll:()=>[]};}});
const row=(texts,group=false)=>({cells:texts.map(cell),hidden:false,classList:{contains:c=>group&&c==='date-group'},querySelector:()=>null});
const header=text=>({textContent:text,setAttribute(){}});
const control={textContent:'',disabled:false,value:'',dispatchEvent(){}};
const body={rows:[],append(...nodes){this.rows=[...this.rows.filter(r=>!nodes.includes(r)),...nodes];},querySelector:()=>null};
const headers=[header('Наименование'),header('Количество')];
const table={tHead:{rows:[{cells:headers}]},tBodies:[body],classList:{toggle(){}}};
const h1=row([],true),a1=row(['Кабель 10','5']),a2=row(['Кабель 2','20']),h2=row([],true),b1=row(['Кабель 1','3']);
const names=new Map([[h1,'H1'],[h2,'H2']]);const label=r=>names.get(r)??r.cells[0].textContent;
body.rows=[h1,a1,a2,h2,b1];
const model={key:'k',prefs:{query:'',sort:1,direction:-1,page:0,size:50,compact:false,filters:{},dates:{}},controls:{querySelector:()=>control},headers,rows:[h1,a1,a2,h2,b1],values:new WeakMap()};
applyDataTable(table,model);
assert.deepEqual(model.rows.map(label),['H1','Кабель 2','Кабель 10','H2','Кабель 1']);
assert.deepEqual(body.rows.map(label),['H1','Кабель 2','Кабель 10','H2','Кабель 1']);
model.prefs.sort=-1;model.prefs.direction=1;model.prefs.query='кабель 2';
applyDataTable(table,model);
assert.deepEqual(model.rows.map(label),['H1','Кабель 2','Кабель 10','H2','Кабель 1']);
assert.equal(h1.hidden,false);assert.equal(a2.hidden,false);assert.equal(a1.hidden,true);assert.equal(h2.hidden,true);assert.equal(b1.hidden,true);
model.prefs.query='';model.prefs.sort=1;model.prefs.direction=-1;model.prefs.size=25;model.prefs.compact=true;
rememberDataTable(model);
const saved=savedTablePreferences('k',2);
assert.deepEqual(saved,{sort:1,direction:-1,size:25,compact:true,hiddenColumns:[],widths:{}});
assert.equal(savedTablePreferences('k',1).sort,-1);
assert.equal(savedTablePreferences('missing',2).size,50);
model.prefs.hiddenColumns=[0];model.prefs.widths={0:360};rememberDataTable(model);
assert.deepEqual(savedTablePreferences('k',2).widths,{0:360});
assert.deepEqual(savedTablePreferences('k',2).hiddenColumns,[0]);
assert.deepEqual(normalizeHiddenTableColumns([0,0,-1,8,'1'],2),[0]);
assert.deepEqual(normalizeHiddenTableColumns([0,1],2),[0]);
assert.deepEqual(normalizeHiddenTableColumns(null,2),[]);
stored[tablePreferenceKey]='[1,2]';assert.equal(savedTablePreferences('k',2).size,50);
for(let i=0;i<120;i++){model.key='key'+i;rememberDataTable(model);}
assert.ok(Object.keys(JSON.parse(stored[tablePreferenceKey])).length<=100);
''')

    def test_column_widths_use_css_properties_and_reuse_columns(self):
        source=(ASSETS/'tables.js').read_text()
        helper=source[source.index('function applyTableWidths('):source.index('function enhanceTableResize(')]
        self.run_js(r'''
const assert=require('node:assert/strict');
const document={createElement:()=>({style:{}})};
const group={children:[],replaceChildren(...cols){this.children=cols;},set innerHTML(_){throw Error('Inline style markup is blocked by CSP');}};
const header=()=>({hidden:false,querySelector:()=>null});
const headers=[header(),header(),header()];
const span={cells:[{colSpan:4}]};
const props={};
const table={querySelector:()=>group,tBodies:[{rows:[span]}],style:{setProperty:(k,v)=>props[k]=v},classList:{add(){}}};
const defaultTableWidth=()=>200;
const model={headers,prefs:{widths:{0:120,1:320,2:144}}};
FUNCTION
applyTableWidths(table,model);
assert.deepEqual(group.children.map(c=>c.style.width),['120px','320px','144px',undefined]);
const columns=[...group.children];
model.prefs.widths[1]=420;applyTableWidths(table,model);
assert.deepEqual(group.children,columns);
assert.deepEqual(group.children.map(c=>c.style.width),['120px','420px','144px',undefined]);
assert.equal(props['--table-width'],'716px');
headers[0].hidden=true;applyTableWidths(table,model);
assert.deepEqual(group.children.map(c=>c.style.width),['420px','144px',undefined]);
assert.equal(span.cells[0].colSpan,3);
'''.replace('FUNCTION',helper))

    def test_date_filters_exist_without_rows_and_totals_keep_units_separate(self):
        source=(ASSETS/'tables.js').read_text()
        helper=source[source.index('function tableFilterColumns('):source.index('function tableCsvValue(')]
        ui=(ASSETS/'ui.js').read_text()
        types=ui[ui.index('function displayTableDate('):ui.index('function addTableFiller(')]
        self.run_js(types+helper+r'''
const assert=require('node:assert/strict'),tableCollator=new Intl.Collator('ru');
const rowTexts=(model,row)=>row;
const tableLabel=(headers,i)=>headers[i].textContent;
const parseTableNumber=s=>Number.isFinite(Number(s))&&s!==''?Number(s):null;
const header=text=>({textContent:text,querySelector:()=>null});
const model={headers:[header('Дата'),header('Количество'),header('Ед. изм.')],totalBox:{textContent:''}};
assert.deepEqual(tableFilterColumns(model,[]),[{index:0,kind:'date'}]);
renderTableTotals(model,[['01.11.2026','10','м'],['02.11.2026','2','шт'],['03.11.2026','5','м']]);
assert.match(model.totalBox.textContent,/Количество: 15 м/);
assert.match(model.totalBox.textContent,/Количество: 2 шт/);
assert.doesNotMatch(model.totalBox.textContent,/17/);
// Native filter controls retain their values/listeners when rows are rebuilt.
const native={nativeFields:true,fieldBox:{innerHTML:'unchanged'},prefs:{filters:{},dates:{}}};
buildTableFilters(native);assert.equal(native.fieldBox.innerHTML,'unchanged');
''')

    def test_page_window_and_saved_width_validation(self):
        source=(ASSETS/'tables.js').read_text()
        helpers=source[source.index('function normalizeTableWidths('):source.index('function renderTablePages(')]
        self.run_js(helpers+r'''
const assert=require('node:assert/strict');
assert.deepEqual(tablePageNumbers(1,1),[1]);
assert.deepEqual(tablePageNumbers(1,10),[1,2,null,10]);
assert.deepEqual(tablePageNumbers(5,10),[1,null,4,5,6,null,10]);
assert.deepEqual(tablePageNumbers(10,10),[1,null,9,10]);
for(let pages=1;pages<100;pages++)for(let page=1;page<=pages;page++){
 const items=tablePageNumbers(page,pages),numbers=items.filter(n=>n!==null);
 assert.ok(numbers.includes(page)&&numbers.includes(1)&&numbers.includes(pages));
 assert.equal(new Set(numbers).size,numbers.length);assert.ok(items.length<=9);
}
assert.deepEqual(normalizeTableWidths({'0':320,'1':79,'2':901,'3':'200','4':140.4,'5':NaN,'6':Infinity,'9':200,'-1':200},7),{'0':320,'4':140});
assert.deepEqual(normalizeTableWidths(null,2),{});assert.deepEqual(normalizeTableWidths([200],2),{});
''')

    def test_hidden_columns_preserve_selection_and_move_sticky_column(self):
        source=(ASSETS/'tables.js').read_text()
        helpers=source[source.index('function applyTableColumns('):source.index('function openTableSettings(')]
        self.run_js(r'''
const assert=require('node:assert/strict');
const tableColumnType=()=> 'text';
function cell(text,check=false,span=1){return {textContent:text,colSpan:span,hidden:false,sticky:false,
 querySelector:()=>check?{}:null,classList:{toggle(name,value){if(name==='sticky-name')this.owner.sticky=value;}}};}
const bind=c=>{c.classList.owner=c;return c;};
const headers=[bind(cell('Выбор',true)),bind(cell('Наименование')),bind(cell('Статус'))];
const data={cells:[bind(cell('')),bind(cell('Кабель')),bind(cell('Готов'))]};
const group={cells:[bind(cell('Ноябрь',false,4))]};
const model={headers,rows:[group,data],prefs:{hiddenColumns:[0,1]}};
FUNCTIONS
applyTableColumns({},model);
assert.equal(headers[0].hidden,false);assert.equal(headers[1].hidden,true);assert.equal(data.cells[1].hidden,true);
assert.equal(headers[2].sticky,true);assert.equal(data.cells[2].sticky,true);assert.equal(group.cells[0].hidden,false);
model.prefs.hiddenColumns=[];applyTableColumns({},model);
assert.equal(headers[1].hidden,false);assert.equal(data.cells[1].hidden,false);
assert.equal(headers[1].sticky,true);assert.equal(headers[2].sticky,false);
'''.replace('FUNCTIONS',helpers))

    def test_column_filters_totals_selection_and_csv_export(self):
        tables=(ASSETS/'tables.js').read_text()
        ui=(ASSETS/'ui.js').read_text()
        helpers=ui[ui.index('function displayTableDate('):ui.index('function addTableFiller(')]
        self.run_js(helpers+tables+r'''
const assert=require('node:assert/strict');
const esc=s=>String(s);
const stored={};globalThis.localStorage={getItem:k=>k in stored?stored[k]:null,setItem:(k,v)=>{stored[k]=String(v);}};
const cell=text=>({textContent:text,dataset:{},cloneNode(){return {textContent:text,querySelectorAll:()=>[]};}});
const row=(texts,id)=>({cells:texts.map(cell),hidden:false,dataset:{rowId:id},classList:{contains:()=>false},querySelector:()=>null});
const header=text=>({textContent:text,setAttribute(){},querySelector:()=>null});
const control={textContent:'',disabled:false,value:'',dispatchEvent(){}};
const body={rows:[],append(...nodes){this.rows=[...this.rows.filter(r=>!nodes.includes(r)),...nodes];},querySelector:()=>null};
const headers=[header('Статус'),header('Дата'),header('Количество'),header('Наименование')];
const r1=row(['Подписан','05.01.2026','10','Кабель "А"'],'1'),r2=row(['Черновик','10.02.2026','2,5','Кабель Б'],'2'),r3=row(['Подписан','20.03.2026','1','Кабель В'],'3');
body.rows=[r1,r2,r3];
const table={tHead:{rows:[{cells:headers}]},tBodies:[body],classList:{toggle(){}},querySelector:()=>null,hasAttribute:()=>true};
const model={key:'k',selectable:true,selected:new Set(),controls:{querySelector:()=>control},headers,rows:[r1,r2,r3],values:new WeakMap(),matched:[],
 prefs:{query:'',sort:-1,direction:1,page:0,size:50,compact:false,filters:{},dates:{}}};
model.filterable=tableFilterColumns(model,[r1,r2,r3]);
assert.deepEqual(model.filterable.map(c=>[c.index,c.kind]),[[0,'select'],[1,'date']]);
model.prefs.filters={0:'Подписан'};applyDataTable(table,model);
assert.deepEqual(model.matched,[r1,r3]);assert.equal(r2.hidden,true);
model.totalBox={textContent:''};applyDataTable(table,model);
assert.match(model.totalBox.textContent,/Количество: 11/);
assert.equal(r1.cells[3].dataset.label,'Наименование');
model.prefs.dates={1:{from:'2026-03-01'}};applyDataTable(table,model);
assert.deepEqual(model.matched,[r3]);
model.chipBox={innerHTML:''};applyDataTable(table,model);
assert.match(model.chipBox.innerHTML,/data-chip="date:1"/);
model.prefs.filters={};model.prefs.dates={};applyDataTable(table,model);
handleRowSelection(table,model,{target:{dataset:{},checked:true,hasAttribute:n=>n==='data-select-visible'}});
assert.deepEqual([...model.selected].sort(),['1','2','3']);
let captured=null;
globalThis.URL={createObjectURL:b=>{captured=b;return 'blob:x';},revokeObjectURL(){}};
globalThis.document={createElement:()=>({click(){}})};
(async()=>{
 downloadTableCsv(table,model,[r1,r2],'Отчёт');
 assert.deepEqual([...new Uint8Array(await captured.slice(0,3).arrayBuffer())],[0xEF,0xBB,0xBF]);
 const lines=(await captured.text()).split('\r\n');
 assert.equal(lines[0],'"Статус";"Дата";"Количество";"Наименование"');
 assert.equal(lines[1],'"Подписан";"05.01.2026";"10";"Кабель ""А"""');
})().catch(e=>{console.error(e);process.exit(1);});
''')
