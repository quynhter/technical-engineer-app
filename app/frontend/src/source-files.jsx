import React,{useEffect,useMemo,useRef,useState} from 'react';
import {Banner,Button,Card,Collapsible,Selector,Skeleton} from '@astryxdesign/core';
import {BrowseTable} from './astryx-tables.jsx';
import {createApiClient,saveFile as defaultSaveFile} from './api-v1.mjs';

const types={contract:'Договор',order:'Распорядительный документ',quality:'Документ, подтверждающий качество',scheme:'Схема',rd:'Рабочая документация',other:'Другой файл'};
const headers=['Наименование','Тип файла'].map((label,index)=>({key:'c'+index,index,label,type:'text'}));
const fileType=file=>file.file_kind||(['certificate','passport'].includes(file.doc_type)?'quality':file.doc_type);
const encode=file=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(Error('Не удалось прочитать файл'));reader.readAsDataURL(file);});
function csv(files){return '\ufeff'+[headers.map(h=>h.label),...files.map(file=>[file.original_name||file.title,types[fileType(file)]||types.other])].map(row=>row.map(v=>'"'+String(v??'').replace(/^[=+\-@\t\r]/,"'$&").replaceAll('"','""')+'"').join(';')).join('\r\n');}

export function SourceFiles({projectId,role,workspaceId='',getToken,onSessionExpired,api:providedApi,onOpen,onDelete,onCheck,onChanged,initialProject,isDirty=()=>false,saveFile=defaultSaveFile}){
 const api=useMemo(()=>providedApi||createApiClient({getToken,onSessionExpired}),[providedApi,getToken,onSessionExpired]);
 const [project,setProject]=useState(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState(''),[type,setType]=useState('contract');
 const input=useRef(null),generation=useRef(0),controller=useRef(null),locked=useRef(false);
 useEffect(()=>{const current=++generation.current,abort=new AbortController();controller.current=abort;locked.current=false;setProject(null);setLoading(true);setBusy(false);setError('');
  (initialProject?Promise.resolve(initialProject):api.json('/project?project_id='+encodeURIComponent(projectId),undefined,{signal:abort.signal})).then(value=>{if(!abort.signal.aborted&&current===generation.current){setProject(value);onChanged?.(value);}}).catch(err=>{if(!abort.signal.aborted&&current===generation.current)setError(err.message);}).finally(()=>{if(!abort.signal.aborted&&current===generation.current)setLoading(false);});
  return()=>abort.abort();
 },[api,projectId,workspaceId]);
 useEffect(()=>{if(initialProject){setProject(initialProject);setLoading(false);}},[initialProject]);
 async function upload(files){
  if(locked.current||role==='viewer'||!files.length)return;
  if(isDirty()){setError('Сначала сохраните изменения.');return;}
  if(files.some(file=>file.size>32*1024*1024)){setError('Допустимый размер файла — до 32 МБ.');return;}
  const current=generation.current,signal=controller.current.signal;locked.current=true;setBusy(true);setError('');
  try{
   for(const file of files){const content=await encode(file);if(signal.aborted)return;await api.json('/upload',{project_id:projectId,name:file.name,content,doc_type:type},{signal});}
  }catch(err){if(!signal.aborted&&current===generation.current)setError(err.message);}
  finally{
   // A partially completed batch must also refresh its already saved files.
   if(!signal.aborted&&current===generation.current){
    try{const value=await api.json('/project?project_id='+encodeURIComponent(projectId),undefined,{signal});if(!signal.aborted&&current===generation.current){setProject(value);onChanged?.(value);}}
    catch(err){if(!signal.aborted&&current===generation.current)setError(previous=>[previous,err.message].filter(Boolean).join(' '));}
    if(!signal.aborted&&current===generation.current){locked.current=false;setBusy(false);if(input.current)input.current.value='';}
   }
  }
 }
 async function check(){if(locked.current)return;if(isDirty()){setError('Сначала сохраните изменения.');return;}locked.current=true;setBusy(true);setError('');try{await onCheck?.();}catch(err){setError(err.message);}finally{locked.current=false;setBusy(false);}}
 const files=project?.source_files||project?.attachments?.filter(file=>project.project_attachment_ids.includes(file.id))||[];
 const allowDelete=role!=='viewer'&&!!onDelete;
 const tableHeaders=useMemo(()=>[...headers,...(allowDelete?[{key:'actions',index:2,label:'Действия',type:'text',action:true}]:[])],[allowDelete]);
 const snapshot=useMemo(()=>({key:'source-files-api-v1:'+workspaceId+':'+projectId+':'+role,title:'Исходные файлы',headers:tableHeaders,selectable:false,hasGroups:false,
  rows:files.map(file=>{const cells=[file.original_name||file.title||'',types[fileType(file)]||types.other];return {_key:String(file.id),_source:file,_cells:[...cells.map((text,index)=>({text,content:index===0?<Button label={text||'Открыть файл'} variant="ghost" isDisabled={busy} onClick={()=>{if(isDirty()){setError('Сначала сохраните изменения.');return;}onOpen?.(file);}}/>:text})),...(allowDelete?[{text:'',content:<Button label="Удалить" variant="destructive" aria-label={'Удалить запись: '+cells[0]} isDisabled={busy} onClick={()=>{if(isDirty()){setError('Сначала сохраните изменения.');return;}onDelete('attachments',file.id);}}/>}]:[])],_search:cells.join(' ').toLocaleLowerCase('ru').replaceAll('ё','е'),c0:cells[0],c1:cells[1]};}),
  exportRows:items=>saveFile({blob:new Blob([csv(items)],{type:'text/csv;charset=utf-8'}),filename:'Исходные файлы.csv'}),syncChoices:()=>{},
 }),[files,workspaceId,projectId,role,busy,onOpen,onDelete,allowDelete,tableHeaders,isDirty,saveFile]);
 return <Card padding={4} data-source-files-api="v1"><Collapsible trigger="Исходные файлы" defaultIsOpen={false}>
  {role!=='viewer'&&<><Selector label="Что загружаете" options={Object.entries(types).map(([value,label])=>({value,label}))} value={type} onChange={setType} isDisabled={busy}/>
   <div className="file-drop" role="group" aria-label="Добавить исходные файлы"
    onDragOver={e=>{e.preventDefault();e.dataTransfer.dropEffect='copy';}}
    onDragEnter={e=>{e.preventDefault();e.currentTarget.classList.add('drag');}}
    onDragLeave={e=>{if(!e.currentTarget.contains(e.relatedTarget))e.currentTarget.classList.remove('drag');}}
    onDrop={e=>{e.preventDefault();e.currentTarget.classList.remove('drag');if(!loading&&!busy&&project)upload([...e.dataTransfer.files]);}}>
    <span className="drop-icon"><svg className="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 16V3m-5 5 5-5 5 5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/></svg></span>
    <p>Перетащите файлы сюда</p>
    <span className="hint">или выберите на компьютере. до 32 МБ на файл</span>
    <div className="toolbar"><input ref={input} type="file" multiple hidden aria-label="Файлы для загрузки" onChange={e=>upload([...e.target.files])}/><Button label="Добавить файлы" onClick={()=>input.current?.click()} isLoading={busy} isDisabled={loading||busy||!project}/><Button label="Проверить файлы" variant="secondary" isDisabled={loading||busy||!project} onClick={check}/></div>
   </div>
   <p className="hint">Файлы сохраняются в архиве выбранного раздела.</p></>}
  {error&&<Banner status="error" title="Не удалось выполнить операцию" description={error}/>}
  {loading?<Skeleton aria-label="Загрузка исходных файлов" height={120}/>:<BrowseTable key={snapshot.key} snapshot={snapshot}/>}
 </Collapsible></Card>;
}
