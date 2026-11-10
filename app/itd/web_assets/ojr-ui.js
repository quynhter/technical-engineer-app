function automaticJournalsPage(){
 const rows=pdata.journals.automatic;
 return card('Журналы по текущим записям',`<p class="hint">ОЖР и ЖВК появляются автоматически после первой записи. Это переходы к текущим записям; печатный выпуск оформляется отдельно.</p><div class="toolbar"><button class="secondary" data-view="participants">Открыть участников строительства</button><button class="secondary" data-manual="assign">Назначить представителя раздела</button></div>`+journalTable(['Журнал','Раздел','Записей'],rows.map(j=>[`<button type="button" class="cell-open" data-auto-journal="${j.kind}" data-journal-project="${j.project_id}">${esc(j.name)}</button>`,esc(j.section_code||'Весь объект'),String(j.count)])),'list');
}
'use strict';
let workMaterialsDraft=[];
function specialRegistryPage(){
 const j=pdata.journals;
 return card('Перечень специальных журналов и журналов авторского надзора',`<p class="hint">Журналы объекта, их выдача и передача заказчику.</p><button data-special-new>Добавить специальный журнал</button>`+journalTable(['Журнал / дата выдачи','Организация','Ответственный за ведение','Передан заказчику','Принял'],j.special.map(s=>[`<button type="button" class="cell-open" data-special-edit="${s.id}">${esc(s.name)}</button>`+'<br>'+journalValue(s.issued_date),journalValue(s.organization?.full_name),journalValue(s.keeper?[[s.keeper.position,s.keeper.fio].filter(Boolean).join(' '),s.keeper.order_doc].filter(Boolean).join(' · '):null),journalValue(s.transfer_date),journalValue(s.recipient?[s.recipient.position,s.recipient.fio].filter(Boolean).join(' '):null)])),'list')+(j.sections['2'].length?card('Прежние записи раздела 2',journalTable(['Название','Дата','Сведения'],j.sections['2'].map(e=>[journalEntryName(e),journalValue(e.work_fields.issued_date),journalEntryAction(e)]))+'<p class="hint">Прежние записи сохранены. Они не дублируются в новом реестре автоматически.</p>','file'):'');
}
function specialEditor(record={}){
 const d=pdata.journals.directory;
 return `<form id="special-journal-form" data-record="${record.id||''}" data-revision="${record.revision||''}"><div class="grid">${input('name','Наименование специального журнала *',record.name,'text',true)}${input('issued_date','Дата выдачи',record.issued_date,'date')}<label class="field"><span>Организация, ведущая журнал</span><select name="org_id"><option value="">Не выбрана</option>${d.organizations.map(o=>option(o.id,o.full_name,record.org_id)).join('')}</select></label><label class="field wide"><span>Ответственный за ведение</span><select name="keeper_id"><option value="">Не выбран</option>${d.people.filter(p=>p.status==='Действует'||p.id===record.keeper_id).map(p=>option(p.id,representativeLabel(p),record.keeper_id)).join('')}</select></label>${input('transfer_date','Дата передачи застройщику / заказчику',record.transfer_date,'date')}<label class="field"><span>Представитель, принявший журнал</span><select name="recipient_id"><option value="">Не выбран</option>${d.people.filter(p=>p.status==='Действует'||p.id===record.recipient_id).map(p=>option(p.id,representativeLabel(p),record.recipient_id)).join('')}</select></label>${input('note','Примечание',record.note,'text',true)}</div><div class="ux-form-actions"><button type="submit">Сохранить журнал</button><button type="button" class="secondary" data-action="cancel-entry">Отменить</button></div></form>`;
}
function ojrPage(){
 let html=`<nav class="tabs" aria-label="Разделы ОЖР">${[['0','Титульный лист'],...Object.entries(pdata.journals.section_names).map(([k,v])=>[k,({1:'Персонал',2:'Журналы',3:'Работы',4:'Строительный контроль',5:'Документы',6:'Госстройнадзор'})[k]])].map(([key,label])=>`<button data-ojr-section="${key}" class="${journalSection===key?'active':''}" ${journalSection===key?'aria-current="page"':''}>${esc(label)}</button>`).join('')}</nav>`;
 if(journalSection==='2')return html+specialRegistryPage();
 if(journalSection==='3')return html+`<p class="journal-purpose">Работы выбранного раздела: ${esc(pdata.project.section_code)}. Выберите записи для подготовки акта.</p>`+workPage();
 if(journalSection==='0')return html+generalJournalPage()+(pdata.journals.legacy.length?`<details class="ux-disclosure card"><summary>Прежние записи без раздела (${pdata.journals.legacy.length})</summary>${journalTable(['Дата','Содержание','Источник'],pdata.journals.legacy.map(e=>[journalValue(e.entry_date),journalEntryName(e),journalEntryAction(e)]))}</details>`:'');
 return html+generalJournalPage();
}
function titleAssignmentsEditor(){
 const rows=pdata.journals.title_assignments;
 return card('Уполномоченные представители',`<p class="hint">Назначения из участников строительства и всех разделов объекта. На одну роль можно назначить нескольких представителей. Подписант конкретного акта выбирается отдельно.</p><div class="toolbar"><button class="secondary" data-view="participants">Открыть участников строительства</button><button class="secondary" data-manual="assign">Назначить представителя раздела</button></div>`+journalTable(['Роль в документах','Организация','Представитель','Основание полномочий','Назначение'],rows.map(r=>[esc(meta.document_roles[r.role_key]||r.role_key),journalValue(r.organization?.full_name),r.person?esc([[r.person.position,r.person.fio].filter(Boolean).join(' '),r.person.status].filter(Boolean).join(' · ')):'Не назначен',journalValue(r.person?.order_doc),esc(r.section_code?'Раздел '+r.section_code:'Весь объект')]),{records:rows.map(r=>({entity:r.record_entity,id:r.record_id}))}),'user');
}
function responsibleSelect(e){return `<label class="field wide"><span>Ответственный исполнитель из раздела 1 ОЖР</span><select name="responsible_id"><option value="">Не выбран</option>${pdata.journals.roster.map(p=>option(p.id,representativeLabel(p),e.responsible_id)).join('')}</select></label>${!pdata.journals.roster.length?'<p class="hint wide">Добавьте исполнителя в раздел 1 ОЖР. Для этого закройте форму и откройте вкладку «ОЖР».</p>':''}`;}
function usedMaterialsHtml(){return workMaterialsDraft.map((m,i)=>`<div class="used-material-row"><label class="field"><span>Ресурс</span><select data-material-index="${i}" data-material-field="resource_id"><option value="">Выберите ресурс</option>${pdata.resources.map(r=>option(r.id,resourceLabel(r.id)+' · '+r.unit,m.resource_id)).join('')}</select></label><label class="field"><span>Использовано</span><input type="number" min="0" step="any" data-material-index="${i}" data-material-field="quantity" value="${esc(m.quantity)}"></label><button type="button" class="secondary" data-material-remove="${i}">Убрать</button></div>`).join('')||'<p class="hint">Ресурсы ещё не выбраны.</p>';}
function workEntryEditor(e){
 workMaterialsDraft=pdata.work_materials.filter(m=>m.entry_id===e.id).map(m=>({resource_id:m.resource_id,quantity:m.quantity}));
 const w=typeof e.work_fields==='string'?JSON.parse(e.work_fields):e.work_fields||{};
 return `<form id="entry-form" data-kind="work"><div class="grid">${input('title','Выполненные работы *',e.title,'text',true)}${input('entry_date','Дата выполнения',e.entry_date,'date')}${input('details','Место работ: этаж, оси, участок',e.details,'text',true)}${responsibleSelect(e)}${input('conditions','Условия производства работ',e.conditions,'text',true)}<label class="field"><span>Вид работ</span><select name="work_type"><option value="">Не выбран</option>${option('general','Общие работы',e.work_type)}${option('cable','Прокладка кабелей',e.work_type)}</select></label><details class="ux-disclosure wide" data-cable-fields ${e.work_type==='cable'?'open':'hidden'}><summary>Кабельная линия</summary><div class="grid">${Object.entries({line_number:'Номер линии',mark:'Марка, напряжение, сечение',drum:'Барабан и длина',couplings:'Муфты',temperature:'Температура',heating:'Подогрев'}).map(([k,l])=>input('work_'+k,l,w[k])).join('')}</div></details></div><section class="rep"><h3>Использованные ресурсы</h3><p class="hint">Использованные ресурсы создают подтверждённый факт монтажа, связанный с записью ОЖР. Укажите дату, место работ и исполнителя.</p><div id="used-materials">${usedMaterialsHtml()}</div><button type="button" class="secondary" data-material-add>Добавить ресурс</button></section><details class="ux-disclosure" ${e.resource_id||e.attachment_id||e.quantity!=null?'open':''}><summary>Дополнительные сведения и документ-основание</summary><div class="grid">${input('quantity','Количество в записи',e.quantity,'number')}${input('unit','Единица записи',e.unit)}${entryResourceSelect(e)}${attachmentSelectForEntry(e)}</div></details>${e.act_id?input('change_reason','Основание изменения работы в акте *','','text',true):''}<div class="ux-form-actions"><button type="submit">Сохранить работу</button>${e.id?`<button type="button" class="secondary" data-copy-entry="${e.id}">Дублировать</button>`:''}<button type="button" class="secondary" data-action="cancel-entry">Отменить</button></div></form>`;
}
function actRoles(definition){
 const result=new Set();
 function visit(fields){for(const f of fields||[]){if(['hidden','not_applicable'].includes(f.state))continue;if(f.kind==='signatory')result.add(f.role);if(f.source?.startsWith('signatories.'))result.add(f.source.split('.')[1]);if(f.kind==='table')visit(f.fields||f.columns);}}
 visit(definition?.ui_fields||definition?.fields);return [...result];
}
function actPeopleSelects(aid=null,definition=null){
 const a=pdata.acts.find(a=>a.id===aid);definition=definition||pdata.forms.find(f=>f.code===a?.act_type)||actForms().find(f=>f.code===$('#act-type')?.value);
 if(!aid&&!definition)return '<div id="act-people-fields"><p class="hint">После выбора формы здесь появятся роли подписантов.</p></div>';
 const existing=pdata.act_signatories.filter(s=>s.act_id===aid),roles=meta.document_roles;
 const body=`<details class="ux-disclosure" open><summary>Подписанты из участников строительства</summary><div class="grid">${actRoles(definition).map(role=>`<label class="field"><span>${esc(participantRoleLabel(role,definition?.ui_fields||definition?.fields||[]))}</span><select name="signer_${role}"><option value="">Не выбран</option>${actRoleCandidates(role).map(p=>option(p.id,representativeLabel(p),existing.find(s=>s.role_key===role)?.signatory_id||(actRoleCandidates(role).length===1?actRoleCandidates(role)[0].id:null))).join('')}</select></label>`).join('')}</div></details>`;
 return aid?body:'<div id="act-people-fields">'+body+'</div>';
}
function actStatusEditor(aid){
 const a=pdata.acts.find(a=>a.id===aid),s=pdata.act_statuses.find(s=>s.act_id===aid);
 return `<form id="act-status-form" data-act="${aid}" data-revision="${s?.revision||0}"><p><strong>${esc(a.act_num)} «${esc(actName(a))}»</strong></p><div class="grid"><label class="field"><span>Статус</span><select name="state">${option('draft','В подготовке',s?.state||'draft')}${option('signed','Подписан',s?.state)}</select></label>${input('signed_date','Дата подписания',s?.signed_date||a.date_signed,'date')}${input('work_description','Наименование работ и место *',a.work_description||s?.work_description,'text',true)}${input('basis','Основание изменения статуса *',null,'text',true)}</div>${actPeopleSelects(aid)}<p class="hint">«Подписан» выбирайте по состоявшемуся подписанию. Запись попадёт в раздел 5 ОЖР; это не электронная подпись файла.</p><div class="ux-form-actions"><button type="submit">Сохранить статус</button><button type="button" class="secondary" data-action="cancel-entry">Отменить</button></div></form>`;
}
function selectedActPeople(form){return Object.fromEntries([...new FormData(form)].filter(([k,v])=>k.startsWith('signer_')&&v).map(([k,v])=>[k.slice(7),Number(v)]));}
async function submitArchitectureForm(form){
 const fd=new FormData(form),id=form.getAttribute('id');
 if(id==='special-journal-form'){
  const data=Object.fromEntries(fd);for(const key of ['org_id','keeper_id','recipient_id'])data[key]=data[key]?Number(data[key]):null;
  data.id=Number(form.dataset.record)||null;data.revision=Number(form.dataset.revision)||null;
  if(!await saveDatedJournal('/api/action',{project_id:projectId,action:'special-journal-save',data},'data'))return;
 }else if(id==='act-status-form'){
  const aid=Number(form.dataset.act),status=pdata.act_statuses.find(s=>s.act_id===aid);
  const choices=selectedActPeople(form),before=Object.fromEntries(pdata.act_signatories.filter(s=>s.act_id===aid).map(s=>[s.role_key,s.signatory_id]));
  // Статус и подписанты сохраняются одним серверным действием.
  if(!await saveDatedJournal('/api/action',{project_id:projectId,action:'act-status',data:{act_id:aid,...Object.fromEntries(fd),signatories:choices,expected_revision:Number(form.dataset.revision)}},'data'))return;
 }
 closeEditor(true);formDirty=false;if(id!=='ojr-title-form')await reloadJournalWorkspace();await loadProject(projectId);render();toast('Сохранено');
}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
 if(b.dataset.ojrSection){if(formDirty)return;journalSection=b.dataset.ojrSection;render();}
 if(b.hasAttribute('data-special-new')||b.dataset.specialEdit){if(formDirty)return;const record=pdata.journals.special.find(s=>s.id===Number(b.dataset.specialEdit))||{};openEditor('manual');$('#editor-content').innerHTML=specialEditor(record);decorateSelects();}
 if(b.hasAttribute('data-material-add')){workMaterialsDraft.push({resource_id:null,quantity:null});$('#used-materials').innerHTML=usedMaterialsHtml();decorateSelects();formDirty=true;}
 if(b.dataset.materialRemove!==undefined){workMaterialsDraft.splice(Number(b.dataset.materialRemove),1);$('#used-materials').innerHTML=usedMaterialsHtml();decorateSelects();formDirty=true;}
 if(b.dataset.actStatus){if(formDirty)return;openEditor('manual');$('#editor-content').innerHTML=actStatusEditor(Number(b.dataset.actStatus));decorateSelects();}
});
function captureMaterial(e){const i=e.target.dataset.materialIndex;if(i!==undefined){const key=e.target.dataset.materialField;workMaterialsDraft[Number(i)][key]=e.target.value===''?null:Number(e.target.value);formDirty=true;}}
document.addEventListener('input',captureMaterial);document.addEventListener('change',captureMaterial);
document.addEventListener('input',e=>{if(e.target.closest('#special-journal-form,#ojr-title-form,#act-status-form'))formDirty=true;});
document.addEventListener('change',e=>{if(e.target.closest('#special-journal-form,#ojr-title-form,#act-status-form'))formDirty=true;});

