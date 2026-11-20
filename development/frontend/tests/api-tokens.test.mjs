import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from '../dependencies.mjs';
const asset=name=>readFileSync(new URL(`../../../app/itd/web_assets/${name}`,import.meta.url),'utf8');
const tick=()=>new Promise(r=>setTimeout(r,0));

for(const theme of ['light','dark'])for(const role of ['viewer','admin'])test(`API tokens profile ${role} ${theme}: creation, one-time display, revoke`,async()=>{
 const dom=new JSDOM(`<html data-theme="${theme}"><body><form id="login-form"><input name="code"><button>Войти</button><p class="account-message"></p></form><button id="login-cancel"></button><button id="session-logout"></button><button id="account-open"></button><div id="content"></div><div id="prompt-content"></div></body></html>`,{url:'http://localhost/',runScripts:'outside-only'});
 const w=dom.window,d=w.document,calls=[],windows=new Map();
 const user={id:2,first_name:'Тест',last_name:'Тест',role};
 const rows=[{id:7,user_id:2,name:'<img src=x onerror=alert(1)>',created_at:100,expires_at:Date.now()/1000+3600,last_used_at:null,revoked_at:null}];
 w.$=s=>d.querySelector(s);w.esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 w.option=(v,t)=>`<option value="${v}">${w.esc(t)}</option>`;
 w.enhanceSelect=()=>{};let enhanced=0;w.enhanceDataTable=()=>{enhanced++;};w.title=name=>`<h1>${name}</h1>`;w.icon=()=>'';w.workspaceView='account';w.render=()=>{d.getElementById('content').innerHTML=w.accountPage();d.querySelectorAll('#account-page [data-account-panel="tokens"] table').forEach(table=>w.enhanceDataTable(table));};
 w.createWorkspaceDialog=(id,options={})=>{const result={open:args=>{result.args=args;args?.focus?.focus();},close:()=>options.onClose?.()};windows.set(id,result);return result;};
 w.api=async(route,data)=>{
  calls.push({route,data});
  if(route==='/api/admin')return {users:[user],settings:{database_path:'/tmp/test.db',itd_root:'/tmp/tree'}};
  if(route.endsWith('/tokens'))return rows;
  if(route.endsWith('/tokens/create'))return {id:8,token:'one-time-secret'};
  if(route.endsWith('/tokens/revoke')){rows[0].revoked_at=Date.now()/1000;return {ok:true};}
  throw Error('Unexpected request '+route);
 };
 w.token="";w.dirty=false;w.formDirty=false;
 w.eval(asset('journals.js').split('function journalValue')[0]+'\nwindow.journalTable=journalTable;');
 w.eval(asset('account.js')+'\ncurrentUser='+JSON.stringify(user)+';window.accountPage=accountPage;window.startAccount=startAccount;window.updateAccount=updateAccount;');
 w.startAccount();
 await w.updateAccount();
 assert.ok(enhanced);assert.equal(d.querySelector('[data-account-panel="tokens"] img'),null);
 assert.ok(d.querySelector('[data-account-panel="tokens"] table'));assert.equal(d.querySelector('input[name=name]').disabled,false);
 assert.ok(calls.some(c=>c.route===(role==='admin'?'/api/admin/tokens':'/api/account/tokens')));
 const form=d.querySelector('[data-account-action="token-create"]');
 form.elements.name.value='Новый';form.elements.expires_at.value='2030-01-02T12:00';
 form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick();
 const request=calls.find(c=>c.route.endsWith('/tokens/create'));
 assert.equal(request.data.name,'Новый');assert.equal(typeof request.data.expires_at,'number');
 assert.equal(d.querySelector('#issued-token').value,'one-time-secret');
 assert.equal(d.activeElement.id,'copy-token');
 assert.equal(w.sessionStorage.length,0);assert.equal(w.localStorage.length,0);
 windows.get('prompt-dialog').close();assert.equal(d.querySelector('#issued-token'),null);
 d.querySelector('[data-account-task="token-revoke"]').click();await tick();d.querySelector('#prompt-confirm').click();await tick();await tick();
 assert.ok(calls.some(c=>c.route===(role==='admin'?'/api/admin/tokens/revoke':'/api/account/tokens/revoke')&&c.data.id===7));
 assert.equal(d.querySelector('[data-account-task="token-revoke"]'),null);
 dom.window.close();
});

for(const count of [0,63])test(`token table uses common controls and footer with ${count} rows`,()=>{
 const dom=new JSDOM('<div id="content"><section data-token-panel></section></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window,d=w.document;
 w.esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 w.enhanceSelect=()=>{};
 for(const name of ['projectId','workspaceView','journalSection','resourcePanel','packagePanel'])w[name]='tokens';
 w.eval(asset('ui.js').slice(asset('ui.js').indexOf('function displayTableDate('),asset('ui.js').indexOf('function addTableFiller('))+'\nwindow.tableColumnType=tableColumnType;window.formatTableNumber=formatTableNumber;window.displayTableDate=displayTableDate;');
 w.eval(asset('journals.js').split('function journalValue')[0]+'\nwindow.journalTable=journalTable;');
 w.eval(asset('tables.js')+'\nwindow.enhanceDataTable=enhanceDataTable;');
 const panel=d.querySelector('[data-token-panel]');
 panel.innerHTML=w.journalTable(['Название','Состояние'],Array.from({length:count},(_,i)=>[`Токен ${i}`,'Действует']));
 const table=panel.querySelector('table');w.enhanceDataTable(table);
 assert.equal(panel.querySelectorAll('.data-table-footer').length,1);
 assert.equal(panel.querySelector('.table-filter-disclosure summary').textContent,'Фильтр');
 assert.ok(panel.querySelector('[data-table-control=search]'));assert.ok(panel.querySelector('[data-table-control=settings]'));
 w.enhanceDataTable(table);assert.equal(panel.querySelectorAll('.data-table-footer').length,1);
 if(count){assert.equal([...table.tBodies[0].rows].filter(r=>!r.hidden).length,50);panel.querySelector('[data-table-control=next]').click();assert.equal([...table.tBodies[0].rows].filter(r=>!r.hidden).length,13);}
 dom.window.close();
});
