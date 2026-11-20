import React,{useEffect,useMemo,useRef,useState} from 'react';
import {AlertDialog,Collapsible,Button,Selector,TextInput,TextArea,CheckboxInput,SideNavItem,ChatMessageList,ChatMessage,ChatMessageBubble,ChatToolCalls,Markdown,ChatComposer} from '@astryxdesign/core';
import {createApiClient} from './api-v1.mjs';

function useApi(config){const latest=useRef(config);latest.current=config;return useMemo(()=>createApiClient({getToken:()=>latest.current?.getToken?.()||'',onSessionExpired:()=>latest.current?.onSessionExpired?.()}),[config?.userId,config?.workspaceId]);}
export function AssistantNavItem({config}){
  const api=useApi(config),[visible,setVisible]=useState(false);
  useEffect(()=>{let alive=true;const load=()=>{if(!config?.userId){setVisible(false);return;}api.json('/assistants').then(a=>{if(alive)setVisible(a.length>0);}).catch(()=>{if(alive)setVisible(false);});};load();document.addEventListener('itd:assistants-changed',load);return()=>{alive=false;document.removeEventListener('itd:assistants-changed',load);};},[api,config?.userId]);
  const icon=<span className="nav-glyph" aria-hidden="true" dangerouslySetInnerHTML={{__html:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/><path d="M9 10h6M9 13.5h3.5"/></svg>'}}/>;
  return visible?<SideNavItem label="Ассистент" title="Ассистент" icon={icon} data-assistant-open="" onClick={()=>document.dispatchEvent(new Event('itd:assistant-open'))}/>:null;
}

async function readSnapshots(response,onSnapshot,signal){
  if(!response.ok)throw Error('Чат недоступен');
  const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
  try{while(!signal.aborted){const {value,done}=await reader.read();buffer+=decoder.decode(value||new Uint8Array(),{stream:!done});let split;while((split=buffer.indexOf('\n\n'))>=0){const frame=buffer.slice(0,split);buffer=buffer.slice(split+2);const data=frame.split('\n').find(l=>l.startsWith('data:'));if(data){const item=JSON.parse(data.slice(5));if(item.error)throw Error(item.error);onSnapshot(item);}}if(done)break;}}finally{reader.releaseLock();}
}

const statusLabels={running:'Формируется ответ',complete:'Сохранено',cancelled:'Отменено',interrupted:'Прервано',error:'Ответ не завершён'};
const missingResultLabels={cancelled:'Ответ отменён до получения результата',interrupted:'Ответ прерван до получения результата',error:'Ответ завершился ошибкой до получения результата'};

function toolCallItems(message){
  return message.tool_calls.map((entry,i)=>{
    const failed=Boolean(entry.result?.error);
    const status=entry.result?(failed?'error':'complete'):message.status==='running'?'running':'error';
    const errorMessage=failed?'Инструмент вернул ошибку':status==='error'?(missingResultLabels[message.status]||'Результат не сохранён'):undefined;
    return {key:String(i),name:entry.call.name,status,errorMessage,resultDetail:<div className="assistant-tool-detail"><strong>Аргументы</strong><pre>{JSON.stringify(entry.call.arguments,null,2)}</pre>{entry.result&&<><strong>Результат</strong><pre>{JSON.stringify(entry.result,null,2)}</pre></>}</div>};
  });
}

function Message({message}){
  return <ChatMessage sender={message.sender} name={message.sender==='user'?'Вы':'Ассистент'}><ChatMessageBubble>{message.sender==='assistant'
    ? <Markdown density="compact" headingLevelStart={3} isStreaming={message.status==='running'}>{message.text||'…'}</Markdown>
    : <><div className="assistant-text">{message.text}</div>{message.attachments?.map((file,index)=><details key={index}><summary>{file.name}</summary><pre className="assistant-text">{file.text}</pre></details>)}</>}</ChatMessageBubble>{message.tool_calls.length>0&&<ChatToolCalls calls={toolCallItems(message)}/>}<small>{statusLabels[message.status]}</small></ChatMessage>;
}

const newProvider={name:'',protocol:'chat',base_url:'',api_key:'',allow_anonymous:false};
function ProviderSettings({api,model,onSaved}){
  const [draft,setDraft]=useState(newProvider),[busy,setBusy]=useState(false),[error,setError]=useState(''),[status,setStatus]=useState(''),[expanded,setExpanded]=useState(!model.providers.length);
  const field=(key,value)=>setDraft(d=>({...d,[key]:value}));
  const profiles=model.provider_profiles||[],presets=model.provider_presets||[];
  const selected=profiles.find(p=>p.name===draft.name);
  function choose(name){
    const profile=profiles.find(p=>p.name===name)||presets.find(p=>p.name===name);
    setDraft({...newProvider,...profile,name:profile?.name||'',api_key:''});setStatus('');setError('');
  }
  async function save(){
    setBusy(true);setError('');setStatus('');
    try{
      const {name,protocol,base_url,api_key,allow_anonymous}=draft;
      await api.json('/assistant/provider',{name,protocol,base_url,api_key,allow_anonymous});
      setDraft(d=>({...d,api_key:''}));
      await onSaved(name);
      document.dispatchEvent(new Event('itd:assistants-changed'));
      setStatus('Подключение сохранено. Теперь выберите его в настройках ассистента.');
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  return <div className="assistant-provider-settings"><Collapsible trigger="Подключения к моделям" isOpen={expanded} onOpenChange={setExpanded}><p>Укажите провайдера и ключ API. Ключ хранится на сервере, после сохранения поле очищается. Подключение доступно сразу.</p>
    <Selector label="Подключение" value={[...profiles,...presets].some(p=>p.name===draft.name)?draft.name:'new'} options={[{value:'new',label:'Новое подключение'},...[...new Set([...profiles,...presets].map(p=>p.name))].map(name=>({value:name,label:name}))]} onChange={choose}/>
    <TextInput label="Название подключения" value={draft.name} onChange={v=>field('name',v)} isDisabled={busy}/>
    <Selector label="Протокол" value={draft.protocol} options={[{value:'chat',label:'OpenAI-совместимый'},{value:'anthropic',label:'Anthropic'},{value:'gemini',label:'Gemini'}]} onChange={v=>field('protocol',v)}/>
    <TextInput label="Адрес API" value={draft.base_url} onChange={v=>field('base_url',v)} isDisabled={busy}/>
    <TextInput label="Ключ API" type="password" autoComplete="new-password" value={draft.api_key} onChange={v=>field('api_key',v)} isDisabled={busy}/>
    {selected?.key_configured&&<p className="hint">Ключ сохранён. Оставьте поле пустым, чтобы сохранить текущий ключ.</p>}
    <CheckboxInput label="Подключение без ключа (например, локальная модель)" value={draft.allow_anonymous} onChange={v=>field('allow_anonymous',v)}/>
    <Button label="Сохранить подключение" variant="secondary" onClick={save} isDisabled={busy||!draft.name||!draft.base_url||(!draft.api_key&&!selected?.key_configured&&!draft.allow_anonymous)}/>
    {error&&<p role="alert">{error}</p>}{status&&<p role="status">{status}</p>}
  </Collapsible></div>;
}

const blank={name:'',instruction:'',provider:'',model:'',allowed_tools:[],knowledge_bases:[],active:true,skill_path:'ai/skills/ai-technical-engineer/SKILL.md'};
function AssistantAdmin({api,onSaved}){
  const [model,setModel]=useState(null),[draft,setDraft]=useState(blank),[error,setError]=useState(''),[status,setStatus]=useState(''),[busy,setBusy]=useState(false);
  const load=()=>api.json('/assistant/admin').then(setModel).catch(e=>setError(e.message));useEffect(()=>{load();},[api]);
  const field=(key,value)=>setDraft(d=>({...d,[key]:value}));
  async function save(){
    setBusy(true);setError('');setStatus('');
    try{
      const {skill_version,...data}=draft;
      const saved=await api.json('/assistant/config',data);
      setDraft(d=>({...d,id:saved.id}));
      await load();
      document.dispatchEvent(new Event('itd:assistants-changed'));
      onSaved();
      setStatus('Ассистент «'+draft.name+'» сохранён.');
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  return <section aria-label="Настройка ассистентов" className="assistant-admin"><h3>Настройка ассистентов</h3><p>Выберите подключение и модель, задайте имя и инструкцию ассистента.</p>{model&&<><ProviderSettings api={api} model={model} onSaved={async name=>{await load();field('provider',name);}}/><Selector label="Редактировать" value={String(draft.id||'new')} options={[{value:'new',label:'Новый ассистент'},...model.assistants.map(a=>({value:String(a.id),label:a.name}))]} onChange={v=>{setStatus('');setDraft(v==='new'?{...blank}:{...model.assistants.find(a=>String(a.id)===v)});}}/><TextInput label="Название" value={draft.name} onChange={v=>field('name',v)}/>{model.providers.length?<Selector label="Провайдер" value={draft.provider} options={[...model.providers,...(draft.provider&&!model.providers.includes(draft.provider)?[draft.provider]:[])].map(v=>({value:v,label:v}))} onChange={v=>field('provider',v)}/>:<p role="status">Добавьте подключение к модели выше, затем сохраните ассистента.</p>}<TextInput label="Модель" value={draft.model} onChange={v=>field('model',v)}/><TextArea label="Инструкция" value={draft.instruction} onChange={v=>field('instruction',v)}/><p className="hint">Используется вся база знаний. Все инструменты подключены автоматически и работают в пределах прав пользователя.</p><TextInput label="Ссылка на навык" value={draft.skill_path} onChange={v=>field('skill_path',v)}/><Selector label="Доступность" value={draft.active?'true':'false'} options={[{value:'true',label:'Включён'},{value:'false',label:'Отключён'}]} onChange={v=>field('active',v==='true')}/><Button label="Сохранить ассистента" onClick={save} isDisabled={busy||!draft.name||!draft.model||!draft.provider}/>{status&&<p role="status">{status}</p>}</>}{error&&<p role="alert">{error}</p>}</section>;
}

const fileFormats='.txt,.md,.csv,.tsv,.json,.pdf,.docx,.xlsx';
const emptyFiles=[];
function encodeFile(file){
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve({name:file.name,data:reader.result.split(',')[1]});
    reader.onerror=()=>reject(Error('Не удалось прочитать файл «'+file.name+'».'));
    reader.readAsDataURL(file);
  });
}

export function AssistantPanel({config}){
  const api=useApi(config),[open,setOpen]=useState(false),[admin,setAdmin]=useState(false),[assistants,setAssistants]=useState([]),[threads,setThreads]=useState([]),[aid,setAid]=useState(''),[tid,setTid]=useState(null),[history,setHistory]=useState(null),[drafts,setDrafts]=useState({}),[error,setError]=useState(''),[busy,setBusy]=useState(false),[revision,setRevision]=useState(0),[streamRetry,setStreamRetry]=useState(0),[renaming,setRenaming]=useState(null),[confirmDelete,setConfirmDelete]=useState(false);
  const scrollRef=useRef(null),nearBottom=useRef(true),closeRef=useRef(null),returnFocus=useRef(null),pending=useRef(null),latest=useRef(config);latest.current=config;
  const draftKey=String(tid||'new'),draft=drafts[draftKey]||'';
  const [fileDrafts,setFileDrafts]=useState({});
  const files=fileDrafts[draftKey]||emptyFiles,fileInput=useRef(null);
  function selectFiles(event){
    const selected=[...files,...event.target.files];
    event.target.value='';
    if(selected.length>4||selected.reduce((sum,f)=>sum+f.size,0)>4*1024*1024){
      setError('Можно прикрепить до четырёх файлов общим размером до 4 МиБ.');return;
    }
    setFileDrafts(d=>({...d,[draftKey]:selected}));setError('');
  }
  const setDraft=text=>setDrafts(d=>({...d,[draftKey]:text}));
  useEffect(()=>{const show=e=>{returnFocus.current=document.activeElement;setOpen(true);setAdmin(e.type==='itd:assistant-admin');};document.addEventListener('itd:assistant-open',show);document.addEventListener('itd:assistant-admin',show);return()=>{document.removeEventListener('itd:assistant-open',show);document.removeEventListener('itd:assistant-admin',show);};},[]);
  const refresh=async()=>{const [a,t]=await Promise.all([api.json('/assistants'),api.json('/assistant/threads')]);setAssistants(a);setThreads(t);setAid(v=>a.some(item=>String(item.id)===v)?v:String(a[0]?.id||''));};
  useEffect(()=>{if(open){closeRef.current?.focus();refresh().catch(e=>setError(e.message));}},[open,api]);
  useEffect(()=>{if(!open)return;const focus=()=>closeRef.current?.focus();document.addEventListener('close',focus,true);return()=>document.removeEventListener('close',focus,true);},[open]);
  useEffect(()=>{if(!open||!tid)return;let alive=true;api.json('/assistant/thread?thread_id='+tid).then(v=>{if(alive){setHistory(v);setAid(String(v.thread.assistant_id));}}).catch(e=>{if(alive)setError(e.message);});return()=>{alive=false;};},[tid,open,api,revision]);
  React.useLayoutEffect(()=>{if(nearBottom.current&&scrollRef.current)scrollRef.current.scrollTop=scrollRef.current.scrollHeight;},[history]);
  const running=history?.messages.find(m=>m.status==='running');
  useEffect(()=>{if(!open||!tid||!running)return;const controller=new AbortController();fetch('/api/v1/assistant/events?thread_id='+tid+'&message_id='+running.id,{headers:{'X-ITD-Token':latest.current.getToken()},signal:controller.signal}).then(async r=>{if(r.status===403)latest.current.onSessionExpired?.();await readSnapshots(r,m=>setHistory(h=>h?{...h,messages:h.messages.map(old=>old.id===m.id?m:old)}:h),controller.signal);}).catch(()=>{if(!controller.signal.aborted)setError('Поток прерван. Повторите подключение или обновите чат.');});return()=>controller.abort();},[open,tid,running?.id,api,streamRetry]);
  function close(){setOpen(false);const target=returnFocus.current;if(window.matchMedia('(max-width:760px)').matches&&!target?.getClientRects().length)document.querySelector('[aria-label="Открыть навигацию"]')?.focus();else target?.focus();}
  function retryStream(){setError('');setStreamRetry(v=>v+1);}
  async function renameThread(){try{await api.json('/assistant/thread-title',{thread_id:tid,title:renaming});setRenaming(null);setError('');await refresh();setRevision(v=>v+1);}catch(e){setError(e.message);}}
  async function removeThread(){try{await api.json('/assistant/thread-delete',{thread_id:tid});setConfirmDelete(false);setTid(null);setHistory(null);setError('');await refresh();}catch(e){setError(e.message);}}
  async function create(){setBusy(true);try{const thread=await api.json('/assistant/threads',{assistant_id:Number(aid),project_id:config.projectId||null,object_id:config.objectId||null});setTid(thread.id);setHistory(null);await refresh();}catch(e){setError(e.message);}finally{setBusy(false);}}
  async function send(text){
    if(!tid||busy||running)return;
    nearBottom.current=true;setBusy(true);setError('');
    try{
      if(pending.current?.tid!==tid||pending.current.text!==text||pending.current.files!==files){
        pending.current={tid,text,files,key:crypto.randomUUID()};
      }
      const attachments=await Promise.all(files.map(encodeFile));
      await api.json('/assistant/messages',{thread_id:tid,text,attachments,request_key:pending.current.key});
      pending.current=null;
      setDrafts(d=>({...d,[draftKey]:''}));
      setFileDrafts(d=>({...d,[draftKey]:emptyFiles}));
      setRevision(v=>v+1);
    }catch(e){setDrafts(d=>({...d,[draftKey]:draft}));setError(e.message);}
    finally{setBusy(false);}
  }
  if(!open||!config?.userId)return null;
  const attached=Boolean(history&&assistants.some(a=>a.id===history.thread.assistant_id));
  const blocked=!tid?'Выберите сохранённый чат или создайте новый.':history&&!attached?'Ассистент отключён или недоступен. Чат открыт только для чтения.':'';
  return <aside className="assistant-panel" aria-label="Ассистент" onKeyDown={e=>{if(e.key==='Escape'&&!e.defaultPrevented&&!e.target.closest?.('[role="listbox"],[role="menu"],[role="alertdialog"],[aria-expanded="true"]')){e.stopPropagation();close();}}}><header><h2>Ассистент</h2><Button ref={closeRef} label="Закрыть ассистента" variant="secondary" onClick={close}/></header><div className="assistant-panel-body" ref={scrollRef} onScroll={e=>{const n=e.currentTarget;nearBottom.current=n.scrollHeight-n.scrollTop-n.clientHeight<80;}}>{config.role==='admin'&&<Button variant="secondary" label={admin?'К чату':'Настроить ассистентов'} onClick={()=>setAdmin(v=>!v)}/>}<p className="hint">{config.projectId?'Раздел'+(config.sectionCode?' '+config.sectionCode:'')+(config.projectLabel?' «'+config.projectLabel+'»':''):config.objectId?'Объект'+(config.objectName?' «'+config.objectName+'»':''):'Все объекты'}. Контекст чата сохраняется при его создании.</p>{admin&&config.role==='admin'?<AssistantAdmin api={api} onSaved={()=>refresh().catch(e=>setError(e.message))}/>:<><Selector label="Ассистент" value={aid} options={assistants.map(a=>({value:String(a.id),label:a.name}))} onChange={v=>{setAid(v);setTid(null);setHistory(null);}}/><Button label="Новый чат" onClick={create} isDisabled={busy||!aid}/>{threads.length>0?<Selector label="Сохранённые чаты" value={tid?String(tid):''} options={threads.map(t=>({value:String(t.id),label:t.title}))} onChange={v=>{setTid(Number(v));setHistory(null);setRenaming(null);setConfirmDelete(false);}}/>:<p className="hint">Сохранённых чатов пока нет.</p>}<div className="assistant-thread-actions"><Button variant="ghost" label="Обновить" onClick={()=>setRevision(v=>v+1)} isDisabled={!tid}/>{tid&&renaming===null&&<><Button variant="ghost" label="Переименовать" onClick={()=>setRenaming(history?.thread.title||'')} isDisabled={!history}/><Button variant="ghost" label="Удалить" onClick={()=>setConfirmDelete(true)} isDisabled={!history||Boolean(running)}/></>}</div>{renaming!==null&&<div className="assistant-thread-actions"><TextInput label="Название чата" value={renaming} onChange={setRenaming}/><Button label="Сохранить название" onClick={renameThread} isDisabled={!renaming.trim()}/><Button variant="ghost" label="Отмена" onClick={()=>setRenaming(null)}/></div>}{history&&<p className="hint">Чат привязан: {history.context}</p>}{!assistants.length&&<p>Доступных ассистентов нет.</p>}<ChatMessageList emptyState={<p>{tid?'Задайте первый вопрос ассистенту.':'Выберите чат или создайте новый, затем задайте вопрос.'}</p>}>{history?.messages.map(m=><Message key={m.id} message={m}/>)}</ChatMessageList>{history&&<small>Навык: {history.thread.skill_path}. {history.thread.skill_version.slice(0,12)}</small>}</>}{error&&<div role="alert"><p>{error}</p>{running&&<Button variant="secondary" label="Повторить подключение" onClick={retryStream}/>}</div>}</div>{!admin&&<div className="assistant-composer">{blocked&&<p className="hint" role="status">{blocked}</p>}<input ref={fileInput} type="file" hidden multiple accept={fileFormats} onChange={selectFiles}/>
    <ChatComposer footerActions={<Button label="Прикрепить файлы" variant="ghost" size="sm" onClick={()=>fileInput.current?.click()} isDisabled={!attached||busy||!!running}/>}
      drawer={files.length>0&&<ul aria-label="Вложения">{files.map((file,index)=><li key={index}>{file.name} <Button variant="ghost" size="sm" label="Убрать" aria-label={'Убрать '+file.name} isDisabled={busy} onClick={()=>setFileDrafts(d=>({...d,[draftKey]:files.filter((_,i)=>i!==index)}))}/></li>)}</ul>}
      sendButton={files.length>0&&!draft.trim()&&!running?<Button label="Отправить" isDisabled={!attached||busy} onClick={()=>send('')}/>:undefined}
      value={draft} onChange={setDraft} onSubmit={send} placeholder="Вопрос ассистенту…" isDisabled={Boolean(blocked)||!attached||busy} isStopShown={!!running} onStop={()=>api.json('/assistant/cancel',{thread_id:tid}).catch(e=>setError(e.message))}/></div>}<AlertDialog isOpen={confirmDelete} onOpenChange={setConfirmDelete} title="Удалить чат?" description="Сообщения этого чата будут удалены без возможности восстановления." cancelLabel="Отмена" actionLabel="Удалить" actionVariant="destructive" onAction={removeThread}/></aside>;
}
