import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';
const asset=name=>readFileSync(new URL('../../itd/web_assets/'+name,import.meta.url),'utf8');
const escape=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const context={act_num:'01',form_name:'Передача документации',context:{city:'Москва',rows:[{number:'1',name:'Рабочие чертежи',quantity:0}]},preview_fields:[{key:'city',label:'Город',group:'Объект и раздел'},{key:'rows',label:'Чертежи',kind:'table',group:'Таблицы и перечни',columns:[{key:'number',label:'№'},{key:'name',label:'Чертёж'},{key:'quantity',label:'Количество'}]}],table_headers:{rows:[[{label:'Документация',span:2,rowspan:1},{label:'Количество',span:1,rowspan:2}],[{label:'№',span:1},{label:'Название',span:1}]]},static_claims:['Соответствует проекту'],missing:[]};

test('viewer opens a document reader without creation, confirmation or editing controls',async()=>{
 for(const theme of ['light','dark']){
  const dom=new JSDOM(`<html data-theme="${theme}"><body><dialog id="editor-dialog"><div id="editor-content"></div></dialog></body></html>`,{runScripts:'outside-only'}),w=dom.window,d=w.document;
  w.esc=escape;w.currentUser={role:'viewer'};w.card=(title,body)=>`<section class="card"><h2>${escape(title)}</h2>${body}</section>`;
  let title,opens=0,requests=[];
  w.editorWindow={setTitle:value=>title=value};w.openEditor=()=>opens++;
  w.$=s=>d.querySelector(s);w.projectId=7;w.api=async path=>{requests.push(path);return context;};
  w.previewFieldLabel=f=>f.label;w.eval(asset('manual.js')+'\nwindow.previewAct=previewAct;window.previewActHtml=previewActHtml;window.previewValue=previewValue;');
  await w.previewAct(3);
  assert.equal(title,'Просмотр документа');assert.equal(opens,1);
  assert.deepEqual(requests,['/api/context?project_id=7&act_id=3']);
  assert.equal(d.querySelector('form'),null);
  assert.equal(d.querySelector('[data-final],[data-preview-draft],[data-preview-edit]'),null);
  assert.equal(d.querySelector('[data-action="cancel-entry"]').textContent,'Закрыть');
  const table=d.querySelector('[data-document-table] table');
  assert.ok(table);assert.equal(table.tHead.rows.length,2);
  assert.equal(table.tHead.rows[0].cells[0].colSpan,2);
  assert.equal(table.tHead.rows[0].cells[1].rowSpan,2);
  assert.equal(table.tBodies[0].rows[0].cells[2].textContent,'0');
  const empty=d.createElement('div');empty.innerHTML=w.previewValue([],context.preview_fields[1],context.table_headers.rows);
  assert.equal(empty.querySelector('table').tHead.rows.length,2);assert.equal(empty.querySelector('tbody td').colSpan,3);
  assert.doesNotMatch(d.querySelector('#editor-content').textContent,/Проверка и создание|Создайте DOCX|Сохранить подтверждение/);
  w.currentUser.role='editor';
  assert.match(w.previewActHtml(3,context),/data-preview-draft/);
  dom.window.close();
 }
});

test('source-document tables retain their merged headers and cells when decorated',()=>{
 const dom=new JSDOM('<div id="editor-content"><div class="table-scroll" data-document-table><table><thead><tr><th colspan="2">Документы</th></tr><tr><th>№</th><th>Название</th></tr></thead><tbody><tr><td>1</td><td>Чертёж</td></tr></tbody></table></div></div>',{runScripts:'outside-only'}),w=dom.window,d=w.document;
 const source=asset('ui.js');w.eval(source.slice(source.indexOf('function decorateDataTables('),source.indexOf('const tableObserver=')));
 const table=d.querySelector('table'),before=table.innerHTML;
 w.decorateDataTables();assert.equal(table.innerHTML,before);
 assert.equal(d.querySelector('.table-scroll').tabIndex,0);
 assert.equal(d.querySelector('.table-scroll').getAttribute('role'),'region');
 dom.window.close();
});

test('viewer restrictions are removed on role change without unlocking intrinsic readonly fields',async()=>{
 const dom=new JSDOM('<div id="content"><input id="editable"><input id="automatic" readonly><input id="object-search"><select id="choice"><option>A</option></select><select id="locked" disabled><option>B</option></select></div><div id="editor-content"></div><div id="editor-footer"></div><button id="account-open"></button><button id="session-logout"></button>',{runScripts:'outside-only'}),w=dom.window,d=w.document;
 w.$=s=>d.querySelector(s);w.createWorkspaceDialog=()=>({});w.eval(asset('account.js')+'\nwindow.setProfile=setProfile;');
 const profile=role=>({role,first_name:'Иван',last_name:'Иванов'});
 w.setProfile(profile('viewer'));
 assert.equal(d.querySelector('#editable').readOnly,true);assert.equal(d.querySelector('#choice').disabled,true);
 assert.equal(d.querySelector('#object-search').readOnly,false);
 d.querySelector('#editor-content').innerHTML='<input id="new-field">';
 await new Promise(resolve=>setTimeout(resolve,0));assert.equal(d.querySelector('#new-field').readOnly,true);
 w.setProfile(profile('editor'));
 assert.equal(d.querySelector('#editable').readOnly,false);assert.equal(d.querySelector('#choice').disabled,false);
 assert.equal(d.querySelector('#automatic').readOnly,true);assert.equal(d.querySelector('#locked').disabled,true);
 assert.equal(d.querySelector('#new-field').readOnly,false);assert.equal(d.querySelector('[data-read-only-note]'),null);
 d.querySelector('#editor-content').innerHTML='<input id="editor-field">';
 await new Promise(resolve=>setTimeout(resolve,0));assert.equal(d.querySelector('#editor-field').readOnly,false);
 dom.window.close();
});
