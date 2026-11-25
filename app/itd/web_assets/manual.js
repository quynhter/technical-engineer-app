'use strict';
// Ручные операции используют тот же сервис, что workspace-action в CLI.
const manualOperations={
 'assign':'Назначения в документах','resource-add':'Добавить ресурс', 'resource-edit':'Изменить ресурс', 'scheme-add':'Добавить схему','scheme-edit':'Карточка схемы',
 'supply-add':'Добавить поставку / партию','supply-set':'Решение по поставке','allocate':'Материал поставки в акте',
 'period-set':'Период участия организации','unit-add':'Добавить корпус / часть объекта','designer-add':'Добавить разработчика раздела','project-link':'Связи раздела',
 'form-connect':'Подключить форму из каталога','journal-add':'Связать форму журнала с записями',
 'requirement-add':'Добавить документ в перечень','requirement-set':'Изменить документ в перечне',
 'fact-set':'Подтвердить / отозвать факт','delivery-add':'Учесть передачу версии документа','delivery-set':'Стадия сдачи',
 'remark-add':'Добавить замечание','remark-resolve':'Устранить замечание',
 'act-composition':'Ресурсы и схемы акта','act-edit':'Реквизиты и поля акта','sources-review':'Повторно сверить источники акта','attachment-edit':'Реквизиты оригинала'
};
async function downloadManual(path,name){const r=await fetch(path,{headers:{'X-ITD-Token':token}});if(!r.ok){const {error}=await r.json();throw Error(error?.message||error);}const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function manualPage(){
 if(!pdata)return title('Ручное ведение','Выберите рабочий раздел на вкладке «Обзор».')+'<button data-view="overview">Открыть обзор</button>';
 return title('Ручное ведение раздела','Изменения сохраняются в общую БД и доступны агенту.')+`<div id="manual-app"></div>`;
}
function originalManualFile(file){return action(()=>downloadManual('/api/v1/original?project_id='+projectId+'&attachment_id='+file.id,file.original_name));}
function mountManual(){
 const host=$('#manual-app');if(!host)return;
 const pid=projectId,workspace=currentUser.workspace_id;
 window.ITDDesign.renderManualRecords(host,{projectId:pid,workspaceId:workspace,role:currentUser.role,operations:manualOperations,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onManual:openWorkflowManual,onResource:openResourceItemById,onOriginal:originalManualFile,onDelete:deleteProjectRecord,onChanged:value=>registryChanged(host,pid,workspace,value),isDirty:registryDirty});
}
function manualOptions(collection){
 const m=pdata.manual;
 const lists={resources:pdata.resources,acts:pdata.acts,schemes:pdata.schemes,supplies:m.supplies,periods:m.periods,
  units:m.units,organizations:state.participants,signatories:state.participants.flatMap(o=>o.representatives.map(r=>({...r,name:representativeLabel(r,o)}))),requirements:pdata.manual.requirements_records,
  facts:pdata.workflow.fact_records,deliveries:pdata.workflow.deliveries,remarks:pdata.workflow.remarks,
  releases:pdata.releases.filter(r=>r.selected&&r.mode==='final'),attachments:pdata.attachments.filter(a=>pdata.project_attachment_ids.includes(a.id)),forms:pdata.forms,
  catalog:pdata.catalog.filter(f=>!pdata.forms.some(x=>x.code===f.code))};
 return (lists[collection]||[]).map(r=>[r.code&&['forms','catalog'].includes(collection)?r.code:r.id,
   collection==='signatories'?r.name:r.act_num?r.act_num+' «'+(pdata.forms.find(f=>f.code===r.act_type)?.name||r.act_type)+'»':(r.id?'№ '+r.id+'. ':'')+(r.name||r.full_name||r.title||r.description||r.source_key||r.recipient||r.work_description||r.code||'Организация № '+r.org_id)]);
}
function manualField(name,label,type='text',options=null,value=null,required=false){
 const req=required?'required':'';
 const opts=typeof options==='string'?manualOptions(options):options;
 if(type==='multi')return `<div class="field wide"><span>${esc(label)}</span><div class="check-list">${(opts||[]).map(([v,t])=>`<label class="choice"><input type="checkbox" name="${name}" value="${esc(v)}">${esc(t)}</label>`).join('')}</div></div>`;

 return `<label class="field ${type==='textarea'||type==='json'?'wide':''}"><span>${esc(cleanFieldLabel(label))}${required?' *':''}</span>${opts?`<select name="${name}" ${type==='multi'?'multiple':''} ${req}><option value="">Выберите…</option>${opts.map(([v,t])=>option(v,t,value)).join('')}</select>`:type==='textarea'||type==='json'?`<textarea name="${name}" ${req}>${esc(type==='json'?JSON.stringify(value??{},null,2):value??'')}</textarea>`:`<input name="${name}" type="${type}" value="${esc(value)}" ${type==='number'?'step="any" min="0"':''} ${req}>`}</label>`;
}
function selectedManualRecord(op,id){
 const coll={'scheme-edit':'schemes','resource-edit':'resources','supply-set':'supplies','requirement-set':'requirements','fact-set':'facts','delivery-set':'deliveries','remark-add':'deliveries','remark-resolve':'remarks','act-edit':'acts','sources-review':'acts','act-composition':'acts','attachment-edit':'attachments','period-set':'organizations'}[op];
 const lists={resources:pdata.resources,schemes:pdata.schemes,supplies:pdata.manual.supplies,requirements:pdata.manual.requirements_records,facts:pdata.workflow.fact_records,deliveries:pdata.workflow.deliveries,remarks:pdata.workflow.remarks,acts:pdata.acts,attachments:pdata.attachments,organizations:state.participants};
 return (lists[coll]||[]).find(r=>r.id===Number(id));
}
function assignmentTargetField(entity){
 return entity==='signatory'
  ?manualField('entity_id','Представитель','text','signatories',null,true)
  :manualField('entity_id','Организация','text','organizations',null,true);
}
function manualEditor(op,recordId=''){
 const f=manualField,r=selectedManualRecord(op,recordId)||{};let body='';
 const coll={'scheme-edit':'schemes','resource-edit':'resources','supply-set':'supplies','requirement-set':'requirements','fact-set':'facts','delivery-set':'deliveries','remark-add':'deliveries','remark-resolve':'remarks','act-edit':'acts','sources-review':'acts','act-composition':'acts','attachment-edit':'attachments','period-set':'organizations'}[op];
 if(coll)body+=f('id','Запись','text',coll,recordId,true);
 const resourceFields=()=>f('name','Полное наименование','text',null,r.name,true)+f('category','Категория','text',meta.categories.map(v=>[v,v]),r.category,true)+f('unit','Единица','text',null,r.unit,true)+f('spec_num','Позиция спецификации','text',null,r.spec_num)+f('type_mark','Марка / тип','text',null,r.type_mark)+f('serial_num','Заводские номера (по одному в строке)','textarea',null,r.serial_num)+f('manufacturer','Производитель','text',null,r.manufacturer)+f('supplier','Поставщик','text',null,r.supplier)+f('qty_proj','Количество по проекту','number',null,r.qty_proj)+f('qty_fact','Подтверждённый общий факт','number',null,r.qty_fact)+f('note','Примечание','textarea',null,r.note);
 if(['resource-add','resource-edit'].includes(op))body+=resourceFields();
 if(op==='assign'){
  body+=f('scope','Уровень назначения','text',[
   ['object','Весь объект'],['project',`Только раздел «${pdata.project.section_code}»`]
  ],'object',true);
  body+=f('role','Роль в документах','text',Object.entries(meta.document_roles),null,true);
  body+=f('entity','Кого назначить','text',[['signatory','Представителя'],['organization','Организацию']],'signatory',true);
  body+=`<div data-assignment-target>${assignmentTargetField('signatory')}</div>`;
  body+=f('mode','Действие','text',[
   ['add','Добавить к роли'],['replace','Заменить назначения этой роли'],['remove','Снять выбранное назначение']
  ],'add',true);
 }
 if(['scheme-add','scheme-edit'].includes(op))body+=f('num','Номер','text',null,r.num,true)+f('name','Наименование','text',null,r.name,true)+f('ref_code','Референс','text',null,r.ref_code)+f('sheets_count','Количество листов','number',null,r.sheets_count)+f('note','Комментарий','textarea',null,r.note);
 if(['scheme-add','scheme-edit'].includes(op)){
  body+=`<div class="field wide"><span>Файл схемы</span>${uploadZone('scheme-file','Добавить файл схемы')}<output data-scheme-selected></output></div>`;
  for(const file of pdata.scheme_files||[])if(file.scheme_id===r.id)body+=`<button type="button" class="secondary" data-original="${file.id}">${esc(file.original_name)}</button>`;
 }
 if(op==='unit-add')body+=f('name','Полное наименование части объекта','text',null,null,true)+f('code','Короткое обозначение')+f('genplan_num','Номер по генплану');
 if(op==='designer-add')body+=f('name','Наименование разработчика','text',null,null,true);
 if(op==='project-link')body+=f('unit_id','Часть объекта','text','units',pdata.project.unit_id)+f('designer_org_id','Разработчик раздела','text','organizations',pdata.project.designer_org_id);
 if(op==='period-set'){
  const p=pdata.manual.periods.find(p=>p.org_id===Number(recordId))||{};
  body+=f('active_from','Начало участия','date',null,p.active_from)+f('active_to','Окончание участия','date',null,p.active_to)+f('basis','Основание периода','textarea',null,p.basis,true);
 }
 if(op==='supply-add')body+=f('resource_id','Ресурс','text','resources',null,true)+f('source_key','Ключ строки источника','text',null,null,true)+f('batch_num','Партия / маркировка')+f('supply_date','Дата поставки','date')+f('quantity','Поставленное количество','number')+f('supplier','Поставщик')+f('source','Источник (документ, страница или сообщение)','textarea',null,null,true)+f('attachment_id','Архивный источник','text','attachments')+f('status','Решение','text',[['pending','Ожидает проверки'],['accepted','Принято по источнику'],['rejected','Не принято']],null,true)+f('note','Что проверено / замечания','textarea');
 if(op==='supply-set')body+=f('status','Новое решение','text',[['accepted','Принято'],['rejected','Не принято'],['void','Отозвано']],null,true)+f('note','Основание решения','textarea',null,null,true);
 if(op==='allocate')body+=f('act_id','Акт','text','acts',null,true)+f('supply_id','Поставка','text','supplies',null,true)+f('quantity','Количество в акте (0 снимает выделение)','number',null,null,true);
 if(op==='form-connect')body+=f('code','Форма из каталога','text','catalog',null,true);
 if(op==='journal-add'){
  body+=f('act_type','Зарегистрированная форма журнала','text','forms',recordId,true)+f('entry_kind','Источник записей','text',[['work','Работы'],['incoming','Входной контроль'],['journal','Журнальные записи']],'work',true)+f('work_type','Вид работ (пусто — все)','text',[['cable','Прокладка кабелей'],['general','Общие работы']])+f('date_signed','Дата подписания','date');
  const form=pdata.forms.find(x=>x.code===recordId);const table=form?.fields.find(x=>x.kind==='table');
  if(table){body+=f('table_key','Таблица формы','text',[[table.key,table.label||table.key]],table.key,true);const paths=[['entry.entry_date','Дата'],['entry.title','Описание'],['entry.quantity','Количество'],['entry.unit','Единица'],['entry.responsible','Ответственный'],['entry.details','Место и сведения'],['entry.conditions','Условия'],...Object.entries({line_number:'Номер линии',mark:'Марка',drum:'Барабан',couplings:'Муфты',temperature:'Температура',heating:'Подогрев и длительность'}).map(([k,v])=>['entry.work_fields.'+k,v])];const defaults=['entry.entry_date','entry.work_fields.line_number','entry.work_fields.mark','entry.quantity','entry.work_fields.drum','entry.work_fields.couplings','entry.work_fields.temperature','entry.work_fields.heating','entry.responsible'];body+=table.fields.map((col,i)=>f('map_'+col.key,col.label||col.key,'text',paths,recordId==='И_1_13_07_18'?defaults[i]:null)).join('');}
 }
 if(['requirement-add','requirement-set'].includes(op)){
  body+=f('title','Какой документ нужен','text',null,r.title,true)+f('work_scope','Для каких работ или участка','textarea',null,r.work_scope,true)+f('basis','На основании чего он нужен','textarea',null,r.basis,true)+f('kind','Тип документа','text',[['act','Акт'],['attachment','Документ из архива'],['scheme','Схема'],['xlsx','Ведомость XLSX']],r.kind,true);
  body+=`<details class="ux-disclosure wide" ${r.act_id||r.attachment_id||r.scheme_id||r.release_id?'open':''}><summary>Связать с готовым документом</summary><div class="grid">`+f('act_id','Акт','text','acts',r.act_id)+f('attachment_id','Документ из архива','text','attachments',r.attachment_id)+f('scheme_id','Схема','text','schemes',r.scheme_id)+f('release_id','Ведомость','text','releases',r.release_id)+'</div></details>';
  body+=`<details class="ux-disclosure wide" ${r.state==='not_applicable'?'open':''}><summary>Особые условия</summary><div class="grid">`+f('state','Применимость','text',[['required','Требуется'],['not_applicable','Не требуется']],r.state||'required',true)+f('reason','Почему документ не требуется','textarea',null,r.reason)+'</div></details>';
 }

 if(op==='fact-set')body+=f('status','Решение','text',[['confirmed','Подтверждено'],['void','Отозвать']],null,true)+f('reason','Источник подтверждения / причина отзыва','textarea',null,null,true);
 if(op==='delivery-add')body+=f('release_id','Точная окончательная версия','text','releases',null,true)+f('recipient','Получатель','text',null,null,true);
 if(op==='delivery-set')body+=f('status','Стадия','text',[['remarks','Получены замечания'],['corrected','Исправлено'],['sent','Передано повторно'],['accepted','Принято']],null,true)+f('release_id','Исправленная окончательная версия','text','releases');
 if(['delivery-add','delivery-set'].includes(op))body+=f('event_date','Дата состоявшегося события','date',null,null,true)+f('source','Подтверждающий источник','textarea',null,null,true)+f('note','Пояснение','textarea',null,null,true);
 if(op==='remark-add')body+=f('description','Замечание','textarea',null,null,true)+f('source','Источник','textarea',null,null,true);
 if(op==='remark-resolve')body+=f('resolution','Что исправлено','textarea',null,null,true)+f('resolution_source','Основание устранения','textarea',null,null,true)+f('resolution_date','Дата устранения','date',null,null,true)+f('resolution_release_id','Точная исправленная версия','text','releases',null,true);
 if(op==='act-edit'){
  const overrides=r.fields||[];const base=pdata.forms.find(x=>x.code===r.act_type)?.fields||[];let effective=base.map(x=>{const v=overrides.find(v=>v.key===x.key);const merged={...x,...(v||{})};if(v?.source&&!Object.hasOwn(v,'value'))delete merged.value;return merged;}).concat(overrides.filter(x=>!base.some(v=>v.key===x.key)));
  const dateField=r.act_type?.startsWith('TPL_')&&effective.find(isDocumentDateField);
  if(dateField)effective=effective.filter(x=>x!==dateField);
  const signingDate=r.date_signed||(dateField?calendarInputValue(overrides.find(isDocumentDateField)?.value):null);
  body+=f('date_signed','Дата подписания','date',null,signingDate)+f('filename_title','Название файла','text',null,r.filename_title)+f('sheets_count','Проверенное количество листов','number',null,r.sheets_count)+f('registry_note','Примечание реестра','textarea',null,r.registry_note);
  body+=effective.filter(x=>x.kind==='literal').map(x=>{
   const type=fieldInputType(x),value=x.value;
   const typed=['date','number'].includes(type)&&String(value??'').search(dbToken)<0;
   return f('literal_'+x.key,x.label||x.key,typed?type:'textarea',null,typed&&type==='date'?calendarInputValue(value):value);
  }).join('');
  body+='<details class="wide"><summary>Расширенная настройка ссылок и таблиц (JSON)</summary>'+f('fields','Индивидуальные поля формы','json',null,effective)+'</details>';
 }
 if(op==='act-composition')body+=f('resources','Ресурсы (можно несколько)','multi','resources')+f('schemes','Схемы (можно несколько)','multi','schemes');
 if(op==='sources-review')body+=f('reason','Что повторно сверено, источник и основание','textarea',null,null,true);
 if(op==='attachment-edit')body+=f('title','Название','text',null,r.title,true)+f('doc_num','Номер','text',null,r.doc_num)+f('doc_date','Дата','date',null,r.doc_date)+f('sheets_count','Проверенное количество листов','number',null,r.sheets_count)+f('note','Примечание','textarea',null,r.note);
 const hint=op==='assign'?'Укажите роль представителя по распорядительному документу.':
  ['requirement-add','requirement-set'].includes(op)?'Готовый файл можно связать с этим пунктом позже.':'Пустые количества и даты сохраняются неизвестными. Изменения применяются только к выбранной записи; устаревшие данные отклоняются.';
 return card(manualOperations[op],`<form id="manual-form" data-operation="${op}"><div class="grid">${body}</div><p class="hint">${hint}</p><button type="submit">Сохранить</button> <button type="button" class="secondary" data-action="cancel-entry">Отменить ввод</button></form>`,'clipboard');
}
function openManual(op,recordId=''){if(dirty){toast('Сначала сохраните сведения карточки');return;}openEditor('manual');editorWindow.setTitle(manualOperations[op]);$('#editor-content').innerHTML=manualEditor(op,recordId);decorateSelects();}
async function submitManual(form){
 const op=form.dataset.operation,fd=new FormData(form);let d={};
 for(const [k,v] of fd){const el=form.elements.namedItem(k);d[k]=v===''?null:el.type==='number'?Number(v):v;}
 for(const k of ['id','act_id','supply_id','resource_id','attachment_id','scheme_id','release_id','resolution_release_id','unit_id','designer_org_id','sheets_count'])if(d[k]!=null)d[k]=Number(d[k]);
 const r=selectedManualRecord(op,d.id);let action=op;
 if(op==='assign'){
  d.entity_id=Number(d.entity_id);
  const organization=d.entity==='organization';
  const list=organization?pdata.manual.org_assignments:pdata.manual.sig_assignments;
  const old=list.filter(r=>r.role_key===d.role&&(d.scope==='object'?r.object_id===state.object.id:r.project_id===projectId));
  d.expected={entity_ids:old.map(r=>organization?r.org_id:r.signatory_id)};
 }
 if(op==='resource-add'){d.serial_numbers=(d.serial_num||'').split('\n').filter(Boolean);delete d.serial_num;}
 if(['scheme-edit','resource-edit','act-edit','attachment-edit'].includes(op)){
  if(!r)throw Error('Выберите запись');const id=d.id;delete d.id;
  if(op==='act-edit'){
   d.fields=JSON.parse(d.fields||'[]');
   for(const key of Object.keys(d).filter(k=>k.startsWith('literal_'))){const field=d.fields.find(x=>x.key===key.slice(8));if(field?.kind==='literal')field.value=d[key];delete d[key];}
  }
  const expected=Object.fromEntries(Object.keys(d).map(k=>[k,k==='fields'?r.fields_json:r[k]]));
  d={entity:{'scheme-edit':'schemes','resource-edit':'resources','act-edit':'acts','attachment-edit':'attachments'}[op],id,changes:d,expected};action='update';
 }
 if(op==='project-link'){d={entity:'projects',id:projectId,changes:d,expected:{unit_id:pdata.project.unit_id,designer_org_id:pdata.project.designer_org_id}};action='update';}
 if(op==='designer-add')d.expected_designer_org_id=pdata.project.designer_org_id;
 if(op==='period-set'){const old=pdata.manual.periods.find(p=>p.org_id===d.id);d.org_id=d.id;delete d.id;if(old)d.expected={revision:old.revision};}
 if(op==='supply-set'){d.expected={revision:r?.revision};}
 if(op==='allocate'){const old=pdata.manual.allocations.find(m=>m.act_id===d.act_id&&m.supply_id===d.supply_id);d.expected={quantity:old?.quantity??null};}
 if(op==='journal-add'){d.mapping=Object.fromEntries(Object.entries(d).filter(([k,v])=>k.startsWith('map_')&&v!=null).map(([k,v])=>[k.slice(4),v]));for(const k of Object.keys(d))if(k.startsWith('map_'))delete d[k];if(!d.work_type)delete d.work_type;}
 if(['requirement-add','requirement-set'].includes(op)){for(const k of ['act_id','attachment_id','scheme_id','release_id'])if(d[k]==null)delete d[k];}
 if(['requirement-set','delivery-set','fact-set','remark-resolve'].includes(op)){const id=d.id;delete d.id;if(op==='delivery-set'&&!d.release_id)delete d.release_id;d={id,changes:d,expected:op==='delivery-set'?{revision:r?.revision}:op==='fact-set'?{status:r?.status}:Object.fromEntries(Object.entries(r||{}).filter(([k])=>!['availability','latest_delivery','binding_error'].includes(k)))};}
 if(op==='remark-add'){const delivery_id=d.id;delete d.id;d={delivery_id,data:d};}
 if(op==='act-composition'){d={act_id:d.id,resources:fd.getAll('resources').filter(Boolean).map(Number),schemes:fd.getAll('schemes').filter(Boolean).map(Number),expected:{resources:pdata.act_resources.filter(a=>a.act_id===d.id).map(a=>a.resource_id),schemes:pdata.act_schemes.filter(a=>a.act_id===d.id).map(a=>a.scheme_id)}};}
 if(op==='sources-review'){d.act_id=d.id;delete d.id;d.expected=pdata.manual.sources.filter(s=>s.act_id===d.act_id).map(s=>({act_id:s.act_id,entry_id:s.entry_id,source_json:s.source_json}));}
 if(op==='scheme-add'||op==='scheme-edit'){
  const file=form.querySelector('#scheme-file').files[0];
  await api('/api/v1/scheme-save',{project_id:projectId,action,data:d,file:file?{name:file.name,content:await readUploadContent(file)}:null});
 }else await api('/api/action',{project_id:projectId,action,data:d});
 closeEditor(true);
 if(['assign','designer-add','project-link','unit-add'].includes(op))await reloadJournalWorkspace();
 await loadProject(projectId);render();toast('Сохранено в общей базе');
}
function previewFieldLabel(field){
 const suffix={day_2digits:' — день',month_genitive_ru:' — месяц',year_4digits:' — год'};
 return field.label+(suffix[field.format]||'');
}
function previewValue(value,field={},templateHeader=[]){
 if(Array.isArray(value)){
  const columns=field.columns||[];
  if(columns.length){
   const header=templateHeader[0]?.reduce((sum,c)=>sum+c.span,0)===columns.length?templateHeader:[columns.map(c=>({label:c.label,span:1,rowspan:1}))];
   return `<div class="table-scroll document-preview-table" data-document-table><table><thead>${header.map(row=>`<tr>${row.map(c=>`<th scope="${c.span>1?'colgroup':'col'}" colspan="${c.span}" rowspan="${c.rowspan||1}">${esc(c.label)}</th>`).join('')}</tr>`).join('')}</thead><tbody>${value.map(row=>`<tr>${columns.map(c=>`<td>${previewValue(row[c.key],c)}</td>`).join('')}</tr>`).join('')||`<tr><td colspan="${columns.length}">Строки не добавлены</td></tr>`}</tbody></table></div>`;
  }
  if(!value.length)return '<span class="small">Строки не добавлены</span>';
  return `<ul>${value.map(v=>`<li>${previewValue(v)}</li>`).join('')}</ul>`;
 }
 if(value&&typeof value==='object')return '<dl class="preview-fields">'+Object.entries(value).map(([key,v],i)=>`<div><dt>Сведение ${i+1}</dt><dd>${previewValue(v)}<details class="technical-detail"><summary>Код поля</summary>${esc(key)}</details></dd></div>`).join('')+'</dl>';
 if(value===null||value===undefined||value==='')return '<span class="small">Не заполнено</span>';
 return `<span class="preview-text">${esc(String(value).replaceAll('[УТОЧНИТЬ]','Нужно заполнить'))}</span>`;
}
function previewMissingLabel(path,fields){
 const parts=path.replace(/\[(\d+)\]/g,'.$1').split('.');
 const field=fields.find(f=>f.key===parts[0]);
 if(!field)return 'Незаполненное поле (подробности в технических данных)';
 const column=field.columns?.find(c=>c.key===parts[2]);
 const row=/^\d+$/.test(parts[1]||'')?'. строка '+Number(parts[1]):'';
 const details={fio:'ФИО',fio_short:'ФИО',position:'должность',nrs_id:'номер в НРС',short_name:'название организации',full_name:'название организации'};
 return field.label+row+(column?'. '+column.label:parts.length>1?'. '+(details[parts.at(-1)]||'сведения представителя'):'');
}
function previewContent(value){
 const fields=value.preview_fields||[];
 const groups=['Объект и раздел','Номер и даты','Участники и подписанты','Содержание акта','Таблицы и перечни'];
 return groups.map(group=>{
  const items=fields.filter(f=>f.group===group&&!['hidden','not_applicable'].includes(f.state));
  if(!items.length)return '';
  return `<section class="preview-section"><h3>${group}</h3>${group==='Таблицы и перечни'?items.map(f=>`<h4>${esc(f.label)}${f.required?' *':''}</h4>${previewValue(value.context[f.key],f,value.table_headers?.[f.key]||[])}`).join(''):`<dl class="preview-fields">${items.map(f=>`<div><dt>${esc(previewFieldLabel(f))}${f.required?' *':''}</dt><dd>${previewValue(value.context[f.key],f)}</dd></div>`).join('')}</dl>`}</section>`;
 }).join('');
}
function syncPreviewActions(){
 document.querySelectorAll('[data-preview-blocked]').forEach(b=>b.disabled=busy||b.dataset.previewBlocked==='true');
}
function previewActHtml(id,value){
 if(typeof currentUser!=='undefined'&&currentUser?.role==='viewer')return card('Просмотр документа',`<p class="preview-act-name">${esc(value.act_num)} «${esc(value.form_name||value.act_type)}»</p><p class="hint">Сведения текущей карточки документа. Доступен только просмотр.</p>${previewContent(value)}<div class="ux-form-actions"><button type="button" class="secondary" data-action="cancel-entry">Закрыть</button></div>`,'file');
 const fields=value.preview_fields||[],missing=value.missing||[],issues=value.source_issues||[],claims=value.static_claims||[];
 const blocked=!!(missing.length||issues.length||value.template_error),needsReview=claims.length&&!value.review_current;
 const issuesHtml=issues.map(issue=>`<li>${esc(findingNames[issue.code]||'Нужно проверить связь с источником')}${issue.entry_id?'. запись № '+Number(issue.entry_id):''}${issue.supply_id?'. поставка № '+Number(issue.supply_id):''}</li>`).join('');
 const check=missing.length?`<p>Заполните обязательные сведения:</p><ul>${[...new Set(missing.map(path=>previewMissingLabel(path,fields)))].map(label=>`<li>${esc(label)}</li>`).join('')}</ul>`:'<p>Обязательные сведения заполнены.</p>';
 return card('Проверка и создание документа',`<p class="preview-act-name">${esc(value.act_num)} «${esc(value.form_name||value.act_type)}»</p><p class="hint">Проверьте сведения, затем создайте черновик для просмотра в Word или окончательный DOCX. Здесь показано содержание; расположение на печатных страницах проверяется в созданном файле.</p><nav class="preview-steps" aria-label="Порядок подготовки"><span>1. Проверьте сведения</span><span>2. Подтвердите утверждения бланка</span><span>3. Создайте DOCX</span></nav>
 <section class="preview-section preview-check"><h3>Что нужно проверить</h3>${check}${value.template_error?`<p role="alert">${esc(value.template_error)}</p>`:''}${issues.length?`<p>Связанные источники требуют повторной проверки:</p><ul>${issuesHtml}</ul>`:'<p>Изменений в связанных источниках не найдено.</p>'}<div class="toolbar"><button class="secondary" data-preview-edit="act-edit" data-act="${id}">Изменить сведения акта</button><button class="secondary" data-preview-edit="act-composition" data-act="${id}">Изменить ресурсы и схемы</button>${issues.length?`<button class="secondary" data-preview-edit="sources-review" data-act="${id}">Повторно сверить источники</button>`:''}</div></section>
 <h3>Сведения документа</h3><p class="hint">* — обязательное поле. Значения показаны в порядке полей внутри каждого блока.</p>${previewContent(value)}
 <section class="preview-section"><h3>Проверка утверждений бланка</h3>${claims.length?`<p class="hint">Эти формулировки уже есть в шаблоне. Убедитесь, что они подтверждены документами и результатами работ.</p><ul class="claim-list">${claims.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>${value.review_current?'<p class="hint">Подтверждение сохранено и соответствует текущим сведениям и шаблону.</p>':`<form id="review-form" data-act="${id}"><label class="choice"><input name="confirmed" type="checkbox" required>Я проверил перечисленные утверждения по источникам</label><label class="field"><span>По каким источникам проверено и каков результат *</span><textarea name="note" placeholder="Укажите документ, страницу или запись и результат сверки" required></textarea></label><p class="hint">Сохранение подтверждения не создаёт файл.${blocked?' Сначала устраните пропуски и замечания выше.':''}</p><button type="submit" class="secondary" data-preview-blocked="${blocked}" ${blocked?'disabled':''}>Сохранить подтверждение</button></form>`}`:'<p>Утверждений, требующих отдельного подтверждения, в шаблоне не найдено.</p>'}</section>
 <section class="preview-section"><h3>Создание файла DOCX</h3><div class="document-actions"><div><h4>Черновик для проверки</h4><p>Пропуски в обязательных полях будут обозначены тире.</p><button class="secondary" data-preview-draft="${id}" data-preview-blocked="${!!value.template_error}" ${value.template_error?'disabled':''}>Создать черновик DOCX</button></div><div><h4>Окончательная версия</h4><p>${blocked?'Сначала заполните обязательные сведения и устраните замечания выше.':needsReview?'Сначала сохраните подтверждение проверки утверждений бланка.':'Сведения заполнены. Можно создать окончательный файл.'}</p><button data-final="${id}" data-preview-blocked="${!!(blocked||needsReview)}" ${blocked||needsReview?'disabled':''}>Создать окончательный DOCX</button></div></div><p class="hint">Файл сохранится в папке ИТД выбранной базы. Предыдущие выпуски останутся в архиве. Создание файла не означает его подписание или приёмку.</p></section>
`,'file');
}
async function previewAct(id){
 const value=await api('/api/context?project_id='+projectId+'&act_id='+id);
 openEditor('preview');
 editorWindow.setTitle(typeof currentUser!=='undefined'&&currentUser?.role==='viewer'?'Просмотр документа':'Проверка и создание документа');
 $('#editor-content').innerHTML=previewActHtml(id,value);
 $('#editor-dialog').scrollTop=0;
 syncPreviewActions();
}
document.addEventListener('change',e=>{
 const form=e.target.closest('#manual-form[data-operation="assign"]');
 if(!form||e.target.name!=='entity')return;
 const target=form.querySelector('[data-assignment-target]');
 target.innerHTML=e.target.value?assignmentTargetField(e.target.value):'';
 if(e.target.value)enhanceSelect(target.querySelector('select'));
});
document.addEventListener('change',e=>{const form=e.target.closest('#manual-form');if(e.target.id==='scheme-file'){form.querySelector('[data-scheme-selected]').textContent=e.target.files[0]?.name||'';return;}if(!form)return;if(e.target.name==='id'||(e.target.name==='act_type'&&form.dataset.operation==='journal-add')){const op=form.dataset.operation;$('#editor-content').innerHTML=manualEditor(op,e.target.value);formDirty=false;decorateSelects();if(op==='act-composition'){for(const [name,links,key] of [['resources',pdata.act_resources,'resource_id'],['schemes',pdata.act_schemes,'scheme_id']]){const chosen=links.filter(x=>x.act_id===Number(e.target.value)).map(x=>String(x[key]));$('#manual-form').querySelectorAll(`input[name="${name}"]`).forEach(input=>input.checked=chosen.includes(input.value));}}}});
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(formDirty&&!b.closest('form')&&!b.form)return;if(b.dataset.previewEdit){openManual(b.dataset.previewEdit);const select=$('#manual-form').elements.namedItem('id');select.value=b.dataset.act;select.dispatchEvent(new Event('change',{bubbles:true}));formDirty=false;notice();$('#editor-dialog').scrollTop=0;}if(b.dataset.manual){if(formDirty)return;openManual(b.dataset.manual,b.dataset.manualRecord||'');}if(b.dataset.original)action(()=>downloadManual('/api/original?project_id='+projectId+'&attachment_id='+b.dataset.original,pdata.attachments.find(a=>a.id===Number(b.dataset.original)).original_name));if(b.dataset.preview)action(()=>previewAct(Number(b.dataset.preview)));if(b.dataset.final||b.dataset.previewDraft)action(async()=>{const id=Number(b.dataset.final||b.dataset.previewDraft);await api('/api/generate',{project_id:projectId,act_id:id,final:!!b.dataset.final});closeEditor(true);await loadProject(projectId);render();toast('Файл DOCX создан и сохранён в папке ИТД выбранной базы.');});});
