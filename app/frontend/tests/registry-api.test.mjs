import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM,VirtualConsole} from 'jsdom';
const bundle=await readFile(new URL('../../itd/web_assets/design.js',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setTimeout(resolve,25));
async function until(fn){for(let i=0;i<80;i++){if(fn())return;await tick();}assert.ok(fn(),'registry UI did not settle');}
function setup(theme){
 const errors=[],log=new VirtualConsole();log.on('jsdomError',e=>errors.push(e));log.on('error',e=>errors.push(e));
 const dom=new JSDOM(`<html data-theme="${theme}"><body><div id="content"><div id="registry-app"></div></div><div id="command-root"></div></body></html>`,{url:'http://localhost/?view=registry',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:log});
 const w=dom.window;
 w.CSS={supports:()=>false,escape:value=>String(value).replace(/[^a-zA-Z0-9_-]/g,c=>'\\'+c)};w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});
 w.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};
 w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLElement.prototype.scrollTo=function(){};
 w.eval(bundle);return {dom,w,d:w.document,errors};
}
function rows(count){return Array.from({length:count},(_,i)=>({no:i+1,id:i+1,entity:'act',name:i===0?'<img src=x onerror=alert(1)>':'Тестовый акт '+(i+1),number:'A-'+i,date:'2026-11-17',organization:'Тестовая организация',sheets_count:i===0?0:2,pages:''}));}

test('new registry renders API data directly with Astryx table controls in both themes',async()=>{
 for(const theme of ['light','dark']){
  const {dom,w,d,errors}=setup(theme),calls=[],opened=[];
  const api={json:async(path)=>{calls.push(path);return {registry:rows(63)};}};
  w.ITDDesign.renderRegistry(d.getElementById('registry-app'),{projectId:7,role:'editor',api,onOpen:item=>opened.push(item)});
  await until(()=>d.querySelector('[data-registry-api] tbody tr'));
  assert.equal(calls[0],'/project?project_id=7');assert.equal(d.querySelectorAll('[data-registry-api] table').length,1);
  assert.equal(d.querySelectorAll('[data-registry-api] tbody tr').length,50);assert.equal(d.querySelector('[data-registry-api] img'),null);
  assert.match(d.querySelector('.astryx-table-totals').textContent,/Кол-во листов: 124/);assert.doesNotMatch(d.querySelector('.astryx-table-totals').textContent,/№ п\/п/);
  assert.match(d.querySelector('[data-registry-api] tbody tr').textContent,/<img/);assert.match(d.querySelector('[data-registry-api] tbody tr').textContent,/0/);
  const filter=[...d.querySelectorAll('[data-registry-api] button')].find(b=>b.textContent==='Фильтр');assert.ok(filter);filter.focus();assert.equal(d.activeElement,filter);
  d.querySelector('[aria-label="Перейти на страницу 2"]').click();await until(()=>d.querySelectorAll('[data-registry-api] tbody tr').length===13);
  d.querySelector('[data-table-control="columns"]').click();await until(()=>d.querySelector('.astryx-column-picker'));
  [...d.querySelectorAll('.astryx-column-picker input')].at(-1).click();await tick();assert.equal(d.querySelectorAll('[data-registry-api] thead th').length,7);
  d.querySelector('[data-registry-api] tbody button').click();assert.equal(opened.length,1);
  const search=d.querySelector('[data-table-control="search"] input')||d.querySelector('input[data-table-control="search"]');
  Object.getOwnPropertyDescriptor(w.HTMLInputElement.prototype,'value').set.call(search,'Тестовый акт 63');
  search.dispatchEvent(new w.Event('input',{bubbles:true}));
  await until(()=>d.querySelectorAll('[data-registry-api] tbody tr').length===1);
  assert.match(d.querySelector('[data-registry-api] tbody tr').textContent,/Тестовый акт 63/);
  assert.equal(errors.length,0,errors.map(e=>e.detail?.stack||e.message).join('\n'));dom.window.close();
 }
});

test('empty viewer registry retains filters/footer and has no export controls',async()=>{
 const {dom,w,d,errors}=setup('light');w.ITDDesign.renderRegistry(d.getElementById('registry-app'),{projectId:1,role:'viewer',api:{json:async()=>({registry:[]})}});
 await until(()=>d.querySelector('[data-registry-api] .astryx-data-footer'));
 assert.ok([...d.querySelectorAll('button')].some(b=>b.textContent==='Фильтр'));
 assert.equal([...d.querySelectorAll('[data-registry-api] button')].some(b=>b.textContent.includes('Экспорт DOCX')||b.textContent.includes('Экспорт ZIP')),false);
 assert.equal(d.querySelectorAll('[data-registry-api] .astryx-data-footer').length,1);assert.equal(errors.length,0);dom.window.close();
});

