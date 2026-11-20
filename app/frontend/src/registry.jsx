import React,{useEffect,useMemo,useRef,useState} from 'react';
import {Banner,Button,Card,Heading,Skeleton} from '@astryxdesign/core';
import {BrowseTable} from './astryx-tables.jsx';
import {createApiClient,saveFile as defaultSaveFile} from './api-v1.mjs';

const labels=['№ п/п','Наименование документа','Номер и дата документа','Организация, составившая документ','Кол-во листов','Номера страниц'];
const headers=labels.map((label,index)=>({key:'c'+index,index,label,type:[0,4].includes(index)?'number':'text',total:index!==0}));
function values(item){const date=/^\d{4}-\d{2}-\d{2}$/.test(item.date||'')?item.date.split('-').reverse().join('.'):item.date;return [item.no,item.name,[item.number,date].filter(v=>v!==null&&v!==undefined&&v!=='').join('. '),item.organization,item.sheets_count,item.pages].map(value=>String(value??''));}
export function registryCsv(items){return '\ufeff'+[labels,...items.map(values)].map(row=>row.map(value=>'"'+String(value).replace(/^[=+\-@\t\r]/,"'$&").replaceAll('"','""')+'"').join(';')).join('\r\n');}

export function Registry({projectId,role,workspaceId='',getToken,api:providedApi,onSessionExpired,onOpen,onDelete,onChanged,initialProject,isDirty=()=>false,saveFile=defaultSaveFile}){
 const api=useMemo(()=>providedApi||createApiClient({getToken,onSessionExpired}),[providedApi,getToken,onSessionExpired]);
 const [project,setProject]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false);
 const generation=useRef(0),locked=useRef(false),abort=useRef(null);
 useEffect(()=>{const current=++generation.current,controller=new AbortController();abort.current=controller;locked.current=false;setBusy(false);setProject(null);setError('');setLoading(true);
  (initialProject?Promise.resolve(initialProject):api.json('/project?project_id='+encodeURIComponent(projectId),undefined,{signal:controller.signal})).then(value=>{if(generation.current===current&&!controller.signal.aborted){setProject(value);onChanged?.(value);}}).catch(err=>{if(!controller.signal.aborted&&generation.current===current)setError(err.message);}).finally(()=>{if(!controller.signal.aborted&&generation.current===current)setLoading(false);});
  return()=>controller.abort();
 },[api,projectId,workspaceId]);
 useEffect(()=>{if(initialProject){setProject(initialProject);setLoading(false);}},[initialProject]);
 async function exportZip(){
  if(locked.current||role==='viewer')return;
  const current=generation.current,signal=abort.current.signal;
  locked.current=true;setBusy(true);setError('');
  try{
   if(isDirty())throw Error('Сначала сохраните изменения.');
   const file=await api.download('/package?project_id='+encodeURIComponent(projectId),{signal,filename:'ИТД — актуальные файлы.zip'});
   if(!signal.aborted&&generation.current===current)saveFile(file);
  }catch(err){if(!signal.aborted&&generation.current===current)setError(err.message);}
  finally{if(generation.current===current&&!signal.aborted){locked.current=false;setBusy(false);}}
 }
 const allowDelete=role!=='viewer'&&!!onDelete;
 const tableHeaders=useMemo(()=>[...headers,...(allowDelete?[{key:'actions',index:6,label:'Действия',type:'text',action:true}]:[])],[allowDelete]);
 const snapshot=useMemo(()=>({key:'registry-api-v1:'+workspaceId+':'+projectId+':'+role,title:'Реестр ИД',headers:tableHeaders,selectable:true,hasGroups:false,
  rows:(project?.registry||[]).map((item,index)=>{const cells=values(item),entity={act:'acts',scheme:'schemes',attachment:'attachments',release:'releases'}[item.entity];return {_key:item.entity+':'+item.id+':'+index,_source:item,_checkbox:{disabled:false},_checked:false,_cells:[...cells.map((text,column)=>({text,content:column===1&&onOpen?<Button variant="ghost" label={text||'Открыть документ'} isDisabled={!!busy} onClick={()=>onOpen(item)}/>:text})),...(allowDelete?[{text:'',content:entity?<Button variant="destructive" label="Удалить" aria-label={'Удалить запись: '+(item.name||item.id)} isDisabled={!!busy} onClick={()=>{if(isDirty()){setError('Сначала сохраните изменения.');return;}onDelete(entity,item.id);}}/>:''}]:[])],_search:cells.join(' ').toLocaleLowerCase('ru').replaceAll('ё','е'),...Object.fromEntries(cells.map((value,i)=>['c'+i,value]))};}),
  menuItems:role==='viewer'?[]:[{label:'Экспорт ZIP',onClick:exportZip,isDisabled:busy}],
  exportRows:items=>saveFile({blob:new Blob([registryCsv(items)],{type:'text/csv;charset=utf-8'}),filename:'Реестр ИД.csv'}),syncChoices:(items,checked)=>items.forEach(item=>{item._checked=checked;}),
 }),[project,projectId,workspaceId,role,onOpen,onDelete,allowDelete,tableHeaders,busy,isDirty,saveFile,api]);
 return <Card padding={4} aria-label="Реестр ИД" data-registry-api="v1">
  <Heading level={2} hasCapsize={false}>Реестр ИД</Heading>
  {error&&<Banner title="Не удалось выполнить операцию" description={error} status="error"/>}
  {loading?<Skeleton aria-label="Загрузка реестра" height={160}/>:project?<BrowseTable key={snapshot.key} snapshot={snapshot}/>:<Button variant="secondary" label="Повторить загрузку" onClick={()=>{setLoading(true);setError('');const current=generation.current,signal=abort.current.signal;api.json('/project?project_id='+encodeURIComponent(projectId),undefined,{signal}).then(value=>{if(current===generation.current&&!signal.aborted){setProject(value);onChanged?.(value);}}).catch(err=>{if(current===generation.current&&!signal.aborted)setError(err.message);}).finally(()=>{if(current===generation.current&&!signal.aborted)setLoading(false);});}}/>}
 </Card>;
}
