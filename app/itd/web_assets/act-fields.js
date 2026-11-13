'use strict';
function actFieldDefinitions(form){return normalizeFormFields(form.code,form.ui_fields||form.fields);}
function fieldInputType(field){return field.input_type||field.value_type==='date'&&'date'||field.value_type==='number'&&'number'||field.format&&'date'||'text';}
function sourceValue(source,roots){
 const aliases={'Object.City':'object.city','Object.Name':'object.name','Project.ShortName':'project.section_code',
  'Project.Name':'project.name','Project.Cipher':'project.code'};
 const match=/^(Organisation|Representative)\.(Id|[1-9][0-9]*)\.([A-Za-z.]+)(?:~default=(\w+))?$/.exec(source||'');
 let path=aliases[source]||source;
 if(match){
  const [,entity,id,property,role]=match;
  const names=entity==='Organisation'?{Name:'full_name',Inn:'inn',ShortName:'short_name'}:
   {Name:'fio',Position:'position','Organisation.ShortName':'organization.short_name'};
  const collection=entity==='Organisation'?'organizations':'signatories';
  roots=roots.participant_ids?.[entity]?.[id]||roots[collection]?.[role];
  path=names[property];
 }
 return (path||'').split('.').reduce((value,key)=>value&&typeof value==='object'?value[key]:undefined,roots);
}
function actInputRoots(){
 const roots=pdata.form_roots||{object:state.object,project:pdata.project,...pdata.participants};
 const chosen=$('#act-form')?selectedActPeople($('#act-form')):{};const signatories=Object.fromEntries(Object.entries(chosen).map(([role,id])=>[role,(()=>{const p=pdata.journals.directory.people.find(p=>p.id===id);return p?{...p,organization:pdata.journals.directory.organizations.find(o=>o.id===p.org_id)}:null;})()]));
 const selectedOrganizations=selectedActOrganizations($('#act-form'));const organizationChoices=pdata.participant_choices?.organizations||{};
 const explicitOrgs=Object.fromEntries(Object.entries(selectedOrganizations).map(([role,id])=>[role,organizationChoices[role]?.find(o=>o.id===id)]).filter(([,o])=>o));
 return {...roots,signatories,organizations:{...roots.organizations,...explicitOrgs,...Object.fromEntries(Object.entries(signatories).filter(([,p])=>p).map(([role,p])=>[role,p.organization]))},act:{date_signed:$('#act-form [name=date_signed]')?.value||null},
  resources:pdata.resources.filter(r=>$('#act-form [name=resource_ids][value="'+r.id+'"]')?.checked),
  schemes:pdata.schemes.filter(s=>$('#act-form [name=scheme_ids][value="'+s.id+'"]')?.checked)};
}
function fieldSourceLabel(field){
 const source=field.source||'',role=source.split('.')[1]||field.role;
 const roles={foreman:'Производитель работ',general_contractor:'Генподрядчик',commissioner:'Пусконаладочная организация',inspector:'Инспектор',worker:'Исполнитель',work_performer:'Исполнитель работ',network_operator:'Эксплуатирующая организация',...meta.document_roles};
 if(source==='act.date_signed')return 'Из поля «Дата подписания» выше';
 if(source==='act.act_num')return 'Номер будет присвоен при создании документа';
 if(source.startsWith('project_documentation.'))return 'Шифр РД текущего раздела и его проектная организация';
 if(source.startsWith('object.'))return 'Из карточки объекта';
 if(source.startsWith('project.'))return 'Из карточки раздела';
 if(source.startsWith('organizations.')||source.startsWith('signatories.')||field.kind==='signatory')return 'По назначению: '+(roles[role]||'участник документа');
 return 'Из сохранённых сведений раздела';
}
function actAutomaticValue(field,roots){
 if(field.source?.startsWith('date_inputs.')){const key=field.source.split('.')[1],input=document.querySelector(`[data-act-field="${key}"]`)||document.querySelector(`[name="version_field_${key}"]`);roots={...roots,date_inputs:{[key]:input?.value}};}
 let value;
 if(field.kind==='signatory'){
  const person=roots.signatories?.[field.role];
  if(!person)return 'Представитель не назначен';
  const patterns={fio:'{signatory.fio}',fio_short:'{signatory.fio_short}',position_org_fio:'{signatory.position} {organization.short_name} {signatory.fio}',position_org_fio_nrs:'{signatory.position} {organization.short_name} {signatory.fio}, номер в НРС №{signatory.nrs_id}'};
  value=(field.template||patterns[field.presentation||'fio']||'').replace(/\{([\w.]+)\}/g,(_,path)=>sourceValue(path,{signatory:person,organization:person.organization||{}})??'Не заполнено');
 }else value=sourceValue(field.source,roots);
 if(field.source==='act.act_num')return 'Будет присвоен при создании';
 if(field.source==='project_documentation.description'&&!value){const doc=roots.project_documentation||{};return `${doc.code||'Шифр РД не указан'}, ${doc.designer_name||'проектная организация не назначена'}`;}
 if(value===null||value===undefined||value==='')return field.source==='act.date_signed'?'Выберите дату подписания выше':'Не заполнено — уточните исходные сведения';
 if(field.format||field.value_type==='date'){
  const parts=String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if(parts){const [,year,month,day]=parts;const months=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];value=({day_2digits:day,month_genitive_ru:months[Number(month)-1],year_4digits:year})[field.date_group?null:field.format]||`${day}.${month}.${year}`;}
 }
 return String(value);
}
function updateActAutomaticValues(){
 const code=$('#act-type')?.value,form=actForms().find(f=>f.code===code);if(!form)return;
 const fields=actFieldDefinitions(form),roots=actInputRoots();
 document.querySelectorAll('[data-act-auto]').forEach(el=>{const field=fields.find(f=>f.key===el.dataset.actAuto);if(field)el.textContent=actAutomaticValue(field,roots);});
}
function renderActFields(code){
 let form=actForms().find(f=>f.code===code);
 const host=$('#act-fields'),draft=$('#act-form');
 if(form&&host?.dataset?.formCode===code&&draft){
  const saved=collectActFields(draft,form);
  form={...form,ui_fields:actFieldDefinitions(form).map(f=>({...f,...saved.find(value=>value.key===f.key)}))};
 }
 if(host?.dataset)host.dataset.formCode=code;
 const fieldsForLinks=form?actFieldDefinitions(form):[];
 function uses(fields,root){return fields.some(f=>!['hidden','not_applicable'].includes(f.state)&&
  (f.source===root||f.source?.startsWith(root+'.')||uses(f.fields||[],root)));}
 for(const [section,roots] of [['act-resources',['resources','materials','work_materials','facts']],['act-schemes',['schemes']]]){
  const panel=$('#'+section);
  if(!panel)continue;
  panel.hidden=!roots.some(root=>uses(fieldsForLinks,root));
  panel.querySelectorAll('input').forEach(input=>input.disabled=panel.hidden);
 }
 if(!form){$('#act-fields').innerHTML='';return;}
 if($('#act-resources'))syncLinkedActResources();
 const people=$('#act-people-fields');if(people){people.outerHTML=actPeopleSelects(null,form);decorateSelects();}
 const fields=actFieldDefinitions(form).filter(f=>!['hidden','not_applicable'].includes(f.state)),roots=actInputRoots();
 const literals=fields.filter(f=>f.kind==='literal'&&!f.readonly),automatic=fields.filter(f=>['reference','signatory'].includes(f.kind)&&(!f.date_group||f.date_group===f.key));
 const objectInfo=f=>/^(object|project|project_documentation)\./.test(f.source||'')?0:1;
 automatic.sort((a,b)=>objectInfo(a)-objectInfo(b));
 $('#act-fields').innerHTML=documentCreationGuidance(form)+participantRoleChoosers(fields)+organizationSelects(fields)+`<h3 class="rep">Сведения документа</h3><p class="hint">Обязательные сведения отмечены *. Можно сохранить незаполненный документ для дальнейшей подготовки; пропуски будут показаны при проверке.</p><div class="grid">${literals.map(f=>{
  const type=fieldInputType(f),long=type==='text'&&(/описан|перечень|приложен|работ|решени|замечан|услови|основан|материал|испытан|документ|регламент/i.test(f.label)||String(f.value||'').length>100);
  const attrs=`data-act-field="${esc(f.key)}" ${f.key==='work_description'?'placeholder="Можно оставить пустым: подставится из выбранных работ"':''}`;
  return `<label class="field ${type==='text'?'wide':''}"><span>${esc(f.label||f.key)}${f.required?' *':''}</span>${long?`<textarea ${attrs}>${esc(f.value)}</textarea>`:`<input ${attrs} type="${type}" ${type==='number'?'step="any"':''} value="${esc(f.value)}">`}</label>`;
 }).join('')||'<p class="hint">Индивидуальных текстовых полей в этой форме нет.</p>'}</div>
 ${automatic.length?`<details class="act-auto-block"><summary>Реквизиты из карточек и назначений (${automatic.length})</summary><p class="hint">Эти значения подставляются автоматически и обновляются при создании DOCX. Организации и представители берутся по назначенным ролям. Организации и представителей изменяйте в «Участниках строительства»; подписантов документа выбирайте в его карточке.</p><dl class="preview-fields">${automatic.map(f=>`<div><dt>${esc(f.label||f.key)}${f.required?' *':''}<small>${esc(fieldSourceLabel(f))}</small></dt><dd><output data-act-auto="${esc(f.key)}">${esc(actAutomaticValue(f,roots))}</output></dd></div>`).join('')}</dl></details>`:''}
 ${versionTables(fields,{},false)}
 ${fields.some(f=>f.kind==='table'&&f.source)?`<details class="act-auto-block"><summary>Автоматические таблицы и перечни</summary><ul>${fields.filter(f=>f.kind==='table'&&f.source).map(f=>`<li>${esc(f.label||'Перечень')} — из связанных сведений раздела и выбранных ресурсов</li>`).join('')}</ul></details>`:''}`;
 decorateSelects();
}
function collectActFields(form,definition){
 const fields=actFieldDefinitions(definition);
 const roleChanges=fields.filter(f=>f.role_slot&&(f.role&&f.role!==f.role_slot||f.source?.startsWith('organizations.')&&f.source.split('.')[1]!==f.role_slot));
 return roleChanges.concat(collectCreationTables(form,fields),[...form.querySelectorAll('[data-act-field]')].filter(el=>el.value!=='').map(el=>{
  const def=fields.find(f=>f.key===el.dataset.actField),type=fieldInputType(def);
  return {key:def.key,label:def.label,kind:'literal',value:type==='number'?Number(el.value):el.value,required:def.required||false,
   ...(type==='date'?{value_type:'date',format:def.format||'date_ru'}:type==='number'?{value_type:'number'}:def.value_type?{value_type:def.value_type}:{})};
 }));
}
function linkedActResourceIds(entryIds,factIds=[]){
 return new Set([...pdata.workspace_entries.filter(e=>entryIds.includes(e.id)).map(e=>e.resource_id),...(pdata.work_materials||[]).filter(m=>entryIds.includes(m.entry_id)).map(m=>m.resource_id),...pdata.workflow.fact_records.filter(f=>factIds.includes(f.id)).map(f=>f.resource_id)].filter(Boolean));
}
function syncLinkedActResources(){
 const form=$('#act-form');if(!form)return;
 const selected=name=>[...form.querySelectorAll(`[name=${name}]:checked`)].map(el=>Number(el.value));
 const linked=linkedActResourceIds(selected('entry_ids'),selected('fact_ids'));
 for(const input of form.querySelectorAll('[name=resource_ids]')){
  if(!input.disabled&&!input.dataset.manualChoice)input.checked=linked.has(Number(input.value));
 }
 updateActAutomaticValues();
}

