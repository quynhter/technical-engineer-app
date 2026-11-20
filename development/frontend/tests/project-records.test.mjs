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
test('schemes retain creation, opening, deletion preview, zero values and safe text in both themes',async()=>{
 for(const theme of ['light','dark']){
  const {dom,w,d,errors}=setup(theme),calls=[];let dirty=false;
  w.ITDDesign.renderProjectRecords(d.querySelector('#records-app'),{kind:'schemes',projectId:7,role:'editor',api:{json:async()=>({schemes:[{id:3,num:0,name:'<img src=x onerror=alert(1)>',ref_code:'РД',note:'Примечание'}]})},isDirty:()=>dirty,onCreate:()=>calls.push(['create']),onOpen:item=>calls.push(['open',item.id]),onDelete:(entity,id)=>calls.push([entity,id])});
  await until(()=>d.querySelector('tbody button'));assert.equal(d.querySelector('img'),null);assert.match(d.querySelector('tbody').textContent,/0/);assert.match(d.querySelector('tbody').textContent,/Примечание/);
  button(d,'Добавить схему').click();button(d,'<img src=x onerror=alert(1)>').click();button(d,'Удалить').click();await tick();assert.deepEqual(calls,[['create'],['open',3],['schemes',3]]);
  dirty=true;button(d,'Удалить').click();await until(()=>d.body.textContent.includes('Сначала сохраните'));assert.equal(calls.length,3);
  assert.ok(d.querySelector('.astryx-column-filters .astryx-power-search .astryx-field-label'));assert.equal(d.querySelectorAll('.astryx-data-footer').length,1);assert.equal(errors.length,0);dom.window.close();
 }
});
test('empty viewer schemes keep filter/footer and never render mutation buttons',async()=>{
 const {dom,w,d}=setup('light');w.ITDDesign.renderProjectRecords(d.querySelector('#records-app'),{kind:'schemes',projectId:1,role:'viewer',api:{json:async()=>({schemes:[]})},onCreate:()=>assert.fail(),onDelete:()=>assert.fail()});
 await until(()=>d.querySelector('.astryx-data-footer'));assert.ok(d.querySelector('.astryx-column-filters .astryx-power-search .astryx-field-label'));assert.equal(button(d,'Удалить'),undefined);assert.equal(button(d,'Добавить схему'),undefined);assert.equal(d.querySelectorAll('.astryx-data-footer').length,1);dom.window.close();
});
test('changing workspace aborts old scheme reads and keeps the new project visible',async()=>{
 const {dom,w,d}=setup('dark');let resolveOld,oldSignal;const api={json:(path,data,{signal})=>path.endsWith('=1')?new Promise(resolve=>{resolveOld=resolve;oldSignal=signal;}):Promise.resolve({schemes:[{id:2,name:'Новая схема'}]})};
 const host=d.querySelector('#records-app');w.ITDDesign.renderProjectRecords(host,{kind:'schemes',projectId:1,workspaceId:'old',role:'viewer',api});await until(()=>resolveOld);
 w.ITDDesign.renderProjectRecords(host,{kind:'schemes',projectId:2,workspaceId:'new',role:'viewer',api});await until(()=>d.body.textContent.includes('Новая схема'));assert.equal(oldSignal.aborted,true);resolveOld({schemes:[{id:1,name:'Старая схема'}]});await tick();assert.equal(d.body.textContent.includes('Старая схема'),false);dom.window.close();
});

test('documents preserve active rows, title, date, status, creation and upload; viewers have only reading',async()=>{
 for(const role of ['editor','viewer']){
  const {dom,w,d}=setup('light'),calls=[];
  const project={acts:[{id:1,act_num:'А-01',act_type:'TEST',is_active:1,date_signed:'2026-11-17'},{id:2,act_type:'HIDDEN',is_active:0}],forms:[{code:'TEST',name:'Учебный акт'}],act_statuses:[{act_id:1,state:'signed'}]};
  w.ITDDesign.renderProjectRecords(d.querySelector('#records-app'),{kind:'documents',projectId:1,role,api:{json:async()=>project},onCreate:()=>calls.push('create'),onImport:()=>calls.push('upload'),onOpen:item=>calls.push(item.id),onDelete:()=>calls.push('delete')});
  await until(()=>d.querySelector('tbody button'));assert.match(d.querySelector('tbody').textContent,/А-01/);assert.match(d.querySelector('tbody').textContent,/17\.11\.2026/);assert.match(d.querySelector('tbody').textContent,/Подписан/);assert.doesNotMatch(d.body.textContent,/HIDDEN/);
  button(d,'Учебный акт').click();assert.deepEqual(calls,[1]);
  if(role==='editor'){button(d,'Создать').click();button(d,'Загрузить').click();assert.deepEqual(calls,[1,'create','upload']);assert.ok(button(d,'Удалить'));}
  else for(const label of ['Создать','Загрузить','Удалить'])assert.equal(button(d,label),undefined);
  dom.window.close();
 }
});

