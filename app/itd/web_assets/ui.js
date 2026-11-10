'use strict';
function representativeLabel(person,organization=null){
 const organizations=typeof pdata!=='undefined'?pdata?.journals?.directory?.organizations:[];
 const participants=typeof state!=='undefined'?state?.participants:[];
 const org=person.organization||organization||organizations?.find(o=>o.id===person.org_id)||participants?.find(o=>o.id===person.org_id||o.representatives?.some(r=>r.id===person.id));
 const fio=[person.last_name,person.first_name,person.middle_name].filter(Boolean).join(' ')||person.fio;
 return [person.position,org?.short_name||org?.full_name,fio].filter(Boolean).join(' ');
}
function cleanFieldLabel(label){return String(label??'').replace(/[()]/g,'').replace(/\s+/g,' ').trim().replace(/\p{L}/u,c=>c.toLocaleUpperCase('ru'));}
function fitMiddleText(text,maxWidth,measure){
 const chars=Array.from(String(text));
 if(measure(text)<=maxWidth)return String(text);
 let lo=0,hi=Math.max(0,chars.length-1),best='...';
 while(lo<=hi){
  const count=Math.floor((lo+hi)/2),head=Math.floor(count*.65),tail=count-head;
  const value=chars.slice(0,head).join('')+'...'+(tail?chars.slice(-tail).join(''):'');
  if(measure(value)<=maxWidth){best=value;lo=count+1;}else hi=count-1;
 }
 return best;
}
let middleCanvas;
function refreshMiddleLabel(element){
 if(!element.isConnected||element.classList.contains('text-expanded'))return;
 const width=element.clientWidth;if(!width)return;
 middleCanvas??=document.createElement('canvas');const ctx=middleCanvas.getContext('2d');
 ctx.font=getComputedStyle(element).font;
 const value=fitMiddleText(element.dataset.fullText,width,text=>ctx.measureText(text).width);
 if(element.textContent!==value)element.textContent=value;
}
const middleObserver=new ResizeObserver(entries=>entries.forEach(entry=>refreshMiddleLabel(entry.target)));
function middleLabel(element,text,expandable=false){
 text=String(text);
 if(element.dataset.fullText!==text){element.dataset.fullText=text;element.textContent=text;}
 element.title=text;element.classList.add('middle-label');element.setAttribute('aria-label',text);
 if(expandable){element.dataset.expandText='';element.tabIndex=0;element.setAttribute('role','button');if(!element.hasAttribute('aria-expanded'))element.setAttribute('aria-expanded','false');}
 middleObserver.observe(element);refreshMiddleLabel(element);
}
function tableCellLabels(table){
 const cells=[...table.querySelectorAll('tbody td')].filter(cell=>cell.colSpan===1&&!cell.matches('.empty,[data-table-fill]'));
 for(const cell of cells){
  if(!cell.children.length&&cell.textContent.trim().length>40){const text=document.createElement('span');text.className='cell-text';text.textContent=cell.textContent;cell.replaceChildren(text);}
  cell.querySelectorAll('.cell-text,p.hint,.cell-open>strong,.cell-open>span,.cell-open:not(:has(*)),.record-name:not(:has(*)),.link-button:not(:has(*))').forEach(el=>{
   const text=el.dataset.fullText||el.textContent.trim();
   if(text.length>24&&!el.querySelector('button,input,select,a,details'))middleLabel(el,text,!el.closest('button,a'));
  });
 }
}
let smartSequence=0;
function enhanceSelect(select){
 if(select.multiple)return;if(select.closest('.smart-select')){select.dispatchEvent(new Event('smart-sync'));return;}
 const label=(select.getAttribute('aria-label')||select.closest('label')?.querySelector('span')?.textContent||document.querySelector(`label[for="${select.id}"]`)?.textContent||'Выберите значение').trim();
 const wrap=document.createElement('div');wrap.className='smart-select';
 select.before(wrap);wrap.append(select);select.classList.add('smart-native');select.tabIndex=-1;select.setAttribute('aria-hidden','true');
 const input=document.createElement('input');input.type='text';input.className='smart-input';input.autocomplete='off';input.setAttribute('role','combobox');input.setAttribute('aria-label',label);input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','false');
 const list=document.createElement('div');list.className='smart-options';list.id='smart-options-'+(++smartSequence);list.setAttribute('role','listbox');list.hidden=true;input.setAttribute('aria-controls',list.id);
 input.id='smart-input-'+smartSequence;const owner=select.closest('label')||[...document.querySelectorAll('label[for]')].find(el=>el.htmlFor===select.id);if(owner)owner.htmlFor=input.id;
 wrap.append(input);const display=document.createElement('span');display.className='smart-display';display.setAttribute('aria-hidden','true');wrap.append(display);wrap.insertAdjacentHTML('beforeend','<svg class="smart-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 8.5 7 7 7-7"/></svg>');wrap.append(list);
 let choices=[],active=-1;
 const normalized=s=>s.toLocaleLowerCase('ru').replaceAll('ё','е');
 const sync=()=>{input.value=select.selectedOptions[0]?.textContent||'';input.disabled=select.disabled;input.title=input.value;middleLabel(display,input.value);};
 function close(){list.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');sync();}
 function highlight(index){active=index;for(const [i,el] of [...list.querySelectorAll('[role=option]')].entries())el.classList.toggle('highlighted',i===active);const el=list.querySelectorAll('[role=option]')[active];if(el&&choices.length){input.setAttribute('aria-activedescendant',el.id);el.scrollIntoView({block:'nearest'});}}
 function choose(index){const item=choices[index];if(!item)return;select.value=item.value;close();select.dispatchEvent(new Event('input',{bubbles:true}));select.dispatchEvent(new Event('change',{bubbles:true}));queueMicrotask(sync);}
 function show(query=''){
  document.querySelectorAll('.smart-input[aria-expanded="true"]').forEach(el=>{if(el!==input)el.dispatchEvent(new Event('smart-close'));});
  choices=[...select.options].filter(o=>!o.disabled&&normalized(o.textContent).includes(normalized(query)));list.replaceChildren();
  let group='';
  choices.forEach((o,i)=>{const name=o.parentElement.tagName==='OPTGROUP'?o.parentElement.label:'';if(name&&name!==group){const heading=document.createElement('div');heading.className='smart-group';heading.textContent=name;heading.setAttribute('role','presentation');list.append(heading);}group=name;const el=document.createElement('div');el.className='smart-option';el.id=list.id+'-'+i;el.setAttribute('role','option');el.setAttribute('aria-selected',String(o.selected));el.textContent=o.textContent;el.addEventListener('mousedown',e=>e.preventDefault());el.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();choose(i);});list.append(el);});
  if(!choices.length){const el=document.createElement('div');el.className='smart-empty';el.textContent='Ничего не найдено';list.append(el);}
  list.hidden=false;input.setAttribute('aria-expanded','true');active=-1;input.removeAttribute('aria-activedescendant');
 }
 sync();input.addEventListener('focus',()=>{show();input.select();});input.addEventListener('click',()=>{if(list.hidden)show();});input.addEventListener('input',()=>show(input.value));input.addEventListener('smart-close',close);input.addEventListener('blur',close);
 input.addEventListener('keydown',e=>{
  if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();if(list.hidden)show();if(choices.length)highlight((active+(e.key==='ArrowDown'?1:-1)+choices.length)%choices.length);}
  if(e.key==='Enter'&&!list.hidden){e.preventDefault();choose(active>=0?active:choices.length===1?0:-1);}
  if(e.key==='Escape'){e.preventDefault();e.stopPropagation();close();}
  if(e.key==='Tab')close();
 });
 select.addEventListener('change',()=>queueMicrotask(sync));select.addEventListener('smart-sync',sync);
}
function fieldLabel(el){return (el.closest('label')?.querySelector('span')?.textContent||el.getAttribute('aria-label')||el.name||'Обязательное поле').replace(/\s*\*\s*$/,'').trim();}
function markInvalid(el){el.setAttribute('aria-invalid','true');el.closest('.field')?.classList.add('field-invalid');}
function clearInvalid(el){const field=el.closest('.field');el.removeAttribute('aria-invalid');field?.classList.remove('field-invalid');field?.querySelectorAll('[aria-invalid]').forEach(item=>item.removeAttribute('aria-invalid'));}
function validationMessage(labels){labels=[...new Set(labels)];return labels.length===1?'Пожалуйста, заполните поле «'+labels[0]+'».':'Пожалуйста, заполните поля:\n'+labels.map(s=>'• «'+s+'»').join('\n');}
function validateInputs(root){
 const controls=[...root.querySelectorAll('input,select,textarea')].filter(el=>!el.classList.contains('smart-input')&&!el.disabled);
 const invalid=controls.filter(el=>{const bad=(el.required&&(!el.value.trim()||el.type==='checkbox'&&!el.checked))||!el.checkValidity();if(bad)markInvalid(el);else clearInvalid(el);return bad;});
 if(!invalid.length)return true;
 for(const control of invalid){for(let parent=control.parentElement;parent&&parent!==root;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;}
 const missing=invalid.filter(el=>el.required&&!el.value.trim());
 notice(missing.length===invalid.length?validationMessage(invalid.map(fieldLabel)):'Пожалуйста, проверьте заполнение полей:\n'+invalid.map(el=>'• «'+fieldLabel(el)+'»').join('\n'));
 const el=invalid[0];(el.closest('.smart-select')?.querySelector('.smart-input')||el).focus();return false;
}
function showWorkspaceErrors(fields){
 const first=fields[0]?.path||'';
 if(first.startsWith('object.'))navigate('object');
 if(first.startsWith('participants.')){orgIndex=Number(first.split('.')[1]);navigate('participants');}
 if(first.startsWith('projects.'))navigate('rd');
 for(const field of fields){const el=[...document.querySelectorAll('[data-path]')].find(el=>el.dataset.path===field.path);if(el)markInvalid(el);}
 const target=document.querySelector('[aria-invalid="true"]');target?.focus();
}
function updateDatabaseStatus(state){const el=document.querySelector('#database-status');if(!el||el.dataset.state===state)return;el.dataset.state=state;el.querySelector('span').textContent={ready:'База подключена',offline:'Нет связи с базой',session:'Сеанс завершён',checking:'Проверка базы…'}[state];}
async function checkDatabaseStatus(){
 if(!token||sessionSuspended)return;
 const requestToken=token;
 try{const response=await fetch('/api/status',{headers:{'X-ITD-Token':token},signal:AbortSignal.timeout(5000)});if(response.status===403){updateDatabaseStatus('session');if(requestToken&&token===requestToken)suspendWorkspace();return;}const value=await response.json();updateDatabaseStatus(response.ok&&value.database==='ready'?'ready':'offline');}
 catch(_){updateDatabaseStatus('offline');}
}
document.addEventListener('input',e=>{if(e.target.closest('.field-invalid'))clearInvalid(e.target);});
document.addEventListener('change',e=>{if(e.target.closest('.field-invalid'))clearInvalid(e.target);});

function closeAgentHelp(){document.querySelectorAll('.agent-help[open]').forEach(help=>help.open=false);}
// Capture нужен и для пунктов списков, которые останавливают всплытие клика.
document.addEventListener('click',e=>{if(!e.target.closest('.agent-help'))closeAgentHelp();},true);
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeAgentHelp();});
document.addEventListener('change',e=>{if(e.target.matches('#object-select,#project-select'))closeAgentHelp();},true);

