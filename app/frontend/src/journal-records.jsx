import React,{useEffect,useMemo,useState} from 'react';
import {Banner,Button,Card,Heading,Skeleton} from '@astryxdesign/core';
import {BrowseTable} from './astryx-tables.jsx';
import {createApiClient,saveFile as defaultSaveFile} from './api-v1.mjs';
import {journalBlocks} from './journal-model.mjs';
const toolLabels={export:'Экспорт в DOCX',participants:'Открыть участников строительства',participantsShort:'Открыть участников',assign:'Изменить назначения',special:'Добавить специальный журнал'};
const entryLabels={'1':'Добавить работника','4':'Внести проверку','6':'Добавить мероприятие'};
export function JournalBlock({block,context,editable,perform,onTool,onOpen,onDelete,saveFile}){
 const deletable=editable&&onDelete&&block.rows.some(row=>row.entity);
 const headers=[...block.headers.map((label,index)=>({key:'c'+index,index,label,type:block.types?.[index]||'text'})),...(deletable?[{key:'actions',index:block.headers.length,label:'Действия',type:'text',action:true}]:[])];
 const snapshot={key:context+':'+block.key,title:block.title,headers,hasGroups:false,selectable:false,
  rows:block.rows.map(row=>{const values=row.values.map(v=>String(v??''));return {_key:String(row.id),_source:row,_search:values.join(' ').toLocaleLowerCase('ru').replaceAll('ё','е'),...Object.fromEntries(values.map((v,i)=>['c'+i,v])),_cells:[...values.map((text,index)=>({text,content:row.action&&index===row.nameIndex?<Button label={text||'Открыть запись'} variant="ghost" onClick={()=>perform(onOpen,row.action,row.item)}/>:text})),...(deletable?[{text:'',content:row.entity?<Button label="Удалить" aria-label={'Удалить запись: '+(row.values[row.nameIndex??0]||row.id)} variant="destructive" onClick={()=>perform(onDelete,row.entity,row.recordId??row.id)}/>:null}]:[])]};}),
  exportRows:rows=>{const csv='\ufeff'+[block.headers,...rows.map(row=>row.values)].map(row=>row.map(v=>'"'+String(v??'').replace(/^[=+\-@\t\r]/,"'$&").replaceAll('"','""')+'"').join(';')).join('\r\n');saveFile({blob:new Blob([csv],{type:'text/csv;charset=utf-8'}),filename:block.title+'.csv'});},syncChoices:()=>{}};
 return <Card padding={4}><Heading level={2} hasCapsize={false}>{block.title}</Heading>{block.description&&<p className="hint">{block.description}</p>}<div className="toolbar">{block.tools?.filter(tool=>editable||!['assign','special','entry'].includes(tool)).map(tool=><Button key={tool} label={tool==='entry'?entryLabels[block.section]:toolLabels[tool]} variant="secondary" onClick={()=>perform(onTool,tool,block.section)}/>)}</div><BrowseTable key={snapshot.key} snapshot={snapshot}/></Card>;
}
export function JournalRecords({projectId,workspaceId='',role,section,roles={},getToken,onSessionExpired,api:providedApi,onChanged,initialProject,onTool,onOpen,onDelete,isDirty=()=>false,saveFile=defaultSaveFile}){
 const api=useMemo(()=>providedApi||createApiClient({getToken,onSessionExpired}),[providedApi,getToken,onSessionExpired]);
 const [project,setProject]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState(''),[retry,setRetry]=useState(0);
 useEffect(()=>{const controller=new AbortController();setProject(null);setLoading(true);setError('');(initialProject?Promise.resolve(initialProject):api.json('/project?project_id='+encodeURIComponent(projectId),undefined,{signal:controller.signal})).then(value=>{if(!controller.signal.aborted){setProject(value);onChanged?.(value);}}).catch(err=>{if(!controller.signal.aborted)setError(err.message);}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[api,projectId,workspaceId,section,retry]);
 useEffect(()=>{if(initialProject){setProject(initialProject);setLoading(false);}},[initialProject]);
 async function perform(callback,...args){if(isDirty()){setError('Сначала сохраните изменения.');return;}try{await callback?.(...args);}catch(err){setError(err.message);}}
 return <div className="workspace-stack" data-journal-api="v1">{error&&<Banner title="Не удалось выполнить операцию" description={error} status="error"/>}{loading?<Skeleton aria-label="Загрузка ОЖР" height={160}/>:project?journalBlocks(project,section,roles).map(block=><JournalBlock key={block.key} block={block} context={'ojr:'+workspaceId+':'+projectId+':'+role} editable={role!=='viewer'} perform={perform} onTool={onTool} onOpen={onOpen} onDelete={onDelete} saveFile={saveFile}/>):<Button label="Повторить загрузку" onClick={()=>setRetry(n=>n+1)}/>}</div>;
}
