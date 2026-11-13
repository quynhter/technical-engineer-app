'use strict';
let resourceImport=null,resourceImportConfig=null;
function installedValue(resource,summary){
 // A work already creates a fact: never add consumed, confirmed_total and qty_fact.
 if(resource.qty_fact!=null)return {value:resource.qty_fact,label:'Итог ведомости'};
 if(summary?.confirmed_ids?.length)return {value:summary.confirmed_total,label:'По подтверждённым записям'};
 return {value:null,label:'Не внесено'};
}
function resourceFactPicker(){
 if(!pdata.resources.length)return '';
 return `<details class="table-filter-disclosure resource-fact-picker"><summary>Монтаж по ресурсу</summary><div class="data-table-filters"><label class="field"><span>Ресурс</span><select id="resource-activity-select"><option value="">Выберите ресурс…</option>${pdata.resources.map(r=>option(r.id,resourceLabel(r.id))).join('')}</select></label><button type="button" class="secondary" data-resource-facts>Открыть монтаж по ресурсу</button></div></details>`;
}
function resourcePage(){
 const nav=`<nav class="panel-nav" aria-label="Учёт ресурсов">${[['list','resources','Спецификация'],['incoming','incoming','Входной контроль'],['facts','facts','Факт монтажа']].map(([key,view,label])=>`<button class="${resourcePanel===key?'active':'secondary'}" data-view="${view}" ${resourcePanel===key?'aria-current="page"':''}>${label}</button>`).join('')}</nav>`;
 const resourceName=id=>pdata.resources.find(r=>r.id===id)?.name;
 const workLink=id=>{
  const work=pdata.workspace_entries.find(e=>e.id===id);
  return work?`<button class="cell-open" data-edit-entry="${work.id}">${esc(work.title)}</button>`:'';
 };
 if(resourcePanel==='incoming')return nav+incomingPage();
 if(resourcePanel==='facts'){const facts=pdata.workflow.fact_records.filter(f=>f.status!=='void').sort((a,b)=>(b.end_date||b.start_date||'').localeCompare(a.end_date||a.start_date||''));return nav+card('Факт монтажа','<div class="toolbar"><button data-editor="fact">Добавить факт</button></div>'+resourceFactPicker()+
  journalTable(['Дата','Материал','Количество','Ед. изм.','Место','Работа в ОЖР','Статус'],facts.map(f=>{
    const work=pdata.work_materials.find(m=>m.fact_id===f.id);
    return [journalValue(f.end_date||f.start_date),esc(resourceName(f.resource_id)),journalValue(f.quantity),esc(f.unit),
     esc(f.location),workLink(f.work_entry_id||work?.entry_id),
     f.status==='confirmed'?'Подтверждён':'Ожидает проверки'];
   }),{records:facts.map(f=>({entity:'work_facts',id:f.id}))}),'list');}
 return nav+card('Спецификация','<div class="toolbar"><button data-resource-import>Импорт Excel / CSV</button><button class="secondary" data-manual="resource-add">Добавить ресурс</button></div>'+
  journalTable(['Позиция','Наименование','Категория','Марка / тип','Производитель','Поставщик','Ед. изм.','По проекту','Смонтировано','Комментарий'],pdata.inventory.map(r=>{
   const summary=pdata.workflow.facts.find(f=>f.resource_id===r.id);
   return [esc(r.spec_num),`<button class="cell-open" data-resource-card="${r.id}">${esc(r.name)}</button>`,
    esc(r.category),esc(r.type_mark),esc(r.manufacturer),esc(r.supplier),esc(r.unit),journalValue(r.qty_proj),
    journalValue(installedValue(r,summary).value),esc(r.note)];
  })),'list');
}
function importPayload(){return {...resourceImportConfig,project_id:projectId,import_id:resourceImport.import_id};}
function importEditor(){
 if(!resourceImport)return `<p>Выберите ведомость. Сопоставление и проверка появятся после загрузки.</p>${uploadZone('resource-import-file','Выбрать ведомость',{accept:'.xlsx,.csv',maxMB:8})}<p class="hint">До 8 МБ, до 10 000 строк. Исходный файл сохраняется в архиве при импорте.</p>`;
 const v=resourceImport,c=resourceImportConfig;
 return `<form id="resource-import-form"><p><strong>${esc(v.filename)}</strong> · строк данных: ${v.count}</p><div class="grid"><label class="field"><span>Лист</span><select name="sheet">${v.sheets.map(s=>option(s,s,c.sheet)).join('')}</select></label>${input('header_row','Строка заголовков',c.header_row,'number')}<label class="field"><span>Категория для пустых ячеек</span><select name="default_category"><option value="">Не задана</option>${meta.categories.map(s=>option(s,s,c.defaults?.category)).join('')}</select></label>${input('default_unit','Единица для пустых ячеек',c.defaults?.unit)}</div><h3 class="rep">Сопоставьте колонки</h3><p class="hint">Выберите колонку для наименования, единицы и категории. Единицу и категорию можно задать выше для всего файла. Импортируются сведения спецификации и проектные количества.</p><div class="grid">${Object.entries(v.fields).filter(([key])=>key!=='qty_received').map(([key,label])=>`<label class="field"><span>${esc(label)}</span><select name="map_${key}"><option value="">Не импортировать</option>${v.headers.map((h,i)=>option(i,(i+1)+'. '+(h||'Без заголовка'),c.mapping?.[key])).join('')}</select></label>`).join('')}</div>${v.category_values?.some(value=>!meta.categories.includes(value))?`<h3 class="rep">Категории из файла</h3><p class="hint">Для каждого обозначения выберите категорию ресурсов. Названия в исходном файле сохраняются без изменений.</p><div class="grid">${v.category_values.map((value,i)=>`<label class="field"><span>${esc(value)}</span><select name="category_${i}"><option value="">${meta.categories.includes(value)?"Совпадает со справочником":"Выберите категорию…"}</option>${meta.categories.map(cat=>option(cat,cat,c.category_map?.[value])).join('')}</select></label>`).join('')}</div>`:''}<details class="ux-disclosure"><summary>Исходные строки</summary>${journalTable(v.headers,v.sample.map(row=>v.headers.map((_,i)=>esc(row[i]))))}</details><div class="toolbar rep"><button type="submit">Проверить сопоставление</button></div>${c.checked?`<h3>Предпросмотр изменений</h3>${!v.valid?`<div class="callout" role="status"><strong>Импорт пока недоступен</strong><ul>${v.rows.filter(r=>r.errors.length).slice(0,10).map(r=>`<li>Строка ${r.row}: ${esc(r.errors.join('; '))}</li>`).join('')}</ul><p>Если категория или единица пропущены в файле, задайте их для пустых ячеек выше, затем повторите проверку.</p></div>`:''}<p>Новых ресурсов: ${v.new_count}. Ранее импортировано: ${v.count-v.new_count}.</p>${journalTable(['Строка','Ресурс','Ед. изм.','Проект','Проверка'],v.rows.slice(0,100).map(r=>[String(r.row),esc(r.values.name),esc(r.values.unit),journalValue(r.values.qty_proj),esc(r.errors.join('; ')||(r.duplicate?'Уже импортировано':'Будет добавлен новый ресурс'))]))}${v.count>100?'<p class="hint">Показаны первые 100 строк; проверены все строки.</p>':''}<p class="hint">Существующие ресурсы не перезаписываются. Повторный импорт тех же строк не увеличивает количества.</p><button type="button" data-resource-import-commit ${!v.valid?'disabled':''}>Импортировать ${v.new_count} ресурсов</button>`:''}</form>`;
}
function showImport(){editEntry=null;formDirty=false;$('#editor-content').innerHTML=importEditor();decorateSelects();editorWindow.open({title:'Импорт ресурсов'});}
function readImportConfig(form){const fd=new FormData(form);return {sheet:fd.get('sheet'),header_row:Number(fd.get('header_row')),defaults:{category:fd.get('default_category')||null,unit:fd.get('default_unit')||null},category_map:Object.fromEntries((resourceImport.category_values||[]).map((v,i)=>[v,fd.get('category_'+i)]).filter(([,v])=>v)),mapping:Object.fromEntries([...fd].filter(([k,v])=>k.startsWith('map_')&&v!=='').map(([k,v])=>[k.slice(4),Number(v)]))};}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
 if(b.hasAttribute('data-resource-import')){if(formDirty)return;resourceImport=null;resourceImportConfig=null;showImport();}
 if(b.hasAttribute('data-resource-import-commit'))action(async()=>{const form=$('#resource-import-form'),current=readImportConfig(form);if(JSON.stringify(current)!==JSON.stringify(Object.fromEntries(Object.entries(resourceImportConfig).filter(([k])=>k!=='checked'))))throw Error('Сопоставление изменилось. Нажмите «Проверить сопоставление».');const result=await api('/api/resource-import/commit',{...importPayload(),preview_token:resourceImport.preview_token});closeEditor(true);await loadProject(projectId);render();toast('Добавлено ресурсов: '+result.imported+'; повторов пропущено: '+result.skipped);});
});
document.addEventListener('change',e=>{if(e.target.id==='resource-import-file')action(async()=>{const f=e.target.files[0];if(!f)return;if(f.size>8*1024*1024)throw Error('Допустимый размер ведомости — 8 МБ');const content=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(Error('Не удалось прочитать файл'));reader.readAsDataURL(f);});resourceImport=await api('/api/resource-import/stage',{project_id:projectId,filename:f.name,content});resourceImportConfig={sheet:resourceImport.sheet,header_row:resourceImport.header_row,defaults:{category:null,unit:null},category_map:{},mapping:suggestResourceColumns(resourceImport.headers)};showImport();});
 if(e.target.closest('#resource-import-form'))formDirty=true;
});
document.addEventListener('input',e=>{if(e.target.closest('#resource-import-form'))formDirty=true;});
async function submitResourceImport(form){resourceImportConfig=readImportConfig(form);resourceImport=await api('/api/resource-import/preview',importPayload());resourceImportConfig.checked=true;formDirty=false;$('#editor-content').innerHTML=importEditor();decorateSelects();}

