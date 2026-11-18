import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM,VirtualConsole} from 'jsdom';
import {workRows,workValues} from '../src/work-table.mjs';
const bundle=readFileSync(new URL('../../itd/web_assets/design.js',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setTimeout(resolve,20));
async function until(fn){for(let i=0;i<100;i++){if(fn())return;await tick();}assert.ok(fn(),'project records did not settle');}
function setup(theme){
 const errors=[],log=new VirtualConsole();log.on('jsdomError',e=>errors.push(e));log.on('error',e=>errors.push(e));
 const dom=new JSDOM(`<html data-theme="${theme}"><body><div id="content"><div id="records-app"></div></div><div id="command-root"></div></body></html>`,{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:log}),w=dom.window;
 w.CSS={supports:()=>false,escape:String};w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});w.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};w.HTMLElement.prototype.scrollIntoView=function(){};w.eval(bundle);return {dom,w,d:w.document,errors};
}
function button(d,label){return [...d.querySelectorAll('button')].find(b=>b.textContent.trim()===label);}
const project={workspace_entries:[{id:1,kind:'work',entry_date:'2026-11-18',title:'Без акта',details:'Участок',quantity:0,unit:'м'},{id:2,kind:'work',entry_date:'2026-11-17',title:'В акте',act_id:8,attachment_id:4},{id:3,kind:'incoming',title:'Поставка'}],acts:[{id:8,act_num:'А-08'}],attachments:[{id:4,title:'Источник.pdf'}],resources:[{id:5,name:'Кабель'}],work_materials:[{entry_id:1,resource_id:5,quantity:0,unit:'м'}]};
test('work display keeps dates, zero, resource, source and filtering without changing records',()=>{
 const before=JSON.stringify(project);assert.deepEqual(workRows(project,{unbound:true}).map(e=>e.id),[1]);assert.deepEqual(workRows(project,{from:'2026-11-18',query:'кабель'}).map(e=>e.id),[1]);assert.match(workValues(project.workspace_entries[0],project)[2],/Кабель · 0 м/);assert.match(workValues(project.workspace_entries[0],project)[3],/0 м/);assert.match(workValues(project.workspace_entries[1],project)[5],/А-08.*\nИсточник: Источник.pdf/);assert.equal(JSON.stringify(project),before);
});
test('work API table preserves card, act preview, unbound selection, creation and export in both themes',async()=>{
 for(const theme of ['light','dark']){
 const {dom,w,d,errors}=setup(theme),calls=[],saved=[],selection=[];
 w.ITDDesign.renderWorkRecords(d.querySelector('#records-app'),{projectId:7,role:'editor',api:{json:async()=>project},onOpen:item=>calls.push(['open',item.id]),onActPreview:id=>calls.push(['preview',id]),onCreate:()=>calls.push(['new']),onCreateAct:()=>calls.push(['act']),onDelete:(entity,id)=>calls.push([entity,id]),onSelectionChange:ids=>selection.push([...ids]),saveFile:file=>saved.push(file)});
 await until(()=>d.querySelectorAll('tbody tr').length===2);assert.equal(d.querySelectorAll('tbody input[type=checkbox]').length,1);assert.match(d.querySelector('tbody').textContent,/Кабель · 0 м/);assert.match(d.querySelector('tbody').textContent,/Источник.pdf/);assert.equal(button(d,'Сформировать акт'),undefined);
 button(d,'Без акта').click();button(d,'А-08').click();button(d,'Добавить запись').click();d.querySelector('tbody input[type=checkbox]').click();await until(()=>button(d,'Сформировать акт'));button(d,'Сформировать акт').click();assert.deepEqual(calls,[['open',1],['preview',8],['new'],['act']]);assert.deepEqual(selection.at(-1),[1]);button(d,'Экспорт выбранных').click();assert.equal(saved[0].filename,'Сведения о выполнении работ.csv');
 const csv=await new Promise(resolve=>{const reader=new w.FileReader();reader.onload=()=>resolve(reader.result);reader.readAsText(saved[0].blob);});assert.match(csv,/Без акта/);assert.doesNotMatch(csv,/В акте/);
 button(d,'Фильтр').click();await until(()=>d.querySelector('input[type=checkbox][aria-label="Только работы без актов"]')||[...d.querySelectorAll('label')].some(l=>l.textContent.includes('Только работы без актов')));
 const label=[...d.querySelectorAll('label')].find(l=>l.textContent.includes('Только работы без актов'));d.getElementById(label.htmlFor).click();await until(()=>d.querySelectorAll('tbody tr').length===1);assert.doesNotMatch(d.querySelector('tbody').textContent,/В акте/);button(d,'Экспорт').click();assert.equal(saved.at(-1).filename,'Записи журналов.json');assert.equal(errors.length,0);dom.window.close();
 }
});
test('viewer work table keeps reading and filters without creation or deletion',async()=>{
 const {dom,w,d}=setup('light');w.ITDDesign.renderWorkRecords(d.querySelector('#records-app'),{projectId:1,role:'viewer',api:{json:async()=>project},onDelete:()=>assert.fail()});await until(()=>d.querySelector('tbody button'));for(const label of ['Добавить запись','Сформировать акт','Удалить'])assert.equal(button(d,label),undefined);assert.ok(button(d,'Фильтр'));dom.window.close();
});