document.addEventListener('change',e=>{if(e.target.closest('#act-form')&&e.target.name?.startsWith('signer_'))updateActAutomaticValues();});



document.addEventListener('change',e=>{const form=e.target.closest('#entry-form');if(form?.dataset.kind!=='journal'||e.target.name!=='work_person_id')return;const person=pdata.journals.directory.people.find(p=>p.id===Number(e.target.value));if(person){const org=form.elements.namedItem('work_org_id');org.value=String(person.org_id);org.dispatchEvent(new Event('smart-sync'));const title=form.elements.namedItem('title');if(!title.value.trim())title.value=person.fio;}});

document.addEventListener('click',e=>{const b=e.target.closest('[data-auto-journal]');if(!b||formDirty||dirty)return;action(async()=>{if(Number(b.dataset.journalProject)!==projectId)await loadProject(Number(b.dataset.journalProject),true);if(b.dataset.autoJournal==='ojr')journalSection='0';navigate(b.dataset.autoJournal==='ojr'?'ojr':'incoming');});});

function actRoleCandidates(role){
 const all=pdata.journals.directory.people.filter(p=>p.status==='Действует');
 if(pdata.participant_choices?.people){const choices=pdata.participant_choices.people[role]||[];return choices.length?choices:all;}
 const assignments=(pdata.manual.sig_assignments||[]).filter(r=>r.role_key===role);
 const scoped=assignments.filter(r=>r.project_id===projectId),rows=scoped.length?scoped:assignments.filter(r=>r.object_id===state.object.id);
 const choices=all.filter(p=>rows.some(r=>r.signatory_id===p.id));
 return choices.length?choices:all;
}