test('resource inventory keeps all columns, import menu actions and a single installation quantity source',async()=>{
 const {dom,w,d}=setup('light'),calls=[];
 const inventory=[{id:1,spec_num:'01',name:'Кабель',category:'Материалы',type_mark:'Тест',manufacturer:'Завод',supplier:'Склад',unit:'м',qty_proj:0,qty_fact:10,consumed:8,note:'Примечание'},{id:2,name:'Ноль',qty_fact:0},{id:3,name:'Неизвестно',qty_fact:null}];
 w.ITDDesign.renderProjectRecords(d.querySelector('#records-app'),{kind:'resources',projectId:7,role:'editor',api:{json:async()=>({inventory,workflow:{facts:[{resource_id:1,confirmed_ids:[1],confirmed_total:8}]}})},onCreate:()=>calls.push('create'),onImport:()=>calls.push('import'),onOpen:item=>calls.push(item.id),onDelete:()=>{}});
 await until(()=>d.querySelectorAll('tbody tr').length===3);
 const cells=[...d.querySelector('tbody tr').cells].map(cell=>cell.textContent.trim());assert.deepEqual(cells.slice(0,10),['01','Кабель','Материалы','Тест','Завод','Склад','м','0','10','Примечание']);
 assert.equal(d.querySelectorAll('tbody tr')[1].cells[8].textContent,'0');assert.equal(d.querySelectorAll('tbody tr')[2].cells[8].textContent,'Не указано');
 assert.equal(d.querySelectorAll('.astryx-data-footer').length,1);assert.equal(d.querySelector('.astryx-table-totals'),null);
 assert.deepEqual([...d.querySelectorAll('.toolbar button')].map(b=>b.textContent.trim()),['Добавить ресурс']);d.querySelector('[aria-label="Действия с таблицей"]').click();await until(()=>[...d.querySelectorAll('[role=menuitem]')].some(item=>item.textContent.includes('Импорт Excel / CSV')));const menu=[...d.querySelectorAll('[role=menuitem]')];assert.match(menu[0].textContent,/Импорт Excel/);assert.match(menu[1].textContent,/Экспорт CSV/);menu[0].click();button(d,'Добавить ресурс').click();button(d,'Кабель').click();assert.deepEqual(calls,['import','create',1]);dom.window.close();
});

test('viewer table preferences cannot hide editor actions after reauthentication',async()=>{
 const {dom,w,d}=setup('light'),host=d.querySelector('#records-app'),api={json:async()=>({schemes:[{id:1,name:'Схема'}]})};
 const props={kind:'schemes',projectId:1,api,onDelete:()=>{}};
 w.ITDDesign.renderProjectRecords(host,{...props,role:'viewer'});await until(()=>d.querySelector('tbody tr'));assert.equal(button(d,'Удалить'),undefined);
 const input=d.querySelector('input[data-table-control="search"]')||d.querySelector('[data-table-control="search"] input');Object.getOwnPropertyDescriptor(w.HTMLInputElement.prototype,'value').set.call(input,'нет совпадений');input.dispatchEvent(new w.Event('input',{bubbles:true}));await until(()=>d.body.textContent.includes('Нет совпадений'));
 w.ITDDesign.renderProjectRecords(host,{...props,role:'editor'});await until(()=>button(d,'Удалить'));assert.match(d.querySelector('tbody').textContent,/Схема/);dom.window.close();
});

test('schemes and documents preserve checked-row CSV export',async()=>{
 for(const kind of ['schemes','documents']){
  const {dom,w,d}=setup('dark'),saved=[];
  const project={schemes:[{id:1,name:'Первая схема'},{id:2,name:'Вторая схема'}],acts:[{id:1,act_type:'FIRST',is_active:1},{id:2,act_type:'SECOND',is_active:1}]};
  w.ITDDesign.renderProjectRecords(d.querySelector('#records-app'),{kind,projectId:1,role:'viewer',api:{json:async()=>project},saveFile:file=>saved.push(file)});
  await until(()=>d.querySelectorAll('tbody input[type=checkbox]').length===2);d.querySelector('tbody input[type=checkbox]').click();await until(()=>button(d,'Экспорт выбранных'));button(d,'Экспорт выбранных').click();assert.equal(saved.length,1);
  const csv=await new Promise((resolve,reject)=>{const reader=new w.FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsText(saved[0].blob);});
  assert.equal(csv.split('\r\n').length,2);assert.match(csv,kind==='schemes'?/Первая схема/:/FIRST/);assert.doesNotMatch(csv,kind==='schemes'?/Вторая схема/:/SECOND/);dom.window.close();
 }
});

