import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from '../dependencies.mjs';
const asset=name=>readFileSync(new URL('../../../app/itd/web_assets/'+name,import.meta.url),'utf8');
function fixture(theme='light'){
 const dom=new JSDOM(`<html data-theme="${theme}"><body><div id="editor-content"></div></body></html>`,{runScripts:'outside-only'}),w=dom.window;
 w.structuredClone=structuredClone;
 w.eval(`
 var $=s=>document.querySelector(s),esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;');
 var meta={document_roles:{first:'Заказчик',second:'Исполнитель'}},projectId=1,formDirty=false;
 var pdata={date_groups:{},form_bindings:{},forms:[{code:'TEST',fields:[{key:'city',label:'Город',kind:'reference',source:'object.city'},{key:'note',label:'Описание',kind:'literal',value:'Исходный текст'},{key:'first_person',kind:'signatory',role:'first',required:true},{key:'second_person',kind:'signatory',role:'second',required:true}]}],acts:[{id:1,act_type:'TEST',act_num:'Акт 1'}],act_statuses:[],attachments:[],form_roots:{object:{city:'Москва'}}};
 var cleanFieldLabel=v=>v,actRoles=()=>['first','second'],decorateSelects=()=>{},enhanceSelect=()=>{},icon=()=>'',actName=()=> 'Испытания',participantRoleLabel=r=>r;
 var option=(value,label,selected)=>'<option value="'+value+'" '+(value===selected?'selected':'')+'>'+label+'</option>';
 var representativeLabel=p=>p.fio,notice=text=>window.lastNotice=text,notifyWorkspace=notice;
 var uploadZone=(id,label)=>'<div class="file-drop" data-upload-target="'+id+'"><input type="file" id="'+id+'" aria-label="'+label+'"></div>';
 `);
 w.eval(asset('act-fields.js')+'\n'+asset('field-functions.js')+'\n'+asset('document-versions.js')+`
 documentVersionState={aid:1,selected:11,required_roles:['first','second'],candidates:{first:[{id:1,fio:'Первый'}],second:[{id:2,fio:'Второй'}]},versions:[{id:11,ordinal:1,revision:1,card:{fields:[],date_signed:null},signers:[{role:'first',person_id:1,signed:false},{role:'second',person_id:2,signed:false}]}],binding_sources:[{source:'object.city',group:'Объект',label:'Город',value:'Москва'},{source:'project.name',group:'Раздел',label:'Название раздела',value:'Раздел 1'}]};
 renderDocumentVersion();
 window.openDocumentVersions=openDocumentVersions;window.saveDocumentVersion=saveDocumentVersion;window.collect=collectVersionDraft;window.model=()=>documentVersionState;window.renderCard=renderDocumentVersion;
 `);
 return dom;
}
test('signed upload appears after the last signature in either order and retains the chosen file',()=>{
 for(const order of [[0,1],[1,0]]){
  const dom=fixture(),d=dom.window.document;
  assert.ok(d.querySelector('#signed-document-section').hidden);
  d.querySelector(`[data-signature-toggle="${order[0]}"]`).click();
  assert.ok(d.querySelector('#signed-document-section').hidden);
  d.querySelector(`[data-signature-toggle="${order[1]}"]`).click();
  assert.equal(d.querySelector('#signed-document-section').hidden,false);
  assert.equal(d.querySelector('#signed-document-file').getAttribute('aria-required'),'true');
  const file=new dom.window.File(['signed'],'signed.pdf',{type:'application/pdf'});
  Object.defineProperty(d.querySelector('#signed-document-file'),'files',{value:[file],configurable:true});
  d.querySelector('#signed-document-file').dispatchEvent(new dom.window.Event('change',{bubbles:true}));
  assert.equal(dom.window.model().pendingSignedFile,file);
  d.querySelector('[data-signature-toggle="0"]').click();assert.ok(d.querySelector('#signed-document-section').hidden);
  d.querySelector('[data-signature-toggle="0"]').click();assert.match(d.querySelector('#signed-document-name').textContent,/signed.pdf/);
  const buttons=[...d.querySelectorAll('.ux-form-actions button')].map(b=>b.textContent.trim());
  assert.deepEqual(buttons,['Сохранить','Обновить на диске','Скачать документ','Удалить версию','Отмена']);
  assert.equal(d.querySelector('[data-delete-document-version]').disabled,true);
  dom.window.close();
 }
});
test('f preserves existing bindings, applies a source only on the second click and does not change other fields in either theme',()=>{
 for(const theme of ['light','dark']){
  const dom=fixture(theme),w=dom.window,d=w.document;
  assert.equal(d.querySelector('[data-document-field="city"] textarea').value,'Москва');
  const city=d.querySelector('[data-document-field="city"]');city.querySelector('button').click();
  city.querySelector('button').click();
  assert.equal(w.collect().card.fields.find(f=>f.key==='city').source,'object.city');
  const note=d.querySelector('[data-document-field="note"]');note.querySelector('textarea').value='Не потерять';note.querySelector('button').click();
  assert.throws(()=>w.collect(),/Подтвердите/);
  note.querySelector('select').value='project.name';note.querySelector('button').click();
  let fields=w.collect().card.fields;
  assert.equal(fields.find(f=>f.key==='note').source,'project.name');assert.equal(fields.find(f=>f.key==='note').binding_explicit,true);
  assert.equal(fields.find(f=>f.key==='city').source,'object.city');
  const bound=d.querySelector('[data-document-field="note"]');bound.querySelector('button').click();bound.querySelector('select').value='__manual__';bound.querySelector('button').click();
  fields=w.collect().card.fields;assert.equal(fields.find(f=>f.key==='note').kind,'literal');assert.ok(fields.find(f=>f.key==='note').binding_explicit);
  dom.window.close();
 }
});

