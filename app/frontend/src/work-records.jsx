import React,{useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {Banner,Button,Card,CheckboxInput,DateInput,Heading,Skeleton} from '@astryxdesign/core';
import {BrowseTable} from './astryx-tables.jsx';
import {createApiClient,saveFile as defaultSaveFile} from './api-v1.mjs';
import {workCsv,workLabels,workRows,workSearch,workSources,workValues} from './work-table.mjs';

const emptyFilters={unbound:false,group:false,from:'',to:''};
export function WorkRecords({projectId,role,workspaceId='',getToken,onSessionExpired,api:providedApi,onChanged,onOpen,onCreate,onCreateAct,onActPreview,onDelete,initialSelected=[],onSelectionChange,initialFilters={},onFiltersChange,isDirty=()=>false,saveFile=defaultSaveFile}){
 const api=useMemo(()=>providedApi||createApiClient({getToken,onSessionExpired}),[providedApi,getToken,onSessionExpired]);
 const [project,setProject]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState(''),[retry,setRetry]=useState(0),[query,setQuery]=useState(initialFilters.search||''),[filters,setFilters]=useState(()=>({...emptyFilters,...initialFilters})),[chosen,setChosen]=useState(()=>new Set(initialSelected.map(Number)));
 const generation=useRef(0),selected=useRef(chosen);
 useEffect(()=>{const current=++generation.current,controller=new AbortController();setProject(null);setLoading(true);setError('');
  api.json('/project?project_id='+encodeURIComponent(projectId),undefined,{signal:controller.signal}).then(value=>{if(controller.signal.aborted||generation.current!==current)return;
   const allowed=new Set((value.workspace_entries||[]).filter(item=>item.kind==='work'&&!item.act_id).map(item=>item.id));const next=new Set([...selected.current].filter(id=>allowed.has(id)));selected.current=next;setChosen(next);onSelectionChange?.([...next]);setProject(value);onChanged?.(value);
  }).catch(err=>{if(!controller.signal.aborted&&generation.current===current)setError(err.message);}).finally(()=>{if(!controller.signal.aborted&&generation.current===current)setLoading(false);});
  return()=>controller.abort();
 },[api,projectId,workspaceId,retry]);
 useEffect(()=>{onFiltersChange?.({...filters,search:query});},[filters,query,onFiltersChange]);
 const perform=useCallback(async(callback,...args)=>{if(isDirty()){setError('Сначала сохраните изменения.');return;}try{await callback?.(...args);}catch(err){setError(err.message);}},[isDirty]);
 const choose=useCallback((items,checked)=>{const next=new Set(selected.current);for(const item of items){const entry=item._source;if(!entry.act_id)checked?next.add(entry.id):next.delete(entry.id);}selected.current=next;setChosen(next);onSelectionChange?.([...next]);},[onSelectionChange]);
 const resetFilters=useCallback(()=>setFilters({...emptyFilters}),[]);
 const headers=useMemo(()=>[...workLabels.map((label,index)=>({key:'c'+index,index,label,type:index===0?'date':'text'})),...(role!=='viewer'&&onDelete?[{key:'actions',index:6,label:'Действия',type:'text',action:true}]:[])],[role,onDelete]);
 const entries=useMemo(()=>project?workRows(project,filters):[],[project,filters]);
 const rows=useMemo(()=>entries.map(entry=>{const values=workValues(entry,project),sources=workSources(entry,project);const content=values.map((text,index)=>({text,content:index===1?<div><Button label={entry.title||'Открыть работу'} variant="ghost" onClick={()=>perform(onOpen,entry,project)}/>{entry.details&&<p className="hint">{entry.details}</p>}</div>:index===5?<div className="work-links"><div className="record-link"><span className="record-link-label">Акт</span>{entry.act_id?<Button label={sources.act} variant="ghost" onClick={()=>perform(onActPreview,entry.act_id)}/>:<span>Не сформирован</span>}</div><div className="record-link"><span className="record-link-label">Источник</span><span title={sources.attachment||undefined}>{sources.attachment||'Не указан'}</span></div></div>:text}));
  if(role!=='viewer'&&onDelete)content.push({text:'',content:<Button label="Удалить" aria-label={'Удалить запись: '+entry.title} variant="destructive" onClick={()=>perform(onDelete,'workspace_entries',entry.id)}/>});
  return {_key:String(entry.id),_source:entry,_label:'Работа № '+entry.id+': '+entry.title,_checkbox:entry.act_id?undefined:{disabled:false},_checked:!entry.act_id&&chosen.has(entry.id),_group:filters.group?(entry.entry_date?workValues(entry,project)[0]:'Дата не указана'):undefined,_search:workSearch(entry,project),_cells:content,...Object.fromEntries(values.map((value,i)=>['c'+i,value]))};
 }),[entries,project,role,onDelete,chosen,filters.group,perform,onOpen,onActPreview]);
 const extraFilters=<div className="grid"><CheckboxInput label="Только работы без актов" value={filters.unbound} onChange={value=>setFilters(previous=>({...previous,unbound:value}))}/><CheckboxInput label="Группировать по дате" value={filters.group} onChange={value=>setFilters(previous=>({...previous,group:value}))}/><DateInput label="Дата с" value={filters.from||undefined} onChange={value=>setFilters(previous=>({...previous,from:value||''}))}/><DateInput label="Дата по" value={filters.to||undefined} onChange={value=>setFilters(previous=>({...previous,to:value||''}))}/></div>;
 const snapshot={key:'work-api-v1:'+workspaceId+':'+projectId+':'+role,title:'Сведения о выполнении работ',headers,rows,selectable:true,hasGroups:filters.group,showTotals:false,initialQuery:initialFilters.search||'',onQueryChange:setQuery,extraFilters,resetExtraFilters:resetFilters,syncChoices:choose,
  exportRows:items=>saveFile({blob:new Blob([workCsv(items,project)],{type:'text/csv;charset=utf-8'}),filename:'Сведения о выполнении работ.csv'}),
 };
 return <Card padding={4} data-work-api="v1"><Heading level={2} hasCapsize={false}>Сведения о выполнении работ</Heading>
  <div className="toolbar">{role!=='viewer'&&<><Button label="Добавить запись" isDisabled={loading||!project} onClick={()=>perform(onCreate)}/>{chosen.size>0&&<Button label="Сформировать акт" variant="secondary" onClick={()=>perform(onCreateAct)}/>}</>}<Button label="Экспорт" variant="secondary" isDisabled={loading||!project} onClick={()=>saveFile({blob:new Blob([JSON.stringify(workRows(project,{...filters,query}),null,2)],{type:'application/json'}),filename:'Записи журналов.json'})}/></div>
  {error&&<Banner title="Не удалось выполнить операцию" description={error} status="error"/>}
  {loading?<Skeleton aria-label="Загрузка работ" height={160}/>:project?<BrowseTable key={snapshot.key} snapshot={snapshot}/>:<Button label="Повторить загрузку" variant="secondary" onClick={()=>setRetry(n=>n+1)}/>}
 </Card>;
}
