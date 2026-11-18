import React,{useEffect,useMemo,useRef,useState} from 'react';
import {Banner,Button,Card,Collapsible,Heading,Selector,Skeleton} from '@astryxdesign/core';
import {BrowseTable} from './astryx-tables.jsx';
import {createApiClient,saveFile as defaultSaveFile} from './api-v1.mjs';
import {installedValue,tableValue} from './table-values.js';

function factWork(item,project){const workId=item.work_entry_id||(project.work_materials||[]).find(material=>material.fact_id===item.id)?.entry_id;return (project.workspace_entries||[]).find(entry=>entry.id===workId);}
function resourceOptionLabel(item){const parts=[item.spec_num?'Поз. '+item.spec_num:null,item.name,item.type_mark].filter(Boolean);return parts.map((part,index)=>index===parts.length-1?part:String(part).trimEnd().replace(/\.+$/,'')).join('. ');}
const incomingResults={pending:'Проверка не завершена',accepted:'Входной контроль пройден',rejected:'Не принято'};

export const recordDefinitions={
 schemes:{title:'Схемы',create:'Добавить схему',entity:'schemes',nameIndex:1,selectable:true,
  headers:['Номер','Наименование','Референс','Комментарий'],rows:project=>project.schemes||[],values:item=>[item.num,item.name,item.ref_code,item.note]},
 documents:{title:'Основные документы',create:'Создать',import:'Загрузить',entity:'acts',nameIndex:1,selectable:true,types:{2:'date'},
  headers:['Номер','Название','Дата подписания','Статус'],rows:project=>(project.acts||[]).filter(item=>item.is_active),values:(item,project)=>[item.act_num,(project.forms||[]).find(form=>form.code===item.act_type)?.name||item.act_type,item.date_signed?(/^\d{4}-\d{2}-\d{2}$/.test(item.date_signed)?item.date_signed.split('-').reverse().join('.'):item.date_signed):'Не указана',(project.act_statuses||[]).find(status=>status.act_id===item.id)?.state==='signed'?'Подписан':'Сформирован']},
 resources:{title:'Спецификация',create:'Добавить ресурс',import:'Импорт Excel / CSV',importFirst:true,entity:'resources',nameIndex:1,types:{7:'number',8:'number'},
  headers:['Позиция','Наименование','Категория','Марка / тип','Производитель','Поставщик','Ед. изм.','По проекту','Смонтировано','Комментарий'],rows:project=>project.inventory||[],values:(item,project)=>[item.spec_num,item.name,item.category,item.type_mark,item.manufacturer,item.supplier,item.unit,tableValue(item.qty_proj),tableValue(installedValue(item,project.workflow?.facts?.find(fact=>fact.resource_id===item.id)).value),item.note]},
 facts:{title:'Факт монтажа',create:'Добавить факт',entity:'work_facts',nameIndex:5,types:{0:'date',2:'number'},canOpen:(item,project)=>!!factWork(item,project),
  headers:['Дата','Материал','Количество','Ед. изм.','Место','Работа в ОЖР','Статус'],rows:project=>(project.workflow?.fact_records||[]).filter(item=>item.status!=='void').sort((a,b)=>(b.end_date||b.start_date||'').localeCompare(a.end_date||a.start_date||'')),values:(item,project)=>[tableValue(item.end_date||item.start_date),(project.resources||[]).find(resource=>resource.id===item.resource_id)?.name,tableValue(item.quantity),item.unit,item.location,factWork(item,project)?.title||'',item.status==='confirmed'?'Подтверждён':'Ожидает проверки']},
 incoming:{title:'Входной контроль',create:'Добавить запись',entity:'workspace_entries',nameIndex:1,types:{0:'date',2:'number'},
  headers:['Дата','Ресурс','Количество','Ед. изм.','Результат','Примечание'],rows:project=>(project.journals?.incoming||[]).filter(item=>item.kind==='incoming').sort((a,b)=>(b.entry_date||'').localeCompare(a.entry_date||'')||b.id-a.id),values:item=>[tableValue(item.entry_date||''),item.resource?.name||item.title,tableValue(item.quantity??item.supply?.quantity),item.unit||item.supply?.unit||item.resource?.unit,incomingResults[item.work_fields?.incoming_result||'pending'],item.details]},
 cable:{title:'ЖПК',description:'Журнал прокладки кабеля',create:'Записать прокладку кабеля',entity:'workspace_entries',nameIndex:1,types:{0:'date'},
  headers:['Дата','Работа','Место'],rows:project=>(project.workspace_entries||[]).filter(item=>item.kind==='work'&&item.work_type==='cable'),values:item=>[tableValue(item.entry_date),item.title,item.details]},
};

