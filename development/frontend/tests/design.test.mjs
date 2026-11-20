import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM,VirtualConsole} from '../dependencies.mjs';
const bundle=await readFile(new URL('../../../app/itd/web_assets/design.js',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setTimeout(resolve,60));
async function until(fn){for(let i=0;i<40;i++){if(fn())return;await tick();}assert.ok(fn(),'UI did not settle');}
test('Astryx preserves account actions, native form data, delegated tabs and table controls',async()=>{
 const errors=[],log=new VirtualConsole();log.on('jsdomError',e=>errors.push(e));log.on('error',e=>errors.push(e));
 const dom=new JSDOM(`<html data-theme="light"><body><div id="account-controls" hidden><button id="account-open" class="account-avatar">ИИ</button><button id="session-resume" hidden>Войти</button><button id="session-logout">Выйти из системы</button></div><div class="context" id="overview-object-picker" hidden><div><select id="object-select"><option value="">Выберите объект</option></select></div><button id="new-object">Новый объект</button></div><nav id="steps"></nav><div id="breadcrumbs"></div><main class="no-sidebar"><div id="content" class="id-workspace"><nav class="tabs"><button data-tab="0" class="active">Акты</button><button data-tab="1">Ресурсы</button></nav><nav class="panel-nav" aria-label="Подраздел"><button class="active">Список</button></nav><form id="kept-form"><label class="field"><span>Категория</span><select name="category"><option value="a">Приборы</option><option value="b">Кабель</option></select></label><input id="kept-input" name="note" value="Несохранённое значение"><button id="kept-button" class="secondary">Действие</button></form><button class="object-tile">Полное название объекта</button><div class="data-table-footer"><button data-table-control="next">Следующая страница</button></div></div><div id="actions"></div></main><footer id="workspace-status"><details class="table-filter-disclosure resource-fact-picker"><summary>Монтаж по ресурсу</summary><div class="data-table-filters">Выберите ресурс</div></details></footer><div id="editor-content"></div><div id="editor-footer"></div><div id="account-content"></div><div id="prompt-content"></div><div id="knowledge-results"></div><div id="command-root"></div></body></html>`,{url:'http://localhost/?view=registry',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:log});
 const w=dom.window,d=w.document;
 w.CSS={supports:()=>false,escape:value=>String(value).replace(/[^a-zA-Z0-9_-]/g,c=>'\\'+c)};
 w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});
 w.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};
 w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLElement.prototype.scrollTo=function(){};
 const input=d.getElementById('kept-input'),button=d.getElementById('kept-button'),avatar=d.getElementById('account-open'),select=d.querySelector('[name="category"]');
 let clicks=0,profiles=0;button.addEventListener('click',e=>{e.preventDefault();clicks++;});avatar.addEventListener('click',()=>profiles++);
 w.eval(bundle);w.ITDDesign.renderNav([['overview','Обзор',''],['registry','Исполнительная документация','']],'registry',()=>{});
 await until(()=>d.querySelector('.tabs [data-tab-menu]')&&d.querySelector('.workspace-nav [data-account-open]'));
 let themeEvents=0;d.addEventListener('itd:theme-toggle',()=>themeEvents++);const themeButton=[...d.querySelectorAll('button')].find(button=>button.textContent==='Тёмная тема');themeButton.click();assert.equal(themeEvents,1);assert.equal(d.querySelector('#theme-toggle'),null);assert.doesNotMatch(d.querySelector('.header-actions').textContent,/Акцентный цвет|Синий|Зелёный/);assert.equal(d.querySelectorAll('.header-actions [role=combobox]').length,1);assert.match(d.querySelector('.header-actions').textContent,/Neutral/);assert.equal(d.querySelector('[data-open-knowledge]'),null);assert.ok(![...d.querySelectorAll('.workspace-nav button, .workspace-nav a')].some(el=>/Ручное ведение|База знаний/.test(el.textContent)));
 assert.equal(d.querySelector('.account-control [aria-haspopup=menu]'),null);assert.ok(d.querySelector('.account-control #session-logout'));
 assert.equal(d.querySelectorAll('#workspace-status').length,1);assert.ok(d.querySelector('.workspace-nav #workspace-status'));

 const help=d.querySelector('.resource-fact-picker');
 await until(()=>help.querySelector('button[aria-expanded]'));
 const trigger=help.querySelector('button[aria-expanded]');
 assert.equal(help.tagName,'DIV');assert.equal(trigger.textContent.trim(),'Монтаж по ресурсу');
 assert.equal(trigger.getAttribute('aria-expanded'),'false');
 trigger.focus();assert.equal(d.activeElement,trigger);
 trigger.click();await tick();assert.equal(trigger.getAttribute('aria-expanded'),'true');
 assert.match(help.textContent,/Выберите ресурс/);
 button.click();await tick();assert.equal(trigger.getAttribute('aria-expanded'),'true');clicks=0;
 trigger.click();await tick();assert.equal(trigger.getAttribute('aria-expanded'),'false');
 assert.equal(d.getElementById('kept-input'),input);assert.equal(input.value,'Несохранённое значение');
 button.click();assert.equal(clicks,1);assert.match(button.className,/astryx-button/);assert.ok(button.querySelector('[data-itd-button-body]'));
 assert.equal(d.getElementById('account-open'),avatar);d.querySelector('.workspace-nav [data-account-open]').click();assert.equal(profiles,1);assert.equal(d.querySelector('.account-control #account-open'),null);
 let tab=null;d.addEventListener('click',e=>{const b=e.target.closest('[data-tab]');if(b)tab=b.dataset.tab;});
 assert.equal(d.getElementById('overview-object-picker').hidden,true);
 assert.equal(d.getElementById('new-object').closest('[hidden]'),d.getElementById('overview-object-picker'));
 assert.equal(d.querySelectorAll('.workspace-tab-row>nav [data-tab-menu]').length,2);
 const tabMenu=d.querySelector('.tabs [data-tab-menu]');
 tabMenu.click();await until(()=>tabMenu.getAttribute('aria-expanded')==='true');
 const choices=d.getElementById(tabMenu.getAttribute('aria-controls')).querySelectorAll('[role=menuitemradio]');
 choices[0].focus();
 choices[0].dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));
 assert.equal(d.activeElement,choices[1]);
 choices[1].dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
 await tick();assert.equal(tab,'1');
 assert.equal(d.querySelector('[data-tab="1"]').dataset.primitive,undefined);
 assert.equal(d.querySelector('.object-tile').classList.contains('astryx-button'),false);
 assert.ok(d.querySelector('[data-table-control="next"]'));assert.equal(d.querySelectorAll('.data-table-footer').length,1);
 w.ITDDesign.enhanceSelect(select);await until(()=>select.nextElementSibling.querySelector('[role="combobox"]'));
 assert.equal(new w.FormData(d.getElementById('kept-form')).get('category'),'a');
 select.value='b';select.dispatchEvent(new w.Event('smart-sync'));await tick();assert.match(select.nextElementSibling.textContent,/Кабель/);
 select.disabled=true;await tick();assert.equal(select.nextElementSibling.querySelector('[role="combobox"]').getAttribute('aria-disabled'),'true');
 assert.equal(new w.FormData(d.getElementById('kept-form')).get('note'),'Несохранённое значение');
 const scroll=d.createElement('div');scroll.className='table-scroll';scroll.innerHTML='<table><thead><tr><th>Позиция</th><th>Наименование</th></tr></thead><tbody>'+Array.from({length:63},(_,i)=>`<tr data-row-id="${i}"><td>${i+1}</td><td>Ресурс ${i+1}</td></tr>`).join('')+'</tbody></table>';d.getElementById('content').append(scroll);
 const source=scroll.querySelector('table'),controls=d.createElement('div'),footer=d.createElement('div'),panel=d.createElement('div');scroll.before(controls);scroll.after(panel,footer);
 const rows=[...source.tBodies[0].rows],model={key:'test-astryx-table',headers:[...source.tHead.rows[0].cells],rows,matched:rows,controls,footer,panel,nativeFields:false};
 w.ITDDesign.enhanceTable(source,model,()=>{});await until(()=>d.querySelector('.astryx-data-view table'));
 const view=d.querySelector('.astryx-data-view');assert.equal(scroll.hidden,true);assert.equal(controls.hidden,true);assert.equal(footer.hidden,true);
 assert.ok(view.querySelector('[data-table-hooks="columnResize columnSettings filtering"]'));
 assert.equal(view.querySelectorAll('thead [role="separator"]').length,2);assert.equal(view.querySelectorAll('thead [aria-haspopup]').length,0);
 const lastHandle=[...view.querySelectorAll('thead [role="separator"]')].at(-1),beforeWidth=Number(lastHandle.getAttribute('aria-valuenow'));
 lastHandle.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Home',bubbles:true}));await tick();assert.equal(Number(lastHandle.getAttribute('aria-valuenow')),Number(lastHandle.getAttribute('aria-valuemin')));assert.ok(Number(lastHandle.getAttribute('aria-valuenow'))<beforeWidth,'The final business column must resize independently of the flexible gutter');
 assert.equal(view.querySelectorAll('tbody tr').length,50);view.querySelector('[aria-label="Перейти на страницу 2"]').click();await tick();assert.equal(view.querySelectorAll('tbody tr').length,13);assert.match(view.textContent,/51.*63.*63/s);
 view.querySelector('[data-table-control="columns"]').click();await until(()=>d.querySelector('.astryx-column-picker'));
 [...d.querySelectorAll('.astryx-column-picker input')].at(-1).click();await tick();assert.equal(view.querySelectorAll('thead th').length,2);
 assert.ok(input.parentElement.classList.contains('itd-field-control'),'Native input must retain the complete field frame');
 d.documentElement.dataset.theme='dark';d.dispatchEvent(new w.Event('itd:appearance'));await tick();
 tabMenu.click();await until(()=>tabMenu.getAttribute('aria-expanded')==='true');
 assert.equal(d.getElementById(tabMenu.getAttribute('aria-controls')).querySelectorAll('[role=menuitemradio]').length,2);
 tabMenu.click();await until(()=>tabMenu.getAttribute('aria-expanded')==='false');
 trigger.click();await tick();assert.equal(trigger.getAttribute('aria-expanded'),'true');trigger.click();await tick();assert.equal(trigger.getAttribute('aria-expanded'),'false');
 d.getElementById('content').innerHTML='<nav class="tabs"><button data-tab="0" class="active">Новая вкладка</button></nav>';
 w.ITDDesign.renderNav([['overview','Обзор','']],'overview',()=>{});
 await until(()=>d.querySelector('.tabs[data-astryx-island] [data-tab]'));await tick();
 assert.equal(d.getElementById('overview-object-picker').hidden,false);
 assert.equal(d.getElementById('breadcrumbs').nextElementSibling,d.getElementById('overview-object-picker'));
 assert.equal(d.getElementById('new-object').closest('[hidden]'),null);
 assert.equal(d.documentElement.dataset.astryxTheme,'neutral','Unmounting a tab must not remove the root theme');assert.equal(d.documentElement.dataset.theme,'dark');
 const dynamicDialog=d.createElement('dialog');dynamicDialog.className='workspace-dialog';dynamicDialog.innerHTML='<div class="dialog-content"><button>Первое действие</button></div>';d.body.append(dynamicDialog);
 await until(()=>dynamicDialog.querySelector('button').dataset.primitive==='button-primary');
 dynamicDialog.querySelector('.dialog-content').innerHTML='<div class="workspace-stack"><button class="secondary">Появившееся действие</button></div>';
 await until(()=>dynamicDialog.querySelector('button').dataset.primitive==='button-secondary');
 assert.equal(errors.length,0,errors.map(e=>e.detail?.stack||e.message).join('\n'));dom.window.close();
});


