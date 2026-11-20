import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM,VirtualConsole} from '../dependencies.mjs';
const bundle=readFileSync(new URL('../../../app/itd/web_assets/design.js',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setTimeout(resolve,20));
async function until(fn){for(let i=0;i<100;i++){if(fn())return;await tick();}assert.ok(fn(),'source files UI did not settle');}
function setup(theme){
 const errors=[],log=new VirtualConsole();log.on('jsdomError',e=>errors.push(e));log.on('error',e=>errors.push(e));
 const dom=new JSDOM(`<html data-theme="${theme}"><body><div id="content"><div id="source-files-app"></div></div><div id="command-root"></div></body></html>`,{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:log}),w=dom.window;
 w.CSS={supports:()=>false,escape:String};w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});
 w.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};w.HTMLElement.prototype.scrollIntoView=function(){};w.eval(bundle);
 return {dom,w,d:w.document,errors};
}
function click(d,label){const button=[...d.querySelectorAll('button')].find(b=>b.textContent.trim()===label);assert.ok(button,label);button.click();return button;}
test('source files preserve the table, empty filters, names and viewer reading in both themes',async()=>{
 for(const theme of ['light','dark']){
  const {dom,w,d,errors}=setup(theme),opened=[];
  const api={json:async()=>({source_files:[{id:4,original_name:'<img src=x onerror=alert(1)>',doc_type:'quality'}]})};
  w.ITDDesign.renderSourceFiles(d.querySelector('#source-files-app'),{projectId:7,workspaceId:'one',role:'viewer',api,onOpen:file=>opened.push(file.id),onDelete:()=>assert.fail('viewer deletion')});
  await until(()=>d.querySelector('[data-source-files-api] button'));click(d,'Исходные файлы');await until(()=>d.querySelector('[data-source-files-api] tbody button'));
  assert.equal(d.querySelector('[data-source-files-api] img'),null);assert.match(d.querySelector('tbody').textContent,/<img/);
  assert.equal([...d.querySelectorAll('button')].some(b=>['Добавить файлы','Проверить файлы','Удалить'].includes(b.textContent.trim())),false);
  click(d,'<img src=x onerror=alert(1)>');assert.deepEqual(opened,[4]);assert.ok(d.querySelector('.astryx-column-filters .astryx-power-search .astryx-field-label'));
  assert.equal(d.querySelectorAll('.astryx-data-footer').length,1);assert.equal(errors.length,0);dom.window.close();
 }
});
test('source upload is explicit, writes once, refreshes partial batches and respects dirty state',async()=>{
 const {dom,w,d,errors}=setup('light'),calls=[],changed=[],deleted=[];let dirty=true,records=[];
 const api={json:async(path,data)=>{calls.push({path,data});if(path==='/upload'){if(data.name==='fail.txt')throw Error('Результат операции неизвестен');records=[{id:5,original_name:data.name,doc_type:data.doc_type}];return {ok:true};}return {source_files:records};}};
 w.ITDDesign.renderSourceFiles(d.querySelector('#source-files-app'),{projectId:7,role:'editor',api,isDirty:()=>dirty,onChanged:v=>changed.push(v),onDelete:(entity,id)=>deleted.push([entity,id])});
 await until(()=>d.querySelector('[data-source-files-api] button'));click(d,'Исходные файлы');await until(()=>d.querySelector('input[type=file]'));
 const input=d.querySelector('input[type=file]'),choose=files=>{Object.defineProperty(input,'files',{configurable:true,value:files});input.dispatchEvent(new w.Event('change',{bubbles:true}));};
 choose([new w.File(['first'],'one.txt')]);await until(()=>d.body.textContent.includes('Сначала сохраните'));assert.equal(calls.filter(c=>c.path==='/upload').length,0);
 dirty=false;choose([new w.File(['first'],'one.txt'),new w.File(['second'],'fail.txt')]);await until(()=>d.body.textContent.includes('Результат операции неизвестен')&&d.querySelector('tbody button'));
 assert.equal(calls.filter(c=>c.path==='/upload').length,2);assert.equal(calls.find(c=>c.path==='/upload').data.content,'Zmlyc3Q=');assert.equal(calls.find(c=>c.path==='/upload').data.project_id,7);
 assert.equal(changed.length,2);assert.equal(changed[0].source_files.length,0);assert.equal(changed[1].source_files[0].id,5);assert.match(d.querySelector('tbody').textContent,/one.txt/);click(d,'Удалить');assert.deepEqual(deleted,[['attachments',5]]);assert.equal(errors.length,0);dom.window.close();
});
test('source requests abort when database or project changes',async()=>{
 const {dom,w,d}=setup('dark');let resolveOld,oldSignal;
 const api={json:(path,data,{signal})=>path.endsWith('=1')?new Promise(resolve=>{resolveOld=resolve;oldSignal=signal;}):Promise.resolve({source_files:[]})};
 const host=d.querySelector('#source-files-app');w.ITDDesign.renderSourceFiles(host,{projectId:1,workspaceId:'old',role:'viewer',api});await until(()=>resolveOld);
 w.ITDDesign.renderSourceFiles(host,{projectId:2,workspaceId:'new',role:'viewer',api});await until(()=>oldSignal.aborted);
 resolveOld({source_files:[{id:1,title:'Старый файл'}]});await tick();click(d,'Исходные файлы');await until(()=>d.querySelector('.astryx-data-footer'));assert.equal(d.body.textContent.includes('Старый файл'),false);dom.window.close();
});
