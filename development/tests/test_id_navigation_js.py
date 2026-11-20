"""Общий контекст ИД и независимые столбцы связей/действий."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ASSETS=Path(__file__).parents[2]/'app/itd/web_assets'

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
assert.match(html,/id="documents-app"/); // Buttons/data now belong to the API-backed Astryx component.
assert.doesNotMatch(html,/class="table-total"/); // The shared footer owns the record count.
assert.doesNotMatch(html,/Файлы документов|Исходные файлы|Ведомость|Скачать ZIP|Проверка|Сдача/);
packagePanel='check';assert.doesNotMatch(packagePage(),/data-editor="act"/);
'''.replace('FUNCTIONS',functions))

    def test_installed_count_uses_one_source_and_preserves_unknown_zero(self):
        module=(ASSETS.parents[2]/'app/frontend/src/table-values.js').resolve().as_uri()
        self.run_js('import('+json.dumps(module)+').then(({installedValue})=>{'+r"""
const assert=require('node:assert/strict');
const summary={confirmed_ids:[1,2],confirmed_total:8};
assert.equal(installedValue({qty_fact:10,consumed:8},summary).value,10);
assert.equal(installedValue({qty_fact:0},summary).value,0);
assert.equal(installedValue({qty_fact:null},summary).value,8);
assert.equal(installedValue({qty_fact:null},{confirmed_ids:[],confirmed_total:null}).value,null);
assert.equal(installedValue({qty_fact:null},{confirmed_ids:[1],confirmed_total:null}).value,null);
"""+'});')

    def test_ojr_title_uses_all_assigned_roles_and_follows_object_card(self):
        module=(ASSETS.parents[2]/'app/frontend/src/journal-model.mjs').resolve().as_uri()
        self.run_js('import('+json.dumps(module)+').then(({journalBlocks})=>{'+r"""
const assert=require('node:assert/strict');
const project={journals:{object:{name:'Сведения об объекте'},title_assignments:[
 {role_key:'builder',organization:{full_name:'Организация подрядчика'},person:{fio:'Иванов',position:'Инженер'}},
 {role_key:'builder',organization:{full_name:'Организация подрядчика'},person:{fio:'Петров',position:'Инженер'}},
 {role_key:'foreman',organization:{full_name:'Организация монтажника'},person:{fio:'Сидоров',position:'Прораб'},section_code:'ЭОМ'}]}};
const blocks=journalBlocks(project,'0',{document_roles:{builder:'Подрядчик',foreman:'Производитель работ'}});
assert.equal(blocks[0].title,'Сведения об объекте');assert.equal(blocks[1].title,'Уполномоченные представители');
const text=JSON.stringify(blocks);for(const value of ['Подрядчик','Иванов','Петров','Производитель работ','Организация монтажника','Раздел ЭОМ'])assert.ok(text.includes(value));
"""+'});')

    def test_resource_and_ojr_deep_links_share_one_id_context(self):
        source=(ASSETS/'app.js').read_text()
        constants='\n'.join(line for line in source.splitlines() if line.startswith(('const idViews=','const tabs=','const journalViews=')))
        navigate=source[source.index('function navigate('):source.index('function render(')]
        page=source[source.index('function projectGuard('):source.index('function actName(')]
        self.run_js(r'''
const assert=require('node:assert/strict');
let workspaceView,step,tab,editEntry,journalSection,packagePanel,resourcePanel;
const state={object:{id:1},projects:[]},pdata={};
const location={href:'http://127.0.0.1/?view=overview'},history={replaceState(){}};
const window={scrollTo(){}},notice=()=>{},render=()=>{},refreshJournals=()=>{};
const title=name=>'<h1>'+name+'</h1>',projectSelector=()=>'<select id="project-select"></select>',icon=()=>'',card=()=>'';
const packagePage=()=>'',workPage=()=>'',incomingPage=()=>'',journalsPage=()=>'<nav>Разделы ОЖР</nav>',schemesPage=()=>'<section>SCHEMES CONTENT</section>',factsPage=()=>'',checkPage=()=>'';
const resourcePage=()=>'<section>RESOURCE CONTENT</section>',ojrPage=()=>'<nav aria-label="Разделы ОЖР">Титульный лист / Раздел 1</nav>';
CONSTANTS
NAVIGATE
PAGE
for(const [view,marker] of [['resources','RESOURCE CONTENT'],['schemes','schemes-app']]){
 navigate(view);assert.equal(step,3,'Вкладка должна оставаться внутри ИД');
 assert.equal(idViews[tab],view);const html=idPage();assert.ok(html.includes(marker));
 assert.equal((html.match(/id="project-select"/g)||[]).length,0);
 assert.equal((html.match(/<h1>/g)||[]).length,1);
 assert.ok(html.includes('Исполнительная документация'));
}
assert.deepEqual(tabs,['Комплект ИД','Ресурсы','Схемы']);
navigate('ojr');assert.equal(step,3);assert.ok(journalViews.includes(workspaceView));
const journalHtml=idPage();assert.ok(journalHtml.includes('Разделы ОЖР'));assert.ok(journalHtml.includes('Журналы'));
assert.equal((journalHtml.match(/<h1>/g)||[]).length,1);assert.equal(journalHtml.includes('Исполнительная документация'),false);
navigate('work');assert.equal(journalSection,'3');assert.ok(journalViews.includes(workspaceView));
navigate('facts');assert.equal(idViews[tab],'resources');
navigate('check');assert.equal(idViews[tab],'documents');assert.equal(packagePanel,'check');
navigate('delivery');assert.equal(idViews[tab],'documents');assert.equal(packagePanel,'delivery');
navigate('incoming');assert.equal(idViews[tab],'resources');assert.equal(resourcePanel,'incoming');
const disclosure={open:false},document={querySelector:()=>disclosure};
navigate('permits');assert.equal(workspaceView,'object');assert.equal(step,0);assert.equal(disclosure.open,true);
'''.replace('CONSTANTS',constants).replace('NAVIGATE',navigate).replace('PAGE',page))

    def test_ojr_work_section_uses_the_project_work_editor(self):
        source=(ASSETS/'ojr-ui.js').read_text()
        functions=source[source.index('function ojrPage('):source.index('function journalTool(')]
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
        source=(ASSETS.parents[2]/'app/frontend/src/work-records.jsx').read_text()
        self.assertIn('perform(onOpen,entry,project)',source)
        self.assertIn('perform(onActPreview,entry.act_id)',source)
        self.assertNotIn('Дублировать',source)
        module=(ASSETS.parents[2]/'app/frontend/src/work-table.mjs').resolve().as_uri()
        self.run_js('import('+json.dumps(module)+').then(({workLabels,workSources,workValues})=>{'+r"""
const assert=require('node:assert/strict');
const entry={id:7,entry_date:'2026-11-02',title:'Монтаж',act_id:3,attachment_id:9};
const project={acts:[{id:3,act_num:'А-03'}],attachments:[{id:9,title:'Основание'}]};
assert.deepEqual(workLabels.slice(1,3),['Наименование работы','Описание']);assert.deepEqual(workLabels.slice(8),['Акт','Источник']);
assert.deepEqual(workSources(entry,project),{act:'А-03',attachment:'Основание'});
assert.deepEqual(workValues(entry,project).slice(8),['А-03','Основание']);
"""+'});')

if __name__=='__main__':unittest.main()