export function ProjectRecords({kind,projectId,role,workspaceId='',getToken,onSessionExpired,api:providedApi,onOpen,onCreate,onImport,onDelete,onResource,onChanged,isDirty=()=>false,saveFile=defaultSaveFile}){
 const definition=recordDefinitions[kind];
 const api=useMemo(()=>providedApi||createApiClient({getToken,onSessionExpired}),[providedApi,getToken,onSessionExpired]);
 const [project,setProject]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState(''),[retry,setRetry]=useState(0),[resourceId,setResourceId]=useState('');
 const generation=useRef(0),abort=useRef(null);
 useEffect(()=>{const current=++generation.current,controller=new AbortController();abort.current=controller;setProject(null);setLoading(true);setError('');setResourceId('');
  api.json('/project?project_id='+encodeURIComponent(projectId),undefined,{signal:controller.signal}).then(value=>{if(!controller.signal.aborted&&current===generation.current){setProject(value);onChanged?.(value);}}).catch(err=>{if(!controller.signal.aborted&&current===generation.current)setError(err.message);}).finally(()=>{if(!controller.signal.aborted&&current===generation.current)setLoading(false);});
  return()=>controller.abort();
 },[api,projectId,workspaceId,kind,retry]);
 const editable=role!=='viewer';
 const headers=useMemo(()=>[...definition.headers.map((label,index)=>({key:'c'+index,index,label,type:definition.types?.[index]||'text'})),...(editable&&onDelete?[{key:'actions',index:definition.headers.length,label:'Действия',type:'text',action:true}]:[])],[definition,editable,onDelete]);
 const rows=project?definition.rows(project):[];
 async function perform(callback,...args){if(isDirty()){setError('Сначала сохраните изменения.');return;}try{await callback?.(...args);}catch(err){setError(err.message);}}
 const snapshot={key:kind+'-api-v1:'+workspaceId+':'+projectId+':'+role,title:definition.title,headers,selectable:!!definition.selectable,hasGroups:false,showTotals:true,
  rows:rows.map(item=>{const values=definition.values(item,project).map(v=>String(v??''));return {_key:String(item.id),_source:item,_checkbox:definition.selectable?{disabled:false}:undefined,_checked:false,_search:values.join(' ').toLocaleLowerCase('ru').replaceAll('ё','е'),
   ...Object.fromEntries(values.map((v,i)=>['c'+i,v])),_cells:[...values.map((text,index)=>({text,content:index===definition.nameIndex&&onOpen&&(!definition.canOpen||definition.canOpen(item,project))?<Button label={text||'Открыть запись'} variant="ghost" onClick={()=>perform(onOpen,item,project)}/>:text})),...(editable&&onDelete?[{text:'',content:<Button label="Удалить" aria-label={'Удалить запись: '+(values[definition.nameIndex]||item.id)} variant="destructive" onClick={()=>perform(onDelete,definition.entity,item.id)}/>}]:[])]};}),
  exportRows:items=>{const csv='\ufeff'+[definition.headers,...items.map(item=>definition.values(item,project))].map(row=>row.map(v=>'"'+String(v??'').replace(/^[=+\-@\t\r]/,"'$&").replaceAll('"','""')+'"').join(';')).join('\r\n');saveFile({blob:new Blob([csv],{type:'text/csv;charset=utf-8'}),filename:definition.title+'.csv'});},syncChoices:(items,checked)=>items.forEach(item=>{item._checked=checked;}),
 };
 return <Card padding={4} data-project-records={kind}><Heading level={2} hasCapsize={false}>{definition.title}</Heading>
  {definition.description&&<p>{definition.description}</p>}
  {editable&&(onCreate||onImport)&&<div className="toolbar">{(definition.importFirst?['import','create']:['create','import']).map(action=>action==='create'?(onCreate&&<Button key={action} label={definition.create} variant={definition.importFirst?'secondary':'primary'} onClick={()=>perform(onCreate)} isDisabled={loading||!project}/>):(onImport&&<Button key={action} label={definition.import} variant={definition.importFirst?'primary':'secondary'} onClick={()=>perform(onImport)} isDisabled={loading||!project}/>) )}</div>}
  {kind==='facts'&&!!project?.resources?.length&&<Collapsible trigger="Монтаж по ресурсу" defaultIsOpen={false}><Selector label="Ресурс" value={resourceId} options={[{value:'',label:'Выберите ресурс…'},...project.resources.map(item=>({value:String(item.id),label:resourceOptionLabel(item)}))]} onChange={setResourceId}/><Button label="Открыть монтаж по ресурсу" variant="secondary" onClick={()=>{if(!resourceId){setError('Выберите ресурс');return;}perform(onResource,Number(resourceId));}}/></Collapsible>}
  {error&&<Banner title="Не удалось выполнить операцию" description={error} status="error"/>}
  {loading?<Skeleton aria-label={'Загрузка: '+definition.title} height={140}/>:project?<BrowseTable key={snapshot.key} snapshot={snapshot}/>:<Button label="Повторить загрузку" variant="secondary" onClick={()=>setRetry(n=>n+1)}/>}
 </Card>;
}