// Общие правила таблиц: одна типографика и одинаковое поведение во всех вкладках.
function displayTableDate(value){return /^\d{4}-\d{2}-\d{2}$/.test(value||'')?value.split('-').reverse().join('.'):value;}
function formatTableNumber(value){return typeof value==='number'&&Number.isFinite(value)?new Intl.NumberFormat('ru-RU',{maximumFractionDigits:3,useGrouping:false}).format(value):value;}
function tableColumnType(label){
 if(/^(по проекту|приход|поступило|поставлено|использовано|зарезервировано|доступный остаток|списано|выделено|остаток|проект$|факт$|смонтировано|количество|кол-во|объем|объём|записей$|строка$|в актах$)/i.test(label))return 'number';
 if(/дата|начало|окончание|передан заказчику|срок устранения/i.test(label)&&!/журнал|документ/i.test(label))return 'date';
 return /^(выбор|отметка)$/i.test(label)?'check':'text';
}
function addTableFiller(table){
 table.querySelectorAll('[data-table-fill]').forEach(el=>el.remove());
 const head=table.tHead?.rows[0];if(!head)return;
 const count=head.cells.length;
 const filler=document.createElement('th');filler.dataset.tableFill='';filler.className='table-fill';filler.setAttribute('aria-hidden','true');head.append(filler);
 for(const body of table.tBodies)for(const row of body.rows){
  if(row.cells.length===1&&(row.cells[0].colSpan>1||row.cells[0].classList.contains('empty'))){row.cells[0].colSpan=count+1;continue;}
  if(row.cells.length!==count)continue;
  const cell=document.createElement('td');cell.dataset.tableFill='';cell.className='table-fill';cell.setAttribute('aria-hidden','true');row.append(cell);
 }
}
function decorateDataTables(root=document){
 const scrolls=root.matches?.('.table-scroll')?[root]:root.querySelectorAll('.table-scroll');
 scrolls.forEach(scroll=>{
  scroll.tabIndex=0;scroll.setAttribute('role','region');scroll.setAttribute('aria-label','Таблица. Прокрутите для просмотра всех колонок');
  const table=scroll.querySelector('table');if(!table||scroll.closest('[data-version-table]'))return;
  table.querySelectorAll('[data-table-fill]').forEach(el=>el.remove());
  const headers=[...table.querySelectorAll('thead th')];
  const nameIndex=headers.findIndex(th=>/наименование|название|описание|материал|содержание|ресурс|работы|журнал|документ/i.test(th.textContent));
  const stickyIndex=headers.findIndex(th=>!th.querySelector('input')&&tableColumnType(th.textContent)!=='check');
  headers.forEach((th,i)=>{
   const type=tableColumnType(th.textContent.trim());
   const cells=[th,...[...table.tBodies].flatMap(body=>[...body.rows].filter(row=>row.cells.length===headers.length&&row.cells[i].colSpan===1).map(row=>row.cells[i]))];
   cells.forEach(cell=>{
    cell.classList.remove('text-left','text-right','text-center','sticky-actions','table-number','table-date','table-text','table-check');
    cell.classList.add('table-'+type,type==='number'?'text-right':['date','check'].includes(type)?'text-center':'text-left');
    cell.classList.toggle('tabular-nums',type==='number'||type==='date');cell.classList.toggle('sticky-name',i===stickyIndex);cell.classList.toggle('name-column',i===nameIndex);
    if(cell.tagName==='TH')return;
    const walker=document.createTreeWalker(cell,NodeFilter.SHOW_TEXT);let node;
    while(node=walker.nextNode()){
     if(node.parentElement.closest('button,a,select,textarea,[data-full-text]'))continue;
     const text=node.textContent.trim();
     if(type==='number'&&/^-?\d+(?:[.,]\d+)?(?:e[+-]?\d+)?$/i.test(text))node.textContent=String(formatTableNumber(Number(text.replace(',','.'))));
     if(type==='date')node.textContent=node.textContent.replace(/\b\d{4}-\d{2}-\d{2}\b/g,displayTableDate);
    }
   });
  });
  tableCellLabels(table);addTableFiller(table);
  if(typeof enhanceDataTable==='function')enhanceDataTable(table);
 });
}
const tableObserver=new MutationObserver(records=>{
 const affected=new Set();
 for(const record of records){
  const owner=record.target.closest?.('.table-scroll');if(owner)affected.add(owner);
  for(const node of record.addedNodes)if(node.nodeType===1){if(node.matches('.table-scroll'))affected.add(node);node.querySelectorAll('.table-scroll').forEach(el=>affected.add(el));}
  for(const node of record.removedNodes)if(node.nodeType===1){if(node.matches('.middle-label'))middleObserver.unobserve(node);node.querySelectorAll('.middle-label').forEach(el=>middleObserver.unobserve(el));}
 }
 if(!affected.size)return;
 tableObserver.disconnect();affected.forEach(scroll=>{if(scroll.isConnected)decorateDataTables(scroll);});observeTables();
});
function observeTables(){for(const id of ['content','editor-content','knowledge-results']){const el=document.getElementById(id);if(el)tableObserver.observe(el,{childList:true,subtree:true});}}
observeTables();
function tableLoading(){
 const saved=[...document.querySelectorAll('#content table tbody')].map(body=>({body,html:body.innerHTML}));
 tableObserver.disconnect();
 saved.forEach(({body})=>{const count=body.closest('table').querySelectorAll('th').length||5;body.innerHTML=Array.from({length:4},()=>'<tr aria-hidden="true">'+Array.from({length:count},()=>'<td><span class="table-skeleton"></span></td>').join('')+'</tr>').join('');body.closest('.table-scroll').setAttribute('aria-busy','true');});
 return ()=>{saved.forEach(({body,html})=>{if(body.isConnected){body.innerHTML=html;body.closest('.table-scroll').removeAttribute('aria-busy');}});decorateDataTables();observeTables();};
}