test('installation facts preserve dates, zero/unknown, status, work links and the resource picker',async()=>{
 const {dom,w,d}=setup('light'),opened=[],resources=[];
 const project={resources:[{id:1,name:'Кабель',spec_num:'01'}],workspace_entries:[{id:10,title:'Работа в ОЖР',kind:'work'}],work_materials:[{fact_id:1,entry_id:10}],workflow:{fact_records:[{id:1,resource_id:1,quantity:0,unit:'м',start_date:'2026-11-17',status:'confirmed'},{id:2,resource_id:1,quantity:null,end_date:'2026-11-18',work_entry_id:10,status:'pending'},{id:3,status:'void'},{id:4,resource_id:1,quantity:5,status:'pending'}]}};
 w.ITDDesign.renderProjectRecords(d.querySelector('#records-app'),{kind:'facts',projectId:1,role:'viewer',api:{json:async()=>project},onOpen:(item,p)=>opened.push([item.id,p===project]),onResource:id=>resources.push(id)});
 await until(()=>d.querySelectorAll('tbody tr').length===3);
 const rows=[...d.querySelectorAll('tbody tr')];assert.match(rows[0].textContent,/18\.11\.2026/);assert.match(rows[0].textContent,/Не указано/);assert.match(rows[0].textContent,/Ожидает проверки/);assert.equal(rows[1].cells[2].textContent,'0');assert.match(rows[1].textContent,/Подтверждён/);assert.equal(rows[2].querySelector('button'),null);
 rows[0].querySelector('button').click();rows[1].querySelector('button').click();assert.deepEqual(opened,[[2,true],[1,true]]);
 button(d,'Монтаж по ресурсу').click();await until(()=>button(d,'Открыть монтаж по ресурсу'));button(d,'Открыть монтаж по ресурсу').click();await until(()=>d.body.textContent.includes('Выберите ресурс'));assert.equal(resources.length,0);
 d.querySelector('[role=combobox]').click();await until(()=>[...d.querySelectorAll('[role=option]')].some(option=>option.textContent.includes('Кабель')));[...d.querySelectorAll('[role=option]')].find(option=>option.textContent.includes('Кабель')).click();await tick();button(d,'Открыть монтаж по ресурсу').click();assert.deepEqual(resources,[1]);dom.window.close();
});

test('incoming control keeps its six fields, zero before supply fallback, results, ordering and role actions',async()=>{
 for(const role of ['editor','viewer']){
  const {dom,w,d}=setup('light'),calls=[];
  const incoming=[{id:1,kind:'incoming',entry_date:'2026-11-05',title:'Старое имя',resource:{name:'Кабель'},quantity:0,unit:'м',supply:{quantity:99},work_fields:{incoming_result:'accepted'},details:'Примечание'},{id:2,kind:'incoming',entry_date:'2026-11-05',title:'Манометр',quantity:null,supply:{quantity:2,unit:'шт'},work_fields:{}},{id:3,kind:'incoming',entry_date:'2026-11-04',title:'Отклонено',work_fields:{incoming_result:'rejected'}},{id:4,kind:'work',title:'Не входной контроль'}];
  w.ITDDesign.renderProjectRecords(d.querySelector('#records-app'),{kind:'incoming',projectId:1,role,api:{json:async()=>({journals:{incoming}})},onOpen:item=>calls.push(item.id),onCreate:()=>calls.push('create'),onDelete:(entity,id)=>calls.push([entity,id])});
  await until(()=>d.querySelectorAll('tbody tr').length===3);const rows=[...d.querySelectorAll('tbody tr')];
  assert.deepEqual([...rows[0].cells].slice(0,6).map(cell=>cell.textContent),['05.11.2026','Манометр','2','шт','Проверка не завершена','']);assert.equal(rows[1].cells[2].textContent,'0');assert.match(rows[1].textContent,/Входной контроль пройден/);assert.match(rows[2].textContent,/Не принято/);assert.doesNotMatch(d.body.textContent,/Не входной контроль/);
  button(d,'Манометр').click();assert.equal(calls[0],2);
  if(role==='editor'){button(d,'Добавить запись').click();assert.equal(calls[1],'create');rows[0].querySelector('[aria-label^="Удалить запись"]').click();assert.deepEqual(calls[2],['workspace_entries',2]);}
  else {assert.equal(button(d,'Добавить запись'),undefined);assert.equal(button(d,'Удалить'),undefined);}
  dom.window.close();
 }
});

