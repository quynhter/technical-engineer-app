'use strict';

const roleNames = {admin:'Администратор', editor:'Редактор', viewer:'Наблюдатель'};
const accountTabLabels = {profile:'Личные данные', assistants:'Ассистенты', paths:'Рабочие пути', users:'Пользователи', tokens:'Токены API', access:'Вход и сеанс'};
let currentUser;
let accountTab='profile';
let accountData=null;
let accountLoading=null;
let sessionSuspended=false;
let viewerObserver;
const viewerRestrictions=new Map();
const viewerActionStyles=new Map();
const viewerWriteActions='[type="submit"],[data-action="save"],[data-action="new-object"],[data-action="import"],[data-editor],[data-manual],[data-upload-target],[data-files-check],[data-files-apply],[data-file-delete],[data-record-delete],[data-remove-project],[data-remove-rep],[data-remove-file],[data-copy-entry],[data-material-add],[data-material-remove],[data-incoming-add],[data-incoming-remove],[data-final],[data-preview-draft],[data-resource-import-commit],[data-version-add],[data-signer-remove],[data-signature-toggle],[data-delete-document-version],[data-regenerate-document]';
function clearViewerRestrictions(){
 viewerObserver?.disconnect();viewerObserver=undefined;
 for(const [control,properties] of viewerRestrictions)for(const [name,value] of Object.entries(properties))control[name]=value;
 viewerRestrictions.clear();
 for(const [control,style] of viewerActionStyles){if(style.value)control.style.setProperty('display',style.value,style.priority);else control.style.removeProperty('display');}
 viewerActionStyles.clear();
 document.querySelectorAll('[data-read-only-note]').forEach(note=>note.remove());
}
function restrictViewerAction(control){
 restrictViewerControl(control,'disabled');
 if(!viewerActionStyles.has(control))viewerActionStyles.set(control,{value:control.style.getPropertyValue('display'),priority:control.style.getPropertyPriority('display')});
 // Inline important also wins over the library's layered display rules.
 control.style.setProperty('display','none','important');
}
function restrictViewerControl(control,property){
 if(control[property])return;
 const properties=viewerRestrictions.get(control)||{};
 if(!Object.hasOwn(properties,property))properties[property]=control[property];
 viewerRestrictions.set(control,properties);control[property]=true;
}
let finishPrompt;
let promptAccepted=false;
const promptWindow = createWorkspaceDialog('prompt-dialog', {
 onClose:()=>{
  const resolve=finishPrompt;
  finishPrompt=undefined;
  document.querySelector('#prompt-content').replaceChildren();
  resolve?.(promptAccepted);
  promptAccepted=false;
 }
});
const loginWindow = createWorkspaceDialog('login-dialog', {beforeClose:()=>sessionSuspended});

function confirmWorkspace(message, label='Продолжить'){
 $('#prompt-content').innerHTML=`<p>${esc(message)}</p><div class="account-actions"><button type="button" class="secondary" data-dialog-close>Назад</button><button type="button" id="prompt-confirm">${esc(label)}</button></div>`;
 return new Promise(resolve=>{
  finishPrompt=resolve;
  $('#prompt-confirm').onclick=()=>{promptAccepted=true;promptWindow.close(true);};
  promptWindow.open({title:'Подтверждение',focus:$('#prompt-content [data-dialog-close]')});
 });
}

function notifyWorkspace(message){
 $('#prompt-content').innerHTML=`<p>${esc(message)}</p><div class="account-actions"><button type="button" data-dialog-close>Понятно</button></div>`;
 promptWindow.open({title:'Уведомление',focus:$('#prompt-content [data-dialog-close]')});
}
function showCode(code){
 $('#prompt-content').innerHTML=`<p class="hint">Сохраните код или передайте ссылку владельцу аккаунта. Код показан один раз.</p>
 <label class="field"><span>Код входа</span><input id="issued-code" value="${esc(code)}" readonly></label>
 <div class="account-actions"><button type="button" id="copy-code">Копировать код</button><button type="button" class="secondary" id="copy-link">Копировать ссылку</button></div>
 <p class="account-message" role="status"></p>`;
 async function copy(value){
  const message=$('#prompt-content .account-message');
  try{await navigator.clipboard.writeText(value);message.textContent='Скопировано.';}
  catch(_){$('#issued-code').value=value;$('#issued-code').select();message.textContent='Скопируйте выделенное значение.';}
 }
 $('#copy-code').onclick=()=>copy(code);
 $('#copy-link').onclick=()=>copy(location.origin+'/#'+code);
 promptWindow.open({title:'Новый код входа',focus:$('#copy-code')});
}