test('table cell f saves a source in that cell without adding a scalar field or changing adjacent values',()=>{
 const dom=fixture(),w=dom.window,d=w.document;
 w.model().versions[0].card.fields.push({key:'readings',kind:'table',value:[{pressure:0,note:'Сохранить'}],fields:[{key:'pressure',label:'Давление',kind:'reference',source:'item.pressure',input_type:'number'},{key:'note',label:'Примечание',kind:'reference',source:'item.note'}]});w.renderCard();
 const cell=d.querySelector('[data-table-column="note"]');cell.querySelector('button').click();
 cell.querySelector('select').value='object.city';cell.querySelector('button').click();
 const fields=w.collect().card.fields,table=fields.find(f=>f.key==='readings');
 assert.equal(table.value[0].pressure,0);assert.equal(table.value[0].note.__itd_source,'object.city');
 assert.equal(fields.filter(f=>f.key.startsWith('table_cell_')).length,0);
 dom.window.close();
});

test('released fields show saved values and an unselected optional signer does not block the signed upload',()=>{
 const dom=fixture(),w=dom.window,d=w.document;
 const version=w.model().versions[0];
 version.signers.push({role:'optional',person_id:null,signed:false});version.signers[0].signed=true;version.signers[1].signed=true;
 w.renderCard();assert.equal(d.querySelector('#signed-document-section').hidden,false);
 version.release_id=4;version.snapshot={city:'Город в сохранённой версии',note:'Сохранённое описание'};
 w.renderCard();
 assert.equal(d.querySelector('[data-document-field="city"] textarea').value,'Город в сохранённой версии');
 assert.equal(d.querySelector('[data-document-field="city"] [data-field-function]').disabled,true);
 dom.window.close();
});


test('function picker closes without a selection and preserves manual text in either theme',()=>{
 for(const theme of ['light','dark']){
  const dom=fixture(theme),w=dom.window,d=w.document;
  let row=d.querySelector('[data-document-field="note"]');
  row.querySelector('textarea').value='Текст перед переключением';
  row.querySelector('button').click();
  assert.equal(row.querySelector('select').value,'');
  row.querySelector('button').click();
  row=d.querySelector('[data-document-field="note"]');
  assert.equal(row.querySelector('textarea').value,'Текст перед переключением');
  assert.equal(row.querySelector('select'),null);
  assert.equal(row.querySelector('button').getAttribute('aria-pressed'),'false');
  assert.ok(row.querySelector('button svg[aria-hidden="true"]'));
  assert.equal(d.activeElement,row.querySelector('button'));
  assert.equal(w.collect().card.fields.find(f=>f.key==='note').value,'Текст перед переключением');
  dom.window.close();
 }
});