// Подсказка открывается клавиатурой или нажатием; Escape и клик снаружи закрывают её.
document.addEventListener('click',e=>{document.querySelectorAll('.help-tip[open]').forEach(tip=>{if(!tip.contains(e.target))tip.open=false;});},true);
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.help-tip[open]').forEach(tip=>{tip.open=false;});});

document.addEventListener('click',e=>{
 const el=e.target?.closest?.('[data-expand-text]');if(!el)return;
 const expanded=el.getAttribute('aria-expanded')!=='true';
 el.setAttribute('aria-expanded',String(expanded));el.classList.toggle('text-expanded',expanded);
 if(expanded)el.textContent=el.dataset.fullText;else refreshMiddleLabel(el);
});
document.addEventListener('keydown',e=>{const el=e.target?.closest?.('[data-expand-text]');if(el&&['Enter',' '].includes(e.key)){e.preventDefault();el.click();}});

// One accessible upload surface for the section, RD, quality and resource import.
function uploadZone(id,label,{multiple=false,accept='',maxMB=32,extra=''}={}){
 return `<div class="file-drop" data-upload-target="${id}" role="group" aria-label="${esc(label)}"><span class="drop-icon">${icon('upload')}</span><p>Перетащите ${multiple?'файлы':'файл'} сюда</p><span class="hint">или выберите на компьютере · до ${maxMB} МБ${multiple?' на файл':''}</span><div class="toolbar"><button type="button" data-pick-file="${id}">${esc(label)}</button>${extra}</div><input hidden tabindex="-1" aria-label="${esc(label)}" type="file" id="${id}" ${multiple?'multiple':''} accept="${accept}" data-max-mb="${maxMB}"></div>`;
}
function validateUploadFiles(input,files){
 if(!input.multiple&&files.length>1)throw Error('Выберите один файл.');
 const accepted=input.accept.split(',').filter(Boolean);
 for(const file of files){
  if(file.size>Number(input.dataset.maxMb||32)*1024*1024)throw Error('Слишком большой файл: '+file.name);
  if(accepted.length&&!accepted.some(ext=>file.name.toLowerCase().endsWith(ext)))throw Error('Допустимы '+input.accept+': '+file.name);
 }
}
document.addEventListener('click',e=>{const pick=e.target.closest('[data-pick-file]');if(pick)document.getElementById(pick.dataset.pickFile)?.click();});
document.addEventListener('change',e=>{
 if(!e.target.matches('input[type="file"][data-max-mb]'))return;
 try{validateUploadFiles(e.target,[...e.target.files]);}catch(error){e.stopImmediatePropagation();e.target.value='';notice(error.message);}
},true);
for(const name of ['dragenter','dragover','dragleave','drop'])document.addEventListener(name,e=>{
 const zone=e.target.closest('[data-upload-target]');if(!zone||!(Array.from(e.dataTransfer?.types||[]).includes('Files')))return;
 e.preventDefault();
 if(name==='dragenter'||name==='dragover'){zone.classList.add('drag');e.dataTransfer.dropEffect='copy';return;}
 if(name==='dragleave'){if(!zone.contains(e.relatedTarget))zone.classList.remove('drag');return;}
 zone.classList.remove('drag');
 try{
  if([...e.dataTransfer.items].some(item=>item.webkitGetAsEntry?.()?.isDirectory))throw Error('Перетащите файлы, а не папку.');
  const input=document.getElementById(zone.dataset.uploadTarget),files=[...e.dataTransfer.files];
  validateUploadFiles(input,files);const transfer=new DataTransfer();files.forEach(file=>transfer.items.add(file));input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));
 }catch(error){notice(error.message);}
});