function keepSession(session){
 token=session;
 if(session)sessionStorage.setItem('itd-session',session);
 else sessionStorage.removeItem('itd-session');
}

function setProfile(user){
 user={...user,workspace_id:user.workspace_id??currentUser?.workspace_id};
 currentUser=user;
 document.body.dataset.role=user.role;
 if(user.role!=='viewer')clearViewerRestrictions();
 if(user.role==='viewer'&&!viewerObserver){
  const readOnly=()=>{
   for(const control of viewerRestrictions.keys())if(!control.isConnected)viewerRestrictions.delete(control);
   for(const control of viewerActionStyles.keys())if(!control.isConnected)viewerActionStyles.delete(control);
   const content=document.getElementById('editor-content');
   if(content.firstElementChild&&!content.querySelector('[data-read-only-note]')){const note=document.createElement('p');note.dataset.readOnlyNote='';note.className='hint';note.textContent='Просмотр. изменение сведений недоступно для вашей роли.';content.prepend(note);}

   document.querySelectorAll('#editor-dialog [data-action="cancel-entry"]').forEach(button=>{if(button.textContent!=='Закрыть')button.textContent='Закрыть';});
   document.querySelectorAll('#new-object,:is(#content,#editor-content,#editor-footer,#actions,#sidebar) button:is('+viewerWriteActions+')').forEach(control=>{if(!control.closest('#account-page'))restrictViewerAction(control);});
   document.querySelectorAll('#content :is(input,textarea,select),#editor-content :is(input,textarea,select)').forEach(el=>{
    if(el.closest('.astryx-data-view,.astryx-table-workspace,#account-page'))return;
    const nativeInput=el.closest('.date-island')?._nativeInput;
    if(nativeInput?.matches('[data-filter],[data-table-control]'))return;
    const nativeSelect=el.closest('.select-island')?._nativeSelect;
    if(nativeSelect?.matches('#project-select,[data-journal-project],[data-table-control]'))return;
    if(el.matches('#object-search,#project-select,[data-filter],[data-check-search],[data-table-control]')||
       el.closest('.smart-select')?.querySelector('select')?.matches('#project-select,[data-journal-project],[data-table-control]')||
       el.matches('[data-journal-project]'))return;
    restrictViewerControl(el,el.matches('select,input[type=checkbox],input[type=radio],input[type=file],.smart-input')?'disabled':'readOnly');
   });
  };
  viewerObserver=new MutationObserver(readOnly);
  for(const id of ['content','editor-content','editor-footer'])viewerObserver.observe(document.getElementById(id),{childList:true,subtree:true});
  readOnly();
 }
 const avatar=$('#account-open');
 avatar.textContent='Настройки';
 avatar.setAttribute('aria-label','Настройки');
 avatar.title=`${user.first_name} ${user.last_name}. ${roleNames[user.role]}`;
 avatar.hidden=false;
 $('#session-logout').hidden=false;
}

async function logoutWorkspace(){
 if((dirty||formDirty)&&!await confirmWorkspace('Выйти без сохранения изменений?','Выйти'))return;
 try{await api('/api/logout',{});}catch(error){if(error.status!==403)throw error;}
 leaveWorkspace();
}