function suggestResourceColumns(headers){const aliases={name:['наименование'],unit:['ед. изм.','единица измерения','ед.'],category:['категория','обозначение'],spec_num:['номер по спец-ции','позиция'],type_mark:['тип, марка и т. п.','тип / марка'],supplier:['поставщик'],manufacturer:['изготовитель'],qty_proj:['кол-во/проект','количество по проекту'],note:['примечание']};return Object.fromEntries(Object.entries(aliases).flatMap(([key,names])=>{const i=headers.findIndex(h=>names.includes(h.trim().toLowerCase()));return i<0?[]:[[key,i]];}));}

let resourceCardOriginal=null;
const resourceCardFields=['name','short_name','category','unit','spec_num','type_mark','serial_num','manufacturer','supplier','qty_proj','unit_weight','note'];
const factCardFields=['location','work_description','quantity','unit','start_date','end_date','reported_by','status'];
function resourceRecordFields(r){
 const f=manualField;
 return f('name','Полное наименование','textarea',null,r.name,true)+f('category','Категория','text',meta.categories.map(v=>[v,v]),r.category,true)+f('unit','Ед. изм.','text',null,r.unit,true)+f('spec_num','Позиция спецификации','text',null,r.spec_num)+f('type_mark','Марка / тип','text',null,r.type_mark)+f('qty_proj','Количество по проекту','number',null,r.qty_proj)+`<details class="ux-disclosure wide"><summary>Реквизиты и примечание</summary><div class="grid">`+f('short_name','Краткое наименование для документов','text',null,r.short_name)+f('serial_num','Заводские номера','textarea',null,r.serial_num)+f('manufacturer','Производитель','text',null,r.manufacturer)+f('supplier','Поставщик','text',null,r.supplier)+f('unit_weight','Масса единицы','number',null,r.unit_weight)+f('note','Примечание','textarea',null,r.note)+'</div></details>';
}
function factCardRow(r){
 const f=manualField,key=crypto.randomUUID(),linked=pdata.work_materials.find(m=>m.fact_id===r.id);
 if(linked)return `<div class="callout"><strong>Факт № ${r.id} · ${esc(statusNames[r.status])}</strong><p>${esc(r.work_description)} · ${esc(r.location)}<br>${esc(r.quantity??'Количество неизвестно')} ${esc(r.unit)} · ${esc(r.end_date||'Дата не указана')}<br>${esc(r.reported_by)}</p><button type="button" class="secondary" data-resource-work="${linked.entry_id}">Открыть исходную работу</button></div>`;
 if(r.status==='void')return `<details class="ux-disclosure"><summary>Факт № ${r.id} · Отозван</summary><p>${esc(r.work_description)} · ${esc(r.location)} · ${esc(r.quantity??'Количество неизвестно')} ${esc(r.unit)}</p><p>${esc(r.void_reason)}</p></details>`;
 const inAct=pdata.act_facts.some(a=>a.fact_id===r.id);
 return `<details class="ux-step" data-card-fact data-record="${r.id}" data-source-key="${key}"><summary>Факт № ${r.id} · ${esc(r.location||'Место не указано')} · ${esc(r.quantity??'Количество неизвестно')} ${esc(r.unit||resourceCardOriginal.resource.unit)}</summary>${inAct?'<p class="hint">Факт включён в акт. Для исправления реквизитов сначала измените состав фактов акта.</p>':''}<div class="grid">${f('location','Место работ','text',null,r.location,true)}${f('work_description','Выполненные работы','textarea',null,r.work_description,true)}${f('quantity','Прирост количества','number',null,r.quantity)}${f('unit','Ед. изм.','text',null,r.unit||resourceCardOriginal.resource.unit,true)}${f('start_date','Начало работ','date',null,r.start_date)}${f('end_date','Окончание работ','date',null,r.end_date)}${f('reported_by','Кто сообщил','text',null,r.reported_by,true)}${f('status','Подтверждение факта','text',[['pending','Ожидает подтверждения'],['confirmed','Подтверждён'],['void','Отозван']],r.status||'pending',true)}${f('reason','Основание изменения или подтверждения факта','textarea')}</div></details>`;
}
function resourceFactsEditor(r){
 const summary=pdata.workflow.facts.find(f=>f.resource_id===r.id);
 return `<section class="resource-card-block"><h3>Смонтировано</h3><div class="grid" data-card-total>${manualField('qty_fact','Общий итог для ведомости','number',null,r.qty_fact)}</div><p class="hint">Подтверждено записями: ${esc(summary?.confirmed_ids?.length?summary.confirmed_total:'Не внесено')} ${esc(r.unit)}. Итог и записи не складываются.</p><div id="resource-card-facts" class="workspace-stack">${resourceCardOriginal.facts.map(factCardRow).join('')||'<p class="hint" data-card-empty>Записей монтажа пока нет.</p>'}</div></section>`;
}
function resourceCardEditor(r,kind){
 const body=kind==='fact'?resourceFactsEditor(r):
  `<section class="resource-card-block"><h3>По проекту</h3><div class="grid" data-card-main>${resourceRecordFields(r)}</div></section>`;
 return `<form id="resource-card-form">${body}<div class="ux-form-actions"><button type="submit">Сохранить</button><button type="button" class="secondary" data-action="cancel-entry">Отменить</button></div></form>`;
}
function openResourceCard(id,kind='resource'){
 if(dirty||formDirty){notice('Сначала сохраните текущие изменения.');return;}
 const r=pdata.resources.find(r=>r.id===Number(id));
 if(!r)return;
 resourceCardOriginal={
  resource:{...r},
  facts:kind==='fact'?pdata.workflow.fact_records.filter(f=>f.resource_id===r.id):[]
 };
 const title={resource:'Карточка ресурса',fact:'Факт монтажа'}[kind];
 openEditor('manual');editorWindow.setTitle(kind==='resource'?title:title+' · '+r.name);
 $('#editor-content').innerHTML=resourceCardEditor(r,kind);decorateSelects();
}
function cardFormValues(container,keys){
 return Object.fromEntries(keys.map(key=>{const el=container.querySelector(`[name="${key}"]`);const value=el?.value??'';return [key,value===''?null:(el?.type==='number'||key==='attachment_id')?Number(value):value];}));
}
function resourceCardPayload(form){
 const original=resourceCardOriginal,r=original.resource;
 const fields=form.querySelector('[data-card-main]'),total=form.querySelector('[data-card-total]');
 const main=fields?cardFormValues(fields,resourceCardFields):total?cardFormValues(total,['qty_fact']):{};
 const changes=Object.fromEntries(Object.entries(main).filter(([key,value])=>value!==r[key]));
 const facts=[...form.querySelectorAll('[data-card-fact]')].flatMap(el=>{
  const id=Number(el.dataset.record),before=original.facts.find(r=>r.id===id),values=cardFormValues(el,factCardFields);
  if(factCardFields.every(k=>values[k]===before[k]))return [];
  values.source=before.source;values.attachment_id=before.attachment_id;
  return [{id,values,expected:before,reason:el.querySelector('[name="reason"]')?.value||null,source_key:el.dataset.sourceKey}];
 });
 return {id:r.id,changes,expected:r,supplies:[],facts};
}
async function submitResourceCard(form){
 await api('/api/action',{project_id:projectId,action:'resource-card-save',data:resourceCardPayload(form)});
 closeEditor(true);await loadProject(projectId);render();toast('Сведения сохранены');
}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
 if(b.dataset.resourceCard)openResourceCard(b.dataset.resourceCard);
 if(b.hasAttribute('data-resource-facts')){
  const select=$('#resource-activity-select');
  if(select.value)openResourceCard(select.value,'fact');
  else toast('Выберите ресурс');
 }
 if(b.dataset.resourceWork){if(formDirty){notice('Сначала сохраните карточку ресурса или отмените изменения.');return;}const entry=pdata.workspace_entries.find(e=>e.id===Number(b.dataset.resourceWork));if(!entry)return;closeEditor(true);openEditor('work',entry);}
});
for(const event of ['input','change'])document.addEventListener(event,e=>{if(e.target.closest('#resource-card-form'))formDirty=true;});
