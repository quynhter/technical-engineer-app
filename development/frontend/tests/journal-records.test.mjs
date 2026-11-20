import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM,VirtualConsole} from '../dependencies.mjs';
import {journalBlocks} from '../../../app/frontend/src/journal-model.mjs';
const bundle=readFileSync(new URL('../../../app/itd/web_assets/design.js',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setTimeout(resolve,20));
async function until(fn){for(let i=0;i<100;i++){if(fn())return;await tick();}assert.ok(fn(),'project records did not settle');}
function setup(theme){
 const errors=[],log=new VirtualConsole();log.on('jsdomError',e=>errors.push(e));log.on('error',e=>errors.push(e));
 const dom=new JSDOM(`<html data-theme="${theme}"><body><div id="content"><div id="records-app"></div></div><div id="command-root"></div></body></html>`,{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:log}),w=dom.window;
 w.CSS={supports:()=>false,escape:String};w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});w.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};w.HTMLElement.prototype.scrollIntoView=function(){};w.eval(bundle);return {dom,w,d:w.document,errors};
}
function button(d,label){return [...d.querySelectorAll('button')].find(b=>b.textContent.trim()===label);}
const project={journals:{object:{name:'Объект',permit_date:'2026-01-01'},construction_dates:{start:'2026-02-01',end:'2026-12-01'},title_assignments:[{record_entity:'sig_assignments',record_id:4,role_key:'builder',person:{fio:'Иванов',position:'Прораб',order_doc:'Приказ 1'},section_code:'ЭОМ'},{record_entity:'sig_assignments',record_id:5,role_key:'builder',person:{fio:'Петров'},section_code:'СПС'}],participants:[{id:1,full_name:'Подрядчик',roles:['builder'],representatives:[{fio:'Иванов',order_doc:'Приказ 1'}]}],section_names:{'1':'Персонал','4':'Строительный контроль','6':'Госстройнадзор'},legacy:[{id:8,kind:'journal',title:'Прежняя запись',section_code:'ЭОМ'}],sections:{'1':[{id:1,kind:'journal',title:'Работник',project_id:2,resolved_fields:{organization:'Подрядчик',person:'Иванов',start_date:'2026-02-01'},responsible_person:{fio:'Петров'}}],'2':[{id:2,kind:'journal',title:'Прежний журнал',work_fields:{issued_date:'2026-01-01'}}],'4':[{id:4,kind:'journal',title:'Проверка',resolved_fields:{defects:'Нет',deadline:'2026-11-19',resolved_date:'2026-11-18',resolved_by:'Иванов'}}],'5':[{id:5,act_num:'А-01',form_name:'Акт',date_signed:'2026-11-18',signed_by:[{fio:'Сидоров',organization:{full_name:'Заказчик'}}]}],'6':[{id:6,kind:'journal',title:'Надзор',resolved_fields:{defects:'Нарушение',resolved_by:'Инспектор'}}]},special:[{id:7,name:'Специальный журнал',issued_date:'2026-01-01',keeper:{fio:'Иванов',order_doc:'Приказ 1'},recipient:{fio:'Петров'},organization:{full_name:'Подрядчик'}}],automatic:[{kind:'ojr',name:'ОЖР',project_id:2,count:0}]}};
test('journal models retain every assigned representative, dates, source records and fixed signatures',()=>{
 const before=JSON.stringify(project),roles={document_roles:{builder:'Подрядчик'}};
 const title=journalBlocks(project,'0',roles);assert.equal(title.length,4);assert.match(title[0].rows[3].values[1],/01.02.2026/);assert.equal(title[1].rows.length,2);assert.equal(title[1].rows[0].values[0],'Подрядчик');assert.match(title[1].rows[0].values[2],/Иванов/);assert.match(title[1].rows[1].values[2],/Петров/);assert.equal(title[1].rows[0].recordId,4);assert.equal(title[3].rows[0].item.id,8);
 const special=journalBlocks(project,'2');assert.equal(special.length,2);assert.match(special[0].rows[0].values[2],/Приказ 1/);assert.match(special[0].rows[0].values[4],/Петров/);
 for(const section of ['1','4','6'])assert.equal(journalBlocks(project,section)[0].rows[0].entity,'workspace_entries');
 const signed=journalBlocks(project,'5')[0];assert.equal(signed.rows[0].entity,'acts');assert.match(signed.rows[0].values[4],/Сидоров. Заказчик/);assert.equal(JSON.stringify(project),before);
});
test('all journal views render common filters/footer, preserve actions and restrict viewer in both themes',async()=>{
 for(const theme of ['light','dark'])for(const role of ['editor','viewer'])for(const section of ['0','1','2','4','5','6','automatic']){
 const {dom,w,d,errors}=setup(theme),calls=[];
 w.ITDDesign.renderJournalRecords(d.querySelector('#records-app'),{projectId:1,role,section,api:{json:async()=>project},onOpen:(kind,item)=>calls.push([kind,item.id??item.project_id]),onTool:(kind,section)=>calls.push([kind,section]),onDelete:(entity,id)=>calls.push([entity,id])});
 await until(()=>d.querySelector('.astryx-data-footer'));const expected=journalBlocks(project,section).length;assert.equal(d.querySelectorAll('.astryx-data-footer').length,expected);assert.equal(d.querySelectorAll('.astryx-column-filters .astryx-power-search .astryx-field-label').length,expected);
 const writeButtons=['Назначить представителя раздела','Добавить работника','Добавить специальный журнал','Внести проверку','Добавить мероприятие','Удалить'];if(role==='viewer')for(const label of writeButtons)assert.equal(button(d,label),undefined);
 const openLabel=({'1':'Работник','4':'Проверка','6':'Надзор',automatic:'ОЖР'})[section];if(openLabel){button(d,openLabel).click();await tick();assert.equal(calls[0][0],section==='automatic'?'automatic':'entry');}
 assert.equal(errors.length,0);dom.window.close();
 }
});
test('switching journal context aborts pending reads and ignores late replies',async()=>{
 const {dom,w,d}=setup('dark');let resolveOld,oldSignal;const api={json:(path,data,{signal})=>path.endsWith('=1')?new Promise(resolve=>{resolveOld=resolve;oldSignal=signal;}):Promise.resolve(project)};const host=d.querySelector('#records-app');w.ITDDesign.renderJournalRecords(host,{projectId:1,role:'viewer',section:'1',api});await until(()=>resolveOld);w.ITDDesign.renderJournalRecords(host,{projectId:2,role:'viewer',section:'4',api});await until(()=>button(d,'Проверка'));assert.equal(oldSignal.aborted,true);resolveOld({journals:{}});await tick();assert.ok(button(d,'Проверка'));dom.window.close();
});