function accountNames(user={}){
 return `<div class="grid">
 <label class="field"><span>Имя</span><input name="first_name" autocomplete="given-name" required maxlength="80" value="${esc(user.first_name)}"></label>
 <label class="field"><span>Фамилия</span><input name="last_name" autocomplete="family-name" required maxlength="80" value="${esc(user.last_name)}"></label>
 </div>`;
}
function roleField(value){
 return `<label class="field"><span>Роль</span><select name="role">${Object.entries(roleNames).map(([role,label])=>option(role,label,value)).join('')}</select></label>`;
}
function accountCard(key, heading, body, iconName){
  return `<section class="card" data-account-panel="${key}"${key===accountTab?'':' hidden'}><h2 class="card-title"><span class="icon" aria-hidden="true">${icon(iconName)}</span>${heading}</h2>${body}</section>`;
}
function accountTabs(tabs){
  return `<nav class="tabs" aria-label="Разделы настроек">${tabs.map(([key,label])=>`<button type="button" data-account-tab="${key}" class="${key===accountTab?'active':''}" ${key===accountTab?'aria-current="page"':''}>${label}</button>`).join('')}</nav>`;
}
function adminPanels(model){
 const {settings,users}=model;
 return accountCard('assistants','Ассистенты',`<button type="button" class="secondary" data-account-task="assistants">Настроить ассистентов</button>`,'clipboard')
 + accountCard('paths','Рабочие пути',`<form class="account-form" data-account-action="settings">
 <label class="field"><span>Файл базы данных на сервере</span><input name="database_path" required value="${esc(settings.database_path)}"></label>
 <label class="field"><span>Папка ИТД на сервере</span><input name="itd_root" required value="${esc(settings.itd_root)}"></label>
 <p class="hint">Укажите полные пути к существующему файлу .db и отдельной папке ИТД для этой базы. Если папки ещё нет, приложение её создаст.</p>
 <button type="submit" class="secondary">Применить пути</button>
 <p id="settings-message" class="account-message" role="status" tabindex="-1"></p>
 </form>`,'list')
 + accountCard('users','Пользователи',`<form class="account-form" data-account-action="role">
 <label class="field"><span>Пользователь</span><select name="id" required>
 <option value="">Выберите пользователя…</option>
 ${users.map(u=>option(u.id,`${u.last_name} ${u.first_name}. ${roleNames[u.role]}${u.id===currentUser.id?' (вы)':''}`)).join('')}
 </select></label>
 <div id="account-user-tools" hidden>${roleField('viewer')}
 <div class="account-actions"><button type="submit" class="secondary" id="account-save-role">Сохранить роль</button>
 <button type="button" class="secondary" data-account-task="rotate">Сменить код входа</button>
 <button type="button" class="secondary" data-account-task="delete">Удалить пользователя</button></div></div>
 </form>
 <details class="ux-disclosure"><summary>Добавить пользователя</summary><div class="disclosure-body">
 <form class="account-form" data-account-action="create">${accountNames()}${roleField('viewer')}<button type="submit">Добавить пользователя</button></form>
 </div></details>`,'user');
}
function tokenPanel(tokens, users=[]){
 const date=value=>value?esc(new Date(value*1000).toLocaleString('ru-RU')):'—';
 return accountCard('tokens','Токены API',`<p class="hint">Токен действует с правами владельца. При смене роли он отзывается. Сохраните новый токен: он показывается один раз.</p>
 <form class="account-form" data-account-action="token-create"><label class="field"><span>Название токена</span><input name="name" required maxlength="80" autocomplete="off"></label>
 <label class="field"><span>Действует до</span><input type="datetime-local" name="expires_at" required></label>
 <button type="submit" class="secondary">Создать токен</button></form>
 ${journalTable(['Название','Владелец','Создан','Действует до','Последнее использование','Состояние','Действия'],tokens.map(t=>{
  const owner=users.find(u=>u.id===t.user_id)||currentUser;
  const active=!t.revoked_at&&t.expires_at>Date.now()/1000;
  return [esc(t.name),esc(`${owner.last_name} ${owner.first_name}`),date(t.created_at),date(t.expires_at),date(t.last_used_at),t.revoked_at?'Отозван':active?'Действует':'Истёк',active?`<button type="button" class="secondary" data-account-task="token-revoke" data-token-id="${t.id}">Отозвать</button>`:'—'];
 }))}`,'file');
}
function showToken(value){
 $('#prompt-content').innerHTML=`<p class="hint">Сохраните токен. После закрытия окна получить его снова нельзя.</p><label class="field"><span>Токен API</span><input id="issued-token" readonly autocomplete="off"></label><div class="account-actions"><button type="button" id="copy-token">Копировать токен</button><button type="button" class="secondary" data-dialog-close>Закрыть</button></div><p class="account-message" role="status"></p>`;
 $('#issued-token').value=value;
 $('#copy-token').onclick=async()=>{
  const input=$('#issued-token');
  try{await navigator.clipboard.writeText(input.value);$('#prompt-content .account-message').textContent='Скопировано.';}
  catch(_){input.focus();input.select();$('#prompt-content .account-message').textContent='Скопируйте выделенное значение.';}
 };
 promptWindow.open({title:'Новый токен API',focus:$('#copy-token')});
}
function accountPage(){
 if(!accountData){
  loadAccount().catch(error=>notifyWorkspace(error.message));
  return title('Настройки','Личные данные, доступ и токены API.')+'<p class="hint" role="status">Загрузка…</p>';
 }
 const {model,tokens}=accountData;
 const user=currentUser;
 const keys=Object.keys(accountTabLabels).filter(key=>model||!['assistants','paths','users'].includes(key));
 if(!keys.includes(accountTab))accountTab='profile';
 return title('Настройки','Личные данные, рабочие пути, пользователи и токены API.')+`<div id="account-page">
 <p class="account-message" role="status"></p>${accountTabs(keys.map(key=>[key,accountTabLabels[key]]))}
 ${accountCard('profile','Личные данные',`<p class="hint">${roleNames[user.role]}</p><form class="account-form" data-account-action="profile">${accountNames(user)}<button type="submit" class="secondary">Сохранить имя</button></form>`,'user')}
 ${model?adminPanels(model):''}
 ${tokenPanel(tokens,model?.users)}
 ${accountCard('access','Вход и сеанс',`<div class="account-actions"><button type="button" class="secondary" data-account-task="self-rotate">Сменить код входа</button><button type="button" class="secondary" data-account-task="logout">Выйти из системы</button></div>`,'clock')}
 </div>`;
}

