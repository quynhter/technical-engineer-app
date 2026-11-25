'use strict';
const templateSets=['СП 77.13330.2016','И 1.13-07','Иной согласованный комплект'];
const templateMasks={number:['0','0.00','0.000','0.00 ₽'],date:['«dd» mmmm yyyy','dd.mm.yyyy']};
let templateDraft;
const templateApi=(op,data)=>api('/api/v1/templates/'+op,{project_id:projectId,...data});
function mountTemplates(){
 const host=$('#templates-app');if(!host)return;
 window.ITDDesign.renderProjectRecords(host,{kind:'templates',role:currentUser.role,projectId,workspaceId:currentUser.workspace_id,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onCreate:()=>openTemplate(),
  onOpen:openTemplate,onDelete:async(_,code)=>{
   const item=pdata.templates.find(t=>t.code===code);
   if(!await confirmWorkspace('Удалить шаблон «'+item.name+'»?'))return;
   await templateApi('delete',item);await loadProject(projectId);render();
  },isDirty:registryDirty});
}
async function openTemplate(item){
 const draft=item?structuredClone(item):{form_set:pdata.project.form_set||templateSets[0],name:'',fields:[]};
 if(item?.code&&currentUser.role!=='viewer'){
  let inspected=await templateApi('inspect',{code:item.code});
  if(!Array.isArray(inspected.fields)){
   const file=await templateApi('download',{code:item.code});
   inspected=await templateApi('inspect',{content:file.content});
  }
  draft.fields=templateEditorFields(inspected,draft.fields);
 }
 templateDraft=draft;
 openEditor('manual');editorWindow.setTitle(item?'Изменить шаблон':'Новый шаблон');drawTemplate();
}
function tInput(label,value,attrs){
 return `<label class="field"><span>${esc(label)}</span><input ${attrs} value="${esc(value??'')}"></label>`;
}
function tSelect(label,items,value,attrs){
 return `<label class="field"><span>${esc(label)}</span><select ${attrs}>${items.map(([v,l])=>option(v,l,value)).join('')}</select></label>`;
}
function tMask(type,value,attrs){
 const masks=templateMasks[type];
 return masks?tSelect('Маска поля',masks.map(v=>[v,v]),masks.includes(value)?value:masks[0],attrs):'';
}
const dbToken=/{{\s*\$db\.(\w+)\.(?:(r\d+)\.)?(\w+)\s*}}/g;
const currentDbRows={objects:'object',projects:'project'};
function expressionType(value){
 for(const [,table,,key] of String(value??'').matchAll(dbToken)){
  const type=pdata.template_schema[table]?.columns?.find(c=>c.key===key)?.type;
  if(type&&type!=='text')return type;
 }
 return 'text';
}
function expressionPreview(expression,mask,{bindings=pdata.binding_sources||[],useFirstRecord=false}={}){
 if(String(expression??'').search(dbToken)<0)return '';
 let needsRecord=false;
 const preview=expression.replace(dbToken,(_,table,identity,key)=>{
  if(table==='objects'&&key==='adress')key='address';
  const root=Object.hasOwn(currentDbRows,table)?currentDbRows[table]:null;
  const prefix='records.'+table+'.';
  if(!identity&&!root){
   needsRecord=true;
   if(useFirstRecord)identity=bindings.find(b=>b.source.startsWith(prefix))?.source.split('.')[2];
  }
  const source=identity?prefix+identity+'.'+key:root?root+'.'+key:null;
  const binding=source&&bindings.find(b=>b.source===source);
  if(binding?.value==null||binding.value==='')return '—';
  const {value,value_type}=binding;
  if(value_type==='number'&&templateMasks.number.includes(mask))return Number(value).toFixed(mask==='0'?0:mask==='0.000'?3:2)+(mask.endsWith('₽')?' ₽':'');
  if(value_type==='date'&&templateMasks.date.includes(mask)){
   const [year,month,day]=String(value).split('-');
   return mask==='dd.mm.yyyy'?[day,month,year].join('.'):'«'+day+'» '+['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'][Number(month)-1]+' '+year;
  }
  return String(value);
 });
 if(!needsRecord)return preview;
 return useFirstRecord?'Пример: '+preview:'';
}
function templateExpressionPreview(expression,mask){
 return expressionPreview(expression,mask,{useFirstRecord:true});
}
let templateExpressionId=0;
function expressionInput(value,attrs,mask){
 const id='template-value-'+(++templateExpressionId);
 return `<div class="template-expression">
  <label class="field" for="${id}"><span>Значение</span></label>
  <div class="template-expression-row">
   <input id="${id}" ${attrs} value="${esc(value??'')}">
   <button type="button" data-insert-db aria-label="Вставить поле из базы">ƒ</button>
  </div>
  <output class="hint" data-template-preview>${esc(templateExpressionPreview(value,mask))}</output>
 </div>`;
}
function tableControls(field,i){
 const schema=pdata.template_schema,manual=Array.isArray(field.value),table=field.db_table||((field.key in schema)?field.key:'resources');
 const cols=schema[table].columns;
 let html=tSelect('Тип вставки',[['auto','Автоматическое заполнение'],['manual','Ручное заполнение']],manual?'manual':'auto',`data-table-mode="${i}"`);
 if(manual){
  html+='<div class="table-scroll template-grid" data-document-table><table><thead><tr>'+field.fields.map(c=>`<th scope="col">${esc(c.label||c.key)}</th>`).join('')+'</tr></thead><tbody>';
  html+=field.value.map((row,r)=>'<tr>'+field.fields.map((c,j)=>'<td>'+(c.key==='serial_number'?r+1:expressionInput(row[c.key],`data-row="${r}" data-col="${j}"`,c.mask)+`<div data-expression-mask>${tMask(expressionType(row[c.key]),c.mask,'data-column-mask="'+j+'"')}</div>`)+'</td>').join('')+'</tr>').join('');
  return html+`</tbody></table></div><button type="button" data-add-row="${i}">Добавить строку</button>`;
 }
 html+=tSelect('Таблица',Object.entries(schema).map(([k,v])=>[k,v.label]),table,'data-table-source');
 return html+field.fields.map((c,j)=>{
  if(c.key==='serial_number')return '';
  const key=c.source?.replace(/^item\./,'');
  const type=cols.find(v=>v.key===key)?.type;
  if(templateMasks[type])c.mask||=templateMasks[type][0];
  return tSelect('Поле «'+c.key+'»',[['','Выберите поле'],...cols.map(v=>[v.key,v.label+' ('+v.key+')'])],key,`data-column="${j}"`)+tMask(type,c.mask,`data-column-mask="${j}"`);
 }).join('');
}
function mergeTemplateField(field,previous){
 const old=previous.find(f=>f.key===field.key&&f.kind===field.kind);
 if(!old){
  if(field.kind!=='table'){
   const [prefix,key]=(field.marker_path||'').split('.');
   const column=key||field.key;
   const candidates=previous.filter(t=>t.kind==='table'&&(!prefix||t.key===prefix)&&t.fields.length===1&&t.fields[0].key===column);
   if(candidates.length===1){
    const prior=candidates[0],col=prior.fields[0];
    if(Array.isArray(prior.value))return {...field,label:col.label||field.label,mask:col.mask,
     value_type:col.value_type,value:prior.value.map(row=>row[column]??'').join('; ')};
    if(prior.db_table&&col.source?.startsWith('item.')){
     return {...field,value:'{{ $db.'+prior.db_table+'.'+col.source.slice(5)+' }}',mask:col.mask};
    }
   }
   return field;
  }
  const row={};
  for(const col of field.fields){
   const prior=previous.find(f=>f.kind==='literal'&&(f.marker_path===field.key+'.'+col.key||f.key===col.key));
   if(prior&&col.key!=='serial_number')row[col.key]=prior.value;
  }
  if(Object.keys(row).length||!Object.hasOwn(pdata.template_schema,field.key)){const manual={...field,value:[row]};delete manual.source;return manual;}
  return field;
 }
 const merged={...field,...old};
 if(field.kind==='table'&&Array.isArray(old.value))delete merged.source;
 if(field.fields)merged.fields=field.fields.map(c=>mergeTemplateField(c,old.fields||[]));
 return merged;
}
// A running older server still validates saves against its original table shape.
const legacyTemplateRows=new WeakMap();
function templateEditorFields(result,previous){
 return result.fields.map(field=>{
  const merged=mergeTemplateField(field,previous);
  if(result.row_detection_version||field.kind!=='table'||!/^table_\d+$/.test(field.key)||
     field.fields.length!==1||!Array.isArray(merged.value)||merged.value.length>1)return merged;
  const column=merged.fields[0];
  const scalar={key:column.key,kind:'literal',expression:true,label:column.label||column.key,
   comment:merged.comment,value_type:column.value_type,mask:column.mask,value:merged.value[0]?.[column.key]??''};
  legacyTemplateRows.set(scalar,merged);
  return scalar;
 });
}
function templateSaveField(field){
 const table=legacyTemplateRows.get(field);
 if(!table)return field;
 const column={...table.fields[0],label:field.label,value_type:field.value_type,mask:field.mask};
 return {...table,comment:field.comment,fields:[column],value:[{[column.key]:field.value}]};
}
function scalarControls(field){
 if(isDocumentDateField(field)){
  field.value_type='date';
  return '<p class="hint">Заполняется из поля «Дата подписания» в документе.</p>'+
   tMask('date',field.mask||'dd.mm.yyyy','data-field-prop="mask"');
 }
 const type=field.value_type||expressionType(field.value);
 field.value_type=type;
 if(templateMasks[type])field.mask||=templateMasks[type][0];
 return tSelect('Тип поля',[['text','Строка'],['number','Число'],['date','Дата']],type,'data-field-type')+
  expressionInput(field.value,'data-field-prop="value"'+(type==='date'?' placeholder="ГГГГ-ММ-ДД"':''),field.mask)+
  `<div data-expression-mask>${tMask(type,field.mask,'data-field-prop="mask"')}</div>`;
}
function drawTemplate(){
 const d=templateDraft;
 let html='<h3>Файл шаблона документа</h3>';
 if(!d.original_name)html+=uploadZone('template-file','Добавить файл',{accept:'.docx'});
 else{
  html+=`<div class="toolbar"><span>${esc(d.original_name)}</span><button type="button" data-pick-file="template-file">Изменить</button><button type="button" data-template-download>Скачать</button><input hidden id="template-file" type="file" accept=".docx"></div>`;
  html+=tSelect('Комплект форм',templateSets.map(v=>[v,v]),d.form_set,'data-template-prop="form_set" required')+tInput('Наименование шаблона',d.name,'data-template-prop="name" required');
  html+=d.fields.map((f,i)=>f.key==='serial_number'?'':`<section data-template-field="${i}"><h3>${f.kind==='table'?'Таблица':'Поле'} «${esc(f.marker_path||f.key)}»</h3>${tInput('Наименование',f.label||f.key,'data-field-prop="label"')}${f.kind==='table'?tableControls(f,i):scalarControls(f)}${tInput('Комментарий',f.comment,'data-field-prop="comment"')}</section>`).join('');
 }
 $('#editor-content').innerHTML='<form id="template-editor">'+html+'<div class="toolbar">'+(d.original_name?'<button type="submit" data-template-save>Сохранить</button>':'')+'<button type="button" class="secondary" data-dialog-close>Отмена</button></div></form>';
 if(currentUser.role==='viewer'){
  $('#template-editor').querySelectorAll('input,select,[data-insert-db],[data-pick-file],[data-add-row],[data-template-save]').forEach(el=>{el.disabled=true;});
  $('#template-editor').querySelectorAll('[data-pick-file],[data-add-row],[data-insert-db],[data-template-save]').forEach(el=>el.hidden=true);
 }
 for(const table of document.querySelectorAll('#template-editor .template-grid table')){
  const headers=[...table.tHead.rows[0].cells];
  const field=d.fields[table.closest('[data-template-field]').dataset.templateField];
  const key=JSON.stringify(['template-columns',field.key,field.fields.map(c=>c.key)]);
  const model={headers,key,prefs:savedTablePreferences(key,headers.length)};
  addTableFiller(table);
  enhanceTableResize(table,model);
  applyTableWidths(table,model);
 }
 decorateSelects();
 $('#template-editor').onsubmit=event=>{event.preventDefault();event.stopPropagation();saveTemplate();};
}
const picker=createWorkspaceDialog('template-picker');
function dbRecordOptions(table,bindings){
 const rows=new Map();
 const prefix='records.'+table+'.';
 for(const {source,value} of bindings){
  if(!source.startsWith(prefix))continue;
  const [id,key]=source.slice(prefix.length).split('.');
  if(!rows.has(id))rows.set(id,{});
  if(value!=null&&value!=='')rows.get(id)[key]=value;
 }
 return [...rows].map(([id,row])=>{
  const title=row.full_name||row.fio||[row.last_name,row.first_name,row.middle_name].filter(Boolean).join(' ')||
   row.name||row.title||row.act_num||row.work_description||row.num||row.batch_num||row.entry_date;
  const details=[row.inn&&'ИНН '+row.inn,row.ogrn&&'ОГРН '+row.ogrn,row.position,'№ '+id.slice(1)];
  return [id,[title,...details].filter(Boolean).join('. ')];
 });
}
function dbRecordSelect(table,selected,attrs,bindings){
 const choices=dbRecordOptions(table,bindings);
 if(selected&&!choices.some(([id])=>id===selected))choices.push([selected,'Запись № '+selected.slice(1)+' недоступна']);
 const label='Привязать к записи. '+pdata.template_schema[table].label;
 return tSelect('Привязать к',[['',choices.length?'Выберите запись':'Нет записей'],...choices],selected,
  attrs+' aria-label="'+esc(label)+'" data-select-search'+(!choices.length?' disabled':''));
}
function pickExpression(input,onInsert){
 const start=input.selectionStart,end=input.selectionEnd;
 const host=$('#template-picker .dialog-content'),schema=pdata.template_schema;
 const inDocument=!!input.closest('[data-document-field]');
 host.innerHTML=tSelect('Таблица',Object.entries(schema).map(([k,v])=>[k,(k==='objects'?'Объекты':v.label)+' ('+k+')']),'objects','data-db-table')+'<div data-db-columns></div><button type="button" data-db-insert>Вставить</button>';
 const select=host.querySelector('[data-db-table]');
 const insert=host.querySelector('[data-db-insert]');
 const fields=host.querySelector('[data-db-columns]');
 const needsRecord=()=>inDocument&&!Object.hasOwn(currentDbRows,select.value);
 const columns=()=>{
  const table=select.value;
  fields.innerHTML=(needsRecord()?dbRecordSelect(table,'','data-db-record',functionFieldSources()):'')+
   tSelect('Поле',schema[table].columns.map(c=>[c.key,c.label+' ('+c.key+')']),'','data-db-column');
  if(!inDocument&&!Object.hasOwn(currentDbRows,table))fields.insertAdjacentHTML('beforeend','<p class="hint">Запись выбирается при подготовке документа.</p>');
  const record=fields.querySelector('[data-db-record]');
  insert.disabled=!!record;
  if(record)record.onchange=()=>{insert.disabled=!record.value;};
  fields.querySelectorAll('select').forEach(enhanceSelect);
 };
 columns();select.onchange=columns;enhanceSelect(select);
 insert.onclick=()=>{
  const record=host.querySelector('[data-db-record]')?.value;
  const column=host.querySelector('[data-db-column]').value;
  const token='{{ $db.'+[select.value,record,column].filter(Boolean).join('.')+' }}';
  if(onInsert){
   picker.close(true);
   onInsert(token);
   return;
  }
  input.setRangeText(token,start,end,'end');
  const event=new Event('input',{bubbles:true});
  event.fieldType=schema[select.value].columns.find(c=>c.key===column).type;
  input.dispatchEvent(event);
  picker.close(true);
  requestAnimationFrame(()=>input.focus());
 };picker.open();
}
document.addEventListener('input',event=>{
 const el=event.target;if(!el.closest('#template-editor'))return;
 const f=templateDraft.fields[el.closest('[data-template-field]')?.dataset.templateField];
 if(el.dataset.templateProp)templateDraft[el.dataset.templateProp]=el.value;
 if(el.dataset.fieldProp){
  f[el.dataset.fieldProp]=el.value;
  const preview=el.closest('section').querySelector('[data-template-preview]');
  if(el.dataset.fieldProp==='mask'&&preview)preview.textContent=templateExpressionPreview(f.value,f.mask);
 }
 if(el.hasAttribute('data-row'))f.value[el.dataset.row][f.fields[el.dataset.col].key]=el.value;
 if(el.dataset.fieldProp==='value'||el.hasAttribute('data-row')){
  const column=el.hasAttribute('data-col')?f.fields[el.dataset.col]:null;
  const target=column||f;
  const type=event.fieldType||(column?expressionType(el.value):f.value_type);
  if(event.fieldType&&!column){
   f.value_type=type;el.placeholder=type==='date'?'ГГГГ-ММ-ДД':'';
   const control=el.closest('section').querySelector('[data-field-type]');
   control.value=type;control.dispatchEvent(new Event('smart-sync'));
  }
  target.mask=templateMasks[type]?.includes(target.mask)?target.mask:templateMasks[type]?.[0];
  const expression=el.closest('.template-expression');
  expression.querySelector('[data-template-preview]').textContent=templateExpressionPreview(el.value,target.mask);
  const mask=expression.nextElementSibling;
  if(mask?.hasAttribute('data-expression-mask')&&mask.dataset.type!==type){
   mask.dataset.type=type;
   mask.innerHTML=tMask(type,(column||f).mask,column?'data-column-mask="'+el.dataset.col+'"':'data-field-prop="mask"');
   if(mask.firstElementChild)enhanceSelect(mask.querySelector('select'));
  }
 }
 formDirty=true;
});
document.addEventListener('change',event=>{
 const el=event.target;if(!el.closest('#template-editor'))return;
 if(el.id==='template-file'&&el.files.length){const file=el.files[0],draft=templateDraft;action(async()=>{
  const content=await readUploadContent(file),result=await templateApi('inspect',{content});
  if(templateDraft!==draft)return;
  Object.assign(draft,{content,original_name:file.name,name:draft.name||file.name.replace(/\.docx$/i,''),fields:templateEditorFields(result,draft.fields)});
  formDirty=true;drawTemplate();
 });return;}
 const f=templateDraft.fields[el.closest('[data-template-field]')?.dataset.templateField];if(!f)return;
 if(el.hasAttribute('data-field-type')){
  f.value_type=el.value;f.mask=templateMasks[el.value]?.[0];
  el.closest('section').querySelector('[data-field-prop="value"]').placeholder=el.value==='date'?'ГГГГ-ММ-ДД':'';
  const section=el.closest('section'),mask=section.querySelector('[data-expression-mask]');
  mask.dataset.type=el.value;
  mask.innerHTML=tMask(el.value,f.mask,'data-field-prop="mask"');
  if(mask.firstElementChild)enhanceSelect(mask.querySelector('select'));
  section.querySelector('[data-template-preview]').textContent=templateExpressionPreview(f.value,f.mask);
  formDirty=true;return;
 }
 else if(el.hasAttribute('data-table-mode')){if(el.value==='manual'){delete f.source;delete f.db_table;f.value=[{}];f.fields.forEach(c=>c.source=c.key==='serial_number'?'row.number':'item.'+c.key);}else{delete f.value;f.source=f.key;}}
 else if(el.hasAttribute('data-table-source')){f.db_table=el.value;f.source=f.db_table;}
 else if(el.hasAttribute('data-column')){const c=f.fields[el.dataset.column];c.source='item.'+el.value;delete c.mask;}
 else if(el.hasAttribute('data-column-mask'))f.fields[el.dataset.columnMask].mask=el.value;
 else return;
 formDirty=true;drawTemplate();
});
document.addEventListener('click',event=>{
 const el=event.target.closest('button');if(!el?.closest('#template-editor'))return;
 if(el.hasAttribute('data-insert-db'))pickExpression(el.parentElement.querySelector('input'));
 if(el.hasAttribute('data-add-row')){templateDraft.fields[el.dataset.addRow].value.push({});drawTemplate();}
 if(el.hasAttribute('data-template-download'))action(async()=>{
  const d=templateDraft,payload=d.content?d:await templateApi('download',{code:d.code});
  const bytes=Uint8Array.from(atob(payload.content),v=>v.charCodeAt(0)),url=URL.createObjectURL(new Blob([bytes])),a=document.createElement('a');a.href=url;a.download=d.original_name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 });
});
function saveTemplate(){
 action(async()=>{
  if(currentUser.role==='viewer'||!validateInputs($('#template-editor')))return;
  for(const f of templateDraft.fields)if(f.kind==='table'&&!Array.isArray(f.value))f.db_table||=(f.key in pdata.template_schema?f.key:'resources');
  await templateApi('save',{...templateDraft,fields:templateDraft.fields.map(templateSaveField)});closeEditor(true);await loadProject(projectId);render();
 });
}
