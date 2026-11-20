import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM,VirtualConsole} from '../dependencies.mjs';
const bundle=await readFile(new URL('../../../app/itd/web_assets/design.js',import.meta.url),'utf8');
const tick=()=>new Promise(r=>setTimeout(r,35));
async function until(fn){for(let i=0;i<80;i++){if(fn())return;await tick();}assert.ok(fn(),'Chat UI did not settle');}
function setup(theme,available=true){
 const errors=[],log=new VirtualConsole();log.on('jsdomError',e=>errors.push(e));log.on('error',e=>errors.push(e));
 const dom=new JSDOM('<html data-theme="'+theme+'"><body><div id="breadcrumbs"></div><main><div id="content"><input id="unsaved" value="Несохранённая карточка"></div><div id="actions"></div></main><div id="command-root"></div><div id="editor-content"></div><div id="editor-footer"></div><div id="account-content"></div><div id="prompt-content"></div></body></html>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:log});
 const w=dom.window,d=w.document;w.CSS={supports:()=>false,escape:v=>v};w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});w.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLElement.prototype.scrollTo=function(){};
 const requests=[];let connection=null;const thread={id:17,assistant_id:1,skill_path:'ai/skills/ai-technical-engineer/SKILL.md',skill_version:'fixture-version-1234',project_id:9,object_id:3};
 w.fetch=async(url,options={})=>{requests.push([url,options.body]);let value=[];if(url==='/api/v1/assistants')value=available?[{id:1,name:'Инженер'}]:[];
 if(url==='/api/v1/assistant/threads')value=options.method==='POST'?thread:[thread];
 if(url.startsWith('/api/v1/assistant/thread?'))value={thread,messages:[{id:42,sender:'assistant',text:'**Сохранённый ответ** <script>evil()</script>',status:'complete',tool_calls:[{call:{name:'objects-list',arguments:{}},result:{data:[]}}]}]};
 if(url==='/api/v1/assistant/provider'){connection=JSON.parse(options.body);value={saved:true,name:connection.name};}
 if(url==='/api/v1/assistant/admin')value={assistants:[],providers:connection?[connection.name]:available?['test']:[],provider_profiles:connection?[{name:connection.name,protocol:connection.protocol,base_url:connection.base_url,key_configured:true}]:[],corpora:['test'],tools:[{name:'objects-list',description:'Список объектов'}]};
 return {ok:true,json:async()=>value};};
 w.eval(bundle);return {dom,w,d,errors,requests};
}
for(const theme of ['light','dark'])test('Assistant sidebar and keyboard preserve workspace in '+theme,async()=>{
 const {dom,w,d,errors,requests}=setup(theme);let navigations=0;
 const config={userId:4,role:'viewer',workspaceId:'test',projectId:9,sectionCode:'ЭОМ',projectLabel:'Электроснабжение',objectId:3,getToken:()=> 'fixture-only'};
 w.ITDDesign.renderNav([['overview','Обзор','']],'overview',()=>navigations++,[],config);
 await until(()=>d.querySelector('[data-assistant-open]'));
 assert.ok(!d.querySelector('.workspace-search-button'));
 const shortcut=new w.KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true,cancelable:true});
 d.dispatchEvent(shortcut);assert.equal(shortcut.defaultPrevented,false);
 const nav=d.querySelector('[data-assistant-open]');assert.equal(nav.title,'Ассистент');assert.ok(nav.tabIndex>=0);
 const labels=[...d.querySelectorAll('.workspace-nav [title]')].map(n=>n.title);assert.equal(labels.indexOf('Ассистент'),labels.indexOf('Все объекты')+1);
 nav.focus();nav.click();await until(()=>d.querySelector('.assistant-panel'));
 assert.equal(d.activeElement.textContent,'Закрыть ассистента');assert.equal(d.activeElement.dataset.variant,'secondary');assert.ok(d.querySelector('.assistant-panel').textContent.includes('Раздел ЭОМ «Электроснабжение».'));assert.ok(!d.querySelector('.assistant-panel').textContent.includes(String.fromCharCode(183)));assert.equal(navigations,0);assert.equal(d.getElementById('unsaved').value,'Несохранённая карточка');
 [...d.querySelectorAll('.assistant-panel button')].find(b=>b.textContent==='Новый чат').click();await until(()=>d.querySelector('[role="log"]')?.textContent.includes('Сохранённый ответ'));
 assert.equal(d.querySelector('[role="log"] strong')?.textContent,'Сохранённый ответ');
 const picker=d.querySelector('.assistant-composer input[type=file]');
 Object.defineProperty(picker,'files',{value:[new w.File(['fixture'], 'акт.txt')]});
 picker.dispatchEvent(new w.Event('change',{bubbles:true}));
 await until(()=>d.querySelector('[aria-label="Вложения"]')?.textContent.includes('акт.txt'));
 const send=[...d.querySelectorAll('.assistant-composer button')].find(b=>b.textContent==='Отправить');
 assert.ok(send&&!send.disabled);send.click();
 await until(()=>requests.some(([url])=>url==='/api/v1/assistant/messages'));
 const sent=JSON.parse(requests.find(([url])=>url==='/api/v1/assistant/messages')[1]);
 assert.equal(sent.text,'');assert.deepEqual(sent.attachments,[{name:'акт.txt',data:'Zml4dHVyZQ=='}]);
 assert.equal(d.querySelector('.assistant-panel script'),null);assert.ok(d.querySelector('.assistant-panel textarea,.assistant-panel [contenteditable="true"]'));assert.ok(requests.some(([url])=>url==='/api/v1/assistant/threads'));
 d.querySelector('.assistant-panel').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await until(()=>!d.querySelector('.assistant-panel'));assert.equal(d.activeElement,nav);
 w.ITDDesign.renderNav([['overview','Обзор','']],'overview',()=>{},[],{...config,userId:5,workspaceId:'other'});await tick();assert.equal(d.querySelector('.assistant-panel'),null);
 assert.equal(errors.length,0,errors.map(e=>e.message).join('\n'));dom.window.close();
});
test('No available assistants hides nav; administrators configure from profile event',async()=>{
 const {dom,w,d,errors}=setup('light',false);w.ITDDesign.renderNav([],'objects',()=>{},[],{userId:1,role:'admin',workspaceId:'admin',getToken:()=> 'fixture'});await tick();await tick();assert.equal(d.querySelector('[data-assistant-open]'),null);
 d.dispatchEvent(new w.Event('itd:assistant-admin'));await until(()=>d.querySelector('[aria-label="Настройка ассистентов"]'));assert.ok(d.querySelector('.assistant-admin input'));assert.ok(d.querySelector('.assistant-admin').textContent.includes('Используется вся база знаний'));assert.equal(d.querySelector('.assistant-admin [aria-label="Разрешённые инструменты"]'),null);assert.equal(d.querySelector('.assistant-admin [aria-label="Корпуса знаний"]'),null);assert.equal(errors.length,0);dom.window.close();
});

