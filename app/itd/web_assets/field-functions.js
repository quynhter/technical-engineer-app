'use strict';
// Сохраняем исходный kind/source/template целиком, пока пользователь явно не изменит связь.
function functionFieldSources(){return (document.querySelector('#document-version-form')?documentVersionState?.binding_sources:null)||pdata.binding_sources||[];}
function functionFieldValue(field,roots){
 if(Object.hasOwn(field,'_display_value'))return field._display_value??'';
 if(field.kind==='literal')return field.value??'';
 if(field.source?.startsWith('records.'))return functionFieldSources().find(x=>x.source===field.source)?.value??'';
 return actAutomaticValue(field,roots);
}
function documentScalarFields(fields){return fields.filter(f=>['literal','reference','signatory'].includes(f.kind)&&!['hidden','not_applicable'].includes(f.state)&&(!f.date_group||f.date_group===f.key));}
function functionField(field,locked=false,mode='version',roots=pdata.form_roots||{}){
 const linked=field.kind!=='literal',value=functionFieldValue(field,roots),type=fieldInputType(field);
 const name=mode==='table'?'':mode==='version'?`name="version_field_${esc(field.key)}"`:`data-act-field="${esc(field.key)}"`;
 return `<div class="field wide document-function-field" data-document-field="${esc(field.key)}" data-field-definition="${esc(JSON.stringify(field))}" data-field-mode="${mode}">
  <label for="document-value-${esc(field.key)}">${esc(field.label||field.key)}${field.required?' *':''}</label>
  <div class="document-function-control"><div data-function-control>${linked||type==='text'?`<textarea id="document-value-${esc(field.key)}" ${name} ${linked?'readonly':''} ${locked?'disabled':''}>${esc(value)}</textarea>`:`<input id="document-value-${esc(field.key)}" ${name} type="${type}" ${type==='number'?'step="any"':''} value="${esc(value)}" ${locked?'disabled':''}>`}</div><button type="button" class="secondary function-toggle" data-field-function aria-label="Выбрать источник: ${esc(field.label||field.key)}" aria-pressed="false" title="Выбрать поле базы данных" ${locked?'disabled':''}><svg class="function-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M17 4h-2a3 3 0 0 0-3 2.5l-2 11A3 3 0 0 1 7 20H6M8 10h8"/></svg></button></div>
  <span class="hint function-source" data-function-source>${linked?esc(fieldSourceLabel(field))+' · '+esc(field.source||'Представление подписанта'):''}</span>
 </div>`;
}
function collectFunctionFields(form){
 return [...form.querySelectorAll('[data-document-field]')].filter(row=>!row.closest('[data-version-table]')&&!row.querySelector('input,textarea')?.disabled).map(row=>{
  if(row.dataset.functionEditing==='true')throw Error('Подтвердите выбранную связь кнопкой f.');
  const field=JSON.parse(row.dataset.fieldDefinition),input=row.querySelector('input,textarea');
  if(field.kind==='literal'&&input&&!input.disabled){field.value=input.value===''?null:fieldInputType(field)==='number'?Number(input.value):input.value;}
  return field;
 });
}
function functionSourceOptions(field){
 const choices=functionFieldSources().filter(item=>!field.date_group||item.value_type==='date'),groups=new Map();
 for(const choice of choices){if(!groups.has(choice.group))groups.set(choice.group,[]);groups.get(choice.group).push(choice);}
 return `<option value="__manual__">Вводить текст вручную</option>${field.kind!=='literal'?'<option value="__current__" selected>Сохранить текущую связь · '+esc(field.source||'Подписант')+'</option>':'<option value="" selected>Найдите таблицу и поле…</option>'}`+[...groups].map(([label,items])=>`<optgroup label="${esc(label)}">${items.map(item=>`<option value="${esc(item.source)}">${esc(item.group+' · '+item.label)}</option>`).join('')}</optgroup>`).join('');
}
document.addEventListener('click',e=>{
 const button=e.target.closest('[data-field-function]');if(!button||button.disabled)return;
 const row=button.closest('[data-document-field]'),field=JSON.parse(row.dataset.fieldDefinition),control=row.querySelector('[data-function-control]');
 if(row.dataset.functionEditing!=='true'){
  const input=control.querySelector('input,textarea');
  row.dataset.functionValue=input.value;
  if(field.kind==='literal')field.value=input.value===''?null:fieldInputType(field)==='number'?Number(input.value):input.value;
  row.dataset.fieldDefinition=JSON.stringify(field);row.dataset.functionEditing='true';
  control.innerHTML=`<select aria-label="Таблица и поле: ${esc(field.label||field.key)}" data-function-source-select>${functionSourceOptions(field)}</select>`;
  button.setAttribute('aria-pressed','true');button.title='Применить выбранную связь';
  enhanceSelect(control.querySelector('select'));
  const focus=()=>control.querySelector('[role="combobox"],.smart-input')?.focus();
  if(typeof requestAnimationFrame==='function')requestAnimationFrame(focus);
  else control.querySelector('select')?.focus();
 }else{
  const source=control.querySelector('select').value||'__current__';
  let next={...field};
  if(source!=='__current__')next.binding_explicit=true;
  if(field.kind==='signatory')next.binding_role=field.role;
  if(source!=='__current__'){
   for(const key of ['value','source','role','template','presentation','_display_value'])delete next[key];
   if(source==='__manual__'){
    const value=row.dataset.functionValue??'';
    Object.assign(next,{kind:'literal',value:value===''?null:fieldInputType(field)==='number'?Number(value):value});
   }
   else {
    const choice=functionFieldSources().find(item=>item.source===source),type=choice?.value_type||(typeof choice?.value==='number'?'number':'text');
    Object.assign(next,{kind:'reference',source,value_type:type,input_type:type});
    if(type!=='date')delete next.format;
    else next.format=next.format||'date_ru';
   }
  }
  const roots=(row.dataset.fieldMode==='version'||row.closest('#document-version-form'))?versionFieldRoots(documentVersionState.versions.find(v=>v.id===documentVersionState.selected)):actInputRoots();
  if(source==='__manual__'&&fieldInputType(field)==='date'){
   const raw=sourceValue(field.source,roots),display=row.dataset.functionValue||'';
   next.value=/^\d{4}-\d{2}-\d{2}$/.test(raw||'')?raw:/^\d{2}\.\d{2}\.\d{4}$/.test(display)?display.split('.').reverse().join('-'):field.value||null;
  }
  const wrapper=document.createElement('div');wrapper.innerHTML=functionField(next,false,row.dataset.fieldMode,roots);
  if(row.dataset.tableColumn){wrapper.firstElementChild.dataset.tableColumn=row.dataset.tableColumn;wrapper.firstElementChild.classList.add('table-function-cell');}
  const replacement=wrapper.firstElementChild;row.replaceWith(replacement);
  replacement.querySelector('[data-field-function]').focus();
  formDirty=true;
 }
});