test('form tables keep native layout and are not primed as Astryx tables',async()=>{
 const errors=[],log=new VirtualConsole();log.on('jsdomError',e=>errors.push(e));log.on('error',e=>errors.push(e));
 const dom=new JSDOM(`<html data-theme="light"><body><div id="content"><div class="table-scroll" id="browse"><table><thead><tr><th>Позиция</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></div></div><div id="editor-content"><form id="import-form"><div class="table-scroll" id="src"><table><thead><tr><th>Наименование</th><th>Ед. изм.</th></tr></thead><tbody><tr><td>Кабель</td><td>м</td></tr></tbody></table></div></form></div><div id="command-root"></div></body></html>`,{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:log});
 const w=dom.window,d=w.document;
 w.CSS={supports:()=>false,escape:String};w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});
 w.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};
 w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLElement.prototype.scrollTo=function(){};
 w.eval(bundle);
 await until(()=>d.querySelector('#browse table')?.dataset.primitive==='table');
 assert.equal(d.querySelector('#browse table').dataset.primitive,'table');
 assert.equal(d.querySelector('#src table').dataset.primitive,undefined);
 assert.equal(errors.length,0,errors.map(e=>e.detail?.stack||e.message).join('\n'));dom.window.close();
});

test('Legacy loading leaves the React table intact and restores source rows',async()=>{
 const source=await readFile(new URL('../../../app/itd/web_assets/ui.js',import.meta.url),'utf8');
 const loading=source.slice(source.indexOf('function tableLoading(){'),source.indexOf('// Подсказка открывается'));
 const dom=new JSDOM('<div id="content"><div class="table-scroll"><table><thead><tr><th>Название</th></tr></thead><tbody><tr><td>Исходная строка</td></tr></tbody></table></div><div class="astryx-data-grid"><table><tbody><tr><td>Строка React</td></tr></tbody></table></div></div>',{runScripts:'outside-only'});
 const w=dom.window,d=w.document;
 w.eval('const tableObserver={disconnect(){}};const decorateDataTables=()=>{},observeTables=()=>{};'+loading);
 const react=d.querySelector('.astryx-data-grid tbody'),original=react.firstElementChild;
 const restore=w.tableLoading();
 assert.equal(react.firstElementChild,original);
 assert.equal(d.querySelector('.table-scroll').getAttribute('aria-busy'),'true');
 assert.ok(d.querySelector('.table-skeleton'));
 restore();
 assert.equal(d.querySelector('.table-scroll').hasAttribute('aria-busy'),false);
 assert.equal(d.querySelector('.table-scroll tbody').textContent,'Исходная строка');
 assert.equal(react.firstElementChild,original);
 dom.window.close();
});