test('mounting the new registry preserves every main navigation section',async()=>{
 const {dom,w,d,errors}=setup('light'),navigation=[['overview','Обзор',''],['object','Объект',''],['rd','Разделы',''],['participants','Участники',''],['registry','Исполнительная документация','']];
 w.ITDDesign.renderNav(navigation,'registry',()=>{});
 w.ITDDesign.renderRegistry(d.getElementById('registry-app'),{projectId:7,role:'editor',api:{json:async()=>({registry:rows(1)})}});
 await until(()=>d.querySelector('[data-registry-api] tbody tr')&&d.querySelector('.workspace-nav'));
 const labels=[...d.querySelectorAll('.workspace-nav button')].map(button=>button.textContent.trim());
 for(const [,label] of navigation)assert.ok(labels.includes(label),'Missing main navigation: '+label);
 assert.ok(labels.includes('Все объекты'));assert.equal(errors.length,0);dom.window.close();
});

test('registry export uses v1 client, prevents repeats, keeps the filename and shows audit errors',async()=>{
 const {dom,w,d,errors}=setup('dark'),calls=[],saved=[];let resolveDownload;
 const api={json:async(path,data)=>{calls.push({path,data});return path==='/registry/export'?{release_id:5}:{registry:rows(1)};},download:(path)=>{calls.push({path});return new Promise(resolve=>{resolveDownload=resolve;});}};
 w.ITDDesign.renderRegistry(d.getElementById('registry-app'),{projectId:7,role:'editor',api,saveFile:file=>saved.push(file)});
 await until(()=>d.querySelector('[data-registry-api] tbody tr'));
 const button=[...d.querySelectorAll('button')].find(b=>b.textContent==='Экспорт DOCX');button.click();button.click();await until(()=>resolveDownload);
 assert.equal(calls.filter(c=>c.path==='/registry/export').length,1);resolveDownload({blob:new w.Blob(['docx']),filename:'Акт с исходным именем.docx'});
 await until(()=>saved.length===1);assert.equal(saved[0].filename,'Акт с исходным именем.docx');await until(()=>!button.disabled);
 api.download=async()=>{throw Error('Аудит недоступен');};[...d.querySelectorAll('button')].find(b=>b.textContent==='Экспорт ZIP').click();await until(()=>d.body.textContent.includes('Аудит недоступен'));
 assert.equal(saved.length,1);assert.equal(errors.length,0,errors.map(e=>e.detail?.stack||e.message).join('\n'));dom.window.close();
});

test('switching projects aborts old reads and a late response cannot replace the new registry',async()=>{
 const {dom,w,d}=setup('light');let resolveOld,oldSignal;
 const api={json:(path,data,{signal})=>path.endsWith('=1')?new Promise(resolve=>{resolveOld=resolve;oldSignal=signal;}):Promise.resolve({registry:[{...rows(1)[0],name:'Новый раздел'}]})};
 const host=d.getElementById('registry-app');w.ITDDesign.renderRegistry(host,{projectId:1,role:'viewer',api});await until(()=>resolveOld);
 w.ITDDesign.renderRegistry(host,{projectId:2,role:'viewer',api});await until(()=>host.textContent.includes('Новый раздел'));assert.equal(oldSignal.aborted,true);
 resolveOld({registry:[{...rows(1)[0],name:'Старый раздел'}]});await tick();assert.equal(host.textContent.includes('Старый раздел'),false);dom.window.close();
});

test('registry retains inferred deletion actions for every supported entity and keeps journals read-only',async()=>{
 const {dom,w,d}=setup('light'),deleted=[];
 const registry=['act','scheme','attachment','release','journal'].map((entity,index)=>({...rows(1)[0],entity,id:index+1,name:entity}));
 w.ITDDesign.renderRegistry(d.getElementById('registry-app'),{projectId:7,role:'editor',api:{json:async()=>({registry})},onDelete:(entity,id)=>deleted.push([entity,id])});
 await until(()=>d.querySelectorAll('[data-registry-api] tbody button').length===4);
 for(const button of d.querySelectorAll('[data-registry-api] tbody button'))button.click();
 assert.deepEqual(deleted,[['acts',1],['schemes',2],['attachments',3],['releases',4]]);dom.window.close();
});

test('registry exports only checked rows and can clear selection without changing data',async()=>{
 const {dom,w,d}=setup('light'),saved=[];
 w.ITDDesign.renderRegistry(d.getElementById('registry-app'),{projectId:7,role:'viewer',api:{json:async()=>({registry:rows(2)})},saveFile:file=>saved.push(file)});
 await until(()=>d.querySelectorAll('tbody input[type=checkbox]').length===2);
 d.querySelector('tbody input[type=checkbox]').click();
 await until(()=>[...d.querySelectorAll('button')].some(b=>b.textContent==='Экспорт выбранных'));
 [...d.querySelectorAll('button')].find(b=>b.textContent==='Экспорт выбранных').click();assert.equal(saved.length,1);assert.equal(saved[0].filename,'Реестр ИД.csv');
 const csv=await new Promise((resolve,reject)=>{const reader=new w.FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsText(saved[0].blob);});
 assert.match(csv,/<img src=x onerror=alert\(1\)>/);assert.doesNotMatch(csv,/Тестовый акт 2/);assert.equal(csv.split('\r\n').length,2);
 [...d.querySelectorAll('button')].find(b=>b.textContent==='Снять выбор').click();await until(()=>!d.querySelector('.astryx-table-selection'));assert.equal(d.querySelectorAll('tbody tr').length,2);dom.window.close();
});
