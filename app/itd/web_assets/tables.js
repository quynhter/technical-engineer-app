'use strict';
// Shared browsing controls; editor tables remain ordinary forms.
const dataTableModels=new WeakMap(),dataTablePreferences=new Map();
const tablePreferenceKey='itd.tablePreferences',tableSizes=[25,50,100];
const tableCollator=new Intl.Collator('ru',{numeric:true,sensitivity:'base'});
function tableText(cell){
  const copy=cell.cloneNode(true);
  copy.querySelectorAll('[data-full-text]').forEach(el=>el.textContent=el.dataset.fullText);
  return copy.textContent.trim();
}
function parseTableNumber(value){const text=value.replace(/\s/g,'').replace(',','.');return /^-?\d+(\.\d+)?$/.test(text)?Number(text):null;}
function isoTableDate(value){return /^\d{2}\.\d{2}\.\d{4}$/.test(value)?value.split('.').reverse().join('-'):'';}
function compareTableValues(a,b,type){
  if(type==='number'){
   const x=parseTableNumber(a),y=parseTableNumber(b);if(x!==null&&y!==null)return x-y;
  }
  if(type==='date')return tableCollator.compare(isoTableDate(a),isoTableDate(b));
  return tableCollator.compare(a,b);
}
function readTablePreferences(){
  try{const value=JSON.parse(localStorage.getItem(tablePreferenceKey)||'{}');return value&&typeof value==='object'?value:{};}catch(_){return {};}
}
function savedTablePreferences(key,columnCount){
  const saved=readTablePreferences()[key]||{};
  return {
   sort:Number.isInteger(saved.sort)&&saved.sort>=0&&saved.sort<columnCount?saved.sort:-1,
   direction:saved.direction===-1?-1:1,
   size:tableSizes.includes(saved.size)?saved.size:50,
   compact:saved.compact===true,
   hiddenColumns:normalizeHiddenTableColumns(saved.hiddenColumns,columnCount),
   widths:normalizeTableWidths(saved.widths,columnCount)
  };
}
function rememberDataTable(model){
  try{
   const store=readTablePreferences(),{prefs,key}=model;
   delete store[key];
   store[key]={sort:prefs.sort,direction:prefs.direction,size:prefs.size,compact:prefs.compact,hiddenColumns:prefs.hiddenColumns||[],widths:prefs.widths||{}};
   const keys=Object.keys(store);keys.slice(0,Math.max(0,keys.length-100)).forEach(k=>delete store[k]);
   localStorage.setItem(tablePreferenceKey,JSON.stringify(store));
  }catch(_){}
}
// Keep at least one data column visible, even with stale browser preferences.
function normalizeHiddenTableColumns(value,count){
 const hidden=[...new Set(Array.isArray(value)?value.filter(i=>Number.isInteger(i)&&i>=0&&i<count):[])];
 return hidden.length>=count?hidden.slice(0,Math.max(0,count-1)):hidden;
}
function normalizeTableWidths(value,count){
 const widths={};
 if(value&&typeof value==='object'&&!Array.isArray(value))for(const [i,width] of Object.entries(value)){
  if(/^\d+$/.test(i)&&Number(i)<count&&Number.isFinite(width)&&width>=80&&width<=900)widths[i]=Math.round(width);
 }
 return widths;
}
function defaultTableWidth(th){
 if(th.querySelector('input')||tableColumnType(th.textContent)==='check')return 44;
 if(th.classList.contains('name-column'))return 320;
 return ({number:120,date:144})[tableColumnType(th.textContent)]||200;
}
function tablePageNumbers(page,pages){
 const numbers=new Set([1,pages]);
 for(let n=Math.max(1,page-1);n<=Math.min(pages,page+1);n++)numbers.add(n);
 const result=[];for(const n of [...numbers].sort((a,b)=>a-b)){
  const last=result[result.length-1];
  if(last&&n-last===2)result.push(last+1);else if(last&&n-last>2)result.push(null);
  result.push(n);
 }
 return result;
}
function renderTablePages(model,pages){
 const host=model.footer.querySelector('.table-page-numbers');
 const html=tablePageNumbers(model.prefs.page+1,pages).map(n=>n===null?'<span class="table-page-gap" aria-hidden="true">…</span>':`<button type="button" class="table-page" data-table-control="page" data-page="${n-1}" aria-label="Страница ${n}"${n===model.prefs.page+1?' aria-current="page"':''}>${n}</button>`).join('');
 if(host.innerHTML===html)return;
 const focused=host.contains(document.activeElement);host.innerHTML=html;
 if(focused)host.querySelector('[aria-current="page"]')?.focus({preventScroll:true});
}
function applyTableWidths(table,model){
 let group=table.querySelector('colgroup[data-table-widths]');
 if(!group){group=document.createElement('colgroup');group.dataset.tableWidths='';table.prepend(group);}
 const visible=model.headers.map((th,i)=>({th,i})).filter(({th})=>!th.hidden);
 // Assign individual CSS properties: markup style attributes are blocked by the server CSP.
 // Reuse columns while dragging so layout updates do not rebuild the table structure.
 if(group.children.length!==visible.length+1)group.replaceChildren(...Array.from({length:visible.length+1},()=>document.createElement('col')));
 visible.forEach(({th,i},index)=>{
  const width=(model.prefs.widths?.[i]||defaultTableWidth(th))+'px';
  if(group.children[index].style.width!==width)group.children[index].style.width=width;
 });
 for(const body of table.tBodies)for(const row of body.rows){
  if(row.cells.length===1&&row.cells[0].colSpan>1)row.cells[0].colSpan=visible.length+1;
 }
 const width=visible.reduce((sum,{th,i})=>sum+(model.prefs.widths?.[i]||defaultTableWidth(th)),32);
 table.style.setProperty('--table-width',width+'px');table.classList.add('table-sized');
 model.headers.forEach((th,i)=>{const handle=th.querySelector('.table-column-resize');if(handle)handle.setAttribute('aria-valuenow',String(model.prefs.widths?.[i]||defaultTableWidth(th)));});
}
function enhanceTableResize(table,model){
 model.headers.forEach((th,i)=>{
  if(th.querySelector('.table-column-resize')||th.querySelector('input')||tableColumnType(th.textContent)==='check')return;
  const handle=document.createElement('span');handle.className='table-column-resize';handle.tabIndex=0;
  handle.setAttribute('role','separator');handle.setAttribute('aria-orientation','vertical');handle.setAttribute('aria-label','Ширина столбца «'+tableLabel(model.headers,i)+'»');
  handle.setAttribute('aria-valuemin','80');handle.setAttribute('aria-valuemax','900');
  handle.title='Потяните для изменения ширины. Стрелки ← → — 10 пкс, Shift — 50 пкс. Home или двойной щелчок — исходная ширина.';
  const current=()=>model.prefs.widths?.[i]||defaultTableWidth(th);
  const set=width=>{model.prefs.widths??={};model.prefs.widths[i]=Math.max(80,Math.min(900,Math.round(width)));applyTableWidths(table,model);};
  const reset=()=>{if(model.prefs.widths)delete model.prefs.widths[i];applyTableWidths(table,model);rememberDataTable(model);};
  handle.addEventListener('click',e=>e.stopPropagation());
  handle.addEventListener('dblclick',reset);
  handle.addEventListener('keydown',e=>{
   if(!['ArrowLeft','ArrowRight','Home'].includes(e.key))return;e.preventDefault();e.stopPropagation();
   if(e.key==='Home')return reset();
   set(current()+(e.key==='ArrowRight'?1:-1)*(e.shiftKey?50:10));rememberDataTable(model);
  });
  let drag=null;
  handle.addEventListener('pointerdown',e=>{
   if(e.button!==0)return;e.preventDefault();e.stopPropagation();
   drag={x:e.clientX,width:current(),saved:model.prefs.widths?.[i]};handle.setPointerCapture(e.pointerId);handle.classList.add('resizing');
  });
  handle.addEventListener('pointermove',e=>{if(drag)set(drag.width+e.clientX-drag.x);});
  const finish=e=>{
   if(!drag)return;
   if(e.type==='pointercancel'){if(drag.saved===undefined)delete model.prefs.widths?.[i];else model.prefs.widths[i]=drag.saved;applyTableWidths(table,model);}
   else rememberDataTable(model);
   drag=null;handle.classList.remove('resizing');
  };
  handle.addEventListener('pointerup',finish);handle.addEventListener('pointercancel',finish);handle.addEventListener('lostpointercapture',finish);
  th.append(handle);
 });
}
function applyTableColumns(table,model){
 const hidden=new Set(model.prefs.hiddenColumns||[]);
 const sticky=model.headers.findIndex((th,i)=>!hidden.has(i)&&!th.querySelector('input')&&tableColumnType(th.textContent)!=='check');
 model.headers.forEach((th,i)=>{
  // Selection remains available regardless of the displayed data columns.
  const hide=hidden.has(i)&&!th.querySelector('input')&&tableColumnType(th.textContent)!=='check';
  const cells=[th,...model.rows.filter(row=>row.cells.length>=model.headers.length&&row.cells[i]?.colSpan===1).map(row=>row.cells[i])];
  cells.forEach(cell=>{cell.hidden=hide;cell.classList.toggle('sticky-name',i===sticky);});
 });
}
function openTableSettings(table,model){
 const dialog=document.createElement('dialog');dialog.id='table-settings-dialog';dialog.className='workspace-dialog workspace-dialog--settings';
 dialog.setAttribute('aria-labelledby','table-settings-title');
 const columns=model.headers.map((th,i)=>({th,i})).filter(({th})=>!th.querySelector('input')&&tableColumnType(th.textContent)!=='check');
 dialog.innerHTML=`<div class="dialog-bar"><h2 class="dialog-title" id="table-settings-title">Настроить список</h2><button type="button" class="secondary" data-dialog-close aria-label="Закрыть настройки списка">×</button></div><div class="dialog-content"><p class="hint">Выберите столбцы для этой таблицы. Ширину можно менять здесь или перетаскиванием границ заголовков. Настройки сохраняются в этом браузере.</p><fieldset class="table-column-options"><legend>Видимые столбцы</legend>${columns.map(({th,i})=>`<div class="table-column-option"><label class="choice"><input type="checkbox" data-column="${i}" ${model.prefs.hiddenColumns?.includes(i)?'':'checked'}>${esc(th.textContent.trim())}</label><label class="table-column-width"><span class="sr">Ширина: ${esc(th.textContent.trim())}, пиксели</span><input type="number" min="80" max="900" step="1" data-column-width="${i}" value="${model.prefs.widths?.[i]||defaultTableWidth(th)}"><span aria-hidden="true">пкс</span></label></div>`).join('')}</fieldset><label class="choice"><input type="checkbox" data-table-density ${model.prefs.compact?'checked':''}>Компактные строки</label><p role="alert" data-column-error></p><div class="toolbar"><button type="button" data-apply-columns>Применить</button><button type="button" class="secondary" data-default-columns>Все столбцы</button><button type="button" class="secondary" data-reset-widths>Исходная ширина</button><button type="button" class="secondary" data-dialog-close>Отмена</button></div></div>`;
 document.body.append(dialog);
 const opener=model.controls.querySelector('[data-table-control="settings"]');
 const window=createWorkspaceDialog(dialog.id,{onClose:()=>{dialog.remove();if(opener?.isConnected)opener.focus();}});
 dialog.querySelector('[data-default-columns]').addEventListener('click',()=>dialog.querySelectorAll('[data-column]').forEach(box=>box.checked=true));
 dialog.querySelector('[data-reset-widths]').addEventListener('click',()=>dialog.querySelectorAll('[data-column-width]').forEach(input=>input.value=defaultTableWidth(model.headers[Number(input.dataset.columnWidth)])));
 dialog.querySelector('[data-apply-columns]').addEventListener('click',()=>{
  const boxes=[...dialog.querySelectorAll('[data-column]')];
  if(!boxes.some(box=>box.checked)){dialog.querySelector('[data-column-error]').textContent='Оставьте хотя бы один столбец.';boxes[0]?.focus();return;}
  const widths=[...dialog.querySelectorAll('[data-column-width]')];
  const invalid=widths.find(input=>!input.value||!input.checkValidity());
  if(invalid){dialog.querySelector('[data-column-error]').textContent='Ширина столбца должна быть целым числом от 80 до 900 пкс.';invalid.focus();return;}
  model.prefs.widths=Object.fromEntries(widths.map(input=>[input.dataset.columnWidth,Number(input.value)]));
  model.prefs.hiddenColumns=boxes.filter(box=>!box.checked).map(box=>Number(box.dataset.column));
  model.prefs.compact=dialog.querySelector('[data-table-density]').checked;
  applyDataTable(table,model);rememberDataTable(model);window.close();
 });
 window.open();
}
function tableLabel(headers,i){return headers[i]?.textContent.trim()||'';}
function isDataRow(row){return !row.querySelector('.empty')&&!row.classList.contains('date-group');}
function rowTexts(model,row){
  if(!model.values.has(row))model.values.set(row,[...row.cells].slice(0,model.headers.length).map(tableText));
  return model.values.get(row);
}
function tableFilterColumns(model,data){
  const result=[];
  model.headers.forEach((th,i)=>{
   const type=tableColumnType(th.textContent);
   if(th.querySelector('input')||type==='check'||type==='number')return;
   const texts=data.map(row=>rowTexts(model,row)[i]||'');
   if(type==='date'||texts.some(text=>/^\d{2}\.\d{2}\.\d{4}$/.test(text))){result.push({index:i,kind:'date'});return;}
   const distinct=[...new Set(texts.filter(Boolean))];
   if(distinct.length>=2&&distinct.length<=25&&distinct.length<data.length)result.push({index:i,kind:'select',options:distinct.sort((a,b)=>tableCollator.compare(a,b))});
  });
  return result;
}
function buildTableFilters(model){
  const {prefs,headers,fieldBox}=model;
  if(model.nativeFields)return;
  const data=model.rows.filter(isDataRow);
  model.filterable=model.native?[]:tableFilterColumns(model,data);
  const find=(i,kind)=>model.filterable.find(c=>String(c.index)===i&&c.kind===kind);
  for(const i of Object.keys(prefs.dates))if(!find(i,'date'))delete prefs.dates[i];
  for(const i of Object.keys(prefs.filters))if(!find(i,'select')?.options.includes(prefs.filters[i]))delete prefs.filters[i];
  if(!fieldBox)return;
  fieldBox.innerHTML=model.filterable.map(col=>{
   const label=esc(tableLabel(headers,col.index));
   if(col.kind==='date')return `<fieldset class="table-date-range"><legend>${label}</legend><label class="field"><span>С</span><input type="date" data-table-date="${col.index}" data-edge="from" aria-label="${label}: с" value="${esc(prefs.dates[col.index]?.from||'')}"></label><label class="field"><span>По</span><input type="date" data-table-date="${col.index}" data-edge="to" aria-label="${label}: по" value="${esc(prefs.dates[col.index]?.to||'')}"></label></fieldset>`;
   return `<label class="field"><span>${label}</span><select data-table-filter="${col.index}"><option value="">Все</option>${col.options.map(v=>`<option value="${esc(v)}"${v===prefs.filters[col.index]?' selected':''}>${esc(v)}</option>`).join('')}</select></label>`;
  }).join('');
  fieldBox.querySelectorAll('select').forEach(enhanceSelect);
  const disclosure=fieldBox.closest('details');if(disclosure)disclosure.hidden=!model.filterable.length;
}
function renderTableChips(model){
  const {prefs,headers,chipBox}=model;
  const label=i=>tableLabel(headers,i);
  const chips=[];
  if(prefs.query.trim())chips.push({chip:'query',text:`Поиск: ${prefs.query.trim()}`});
  for(const [i,value] of Object.entries(prefs.filters))chips.push({chip:'filter:'+i,text:`${label(i)}: ${value}`});
  for(const [i,range] of Object.entries(prefs.dates))chips.push({chip:'date:'+i,text:`${label(i)}: ${range.from?displayTableDate(range.from):'начало'} – ${range.to?displayTableDate(range.to):'конец'}`});
  const html=chips.map(c=>`<button type="button" class="table-chip" data-table-control="chip" data-chip="${esc(c.chip)}" aria-label="Убрать условие: ${esc(c.text)}">${esc(c.text)}<span aria-hidden="true"> ×</span></button>`).join('')+(chips.length?'<button type="button" class="ghost" data-table-control="reset">Сбросить все</button>':'');
  if(chipBox.innerHTML!==html)chipBox.innerHTML=html;
}
function renderTableTotals(model,matched){
  const {headers,totalBox}=model,parts=[];
  const unitIndex=headers.findIndex(th=>/^(ед\.?\s*изм\.?|единица измерения)$/i.test(th.textContent.trim()));
  headers.forEach((th,i)=>{
   if(tableColumnType(th.textContent)!=='number'||/^(строка|записей)/i.test(th.textContent.trim()))return;
   const sums=new Map();
   for(const row of matched){
    const texts=rowTexts(model,row),n=parseTableNumber(texts[i]||'');if(n===null)continue;
    const unit=unitIndex>=0?(texts[unitIndex]||'без ед. изм.'):'';
    sums.set(unit,(sums.get(unit)||0)+n);
   }
   for(const [unit,sum] of sums)parts.push(`${tableLabel(headers,i)}: ${formatTableNumber(Math.round(sum*1000)/1000)}${unit?' '+unit:''}`);
  });
  totalBox.textContent=parts.length&&matched.length?`Итого по отфильтрованным записям (${matched.length}) · ${parts.join(' · ')}`:'';
}
function tableCsvValue(value){return `"${String(value).replaceAll('"','""')}"`;}
function tableExportName(table){
  const title=table.closest('.card')?.querySelector('h2,h3')?.textContent.trim()||'Таблица';
  return title.replace(/[\\/:*?"<>|]+/g,' ').replace(/\s+/g,' ').trim()||'Таблица';
}
function downloadTableCsv(table,model,rows,name=tableExportName(table)){
  const columns=model.headers.map((th,i)=>({th,i})).filter(({th})=>!th.querySelector('input')&&tableColumnType(th.textContent)!=='check');
  const lines=[columns.map(({th})=>tableCsvValue(th.textContent.trim())).join(';')];
  for(const row of rows)lines.push(columns.map(({i})=>tableCsvValue(rowTexts(model,row)[i]??'')).join(';'));
  const url=URL.createObjectURL(new Blob(['\uFEFF'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=`${name}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function resetDataTable(model){
  const {prefs,controls}=model;
  Object.assign(prefs,{query:'',sort:-1,direction:1,page:0,filters:{},dates:{}});
  const search=controls.querySelector('[type="search"]');if(search)search.value='';
}
function removeTableChip(model,chip){
  const {prefs,controls}=model,[kind,i]=chip.split(':');
  if(kind==='query'){prefs.query='';const search=controls.querySelector('[type="search"]');if(search)search.value='';}
  else if(kind==='filter')delete prefs.filters[i];
  else if(kind==='date')delete prefs.dates[i];
  prefs.page=0;
}
function rowSelectionId(row){return row.dataset?.rowId??'';}
function handleTableChange(table,model,e){
  const el=e.target,{prefs}=model;
  if(el.dataset.tableFilter!==undefined){if(el.value)prefs.filters[el.dataset.tableFilter]=el.value;else delete prefs.filters[el.dataset.tableFilter];prefs.page=0;return applyDataTable(table,model);}
  if(el.dataset.tableDate!==undefined){const i=el.dataset.tableDate,range={...(prefs.dates[i]||{})};range[el.dataset.edge]=el.value;if(range.from||range.to)prefs.dates[i]=range;else delete prefs.dates[i];prefs.page=0;return applyDataTable(table,model);}
  const task=el.dataset.tableControl;
  if(task==='size'){prefs.size=Number(el.value);prefs.page=0;}
  else if(task==='compact')prefs.compact=el.checked;
  else if(task==='sort-select'){
   if(el.value){const [index,direction]=el.value.split(':');prefs.sort=Number(index);prefs.direction=Number(direction);}else prefs.sort=-1;
   prefs.page=0;
  }else return;
  applyDataTable(table,model);rememberDataTable(model);
}
function handleTableClick(table,model,e){
  const button=e.target.closest('[data-table-control]');if(!button)return;
  const task=button.dataset.tableControl,{prefs}=model;
  if(task==='settings')return openTableSettings(table,model);
  if(task==='prev')prefs.page--;
  else if(task==='next')prefs.page++;
  else if(task==='page')prefs.page=Number(button.dataset.page);
  else if(task==='reset'){resetDataTable(model);}
  else if(task==='chip')removeTableChip(model,button.dataset.chip);
  else if(task==='export')downloadTableCsv(table,model,model.matched);
  else if(task==='export-selected')downloadTableCsv(table,model,model.rows.filter(row=>isDataRow(row)&&model.selected.has(rowSelectionId(row))));
  else if(task==='clear-selection')model.selected.clear();
  else return;
  applyDataTable(table,model);
  if(task==='reset')rememberDataTable(model);
}
function handleRowSelection(table,model,e){
  const el=e.target;
  if(el.dataset.rowSelect!==undefined){el.checked?model.selected.add(el.dataset.rowSelect):model.selected.delete(el.dataset.rowSelect);}
  else if(el.hasAttribute('data-select-visible')){
   for(const row of model.matched){const id=rowSelectionId(row);if(id)el.checked?model.selected.add(id):model.selected.delete(id);}
  }else return;
  applyDataTable(table,model);
}
function enhanceDataTable(table){
  if(!table.closest('#content')||table.closest('form,[data-version-table]')||!table.tHead||!table.tBodies[0])return;
  if(typeof enhanceRowDeletion==='function')enhanceRowDeletion(table);
  const scroll=table.closest('.table-scroll'),body=table.tBodies[0];
  const headers=[...table.tHead.rows[0].cells].filter(cell=>!cell.hasAttribute('data-table-fill'));
  let model=dataTableModels.get(table);
  if(!model){
   const context=[projectId,workspaceView,journalSection,resourcePanel,packagePanel];
   const key=JSON.stringify([...context,headers.map(th=>th.textContent.trim()),[...document.querySelectorAll('#content table')].indexOf(table)]);
   const prefs=dataTablePreferences.get(key)||{query:'',page:0,filters:{},dates:{},...savedTablePreferences(key,headers.length)};
   dataTablePreferences.set(key,prefs);
   if(dataTablePreferences.size>100)dataTablePreferences.delete(dataTablePreferences.keys().next().value);
   const card=scroll.closest('.card');
   const nativeSearch=card?.querySelector('[data-filter="search"]');
   const sortable=headers.map((th,i)=>({th,i})).filter(({th})=>!th.querySelector('input')&&tableColumnType(th.textContent)!=='check');
   const controls=document.createElement('div');controls.className='data-table-controls';
   controls.innerHTML=`<label class="field data-table-search"><span>Поиск в таблице</span><input type="search" data-table-control="search" placeholder="Поиск по всем столбцам…"></label><label class="field table-sort-mobile"><span>Сортировка</span><select data-table-control="sort-select"><option value="">Без сортировки</option>${sortable.flatMap(({th,i})=>[`<option value="${i}:1">${esc(th.textContent.trim())} ↑</option>`,`<option value="${i}:-1">${esc(th.textContent.trim())} ↓</option>`]).join('')}</select></label><button type="button" class="secondary" data-table-control="settings">Настроить список</button><button type="button" class="secondary" data-table-control="export">Экспорт CSV</button>`;
   const footer=document.createElement('div');footer.className='data-table-footer';
   footer.innerHTML='<div class="table-footer-line"><span class="table-count" role="status" aria-live="polite"></span><nav class="table-pagination" aria-label="Страницы таблицы"><button type="button" class="table-page table-page-direction" data-table-control="prev" aria-label="Предыдущая страница таблицы">‹</button><div class="table-page-numbers"></div><button type="button" class="table-page table-page-direction" data-table-control="next" aria-label="Следующая страница таблицы">›</button></nav><label class="field table-page-size"><span>На странице</span><select data-table-control="size"><option value="25">25</option><option value="50">50</option><option value="100">100</option></select></label></div>';
   const panel=document.createElement('div');panel.className='data-table-panel';
   panel.innerHTML=`<details class="table-filter-disclosure"><summary>Фильтр</summary><div class="data-table-filters"></div></details><div class="data-table-chips"></div><div class="table-totals" aria-live="polite"></div>${table.hasAttribute('data-selectable')?'<div class="table-selection" hidden><span>Выбрано: <b data-selected-count>0</b></span><button type="button" class="secondary" data-table-control="export-selected">Экспорт выбранных в CSV</button><button type="button" class="secondary" data-table-control="clear-selection">Снять выбор</button></div>':''}`;
   const nativeFilters=card?.querySelector('.table-filters');
   const nativeCount=card?.querySelector('#table-count');
   if(nativeCount)nativeCount.hidden=true;
   if(nativeSearch){nativeSearch.type='search';controls.querySelector('[data-table-control="search"]').replaceWith(nativeSearch);}
   const fieldBox=panel.querySelector('.data-table-filters');
   if(nativeFilters){fieldBox.append(...nativeFilters.children);nativeFilters.remove();}
   scroll.before(controls);controls.after(panel);scroll.after(footer);
   const selection=panel.querySelector('.table-selection');if(selection)footer.append(selection);
   const totals=panel.querySelector('.table-totals');footer.prepend(totals);
   model={key,prefs,controls,footer,panel,headers,nativeFields:Boolean(nativeFilters),nativeCount,native:Boolean(card?.querySelector('[data-filter]')),selectable:table.hasAttribute('data-selectable'),rows:[],values:new WeakMap(),selected:new Set(),matched:[],filterable:[],
    fieldBox:panel.querySelector('.data-table-filters'),chipBox:panel.querySelector('.data-table-chips'),totalBox:footer.querySelector('.table-totals'),selectionBox:footer.querySelector('.table-selection')};
   dataTableModels.set(table,model);
   controls.querySelector('[data-table-control="search"]')?.setAttribute('value',prefs.query);
   footer.querySelector('select[data-table-control="size"]').value=String(prefs.size);
   let timer;
   controls.addEventListener('input',e=>{if(e.target.dataset.tableControl!=='search')return;clearTimeout(timer);timer=setTimeout(()=>{prefs.query=e.target.value;prefs.page=0;applyDataTable(table,model);},180);});
   controls.addEventListener('change',e=>handleTableChange(table,model,e));
   footer.addEventListener('change',e=>handleTableChange(table,model,e));
   footer.addEventListener('click',e=>handleTableClick(table,model,e));
   footer.querySelectorAll('select').forEach(enhanceSelect);
   panel.addEventListener('change',e=>handleTableChange(table,model,e));
   controls.addEventListener('click',e=>handleTableClick(table,model,e));
   panel.addEventListener('click',e=>handleTableClick(table,model,e));
   table.addEventListener('click',e=>handleTableClick(table,model,e));
   table.addEventListener('change',e=>handleRowSelection(table,model,e));
   controls.querySelectorAll('select[data-table-control]').forEach(enhanceSelect);
  }
  const rows=[...body.rows].filter(row=>!row.querySelector('.table-skeleton'));
  const known=new Set(model.rows);
  if(!model.filtersBuilt||model.rows.length!==rows.length||rows.some(row=>!known.has(row))){model.rows=rows;model.values=new WeakMap();buildTableFilters(model);model.filtersBuilt=true;}
  headers.forEach((th,index)=>{
   if(th.querySelector('button')||tableColumnType(th.textContent)==='check'||th.querySelector('input'))return;
   const button=document.createElement('button');button.type='button';button.dataset.tableControl='sort';button.className='table-sort';button.textContent=th.textContent.trim();button.title='Сортировать по колонке';
   th.replaceChildren(button);button.addEventListener('click',()=>{const p=model.prefs;p.direction=p.sort===index?-p.direction:1;p.sort=index;p.page=0;applyDataTable(table,model);rememberDataTable(model);});
  });
  enhanceTableResize(table,model);
  applyDataTable(table,model);
}
function applyDataTable(table,model){
  const {prefs,controls,headers}=model,body=table.tBodies[0];
  const data=model.rows.filter(isDataRow);
  const dataSet=new Set(data);
  const query=prefs.query.toLocaleLowerCase('ru').replaceAll('ё','е').trim();
  const type=tableColumnType(headers[prefs.sort]?.textContent||'');
  const compare=(a,b)=>prefs.direction*compareTableValues(rowTexts(model,a)[prefs.sort]||'',rowTexts(model,b)[prefs.sort]||'',type);
  const passes=row=>{
   const texts=rowTexts(model,row);
   for(const [i,value] of Object.entries(prefs.filters))if(texts[i]!==value)return false;
   for(const [i,range] of Object.entries(prefs.dates)){const iso=isoTableDate(texts[i]||'');if(range.from&&(!iso||iso<range.from))return false;if(range.to&&(!iso||iso>range.to))return false;}
   return texts.join(' ').toLocaleLowerCase('ru').replaceAll('ё','е').includes(query);
  };
  // Rows are sorted inside each date group, so group headers keep their order and stay above their rows.
  const segments=[{header:null,rows:[]}];
  for(const row of model.rows){if(row.classList.contains('date-group'))segments.push({header:row,rows:[]});else segments[segments.length-1].rows.push(row);}
  const matched=[],ordered=[];
  for(const segment of segments){
   const hits=segment.rows.filter(row=>dataSet.has(row)&&passes(row));
   if(prefs.sort>=0)hits.sort(compare);
   const hitSet=new Set(hits);
   if(segment.header)ordered.push(segment.header);
   ordered.push(...hits,...segment.rows.filter(row=>!hitSet.has(row)));
   matched.push(...hits);
  }
  model.matched=matched;
  const pages=Math.max(1,Math.ceil(matched.length/prefs.size));prefs.page=Math.max(0,Math.min(prefs.page,pages-1));
  const shown=new Set(matched.slice(prefs.page*prefs.size,(prefs.page+1)*prefs.size));
  if(model.footer&&model.lastPage!==prefs.page){table.closest('.table-scroll').scrollTop=0;model.lastPage=prefs.page;}
  // Only reorder when necessary, so the shared MutationObserver settles after one pass.
  if(ordered.some((row,i)=>body.rows[i]!==row))body.append(...ordered);
  model.rows=ordered;
  for(const segment of segments){
   if(segment.header)segment.header.hidden=!segment.rows.some(row=>shown.has(row));
   for(const row of segment.rows)row.hidden=!shown.has(row);
  }
  for(const row of model.rows)if(isDataRow(row))[...row.cells].slice(0,headers.length).forEach((cell,i)=>{cell.dataset.label=tableLabel(headers,i);});
  const empty=model.rows.find(row=>row.querySelector('.empty'));if(empty)empty.hidden=data.length>0;
  const total=Number(model.nativeCount?.dataset.total)||data.length;
  const filtered=query.length>0||Object.keys(prefs.filters).length>0||Object.keys(prefs.dates).length>0||total!==data.length;
  let noMatch=body.querySelector('[data-table-no-match]');
  if(data.length&&!matched.length&&!noMatch){noMatch=document.createElement('tr');noMatch.dataset.tableNoMatch='';const cell=document.createElement('td');cell.colSpan=table.tHead.rows[0].cells.length;cell.className='empty';cell.innerHTML='По заданным условиям записей нет. Измените поиск или <button type="button" class="secondary" data-table-control="reset">сбросьте условия</button>.';noMatch.append(cell);body.append(noMatch);}
  if(noMatch)noMatch.hidden=matched.length>0||!data.length;
  const start=matched.length?prefs.page*prefs.size+1:0,end=Math.min((prefs.page+1)*prefs.size,matched.length);
  const text=`${start}–${end} из ${matched.length}${filtered?' · всего '+total:''}`;
  const pagination=model.footer||controls;
  const count=pagination.querySelector('[role="status"]');if(count.textContent!==text)count.textContent=text;
  pagination.querySelector('[data-table-control="prev"]').disabled=prefs.page===0;
  pagination.querySelector('[data-table-control="next"]').disabled=prefs.page+1>=pages;
  controls.querySelector('[data-table-control="export"]').disabled=!matched.length;
  headers.forEach((th,i)=>th.setAttribute('aria-sort',i===prefs.sort?(prefs.direction===1?'ascending':'descending'):'none'));
  table.classList.toggle('table-compact',prefs.compact);
  if(model.footer){applyTableColumns(table,model);applyTableWidths(table,model);renderTablePages(model,pages);}
  const sortValue=prefs.sort>=0?`${prefs.sort}:${prefs.direction}`:'';
  const sortSelect=controls.querySelector('[data-table-control="sort-select"]');
  if(sortSelect&&sortSelect.value!==sortValue){sortSelect.value=sortValue;sortSelect.dispatchEvent(new Event('smart-sync'));}
  if(model.fieldBox){
   model.fieldBox.querySelectorAll('[data-table-filter]').forEach(select=>{const value=prefs.filters[select.dataset.tableFilter]||'';if(select.value!==value){select.value=value;select.dispatchEvent(new Event('smart-sync'));}});
   model.fieldBox.querySelectorAll('[data-table-date]').forEach(input=>{const value=prefs.dates[input.dataset.tableDate]?.[input.dataset.edge]||'';if(input.value!==value)input.value=value;});
  }
  if(model.nativeFields){
   const active=[...model.fieldBox.querySelectorAll('[data-filter]')].filter(el=>el.type==='checkbox'?el.checked:el.value).length;
   model.fieldBox.closest('details').querySelector('summary').textContent='Фильтр'+(active?' ('+active+')':'');
  }
  if(model.chipBox)renderTableChips(model);
  if(model.totalBox)renderTableTotals(model,matched);
  if(model.selectable){
   const ids=new Set(model.rows.map(rowSelectionId));
   for(const id of [...model.selected])if(!ids.has(id))model.selected.delete(id);
   for(const row of model.rows){const box=row.querySelector('[data-row-select]');if(box)box.checked=model.selected.has(rowSelectionId(row));}
   const picked=matched.filter(row=>model.selected.has(rowSelectionId(row))).length;
   const all=table.querySelector('[data-select-visible]');
   if(all){all.checked=matched.length>0&&picked===matched.length;all.indeterminate=picked>0&&picked<matched.length;}
   if(model.selectionBox){model.selectionBox.hidden=!model.selected.size;model.selectionBox.querySelector('[data-selected-count]').textContent=model.selected.size;}
  }
}