let accountBusy=false;
async function accountAction(run, message=$('#account-page .account-message')){
 if(accountBusy)return;
 accountBusy=true;
 if(message)message.textContent='';
 try{await run();}
 catch(error){
  if(message&&message.id!=='settings-message')message.textContent=error.message;
  else notifyWorkspace(error.message);
 }
 finally{accountBusy=false;}
}

async function loadAccount(){
 if(accountLoading)return accountLoading;
 accountLoading=(async()=>{
  try{
   const model=currentUser.role==='admin'?await api('/api/admin'):null;
   const tokens=await api(currentUser.role==='admin'?'/api/admin/tokens':'/api/account/tokens');
   accountData={model,tokens};
   if(workspaceView==='account')render();
  }finally{accountLoading=null;}
 })();
 return accountLoading;
}

async function updateAccount(){
 await loadAccount();
}

async function openAccount(){
 if(workspaceView!=='account')accountTab='profile';
 await loadAccount();
 navigate('account');
}

function suspendWorkspace(){
 if(sessionSuspended||!currentUser)return;
 sessionSuspended=true;keepSession('');
 document.querySelectorAll('[data-session-resume]').forEach(button=>button.hidden=false);
 $('#login-cancel').hidden=false;
 notice('Сеанс завершён. Ввод сохранён в открытой форме. Войдите снова для продолжения.');
}

function leaveWorkspace(){
 keepSession('');
 dirty=false;
 formDirty=false;
 location.replace(location.pathname);
}

