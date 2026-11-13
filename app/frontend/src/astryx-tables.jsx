import React,{useState,useMemo,useEffect} from 'react';
import {Button,TextInput,CheckboxInput,Popover,Pagination,EmptyState} from '@astryxdesign/core';
import {Table,useTableColumnResize,useTableColumnSettings,useTableColumnSettingsState,useTableFiltering,useTableFilterState,toSearchFilters,useTableSortable,useTableSortableState,useTableGroupedRows,useTableSelection,pixel,proportional} from '@astryxdesign/core/Table';
import {usePowerSearchConfig} from '@astryxdesign/core/PowerSearch';

const collator=new Intl.Collator('ru',{numeric:true,sensitivity:'base'});
const preferenceKey='itd.astryx.tables.v1',memory=new Map();
function readPrefs(key){if(memory.has(key))return memory.get(key);try{return JSON.parse(localStorage.getItem(preferenceKey)||'{}')[key]||{};}catch(_){return {};}}
function savePrefs(key,value){memory.set(key,value);try{const all=JSON.parse(localStorage.getItem(preferenceKey)||'{}');delete all[key];all[key]=value;const keys=Object.keys(all);keys.slice(0,Math.max(0,keys.length-100)).forEach(k=>delete all[k]);localStorage.setItem(preferenceKey,JSON.stringify(all));}catch(_){}}
function plainCell(cell){const clone=cell.cloneNode(true);clone.querySelectorAll('[data-full-text]').forEach(el=>{el.textContent=el.dataset.fullText;el.classList.remove('middle-label');el.removeAttribute('data-expand-text');});clone.querySelectorAll('input[type=checkbox]').forEach((el,i)=>el.toggleAttribute('checked',cell.querySelectorAll('input[type=checkbox]')[i].checked));return {text:clone.textContent.trim(),html:clone.innerHTML};}
function cellContent(html){
 const template=document.createElement('template');template.innerHTML=html;
 function node(el,key){
  if(el.nodeType===3)return el.textContent;
  if(el.nodeType!==1)return null;
  if(el.tagName==='BUTTON'){
   const attrs=Object.fromEntries([...el.attributes].filter(a=>a.name.startsWith('data-')&&!['data-primitive','data-variant','data-size','data-elevation','data-astryx-pressable'].includes(a.name)||a.name==='title'||a.name==='aria-label').map(a=>[a.name,a.value]));
   const label=el.getAttribute('aria-label')||el.textContent.trim()||'Открыть';
   return <Button className="astryx-cell-action" key={key} label={label} variant={el.classList.contains('danger')?'destructive':'ghost'} {...attrs} isDisabled={el.disabled}><span dangerouslySetInnerHTML={{__html:el.innerHTML}}/></Button>;
  }
  if(el.querySelector('button'))return React.createElement(el.tagName.toLowerCase(),{key,className:el.className},[...el.childNodes].map((child,i)=>node(child,i)));
  return <span key={key} dangerouslySetInnerHTML={{__html:el.outerHTML}}/>;
 }
 return [...template.content.childNodes].map((el,i)=>node(el,i));
}
function Cell({html}){return useMemo(()=>cellContent(html),[html]);}
function BrowseTable({snapshot}){
 const {key,headers,rows,hasGroups,selectable,exportRows,syncChoices,nativeFilters}=snapshot;
 const saved=useMemo(()=>readPrefs(key),[key]);
 const [query,setQuery]=useState(saved.query||''),[page,setPage]=useState(1),[size,setSize]=useState([25,50,100].includes(saved.size)?saved.size:50),[widths,setWidths]=useState(saved.widths||{}),[sort,setSort]=useState(saved.sort||[]),[collapsed,setCollapsed]=useState(new Set()),[selected,setSelected]=useState(new Set(rows.filter(r=>r._checked).map(r=>r._key)));
 const allKeys=useMemo(()=>headers.map(h=>h.key),[headers]);
 const [activeKeys,setActiveKeys]=useState(()=>saved.activeKeys?.filter(k=>allKeys.includes(k))||allKeys);
 const columnOptions=useMemo(()=>headers.map((h,i)=>({key:h.key,label:h.label||'Действия',isAlwaysVisible:i===0})),[headers]);
 const columnState=useTableColumnSettingsState({columns:columnOptions,activeColumnKeys:activeKeys,onChangeActiveColumnKeys:setActiveKeys,defaultColumnKeys:allKeys});
 const settingsPlugin=useTableColumnSettings(columnState.columnSettingsConfig);
 const {filters,onFilterChange,clearAll}=useTableFilterState(saved.filters||{});
 const fields=useMemo(()=>headers.filter(h=>!h.action).map(h=>({key:h.key,type:'string',label:h.label})),[headers]);
 const {config,applyFilters}=usePowerSearchConfig(fields,'ИТД');
 const columns=useMemo(()=>headers.map(h=>({key:h.key,header:h.label,width:h.action?pixel(112):/наименование|название|описание|журнал|документ/i.test(h.label)?proportional(2,{minWidth:280}):pixel(h.type==='number'?140:h.type==='date'?160:180),resizable:!h.action,sortable:!h.action,filter:h.action?undefined:h.key,align:h.type==='number'?'end':h.type==='date'?'center':'start',renderCell:item=><Cell html={item._cells[h.index]?.html||''}/>})),[headers]);
 const filterPlugin=useTableFiltering({filters,onFilterChange,searchConfig:config,variant:'popover'});
 const resizePlugin=useTableColumnResize({columns,columnWidths:widths,onColumnResizeEnd:updates=>setWidths(previous=>({...previous,...updates})),minWidth:64,maxWidth:1200});
 const matched=useMemo(()=>{const filtered=applyFilters(toSearchFilters(filters,columns,config),rows),term=query.toLocaleLowerCase('ru').replaceAll('ё','е').trim();return term?filtered.filter(row=>row._search.includes(term)):filtered;},[applyFilters,filters,columns,config,rows,query]);
 const comparators=useMemo(()=>Object.fromEntries(headers.map(h=>[h.key,(a,b)=>{const x=a[h.key]||'',y=b[h.key]||'';if(h.type==='number'){const n=s=>Number(s.replace(/\s/g,'').replace(',','.'));if(x&&y&&Number.isFinite(n(x))&&Number.isFinite(n(y)))return n(x)-n(y);}if(h.type==='date'){const iso=s=>/^\d{2}\.\d{2}\.\d{4}$/.test(s)?s.split('.').reverse().join('-'):s;return collator.compare(iso(x),iso(y));}return collator.compare(x,y);} ])),[headers]);
 const {sortedData,sortConfig}=useTableSortableState({data:matched,sort,onSortChange:setSort,comparators,isMultiSortEnabled:true});
 const sortPlugin=useTableSortable(sortConfig);
 const pages=Math.max(1,Math.ceil(sortedData.length/size)),currentPage=Math.min(page,pages);
 const pageRows=useMemo(()=>sortedData.slice((currentPage-1)*size,currentPage*size),[sortedData,currentPage,size]);
 const grouped=useTableGroupedRows({data:pageRows,groupBy:row=>row._group,collapsedGroups:collapsed,onToggleGroup:key=>setCollapsed(prev=>{const next=new Set(prev);next.has(key)?next.delete(key):next.add(key);return next;}),getRowKey:row=>row._key});
 function choose(items,checked){setSelected(prev=>{const next=new Set(prev);items.forEach(row=>checked?next.add(row._key):next.delete(row._key));return next;});syncChoices(items,checked);}
 const selectionPlugin=useTableSelection({getIsItemSelected:row=>selected.has(row._key),onSelectItem:({item,isSelected})=>choose([item],isSelected),onSelectAll:({isAllSelected})=>choose(pageRows.filter(r=>r._checkbox&&!r._checkbox.disabled),isAllSelected),getIsAllSelected:()=>pageRows.some(r=>r._checkbox)&&pageRows.filter(r=>r._checkbox).every(r=>selected.has(r._key)),getIsIndeterminate:()=>pageRows.some(r=>selected.has(r._key))&&!pageRows.every(r=>selected.has(r._key)),getIsItemSelectable:row=>Boolean(row._checkbox),getIsItemEnabled:row=>!row._checkbox?.disabled,getRowLabel:row=>headers.map(h=>row[h.key]).find(Boolean)||'Запись'});
 const plugins={columnSettings:settingsPlugin,filter:filterPlugin,sort:sortPlugin,resize:resizePlugin,...(hasGroups?{group:grouped.plugin}:{}),...(selectable?{selection:selectionPlugin}:{})};
 useEffect(()=>{setPage(1);},[query,filters,size]);
 useEffect(()=>{savePrefs(key,{query,size,widths,activeKeys,sort,filters});},[key,query,size,widths,activeKeys,sort,filters]);
 useEffect(()=>{setSelected(new Set(rows.filter(r=>r._checked).map(r=>r._key)));},[rows]);
 const picked=rows.filter(row=>selected.has(row._key));
 const totals=useMemo(()=>{const unit=headers.find(h=>/^ед\.?\s*изм\.?$|единица измерения/i.test(h.label));return headers.filter(h=>h.type==='number').flatMap(h=>{const groups=new Map();for(const row of matched){const value=row[h.key].replace(/\s/g,'').replace(',','.');if(!/^-?\d+(\.\d+)?$/.test(value))continue;const u=unit?row[unit.key]:'';groups.set(u,(groups.get(u)||0)+Number(value));}return [...groups].map(([u,sum])=>`${h.label}: ${new Intl.NumberFormat('ru',{maximumFractionDigits:3}).format(sum)}${u?' '+u:''}`);}).join(' · ');},[headers,matched]);
 return <div className="astryx-table-workspace" data-table-hooks="columnResize columnSettings filtering">
  <div className="astryx-data-toolbar">
   <TextInput label="Поиск в таблице" value={query} onChange={setQuery} placeholder="Поиск по всем столбцам…" data-table-control="search" containerClassName="astryx-table-search"/>
   <Popover alignment="end" content={<div className="astryx-column-picker"><h3>Столбцы</h3>{columnOptions.map(option=><CheckboxInput key={option.key} label={option.label} value={columnState.isColumnActive(option.key)} isDisabled={!columnState.isColumnToggleable(option.key)} onChange={()=>columnState.toggleColumn(option.key)}/>)}<Button label="Показать все" variant="secondary" onClick={columnState.showAllColumns}/></div>}><Button label="Столбцы" variant="secondary" data-table-control="columns"/></Popover>
   <Button label="Экспорт CSV" variant="secondary" onClick={()=>exportRows(sortedData.map(r=>r._source))} isDisabled={!matched.length} data-table-control="export"/>
  </div>
  {!nativeFilters&&<details className="astryx-column-filters"><summary>Фильтр{Object.keys(filters).length?' ('+Object.keys(filters).length+')':''}</summary><div className="astryx-filter-fields">{fields.map(field=><TextInput key={field.key} label={field.label} value={String(filters[field.key]||'')} onChange={value=>onFilterChange(field.key,value||null)} data-table-control="filter"/>)}</div><Button label="Сбросить фильтры" variant="ghost" onClick={clearAll} data-table-control="reset"/></details>}
  <div className="astryx-data-grid"><Table data={hasGroups?grouped.data:pageRows} columns={columns} idKey={hasGroups?grouped.idKey:'_key'} plugins={plugins} density="balanced" hasHover textOverflow="truncate" aria-label={snapshot.title} emptyState={<EmptyState title={rows.length?'Нет совпадений':'Записей пока нет'} description={rows.length?'Измените поиск или условия фильтра.':'Добавьте первую запись кнопкой над таблицей.'}/>}/></div>
  <div className="astryx-data-footer">{totals&&<p className="astryx-table-totals">{totals}</p>}<div className="astryx-page-line"><span role="status">{matched.length?(currentPage-1)*size+1:0}–{Math.min(currentPage*size,matched.length)} из {matched.length}</span><Pagination page={currentPage} onChange={setPage} totalItems={matched.length} pageSize={size} pageSizeOptions={[25,50,100]} onPageSizeChange={setSize} label={'Страницы: '+snapshot.title}/></div>{picked.length>0&&<div className="astryx-table-selection"><span>Выбрано: {picked.length}</span><Button label="Экспорт выбранных" variant="secondary" onClick={()=>exportRows(picked.map(r=>r._source))}/><Button label="Снять выбор" variant="ghost" onClick={()=>choose(picked,false)}/></div>}</div>
 </div>;
}
export function createTableAdapter(mount){
 const states=new WeakMap();
 return function enhanceTable(table,model,exportRows){
  if(model._astryxSelecting)return;
  const scroll=table.closest('.table-scroll');if(!scroll)return;
  let state=states.get(table);if(!state){const host=document.createElement('div');host.className='astryx-data-view';scroll.after(host);state={host};states.set(table,state);}
  if(!state.host.isConnected)scroll.after(state.host);
  scroll.hidden=true;model.controls.hidden=true;model.footer.hidden=true;model.panel.hidden=!model.nativeFields;
  const sourceHeaders=model.headers.map((th,index)=>({index,key:'c'+index,label:th.textContent.trim(),type:th.classList.contains('table-number')?'number':th.classList.contains('table-date')?'date':'text',check:!!th.querySelector('input')||th.classList.contains('table-check'),action:th.hasAttribute('data-delete-column')}));
  const selectable=sourceHeaders.some(h=>h.check),headers=sourceHeaders.filter(h=>!selectable||!h.check);
  const admitted=new Set(model.matched);let group='';const rows=[];
  for(const [index,row] of model.rows.entries()){
   if(row.classList.contains('date-group')){group=row.textContent.trim();continue;}
   if(!admitted.has(row))continue;
   const cells=[...row.cells].map(plainCell),checkbox=row.querySelector('[data-row-select],[data-select-entry]');
   const item={_key:row.dataset.rowId||String(index),_source:row,_cells:cells,_group:group,_checkbox:checkbox,_checked:checkbox?.checked||false};
   for(const h of headers)item[h.key]=cells[h.index]?.text||'';
   item._search=cells.map(c=>c.text).join(' ').toLocaleLowerCase('ru').replaceAll('ё','е');rows.push(item);
  }
  const signature=JSON.stringify([headers,rows.map(row=>[row._key,row._search,row._group,row._checked,row._checkbox?.disabled,[...row._source.querySelectorAll('button')].map(b=>[...b.attributes].filter(a=>a.name.startsWith('data-')&&!['data-primitive','data-variant','data-size','data-elevation','data-astryx-pressable'].includes(a.name)).map(a=>[a.name,a.value]))])]);
  if(signature===state.signature)return;state.signature=signature;
  const snapshot={key:model.key,headers,rows,selectable,hasGroups:rows.some(r=>r._group),nativeFilters:model.nativeFields,title:scroll.closest('.card')?.querySelector('h2,h3')?.textContent.trim()||'Таблица',exportRows,syncChoices:(items,checked)=>{model._astryxSelecting=true;try{for(const row of items){const input=row._checkbox;if(input&&!input.disabled){input.checked=checked;input.dispatchEvent(new Event('change',{bubbles:true}));}}}finally{model._astryxSelecting=false;}state.signature=null;enhanceTable(table,model,exportRows);}};
  mount(state.host,<BrowseTable key={model.key} snapshot={snapshot}/>);
 };
}