// Поиск не меняет выбранные отметки: скрываются только несовпавшие строки.
function enhanceCheckLists(){
 document.querySelectorAll('.check-list').forEach((list,index)=>{
  if(list.previousElementSibling?.matches('[data-check-search]'))return;
  const field=document.createElement('label');field.className='field check-search';field.dataset.checkSearch='';
  const input=document.createElement('input');input.type='search';input.placeholder='Найти в списке…';input.setAttribute('aria-label','Поиск: '+(list.previousElementSibling?.textContent||'элементы'));
  const empty=document.createElement('p');empty.className='small check-search-empty';empty.textContent='Ничего не найдено';empty.hidden=true;list.append(empty);
  input.addEventListener('input',()=>{const words=input.value.toLocaleLowerCase('ru').replaceAll('ё','е').trim().split(/\s+/).filter(Boolean);const rows=[...list.querySelectorAll('.choice')];rows.forEach(row=>{const text=row.textContent.toLocaleLowerCase('ru').replaceAll('ё','е');row.hidden=!words.every(w=>text.includes(w));});empty.hidden=!rows.length||rows.some(r=>!r.hidden);});
  field.append(input);list.before(field);
 });
}

function enhanceEditorActions(){
 document.querySelectorAll('#editor-content form').forEach(form=>{
  if(form.querySelector('.ux-form-actions'))return;
  const buttons=[...form.children].filter(el=>el.tagName==='BUTTON');
  if(!buttons.length)return;
  const bar=document.createElement('div');bar.className='ux-form-actions';buttons[0].before(bar);buttons.forEach(b=>bar.append(b));
 });
}

// Действия вынесены из области прокрутки и остаются связаны со своей формой.
function mountDialogFooter(){
 const content=document.getElementById('editor-content'),footer=document.getElementById('editor-footer');if(!content||!footer)return;
 enhanceEditorActions();enhanceCheckLists();
 const bar=content.querySelector('.ux-form-actions');
 if(bar){const form=bar.closest('form');if(form){if(!form.id)form.id='dialog-active-form';bar.querySelectorAll('button').forEach(button=>button.setAttribute('form',form.id));bar.dataset.ownerForm=form.id;}footer.replaceChildren(bar);footer._sourceElement=content.firstElementChild;}
 else if(footer._sourceElement&&!content.contains(footer._sourceElement))footer.replaceChildren();
 footer.hidden=!footer.childElementCount;
}
const dialogBodyObserver=new MutationObserver(()=>mountDialogFooter());
dialogBodyObserver.observe(document.getElementById('editor-content'),{childList:true,subtree:true});