function startAccount(){
 const form=$('#login-form');
 document.querySelectorAll('[data-session-resume]').forEach(button=>button.addEventListener('click',()=>loginWindow.open({focus:form.elements.code})));
 async function signIn(code){
  const message=form.querySelector('.account-message');
  const submit=form.querySelector('button');
  submit.disabled=true;
  message.textContent='';
  try{
   const result=await api('/api/login',{code});
   if(sessionSuspended&&currentUser){
    const same=currentUser.id===result.user.id&&currentUser.role===result.user.role&&currentUser.workspace_id===result.user.workspace_id;
    if(!same){
     if(!await confirmWorkspace('Пользователь, права или рабочая база изменились. Открыть новое рабочее пространство и удалить несохранённый ввод?','Открыть'))return;
     keepSession(result.session);dirty=false;formDirty=false;location.replace(location.pathname);return;
    }
    keepSession(result.session);sessionSuspended=false;document.querySelectorAll('[data-session-resume]').forEach(button=>button.hidden=true);$('#login-cancel').hidden=true;
    form.reset();loginWindow.close(true);notice('Сеанс восстановлен. Проверьте актуальность данных перед сохранением.');
    const focus=$('#editor-dialog').open?$('#editor-content textarea,#editor-content input:not(.smart-native)'):$('#account-open');focus?.focus({preventScroll:true});return;
   }
   keepSession(result.session);
   form.reset();
   loginWindow.close(true);
   openWorkspace(result.user);
  }catch(error){
   keepSession('');
   form.reset();
   message.textContent=error.message;
   loginWindow.open({focus:form.elements.code});
  }finally{submit.disabled=false;}
 }
 function openWorkspace(user){
  setProfile(user);
  document.body.dataset.auth='ready';
  startWorkspace();
 }
 form.addEventListener('submit',e=>{
  e.preventDefault();
  e.stopPropagation();
  const raw=form.elements.code.value.trim();
  signIn(raw.includes('/#')?raw.split('/#').pop():raw);
 });
 $('#session-logout').addEventListener('click',()=>accountAction(logoutWorkspace));
 $('#account-open').addEventListener('click',()=>accountAction(openAccount));
 const content=$('#content');
 content.addEventListener('submit',e=>{
  if(!e.target.closest('#account-page'))return;
  e.preventDefault();
  e.stopPropagation();
  const form=e.target;
  const operation=form.dataset.accountAction;
  const data=Object.fromEntries(new FormData(form));
  accountAction(async()=>{
   if(operation==='token-create'){
    const result=await api('/api/account/tokens/create',{name:data.name,expires_at:new Date(data.expires_at).getTime()/1000});
    showToken(result.token);
    await updateAccount();
   }else if(operation==='profile'){
    setProfile(await api('/api/account/profile',data));
    $('#account-page .account-message').textContent='Личные данные сохранены.';
   }else if(operation==='settings'){
    const message='Применить рабочие пути? При изменении остальные сеансы завершатся.'+
     (dirty||formDirty?' Несохранённый ввод будет потерян.':'');
    if(!await confirmWorkspace(message,'Применить'))return;
    const result=await api('/api/admin/settings',data);
    if(result.session){
     keepSession(result.session);
     dirty=false;
     formDirty=false;
     location.replace(location.pathname);
    }else $('#settings-message').textContent='Рабочие пути уже установлены.';
   }else if(operation==='role'){
    await api('/api/admin/role',{...data,id:Number(data.id)});
    await updateAccount();
    $('#account-page .account-message').textContent='Роль сохранена.';
   }else if(operation==='create'){
    const result=await api('/api/admin/create',data);
    showCode(result.code);
    await updateAccount();
   }
  },operation==='settings'?$('#settings-message'):undefined);
 });
 content.addEventListener('click',e=>{
  const button=e.target.closest('[data-account-task]');
  if(!button||!button.closest('#account-page'))return;
  accountAction(async()=>{
   const task=button.dataset.accountTask;
   const id=Number($('[data-account-action="role"]')?.elements.id.value);
   if(task==='assistants'){document.dispatchEvent(new Event('itd:assistant-admin'));}else if(task==='token-revoke'){
    if(!await confirmWorkspace('Отозвать токен? Запросы с ним перестанут работать.','Отозвать'))return;
    await api(currentUser.role==='admin'?'/api/admin/tokens/revoke':'/api/account/tokens/revoke',{id:Number(button.dataset.tokenId)});
    await updateAccount();
   }else if(task==='logout'){
    await logoutWorkspace();
   }else if(task==='delete'){
    if(!await confirmWorkspace('Удалить выбранного пользователя? Его сеансы завершатся.','Удалить'))return;
    await api('/api/admin/delete',{id});
    await updateAccount();
    $('#account-page .account-message').textContent='Пользователь удалён.';
   }else{
    if(!await confirmWorkspace('Сменить код входа? Прежний код и другие сеансы перестанут работать.','Сменить код'))return;
    const result=await (task==='self-rotate'?api('/api/account/rotate',{}):api('/api/admin/rotate',{id}));
    if(result.session)keepSession(result.session);
    showCode(result.code);
   }
  });
 });
 content.addEventListener('click',e=>{
   const tab=e.target.closest('[data-account-tab]');
   if(!tab||!tab.closest('#account-page'))return;
   accountTab=tab.dataset.accountTab;
   render();
  });
  content.addEventListener('change',e=>{
   const select=e.target;
   if(select.name!=='id'||!select.closest('[data-account-action="role"]'))return;
   const form=select.form;
   const target=accountData?.model?.users.find(u=>u.id===Number(select.value));
   $('#account-user-tools').hidden=!target;
   if(!target)return;
   form.elements.role.value=target.role;
   form.elements.role.dispatchEvent(new Event('smart-sync'));
   form.elements.role.closest('.field').hidden=target.id===currentUser.id;
   $('#account-save-role').hidden=target.id===currentUser.id;
   form.querySelector('[data-account-task="delete"]').hidden=target.id===currentUser.id;
  });
  window.addEventListener('hashchange',()=>{
  if(/^[A-Za-z0-9_-]{43}$/.test(location.hash.slice(1)))location.reload();
 });
 (async()=>{
  const fragment=location.hash.slice(1);
  if(/^[A-Za-z0-9_-]{43}$/.test(fragment)){
   history.replaceState(null,'',location.pathname+location.search);
   await signIn(fragment);
   return;
  }
  if(token){
   try{openWorkspace(await api('/api/account'));return;}
   catch(error){if(error.status===403)keepSession('');form.querySelector('.account-message').textContent=error.message;}
  }
  loginWindow.open({focus:form.elements.code});
 })();
}
