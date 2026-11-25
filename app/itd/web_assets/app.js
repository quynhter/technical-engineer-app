'use strict';
const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Время выпуска отображается в часовом поясе браузера.
function formatDateTime(value){
 if(!value)return 'Дата не указана';
 const date=new Date(value);
 if(Number.isNaN(date.getTime()))return 'Дата не распознана';
 const pad=n=>String(n).padStart(2,'0');
 return `${pad(date.getDate())}.${pad(date.getMonth()+1)}.${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
const iconPaths = {
 plus: '<path d="M12 5v14M5 12h14"/>',
 check: '<path d="m5 12 4 4L19 6"/>',
 left: '<path d="m12 5-7 7 7 7M5 12h14"/>',
 right: '<path d="m12 5 7 7-7 7M5 12h14"/>',
 down: '<path d="m6 9 6 6 6-6"/>',
 home: '<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',
 list: '<path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01"/>',
 clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 building: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h1m4 0h1M9 11h1m4 0h1M9 15h1m4 0h1M10 21v-3h4v3"/>',
 user: '<circle cx="12" cy="8" r="4"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/>',
 file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h6"/>',
 download: '<path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/>',
 upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
 clipboard: '<rect x="5" y="5" width="14" height="16" rx="2"/><rect x="9" y="2" width="6" height="6" rx="1"/><path d="M9 13h6M9 17h6"/>',
 sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
 moon: '<path d="M20.8 13.2A9 9 0 0 1 10.8 3a9 9 0 1 0 10 10.2Z"/>',
  journal: '<path d="M7 3h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M9 8h6M9 12h6M9 16h4"/>'
};
function icon(name) {
 return `<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${iconPaths[name] || iconPaths.plus}</svg>`;
}
function decorateSelects(){decorateDataTables();enhanceEditorActions();enhanceCheckLists();document.querySelectorAll('select').forEach(enhanceSelect);document.querySelectorAll('form').forEach(form=>form.noValidate=true);}
const appearanceKey = 'itd-appearance';
let appearance = {theme: 'light'};
try {
 const saved = JSON.parse(localStorage.getItem(appearanceKey) || '{}');
 if (['light','dark'].includes(saved.theme)) appearance.theme = saved.theme;
} catch (_) { /* Недоступное хранилище не мешает работе формы. */ }
function applyAppearance() {
 document.documentElement.dataset.theme = appearance.theme;
 try { localStorage.setItem(appearanceKey, JSON.stringify(appearance)); } catch (_) {}
 document.dispatchEvent(new Event('itd:appearance'));
}
applyAppearance();
document.addEventListener('itd:theme-toggle',()=>{appearance.theme=appearance.theme==='light'?'dark':'light';applyAppearance();});
let token=sessionStorage.getItem('itd-session')||'';
let meta, state={object:{},participants:[],projects:[],token:null}, step=0, tab=0, orgIndex=0, projectId=null, pdata=null, dirty=false, formDirty=false, busy=false, pending=[], editEntry=null;
let workspaceView='overview', selectedEntries=new Set();
const tableFilters=Object.fromEntries(['work','incoming','journal'].map(k=>[k,{search:'',unbound:false,group:false,from:'',to:''}]));
const idViews=['documents','resources','schemes','templates'];
let packagePanel='registry',resourcePanel='list';
const tabs=['Комплект ИД','Ресурсы','Схемы','Шаблоны документов'];
const tabViews=['registry','resources','schemes','templates'];
const journalViews=['ojr','journal','cable','work'];
function crumbTrail(view){
  const root={label:'Объекты',view:'objects'};
  if(view==='account')return [root,{label:'Настройки',view:'account'},{label:accountTabLabels[accountTab]||accountTabLabels.profile,view:'account'}];
  if(journalViews.includes(view)){
   const trail=[root,{label:'Журналы',view:'ojr'},view==='journal'?{label:'ЖВК',view:'journal'}:view==='cable'?{label:'ЖПК',view:'cable'}:{label:'ОЖР',view:'ojr'}];
   const section=pdata?.journals?.section_names?.[journalSection];
   if(journalSection!=='0'&&section&&['ojr','work'].includes(view))trail.push({label:section,view:'ojr'});
   return trail;
  }
  const idTab={registry:0,documents:0,check:0,delivery:0,resources:1,incoming:1,facts:1,schemes:2,templates:3}[view];
  if(idTab===undefined){
   if(view==='objects')return [{label:'Объекты',view:'objects'}];
   const labels={object:'Объект',participants:'Участники',rd:'Разделы',permits:'Разрешительная документация',overview:'Обзор',manage:'Ручное ведение'};
   return [root,{label:labels[view]||'Обзор',view}];
  }
  const trail=[root,{label:'Исполнительная документация',view:'registry'},{label:tabs[idTab],view:tabViews[idTab]}];
  if(idTab===0)trail.push({label:{registry:'Реестр ИД',documents:'Основные документы',check:'Проверка',delivery:'Сдача'}[packagePanel],view:packagePanel});
  if(idTab===1)trail.push({label:{list:'Спецификация',incoming:'Входной контроль',facts:'Факт монтажа'}[resourcePanel],view:{list:'resources',incoming:'incoming',facts:'facts'}[resourcePanel]});
  return trail;
}
async function api(path,data){
 if(sessionSuspended&&data&&!['/api/login','/api/logout'].includes(path))throw Error('Сеанс завершён. Войдите снова; введённые данные остаются в открытой форме.');
 let res,value;
 try{
  res=await fetch(path,{method:data?'POST':'GET',headers:{'X-ITD-Token':token,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined,signal:AbortSignal.timeout(data?120000:30000)});
  value=await res.json();
 }catch(error){
  const reason=['TimeoutError','AbortError'].includes(error.name)?'Сервер не ответил вовремя.':'Не удалось получить ответ сервера.';
  const failure=Error(reason+(data?' Результат операции неизвестен. Проверьте данные перед повторной отправкой.':' Проверьте соединение и повторите загрузку.')+' Ввод остаётся в открытой форме.');
  failure.unknownResult=Boolean(data);
  throw failure;
 }
 if(!res.ok){const error=Error(value.error?.message||value.error||'Не удалось выполнить запрос');error.fields=value.fields;error.journalDates=value.journal_dates;error.status=res.status;error.code=value.error?.code;if(res.status===403&&value.session_expired)suspendWorkspace();throw error;}
 return value;
}
function notice(text=''){ const target=$('#editor-dialog').open?$('#editor-notice'):$('#notice');target.textContent=text; }
function toast(text){$('#toast').textContent=text;$('#toast').style.display='block';setTimeout(()=>$('#toast').style.display='none',4000);}
async function reloadJournalWorkspace(){
 if(!dirty)state=await api('/api/workspace?object_id='+state.object.id);
}
async function refreshAfterWritePreview(affectedProject){
 const workspace=currentUser?.workspace_id,objectId=state.object.id,selected=projectId;
 const [nextState,nextProject]=await Promise.all([
  objectId?api('/api/workspace?object_id='+objectId):null,
  selected===affectedProject?api('/api/project?project_id='+selected):null,
 ]);
 if(registryDirty()||workspace!==currentUser?.workspace_id||objectId!==state.object.id||selected!==projectId)return;
 if(nextState)state=nextState;
 if(nextProject){
  if(nextProject._revision)nextProject._checkedAt=Date.now();
  pdata=nextProject;
  selectedEntries=new Set([...selectedEntries].filter(id=>pdata.workspace_entries.some(e=>e.id===id&&!e.act_id)));
 }
 const opener=document.activeElement?.closest('[data-open-write-previews]');
 render();
 if(opener&&!opener.isConnected)document.querySelector('[data-open-write-previews]')?.focus();
}
async function saveDatedJournal(path,request,key){
 let payload=request;
 for(;;){
  try{await api(path,payload);break;}
  catch(error){
   if(!error.journalDates?.length)throw error;
   const changes=error.journalDates.map(c=>`${c.scope}: ${displayTableDate(c.before)} → ${displayTableDate(c.after)}`).join('\n');
   if(!await confirmWorkspace('Дата записи раньше начала работ. Перенести начало и сохранить запись?\n\n'+changes,'Перенести и сохранить'))return false;
   payload={...request,[key]:{...request[key],journal_dates_confirmation:error.journalDates}};
  }
 }
 return true;
}
async function action(fn){
 if(busy)return;busy=true;notice();
 const buttons=[...document.querySelectorAll('button')].filter(b=>!b.closest('#account-page,#prompt-dialog,#login-dialog'));
 const disabled=buttons.map(b=>b.disabled);buttons.forEach(b=>b.disabled=true);
 try{await fn();}catch(e){if(e.fields)showWorkspaceErrors(e.fields);notice(e.message);($('#editor-dialog').open?$('#editor-notice'):$('#notice')).scrollIntoView({block:'nearest',behavior:'smooth'});}
 finally{busy=false;buttons.forEach((b,i)=>{if(b.isConnected)b.disabled=disabled[i];});syncPreviewActions();}
}
function get(path){return path.split('.').reduce((v,k)=>v?.[k],state);}
function put(path,value){const keys=path.split('.'),last=keys.pop();let obj=state;for(const k of keys)obj=obj[k];obj[last]=value;dirty=true;$('#save-status')&&( $('#save-status').textContent='Есть несохранённые изменения');}
function field(path,label,type='text',wide=false,extra=''){let v=get(path);return `<label class="field ${wide?'wide':''}"><span>${label}</span>${type==='textarea'?`<textarea data-path="${esc(path)}" ${extra}>${esc(v)}</textarea>`:`<input data-path="${esc(path)}" type="${type}" value="${esc(v)}" ${extra}>`}</label>`;}
function select(path,label,options,wide=false){const value=get(path);return `<label class="field ${wide?'wide':''}"><span>${label}</span><select data-path="${esc(path)}"><option value="">Выберите…</option>${Object.entries(options).map(([v,t])=>`<option value="${esc(v)}" ${v===value?'selected':''}>${esc(t)}</option>`).join('')}</select></label>`;}
function check(path,label){return `<label class="choice"><input type="checkbox" data-path="${esc(path)}" ${get(path)?'checked':''}>${esc(label)}</label>`;}
function controlChoice(value,label,checked){return `<label class="choice"><input type="radio" name="construction-control" data-control="${value}" ${checked?'checked':''}>${esc(label)}</label>`;}
function title(name,sub){return `<div class="title-row"><div><h1>${name}</h1><p class="subtitle">${sub}</p></div></div>`;}
function card(heading,content,iconName='plus'){return `<section class="card"><h2 class="card-title"><span class="icon" aria-hidden="true">${icon(iconName)}</span>${heading}</h2>${content}</section>`;}
function option(v,t,selected){return `<option value="${esc(v)}" ${v==selected?'selected':''}>${esc(t)}</option>`;}
function navigate(view){const revealPermits=view==='permits';if(revealPermits)view='object';workspaceView=view;const url=new URL(location.href);url.searchParams.set('view',view);history.replaceState(null,'',url.pathname+url.search);const map={object:0,participants:1,rd:2,documents:3,registry:3,schemes:3,templates:3,work:3,incoming:3,journal:3,cable:3,facts:3,check:3,delivery:3,manage:4,resources:3,ojr:3};step=map[view]??0;if(view==='work')journalSection='3';if(view==='incoming')resourcePanel='incoming';else if(view==='facts')resourcePanel='facts';else if(view==='resources')resourcePanel='list';if(view==='check')packagePanel='check';else if(view==='delivery')packagePanel='delivery';else if(['documents','registry'].includes(view))packagePanel=view;const ti=idViews.indexOf(({work:'ojr',journal:'ojr',cable:'ojr',registry:'documents',facts:'resources',incoming:'resources',check:'documents',delivery:'documents'})[view]||view);if(ti>=0)tab=ti;editEntry=null;notice();render();if(revealPermits){const disclosure=document.querySelector('#object-permits');if(disclosure)disclosure.open=true;}window.scrollTo({top:0,behavior:'auto'});window.requestAnimationFrame?.(()=>{const target=document.querySelector(['check','delivery'].includes(view)?'#package-panel-title':'#content h1');if(target){target.setAttribute('tabindex','-1');target.focus({preventScroll:true});if(['check','delivery'].includes(view))target.scrollIntoView({block:'start',behavior:'auto'});}});refreshJournals();}
let renderedTableContext=null;
function render(){
 const nav=[['overview','Обзор','home'],['object','Объект','building'],['rd','Разделы','file'],['participants','Участники','user'],['registry','Исполнительная документация','list'],['ojr','Журналы','journal']];
 if(window.ITDDesign)window.ITDDesign.renderNav(nav.map(([v,n,i])=>[v,n,icon(i)]),workspaceView,navigate,crumbTrail(workspaceView),{userId:currentUser?.id,role:currentUser?.role,workspaceId:currentUser?.workspace_id,projectId,projectLabel:pdata?.project?.name||state.projects.find(p=>p.id===projectId)?.name,sectionCode:pdata?.project?.section_code||state.projects.find(p=>p.id===projectId)?.section_code,objectId:state.object?.id,objectName:state.object?.name,getToken:registryToken,onSessionExpired:suspendWorkspace});
 $('#sidebar').innerHTML=step===1&&workspaceView==='participants'?orgSidebar():'';
 $('#sidebar').hidden=!(step===1&&workspaceView==='participants');
 $('main').classList.toggle('no-sidebar',$('#sidebar').hidden);
 const tableContext=JSON.stringify([workspaceView,projectId,currentUser?.workspace_id,currentUser?.role,journalSection,packagePanel,resourcePanel]);
 const keepTable=['registry','documents','schemes','templates','resources','incoming','facts','cable','work','journal','ojr','check','delivery','manage'].includes(workspaceView)&&renderedTableContext===tableContext&&!!$('#content [data-astryx-island]')&&!!$('#content [id$="-app"]');
 if(!keepTable)$('#content').innerHTML=workspaceView==='objects'?objectsPage():workspaceView==='overview'?overviewPage():workspaceView==='account'?accountPage():[objectPage,participantsPage,rdPage,idPage,manualPage][step]();
 renderedTableContext=tableContext;
 $('#actions').innerHTML=!dirty&&!['object','participants','rd'].includes(workspaceView)?'':`<span id="save-status" class="status-text ${dirty?'unsaved':''}">${dirty?'Есть несохранённые изменения':state.object.id?'Сведения сохранены':'Новый объект. пока не сохранён'}</span><div class="footer-right">${state.object.id?'<button class="secondary" data-action="import">Импорт</button><button class="secondary" data-action="export">Экспорт</button>':''}<button data-action="save">Сохранить сведения</button></div>`;
 mountRegistry();
 mountSourceFiles();
 mountSchemes();
 mountTemplates();
 mountDocuments();
 mountResources();
 mountFacts();
 mountIncoming();
 mountCable();
 mountWork();
 mountJournal();
 mountWorkflow();
 mountManual();
 mountSectionTabs();
 decorateSelects();
}
function registryToken(){return token;}
function registryDirty(){return dirty||formDirty||sessionSuspended;}
function registryChanged(host,pid,workspace,value){if(host.isConnected&&projectId===pid&&currentUser?.workspace_id===workspace)pdata=value;}
function openRegistryItem(item){
 if(dirty||formDirty){notice('Сначала сохраните изменения.');return;}
 if(sessionSuspended){notice('Сеанс завершён. Войдите снова.');return;}
 if(item.entity==='act'){action(()=>currentUser?.role==='viewer'?previewAct(Number(item.id)):openDocumentVersions(Number(item.id)));return;}
 if(item.entity==='scheme'){openManual('scheme-edit',item.id);return;}
 if(item.entity==='attachment'){openSourceFileCard(Number(item.id));return;}
 if(item.entity==='release'){action(()=>downloadRelease(Number(item.id)));return;}
 if(item.entity==='journal')navigate(item.id==='incoming'?'journal':item.id);
}
function mountRegistry(){
 const host=$('#registry-app');if(!host)return;
 const pid=projectId,workspace=currentUser.workspace_id;
 window.ITDDesign.renderRegistry(host,{projectId:pid,role:currentUser.role,workspaceId:workspace,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onOpen:openRegistryItem,onDelete:deleteProjectRecord,onChanged:value=>registryChanged(host,pid,workspace,value),isDirty:registryDirty});
}
function openSourceItem(file){openSourceFileCard(Number(file.id));}
function checkSourceFiles(){return previewFiles('check');}
function mountSourceFiles(){
 const host=$('#source-files-app');if(!host)return;
 const pid=projectId,workspace=currentUser.workspace_id;
 window.ITDDesign.renderSourceFiles(host,{projectId:pid,role:currentUser.role,workspaceId:workspace,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onOpen:openSourceItem,onDelete:deleteProjectRecord,onCheck:checkSourceFiles,onChanged:value=>registryChanged(host,pid,workspace,value),isDirty:registryDirty});
}
function createScheme(){openManual('scheme-add');}
function openScheme(item){openManual('scheme-edit',item.id);}
function deleteProjectRecord(entity,id){return action(()=>previewRecordDeletion(entity,id));}
function mountSchemes(){
 const host=$('#schemes-app');if(!host)return;
 const pid=projectId,workspace=currentUser.workspace_id;
 window.ITDDesign.renderProjectRecords(host,{kind:'schemes',projectId:pid,workspaceId:workspace,role:currentUser.role,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onCreate:createScheme,onOpen:openScheme,onDelete:deleteProjectRecord,onChanged:value=>registryChanged(host,pid,workspace,value),isDirty:registryDirty});
}
function createDocument(){openEditor('act');}
function importDocument(){openUploadedAct();}
function openDocumentItem(item){openRegistryItem({...item,entity:'act'});}
function mountDocuments(){
 const host=$('#documents-app');if(!host)return;
 const pid=projectId,workspace=currentUser.workspace_id;
 window.ITDDesign.renderProjectRecords(host,{kind:'documents',projectId:pid,workspaceId:workspace,role:currentUser.role,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onCreate:createDocument,onImport:importDocument,onOpen:openDocumentItem,onDelete:deleteProjectRecord,onChanged:value=>registryChanged(host,pid,workspace,value),isDirty:registryDirty});
}
function createResource(){openManual('resource-add');}
function importResources(){resourceImport=null;resourceImportConfig=null;showImport();}
function openResourceItem(item){openResourceCard(item.id);}
function mountResources(){
 const host=$('#resource-list-app');if(!host)return;
 const pid=projectId,workspace=currentUser.workspace_id;
 window.ITDDesign.renderProjectRecords(host,{kind:'resources',projectId:pid,workspaceId:workspace,role:currentUser.role,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onCreate:createResource,onImport:importResources,onOpen:openResourceItem,onDelete:deleteProjectRecord,onChanged:value=>registryChanged(host,pid,workspace,value),isDirty:registryDirty});
}
function createFact(){openEditor('fact');}
function openFactResource(id){openResourceCard(id,'fact');}
function openFactWork(item,project){const workId=item.work_entry_id||(project.work_materials||[]).find(material=>material.fact_id===item.id)?.entry_id;const entry=project.workspace_entries.find(entry=>entry.id===workId);if(entry)openEditor(entry.kind,{...entry});}
function mountFacts(){
 const host=$('#facts-app');if(!host)return;
 const pid=projectId,workspace=currentUser.workspace_id;
 window.ITDDesign.renderProjectRecords(host,{kind:'facts',projectId:pid,workspaceId:workspace,role:currentUser.role,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onCreate:createFact,onOpen:openFactWork,onResource:openFactResource,onDelete:deleteProjectRecord,onChanged:value=>registryChanged(host,pid,workspace,value),isDirty:registryDirty});
}
function createIncoming(){openEditor('incoming');}
function openIncomingItem(item,project){const entry=project.workspace_entries.find(entry=>entry.id===item.id);if(entry)openEditor(entry.kind,{...entry});}
function exportJournal(kind){
 const names={ojr:'Общий журнал работ',incoming:'Журнал входного контроля',cable:'Журнал прокладки кабелей'};
 return downloadManual('/api/v1/journal-docx?project_id='+projectId+'&kind='+kind,names[kind]+'.docx');
}
function mountIncoming(){
 const host=$('#incoming-app');if(!host)return;
 const pid=projectId,workspace=currentUser.workspace_id;
 window.ITDDesign.renderProjectRecords(host,{kind:'incoming',projectId:pid,workspaceId:workspace,role:currentUser.role,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onCreate:createIncoming,onExport:()=>exportJournal('incoming'),onOpen:openIncomingItem,onDelete:deleteProjectRecord,onChanged:value=>registryChanged(host,pid,workspace,value),isDirty:registryDirty});
}
function createCableWork(){openEditor('work',{kind:'work',work_type:'cable'});}
function mountCable(){
 const host=$('#cable-app');if(!host)return;
 const pid=projectId,workspace=currentUser.workspace_id;
 window.ITDDesign.renderProjectRecords(host,{kind:'cable',projectId:pid,workspaceId:workspace,role:currentUser.role,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onCreate:createCableWork,onExport:()=>exportJournal('cable'),onOpen:openIncomingItem,onDelete:deleteProjectRecord,onChanged:value=>registryChanged(host,pid,workspace,value),isDirty:registryDirty});
}
function createWork(){openEditor('work');}
function previewWorkAct(id){return action(()=>previewAct(id));}
function mountWork(){
 const host=$('#work-app');if(!host)return;
 const pid=projectId,workspace=currentUser.workspace_id;
 const active=()=>host.isConnected&&projectId===pid&&currentUser?.workspace_id===workspace;
 window.ITDDesign.renderWorkRecords(host,{projectId:pid,workspaceId:workspace,role:currentUser.role,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onCreate:createWork,onCreateAct:createDocument,onOpen:openIncomingItem,onActPreview:previewWorkAct,onDelete:deleteProjectRecord,
  initialSelected:[...selectedEntries],initialFilters:tableFilters.work,onSelectionChange:ids=>{if(active())selectedEntries=new Set(ids);},onFiltersChange:filters=>{if(active())tableFilters.work=filters;},
  onChanged:value=>registryChanged(host,pid,workspace,value),isDirty:registryDirty});
}
function openResourceItemById(id){openResourceCard(id);}
function openWorkflowManual(operation,id){openManual(operation,id);}
function mountWorkflow(){
 const host=$('#workflow-app');if(!host)return;
 const pid=projectId,workspace=currentUser.workspace_id;
 window.ITDDesign.renderWorkflowRecords(host,{kind:host.dataset.kind,projectId:pid,workspaceId:workspace,role:currentUser.role,statusNames,findingNames,
  initialProject:pdata,getToken:registryToken,onSessionExpired:suspendWorkspace,onManual:openWorkflowManual,onNavigate:navigate,onResource:openResourceItemById,onActPreview:previewWorkAct,onDelete:deleteProjectRecord,
  onChanged:value=>registryChanged(host,pid,workspace,value),isDirty:registryDirty});
}
function objectsPage(){return title('Объекты','Все объекты и разделы в вашей локальной базе.','Рабочее пространство')+`<div class="toolbar"><input id="object-search" aria-label="Поиск объектов" placeholder="Найти объект по названию…"></div><div class="object-cards">${meta.objects.map(o=>`<button class="object-tile" data-open-object="${o.id}" data-object-search="${esc(o.name.toLowerCase())}"><span class="tile-icon">${icon('building')}</span><strong>${esc(o.name)}</strong><span class="small">Разделы РД: ${meta.projects.filter(p=>p.object_id===o.id).length}</span><span class="tile-link">Открыть объект ${icon('right')}</span></button>`).join('')||'<div class="empty">Объектов пока нет.</div>'}</div><p id="object-empty" class="empty" hidden>Объекты по этому запросу не найдены.</p>`;}
function overviewPage(){
 let html=title(state.object.name?esc(state.object.name):'Ваше рабочее пространство','Ведение ИТД: исходные данные, работы, документы и сдача.');
 if(!state.object.id)return html+card('Начните с объекта',`<p>Выберите существующий объект вверху или создайте карточку нового. Затем добавьте раздел РД и выберите комплект форм.</p><p class="hint">Можно начать с РД выбранного раздела или договора для уточнения участников. Весь комплект исходных документов сразу не нужен.</p>`,'building');
 html+=`<div class="section-toolbar">${projectSelector()}</div>`;
 if(!pdata)return `<div class="content-stack">${html}${card(state.projects.some(p=>p.id)?'Продолжите работу с разделом':'Добавьте первый раздел РД',`<p>${state.projects.some(p=>p.id)?'Выберите рабочий раздел выше. Здесь появятся действия по выбранному разделу.':'Укажите название и шифр из РД, затем выберите согласованный комплект форм.'}</p><button class="secondary" data-view="rd">Открыть разделы РД</button>`)}</div>`;
 html+=card('Ежедневная работа',`<div class="quick-actions"><button data-editor="work">Записать работу в ОЖР</button><button class="secondary" data-view="incoming">Открыть журнал входного контроля</button><button class="secondary" data-view="resources">Открыть спецификацию</button><button class="secondary" data-view="ojr">Открыть общий журнал работ</button></div><p class="hint">Работы и ресурсы относятся к выбранному разделу. ОЖР объединяет разделы объекта.</p>`,'plus');
 return `<div class="content-stack">${html}</div>`;
}
const editorWindow=createWorkspaceDialog('editor-dialog',{
 beforeClose:()=>!formDirty||confirmWorkspace('Отменить несохранённый ввод?', 'Отменить ввод'),
 onClose:()=>{$('#editor-content').innerHTML='';$('#editor-notice').textContent='';editEntry=null;formDirty=false;}
});
function closeEditor(force=false){return editorWindow.close(force);}
function openEditor(kind,entry=null){
 if($('#editor-dialog').open)return;
 editEntry=entry;formDirty=false;$('#editor-notice').textContent='';
 $('#editor-content').innerHTML=kind==='act'?actEditor():kind==='fact'?factEditor():['manual','preview'].includes(kind)?'':entryEditor(kind);
 decorateSelects();editorWindow.open({title:{act:'Создать документ',fact:'Факт монтажа',incoming:'Запись входного контроля',work:'Записать работу',journal:'Запись общего журнала'}[kind]||'Ввод сведений'});
}
function objectPage(){return title('Информация об объекте','Основные реквизиты для подготовки исполнительной документации.','Карточка объекта')+card('Общие сведения',`<div class="grid">${select('object.construction_type','Тип строительства',{'Строительство':'Строительство','Реконструкция':'Реконструкция','Капитальный ремонт':'Капитальный ремонт','Прочее':'Прочее'})}${field('object.gsn_case','Номер дела ГСН')}${field('object.name','Полное наименование объекта <span class="required">*</span>','textarea',true)}${field('object.display_name','Рабочее название (только для интерфейса)','text',true)}${field('object.city','Город','text',true)}${field('object.address','Адрес объекта','textarea',true)}</div><p class="hint">Сохраните полную формулировку из РД или согласованное наименование. Адрес хранится отдельно и не сокращает название.</p>`,'home')+card('Сроки работ по объекту',`<div class="grid">${field('object.work_start','Дата начала работ','date')}${field('object.work_end','Дата окончания работ','date')}</div><p class="hint">Даты всего объекта. Даты СМР/ПНР раздела и даты конкретных актов задаются отдельно.</p>`,'clock')+`<details id="object-permits" class="ux-disclosure"><summary>Разрешительная документация</summary><div class="disclosure-body">${permitFields()}</div></details>`;}
function permitFields(){return card('Разрешение на строительство',`<div class="grid">${field('object.permit_num','Номер')}${field('object.permit_date','Дата выдачи','date')}${field('object.permit_authority','Орган, выдавший разрешение','text',true)}</div>`,'list')+card('Заключение экспертизы проектной документации',`<div class="grid">${field('object.expertise_num','Номер')}${field('object.expertise_date','Дата выдачи','date')}${field('object.expertise_authority','Орган, выдавший заключение','text',true)}</div>`,'check');}
function orgSidebar(){return `<div class="org-list">${state.participants.map((o,i)=>`<button data-org="${i}" class="${i===orgIndex?'selected':''}"><small>${esc(o.roles.map(r=>meta.roles[r]||r).join(', '))}</small>${esc(o.full_name||'Новая организация')}<p class="hint">Представителей: ${(o.representatives||[]).length}</p></button>`).join('')}</div><button data-action="add-org" class="secondary">${icon('plus')}Добавить организацию</button>`;}
function roleOptions(){let result={...meta.roles};if(state.object.developer_functions!=='technical_customer')delete result.customer;if(!state.object.control_external)delete result.customer_control;if(!state.object.author_supervision)delete result.author_supervision;if(!state.participants.some(o=>o.roles.includes('developer')))result={developer:meta.roles.developer};return result;}
function roleChecks(path,values,options){return `<div class="choices">${Object.entries({...options,...Object.fromEntries(values.filter(r=>!options[r]).map(r=>[r,r]))}).map(([r,label])=>`<label class="choice"><input type="checkbox" data-array="${esc(path)}" value="${esc(r)}" ${values.includes(r)?'checked':''}>${esc(label)}</label>`).join('')}</div>`;}
function participantsPage(){const o=state.participants[orgIndex];let html=title('Участники строительства','Организации и уполномоченные представители вашего объекта.',`${state.participants.length} организаций`);if(!o)return html+card('Добавьте первого участника',`<div class="empty">Начните с застройщика.<br>Затем укажите схему взаимодействия и остальных участников.</div><button data-action="add-org">${icon('plus')}Добавить застройщика</button>`,'building');
 const p=`participants.${orgIndex}`;html+=card(o.id?'Организация № '+o.id:'Новая организация',`${!o.id?'<button class="ghost danger" data-action="remove-org">Убрать несохранённую организацию</button>':''}<h3>Типы участника</h3>${roleChecks(p+'.roles',o.roles,roleOptions())}<div class="grid">${field(p+'.full_name','Полное наименование <span class="required">*</span>','textarea',true)}${field(p+'.short_name','Краткое наименование для документов','text',true)}${field(p+'.inn','ИНН','text',false,'inputmode="numeric"')}${field(p+'.ogrn','ОГРН','text',false,'inputmode="numeric"')}${field(p+'.postal_code','Индекс')}${field(p+'.phone','Телефон','tel')}${field(p+'.address','Адрес','textarea',true)}${field(p+'.email','Электронная почта','email',true)}${field(p+'.sro_info','Наименование СРО','text',true)}${field(p+'.sro_ogrn','ОГРН СРО')}${field(p+'.sro_inn','ИНН СРО')}${field(p+'.sro_certificate_num','Номер свидетельства СРО')}${field(p+'.sro_certificate_date','Дата свидетельства СРО','date')}</div>${o.roles.includes('developer')?developerPanel():''}<details class="rep"><summary>Назначения организации в документах</summary><p class="hint">Выберите роль только при наличии основания. Эти назначения общие для всех разделов объекта.</p>${roleChecks(p+'.document_roles',o.document_roles||[],meta.document_roles)}</details>`,'building');
 html+=card('Уполномоченные представители',`<p class="hint">Роли представителей назначаются на титульном листе ОЖР, в таблице «Уполномоченные представители».</p>${(o.representatives||[]).map((r,j)=>repPanel(p,j,r)).join('')||'<p class="small">Представители ещё не добавлены.</p>'}<button class="secondary" data-action="add-rep">${icon('plus')}Добавить представителя</button>`,'user');return html;}
function developerPanel(){const functions=[['self','Сам застройщик'],['technical_customer','Передаёт функции техническому заказчику']].map(([v,t])=>`<label class="choice"><input type="radio" name="functions" data-path="object.developer_functions" value="${v}" ${state.object.developer_functions===v?'checked':''}>${t}</label>`).join('');const selfLabel=state.object.developer_functions==='self'?'Сам застройщик':'Сам технический заказчик';const externalLabel=state.object.developer_functions==='self'?'Строительная организация':'Сторонняя организация';const controlSelf=state.object.control_self===1;const controlExternal=state.object.control_external===1&&state.object.control_self!==1;const control=state.object.developer_functions?`<h3>Строительный контроль осуществляет</h3><div class="choices">${controlChoice('self',selfLabel,controlSelf)}${controlChoice('external',externalLabel,controlExternal)}</div><p class="hint">Выберите, кто осуществляет строительный контроль: сам застройщик (техзаказчик) или сторонняя организация. От выбора зависит, какой связанный тип участника появится в списке.</p>`:'';return `<div class="callout"><h3>Как организована работа застройщика?</h3><p>Укажите, кто выполняет функции по организации строительства и заключению договоров. Выбор фиксирует сообщённую вами схему взаимодействия.</p><div class="choices">${functions}</div>${control}${check('object.author_supervision','Предусмотрен авторский надзор')}</div>`;}
const authorityUploads=new Map();
function authorityFile(path,rep){
 const id='authority-file-'+path.replaceAll('.','-');
 const pendingFile=authorityUploads.get(rep);
 const existing=pdata?.attachments?.find(a=>a.id===rep.order_attachment_id);
 const name=pendingFile?.name||existing?.original_name;
 const picker=name?`<div class="toolbar"><span>${esc(name)}</span><button type="button" data-pick-file="${id}">Изменить</button><button type="button" data-authority-download="${path}">Скачать</button><input hidden type="file" id="${id}" aria-label="Изменить файл документа"></div>`:uploadZone(id,'Добавить файл');
 return `<div class="field" data-authority="${path}"><span>Файл документа</span>${picker}</div>`;
}
document.addEventListener('change',event=>{
 const container=event.target.closest('[data-authority]');
 if(!container||event.target.type!=='file'||!event.target.files.length)return;
 const file=event.target.files[0],path=container.dataset.authority,rep=get(path);
 if(file.size>32*1024*1024){notice('Файл больше 32 МБ');return;}
 authorityUploads.set(rep,file);dirty=true;container.outerHTML=authorityFile(path,rep);
});
document.addEventListener('click',event=>{
 const button=event.target.closest('[data-authority-download]');if(!button)return;
 const rep=get(button.dataset.authorityDownload),file=authorityUploads.get(rep);
 if(!file){originalManualFile({id:rep.order_attachment_id,original_name:pdata.attachments.find(a=>a.id===rep.order_attachment_id)?.original_name});return;}
 const url=URL.createObjectURL(file),link=document.createElement('a');link.href=url;link.download=file.name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
async function uploadAuthorityFiles(){
 for(const org of state.participants)for(const rep of org.representatives){
  const file=authorityUploads.get(rep);if(!file)continue;
  if(!projectId)throw Error('Выберите раздел для загрузки распорядительного документа');
  const result=await uploadFile(file,'order');rep.order_attachment_id=result.id;authorityUploads.delete(rep);
 }
}
function repPanel(p,j,r){p+=`.representatives.${j}`;return `<details class="rep" open><summary>${esc(r.fio||[r.last_name,r.first_name,r.middle_name].filter(Boolean).join(' ')||'Новый представитель')}</summary>${!r.id?`<button class="ghost danger" data-remove-rep="${j}">Убрать несохранённого представителя</button>`:''}<div class="grid">${field(p+'.position','Должность <span class="required">*</span>')}${field(p+'.email','E-mail','email')}${field(p+'.last_name','Фамилия')}${field(p+'.first_name','Имя')}${field(p+'.middle_name','Отчество')}${field(p+'.nrs_id','Номер в НРС')}${select(p+'.status','Статус',{'Действует':'Действует','Отозван':'Отозван'})}</div><h3 class="rep astryx-heading">Распорядительный документ</h3>${authorityFile(p,r)}<div class="grid">${select(p+'.authority_type','Тип документа',{'Приказ':'Приказ','Распоряжение':'Распоряжение','Доверенность':'Доверенность','Указания':'Указания','Постановления и решения':'Постановления и решения'})}${field(p+'.authority_num','Номер')}${field(p+'.authority_date','Дата','date')}</div></details>`;}
function projectsPanel(){return card('Разделы рабочей документации',state.projects.map((p,i)=>`<div class="rep"><div class="split"><h3>${esc(p.name||'Новый раздел')}</h3>${!p.id?`<button class="ghost danger" data-remove-project="${i}">Убрать</button>`:''}${p.id?`<button class="ghost" data-project="${p.id}">${p.id===projectId?icon('check')+'Выбран':'Выбрать'}</button>`:''}</div><div class="grid">${field(`projects.${i}.section_code`,'Обозначение раздела','text',false,p.id?'readonly':'')}${field(`projects.${i}.code`,'Шифр РД')}${field(`projects.${i}.name`,'Полное название раздела','text',true)}${field(`projects.${i}.city`,'Город')}${field(`projects.${i}.gip`,'Главный инженер проекта (ГИП)')}${field(`projects.${i}.inv_num`,'Инвентарный номер проекта')}${field(`projects.${i}.smr_start`,'Начало СМР раздела','date')}${field(`projects.${i}.smr_end`,'Окончание СМР раздела','date')}${field(`projects.${i}.pnr_start`,'Начало ПНР раздела','date')}${field(`projects.${i}.pnr_end`,'Окончание ПНР раздела','date')}${select(`projects.${i}.form_set`,'Комплект форм',Object.fromEntries(templateSets.map(v=>[v,v])))}</div></div>`).join('')+`<button class="secondary add-project" data-action="add-project">${icon('plus')}Добавить раздел</button><p class="hint">Шифр и название перепишите из РД. Комплект форм выбирается отдельно; дополнительные акты Минстроя подключаются по составу работ.</p>`,'file');}
function projectSelector(){return `<label class="field"><span>Рабочий раздел</span><select id="project-select"><option value="">Выберите раздел…</option>${state.projects.filter(p=>p.id).map(p=>option(p.id,p.code+' «'+p.name+'»',projectId)).join('')}</select></label>`;}
function rdPage(){return title('Рабочая документация','Разделы и файлы рабочей документации.','Источники')+projectsPanel()+(projectId&&currentUser?.role!=='viewer'?'<div class="toolbar"><button type="button" class="secondary" data-open-write-previews>Предпросмотры изменений</button></div>':'')+card('Файлы рабочей документации',`<p class="hint">В ZIP эти файлы попадут в папку «Рабочая документация». Сначала сохраните карточку и выберите раздел.</p>${uploadZone('file-input','Добавить файлы РД',{multiple:true})}<ul class="file-list">${pending.map((f,i)=>`<li><span>${esc(f.name)} <small>ожидает сохранения</small></span><button class="ghost" data-remove-file="${i}">Убрать</button></li>`).join('')}${(pdata?.attachments||[]).filter(a=>a.doc_type==='rd').map(a=>`<li><span><button class="record-name" data-original="${a.id}">${esc(a.original_name)}</button><br><small>${a.doc_date?esc(displayTableDate(a.doc_date)):'Дата документа не указана'}</small></span><span class="pill" tabindex="0" title="Оригинал сохранён в локальном архиве и связан с разделом. Это не означает проверку документа или включение в ZIP выпусков.">Оригинал сохранён</span></li>`).join('')}</ul>`,'upload')+(pdata?'<div id="source-files-app"></div>':'');}
function projectGuard(){return card(state.object.id?'Выберите рабочий раздел':'Сначала выберите объект',`<p>${!state.object.id?'Выберите объект на вкладке «Обзор».':state.projects.some(p=>p.id)?'Выберите рабочий раздел на вкладке «Обзор».':'Добавьте раздел РД, чтобы сохранять работы и документы.'}</p>${state.object.id&&!state.projects.some(p=>p.id)?'<button data-view="rd">Добавить раздел РД</button>':'<button data-view="overview">Открыть обзор</button>'}`);}
function idPage(){
  if(journalViews.includes(workspaceView))return journalsWorkspace();
  const descriptions=['Реестр и основные документы.','Спецификация, входной контроль и монтаж.','Исполнительные схемы.','Шаблоны документов.'];
  let html=title('Исполнительная документация',descriptions[tab])+'<div id="section-tabs" class="section-tabs"></div>';
  if(!pdata)html+=projectGuard();
  else html+=`<div class="content-stack">${[packagePage,resourcePage,()=>'<div id="schemes-app"></div>',()=>'<div id="templates-app"></div>'][tab]()}</div>`;
  return `<div class="content-stack id-workspace">${html}</div>`;
}
function journalsWorkspace(){
  let html=title('Журналы','Журналы производства и контроля работ.')+'<div id="journal-tabs" class="section-tabs"></div>';
  if(!pdata)html+=projectGuard();
  else html+=`<div class="content-stack">${journalsPage()}</div>`;
  return `<div class="content-stack id-workspace">${html}</div>`;
}
function mountSectionTabs(){
  if(!window.ITDDesign)return;
  const idHost=$('#section-tabs'),journalHost=$('#journal-tabs');
  if(idHost){
   const reviewOptions=['check','delivery'].includes(packagePanel)?[{value:'check',label:'Проверка'},{value:'delivery',label:'Сдача'}]:[];
   window.ITDDesign.renderSectionTabs(idHost,{label:'Разделы ИД',value:workspaceView,onChange:navigate,items:[
    {label:'Комплект ИД',options:[{value:'registry',label:'Реестр ИД'},{value:'documents',label:'Основные документы'},...reviewOptions]},
    {label:'Ресурсы',options:[{value:'resources',label:'Спецификация'},{value:'incoming',label:'Входной контроль'},{value:'facts',label:'Факт монтажа'}]},
    {value:'schemes',label:'Схемы'},{value:'templates',label:'Шаблоны документов'}
   ]});
  }
  if(journalHost)window.ITDDesign.renderSectionTabs(journalHost,{label:'Виды журналов',value:journalView()==='ojr'?'ojr:'+journalSection:journalView(),onChange:journalTabChange,items:[{label:'ОЖР',options:ojrSectionItems.map(([key,label])=>({value:'ojr:'+key,label}))},{value:'journal',label:'ЖВК'},{value:'cable',label:'ЖПК'}]});
}
function journalTabChange(value){
 if(value.startsWith('ojr:'))selectOjrSection(value.slice(4));
 else navigate(value);
}
function actName(act){return pdata.forms.find(f=>f.code===act.act_type)?.name||act.act_type;}
function helpTip(label,text){return `<details class="help-tip"><summary aria-label="${esc(label)}" title="${esc(label)}"><span aria-hidden="true">?</span></summary><p>${esc(text)}</p></details>`;}
function packagePage(){
  if(packagePanel==='registry')return '<div id="registry-app"></div>';
  if(packagePanel==='check')return `<div class="content-stack">${checkPage()}</div>`;
  if(packagePanel==='delivery')return `<div class="content-stack">${deliveryPage()}</div>`;
  return '<div id="documents-app"></div>';
}
const sourceTypeNames={contract:'Договор',order:'Распорядительный документ',quality:'Документ, подтверждающий качество',scheme:'Схема',rd:'Рабочая документация',other:'Другой файл'};
function sourceType(a){return a.file_kind||(['certificate','passport'].includes(a.doc_type)?'quality':a.doc_type);}
function sourceTypeOptions(value='contract'){return Object.entries(sourceTypeNames).map(([k,v])=>option(k,v,value)).join('');}
function openSourceFileCard(id){
 const file=pdata.source_files?.find(a=>a.id===id)||pdata.attachments.find(a=>a.id===id);if(!file)return;
 openEditor('manual');editorWindow.setTitle('Исходный файл');
 $('#editor-content').innerHTML=`<h3>${esc(file.original_name||file.title)}</h3><p>${esc(sourceTypeNames[sourceType(file)]||'Другой файл')}</p><div class="toolbar"><button type="button" data-original="${file.id}">Скачать файл</button><button type="button" class="secondary danger" data-file-delete="${file.id}">Удалить</button></div>`;
}
let filePlan=null;
async function previewFiles(purpose,attachmentId=null){
 if(dirty||formDirty)throw Error('Сначала сохраните изменения.');
 if(!projectId)throw Error('Выберите раздел');
 try{
  filePlan=await api('/api/files/plan',{project_id:projectId,purpose,attachment_id:attachmentId});
 }catch(error){
  if(!error.message.includes('Сначала выполните восстановление'))throw error;
  if(!await confirmWorkspace('Восстановить незавершённые файловые операции и повторить проверку?', 'Восстановить файлы'))return;
  await api('/api/files/recover',{project_id:projectId,confirmed:true});
  filePlan=await api('/api/files/plan',{project_id:projectId,purpose,attachment_id:attachmentId});
 }
 const labels={repair:'Восстановить архивную копию',add:'Добавить',remove:'Удалить из БД и с диска',detach:'Убрать из раздела; сохранить в других разделах',restore:'Вернуть копию из архива'};
 openEditor('manual');editorWindow.setTitle(purpose==='delete'?'Удаление файла':'Проверка файлов');
 $('#editor-content').innerHTML=`<p>${filePlan.plan.actions.length?'Проверьте изменения перед применением.':'Изменений не требуется.'}</p>${filePlan.plan.actions.length?journalTable(['Файл','Изменение'],filePlan.plan.actions.map(a=>[`<span class="cell-text">${esc(a.name)}</span>${a.path?`<small>${esc(a.path)}</small>`:''}`,`${esc(labels[a.action])}${a.unlink_resources?.length?`<p>Будут сняты связи с ресурсами этого раздела: ${a.unlink_resources.length}.</p>`:''}${a.action==='add'&&!a.existing&&a.type!=='rd'?`<label class="field"><span>Тип файла</span><select data-plan-type="${esc(a.path)}">${sourceTypeOptions(a.type)}</select></label>`:''}${a.paths?.length?`<details class="technical-detail"><summary>Файлы на диске: ${a.paths.length}</summary>${a.paths.map(p=>`<p>${esc(p)}</p>`).join('')}</details>`:''}`])):''}${filePlan.plan.blocked.length?'<h3>Сохранены без изменений</h3><ul>'+filePlan.plan.blocked.map(a=>`<li><strong>${esc(a.name)}</strong><p>${esc(a.reason)}</p></li>`).join('')+'</ul>':''}<div class="toolbar rep">${filePlan.plan.actions.length?`<button type="button" data-files-apply>${purpose==='delete'?'Удалить':'Применить изменения'}</button>`:''}<button type="button" class="secondary" data-dialog-close>Закрыть</button></div>`;
 decorateSelects();
}

function workPage(){return '<div id="work-app"></div>';}
function incomingPage(){return '<div id="incoming-app"></div>';}
function journalView(){return ['journal','cable'].includes(workspaceView)?workspaceView:'ojr';}
function journalsPage(){
  const active=journalView();
  if(active==='journal')return incomingPage();
  if(active==='cable')return '<div id="cable-app"></div>';
  return ojrPage();
}
const statusNames={pending:'Ожидает подтверждения',confirmed:'Подтверждено',void:'Отозвано',matches:'Соответствует',mismatch:'Несоответствие',uncertain:'Не удалось подтвердить',sent:'Передано',remarks:'Получены замечания',corrected:'Исправлено',accepted:'Принято',open:'Открыто',resolved:'Устранено',required:'Требуется',not_applicable:'Не применяется',prepared:'Файл ещё не создан',draft:'Черновик',final:'Окончательная версия',file_present:'Оригинал в архиве',registered:'Зарегистрировано',available:'Есть документ',missing:'Документ отсутствует',inactive:'Документ неактивен',unselected:'Версия не выбрана',binding_mismatch:'Связь не соответствует требованию'};
const findingNames={work_supply_invalid:'Поставка использованного ресурса отклонена, изменилась или не покрывает расход',entry_source_changed:'Рабочая запись изменилась после включения в акт',entry_resource_missing:'Ресурс связанной работы исключён из акта',act_material_invalid:'Поставка акта не принята или её ресурс исключён',supply_overallocated:'Превышено количество поставки',participant_outside_period:'Дата акта вне периода участия организации',facts_pending:'Есть неподтверждённый факт',fact_quantity_unknown:'Количество факта неизвестно',fact_total_differs:'Сумма приростов отличается от итогового факта',fact_dates_incomplete:'Не все даты факта известны',fact_unit_changed:'Изменилась единица ресурса',qty_fact_unknown:'Итоговый факт неизвестен',fact_exceeds_project:'Факт превышает проект',quality_document_missing:'Нет связанного документа качества',quality_unreviewed:'Документ качества не проверен',quality_stale:'Проверка качества устарела',quality_mismatch:'Несоответствие документа качества',quality_uncertain:'Применимость документа качества не подтверждена',act_fact_not_confirmed:'Факт акта не подтверждён',act_fact_resource_missing:'Ресурс факта отсутствует в акте',act_signed_before_work_end:'Акт подписан раньше окончания работ',act_facts_missing:'Не все ресурсы акта связаны с фактом',act_required_fields_missing:'Не заполнены обязательные поля акта',release_context_changed:'Сведения изменились после создания файла',act_context_error:'Ошибка контекста акта',requirements_not_configured:'Не указан перечень документов к сдаче',requirement_missing:'Не подготовлен документ из перечня',requirement_inactive:'Связанный документ неактивен',requirement_unselected:'Выпуск документа из перечня не выбран',requirement_binding_mismatch:'Связь документа из перечня не соответствует требованию',specification_pending:'Есть вопросы по спецификации',open_remark:'Открыто замечание при сдаче'};
function resourceSelect(){return `<label class="field wide"><span>Ресурс *</span><select name="resource_id" required><option value="">Выберите…</option>${pdata.resources.map(r=>option(r.id,'№ '+r.id+'. '+r.name+'. '+r.unit,'')).join('')}</select></label>`;}
function factEditor(){
 const work=`<label class="field wide"><span>Запись в ОЖР *</span><select name="work_entry_id" required><option value="">Выберите запись…</option>${pdata.workspace_entries.filter(e=>e.kind==='work').map(e=>option(e.id,[displayTableDate(e.entry_date),e.title].filter(Boolean).join('. '))).join('')}</select></label>`;
 return card('Добавить факт',`<form id="fact-form" data-source-key="web:${crypto.randomUUID()}"><div class="grid">${work}${resourceSelect()}${input('quantity','Количество монтажа','','number')}<label class="field"><span>Подтверждение</span><select name="status"><option value="pending">Ожидает подтверждения</option><option value="confirmed">Подтверждено</option></select></label></div><div class="ux-form-actions"><button type="submit">Сохранить факт</button><button type="button" class="secondary" data-action="cancel-entry">Отменить</button></div></form>`,'plus');
}
function resourceLabel(id){
 const r=pdata.resources.find(r=>r.id===Number(id));
 if(!r)return 'Ресурс недоступен (ID '+id+')';
 const parts=[r.spec_num?'Поз. '+r.spec_num:null,r.name,r.type_mark].filter(Boolean);
 return parts.map((part,index)=>index===parts.length-1?part:String(part).trimEnd().replace(/\.+$/,'')).join('. ');
}
function checkPage(){return '<div id="workflow-app" data-kind="check"></div>';}
function deliveryPage(){return '<div id="workflow-app" data-kind="delivery"></div>';}
function filteredEntries(kind){const f=tableFilters[kind];const entries=kind==='incoming'?pdata.journals.incoming.map(e=>({...e,entry_date:e.entry_date||'',search_fields:[JSON.stringify(e.work_fields),e.resource?.name,e.supply?.supplier,e.supply?.batch_num,e.quality_review?.note].join(' ')})):pdata.workspace_entries;return entries.filter(e=>e.kind===kind&&(!f.unbound||!e.act_id)&&(!f.from||(e.entry_date&&e.entry_date>=f.from))&&(!f.to||(e.entry_date&&e.entry_date<=f.to))&&[e.title,e.details,e.responsible,e.conditions,e.unit,e.quantity,e.search_fields].join(' ').toLowerCase().includes(f.search.toLowerCase())).sort((a,b)=>(b.entry_date||'').localeCompare(a.entry_date||'')||b.id-a.id);}
function input(name,label,value='',type='text',wide=false){return `<label class="field ${wide?'wide':''}"><span>${label}</span><input name="${esc(name)}" value="${esc(value)}" type="${type}" ${type==='number'?'step="any" min="0"':''} ${name==='title'||label.includes('*')?'required':''}></label>`;}
function entryEditor(kind){const e=editEntry?.kind===kind?editEntry:{};return kind==='work'?workEntryEditor(e):specializedEntryEditor(kind,e);}
function actForms(){return pdata.templates||[];}
function actFormOptions(formSet){return '<option value="">Выберите шаблон…</option>'+actForms().filter(f=>f.form_set===formSet).map(f=>option(f.code,f.name,'')).join('');}
function updateActTemplateChoices(){
 const select=$('#act-type');
 select.innerHTML=actFormOptions($('#act-form-set').value);
 enhanceSelect(select);
 renderActFields(select.value);
}
document.addEventListener('change',event=>{
 if(event.target.id==='act-form-set')updateActTemplateChoices();
});
function actEditor(){const formSet=pdata.project.form_set||templateSets[0];return card('Создать документ',`<form id="act-form"><div class="grid">${tSelect('Комплект форм',templateSets.map(v=>[v,v]),formSet,'id="act-form-set" required')}<label class="field"><span>Шаблон документа</span><select name="act_type" id="act-type" required>${actFormOptions(formSet)}</select></label>${input('date_signed','Дата подписания','','date')}</div>${actPeopleSelects()}<div id="act-fields" class="workspace-stack"></div><h3 class="rep">Работы, включаемые в документ</h3><div class="check-list">${pdata.workspace_entries.filter(e=>e.kind==='work'&&!e.act_id).map(e=>`<label class="choice"><input type="checkbox" name="entry_ids" value="${e.id}" ${selectedEntries.has(e.id)?'checked':''}>${esc(e.entry_date)}. ${esc(e.title)}</label>`).join('')||'<span class="small">Можно создать документ без записей журнала.</span>'}</div><section id="act-resources" class="workspace-stack" hidden><h3>Ресурсы</h3><div class="check-list">${pdata.resources.map(r=>`<label class="choice"><input type="checkbox" name="resource_ids" value="${r.id}" ${linkedActResourceIds([...selectedEntries]).has(r.id)?'checked':''}>${esc(r.name)}</label>`).join('')||'<span class="small">Ресурсы ещё не добавлены.</span>'}</div><h3>Подтверждённые факты монтажа</h3><div class="check-list">${pdata.workflow.fact_records.filter(f=>f.status==='confirmed').map(f=>`<label class="choice"><input type="checkbox" name="fact_ids" value="${f.id}">Факт № ${f.id}. Ресурс № ${f.resource_id}. ${esc(f.location)}. ${esc(f.quantity??'Количество неизвестно')}</label>`).join('')||'<span class="small">Подтверждённые факты ещё не внесены.</span>'}</div><p class="hint">Ресурсы выбранных фактов и записей работ должны входить в состав документа.</p></section><section id="act-schemes" class="workspace-stack" hidden><h3>Исполнительные схемы</h3><div class="check-list">${pdata.schemes.map(s=>`<label class="choice"><input type="checkbox" name="scheme_ids" value="${s.id}">${esc(s.num)}. ${esc(s.name)}</label>`).join('')||'<span class="small">Схемы ещё не зарегистрированы.</span>'}</div></section><button type="submit">Создать документ</button> <button type="button" class="secondary" data-action="cancel-entry">Отменить ввод</button><p class="hint">Номер назначается автоматически. Выбранные записи связываются с документом; содержание полей нужно проверить. Проверка сведений и создание DOCX доступны в «Комплекте ИД».</p></form>`,'plus');}
async function refreshMeta(){meta=await api('/api/bootstrap');$('#object-select').innerHTML='<option value="">Выберите объект или создайте новый</option>'+meta.objects.map(o=>option(o.id,o.display_name||o.name,state.object.id)).join('');}
async function loadProject(pid,activate=false){
 const nextId=pid?Number(pid):null,restoreTables=tableLoading();
 try{
  const next=nextId?await api('/api/project?project_id='+nextId):null;
  if(next?._revision)next._checkedAt=Date.now();
  if(activate&&nextId&&currentUser?.role!=='viewer')await api('/api/activate',{project_id:nextId});
  if(projectId!==nextId)selectedEntries.clear();projectId=nextId;pdata=next;editEntry=null;
 }catch(error){const select=$('#project-select');if(select){select.value=projectId||'';select.dispatchEvent(new Event('smart-sync'));}throw error;}
 finally{restoreTables();}
}
async function loadObject(id){
 try{
  const next=await api('/api/workspace'+(id?'?object_id='+id:''));
  const current=next.projects.find(p=>p.id===meta.active_project_id);
  await loadProject(current?.id||null);
  state=next;authorityUploads.clear();orgIndex=0;pending=[];dirty=false;formDirty=false;
  $('#object-select').value=state.object.id||'';render();
 }catch(error){$('#object-select').value=state.object.id||'';$('#object-select').dispatchEvent(new Event('smart-sync'));throw error;}
}
async function save(){
 if(!validateInputs($('#content')))return;
 await uploadAuthorityFiles();
 const participants=state.participants.map(org=>({...org,
  representatives:org.representatives.map(({document_roles,...rep})=>rep)
 }));
 state=await api('/api/save',{...state,participants});
 dirty=pending.length>0;
 await refreshMeta();
 if(projectId&&!state.projects.some(p=>p.id===projectId))await loadProject(null);
 if(pending.length&&!projectId)throw Error('Карточка сохранена. Выберите раздел для загрузки ожидающих файлов.');
 if(pending.length)await uploadPending();
 dirty=false;
 if(projectId)await loadProject(projectId);
 render();toast('Сведения сохранены в базе');
}
function addFiles(files){for(const f of files){if(f.size>32*1024*1024){notice('Файл '+f.name+' больше 32 МБ. Добавьте его через file-add.');continue;}if(!pending.some(x=>x.name===f.name&&x.size===f.size))pending.push(f);}dirty=true;render();}
function readUploadContent(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(Error('Не удалось прочитать файл'));reader.readAsDataURL(file);});}
async function uploadFile(file,type){if(!file)throw Error('Выберите файл');if(file.size>32*1024*1024)throw Error('Файл больше 32 МБ: '+file.name);const content=await readUploadContent(file);return api('/api/upload',{project_id:projectId,name:file.name,content,doc_type:type});}
async function uploadPending(){while(pending.length){await uploadFile(pending[0],'rd');pending.shift();}}
async function exportHandoff(name){if(dirty)throw Error('Сначала сохраните карточку.');state=await api('/api/workspace?object_id='+state.object.id);const projects=await Promise.all(state.projects.filter(p=>p.id).map(p=>api('/api/project?project_id='+p.id)));downloadJson({...state,project_data:projects},name);}
function downloadJson(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function downloadRelease(id){const r=await fetch('/api/download?project_id='+projectId+'&release_id='+id,{headers:{'X-ITD-Token':token}});if(!r.ok)throw Error((await r.json()).error);const blob=await r.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;const rel=pdata.releases.find(x=>x.id===id);a.download=rel?.path.split(/[\\/]/).pop()||'Документ';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
document.addEventListener('input',e=>{const el=e.target;if(el.closest('#act-form')&&el.name==='date_signed')updateActAutomaticValues();if(el.closest('#entry-form, #incoming-day-form, #act-form, #fact-form, #manual-form, #review-form'))formDirty=true;if(el.dataset.path){put(el.dataset.path,el.type==='checkbox'?Number(el.checked):el.dataset.path.endsWith('order_attachment_id')?(el.value?Number(el.value):null):el.value||null);}if(el.id==='object-search'){const tiles=[...document.querySelectorAll('[data-object-search]')];tiles.forEach(tile=>tile.hidden=!tile.dataset.objectSearch.includes(el.value.toLowerCase()));$('#object-empty').hidden=tiles.length===0||tiles.some(tile=>!tile.hidden);}});
document.addEventListener('change',e=>{const el=e.target;if(el.closest('#entry-form, #incoming-day-form, #act-form, #fact-form, #manual-form, #review-form'))formDirty=true;if(el.dataset.array){let old=get(el.dataset.array)||[];put(el.dataset.array,el.checked?[...old,el.value]:old.filter(v=>v!==el.value));render();}if(el.dataset.control&&el.checked){put('object.control_self',el.dataset.control==='self'?1:0);put('object.control_external',el.dataset.control==='external'?1:0);render();}if(['object.developer_functions','object.control_self','object.control_external','object.author_supervision'].includes(el.dataset.path)){render();}if(el.id==='object-select')action(async()=>{if((dirty||formDirty)&&!await confirmWorkspace('Есть несохранённые изменения. Перейти к другому объекту?')){el.value=state.object.id||'';return;}await loadObject(el.value);navigate(state.object.id?'overview':'object');});if(el.id==='project-select')action(async()=>{if(formDirty){el.value=projectId||'';throw Error('Сначала сохраните запись или отмените ввод в форме ниже.');}if(pending.length&&projectId&&Number(el.value)!==projectId)throw Error('Сначала сохраните ожидающие файлы в выбранном разделе или уберите их из списка.');await loadProject(el.value,true);render();});if(el.id==='file-input')addFiles(el.files);if(el.id==='act-type')renderActFields(el.value);if(el.matches('#act-form [name=resource_ids]'))el.dataset.manualChoice='1';if(el.closest('#act-form')&&['entry_ids','fact_ids'].includes(el.name))syncLinkedActResources();});
document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b||b.closest('#account-page,#prompt-dialog,#login-dialog'))return;
 if(b.hasAttribute('data-open-knowledge')||b.hasAttribute('data-dialog-close')||b.closest('#knowledge-dialog,#write-preview-dialog')||b.hasAttribute('data-open-write-previews'))return;
 if(b.id==='account-open')return;
 if(formDirty&&b.closest('#breadcrumbs,#overview-object-picker,#sidebar,#content,#actions')&&!b.closest('form')&&!b.form){notice('Сначала сохраните запись или отмените ввод в форме ниже.');return;}
 if(b.dataset.step!==undefined){step=Number(b.dataset.step);editEntry=null;notice();render();return;}
 if(b.dataset.org!==undefined){orgIndex=Number(b.dataset.org);render();return;}
 if(b.dataset.removeRep!==undefined){state.participants[orgIndex].representatives.splice(Number(b.dataset.removeRep),1);dirty=true;render();return;}
 if(b.dataset.removeProject!==undefined){state.projects.splice(Number(b.dataset.removeProject),1);dirty=true;render();return;}
 if(b.dataset.removeFile!==undefined){pending.splice(Number(b.dataset.removeFile),1);render();return;}
 if(b.dataset.project){action(async()=>{await loadProject(b.dataset.project,true);render();});return;}
 if(b.dataset.download){action(()=>downloadRelease(Number(b.dataset.download)));return;}
 if(b.dataset.generate){action(async()=>{const r=await api('/api/generate',{project_id:projectId,act_id:Number(b.dataset.generate)});await loadProject(projectId);render();toast('Создан черновик DOCX, версия № '+r.release_id);});return;}
 if(b.dataset.editEntry||b.dataset.copyEntry){const entry={...pdata.workspace_entries.find(x=>x.id===Number(b.dataset.editEntry||b.dataset.copyEntry))};if(b.dataset.copyEntry){if(formDirty&&!await confirmWorkspace('Оставить изменения без сохранения и создать копию?'))return;delete entry.id;delete entry.revision;entry.act_id=null;entry.title='Копия: '+entry.title;}if(b.dataset.copyEntry&&$('#editor-dialog').open){editEntry=entry;formDirty=false;$('#editor-content').innerHTML=entryEditor(entry.kind);editorWindow.setTitle('Копия работы');decorateSelects();}else openEditor(entry.kind,entry);return;}
 if(b.id==='new-object'||b.dataset.action==='new-object'){action(async()=>{if((dirty||formDirty)&&!await confirmWorkspace('Оставить несохранённые изменения и открыть новый объект?'))return;await loadObject(null);$('#object-select').value='';navigate('object');});return;}
 if(b.dataset.view){navigate(b.dataset.view);return;}
 if(b.dataset.editor){openEditor(b.dataset.editor);return;}
 if(b.dataset.openObject){action(async()=>{if((dirty||formDirty)&&!await confirmWorkspace('Оставить несохранённые изменения?'))return;await loadObject(b.dataset.openObject);navigate('overview');});return;}
 const a=b.dataset.action;
 if(a==='objects'){navigate('objects');return;}
 if(a==='close-editor'){closeEditor();return;}
 if(a==='remove-org'){state.participants.splice(orgIndex,1);orgIndex=Math.max(0,orgIndex-1);dirty=true;render();}
 if(a==='add-org'){state.participants.push({full_name:'',roles:[state.participants.some(o=>o.roles.includes('developer'))?'builder':'developer'],document_roles:[],representatives:[]});orgIndex=state.participants.length-1;dirty=true;render();}
 if(a==='add-rep'){state.participants[orgIndex].representatives.push({status:'Действует'});dirty=true;render();}
 if(a==='add-project'){state.projects.push({section_code:'',code:'',name:'',form_set:null});dirty=true;render();}
 if(a==='back'){step=Math.max(0,step-1);render();}
 if(a==='next'){step=Math.min(3,step+1);render();window.scrollTo({top:0,behavior:'smooth'});}
 if(a==='save'||a==='finish')action(async()=>{await save();if(a==='finish'){await exportHandoff('Сведения ИТД — объект '+state.object.id+'.json');toast('Сохранено. JSON со сведениями подготовлен для агента.');}});
 if(a==='export')action(()=>exportConfiguration());
 if(a==='import')chooseConfiguration();
 if(a==='statement')action(async()=>{const r=await api('/api/statement',{project_id:projectId});await loadProject(projectId);render();toast('Ведомость создана, версия № '+r.release_id);});
 if(a==='cancel-entry')closeEditor();
});

document.addEventListener('submit',e=>{e.preventDefault();const form=e.target;if(form.closest('#account-page,#prompt-dialog,#login-dialog')||currentUser?.role==='viewer'||!validateInputs(form))return;action(async()=>{if(form.getAttribute('id')==='incoming-day-form'){await submitIncomingDay(form);return;}const fd=new FormData(form);if(form.id==='uploaded-act-form'){await saveUploadedAct(form);return;}if(form.id==='document-version-form'){await saveDocumentVersion();return;}if(form.getAttribute('id')==='resource-card-form'){await submitResourceCard(form);return;}if(form.getAttribute('id')==='resource-import-form'){await submitResourceImport(form);return;}if(['special-journal-form','ojr-title-form','act-status-form'].includes(form.getAttribute('id'))){await submitArchitectureForm(form);return;}if(form.getAttribute('id')==='manual-form'){await submitManual(form);return;}if(form.getAttribute('id')==='review-form'){await api('/api/review',{project_id:projectId,act_id:Number(form.dataset.act),note:fd.get('note'),confirmed:fd.has('confirmed')});formDirty=false;await previewAct(Number(form.dataset.act));toast('Подтверждение проверки сохранено');return;}if(form.getAttribute('id')==='entry-form'){const entry={...editEntry,...Object.fromEntries(fd),kind:form.dataset.kind};entry.work_fields={...(typeof editEntry?.work_fields==='string'?JSON.parse(editEntry.work_fields):editEntry?.work_fields||{}),...Object.fromEntries(Object.entries(entry).filter(([k])=>k.startsWith('work_')&&k!=='work_type'&&k!=='work_fields').map(([k,v])=>[k.slice(5),v||null]))};for(const k of Object.keys(entry))if(k.startsWith('work_')&&!['work_type','work_fields'].includes(k))delete entry[k];for(const k of ['supply_id','quality_review_id','org_id','person_id','entry_id'])if(k in entry.work_fields)entry.work_fields[k]=entry.work_fields[k]?Number(entry.work_fields[k]):null;entry.quantity=entry.quantity==null||entry.quantity===''?null:Number(entry.quantity);if(entry.kind==='work'){entry.materials=workMaterialsDraft;entry.responsible_id=Number(entry.responsible_id)||null;}for(const k of ['resource_id','attachment_id'])entry[k]=entry[k]?Number(entry[k]):null;if(!await saveDatedJournal('/api/entry',{project_id:projectId,entry},'entry'))return;toast('Запись сохранена');editEntry=null;}else if(form.getAttribute('id')==='act-form'){const fields=collectActFields(form,actForms().find(f=>f.code===fd.get('act_type')));const r=await api('/api/act',{project_id:projectId,act_type:fd.get('act_type'),date_signed:fd.get('date_signed')||null,signatories:selectedActPeople(form),organizations:selectedActOrganizations(form),fields,entry_ids:fd.getAll('entry_ids').map(Number),resource_ids:actLinkIds(form,fd,'act-resources','resource_ids'),scheme_ids:actLinkIds(form,fd,'act-schemes','scheme_ids'),fact_ids:actLinkIds(form,fd,'act-resources','fact_ids'),resource_removals:actResourceRemovals(form,fd),work_only:form.querySelector('#act-resources')?.hidden===true});toast('Документ создан');}else if(form.getAttribute('id')==='fact-form'){const fact=Object.fromEntries(fd);fact.resource_id=Number(fact.resource_id);fact.work_entry_id=Number(fact.work_entry_id)||null;fact.quantity=fact.quantity===''?null:Number(fact.quantity);fact.source_key=form.dataset.sourceKey;await api('/api/work-fact',{project_id:projectId,fact});toast('Факт сохранён без изменения итогового количества');}closeEditor(true);if(form.dataset.kind||form.getAttribute('id')==='act-form')await reloadJournalWorkspace();await loadProject(projectId);render();});});

window.addEventListener('beforeunload',e=>{if(dirty||formDirty){e.preventDefault();e.returnValue='';}});
async function startWorkspace(){window.ITDDesign?.setLoading(true);checkDatabaseStatus();setInterval(checkDatabaseStatus,15000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkDatabaseStatus();});
try{await refreshMeta();const active=meta.projects.find(p=>p.id===meta.active_project_id);await loadObject(active?.object_id||null);const view=new URLSearchParams(location.search).get('view');navigate(['objects','overview','object','participants','rd','permits','documents','registry','schemes','templates','work','incoming','journal','cable','facts','check','delivery','manage','resources','ojr','account'].includes(view)?view:state.object.id?'overview':(meta.objects.length||currentUser?.role==='viewer')?'objects':'object');}catch(e){if(e.fields)showWorkspaceErrors(e.fields);notice(e.message);$('#content').textContent='Не удалось открыть базу. Проверьте подключение к серверу.';}finally{window.ITDDesign?.setLoading(false);}}
startAccount();


document.addEventListener('click',e=>{
 const card=e.target.closest('[data-file-card]');if(card)openSourceFileCard(Number(card.dataset.fileCard));
 const remove=e.target.closest('[data-file-delete]');
 if(remove)action(()=>previewFiles('delete',Number(remove.dataset.fileDelete)));
 if(e.target.closest('[data-files-apply]'))action(async()=>{
  const types={};document.querySelectorAll('[data-plan-type]').forEach(el=>types[el.dataset.planType]=el.value);
  const result=await api('/api/files/apply',{...filePlan,types});
  closeEditor(true);filePlan=null;await loadProject(projectId);render();toast(result.cleanup_pending?'Записи обновлены. Очистка удалённых копий продолжится при следующей проверке.':'Файлы обновлены');
 });
});

document.addEventListener('change',handleActParticipantChange);
