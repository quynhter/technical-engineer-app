import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM,VirtualConsole} from '../dependencies.mjs';
const bundle=readFileSync(new URL('../../../app/itd/web_assets/design.js',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setTimeout(resolve,20));
async function until(fn){for(let i=0;i<100;i++){if(fn())return;await tick();}assert.ok(fn(),'project records did not settle');}
function setup(theme){
 const errors=[],log=new VirtualConsole();log.on('jsdomError',e=>errors.push(e));log.on('error',e=>errors.push(e));
 const dom=new JSDOM(`<html data-theme="${theme}"><body><div id="content"><div id="records-app"></div></div><div id="command-root"></div></body></html>`,{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:log}),w=dom.window;
 w.CSS={supports:()=>false,escape:String};w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});w.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};w.HTMLElement.prototype.scrollIntoView=function(){};w.eval(bundle);return {dom,w,d:w.document,errors};
}
function button(d,label){return [...d.querySelectorAll('button')].find(b=>b.textContent.trim()===label);}
const project={resources:[{id:1,name:'Кабель',qty_proj:0,qty_fact:null,unit:'м'}],attachments:[{id:8,title:'Оригинал',original_name:'Исходник.pdf'}],manual:{supplies:[{id:2,resource_id:1,quantity:0,unit:'м',allocated:0,remaining:0,status:'pending'}],periods:[{org_id:1,basis:'Договор'}],journals:[{act_id:3,entry_kind:'work'}],sources:[{act_id:3,entry_id:5}]}};
test('manual workspace preserves operations, tables, original downloads and source/period/journal information',async()=>{
 for(const theme of ['light','dark'])for(const role of ['editor','viewer']){
 const {dom,w,d,errors}=setup(theme),calls=[];
 w.ITDDesign.renderManualRecords(d.querySelector('#records-app'),{projectId:1,role,api:{json:async()=>project},operations:{'period-set':'Период участия организации','journal-add':'Связать форму журнала с записями'},onManual:op=>calls.push(op),onResource:id=>calls.push(id),onOriginal:file=>calls.push(file.original_name),onDelete:(entity,id)=>calls.push([entity,id])});await until(()=>d.querySelectorAll('.astryx-data-footer').length===2);assert.match(d.body.textContent,/Неизвестно/);assert.match(d.body.textContent,/Начало неизвестно/);assert.match(d.body.textContent,/Договор/);assert.match(d.body.textContent,/Акт № 3 использует запись № 5/);assert.equal(d.querySelectorAll('.astryx-column-filters .astryx-power-search .astryx-field-label').length,2);
 button(d,'Скачать оригинал').click();button(d,'Кабель\n. м').click();assert.deepEqual(calls,['Исходник.pdf',1]);
 if(role==='editor'){button(d,'Период участия организации').click();assert.equal(calls.at(-1),'period-set');const deleteButtons=[...d.querySelectorAll('button')].filter(b=>b.textContent==='Удалить');assert.equal(deleteButtons.length,2);deleteButtons[1].click();assert.deepEqual(calls.at(-1),['supplies',2]);}else{assert.equal(button(d,'Период участия организации'),undefined);assert.equal(button(d,'Удалить'),undefined);}assert.equal(errors.length,0);dom.window.close();
 }
});
