'use strict';
let documentVersionState=null;
const otherSignerRoles=['other_1','other_2','other_3'];
function versionEffectiveFields(a,version){const definition=pdata.forms.find(f=>f.code===a.act_type),base=(definition?.ui_fields||definition?.fields||[]).map(f=>a.act_type.startsWith('TPL_')&&f.kind==='literal'?{...f,expression:true}:f),overrides=version.card.fields||[];const fields=base.map(f=>{const override=overrides.find(x=>x.key===f.key);return override?{...Object.fromEntries(Object.entries(f).filter(([key])=>!['kind','source','value','role','template','presentation'].includes(key))),...override}:f;}).concat(overrides.filter(f=>!base.some(x=>x.key===f.key)));
 return normalizeFormFields(a.act_type,fields);}
async function openDocumentVersions(aid){
 const result=await api('/api/versions/list',{project_id:projectId,act_id:aid});
 documentVersionState={...result,aid,selected:result.versions.at(-1)?.id};
 openEditor('manual');editorWindow.setTitle('Изменить документ');renderDocumentVersion();
 if(!result.versions.length)window.requestAnimationFrame?.(()=>$('#editor-content [data-version-ensure]')?.focus());
}
function renderDocumentVersion(){
 const model=documentVersionState,a=pdata.acts.find(a=>a.id===model.aid),version=model.versions.find(v=>v.id===model.selected),last=model.versions.at(-1);
 if(!version){
  $('#editor-content').innerHTML='<p role="status">Карточка документа ещё не создана. В карточке можно редактировать сведения, вести версии и отмечать подписи.</p><div class="toolbar"><button type="button" data-version-ensure>Создать карточку</button></div>';
  return;
 }
 const signed=pdata.act_statuses.some(status=>status.act_id===a.id&&status.state==='signed');
 const locked=version.id!==last.id||signed;
 const contentLocked=locked||!!version.release_id;
 const fields=versionEffectiveFields(a,version),required=documentRequiredRoles(fields);model.required_roles=required;
 const formRoles=actRoles({fields}).filter(role=>!otherSignerRoles.includes(role));
 const signers=version.signers.map(s=>({...s}));
 if(!contentLocked)for(const role of formRoles){
  if(signers.some(s=>s.role===role))continue;
  const candidates=model.candidates[role]||[];
  signers.push({role,person_id:candidates.length===1?candidates[0].id:null,signed:false});
 }
 const signingDate=fields.find(isDocumentDateField),canonicalDate=a.act_type.startsWith('TPL_')&&signingDate;
 const legacyDate=(version.card.fields||[]).find(isDocumentDateField)?.value;
 const savedDate=contentLocked&&canonicalDate?version.snapshot?.date:null;
 const date=version.card.date_signed||(canonicalDate?calendarInputValue(legacyDate||savedDate):'');
 const formattedDate=!!savedDate&&!/^\d{4}-\d{2}-\d{2}$/.test(date);
 const scalars=documentScalarFields(fields,a.act_type);
 const automaticTables=contentLocked&&version.snapshot?fields.filter(field=>field.kind==='table'&&!editableVersionTable(field)&&!['hidden','not_applicable'].includes(field.state)):[];
 $('#editor-content').innerHTML=`<section class="workspace-stack document-version-nav">
  <h3>Версии</h3>
  <nav class="version-nav" aria-label="Версии документа">${model.versions.map(v=>`<button class="secondary" type="button" data-document-version="${v.id}" aria-current="${v.id===version.id}" aria-label="Версия ${v.ordinal}">${v.ordinal}</button>`).join('')}<button class="secondary" type="button" data-version-add aria-label="Создать следующую версию">+</button></nav>
 </section>
 <form id="document-version-form" data-version="${version.id}">
  <section class="preview-section workspace-stack">
   <h3 id="version-information-title" tabindex="-1">Основная информация</h3><p>${esc(a.act_num)} «${esc(actName(a))}»</p>
   <div class="grid">
    <label class="field"><span>Название файла</span><input name="filename_title" value="${esc(version.card.filename_title||a.act_num.replace(/[<>:"/\\|?*\x00-\x1f]/g,'_'))}" ${contentLocked?'disabled':''}></label>
    <label class="field"><span>Дата подписания${canonicalDate&&signingDate.required?' *':''}</span><input type="${formattedDate?'text':'date'}" name="date_signed" value="${esc(formattedDate?savedDate:date)}" ${contentLocked?'disabled':''}></label>
    <label class="field wide"><span>Комментарий</span><textarea name="work_description" ${contentLocked?'disabled':''}>${esc(version.card.work_description||'')}</textarea></label>
   </div>
   ${participantRoleChoosers(fields,contentLocked)}
  </section>
  ${organizationSelects(fields,version.card.organizations||{},model.organization_candidates||{},contentLocked)}
  ${scalars.length?`<section class="preview-section workspace-stack"><h3>Сведения документа</h3><div class="document-scalar-fields">${scalars.map(f=>functionField(contentLocked&&version.snapshot&&Object.hasOwn(version.snapshot,f.key)?{...f,_display_value:version.snapshot[f.key]}:f,contentLocked,'version',versionFieldRoots(version,null))).join('')}</div></section>`:''}
  ${versionTables(fields,model.table_headers||{},contentLocked,version.snapshot||{})}
  ${automaticTables.length?`<section class="preview-section workspace-stack"><h3>Автоматические таблицы и перечни</h3>${automaticTables.map(f=>`<h4>${esc(f.label||f.key)}</h4>${previewValue(version.snapshot[f.key],{columns:f.fields},model.table_headers?.[f.key]||[])}`).join('')}</section>`:''}
  <section class="preview-section workspace-stack" aria-labelledby="version-signers-title">
   <h3 id="version-signers-title" tabindex="-1">Подписанты</h3>
   ${!locked?'<p class="hint">Укажите даты подписей и сохраните карточку. Для завершения подписания загрузите подписанный документ.</p>':''}
   <div data-version-signers></div>
  </section>
  <section class="preview-section" id="signed-document-section" hidden>
   <h3>Подписанный документ</h3>
   ${!locked?uploadZone('signed-document-file','Выбрать подписанный документ',{accept:'.pdf,.docx,.doc,.png,.jpg,.jpeg'}):''}
   <p id="signed-document-name" class="hint"></p>${version.signed_attachment_id?'<button type="button" class="secondary" data-download-signed>Скачать подписанный документ</button>':''}
  </section>
  ${locked?'<p class="hint">Сохранена карточка этой версии. Для изменений создайте следующую версию кнопкой «+».</p>':''}
  <div class="ux-form-actions">${!locked?'<button type="submit">Сохранить</button>':''}${version.attachment_id||version.release_id||version.id===last.id?`<button type="button" class="secondary" data-regenerate-document ${version.attachment_id&&!version.release_id?'disabled title="Загруженный оригинал не создаётся из шаблона"':''}>Обновить на диске</button><button type="button" class="secondary" data-download-document>${icon('download')}Скачать документ</button>`:''}<button type="button" class="secondary danger" data-delete-document-version ${model.versions.length===1?'disabled title="Нельзя удалить единственную версию"':''}>Удалить версию</button><button type="button" class="secondary" data-action="cancel-entry">Отмена</button></div>
 </form>`;
 model.signerContext={fields,formRoles,locked,contentLocked,custom:a.act_type.startsWith('TPL_')};
 model.draftSigners=signers;
 model.signerBindings=null;
 refreshVersionSigners();
 updateFunctionValues($('#document-version-form'),versionFieldRoots(version));
 decorateSelects();
}
function versionDraftSigners(form){
 return documentVersionState.draftSigners.map((s,i)=>{
  const person=form.elements.namedItem('person_'+i),date=form.elements.namedItem('signed_date_'+i);
  return {...s,person_id:person&&!person.disabled?Number(person.value)||null:s.person_id,
   signed_date:date&&!date.disabled?date.value||null:s.signed_date};
 });
}
function refreshVersionSigners(){
 const model=documentVersionState,form=$('#document-version-form');
 if(!form||!model.signerContext)return;
 const {fields,formRoles,locked,contentLocked,custom}=model.signerContext;
 const sources=model.binding_sources||pdata.binding_sources||[];
 const ids=new Set(sources.filter(item=>item.source.startsWith('records.signatories.')).map(item=>Number(item.source.split('.')[2].slice(1))));
 const directory=(pdata.journals?.directory?.people||[]).filter(person=>ids.has(person.id));
 const links=custom?documentRepresentativeLinks(form,fields,directory):new Map();
 const fingerprint=JSON.stringify([...links]);
 if(model.signerBindings===fingerprint)return;
 const draft=versionDraftSigners(form);
 const signers=contentLocked?draft:draft.filter(s=>!s.role.startsWith('representative_'));
 const pending=[...(links.get(null)||[])];
 if(!contentLocked)for(const [id,labels] of links){
  if(id===null)continue;
  const person=directory.find(p=>p.id===id);
  if(!person){pending.push(...labels);continue;}
  const role='representative_'+id,existing=draft.find(s=>s.role===role);
  signers.push(existing||{role,person_id:id,person,signed:false,signed_date:null});
 }
 const v=model.versions.find(v=>v.id===model.selected);
 model.pendingRepresentatives=!!pending.length||(contentLocked&&!!v.snapshot?._representative_links_pending);
 model.draftSigners=signers;
 model.signerBindings=fingerprint;
 const host=form.querySelector('[data-version-signers]');
 host.innerHTML=signers.map((s,i)=>{
  const linked=s.role.startsWith('representative_');
  const label=linked?(links.get(s.person_id)||[]).join(', ')||'Представитель из шаблона':participantRoleLabel(s.role,fields);
  const orgId=v.card.organizations?.[s.role],historical=s.person;
  const people=(model.candidates?.[s.role]||[]).filter(p=>!orgId||p.org_id===Number(orgId));
  const options=locked&&historical?[historical]:[...people];
  if(historical&&!options.some(p=>p.id===s.person_id))options.push(historical);
  const person=linked?`<div class="version-linked-person"><strong>${esc(label)}</strong><span>${esc(representativeLabel(historical))}</span></div>`:
   `<label class="field"><span>${esc(label)}${model.required_roles.includes(s.role)?' *':''}</span><select name="person_${i}" ${contentLocked?'disabled':''}><option value="">Выберите представителя…</option>${options.map(p=>option(p.id,representativeLabel(p),s.person_id)).join('')}</select></label>`;
  return `<div class="version-signer" data-signer-row="${i}">${person}<div class="signer-controls">
   <label class="field"><span>Дата подписи</span><input type="date" name="signed_date_${i}" aria-label="Дата подписи: ${esc(label)}" value="${esc(s.signed_date||'')}" ${locked?'disabled':''}></label>
   <button type="button" class="secondary signature-toggle" data-preview-blocked="${locked}" data-signature-toggle="${i}" aria-label="Подпись: ${esc(label)}" aria-pressed="${!!s.signed}" ${locked?'disabled':''}>${s.signed?'Подписан':'Не подписан'}</button>
   ${!contentLocked&&!linked&&!formRoles.includes(s.role)?`<button class="ghost danger" type="button" data-signer-remove="${i}" aria-label="Убрать подписанта">Убрать</button>`:''}
  </div></div>`;
 }).join('')+(pending.length?`<p class="hint" role="status">Укажите представителя в полях: ${esc([...new Set(pending)].join(', '))}.</p>`:model.pendingRepresentatives?'<p class="hint" role="status">В этой версии есть поля без выбранного представителя.</p>':signers.length?'':'<p class="hint">В документе нет выбранных подписантов.</p>');
 host.querySelectorAll('select').forEach(enhanceSelect);
 updateSignedDocumentSection();
}
function documentRepresentativeLinks(form,fields,directory){
 const links=new Map();
 function add(identity,label){
  const id=identity?Number(identity.replace(/^r/,'')):null;
  if(!links.has(id))links.set(id,[]);
  if(!links.get(id).includes(label))links.get(id).push(label);
 }
 function visit(field,value,label){
  if(field.state==='hidden'||field.state==='not_applicable')return;
  const reference=/^records\.signatories\.(r[0-9]+)\.\w+$/.exec(field.source||'');
  if(reference)add(reference[1],label);
  for(const [,table,identity] of String(value??'').matchAll(dbToken)){
   if(table==='signatories')add(identity,label);
  }
 }
 for(const field of fields){
  if(field.state==='hidden'||field.state==='not_applicable'||isDocumentDateField(field))continue;
  if(field.kind==='table'&&field.db_table==='signatories'){
   for(const column of field.fields){
    if(column.state!=='hidden'&&column.state!=='not_applicable'&&column.source?.startsWith('item.')){
     for(const person of directory)add(String(person.id),column.label||column.key);
    }
   }
  }
 }
 for(const row of form.querySelectorAll('[data-document-field]')){
  const field=JSON.parse(row.dataset.fieldDefinition);
  const input=row.querySelector('.document-function-control :is(input,textarea):not(.smart-input)');
  visit(field,input&&!input.disabled?input.value:field.value,field.label||field.key);
 }
 return links;
}
function collectVersionDraft(){
 const m=documentVersionState,v=m.versions.find(v=>v.id===m.selected),form=$('#document-version-form'),fd=new FormData(form);
 const a=pdata.acts.find(a=>a.id===m.aid),fields=structuredClone(v.release_id?v.card.fields:versionEffectiveFields(a,v));
 for(const field of collectFunctionFields(form)){const at=fields.findIndex(f=>f.key===field.key);if(at<0)fields.push(field);else fields[at]=field;}
 for(const table of form.querySelectorAll('[data-version-table]')){
  const field=fields.find(f=>f.key===table.dataset.versionTable);
  if(table.dataset.locked==='true')continue;
  field.value=[...table.querySelectorAll('tbody tr')].map(row=>Object.fromEntries(
   [...row.querySelectorAll('[data-table-column]')].map(input=>[input.dataset.tableColumn,
    collectFunctionTableCell(input)])));
 }
 return {card:{...v.card,fields,organizations:form.querySelectorAll('[data-organization-role]:not(:disabled)').length?selectedActOrganizations(form):(v.card.organizations||{}),filename_title:fd.has('filename_title')?(fd.get('filename_title')||null):v.card.filename_title,date_signed:fd.has('date_signed')?(fd.get('date_signed')||null):v.card.date_signed},work_description:fd.has('work_description')?(fd.get('work_description')||null):v.card.work_description,signers:versionDraftSigners(form)};
}
function retainVersionDraft(){
 const model=documentVersionState,version=model.versions.find(v=>v.id===model.selected);
 const draft=collectVersionDraft();
 version.card={...draft.card,work_description:draft.work_description};
 version.signers=draft.signers;
 return version;
}
async function saveDocumentVersion(){
 const model=documentVersionState,version=model.versions.find(v=>v.id===model.selected),draft=collectVersionDraft();
 if(draft.signers.some(s=>s.signed&&!s.person_id))throw Error('Выберите подписанта перед отметкой подписания.');
 const completed=versionSignaturesComplete(draft.signers);
 if(completed){
  if(draft.signers.some(s=>s.person_id&&!s.signed_date))throw Error('Укажите даты всех подписей.');
  if(!version.signed_attachment_id&&!model.pendingSignedFile)throw Error('Загрузите подписанный документ.');
 }
 draft.signers=draft.signers.filter(s=>s.person_id);
 if(completed&&model.pendingSignedFile){
  const uploaded=await uploadFile(model.pendingSignedFile,'other');
  draft.signed_attachment_id=uploaded.id;
 }else draft.signed_attachment_id=version.signed_attachment_id;

 const result=await api('/api/versions/save',{project_id:projectId,act_id:model.aid,id:version.id,revision:version.revision,...draft});
 model.versions=result.versions;model.pendingSignedFile=null;
 formDirty=false;
 await reloadJournalWorkspace();
 await loadProject(projectId);
 model.candidates=pdata.participant_choices.people;
 model.organization_candidates=pdata.participant_choices.organizations;
 render();
 renderDocumentVersion();
 toast(pdata.act_statuses.some(status=>status.act_id===model.aid&&status.state==='signed')?'Документ подписан':'Версия сохранена');
}
async function createDocumentVersion(){
 if(formDirty)throw Error('Сохраните изменения перед созданием версии.');
 const model=documentVersionState,last=model.versions.at(-1);
 const result=await api('/api/versions/create',{project_id:projectId,act_id:model.aid,expected:{id:last.id,revision:last.revision}});
 model.versions=result.versions;
 model.selected=model.versions.at(-1).id;
 await loadProject(projectId);
 render();
 renderDocumentVersion();
}
function addVersionTableRow(table){
 if(table.closest('#act-form')){
  const definition=actForms().find(f=>f.code===$('#act-type').value);
  const field=actFieldDefinitions(definition).find(f=>f.key===table.dataset.versionTable);
  const body=table.querySelector('tbody');
  body.insertAdjacentHTML('beforeend',versionTableRow(field,{},false));
  formDirty=true;focusVersionTableRow(body.lastElementChild);return;
 }
 const model=documentVersionState;
 const act=pdata.acts.find(a=>a.id===model.aid);
 const version=model.versions.find(v=>v.id===model.selected);
 const field=versionEffectiveFields(act,version).find(f=>f.key===table.dataset.versionTable);
 const body=table.querySelector('tbody');
 body.insertAdjacentHTML('beforeend',versionTableRow(field,{},false));
 formDirty=true;
 focusVersionTableRow(body.lastElementChild);
 refreshVersionSigners();
}
function focusVersionTableRow(row){row.querySelector('textarea:not(:disabled),input:not(:disabled):not([type=hidden]),[role=combobox]')?.focus();}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
 if(b.hasAttribute('data-version-table-add')){
  const table=b.closest('[data-version-table]');
  if(table.dataset.locked==='true'){
   action(async()=>{
    const key=table.dataset.versionTable;
    await createDocumentVersion();
    const draft=$('#editor-content').querySelector(`[data-version-table="${CSS.escape(key)}"][data-locked="false"]`);
    if(!draft)throw Error('Таблица недоступна в новой версии.');
    addVersionTableRow(draft);
   });
  }else addVersionTableRow(table);
 }
 if(b.hasAttribute('data-version-table-remove')){b.closest('tr').remove();formDirty=true;refreshVersionSigners();}
 if(b.dataset.documentVersion){if(formDirty){notice('Сохраните изменения перед выбором другой версии.');return;}documentVersionState.pendingSignedFile=null;documentVersionState.selected=Number(b.dataset.documentVersion);renderDocumentVersion();}
 if(b.hasAttribute('data-version-add'))action(createDocumentVersion);
 if(b.hasAttribute('data-signature-toggle')){
  const index=Number(b.dataset.signatureToggle),signer=documentVersionState.draftSigners[index];
  signer.signed=!signer.signed;
  b.setAttribute('aria-pressed',String(signer.signed));
  b.textContent=signer.signed?'Подписан':'Не подписан';
  const date=b.form.elements.namedItem('signed_date_'+index);
  if(signer.signed&&!date.value)date.focus();
  formDirty=true;updateSignedDocumentSection();
 }
 if(b.dataset.signerRemove!==undefined){
  const version=retainVersionDraft();
  version.signers.splice(Number(b.dataset.signerRemove),1);
  renderDocumentVersion();
  $('#version-signers-title')?.focus();
  formDirty=true;
 }
 if(b.hasAttribute('data-regenerate-document'))action(regenerateDocumentVersion);
 if(b.hasAttribute('data-delete-document-version'))action(deleteDocumentVersion);
 if(b.hasAttribute('data-download-signed'))action(downloadSignedDocument);
 if(b.hasAttribute('data-download-document'))action(downloadDocumentVersion);
});
for(const type of ['input','change'])document.addEventListener(type,e=>{if(e.target.closest('#document-version-form')){formDirty=true;if(e.target.closest('[data-document-field]'))refreshVersionSigners();}});