function updateFunctionValues(form,roots){
 if(!form)return;
 for(const row of form.querySelectorAll('[data-document-field]')){
  if(row.dataset.functionEditing==='true')continue;
  const field=JSON.parse(row.dataset.fieldDefinition);
  if(field.kind==='literal')continue;
  const input=row.querySelector('input,textarea');
  if(input&&!input.disabled)input.value=functionFieldValue(field,roots);
 }
}
for(const type of ['input','change'])document.addEventListener(type,e=>{
 const form=e.target.closest('form');if(!form||e.target.matches('[data-function-source-select]'))return;
 if(form.id==='act-form')updateActAutomaticValues();
 if(form.id==='document-version-form'){
  const version=documentVersionState.versions.find(v=>v.id===documentVersionState.selected);
  updateFunctionValues(form,versionFieldRoots(version));
 }
});

let functionTableCellSequence=0;
function functionTableCell(column,value,locked,key){
 const field={...column,key:'table_cell_'+(++functionTableCellSequence),kind:'literal',value};
 delete field.source;
 if(value&&typeof value==='object'&&value.__itd_source){
  Object.assign(field,{kind:'reference',source:value.__itd_source,value_type:value.value_type,format:value.format});
  delete field.value;
 }
 const markup=functionField(field,locked,'table');
 return markup.replace('data-document-field=',`data-table-column="${esc(key)}" data-document-field=`).replace('class="field wide document-function-field"','class="field wide document-function-field table-function-cell"');
}
function collectFunctionTableCell(cell){
 if(!cell.dataset.fieldDefinition)return cell.value===''?null:cell.type==='number'?Number(cell.value):cell.value;
 if(cell.dataset.functionEditing==='true')throw Error('Подтвердите связь ячейки кнопкой f.');
 const field=JSON.parse(cell.dataset.fieldDefinition);
 if(field.kind==='reference')return {__itd_source:field.source,...(field.value_type?{value_type:field.value_type}:{}),...(field.format?{format:field.format}:{})};
 const input=cell.querySelector('input,textarea');
 return input.value===''?null:fieldInputType(field)==='number'?Number(input.value):input.value;
}