for(const theme of ['light','dark'])test('Browser provider settings save and clear secret in '+theme,async()=>{
 const {dom,w,d,errors,requests}=setup(theme,false);
 w.ITDDesign.renderNav([],'objects',()=>{},[],{userId:1,role:'admin',workspaceId:'admin',getToken:()=> 'fixture'});
 await tick();await tick();d.dispatchEvent(new w.Event('itd:assistant-admin'));
 await until(()=>d.querySelector('input[type="password"]'));assert.equal(d.querySelector('.assistant-provider-settings details'),null);assert.ok(d.querySelector('.assistant-provider-settings .astryx-collapsible-trigger'));
 const field=label=>[...d.querySelectorAll('input')].find(n=>n.labels?.[0]?.textContent.includes(label));
 const fill=(label,value)=>{const input=field(label);assert.ok(input,label);Object.getOwnPropertyDescriptor(w.HTMLInputElement.prototype,'value').set.call(input,value);input.dispatchEvent(new w.Event('input',{bubbles:true}));};
 fill('Название подключения','own');fill('Адрес API','https://example.test/v1');fill('Ключ API','fixture-secret');
 await tick();const save=[...d.querySelectorAll('button')].find(b=>b.textContent==='Сохранить подключение');assert.equal(save.disabled,false);save.click();
 await until(()=>d.querySelector('.assistant-provider-settings')?.textContent.includes('Подключение сохранено'));
 const body=JSON.parse(requests.find(([url])=>url==='/api/v1/assistant/provider')[1]);assert.equal(body.api_key,'fixture-secret');assert.equal(body.name,'own');assert.equal(field('Ключ API').value,'');assert.ok(!d.querySelector('.assistant-panel').textContent.includes('fixture-secret'));
 assert.equal(d.querySelector('.assistant-panel').textContent.includes('перезапустите сервер'),false);
 assert.equal(errors.length,0,errors.map(e=>e.message).join('\n'));dom.window.close();
});
