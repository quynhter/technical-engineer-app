'use strict';

const roleNames = {admin:'Администратор', editor:'Редактор', viewer:'Наблюдатель'};
let currentUser;
let sessionSuspended=false;
let viewerObserver;
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
const accountWindow = createWorkspaceDialog('account-dialog', {
 onClose:()=>document.querySelector('#account-content').replaceChildren()
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
 if(user.role==='viewer'&&!viewerObserver){
  const readOnly=()=>{
   const content=document.getElementById('editor-content');
   if(content.firstElementChild&&!content.querySelector('[data-read-only-note]')){const note=document.createElement('p');note.dataset.readOnlyNote='';note.className='hint';note.textContent='Просмотр · изменение сведений недоступно для вашей роли.';content.prepend(note);}

   document.querySelectorAll('#editor-dialog [data-action="cancel-entry"]').forEach(button=>{if(button.textContent!=='Закрыть')button.textContent='Закрыть';});
   document.querySelectorAll('#content :is(input,textarea,select),#editor-content :is(input,textarea,select)').forEach(el=>{
    if(el.closest('.astryx-data-view'))return;
    const nativeSelect=el.closest('.select-island')?._nativeSelect;
    if(nativeSelect?.matches('#project-select,#resource-activity-select,[data-journal-project],[data-table-control]'))return;
    if(el.matches('#object-search,#project-select,#resource-activity-select,[data-filter],[data-check-search],[data-table-control]')||
       el.closest('.smart-select')?.querySelector('select')?.matches('#project-select,#resource-activity-select,[data-journal-project],[data-table-control]')||
       el.matches('[data-journal-project]'))return;
    if(el.matches('select,input[type=checkbox],input[type=radio],input[type=file],.smart-input'))el.disabled=true;
    else el.readOnly=true;
   });
  };
  viewerObserver=new MutationObserver(readOnly);
  for(const id of ['content','editor-content','editor-footer'])viewerObserver.observe(document.getElementById(id),{childList:true,subtree:true});
  readOnly();
 }
 const avatar=$('#account-open');
 const initials=[user.first_name,user.last_name].map(name=>Array.from(name)[0]).join('').toLocaleUpperCase('ru');
 avatar.textContent=initials;
 if(user.role==='admin'){
  avatar.insertAdjacentHTML('beforeend','<span class="account-gear" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M10 2h4l.7 3.1 2 .9 2.8-1.5 2 3.5-2.1 2.3v3.4l2.1 2.3-2 3.5-2.8-1.5-2 .9L14 22h-4l-.7-3.1-2-.9-2.8 1.5-2-3.5 2.1-2.3v-3.4L2.5 8l2-3.5L7.3 6l2-.9z"/><circle cx="12" cy="12" r="3"/></svg></span>');
 }
 avatar.setAttribute('aria-label',`Настройки профиля · ${user.first_name} ${user.last_name} · ${roleNames[user.role]}`);
 avatar.hidden=false;
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
function adminPanels(model){
 const {settings,users}=model;
 return `<section class="account-section"><h3>Рабочие пути</h3>
 <form data-account-action="settings">
 <label class="field"><span>Файл базы данных на сервере</span><input name="database_path" required value="${esc(settings.database_path)}"></label>
 <label class="field"><span>Папка ИТД на сервере</span><input name="itd_root" required value="${esc(settings.itd_root)}"></label>
 <p class="hint">Укажите полные пути к существующему файлу .db и отдельной папке ИТД для этой базы. Если папки ещё нет, приложение её создаст.</p>
 <button type="submit" class="secondary">Применить пути</button>
 <p id="settings-message" class="account-message" role="status" tabindex="-1"></p>
 </form></section>
 <section class="account-section"><h3>Пользователи</h3>
 <form data-account-action="role">
 <label class="field"><span>Пользователь</span><select name="id" required>
 <option value="">Выберите пользователя…</option>
 ${users.map(u=>option(u.id,`${u.last_name} ${u.first_name} · ${roleNames[u.role]}${u.id===currentUser.id?' (вы)':''}`)).join('')}
 </select></label>
 <div id="account-user-tools" hidden>${roleField('viewer')}
 <div class="account-actions"><button type="submit" class="secondary" id="account-save-role">Сохранить роль</button>
 <button type="button" class="secondary" data-account-task="rotate">Сменить код входа</button>
 <button type="button" class="secondary" data-account-task="delete">Удалить пользователя</button></div></div>
 </form>
 <details class="ux-disclosure"><summary>Добавить пользователя</summary><div class="disclosure-body">
 <form data-account-action="create">${accountNames()}${roleField('viewer')}<button type="submit">Добавить пользователя</button></form>
 </div></details></section>`;
}
function drawAccount(model=null){
 const user=currentUser;
 $('#account-content').innerHTML=`<p class="account-message" role="status"></p>
 <section class="account-section"><h3>Личные данные</h3><p class="hint">${roleNames[user.role]}</p>
 <form data-account-action="profile">${accountNames(user)}<button type="submit" class="secondary">Сохранить имя</button></form></section>
 ${model?adminPanels(model):''}
 <div class="account-actions"><button type="button" class="secondary" data-account-task="self-rotate">Сменить код входа</button>
 <button type="button" class="secondary" data-account-task="logout">Выйти из системы</button></div>`;
 $('#account-content').querySelectorAll('select').forEach(enhanceSelect);
 if(!model)return;
 const form=$('[data-account-action="role"]');
 form.elements.id.addEventListener('change',()=>{
  const target=model.users.find(u=>u.id===Number(form.elements.id.value));
  $('#account-user-tools').hidden=!target;
  if(!target)return;
  form.elements.role.value=target.role;
  form.elements.role.dispatchEvent(new Event('smart-sync'));
  form.elements.role.closest('.field').hidden=target.id===user.id;
  $('#account-save-role').hidden=target.id===user.id;
  form.querySelector('[data-account-task="delete"]').hidden=target.id===user.id;
 });
}

let accountBusy=false;
async function accountAction(run, message=$('#account-content .account-message')){
 if(accountBusy)return;
 accountBusy=true;
 if(message)message.textContent='';
 try{await run();}
 catch(error){
  if(message){
   if(message.id==='settings-message')notifyWorkspace(error.message);
   else message.textContent=error.message;
  }
 }
 finally{accountBusy=false;}
}

async function updateAccount(){
 drawAccount(currentUser.role==='admin'?await api('/api/admin'):null);
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
 $('#account-open').addEventListener('click',()=>accountAction(async()=>{
  await updateAccount();
  accountWindow.open({focus:$('#account-content input')});
 }));
 const content=$('#account-content');
 content.addEventListener('submit',e=>{
  e.preventDefault();
  e.stopPropagation();
  const form=e.target;
  const operation=form.dataset.accountAction;
  const data=Object.fromEntries(new FormData(form));
  accountAction(async()=>{
   if(operation==='profile'){
    setProfile(await api('/api/account/profile',data));
    content.querySelector('.account-message').textContent='Личные данные сохранены.';
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
    content.querySelector('.account-message').textContent='Роль сохранена.';
   }else if(operation==='create'){
    const result=await api('/api/admin/create',data);
    showCode(result.code);
    await updateAccount();
   }
  },operation==='settings'?$('#settings-message'):undefined);
 });
 content.addEventListener('click',e=>{
  const button=e.target.closest('[data-account-task]');
  if(!button)return;
  accountAction(async()=>{
   const task=button.dataset.accountTask;
   const id=Number($('[data-account-action="role"]')?.elements.id.value);
   if(task==='logout'){
    if((dirty||formDirty)&&!await confirmWorkspace('Выйти без сохранения изменений?','Выйти'))return;
    try{await api('/api/logout',{});}catch(error){if(error.status!==403)throw error;}
    leaveWorkspace();
   }else if(task==='delete'){
    if(!await confirmWorkspace('Удалить выбранного пользователя? Его сеансы завершатся.','Удалить'))return;
    await api('/api/admin/delete',{id});
    await updateAccount();
    content.querySelector('.account-message').textContent='Пользователь удалён.';
   }else{
    if(!await confirmWorkspace('Сменить код входа? Прежний код и другие сеансы перестанут работать.','Сменить код'))return;
    const result=await (task==='self-rotate'?api('/api/account/rotate',{}):api('/api/admin/rotate',{id}));
    if(result.session)keepSession(result.session);
    showCode(result.code);
   }
  });
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
