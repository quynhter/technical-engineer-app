"""Общий контекст ИД и независимые столбцы связей/действий."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ASSETS=Path(__file__).parents[1]/'itd/web_assets'

@unittest.skipUnless(shutil.which('node'),'Нужен Node')
class IdNavigationTests(unittest.TestCase):
    def run_js(self,script):
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_main_documents_only_shows_the_act_list(self):
        source=(ASSETS/'app.js').read_text()
        functions=source[source.index('function actName('):source.index('function workPage(')]
        self.run_js(r'''
const assert=require('node:assert/strict');
const esc=v=>String(v??''),icon=()=>'',formatDateTime=v=>v,checkPage=()=>'',uploadZone=()=>'',journalTable=(headers,rows)=>headers.join('|')+rows.flat().join('|'),option=(v,t)=>'<option>'+t+'</option>';
const workspaceView='documents';let packagePanel='documents';
const card=(title,body)=>'<section><h2>'+title+'</h2>'+body+'</section>';
const pdata={check:{findings:[]},acts:[],attachments:[],releases:[{id:7,title:'Ведомость',kind:'xlsx',selected:true,created_at:'2026-11-02'}]};
FUNCTIONS
const html=packagePage();
assert.match(html,/<h2>Основные документы<\/h2>/);
for(const label of ['Основные документы','Реестр ИД','Создать','Загрузить'])assert.ok(html.includes(label));
assert.doesNotMatch(html,/class="table-total"/); // The shared footer owns the record count.
assert.doesNotMatch(html,/Файлы документов|Исходные файлы|Ведомость|Скачать ZIP|Проверка|Сдача/);
packagePanel='check';assert.doesNotMatch(packagePage(),/data-editor="act"/);
'''.replace('FUNCTIONS',functions))

    def test_installed_count_uses_one_source_and_preserves_unknown_zero(self):
        source=(ASSETS/'resources.js').read_text()
        function=source[source.index('function installedValue('):source.index('function resourcePage(')]
        self.run_js(function+r"""