function openUploadedAct(){
 if(!projectId){notice('Выберите рабочий раздел.');return;}
 openEditor('manual');editorWindow.setTitle('Загрузить документ');
 $('#editor-content').innerHTML=`<form id="uploaded-act-form"><div class="grid"><label class="field wide"><span>Форма документа *</span><select name="act_type" required><option value="">Выберите форму…</option>${actFormOptions()}</select></label><label class="field wide"><span>Название файла в карточке</span><input name="filename_title"></label><label class="field"><span>Дата документа</span><input name="date_signed" type="date"></label></div>${uploadZone('uploaded-act-file','Выбрать документ',{accept:'.pdf,.docx,.doc,.xlsx,.xls,.png,.jpg,.jpeg'})}<p class="hint" id="uploaded-act-filename">Файл ещё не выбран. Оригинал сохранится в архиве и будет связан с карточкой акта. Отметки подписания внесите в версии документа.</p><div class="ux-form-actions"><button type="submit">Загрузить</button><button type="button" class="secondary" data-action="cancel-entry">Отмена</button></div></form>`;
 decorateSelects();
}
async function saveUploadedAct(form){
 const file=form.querySelector('input[type=file]').files[0];if(!file)throw Error('Выберите документ для загрузки.');
 const fd=new FormData(form),uploaded=await uploadFile(file,'other');
 const result=await api('/api/act',{project_id:projectId,act_type:fd.get('act_type'),date_signed:fd.get('date_signed')||null,attachment_id:uploaded.id,fields:[]});
 if(fd.get('filename_title'))await api('/api/action',{project_id:projectId,action:'update',data:{entity:'acts',id:result.act_id,changes:{filename_title:fd.get('filename_title')},expected:{filename_title:null}}});
 formDirty=false;closeEditor(true);await loadProject(projectId);render();await openDocumentVersions(result.act_id);toast('Документ загружен и связан с актом');
}
document.addEventListener('change',e=>{if(e.target.id==='uploaded-act-file'){document.getElementById('uploaded-act-filename').textContent=e.target.files[0]?.name||'Файл ещё не выбран';formDirty=true;}});

