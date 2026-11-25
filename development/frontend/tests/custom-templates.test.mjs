import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {JSDOM} from '../dependencies.mjs';

const asset=name=>readFileSync(new URL('../../../app/itd/web_assets/'+name,import.meta.url),'utf8');
for(const theme of ['light','dark']){
 test('template field picker and form submission in '+theme,async()=>{
  const dom=new JSDOM(asset('index.html'),{url:'http://localhost/',runScripts:'outside-only'}),w=dom.window,d=w.document;
  d.documentElement.dataset.theme=theme;
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  w.HTMLDialogElement.prototype.close=function(){this.open=false;};
  const calls=[];
  Object.assign(w,{structuredClone,currentUser:{role:'editor'},$:s=>d.querySelector(s),
   esc:value=>String(value??'').replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;'),
   projectId:1,pdata:{project:{form_set:'И 1.13-07'},template_schema:{objects:{label:'Объекты',columns:[{key:'work_start',label:'Начало работ',type:'date'}]}}},
   action:async fn=>fn(),editorWindow:{setTitle(){}},openEditor(){},closeEditor(){},decorateSelects(){},enhanceSelect(){},validateInputs:()=>true,
   option:(value,label,selected)=>`<option value="${value}" ${value===selected?'selected':''}>${label}</option>`,
   api:async(path,data)=>calls.push({path,data}),loadProject:async()=>{},render(){},formDirty:false});
  w.ResizeObserver=class{observe(){}unobserve(){}};
  w.HTMLElement.prototype.scrollIntoView=function(){};
  w.eval(['ui.js','dialogs.js','tables.js','templates.js','field-functions.js'].map(asset).join('\n')+
   '\nObject.assign(window,{openTemplate,functionField,collectFunctionFields,functionTableCell,collectFunctionTableCell,enhanceForTest:enhanceSelect});');
  w.openTemplate({original_name:'Ведомость.docx',name:'Ведомость',form_set:'И 1.13-07',fields:[{key:'date',kind:'literal',value:''}]});
  d.querySelector('[data-insert-db]').click();
  assert.equal(d.querySelector('#template-picker').open,true);
  d.querySelector('[data-db-insert]').click();
  assert.equal(d.querySelector('[data-field-prop="value"]').value,'{{ $db.objects.work_start }}');
  assert.equal(d.querySelector('[data-field-type]').value,'date');
  assert.equal(d.querySelector('[data-field-prop="mask"]').value,'«dd» mmmm yyyy');
  const mask=d.querySelector('[data-field-prop="mask"]');mask.value='dd.mm.yyyy';mask.dispatchEvent(new w.Event('input',{bubbles:true}));
  d.querySelector('#template-editor').requestSubmit();
  assert.equal(calls.length,1);assert.equal(calls[0].path,'/api/v1/templates/save');
  assert.equal(calls[0].data.fields[0].mask,'dd.mm.yyyy');
  w.pdata.template_schema.resources={label:'Ресурсы',columns:[{key:'quantity',label:'Количество',type:'number'}]};
  w.pdata.binding_sources=[{source:'records.resources.r1.quantity',value:0,value_type:'number'},
   {source:'records.resources.r2.quantity',value:5,value_type:'number'}];
  const input=d.querySelector('[data-field-prop="value"]');
  input.select();d.querySelector('[data-insert-db]').click();
  const table=d.querySelector('[data-db-table]');table.value='resources';table.dispatchEvent(new w.Event('change'));
  assert.equal(d.querySelector('[data-db-record]'),null);
  d.querySelector('[data-db-insert]').click();
  assert.equal(input.value,'{{ $db.resources.quantity }}');
  assert.equal(d.querySelector('[data-template-preview]').textContent,'Пример: 0');
  assert.equal(d.querySelector('[data-field-type]').value,'number');
  assert.equal(d.querySelector('[data-field-prop="mask"]').value,'0');
  w.pdata.template_schema.organizations={label:'Организации',columns:[
   {key:'full_name',label:'Наименование',type:'text'},{key:'inn',label:'ИНН',type:'text'}]};
  w.pdata.binding_sources.push(
   {source:'records.organizations.r3.full_name',value:'Строймонтаж',value_type:'text'},
   {source:'records.organizations.r3.inn',value:'7700000001',value_type:'text'},
   {source:'records.organizations.r4.full_name',value:'Промстрой',value_type:'text'},
   {source:'records.organizations.r4.inn',value:'7700000002',value_type:'text'});
  const expression='{{ $db.organizations.full_name }}, ИНН: {{ $db.organizations.inn }}';
  input.value=expression;input.dispatchEvent(new w.Event('input',{bubbles:true}));
  assert.equal(d.querySelector('[data-template-preview]').textContent,'Пример: Строймонтаж, ИНН: 7700000001');
  w.pdata.binding_sources.find(b=>b.source==='records.organizations.r3.inn').value=null;
  input.dispatchEvent(new w.Event('input',{bubbles:true}));
  assert.equal(d.querySelector('[data-template-preview]').textContent,'Пример: Строймонтаж, ИНН: —');
  const documentForm=d.createElement('form');
  documentForm.innerHTML=w.functionField({key:'organization',kind:'literal',expression:true,value:expression},false,'creation');
  d.body.append(documentForm);
  const record=documentForm.querySelector('[data-expression-record="organizations"]');
  w.enhanceForTest(record);
  assert.equal(record.value,'');
  assert.equal(documentForm.querySelector('[data-template-preview]').textContent,'Пример: ЗНАЧЕНИЕ, ИНН: ЗНАЧЕНИЕ');
  const combo=record.parentElement.querySelector('[role="combobox"]');
  combo.focus();combo.value='7700000002';combo.dispatchEvent(new w.Event('input',{bubbles:true}));
  combo.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
  assert.equal(record.value,'r4');
  const selected='{{ $db.organizations.r4.full_name }}, ИНН: {{ $db.organizations.r4.inn }}';
  assert.equal(w.collectFunctionFields(documentForm)[0].value,selected);
  assert.equal(documentForm.querySelector('[data-template-preview]').textContent,'Пример: Промстрой, ИНН: 7700000002');
  record.value='r3';record.dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(w.collectFunctionFields(documentForm)[0].value,selected.replaceAll('r4','r3'));
  record.value='';record.dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(w.collectFunctionFields(documentForm)[0].value,expression);
  const text=documentForm.querySelector('textarea');text.select();
  documentForm.querySelector('[data-document-expression]').click();
  const docTable=d.querySelector('[data-db-table]');docTable.value='organizations';docTable.dispatchEvent(new w.Event('change'));
  const docRecord=d.querySelector('[data-db-record]');
  assert.ok(docRecord.parentElement.querySelector('[role="combobox"]'));
  assert.ok(d.querySelector('[data-db-insert]').disabled);
  docRecord.value='r4';docRecord.dispatchEvent(new w.Event('change'));
  d.querySelector('[data-db-insert]').click();
  assert.equal(text.value,'{{ $db.organizations.r4.full_name }}');
  documentForm.innerHTML=w.functionTableCell({type:'text'},expression,false,'organization');
  const cell=documentForm.querySelector('[data-table-column]'),cellRecord=cell.querySelector('select');
  cellRecord.value='r4';cellRecord.dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(w.collectFunctionTableCell(cell),selected);
  documentForm.remove();
  await w.openTemplate({original_name:'Акт.docx',name:'Акт',fields:[
   {kind:'table',key:'materials',fields:[{key:'serial_number'},{key:'quantity'}],value:[{quantity:'5'}]}]});
  const separator=()=>d.querySelectorAll('.template-grid [role="separator"]')[1];
  const width=Number(separator().getAttribute('aria-valuenow'));
  separator().dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
  assert.equal(separator().getAttribute('aria-valuenow'),String(width+10));
  d.querySelector('[data-add-row]').click();
  assert.equal(separator().getAttribute('aria-valuenow'),String(width+10));
  assert.equal(d.querySelector('.template-grid [data-row="0"]').value,'5');
  assert.equal(d.querySelectorAll('.template-grid tbody tr').length,2);
  const legacy={key:'table_2',kind:'table',source:'table_2',fields:[{key:'object',kind:'reference',source:'item.object'}]};
  let saved;
  w.api=async(path,data)=>{
   if(path.endsWith('/inspect'))return {fields:[legacy]};
   saved=data;
  };
  await w.openTemplate({code:'old',name:'Акт',form_set:'И 1.13-07',original_name:'СП_77_А_1.docx',fields:[{...legacy,source:undefined,value:[{object:'Корпус'}]}]});
  assert.equal(d.querySelector('[data-template-field] h3').textContent,'Поле «object»');
  assert.equal(d.querySelector('[data-add-row]'),null);
  const objectInput=d.querySelector('[data-field-prop="value"]');
  assert.equal(objectInput.value,'Корпус');
  objectInput.value='Корпус Б';objectInput.dispatchEvent(new w.Event('input',{bubbles:true}));
  d.querySelector('#template-editor').requestSubmit();
  assert.equal(saved.fields[0].key,'table_2');
  assert.equal(saved.fields[0].value[0].object,'Корпус Б');
  await new Promise(resolve=>setTimeout(resolve,0));
  dom.window.close();
 });
}