const assert=require('node:assert/strict');
const summary={confirmed_ids:[1,2],confirmed_total:8};
assert.equal(installedValue({qty_fact:10,consumed:8},summary).value,10);
assert.equal(installedValue({qty_fact:0},summary).value,0);
assert.equal(installedValue({qty_fact:null},summary).value,8);
assert.equal(installedValue({qty_fact:null},{confirmed_ids:[],confirmed_total:null}).value,null);
assert.equal(installedValue({qty_fact:null},{confirmed_ids:[1],confirmed_total:null}).value,null);
""")

    def test_ojr_title_uses_all_assigned_roles_and_follows_object_card(self):
        source=(ASSETS/'ojr-ui.js').read_text()
        functions=source[source.index('function ojrPage('):source.index('function responsibleSelect(')]
        self.run_js(r'''
const assert=require('node:assert/strict');
const esc=v=>String(v??''),journalValue=esc,card=(t,b)=>t+b, journalTable=(h,rows)=>rows.flat().join('|');
const meta={document_roles:{builder:'Подрядчик',general_contractor:'Генподрядчик',foreman:'Производитель работ'}};
let journalSection='0';
const pdata={journals:{section_names:{},legacy:[],title_assignments:[
 {role_key:'builder',organization:{full_name:'Организация подрядчика'},person:{fio:'Иванов',position:'Инженер'}},
 {role_key:'builder',organization:{full_name:'Организация подрядчика'},person:{fio:'Петров',position:'Инженер'}},
 {role_key:'foreman',organization:{full_name:'Организация монтажника'},person:{fio:'Сидоров',position:'Прораб'},section_code:'ЭОМ'}]}};
const generalJournalPage=()=>'Сведения об объекте'+titleAssignmentsEditor(),specialRegistryPage=()=>'';
FUNCTIONS
const html=ojrPage();
assert.ok(html.indexOf('Сведения об объекте')<html.indexOf('Уполномоченные представители'));
for(const text of ['Подрядчик','Иванов','Петров','Производитель работ','Организация монтажника','Раздел ЭОМ'])assert.ok(html.includes(text));
assert.doesNotMatch(html,/<form|<select/);
'''.replace('FUNCTIONS',functions))

    def test_resource_and_ojr_deep_links_share_one_id_context(self):
        source=(ASSETS/'app.js').read_text()
        constants='\n'.join(line for line in source.splitlines() if line.startswith(('const idViews=','const tabs=')))
        navigate=source[source.index('function navigate('):source.index('function render(')]
        page=source[source.index('function idPage('):source.index('function actName(')]
        self.run_js(r'''
const assert=require('node:assert/strict');
let workspaceView,step,tab,editEntry,journalSection,packagePanel,resourcePanel;
const state={object:{id:1},projects:[]},pdata={};
const location={href:'http://127.0.0.1/?view=overview'},history={replaceState(){}};
const window={scrollTo(){}},closeAgentHelp=()=>{},notice=()=>{},render=()=>{},refreshJournals=()=>{};
const title=name=>'<h1>'+name+'</h1>',projectSelector=()=>'<select id="project-select"></select>',icon=()=>'',card=()=>'';
const packagePage=()=>'',workPage=()=>'',incomingPage=()=>'',journalsPage=()=>'<nav>Разделы ОЖР</nav>',schemesPage=()=>'<section>SCHEMES CONTENT</section>',factsPage=()=>'',checkPage=()=>'';
const resourcePage=()=>'<section>RESOURCE CONTENT</section>',ojrPage=()=>'<nav aria-label="Разделы ОЖР">Титульный лист / Раздел 1</nav>';
CONSTANTS
NAVIGATE
PAGE
for(const [view,marker] of [['resources','RESOURCE CONTENT'],['ojr','Разделы ОЖР'],['schemes','SCHEMES CONTENT']]){
 navigate(view);assert.equal(step,3,'Вкладка должна оставаться внутри ИД');
 assert.equal(idViews[tab],view);const html=idPage();assert.ok(html.includes(marker));
 assert.equal((html.match(/id="project-select"/g)||[]).length,1);
 assert.equal((html.match(/<h1>/g)||[]).length,1);
 assert.ok(html.includes('Исполнительная документация'));
}
assert.deepEqual(tabs,['Комплект ИД','Ресурсы','Схемы','Журналы']);
navigate('work');assert.equal(idViews[tab],'ojr');assert.equal(journalSection,'3');
navigate('facts');assert.equal(idViews[tab],'resources');
navigate('check');assert.equal(idViews[tab],'documents');assert.equal(packagePanel,'check');
navigate('delivery');assert.equal(idViews[tab],'documents');assert.equal(packagePanel,'delivery');
navigate('incoming');assert.equal(idViews[tab],'resources');assert.equal(resourcePanel,'incoming');
'''.replace('CONSTANTS',constants).replace('NAVIGATE',navigate).replace('PAGE',page))

    def test_ojr_work_section_uses_the_project_work_editor(self):
        source=(ASSETS/'ojr-ui.js').read_text()
        functions=source[source.index('function ojrPage('):source.index('function titleAssignmentsEditor(')]
        self.run_js(r'''
const assert=require('node:assert/strict'),esc=v=>String(v??'');
const pdata={project:{section_code:'СПС'},journals:{section_names:{'3':'Выполнение работ'}}};
let journalSection='3';
const generalJournalPage=()=>{throw Error('Нельзя показывать общую таблицу всех разделов');};
const workPage=()=>'<button>Сформировать акт</button>SELECTED PROJECT WORK';
FUNCTIONS
const html=ojrPage();assert.match(html,/Работы выбранного раздела: СПС/);
assert.match(html,/SELECTED PROJECT WORK/);assert.match(html,/Сформировать акт/);
'''.replace('FUNCTIONS',functions))

    def test_work_name_opens_card_and_actions_are_not_in_table(self):
        source=(ASSETS/'app.js').read_text()
        functions=source[source.index('function entryBody('):source.index('function input(')]
        self.run_js(r'''
const assert=require('node:assert/strict');
const displayTableDate=v=>v,esc=v=>String(v??''),icon=()=>'',selectedEntries=new Set();
let rows=[{id:7,entry_date:'2026-11-02',title:'Монтаж',act_id:3,attachment_id:9}];
const pdata={workspace_entries:rows,resources:[],work_materials:[],attachments:[{id:9,title:'Основание'}]};
const tableFilters={work:{search:'',group:false,from:'',to:''}},filteredEntries=()=>rows;
FUNCTIONS
const html=entryTable('work');assert.match(html,/<th>Акт и источник<\/th>/);assert.doesNotMatch(html,/<th>Действия|Дублировать|row-menu/);
const cells=entryBody('work').match(/<td\b[^>]*>[\s\S]*?<\/td>/g);
assert.equal(cells.length,7);assert.match(cells[6],/Акт/);assert.match(cells[6],/Источник/);assert.doesNotMatch(cells[6],/data-edit-entry/);
assert.match(cells[2],/data-edit-entry="7"/);
tableFilters.work.group=true;assert.match(entryBody('work'),/colspan="7"/);
rows=[];assert.match(entryBody('work'),/colspan="7"/);
'''.replace('FUNCTIONS',functions))

if __name__=='__main__':unittest.main()