document.addEventListener('change',e=>{
 const el=e.target;if(!el.closest('#document-version-form'))return;
 if(el.dataset.participantRole&&el.value){
  retainVersionDraft();const m=documentVersionState,v=m.versions.find(v=>v.id===m.selected),a=pdata.acts.find(a=>a.id===m.aid),fields=versionEffectiveFields(a,v);
  const oldRoles=new Set(fields.filter(f=>f.role_slot===el.dataset.participantRole&&f.kind==='signatory').map(f=>f.role));
  v.card.fields=applyParticipantRole(fields,el.dataset.participantRole,el.value);v.signers=v.signers.filter(s=>!oldRoles.has(s.role));v.card.organizations=Object.fromEntries(Object.entries(v.card.organizations||{}).filter(([role])=>!oldRoles.has(role)&&role!==el.dataset.participantRole));
  renderDocumentVersion();formDirty=true;
 }
 if(el.dataset.organizationRole){retainVersionDraft();const m=documentVersionState,v=m.versions.find(v=>v.id===m.selected),role=el.dataset.organizationRole;v.card.organizations={...(v.card.organizations||{}),[role]:Number(el.value)||null};v.signers=v.signers.map(s=>s.role===role&&s.person?.org_id!==Number(el.value)?{...s,person_id:null,person:null,signed:false,signed_date:null}:s);renderDocumentVersion();formDirty=true;}
});