// Эта же явная карта применяется сервером при формировании документа.
function normalizeFormFields(code,fields){
 fields=normalizeDateFields(code,fields);
 const bindings=pdata.form_bindings?.[code]||{};
 return fields.map(field=>{const binding=bindings[field.key];if(binding&&field.kind==='literal'&&(field.value===null||field.value===undefined||field.value==='')&&!['hidden','not_applicable'].includes(field.state)){field={...field};for(const key of ['value','source','role','template','presentation'])delete field[key];field={...field,...binding};}return {...field,label:cleanFieldLabel(field.label||field.key)};});
}
function normalizeDateFields(code,fields){
 const updates=new Map(),formats={day:'day_2digits',month:'month_genitive_ru',year:'year_4digits'};
 for(const group of pdata.date_groups?.[code]||[]){
  const first=fields.find(f=>f.key===group.parts.day);if(!first)continue;
  const legacy=Object.values(group.parts).some(key=>{const f=fields.find(f=>f.key===key);return f?.kind==='literal'&&f.value!==null&&f.value!==undefined&&f.value!==''&&!/^\d{4}-\d{2}-\d{2}$/.test(String(f.value));});
  for(const [part,key] of Object.entries(group.parts)){
   const original=fields.find(f=>f.key===key);if(!original)continue;
   if(legacy){const f={...original};if(f.kind==='literal'&&f.value!==null&&f.value!==undefined&&f.value!==''){for(const attr of ['format','value_type','input_type','date_group'])delete f[attr];}updates.set(key,{...f,label:group.label+' — '+({day:'день',month:'месяц',year:'год'})[part]});continue;}
   let source=first.kind==='literal'&&first.value?null:group.source;
   if(!source&&first.kind==='reference'&&!first.date_group)source=first.source;
   const f={...original};delete f.source;delete f.value;delete f.input_type;
   if(source)Object.assign(f,{kind:'reference',source});
   else if(part==='day')Object.assign(f,{kind:'literal',value:first.value??null});
   else Object.assign(f,{kind:'reference',source:'date_inputs.'+group.parts.day});
   updates.set(key,{...f,label:group.label,value_type:'date',format:formats[part],date_group:group.parts.day,input_type:'date'});
  }
 }
 return fields.map(f=>updates.get(f.key)||f);
}
function organizationRoles(fields){const roles=new Set();for(const f of fields){if(['hidden','not_applicable'].includes(f.state))continue;if(f.source?.startsWith('organizations.'))roles.add(f.source.split('.')[1]);}return [...roles];}
function organizationSelects(fields,values={},choices=pdata.participant_choices?.organizations||{},locked=false){
 const roles=organizationRoles(fields);if(!roles.length)return '';
 return `<section class="preview-section act-organizations"><h3>Организации</h3><div class="grid">${roles.map(role=>{const list=choices[role]||[],selected=values[role]||(list.length===1?list[0].id:null),label=meta.document_roles[role]||fields.find(f=>f.source?.startsWith('organizations.'+role+'.'))?.label||role;return `<label class="field wide"><span>${esc(label)}</span><select name="org_${esc(role)}" data-organization-role="${esc(role)}" ${locked?'disabled':''}><option value="">${list.length?'Выберите организацию…':'Назначьте организацию этой роли в «Участниках»'}</option>${list.map(o=>option(o.id,o.full_name,selected)).join('')}</select></label>`;}).join('')}</div></section>`;
}
function selectedActOrganizations(form){if(!form)return {};return Object.fromEntries([...form.querySelectorAll('[data-organization-role]')].filter(el=>el.value).map(el=>[el.dataset.organizationRole,Number(el.value)]));}
function participantRoleChoosers(fields,locked=false){
 const slots=new Map();for(const f of fields)if(f.role_slot&&f.role_options?.length&&!slots.has(f.role_slot))slots.set(f.role_slot,{...f,current:f.role||f.source?.split('.')[1]});
 return [...slots.values()].map(f=>`<label class="field wide role-choice"><span>${esc(f.label)} — роль</span><select data-participant-role="${esc(f.role_slot)}" ${locked?'disabled':''}><option value="">Выберите роль по бланку…</option>${f.role_options.map(role=>option(role,meta.document_roles[role]||role,f.current===f.role_slot?'':f.current)).join('')}</select></label>`).join('');
}
function applyParticipantRole(fields,slot,role){return fields.map(f=>{if(f.role_slot!==slot)return f;const next={...f,label:meta.document_roles[role]||f.label};if(f.kind==='signatory')next.role=role;if(f.source?.startsWith('organizations.'))next.source='organizations.'+role+'.'+f.source.split('.').slice(2).join('.');return next;});}
function handleActParticipantChange(e){
 const el=e.target;if(el.dataset.participantRole&&el.value){
  const form=el.closest('form');if(form?.id==='act-form'){
   const definition=actForms().find(f=>f.code===form.elements.namedItem('act_type').value),fields=applyParticipantRole(actFieldDefinitions(definition),el.dataset.participantRole,el.value);
   const literalValues=Object.fromEntries([...form.querySelectorAll('[data-act-field]')].map(el=>[el.dataset.actField,el.value]));
   const people=selectedActPeople(form),organizations=selectedActOrganizations(form);
   definition.fields=fields;definition.ui_fields=fields;renderActFields(definition.code);
   form.querySelectorAll('[data-act-field]').forEach(el=>{if(Object.hasOwn(literalValues,el.dataset.actField))el.value=literalValues[el.dataset.actField];});
   for(const [role,id] of Object.entries(people)){const select=form.elements.namedItem('signer_'+role);if(select)select.value=String(id);}
   for(const [role,id] of Object.entries(organizations)){const select=form.elements.namedItem('org_'+role);if(select)select.value=String(id);}
   decorateSelects();updateActAutomaticValues();formDirty=true;
   const replacement=[...form.querySelectorAll('[data-participant-role]')].find(select=>select.dataset.participantRole===el.dataset.participantRole);
   (replacement?.closest('.smart-select')?.querySelector('.smart-input')||replacement)?.focus();
  }
 }
 if(el.dataset.organizationRole){const role=el.dataset.organizationRole,form=el.closest('form');const personSelect=form?.querySelector(`[name="signer_${role}"]`);if(personSelect){const selectedId=Number(personSelect.value),choices=actRoleCandidates(role).filter(p=>!el.value||p.org_id===Number(el.value));personSelect.innerHTML='<option value="">Выберите представителя…</option>'+choices.map(p=>option(p.id,representativeLabel(p),choices.some(p=>p.id===selectedId)?selectedId:choices.length===1?choices[0].id:null)).join('');enhanceSelect(personSelect);}updateActAutomaticValues();}
}