test('adding a text table row focuses its textarea and preserves adjacent rows',()=>{
 const dom=fixture(),w=dom.window,d=w.document;
 w.model().versions[0].card.fields.push({key:'notes',kind:'table',value:[{note:'Существующая строка'}],fields:[{key:'note',label:'Примечание',kind:'reference',source:'item.note'}]});w.renderCard();
 const errors=[];w.addEventListener('error',e=>errors.push(e.error));
 d.querySelector('[data-version-table-add]').click();
 assert.equal(errors.length,0);const rows=d.querySelectorAll('[data-version-table] tbody tr');
 assert.equal(rows.length,2);assert.equal(rows[0].querySelector('textarea').value,'Существующая строка');
 assert.equal(d.activeElement,rows[1].querySelector('textarea'));
 rows[1].querySelector('textarea').value='Новая строка';
 assert.deepEqual(Array.from(w.collect().card.fields.find(f=>f.key==='notes').value,r=>r.note),['Существующая строка','Новая строка']);
 dom.window.close();
});

test('switching a linked field to manual input retains its displayed value',()=>{
 const dom=fixture(),w=dom.window,d=w.document;
 const city=d.querySelector('[data-document-field="city"]');city.querySelector('button').click();city.querySelector('select').value='__manual__';city.querySelector('button').click();
 const input=d.querySelector('[data-document-field="city"] textarea');
 assert.equal(input.value,'Москва');assert.equal(input.readOnly,false);
 input.value='Казань';assert.equal(w.collect().card.fields.find(f=>f.key==='city').value,'Казань');
 dom.window.close();
});

test('an empty optional signer does not require a signature date when saving completed signatures',async()=>{
 const dom=fixture(),w=dom.window,d=w.document;
 const version=w.model().versions[0];version.signed_attachment_id=42;
 version.signers.forEach(s=>{s.signed=true;s.signed_date='2026-11-03';});
 version.signers.push({role:'optional',person_id:null,signed:false});w.renderCard();
 let saved;
 w.api=async(path,body)=>{assert.equal(path,'/api/versions/save');saved=body;return {versions:[version]};};
 w.reloadJournalWorkspace=async()=>{};w.loadProject=async()=>{};w.render=()=>{};w.toast=()=>{};
 w.eval('pdata.participant_choices={people:window.model().candidates,organizations:{}}');
 await w.saveDocumentVersion();
 assert.equal(saved.signers.length,2);assert.ok(saved.signers.every(s=>s.person_id&&s.signed_date));
 dom.window.close();
});

test('switching an automatic date to manual retains a valid ISO calendar value',()=>{
 const dom=fixture(),w=dom.window,d=w.document;
 w.model().versions[0].card.date_signed='2026-11-03';
 w.model().versions[0].card.fields.push({key:'day',label:'Дата',kind:'reference',source:'act.date_signed',value_type:'date',format:'date_ru'});w.renderCard();
 const row=d.querySelector('[data-document-field="day"]');assert.equal(row.querySelector('textarea').value,'03.11.2026');
 row.querySelector('button').click();row.querySelector('select').value='__manual__';row.querySelector('button').click();
 assert.equal(d.querySelector('[data-document-field="day"] input').value,'2026-11-03');
 assert.equal(w.collect().card.fields.find(f=>f.key==='day').value,'2026-11-03');
 dom.window.close();
});


test('empty version list offers an explicit card action in both themes',async()=>{
 for(const theme of ['light','dark']){
  const dom=fixture(theme),w=dom.window,d=w.document,calls=[];
  w.openEditor=()=>{};w.editorWindow={setTitle:()=>{}};
  w.api=async(path)=>{calls.push(path);return {versions:[]};};
  await w.openDocumentVersions(1);
  assert.deepEqual(calls,['/api/versions/list']);
  const button=d.querySelector('[data-version-ensure]');
  assert.equal(button.textContent,'Создать карточку');
  assert.ok(d.querySelector('[role="status"]').textContent.includes('ещё не создана'));
  button.focus();assert.equal(d.activeElement,button);
  assert.equal(d.querySelector('#document-version-form'),null);
  dom.window.close();
 }
});

test('card initialization writes only after the explicit button action',async()=>{
 const dom=fixture(),w=dom.window,d=w.document;
 const versions=w.model().versions;
 w.model().versions=[];w.model().selected=null;w.renderCard();
 const calls=[];
 w.api=async(path)=>{calls.push(path);return {versions};};
 let pending;w.action=fn=>{pending=fn();};
 d.querySelector('[data-version-ensure]').click();await pending;
 assert.deepEqual(calls,['/api/versions/ensure']);
 assert.ok(d.querySelector('#document-version-form'));
 dom.window.close();
});