test('cable journal shows only cable works, keeps its three fields and forwards record actions',async()=>{
 const {dom,w,d}=setup('dark'),calls=[];
 const workspace_entries=[{id:1,kind:'work',work_type:'cable',entry_date:'2026-11-18',title:'Прокладка',details:'Участок'},{id:2,kind:'work',work_type:'other',title:'Не кабель'},{id:3,kind:'incoming',work_type:'cable',title:'Не работа'}];
 w.ITDDesign.renderProjectRecords(d.querySelector('#records-app'),{kind:'cable',projectId:1,role:'editor',api:{json:async()=>({workspace_entries})},onCreate:()=>calls.push('create'),onOpen:item=>calls.push(item.id),onDelete:(entity,id)=>calls.push([entity,id])});
 await until(()=>d.querySelector('tbody button'));assert.equal(d.querySelectorAll('tbody tr').length,1);assert.deepEqual([...d.querySelector('tbody tr').cells].slice(0,3).map(cell=>cell.textContent),['18.11.2026','Прокладка','Участок']);assert.match(d.body.textContent,/Журнал прокладки кабеля/);assert.doesNotMatch(d.body.textContent,/Не кабель|Не работа/);
 button(d,'Записать прокладку кабеля').click();button(d,'Прокладка').click();button(d,'Удалить').click();assert.deepEqual(calls,['create',1,['workspace_entries',1]]);dom.window.close();
});


test('project snapshots update rows without another request or losing the table, page and scroll',async()=>{
 for(const theme of ['light','dark']){
  const {dom,w,d}=setup(theme);let reads=0;
  const api={json:async()=>{reads++;throw Error('Unexpected duplicate read');}},host=d.querySelector('#records-app');
  const initialProject={schemes:Array.from({length:63},(_,i)=>({id:i+1,num:String(i+1),name:'Схема '+(i+1)}))};
  const props={kind:'schemes',projectId:7,workspaceId:'snapshot-test',role:'editor',api,initialProject};
  w.ITDDesign.renderProjectRecords(host,props);await until(()=>d.querySelector('tbody tr'));
  d.querySelector('[aria-label="Перейти на страницу 2"]').click();await until(()=>d.querySelectorAll('tbody tr').length===13);
  const table=d.querySelector('table'),scroller=d.querySelector('.astryx-table-scroll-wrapper');scroller.scrollTop=123;scroller.scrollLeft=42;
  const search=d.querySelector('[data-table-control=search] input')||d.querySelector('input[data-table-control=search]');
  const next={schemes:initialProject.schemes.map(item=>({...item,name:item.id===63?'Исправленная схема':item.name}))};
  w.ITDDesign.renderProjectRecords(host,{...props,initialProject:next});await until(()=>d.body.textContent.includes('Исправленная схема'));
  assert.equal(reads,0);assert.equal(d.querySelector('table'),table);assert.equal(d.querySelectorAll('tbody tr').length,13);
  assert.equal(scroller.scrollTop,123);assert.equal(scroller.scrollLeft,42);assert.equal(d.querySelector('input[data-table-control=search]')||d.querySelector('[data-table-control=search] input'),search);
  assert.equal(d.querySelectorAll('thead [aria-haspopup]').length,0);assert.equal(d.querySelectorAll('.astryx-column-filters .astryx-power-search .astryx-field-label').length,1);
  dom.window.close();
 }
});

test('resource CSV exports an ID and empty project quantity suitable for importing back',async()=>{
 const {dom,w,d}=setup('light'),saved=[];
 w.ITDDesign.renderProjectRecords(d.querySelector('#records-app'),{kind:'resources',projectId:7,role:'viewer',initialProject:{inventory:[{id:17,name:'Кабель',unit:'м',category:'Кабельная продукция',qty_proj:null}]},api:{json:()=>assert.fail('duplicate read')},saveFile:file=>saved.push(file)});
 await until(()=>d.querySelector('tbody tr'));d.querySelector('[aria-label="Действия с таблицей"]').click();await until(()=>d.querySelector('[role=menuitem]'));[...d.querySelectorAll('[role=menuitem]')].find(item=>item.textContent.includes('Экспорт CSV')).click();
 const csv=await new Promise(resolve=>{const reader=new w.FileReader();reader.onload=()=>resolve(reader.result);reader.readAsText(saved[0].blob);});
 assert.match(csv,/^"ID";/);assert.match(csv,/\r\n"17";/);assert.equal(csv.split('\r\n')[1].split(';')[8],'""');dom.window.close();
});