function versionTableColumns(field){
 return field.fields.filter(column=>column.source?.startsWith('item.')&&column.source.split('.').length===2);
}
function editableVersionTable(field){
 if(field.kind!=='table'||field.source)return false;
 const columns=versionTableColumns(field);
 return columns.length&&field.fields.every(c=>c.source==='row.number'||columns.includes(c));
}
function versionTableRow(field,row,locked){
 return `<tr>${versionTableColumns(field).map(column=>{
  const key=column.source.split('.')[1],type=fieldInputType(column);
  return `<td>${functionTableCell(column,row[key],locked,key)}</td>`;
 }).join('')}${locked?'':'<td class="version-row-action"><button type="button" class="secondary" data-version-table-remove aria-label="Удалить строку">✕</button></td>'}</tr>`;
}
async function downloadDocumentVersion(){
 const model=documentVersionState;
 const version=model.versions.find(item=>item.id===model.selected);
 if(formDirty)throw Error('Сохраните изменения перед скачиванием.');
 if(version.release_id)return downloadRelease(version.release_id);
 if(version.attachment_id){
  const original=pdata.attachments.find(file=>file.id===version.attachment_id);
  return downloadManual('/api/original?project_id='+projectId+'&attachment_id='+version.attachment_id,
   original?.original_name||'Документ');
 }
 const result=await api('/api/generate',{project_id:projectId,act_id:model.aid});
 await loadProject(projectId);
 render();
 await openDocumentVersions(model.aid);
 await downloadRelease(result.release_id);
}
function versionTables(fields,headers,locked,resolved={}){
 const tables=fields.filter(f=>!['hidden','not_applicable'].includes(f.state)&&editableVersionTable(f));
 if(!tables.length)return '';
 return `<section class="preview-section version-tables"><h3>Таблицы</h3>${tables.map((field,index)=>{
  const columns=versionTableColumns(field);
  const rows=locked&&Array.isArray(resolved[field.key])?resolved[field.key].map(row=>Object.fromEntries(columns.map(c=>[c.source.split('.')[1],row[c.key]]))):(field.value||[]);
  const templateHeader=headers[field.key]||[];
  const width=templateHeader[0]?.reduce((sum,cell)=>sum+cell.span,0);
  const header=width===columns.length?templateHeader:[columns.map(c=>({label:c.label||c.key,span:1,rowspan:1}))];
  const title=!field.label||/^Таблица\s+\d+$/i.test(field.label)?`Таблица ${index+1}`:field.label;
  return `<div class="workspace-stack" data-version-table="${esc(field.key)}" data-locked="${locked}">
   ${tables.length>1?`<h4>${esc(title)}</h4>`:''}
   <div class="toolbar"><button type="button" class="secondary" data-version-table-add>${locked?'Создать версию и добавить строку':'Добавить строку'}</button></div>
   <div class="table-scroll"><table><thead>${header.map((row,index)=>`<tr>${row.map(c=>`<th colspan="${c.span}" rowspan="${c.rowspan||1}">${esc(c.label)}</th>`).join('')}${locked||index?'':`<th rowspan="${header.length}" class="version-row-action" aria-label="Действия"></th>`}</tr>`).join('')}</thead>
   <tbody>${rows.map(row=>versionTableRow(field,row,locked)).join('')}</tbody></table></div></div>`;
 }).join('')}</section>`;
}