function automaticCardFields(fields,roots){
 const seen=new Set();const items=fields.filter(f=>{if(f.date_group&&f.date_group!==f.key)return false;if(f.kind!=='reference'||!f.source||!f.source.startsWith('object.')&&!f.source.startsWith('project.')&&!f.source.startsWith('project_documentation.')&&!/^(Object|Project)\./.test(f.source))return false;const id=f.source+'|'+(f.format||'');if(seen.has(id))return false;seen.add(id);return true;});
 return items.length?`<section class="preview-section"><h3>Связи</h3><dl class="preview-fields">${items.map(f=>`<div><dt>${esc(f.label||f.key)}</dt><dd>${esc(actAutomaticValue(f,roots))}</dd></div>`).join('')}</dl></section>`:'';
}
function participantRoleLabel(role,fields=[]){return meta.document_roles[role]||fields.find(f=>f.kind==='signatory'&&f.role===role)?.label||fields.find(f=>f.source?.startsWith('organizations.'+role+'.'))?.label||'Представитель документа';}

function actResourceRemovals(form,fd){
 if(form.querySelector('#act-resources')?.hidden)return [];
 const removed=new Set([...form.querySelectorAll('[name="resource_ids"][data-manual-choice]:not(:checked)')].map(el=>Number(el.value)));
 return fd.getAll('entry_ids').map(Number).flatMap(id=>{
  const entry=pdata.workspace_entries.find(e=>e.id===id);
  const materials=(pdata.work_materials||[]).filter(m=>m.entry_id===id).map(m=>m.resource_id);
  const resource_ids=[...new Set([entry.resource_id,...materials])].filter(rid=>removed.has(rid));
  return resource_ids.length?[{id,revision:entry.revision,resource_ids}]:[];
 });
}