test('appearance keeps the saved mode and drops the legacy accent preference',async()=>{
 const source=await readFile(new URL('../../../app/itd/web_assets/app.js',import.meta.url),'utf8'),code=source.slice(source.indexOf("const appearanceKey ="),source.indexOf('let token='));
 const dom=new JSDOM('<html><body></body></html>',{url:'http://localhost',runScripts:'outside-only'}),w=dom.window,d=w.document;
 w.localStorage.setItem('itd-appearance',JSON.stringify({theme:'dark',accent:'rose'}));
 w.eval(code);
 assert.equal(d.documentElement.dataset.theme,'dark');
 assert.equal(d.documentElement.hasAttribute('data-accent'),false);
 assert.deepEqual(JSON.parse(w.localStorage.getItem('itd-appearance')),{theme:'dark'});
 d.dispatchEvent(new w.Event('itd:theme-toggle'));
 assert.equal(d.documentElement.dataset.theme,'light');
 assert.deepEqual(JSON.parse(w.localStorage.getItem('itd-appearance')),{theme:'light'});
 dom.window.close();
});


test('dialog footer submits the local scheme form even if native association resolves another form',async()=>{
 const source=await readFile(new URL('../../../app/itd/web_assets/ui.js',import.meta.url),'utf8');
 const dom=new JSDOM('<form id="manual-form"></form><div id="editor-content"><form id="manual-form"><input name="sheets_count" type="number" value="4"><button type="submit">Сохранить</button><button type="button">Отменить</button></form></div><div id="editor-footer"></div>',{runScripts:'outside-only'}),w=dom.window,d=w.document;
 w.eval('const enhanceCheckLists=()=>{};'+source.slice(source.indexOf('function enhanceEditorActions(){')));
 w.mountDialogFooter();const local=d.querySelector('#editor-content form'),save=d.querySelector('#editor-footer button');let submissions=0;
 local.addEventListener('submit',event=>{event.preventDefault();submissions++;assert.equal(new w.FormData(event.target).get('sheets_count'),'4');});
 assert.notEqual(save.form,local);save.click();assert.equal(submissions,1);dom.window.close();
});
