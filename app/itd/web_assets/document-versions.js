'use strict';
let documentVersionState=null;
const otherSignerRoles=['other_1','other_2','other_3'];
function versionEffectiveFields(a,version){const definition=pdata.forms.find(f=>f.code===a.act_type),base=definition?.ui_fields||definition?.fields||[],overrides=version.card.fields||[];const fields=base.map(f=>({...f,...overrides.find(x=>x.key===f.key)})).concat(overrides.filter(f=>!base.some(x=>x.key===f.key)));
 for(const [key,continuations] of Object.entries(documentVersionState?.field_continuations||{})){
  const first=fields.find(f=>f.key===key);
  if(!first)continue;
  const values=[first.value];
  for(const continuation of continuations){
   const index=fields.findIndex(f=>f.key===continuation);
   if(index>=0)values.push(fields.splice(index,1)[0].value);
  }
  const joined=values.filter(value=>value!==null&&value!==undefined&&value!=='');
  if(joined.length>1||joined.length===1&&joined[0]!==first.value)first.value=joined.join('\n');
 }
 return normalizeFormFields(a.act_type,fields);}
async function openDocumentVersions(aid){
 const result=await api('/api/versions/list',{project_id:projectId,act_id:aid});
 documentVersionState={...result,aid,selected:result.versions.at(-1).id};
 openEditor('manual');editorWindow.setTitle('Изменить документ');renderDocumentVersion();
}
function renderDocumentVersion(){
 const model=documentVersionState,a=pdata.acts.find(a=>a.id===model.aid),version=model.versions.find(v=>v.id===model.selected),last=model.versions.at(-1);
 const signed=pdata.act_statuses.some(status=>status.act_id===a.id&&status.state==='signed');
 const locked=version.id!==last.id||signed;
 const contentLocked=locked||!!version.release_id;
 const fields=versionEffectiveFields(a,version),required=model.required_roles;
 const formRoles=actRoles({fields}).filter(role=>!otherSignerRoles.includes(role));
 const signers=version.signers.map(s=>({...s}));
 if(!contentLocked)for(const role of formRoles){
  if(signers.some(s=>s.role===role))continue;
  const candidates=model.candidates[role]||[];
  signers.push({role,person_id:candidates.length===1?candidates[0].id:null,signed:false});
 }
 const signerHtml=signers.map((s,i)=>{
  const orgId=version.card.organizations?.[s.role];
  const people=(model.candidates[s.role]||[]).filter(p=>!orgId||p.org_id===Number(orgId)),historical=s.person;
  const options=locked&&historical?[historical]:[...people];if(historical&&!options.some(p=>p.id===s.person_id))options.push(historical);
  return `<div class="version-signer" data-signer-row="${i}"><div><label class="field"><span>${esc(participantRoleLabel(s.role,fields))}${required.includes(s.role)?' *':''}</span><select name="person_${i}" ${contentLocked?'disabled':''}><option value="">Выберите представителя…</option>${options.map(p=>option(p.id,representativeLabel(p),s.person_id)).join('')}</select></label><input type="hidden" name="role_${i}" value="${esc(s.role)}"></div><div class="signer-controls"><button type="button" class="secondary signature-toggle" data-preview-blocked="${locked}" data-signature-toggle="${i}" aria-pressed="${!!s.signed}" ${locked?'disabled':''}>${s.signed?'Подписан':'Не подписан'}</button><label class="field"><span>Дата подписи</span><input type="date" name="signed_date_${i}" value="${esc(s.signed_date||'')}" ${locked?'disabled':''}></label>${!contentLocked&&!formRoles.includes(s.role)?`<button class="ghost danger" type="button" data-signer-remove="${i}" aria-label="Убрать подписанта">Убрать</button>`:''}</div></div>`;
 }).join('');
 $('#editor-content').innerHTML=`<h3>Версии</h3><nav class="version-nav" aria-label="Версии документа">${model.versions.map(v=>`<button class="secondary" type="button" data-document-version="${v.id}" aria-current="${v.id===version.id}" aria-label="Версия ${v.ordinal}">${v.ordinal}</button>`).join('')}<button class="secondary" type="button" data-version-add aria-label="Создать следующую версию">+</button></nav><form id="document-version-form" data-version="${version.id}"><section class="preview-section"><h3>Основная информация</h3>${participantRoleChoosers(fields,contentLocked)}${locked&&version.snapshot?previewContent({preview_fields:pdata.forms.find(f=>f.code===a.act_type)?.ui_fields||[],context:version.snapshot}):''}<p>${esc(a.act_num)} «${esc(actName(a))}»</p><div class="grid"><label class="field"><span>Название файла</span><input name="filename_title" value="${esc(version.card.filename_title||a.act_num.replace(/[<>:"/\\|?*\x00-\x1f]/g,'_'))}" ${contentLocked?'disabled':''}></label><label class="field"><span>Дата подписания</span><input type="date" name="date_signed" value="${esc(version.card.date_signed)}" ${contentLocked?'disabled':''}></label>${fields.filter(f=>f.kind==='literal'&&!f.readonly&&!['hidden','not_applicable'].includes(f.state)).map(f=>`<label class="field wide"><span>${esc(f.label||f.key)}${f.required?' *':''}</span>${fieldInputType(f)==='text'?`<textarea name="version_field_${esc(f.key)}" ${contentLocked?'disabled':''}>${esc(f.value??'')}</textarea>`:`<input name="version_field_${esc(f.key)}" type="${fieldInputType(f)}" value="${esc(f.value??'')}" ${fieldInputType(f)==='number'?'step="any"':''} ${contentLocked?'disabled':''}>`}</label>`).join('')}<label class="field wide"><span>Комментарий</span><textarea name="work_description" ${contentLocked?'disabled':''}>${esc(version.card.work_description||'')}</textarea></label></div></section>${!locked?automaticCardFields(fields,pdata.form_roots||{}):''}${organizationSelects(fields,version.card.organizations||{},model.organization_candidates||{},contentLocked)}${versionTables(fields,model.table_headers||{},contentLocked)}<section class="preview-section"><h3>Подписанты</h3>${!locked?'<p class="hint">Укажите даты подписей и нажмите «Сохранить». Статус изменится после подтверждения всех обязательных подписей. Через «Добавить → Иное лицо» можно выбрать до трёх представителей из «Участников строительства». Их должность, организация и ФИО появятся в конце DOCX с местом для подписи.</p>':''}${signerHtml||'<p class="hint">Сведения о подписантах этой версии не внесены.</p>'}${!contentLocked?`<details class="signer-add-menu"><summary class="secondary">Добавить</summary><button type="button" class="secondary" data-signer-add>Иное лицо</button></details>`:''}</section>${locked?'<p class="hint">Сохранена карточка этой версии. Для изменений создайте следующую версию кнопкой «+».</p>':''}<div class="ux-form-actions">${!locked?'<button type="submit">Сохранить</button>':''}${version.attachment_id||version.release_id||version.id===last.id?`<button type="button" class="secondary" data-download-document>${icon('download')}Скачать документ</button>`:''}<button type="button" class="secondary" data-action="cancel-entry">Отмена</button></div></form>`;
 model.draftSigners=signers.map(s=>({...s}));decorateSelects();
}
function collectVersionDraft(){
 const m=documentVersionState,v=m.versions.find(v=>v.id===m.selected),form=$('#document-version-form'),fd=new FormData(form);
 const a=pdata.acts.find(a=>a.id===m.aid),fields=structuredClone(v.release_id?v.card.fields:versionEffectiveFields(a,v));
 for(const f of versionEffectiveFields(a,v).filter(f=>f.kind==='literal')){
  const el=form.elements.namedItem('version_field_'+f.key);if(!el||el.disabled)continue;
  let value=el.value||null;
  const type=fieldInputType(f);if(type==='number'&&value!==null)value=Number(value);
  const at=fields.findIndex(x=>x.key===f.key),next={...f,value,...(type==='number'?{value_type:'number'}:type==='date'?{value_type:'date',format:f.format||'date_ru'}:{})};if(at<0)fields.push(next);else fields[at]=next;
 }
 for(const table of form.querySelectorAll('[data-version-table]')){
  const field=fields.find(f=>f.key===table.dataset.versionTable);
  if(table.dataset.locked==='true')continue;
  field.value=[...table.querySelectorAll('tbody tr')].map(row=>Object.fromEntries(
   [...row.querySelectorAll('[data-table-column]')].map(input=>[input.dataset.tableColumn,
    input.value===''?null:input.type==='number'?Number(input.value):input.value])));
 }
 return {card:{...v.card,fields,organizations:form.querySelectorAll('[data-organization-role]:not(:disabled)').length?selectedActOrganizations(form):(v.card.organizations||{}),filename_title:fd.has('filename_title')?(fd.get('filename_title')||null):v.card.filename_title,date_signed:fd.has('date_signed')?(fd.get('date_signed')||null):v.card.date_signed},work_description:fd.has('work_description')?(fd.get('work_description')||null):v.card.work_description,signers:m.draftSigners.map((s,i)=>({...s,person_id:fd.has('person_'+i)?Number(fd.get('person_'+i))||null:s.person_id,signed_date:fd.has('signed_date_'+i)?fd.get('signed_date_'+i)||null:s.signed_date}))};
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
 draft.signers=draft.signers.filter(s=>s.person_id);
 const result=await api('/api/versions/save',{project_id:projectId,act_id:model.aid,id:version.id,revision:version.revision,...draft});
 model.versions=result.versions;
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
  formDirty=true;body.lastElementChild.querySelector('input').focus();return;
 }
 const model=documentVersionState;
 const act=pdata.acts.find(a=>a.id===model.aid);
 const version=model.versions.find(v=>v.id===model.selected);
 const field=versionEffectiveFields(act,version).find(f=>f.key===table.dataset.versionTable);
 const body=table.querySelector('tbody');
 body.insertAdjacentHTML('beforeend',versionTableRow(field,{},false));
 formDirty=true;
 body.lastElementChild.querySelector('input').focus();
}
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
 if(b.hasAttribute('data-version-table-remove')){b.closest('tr').remove();formDirty=true;}
 if(b.dataset.versionAct)action(()=>openDocumentVersions(Number(b.dataset.versionAct)));
 if(b.dataset.documentVersion){if(formDirty){notice('Сохраните изменения перед выбором другой версии.');return;}documentVersionState.selected=Number(b.dataset.documentVersion);renderDocumentVersion();}
 if(b.hasAttribute('data-version-add'))action(createDocumentVersion);
 if(b.hasAttribute('data-signature-toggle')){
  const index=Number(b.dataset.signatureToggle),signer=documentVersionState.draftSigners[index];
  signer.signed=!signer.signed;
  b.setAttribute('aria-pressed',String(signer.signed));
  b.textContent=signer.signed?'Подписан':'Не подписан';
  const date=b.form.elements.namedItem('signed_date_'+index);
  if(signer.signed&&!date.value)date.focus();
  formDirty=true;
 }
 if(b.hasAttribute('data-signer-add')){
  const role=otherSignerRoles.find(role=>!documentVersionState.draftSigners.some(s=>s.role===role));
  if(!role){notifyWorkspace('К документу можно добавить не более трёх иных лиц.');return;}
  const version=retainVersionDraft();
  version.signers.push({role,person_id:null,signed:false});
  renderDocumentVersion();
  const index=documentVersionState.draftSigners.findIndex(s=>s.role===role);
  const row=$(`[data-signer-row="${index}"]`);
  const control=row?.querySelector('.smart-input, select');
  (control?.closest('.smart-select')?.querySelector('.smart-input')||control)?.focus();
  formDirty=true;
 }
 if(b.dataset.signerRemove!==undefined){
  const version=retainVersionDraft();
  version.signers.splice(Number(b.dataset.signerRemove),1);
  renderDocumentVersion();
  $('#editor-content .signer-add-menu summary')?.focus();
  formDirty=true;
 }
 if(b.hasAttribute('data-download-document'))action(downloadDocumentVersion);
 if(b.hasAttribute('data-upload-act'))openUploadedAct();
});
for(const type of ['input','change'])document.addEventListener(type,e=>{if(e.target.closest('#document-version-form'))formDirty=true;});

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
function versionTableRow(field,row,locked){
 return `<tr>${versionTableColumns(field).map(column=>{
  const key=column.source.split('.')[1],type=fieldInputType(column);
  return `<td><input aria-label="${esc(column.label||column.key)}" data-table-column="${esc(key)}" type="${type}" ${type==='number'?'step="any"':''} value="${esc(row[key])}" ${locked?'readonly':''}></td>`;
 }).join('')}${locked?'':'<td class="version-row-action"><button type="button" class="secondary" data-version-table-remove aria-label="Удалить строку">✕</button></td>'}</tr>`;
}
async function downloadDocumentVersion(){
 const model=documentVersionState;
 const version=model.versions.find(item=>item.id===model.selected);
 if(formDirty)throw Error('Сохраните изменения перед скачиванием.');
 const latest=version.id===model.versions.at(-1).id;
 const signed=pdata.act_statuses.some(s=>s.act_id===model.aid&&s.state==='signed');
 if(version.release_id&&(!latest||signed))return downloadRelease(version.release_id);
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
function versionTables(fields,headers,locked){
 const tables=fields.filter(f=>f.kind==='table'&&!f.source&&!['hidden','not_applicable'].includes(f.state)&&
  versionTableColumns(f).length&&f.fields.every(c=>c.source==='row.number'||versionTableColumns(f).includes(c)));
 if(!tables.length)return '';
 return `<section class="preview-section version-tables"><h3>Таблицы</h3>${tables.map((field,index)=>{
  const columns=versionTableColumns(field);
  const templateHeader=headers[field.key]||[];
  const width=templateHeader[0]?.reduce((sum,cell)=>sum+cell.span,0);
  const header=width===columns.length?templateHeader:[columns.map(c=>({label:c.label||c.key,span:1,rowspan:1}))];
  const title=!field.label||/^Таблица\s+\d+$/i.test(field.label)?`Таблица ${index+1}`:field.label;
  return `<div class="workspace-stack" data-version-table="${esc(field.key)}" data-locked="${locked}">
   ${tables.length>1?`<h4>${esc(title)}</h4>`:''}
   <div class="toolbar"><button type="button" class="secondary" data-version-table-add>${locked?'Создать версию и добавить строку':'Добавить строку'}</button></div>
   <div class="table-scroll"><table><thead>${header.map((row,index)=>`<tr>${row.map(c=>`<th colspan="${c.span}" rowspan="${c.rowspan||1}">${esc(c.label)}</th>`).join('')}${locked||index?'':`<th rowspan="${header.length}" class="version-row-action" aria-label="Действия"></th>`}</tr>`).join('')}</thead>
   <tbody>${(field.value||[]).map(row=>versionTableRow(field,row,locked)).join('')}</tbody></table></div></div>`;
 }).join('')}</section>`;
}
