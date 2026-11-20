import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM,VirtualConsole} from '../dependencies.mjs';
import {findingPresentation,findingResource} from '../../../app/frontend/src/workflow-model.mjs';
const bundle=readFileSync(new URL('../../../app/itd/web_assets/design.js',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setTimeout(resolve,20));
async function until(fn){for(let i=0;i<100;i++){if(fn())return;await tick();}assert.ok(fn(),'project records did not settle');}
function setup(theme){
 const errors=[],log=new VirtualConsole();log.on('jsdomError',e=>errors.push(e));log.on('error',e=>errors.push(e));
 const dom=new JSDOM(`<html data-theme="${theme}"><body><div id="content"><div id="records-app"></div></div><div id="command-root"></div></body></html>`,{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:log}),w=dom.window;
 w.CSS={supports:()=>false,escape:String};w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});w.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};w.HTMLElement.prototype.scrollIntoView=function(){};w.eval(bundle);return {dom,w,d:w.document,errors};
}
function button(d,label){return [...d.querySelectorAll('button')].find(b=>b.textContent.trim()===label);}
const project={resources:[{id:7,spec_num:'12',name:'Кабель <А>',type_mark:'КПС'}],acts:[],forms:[],attachments:[],releases:[],workspace_entries:[],quality_reviews:[],manual:{supplies:[]},check:{findings:[{code:'qty_fact_unknown',fact_id:21},{code:'requirements_not_configured'}]},workflow:{fact_records:[{id:21,resource_id:7,work_description:'Прокладка',location:'Этаж 2'}],matrix:{requirements:[{id:1,title:'Согласованный документ',state:'required',availability:'missing',work_scope:'Монтаж',basis:'Проект',reason:'Согласовано'}]},deliveries:[{id:3,recipient:'Заказчик',status:'sent',release_id:5}],remarks:[{id:4,delivery_id:3,description:'Замечание к комплекту',status:'open'},{id:6,delivery_id:3,description:'Устранённое замечание',status:'resolved'}]},delivery_events:[{delivery_id:3,event_date:'2026-11-18',status:'sent',source:'Письмо',note:'Передано лично'}]};
test('findings resolve exact resource/fact names and destinations without raw identifiers',()=>{
 const {findingDetails,findingDestination,resourceLabel}=findingPresentation(project),f={code:'qty_fact_unknown',resource_id:7,fact_id:21};assert.match(findingDetails(f),/Поз. 12. Кабель <А>. КПС/);assert.match(findingDetails(f),/Этаж 2/);assert.equal(findingResource({fact_id:21},project),7);assert.equal(findingDestination(f.code)[0],'resources');assert.match(resourceLabel(999),/недоступен/);
});
test('check preserves disclosures, exact subject links, requirements and read-only roles in both themes',async()=>{
 for(const theme of ['light','dark'])for(const role of ['editor','viewer']){
 const {dom,w,d,errors}=setup(theme),calls=[];let dirty=false;
 w.ITDDesign.renderWorkflowRecords(d.querySelector('#records-app'),{kind:'check',projectId:1,role,api:{json:async()=>project},isDirty:()=>dirty,onResource:id=>calls.push(['resource',id]),onManual:(op,id)=>calls.push([op,id]),onNavigate:view=>calls.push(['navigate',view]),onDelete:(entity,id)=>calls.push([entity,id])});
 await until(()=>button(d,'Ресурсы и монтаж (1)'));button(d,'Ресурсы и монтаж (1)').click();await until(()=>button(d,'Поз. 12. Кабель <А>. КПС'));button(d,'Поз. 12. Кабель <А>. КПС').click();assert.deepEqual(calls,[['resource',7]]);assert.equal(d.querySelector('img'),null);
 button(d,'Состав комплекта (1)').click();await until(()=>d.body.textContent.includes('Согласованный документ'));if(role==='editor'){button(d,'Добавить документ').click();button(d,'Изменить').click();button(d,'Удалить').click();assert.deepEqual(calls.slice(1),[['requirement-add',undefined],['requirement-set',1],['package_requirements',1]]);}else for(const label of ['Добавить документ','Изменить','Удалить'])assert.equal(button(d,label),undefined);
 dirty=true;button(d,'Поз. 12. Кабель <А>. КПС').click();await until(()=>d.body.textContent.includes('Сначала сохраните'));assert.equal(errors.length,0);dom.window.close();
 }
});
test('delivery keeps full event history and matching actions; viewers only read',async()=>{
 for(const role of ['editor','viewer']){
 const {dom,w,d,errors}=setup('dark'),calls=[];w.ITDDesign.renderWorkflowRecords(d.querySelector('#records-app'),{kind:'delivery',projectId:1,role,api:{json:async()=>project},onManual:(op,id)=>calls.push([op,id]),onDelete:(entity,id)=>calls.push([entity,id])});await until(()=>button(d,'История'));button(d,'История').click();await until(()=>d.body.textContent.includes('Передано лично'));assert.match(d.body.textContent,/18.11.2026/);assert.match(d.body.textContent,/Письмо/);assert.match(d.body.textContent,/Устранённое замечание/);
 if(role==='editor'){for(const label of ['Учесть передачу','Изменить статус','Добавить замечание','Закрыть с основанием'])button(d,label).click();assert.deepEqual(calls,[['delivery-add',undefined],['delivery-set',3],['remark-add',3],['remark-resolve',4]]);assert.equal([...d.querySelectorAll('button')].filter(b=>b.textContent==='Закрыть с основанием').length,1);}else for(const label of ['Учесть передачу','Изменить статус','Добавить замечание','Закрыть с основанием','Удалить'])assert.equal(button(d,label),undefined);assert.equal(errors.length,0);dom.window.close();
 }
});