function versionFieldRoots(version,form=$('#document-version-form')){
 const active=form?.dataset.version===String(version.id);
 const roots={...pdata.form_roots,act:{...pdata.acts.find(a=>a.id===documentVersionState.aid),...version.card,date_signed:active?form.elements.namedItem('date_signed').value:version.card.date_signed}};
 roots.signatories={...roots.signatories};
 roots.organizations={...roots.organizations};
 (active?documentVersionState.draftSigners:version.signers).forEach((signer,index)=>{
  const identity=active&&form.elements.namedItem('person_'+index)?Number(form.elements.namedItem('person_'+index).value):signer.person_id;
  const person=(documentVersionState.candidates[signer.role]||[]).find(p=>p.id===identity)||(signer.person?.id===identity?signer.person:null);
  if(person){
   const organization=person.organization||(documentVersionState.organization_candidates?.[signer.role]||[]).find(o=>o.id===person.org_id);
   roots.signatories[signer.role]={...person,organization:organization||roots.organizations[signer.role]};
   if(organization)roots.organizations[signer.role]=organization;
  }else roots.signatories[signer.role]=null;
 });
 return roots;
}
function versionSignaturesComplete(signers){
 const chosen=signers.filter(s=>s.person_id);
 return !documentVersionState.pendingRepresentatives&&!!chosen.length&&chosen.every(s=>s.signed)&&documentVersionState.required_roles.every(role=>chosen.some(s=>s.role===role));
}
function updateSignedDocumentSection(){
 const model=documentVersionState,section=$('#signed-document-section');if(!model||!section)return;
 const v=model.versions.find(v=>v.id===model.selected),form=$('#document-version-form');
 const signers=versionDraftSigners(form);
 section.hidden=!v.signed_attachment_id&&!versionSignaturesComplete(signers);
 const input=$('#signed-document-file');
 if(input)input.setAttribute('aria-required',String(!section.hidden&&!v.signed_attachment_id));
 const original=pdata.attachments.find(a=>a.id===v.signed_attachment_id);
 $('#signed-document-name').textContent=model.pendingSignedFile?.name||original?.original_name||(v.signed_attachment_id?'Подписанный оригинал сохранён':'Файл ещё не выбран');
}
document.addEventListener('change',e=>{
 if(e.target.id==='signed-document-file'){
  documentVersionState.pendingSignedFile=e.target.files[0]||null;
  updateSignedDocumentSection();formDirty=true;
 }
 if(e.target.closest('#document-version-form')&&e.target.name.startsWith('person_'))updateSignedDocumentSection();
});
async function downloadSignedDocument(){
 const version=documentVersionState.versions.find(v=>v.id===documentVersionState.selected);
 const original=pdata.attachments.find(a=>a.id===version.signed_attachment_id);
 return downloadManual('/api/original?project_id='+projectId+'&attachment_id='+version.signed_attachment_id,original?.original_name||'Подписанный документ');
}
async function regenerateDocumentVersion(){
 if(formDirty)throw Error('Сохраните изменения перед обновлением файла.');
 const m=documentVersionState,v=m.versions.find(v=>v.id===m.selected);
 const result=await api('/api/versions/regenerate',{project_id:projectId,act_id:m.aid,id:v.id,revision:v.revision});
 m.versions=result.versions;
 await loadProject(projectId);render();renderDocumentVersion();toast('Файл пересоздан на диске');
}
async function deleteDocumentVersion(){
 const m=documentVersionState,v=m.versions.find(v=>v.id===m.selected);
 if(m.versions.length===1)throw Error('Нельзя удалить единственную версию.');
 if(!await confirmWorkspace(`Удалить версию ${v.ordinal}? ${formDirty?'Несохранённые изменения будут потеряны. ':''}Остальные версии будут пронумерованы по порядку. Архивные файлы сохранятся.`, 'Удалить версию'))return;
 const result=await api('/api/versions/delete',{project_id:projectId,act_id:m.aid,id:v.id,revision:v.revision,expected:m.versions.map(v=>({id:v.id,revision:v.revision}))});
 m.versions=result.versions;m.selected=m.versions.at(-1).id;m.pendingSignedFile=null;formDirty=false;
 await loadProject(projectId);render();renderDocumentVersion();toast('Версия удалена');
}

function documentRequiredRoles(fields){
 const result=new Set();
 for(const field of fields){
  if(['hidden','not_applicable'].includes(field.state))continue;
  if(field.required){
   if(field.kind==='signatory')result.add(field.role);
   if(field.binding_role)result.add(field.binding_role);
   if(field.source?.startsWith('signatories.'))result.add(field.source.split('.')[1]);
  }
  if(field.kind==='table')for(const role of documentRequiredRoles(field.fields||[]))result.add(role);
 }
 return [...result];
}

async function initializeDocumentVersion(){
 const model=documentVersionState;
 const result=await api('/api/versions/ensure',{project_id:projectId,act_id:model.aid});
 model.versions=result.versions;model.selected=result.versions.at(-1)?.id;
 renderDocumentVersion();
 window.requestAnimationFrame?.(()=>$('#version-information-title')?.focus());
}
document.addEventListener('click',e=>{
 if(e.target.closest('[data-version-ensure]'))action(initializeDocumentVersion);
});