function actLinkIds(form,fd,section,name){
 return form.querySelector('#'+section)?.hidden?[]:fd.getAll(name).map(Number);
}

function documentCreationGuidance(form){
 const guidance=form.guidance;
 return `<section class="preview-section"><h3>${esc(form.name)}</h3>${guidance?`<p class="hint">${esc(guidance.norm)}</p><p>${esc(guidance.summary)}</p><a href="${esc(guidance.url)}" target="_blank" rel="noopener noreferrer">Пример заполнения и пояснения к частям документа</a><p class="hint">Пояснения id-prosto.ru. Применимость и редакцию сверяйте с оригиналом нормы и проектом.</p>`:'<p class="hint">Заполняйте по исходному бланку и проекту. Реквизиты участников подставляются из карточек; результаты, замечания и решение укажите по фактическим данным.</p>'}</section>`;
}
function collectCreationTables(form,fields){
 return [...form.querySelectorAll('[data-version-table]')].map(table=>{
  const field=fields.find(f=>f.key===table.dataset.versionTable);
  return {...field,value:[...table.querySelectorAll('tbody tr')].map(row=>Object.fromEntries(
   [...row.querySelectorAll('[data-table-column]')].map(input=>[input.dataset.tableColumn,
    input.value===''?null:input.type==='number'?Number(input.value):input.value])))};
 });
}
