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
 moon: '<path d="M20.8 13.2A9 9 0 0 1 10.8 3a9 9 0 1 0 10 10.2Z"/>'
};
function icon(name) {
 return `<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${iconPaths[name] || iconPaths.plus}</svg>`;
}
function decorateSelects(){decorateDataTables();enhanceEditorActions();enhanceCheckLists();document.querySelectorAll('select').forEach(enhanceSelect);document.querySelectorAll('form').forEach(form=>form.noValidate=true);}
const appearanceKey = 'itd-appearance';
let appearance = {theme: 'light', accent: 'blue'};
try {
 const saved = JSON.parse(localStorage.getItem(appearanceKey) || '{}');
 if (['light','dark'].includes(saved.theme)) appearance.theme = saved.theme;
 if (['teal','blue','violet','amber','rose'].includes(saved.accent)) appearance.accent = saved.accent;
} catch (_) { /* Недоступное хранилище не мешает работе формы. */ }
function applyAppearance() {
 document.documentElement.dataset.theme = appearance.theme;
 document.documentElement.dataset.accent = appearance.accent;
 const dark = appearance.theme === 'dark';
 $('#theme-toggle').innerHTML = icon(dark ? 'sun' : 'moon') + (dark ? 'Светлая тема' : 'Тёмная тема');
 $('#theme-toggle').setAttribute('aria-label', dark ? 'Включить светлую тему' : 'Включить тёмную тему');
 document.querySelectorAll('.swatch').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.accent === appearance.accent)));
 try { localStorage.setItem(appearanceKey, JSON.stringify(appearance)); } catch (_) {}
 document.dispatchEvent(new Event('itd:appearance'));
}
applyAppearance();
$('#theme-toggle').addEventListener('click', () => {
 appearance.theme = appearance.theme === 'light' ? 'dark' : 'light';
 applyAppearance();
});
document.querySelectorAll('.swatch').forEach(b => b.addEventListener('click', () => {
 appearance.accent = b.dataset.accent;
 applyAppearance();
}));
let token=sessionStorage.getItem('itd-session')||'';
let meta, state={object:{},participants:[],projects:[],token:null}, step=0, tab=0, orgIndex=0, projectId=null, pdata=null, dirty=false, formDirty=false, busy=false, pending=[], editEntry=null;
let workspaceView='overview', selectedEntries=new Set();
const tableFilters=Object.fromEntries(['work','incoming','journal'].map(k=>[k,{search:'',unbound:false,group:false,from:'',to:''}]));
const steps=['Информация об объекте','Участники строительства','Рабочая документация','Исполнительная документация'];
const idViews=['documents','resources','schemes','ojr'];
let packagePanel='registry',resourcePanel='list';
const tabs=['Комплект ИД','Ресурсы','Схемы','Журналы'];
async function api(path,data){
 if(sessionSuspended&&data&&!['/api/login','/api/logout'].includes(path))throw Error('Сеанс завершён. Войдите снова; введённые данные остаются в открытой форме.');
 let res,value;
 try{
  res=await fetch(path,{method:data?'POST':'GET',headers:{'X-ITD-Token':token,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined,signal:AbortSignal.timeout(data?120000:30000)});
  value=await res.json();
 }catch(error){
  const reason=['TimeoutError','AbortError'].includes(error.name)?'Сервер не ответил вовремя.':'Не удалось получить ответ сервера.';
  throw Error(reason+(data?' Результат операции неизвестен. Проверьте данные перед повторной отправкой.':' Проверьте соединение и повторите загрузку.')+' Ввод остаётся в открытой форме.');
 }
 if(!res.ok){const error=Error(value.error||'Не удалось выполнить запрос');error.fields=value.fields;error.journalDates=value.journal_dates;error.status=res.status;if(res.status===403&&value.session_expired)suspendWorkspace();throw error;}
 return value;
}
function notice(text=''){ const target=$('#editor-dialog').open?$('#editor-notice'):$('#notice');target.textContent=text; }
function toast(text){$('#toast').textContent=text;$('#toast').style.display='block';setTimeout(()=>$('#toast').style.display='none',4000);}
async function reloadJournalWorkspace(){
 if(!dirty)state=await api('/api/workspace?object_id='+state.object.id);
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
 const buttons=[...document.querySelectorAll('button')].filter(b=>!b.closest('#account-dialog,#prompt-dialog,#login-dialog'));
 const disabled=buttons.map(b=>b.disabled);buttons.forEach(b=>b.disabled=true);
 try{await fn();}catch(e){if(e.fields)showWorkspaceErrors(e.fields);notice(e.message);($('#editor-dialog').open?$('#editor-notice'):$('#notice')).scrollIntoView({block:'nearest',behavior:'smooth'});}
 finally{busy=false;buttons.forEach((b,i)=>{if(b.isConnected)b.disabled=disabled[i];});syncPreviewActions();}
}
function get(path){return path.split('.').reduce((v,k)=>v?.[k],state);}
function put(path,value){const keys=path.split('.'),last=keys.pop();let obj=state;for(const k of keys)obj=obj[k];obj[last]=value;dirty=true;$('#save-status')&&( $('#save-status').textContent='Есть несохранённые изменения');}
function field(path,label,type='text',wide=false,extra=''){let v=get(path);return `<label class="field ${wide?'wide':''}"><span>${label}</span>${type==='textarea'?`<textarea data-path="${esc(path)}" ${extra}>${esc(v)}</textarea>`:`<input data-path="${esc(path)}" type="${type}" value="${esc(v)}" ${extra}>`}</label>`;}
function select(path,label,options,wide=false){const value=get(path);return `<label class="field ${wide?'wide':''}"><span>${label}</span><select data-path="${esc(path)}"><option value="">Выберите…</option>${Object.entries(options).map(([v,t])=>`<option value="${esc(v)}" ${v===value?'selected':''}>${esc(t)}</option>`).join('')}</select></label>`;}
function check(path,label){return `<label class="choice"><input type="checkbox" data-path="${esc(path)}" ${get(path)?'checked':''}>${esc(label)}</label>`;}
function title(name,sub){return `<div class="title-row"><div><h1>${name}</h1><p class="subtitle">${sub}</p></div></div>`;}
function card(heading,content,iconName='plus'){return `<section class="card"><h2 class="card-title"><span class="icon" aria-hidden="true">${icon(iconName)}</span>${heading}</h2>${content}</section>`;}
function option(v,t,selected){return `<option value="${esc(v)}" ${v==selected?'selected':''}>${esc(t)}</option>`;}
function navigate(view){closeAgentHelp();workspaceView=view;const url=new URL(location.href);url.searchParams.set('view',view);history.replaceState(null,'',url.pathname+url.search);const map={object:0,participants:1,rd:2,permits:4,documents:3,registry:3,schemes:3,work:3,incoming:3,journal:3,cable:3,facts:3,check:3,delivery:3,manage:5,resources:3,ojr:3};step=map[view]??0;if(view==='work')journalSection='3';if(view==='incoming')resourcePanel='incoming';else if(view==='facts')resourcePanel='facts';else if(view==='resources')resourcePanel='list';if(view==='check')packagePanel='check';else if(view==='delivery')packagePanel='delivery';else if(['documents','registry'].includes(view))packagePanel=view;const ti=idViews.indexOf(({work:'ojr',journal:'ojr',cable:'ojr',registry:'documents',facts:'resources',incoming:'resources',check:'documents',delivery:'documents'})[view]||view);if(ti>=0)tab=ti;editEntry=null;notice();render();window.scrollTo({top:0,behavior:'auto'});window.requestAnimationFrame?.(()=>{const target=document.querySelector(['check','delivery'].includes(view)?'#package-panel-title':'#content h1');if(target){target.setAttribute('tabindex','-1');target.focus({preventScroll:true});if(['check','delivery'].includes(view))target.scrollIntoView({block:'start',behavior:'auto'});}});refreshJournals();}
function render(){
 const nav=[['overview','Обзор','home'],['object','Объект','building'],['rd','Разделы','file'],['participants','Участники','user'],['permits','Разрешительная документация','clipboard'],['registry','Исполнительная документация','list']];
 if(window.ITDDesign)window.ITDDesign.renderNav(nav.map(([v,n,i])=>[v,n,icon(i)]),workspaceView,navigate);
 else $('#steps').innerHTML=nav.map(([v,n,i])=>`<button data-view="${v}" class="${workspaceView===v||(v==='registry'&&step===3)?'active':''}" ${workspaceView===v||(v==='registry'&&step===3)?'aria-current="page"':''}>${icon(i)}${n}</button>`).join('');
 $('#sidebar').innerHTML=step===1&&workspaceView==='participants'?orgSidebar():'';
 $('#sidebar').hidden=!(step===1&&workspaceView==='participants');
 $('main').classList.toggle('no-sidebar',$('#sidebar').hidden);
 $('#content').innerHTML=workspaceView==='objects'?objectsPage():workspaceView==='overview'?overviewPage():[objectPage,participantsPage,rdPage,idPage,permitsPage,manualPage][step]();
 $('#actions').innerHTML=!dirty&&!['object','participants','rd','permits'].includes(workspaceView)?'':`<span id="save-status" class="status-text ${dirty?'unsaved':''}">${dirty?'Есть несохранённые изменения':state.object.id?'Сведения сохранены':'Новый объект · пока не сохранён'}</span><div class="footer-right">${state.object.id?'<button class="secondary" data-action="import">Импорт</button><button class="secondary" data-action="export">Экспорт</button>':''}<button data-action="save">Сохранить сведения</button></div>`;
 decorateSelects();
}
function objectsPage(){return title('Объекты','Все объекты и разделы в вашей локальной базе.','Рабочее пространство')+`<div class="toolbar"><input id="object-search" aria-label="Поиск объектов" placeholder="Найти объект по названию…"><button data-action="new-object">${icon('plus')}Новый объект</button></div><div class="object-cards">${meta.objects.map(o=>`<button class="object-tile" data-open-object="${o.id}" data-object-search="${esc(o.name.toLowerCase())}"><span class="tile-icon">${icon('building')}</span><strong>${esc(o.name)}</strong><span class="small">Разделы РД: ${meta.projects.filter(p=>p.object_id===o.id).length}</span><span class="tile-link">Открыть объект ${icon('right')}</span></button>`).join('')||'<div class="empty">Объектов пока нет.</div>'}</div><p id="object-empty" class="empty" hidden>Объекты по этому запросу не найдены.</p>`;}
function overviewPage(){
 let html=title(state.object.name?esc(state.object.name):'Ваше рабочее пространство','Ведение ИТД: исходные данные, работы, документы и сдача.');
 if(!state.object.id)return html+card('Начните с объекта',`<p>Выберите существующий объект вверху или создайте карточку нового. Затем добавьте раздел РД и выберите комплект форм.</p><p class="hint">Можно начать с РД выбранного раздела или договора для уточнения участников. Весь комплект исходных документов сразу не нужен.</p><button data-action="new-object">Создать объект</button>`,'building');
 html+=`<div class="section-toolbar">${projectSelector()}</div>`;
 if(!pdata)return `<div class="content-stack">${html}${card(state.projects.some(p=>p.id)?'Продолжите работу с разделом':'Добавьте первый раздел РД',`<p>${state.projects.some(p=>p.id)?'Выберите рабочий раздел выше. Здесь появятся действия по выбранному разделу.':'Укажите название и шифр из РД, затем выберите согласованный комплект форм.'}</p><button class="secondary" data-view="rd">Открыть разделы РД</button>`)}</div>`;
 html+=card('Ежедневная работа',`<div class="quick-actions"><button data-editor="work">${icon('plus')}Записать работу в ОЖР</button><button class="secondary" data-view="journal">${icon('check')}Открыть журнал входного контроля</button><button class="secondary" data-view="resources">${icon('list')}Открыть спецификацию</button><button class="secondary" data-view="ojr">${icon('clipboard')}Открыть общий журнал работ</button></div><p class="hint">Работы и ресурсы относятся к выбранному разделу. ОЖР объединяет разделы объекта.</p>`,'plus');
 return `<div class="content-stack">${html}</div>`;
}
function permitsPage(){return title('Разрешительная документация','Разрешение на строительство и заключение экспертизы.')+permitFields();}
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
function objectPage(){return title('Информация об объекте','Основные реквизиты для подготовки исполнительной документации.','Карточка объекта')+card('Общие сведения',`<div class="grid">${select('object.construction_type','Тип строительства',{'Строительство':'Строительство','Реконструкция':'Реконструкция','Капитальный ремонт':'Капитальный ремонт','Прочее':'Прочее'})}${field('object.gsn_case','Номер дела ГСН')}${field('object.name','Полное наименование объекта <span class="required">*</span>','textarea',true)}${field('object.display_name','Рабочее название (только для интерфейса)','text',true)}${field('object.city','Город','text',true)}${field('object.address','Адрес объекта','textarea',true)}</div><p class="hint">Сохраните полную формулировку из РД или согласованное наименование. Адрес хранится отдельно и не сокращает название.</p>`,'home')+card('Сроки работ по объекту',`<div class="grid">${field('object.work_start','Дата начала работ','date')}${field('object.work_end','Дата окончания работ','date')}</div><p class="hint">Даты всего объекта. Даты СМР/ПНР раздела и даты конкретных актов задаются отдельно.</p>`,'clock');}
function permitFields(){return card('Разрешение на строительство',`<div class="grid">${field('object.permit_num','Номер')}${field('object.permit_date','Дата выдачи','date')}${field('object.permit_authority','Орган, выдавший разрешение','text',true)}</div>`,'list')+card('Заключение экспертизы проектной документации',`<div class="grid">${field('object.expertise_num','Номер')}${field('object.expertise_date','Дата выдачи','date')}${field('object.expertise_authority','Орган, выдавший заключение','text',true)}</div>`,'check');}
function orgSidebar(){return `<div class="org-list">${state.participants.map((o,i)=>`<button data-org="${i}" class="${i===orgIndex?'selected':''}"><small>${esc(o.roles.map(r=>meta.roles[r]||r).join(', '))}</small>${esc(o.full_name||'Новая организация')}<p class="hint">Представителей: ${(o.representatives||[]).length}</p></button>`).join('')}</div><button data-action="add-org" class="secondary">${icon('plus')}Добавить организацию</button>`;}
function roleOptions(){let result={...meta.roles};if(state.object.developer_functions!=='technical_customer')delete result.customer;if(!state.object.control_external)delete result.customer_control;if(!state.object.author_supervision)delete result.author_supervision;if(!state.participants.some(o=>o.roles.includes('developer')))result={developer:meta.roles.developer};return result;}
function roleChecks(path,values,options){return `<div class="choices">${Object.entries({...options,...Object.fromEntries(values.filter(r=>!options[r]).map(r=>[r,r]))}).map(([r,label])=>`<label class="choice"><input type="checkbox" data-array="${esc(path)}" value="${esc(r)}" ${values.includes(r)?'checked':''}>${esc(label)}</label>`).join('')}</div>`;}
function participantsPage(){const o=state.participants[orgIndex];let html=title('Участники строительства','Организации и уполномоченные представители вашего объекта.',`${state.participants.length} организаций`);if(!o)return html+card('Добавьте первого участника',`<div class="empty">Начните с застройщика.<br>Затем укажите схему взаимодействия и остальных участников.</div><button data-action="add-org">${icon('plus')}Добавить застройщика</button>`,'building');
 const p=`participants.${orgIndex}`;html+=card(o.id?'Организация № '+o.id:'Новая организация',`${!o.id?'<button class="ghost danger" data-action="remove-org">Убрать несохранённую организацию</button>':''}<h3>Типы участника</h3>${roleChecks(p+'.roles',o.roles,roleOptions())}<div class="grid">${field(p+'.full_name','Полное наименование <span class="required">*</span>','textarea',true)}${field(p+'.short_name','Краткое наименование для документов','text',true)}${field(p+'.inn','ИНН','text',false,'inputmode="numeric"')}${field(p+'.ogrn','ОГРН','text',false,'inputmode="numeric"')}${field(p+'.postal_code','Индекс')}${field(p+'.phone','Телефон','tel')}${field(p+'.address','Адрес','textarea',true)}${field(p+'.email','Электронная почта','email',true)}${field(p+'.sro_info','Наименование СРО','text',true)}${field(p+'.sro_ogrn','ОГРН СРО')}${field(p+'.sro_inn','ИНН СРО')}${field(p+'.sro_certificate_num','Номер свидетельства СРО')}${field(p+'.sro_certificate_date','Дата свидетельства СРО','date')}</div>${o.roles.includes('developer')?developerPanel():''}<details class="rep"><summary>Назначения организации в документах</summary><p class="hint">Выберите роль только при наличии основания. Эти назначения общие для всех разделов объекта.</p>${roleChecks(p+'.document_roles',o.document_roles||[],meta.document_roles)}</details>`,'building');
 html+=card('Уполномоченные представители',`${(o.representatives||[]).map((r,j)=>repPanel(p,j,r)).join('')||'<p class="small">Представители ещё не добавлены.</p>'}<button class="secondary" data-action="add-rep">${icon('plus')}Добавить представителя</button>`,'user');return html;}
function developerPanel(){return `<div class="callout"><h3>Как организована работа застройщика?</h3><p>Укажите, кто выполняет функции по организации строительства и заключению договоров. Выбор фиксирует сообщённую вами схему взаимодействия.</p><div class="choices">${[['self','Сам застройщик'],['technical_customer','Передаёт функции техническому заказчику']].map(([v,t])=>`<label class="choice"><input type="radio" name="functions" data-path="object.developer_functions" value="${v}" ${state.object.developer_functions===v?'checked':''}>${t}</label>`).join('')}</div>${state.object.developer_functions?`<h3>Строительный контроль осуществляет</h3><div class="choices">${check('object.control_self',state.object.developer_functions==='self'?'Сам застройщик':'Сам технический заказчик')}${check('object.control_external',state.object.developer_functions==='self'?'Строительная организация':'Сторонняя организация')}</div><p class="hint">Можно отметить оба варианта. Сторона контроля и полномочия представителей назначаются отдельно по договорным основаниям.</p>`:''}${check('object.author_supervision','Предусмотрен авторский надзор')}</div>`;}
function repPanel(p,j,r){p+=`.representatives.${j}`;return `<details class="rep" open><summary>${esc(r.fio||[r.last_name,r.first_name,r.middle_name].filter(Boolean).join(' ')||'Новый представитель')}</summary>${!r.id?`<button class="ghost danger" data-remove-rep="${j}">Убрать несохранённого представителя</button>`:''}<div class="grid">${field(p+'.position','Должность <span class="required">*</span>')}${field(p+'.email','E-mail','email')}${field(p+'.last_name','Фамилия')}${field(p+'.first_name','Имя')}${field(p+'.middle_name','Отчество')}${field(p+'.nrs_id','Номер в НРС')}${field(p+'.fio','Полное ФИО (при необходимости)','text',true)}${select(p+'.authority_type','Распорядительный документ',{'Приказ':'Приказ','Распоряжение':'Распоряжение','Доверенность':'Доверенность','Указания':'Указания','Постановления и решения':'Постановления и решения'})}${field(p+'.authority_num','Номер документа')}${field(p+'.authority_date','Дата документа','date')}<label class="field"><span>Архивный приказ</span><select data-path="${p}.order_attachment_id"><option value="">Не выбран</option>${(pdata?.attachments||[]).filter(a=>a.doc_type==='order').map(a=>option(a.id,a.title,r.order_attachment_id)).join('')}</select></label>${select(p+'.status','Статус',{'Действует':'Действует','Отозван':'Отозван'})}</div><h3 class="rep">Роли представителя в документах</h3>${roleChecks(p+'.document_roles',r.document_roles||[],meta.document_roles)}<p class="hint">Укажите роль по распорядительному документу. Одна подпись в договоре не подтверждает полномочия на подписание актов.</p></details>`;}
function projectsPanel(){return card('Разделы рабочей документации',state.projects.map((p,i)=>`<div class="rep"><div class="split"><h3>${esc(p.name||'Новый раздел')}</h3>${!p.id?`<button class="ghost danger" data-remove-project="${i}">Убрать</button>`:''}${p.id?`<button class="ghost" data-project="${p.id}">${p.id===projectId?icon('check')+'Выбран':'Выбрать'}</button>`:''}</div><div class="grid">${field(`projects.${i}.section_code`,'Обозначение раздела','text',false,p.id?'readonly':'')}${field(`projects.${i}.code`,'Шифр РД')}${field(`projects.${i}.name`,'Полное название раздела','text',true)}${field(`projects.${i}.city`,'Город')}${field(`projects.${i}.gip`,'Главный инженер проекта (ГИП)')}${field(`projects.${i}.inv_num`,'Инвентарный номер проекта')}${field(`projects.${i}.smr_start`,'Начало СМР раздела','date')}${field(`projects.${i}.smr_end`,'Окончание СМР раздела','date')}${field(`projects.${i}.pnr_start`,'Начало ПНР раздела','date')}${field(`projects.${i}.pnr_end`,'Окончание ПНР раздела','date')}${select(`projects.${i}.form_set`,'Комплект форм',{'СП 77.13330.2016':'СП 77.13330.2016','И 1.13-07':'И 1.13-07','Иной согласованный комплект':'Иной согласованный комплект'})}</div></div>`).join('')+`<button class="secondary add-project" data-action="add-project">${icon('plus')}Добавить раздел</button><p class="hint">Шифр и название перепишите из РД. Комплект форм выбирается отдельно; дополнительные акты Минстроя подключаются по составу работ.</p>`,'file');}
function projectSelector(){return `<label class="field"><span>Рабочий раздел</span><select id="project-select"><option value="">Выберите раздел…</option>${state.projects.filter(p=>p.id).map(p=>option(p.id,p.code+' «'+p.name+'»',projectId)).join('')}</select></label>`;}
function rdPage(){return title('Рабочая документация','Добавьте разделы и файлы рабочей документации.','Источники')+projectsPanel()+card('Файлы рабочей документации',projectSelector()+`<p class="hint">РД сохраняется в папку раздела «Рабочая документация». Сначала сохраните карточку и выберите раздел.</p>${uploadZone('file-input','Добавить файлы РД',{multiple:true})}<ul class="file-list">${pending.map((f,i)=>`<li><span>${esc(f.name)} <small>ожидает сохранения</small></span><button class="ghost" data-remove-file="${i}">Убрать</button></li>`).join('')}${(pdata?.attachments||[]).filter(a=>a.doc_type==='rd').map(a=>`<li><span><button class="record-name" data-original="${a.id}">${esc(a.original_name)}</button><br><small>${a.doc_date?esc(displayTableDate(a.doc_date)):'Дата документа не указана'}</small></span><span class="pill" tabindex="0" title="Оригинал сохранён в локальном архиве и связан с разделом. Это не означает проверку документа или включение в ZIP выпусков.">Оригинал сохранён</span></li>`).join('')}</ul>`,'upload')+(pdata?sourceFilesPage():'');}
function idPage(){
 const descriptions=['Реестр и основные документы.','Спецификация, входной контроль и монтаж.','Исполнительные схемы.','Журналы производства и контроля работ.'];
 let html=title('Исполнительная документация',descriptions[tab])+`<div class="section-toolbar">${projectSelector()}</div><nav class="tabs" aria-label="Разделы ИД">${tabs.map((t,i)=>`<button data-tab="${i}" class="${i===tab?'active':''}" ${i===tab?'aria-current="page"':''}>${t}</button>`).join('')}</nav>`;
 if(!pdata)html+=card(state.object.id?'Выберите рабочий раздел':'Сначала выберите объект',`<p>${!state.object.id?'Выберите объект в верхней части страницы.':state.projects.some(p=>p.id)?'Выберите рабочий раздел выше.':'Добавьте раздел РД, чтобы сохранять работы и документы.'}</p>${state.object.id&&!state.projects.some(p=>p.id)?'<button data-view="rd">Добавить раздел РД</button>':''}`);
 else html+=`<div class="content-stack">${[packagePage,resourcePage,schemesPage,journalsPage][tab]()}</div>`;
 return `<div class="content-stack id-workspace">${html}</div>`;
}
function actName(act){return pdata.forms.find(f=>f.code===act.act_type)?.name||act.act_type;}
function helpTip(label,text){return `<details class="help-tip"><summary aria-label="${esc(label)}" title="${esc(label)}"><span aria-hidden="true">?</span></summary><p>${esc(text)}</p></details>`;}
function packagePage(){
 const acts=pdata.acts.filter(a=>a.is_active);
 const nav=`<nav class="panel-nav" aria-label="Подготовка комплекта">${[['registry','Реестр ИД'],['documents','Основные документы']].map(([key,label])=>`<button class="${packagePanel===key?'active':'secondary'}" data-package-panel="${key}" ${packagePanel===key?'aria-current="page"':''}>${label}</button>`).join('')}</nav>`;
 const workflowLinks='<div class="toolbar"><button class="secondary" data-view="check">Проверка</button><button class="secondary" data-view="delivery">Сдача</button></div>';
 if(packagePanel==='registry')return nav+registryPage();
 if(packagePanel==='check')return nav+workflowLinks+`<div class="content-stack">${checkPage()}</div>`;
 if(packagePanel==='delivery')return nav+workflowLinks+`<div class="content-stack">${deliveryPage()}</div>`;
 return nav+card('Основные документы',`<div class="toolbar" id="package-panel-title"><button data-editor="act">${icon('plus')}Создать</button><button class="secondary" data-upload-act>${icon('upload')}Загрузить</button></div>`+
 journalTable(['Номер','Название','Дата подписания','Статус'],acts.map(a=>[esc(a.act_num),`<button class="record-name" ${currentUser?.role==='viewer'?'data-preview':'data-version-act'}="${a.id}">${esc(actName(a))}</button>`,esc(displayTableDate(a.date_signed)||'Не указана'),esc(pdata.act_statuses.find(s=>s.act_id===a.id)?.state==='signed'?'Подписан':'В подготовке')]),{ids:acts.map(a=>a.id),entity:'acts'}),'clipboard');
}
const sourceTypeNames={contract:'Договор',order:'Распорядительный документ',quality:'Документ, подтверждающий качество',scheme:'Схема',rd:'Рабочая документация',other:'Другой файл'};
function sourceType(a){return a.file_kind||(['certificate','passport'].includes(a.doc_type)?'quality':a.doc_type);}
function sourceTypeOptions(value='contract'){return Object.entries(sourceTypeNames).map(([k,v])=>option(k,v,value)).join('');}
function sourceFilesPage(){
 const files=pdata.source_files||pdata.attachments.filter(a=>pdata.project_attachment_ids.includes(a.id));
 return `<details class="ux-disclosure card"><summary>Исходные файлы <span class="pill">${files.length}</span></summary><div class="disclosure-body"><label class="field source-type-field"><span>Что загружаете</span><select id="source-type">${sourceTypeOptions()}</select></label>${uploadZone('source-file','Добавить файлы',{multiple:true,extra:'<button type="button" class="secondary" data-files-check>Проверить файлы</button>'})}${journalTable(['Наименование','Тип файла'],files.map(a=>[`<button class="record-name" data-file-card="${a.id}">${esc(a.original_name||a.title)}</button>`,esc(sourceTypeNames[sourceType(a)]||'Другой файл')]))}</div></details>`;
}
function openSourceFileCard(id){
 const file=pdata.source_files?.find(a=>a.id===id)||pdata.attachments.find(a=>a.id===id);if(!file)return;
 openEditor('manual');editorWindow.setTitle('Исходный файл');
 $('#editor-content').innerHTML=`<h3>${esc(file.original_name||file.title)}</h3><p>${esc(sourceTypeNames[sourceType(file)]||'Другой файл')}</p><div class="toolbar"><button type="button" data-original="${file.id}">Скачать файл</button><button type="button" class="secondary danger" data-file-delete="${file.id}">Удалить</button></div>`;
}
let filePlan=null;
async function previewFiles(purpose,attachmentId=null){
 if(dirty||formDirty)throw Error('Сначала сохраните изменения.');
 if(!projectId)throw Error('Выберите раздел');
 filePlan=await api('/api/files/plan',{project_id:projectId,purpose,attachment_id:attachmentId});
 const labels={repair:'Восстановить архивную копию',add:'Добавить',remove:'Удалить из БД и с диска',detach:'Убрать из раздела; сохранить в других разделах',restore:'Вернуть копию из архива'};
 openEditor('manual');editorWindow.setTitle(purpose==='delete'?'Удаление файла':'Проверка файлов');
 $('#editor-content').innerHTML=`<p>${filePlan.plan.actions.length?'Проверьте изменения перед применением.':'Изменений не требуется.'}</p>${filePlan.plan.actions.length?journalTable(['Файл','Изменение'],filePlan.plan.actions.map(a=>[`<span class="cell-text">${esc(a.name)}</span>${a.path?`<small>${esc(a.path)}</small>`:''}`,`${esc(labels[a.action])}${a.unlink_resources?.length?`<p>Будут сняты связи с ресурсами этого раздела: ${a.unlink_resources.length}.</p>`:''}${a.action==='add'&&!a.existing&&a.type!=='rd'?`<label class="field"><span>Тип файла</span><select data-plan-type="${esc(a.path)}">${sourceTypeOptions(a.type)}</select></label>`:''}${a.paths?.length?`<details class="technical-detail"><summary>Файлы на диске: ${a.paths.length}</summary>${a.paths.map(p=>`<p>${esc(p)}</p>`).join('')}</details>`:''}`])):''}${filePlan.plan.blocked.length?'<h3>Сохранены без изменений</h3><ul>'+filePlan.plan.blocked.map(a=>`<li><strong>${esc(a.name)}</strong><p>${esc(a.reason)}</p></li>`).join('')+'</ul>':''}<div class="toolbar rep">${filePlan.plan.actions.length?`<button type="button" data-files-apply>${purpose==='delete'?'Удалить':'Применить изменения'}</button>`:''}<button type="button" class="secondary" data-dialog-close>Закрыть</button></div>`;
 decorateSelects();
}

function workPage(){return card('Сведения о выполнении работ',entryTable('work'),'list');}
function incomingPage(){return card('Входной контроль',incomingJournalTable(),'list');}
function schemesPage(){
 return card('Схемы','<div class="toolbar"><button data-manual="scheme-add">Добавить схему</button></div>'+journalTable(
  ['Номер','Наименование','Референс','Комментарий'],pdata.schemes.map(s=>[
   esc(s.num),`<button class="cell-open" data-scheme-card="${s.id}">${esc(s.name)}</button>`,esc(s.ref_code),esc(s.note)]),{ids:pdata.schemes.map(s=>s.id),entity:'schemes'}),'file');
}
function registryPage(){
 const rows=pdata.registry||[];
 return card('Реестр ИД','<div class="toolbar"><button data-registry-export>Экспорт DOCX</button></div>'+journalTable(
  ['№ п/п','Наименование документа','Номер и дата документа','Организация, составившая документ','Кол-во листов','Номера страниц'],rows.map(r=>{
   const target={act:currentUser?.role==='viewer'?'data-preview':'data-version-act',scheme:'data-scheme-card',attachment:'data-file-card',release:'data-download'}[r.entity];
   const name=r.entity==='journal'?`<button class="cell-open" data-view="${esc(r.id==='incoming'?'journal':r.id)}">${esc(r.name)}</button>`:target?`<button class="cell-open" ${target}="${r.id}">${esc(r.name)}</button>`:esc(r.name);
   return [r.no,name,esc([r.number,displayTableDate(r.date)].filter(Boolean).join(' · ')),esc(r.organization),esc(r.sheets_count),esc(r.pages)];
  }),{ids:rows.map(r=>`${r.entity}:${r.id}`)}),'list');
}
function journalsPage(){
 const active=['journal','cable'].includes(workspaceView)?workspaceView:'ojr';
 const nav=`<nav class="panel-nav" aria-label="Виды журналов">${[['ojr','ОЖР'],['journal','ЖВК'],['cable','ЖПК']].map(([key,label])=>`<button class="${active===key?'active':'secondary'}" data-view="${key}" ${active===key?'aria-current="page"':''}>${label}</button>`).join('')}</nav>`;
 if(active==='journal')return nav+incomingPage();
 if(active==='cable'){
  const entries=pdata.workspace_entries.filter(e=>e.kind==='work'&&e.work_type==='cable');
  return nav+card('ЖПК','<p class="subtitle">Журнал прокладки кабеля</p>'+
   '<div class="toolbar"><button data-editor="cable">Записать прокладку кабеля</button></div>'+
   journalTable(['Дата','Работа','Место'],entries.map(e=>[journalValue(e.entry_date),
    `<button class="cell-open" data-edit-entry="${e.id}">${esc(e.title)}</button>`,esc(e.details)])),'list');
 }
 return nav+card('ОЖР','<p class="subtitle">Общий журнал работ</p>','list')+ojrPage();
}
const statusNames={pending:'Ожидает подтверждения',confirmed:'Подтверждено',void:'Отозвано',matches:'Соответствует',mismatch:'Несоответствие',uncertain:'Не удалось подтвердить',sent:'Передано',remarks:'Получены замечания',corrected:'Исправлено',accepted:'Принято',open:'Открыто',resolved:'Устранено',required:'Требуется',not_applicable:'Не применяется',prepared:'Файл ещё не создан',draft:'Черновик',final:'Окончательная версия',file_present:'Оригинал в архиве',registered:'Зарегистрировано',available:'Есть документ',missing:'Документ отсутствует',inactive:'Документ неактивен',unselected:'Версия не выбрана',binding_mismatch:'Связь не соответствует требованию'};
const findingNames={work_supply_invalid:'Поставка использованного ресурса отклонена, изменилась или не покрывает расход',entry_source_changed:'Рабочая запись изменилась после включения в акт',entry_resource_missing:'Ресурс связанной работы исключён из акта',act_material_invalid:'Поставка акта не принята или её ресурс исключён',supply_overallocated:'Превышено количество поставки',participant_outside_period:'Дата акта вне периода участия организации',facts_pending:'Есть неподтверждённый факт',fact_quantity_unknown:'Количество факта неизвестно',fact_total_differs:'Сумма приростов отличается от итогового факта',fact_dates_incomplete:'Не все даты факта известны',fact_unit_changed:'Изменилась единица ресурса',qty_fact_unknown:'Итоговый факт неизвестен',fact_exceeds_project:'Факт превышает проект',quality_document_missing:'Нет связанного документа качества',quality_unreviewed:'Документ качества не проверен',quality_stale:'Проверка качества устарела',quality_mismatch:'Несоответствие документа качества',quality_uncertain:'Применимость документа качества не подтверждена',act_fact_not_confirmed:'Факт акта не подтверждён',act_fact_resource_missing:'Ресурс факта отсутствует в акте',act_signed_before_work_end:'Акт подписан раньше окончания работ',act_facts_missing:'Не все ресурсы акта связаны с фактом',act_required_fields_missing:'Не заполнены обязательные поля акта',release_context_changed:'Сведения изменились после создания файла',act_context_error:'Ошибка контекста акта',requirements_not_configured:'Не указан перечень документов к сдаче',requirement_missing:'Не подготовлен документ из перечня',requirement_inactive:'Связанный документ неактивен',requirement_unselected:'Выпуск документа из перечня не выбран',requirement_binding_mismatch:'Связь документа из перечня не соответствует требованию',specification_pending:'Есть вопросы по спецификации',open_remark:'Открыто замечание при сдаче'};
function resourceSelect(){return `<label class="field wide"><span>Ресурс *</span><select name="resource_id" required><option value="">Выберите…</option>${pdata.resources.map(r=>option(r.id,'№ '+r.id+' · '+r.name+' · '+r.unit,'')).join('')}</select></label>`;}
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
function factLabel(id){
 const f=pdata.workflow.fact_records.find(f=>f.id===Number(id));
 return f?[resourceLabel(f.resource_id),f.work_description,f.location].filter(Boolean).join(' · '):'Запись монтажа недоступна (ID '+id+')';
}
function findingResource(f){
 return f.resource_id||(f.resource_ids||[])[0]||pdata.workflow.fact_records.find(item=>item.id===Number(f.fact_id||(f.fact_ids||[])[0]))?.resource_id;
}
function findingSubjectLink(f){
 const rid=findingResource(f);
 if(rid&&pdata.resources.some(r=>r.id===Number(rid)))return `<button class="record-name" data-resource-card="${rid}">${esc(resourceLabel(rid))}</button>`;
 const act=pdata.acts.find(a=>a.id===Number(f.act_id));
 if(act)return `<button class="record-name" data-preview="${act.id}">${esc(act.act_num+' «'+actName(act)+'»')}</button>`;
 return '';
}
function findingDetails(f){
 const labels={resource_id:'Материал / оборудование',resource_ids:'Материалы / оборудование',fact_id:'Монтаж',fact_ids:'Монтаж',act_id:'Акт',release_id:'Файл',attachment_id:'Исходный файл',review_id:'Контроль качества',requirement_id:'Документ комплекта',delivery_id:'Передача',remark_id:'Замечание',pending_ids:'Вопросы по спецификации',fields:'Поля',message:'Описание',confirmed_total:'Подтверждено записями',qty_fact:'Итог ведомости',unit:'Единица',confirmed_ids:'Подтверждённые записи',unknown_quantity_ids:'Монтаж с неизвестным количеством',note:'Пояснение'};
 const find=(rows,id)=>rows?.find(r=>r.id===Number(id));
 const display=(key,id)=>{
  if(['resource_id','resource_ids'].includes(key))return resourceLabel(id);
  if(['fact_id','fact_ids','confirmed_ids','unknown_quantity_ids'].includes(key))return factLabel(id);
  if(key==='act_id'){const a=find(pdata.acts,id);return a?a.act_num+' «'+actName(a)+'»':'Акт недоступен';}
  if(key==='attachment_id')return find(pdata.attachments,id)?.title||'Исходный файл недоступен';
  if(key==='release_id')return find(pdata.releases,id)?.title||'Версия файла недоступна';
  if(key==='requirement_id')return find(pdata.workflow.matrix.requirements,id)?.title||'Документ комплекта недоступен';
  if(key==='delivery_id')return find(pdata.workflow.deliveries,id)?.recipient||'Передача недоступна';
  if(key==='remark_id')return find(pdata.workflow.remarks,id)?.description||'Замечание недоступно';
  if(key==='review_id'){const q=find(pdata.quality_reviews,id);return q?[resourceLabel(q.resource_id),q.checked_date,q.checked_by].filter(Boolean).join(' · '):'Проверка недоступна';}
  if(key==='supply_id'){const s=find(pdata.manual?.supplies,id);return s?[resourceLabel(s.resource_id),s.batch_num,s.supply_date].filter(Boolean).join(' · '):'Поставка недоступна';}
  if(key==='entry_id')return find(pdata.workspace_entries,id)?.title||'Запись работ недоступна';
  return typeof id==='object'?JSON.stringify(id):id??'Неизвестно';
 };
 return Object.entries(f).filter(([k])=>k!=='code').map(([k,v])=>(labels[k]||({supply_id:'Поставка',entry_id:'Работа'})[k]||k)+': '+(Array.isArray(v)?v.map(id=>display(k,id)).join('; '):display(k,v))).join(' · ');
}
function findingDestination(code){
 if(code==='requirements_not_configured'||code.startsWith('requirement_'))return ['requirements','Состав комплекта'];
 if(code==='open_remark')return ['delivery','Замечания'];
 if(code.startsWith('quality_')||code==='work_supply_invalid'||code==='supply_overallocated')return ['incoming','Входной контроль'];
 if(code.startsWith('fact_')||code.startsWith('facts_')||code==='qty_fact_unknown'||code==='specification_pending')return ['resources','Ресурсы и монтаж'];
 return ['documents','Документы'];
}
function checkPage(){
 const findings=pdata.check.findings,requirements=pdata.workflow.matrix.requirements;
 const groups=Object.groupBy(findings,f=>findingDestination(f.code)[0]);
 return card('Что исправить',`<h3 class="sr" id="package-panel-title">Проверка документов</h3><p class="hint">${findings.length?'Вопросов: '+findings.length+'. Откройте группу и проверьте сведения.':'Расхождений во внесённых данных не найдено.'} Проверка базы не подтверждает приёмку.</p><div class="disclosure-group">${Object.entries(groups).map(([view,items])=>`<details class="check-group" ${Object.keys(groups).length===1?'open':''}><summary>${esc(findingDestination(items[0].code)[1])}<span class="pill">${items.length}</span></summary><ul class="file-list">${items.map(f=>`<li><div><strong>${esc(findingNames[f.code]||'Проверьте сведения')}</strong>${findingSubjectLink(f)}<details class="ux-row-source"><summary>Подробности</summary><p>${esc(findingDetails(f))}</p></details></div></li>`).join('')}</ul>${view==='requirements'?'<button class="secondary" data-requirements-open>Открыть состав комплекта</button>':`<button class="secondary" data-view="${view}">Перейти</button>`}</details>`).join('')}</div>`,'check')+
 `<details class="ux-disclosure card" id="requirements-panel"><summary>Состав комплекта <span class="pill">${requirements.length}</span></summary><p class="hint">Документы по вашим работам и основаниям.</p><button class="secondary" data-manual="requirement-add">Добавить документ</button><ul class="file-list">${requirements.map(r=>`<li><div><strong>${esc(r.title)}</strong><small>${esc(statusNames[r.state]||r.state)} · ${esc(statusNames[r.availability]||r.availability)}</small><details class="ux-row-source"><summary>Работы и основание</summary><p>${esc(r.work_scope)}<br>${esc(r.basis)}${r.reason?'<br>'+esc(r.reason):''}</p></details></div><button class="ghost" data-manual="requirement-set" data-manual-record="${r.id}">Изменить</button>${recordDeleteButton('package_requirements',r.id)}</li>`).join('')||'<li class="empty">Укажите документы, согласованные для этого раздела.</li>'}</ul></details>`;
}
function deliveryPage(){
 const w=pdata.workflow,open=w.remarks.filter(r=>r.status==='open');
 return card('Передача документов',`<h3 class="sr" id="package-panel-title">Сдача документов</h3><div class="section-heading"><p class="hint">Запишите уже состоявшуюся передачу. Файлы отсюда не отправляются.</p><button data-manual="delivery-add">Учесть передачу</button></div><ul class="file-list">${w.deliveries.map(d=>`<li><div><strong>${esc(d.recipient)}</strong><small>${esc(statusNames[d.status]||d.status)} · версия № ${d.release_id}</small><details class="ux-row-source"><summary>История</summary>${pdata.delivery_events.filter(e=>e.delivery_id===d.id).map(e=>'<p>'+esc(displayTableDate(e.event_date))+' · '+esc(statusNames[e.status]||e.status)+'<br>'+esc(e.source)+' · '+esc(e.note)+'</p>').join('')}</details></div><div class="table-actions"><button class="secondary" data-manual="delivery-set" data-manual-record="${d.id}">Изменить статус</button><button class="ghost" data-manual="remark-add" data-manual-record="${d.id}">Добавить замечание</button>${recordDeleteButton('deliveries',d.id)}</div></li>`).join('')||'<li class="empty">Передач пока нет.</li>'}</ul>`,'file')+
 card('Замечания'+(open.length?' (открыто: '+open.length+')':''),`<ul class="file-list">${w.remarks.map(r=>`<li><div><strong>${esc(r.description)}</strong><small>${esc(statusNames[r.status]||r.status)} · передача № ${r.delivery_id}</small></div>${r.status==='open'?`<button class="secondary" data-manual="remark-resolve" data-manual-record="${r.id}">Закрыть с основанием</button>`:''}${recordDeleteButton('delivery_remarks',r.id)}</li>`).join('')||'<li class="empty">Замечаний нет.</li>'}</ul>`,'clipboard');
}
function filteredEntries(kind){const f=tableFilters[kind];const entries=kind==='incoming'?pdata.journals.incoming.map(e=>({...e,entry_date:e.entry_date||'',search_fields:[JSON.stringify(e.work_fields),e.resource?.name,e.supply?.supplier,e.supply?.batch_num,e.quality_review?.note].join(' ')})):pdata.workspace_entries;return entries.filter(e=>e.kind===kind&&(!f.unbound||!e.act_id)&&(!f.from||(e.entry_date&&e.entry_date>=f.from))&&(!f.to||(e.entry_date&&e.entry_date<=f.to))&&[e.title,e.details,e.responsible,e.conditions,e.unit,e.quantity,e.search_fields].join(' ').toLowerCase().includes(f.search.toLowerCase())).sort((a,b)=>(b.entry_date||'').localeCompare(a.entry_date||'')||b.id-a.id);}
function entryBody(kind){if(kind==='incoming')return incomingJournalBody();const list=filteredEntries(kind),f=tableFilters[kind],columns=kind==='work'?7:5;let date;return list.map(e=>{let heading='';if(f.group&&date!==e.entry_date){date=e.entry_date;heading=`<tr class="date-group"><td colspan="${columns}">${esc(displayTableDate(date)||'Дата не указана')}</td></tr>`;}return heading+`<tr>${kind==='work'?`<td class="row-check">${!e.act_id?`<input type="checkbox" data-select-entry="${e.id}" aria-label="Выбрать запись № ${e.id}" ${selectedEntries.has(e.id)?'checked':''}>`:''}</td>`:''}<td>${esc(displayTableDate(e.entry_date)||'Не указана')}</td><td class="description"><button type="button" class="cell-open" data-edit-entry="${e.id}"><strong>${esc(e.title)}</strong></button>${e.details?`<p class="hint">${esc(e.details)}</p>`:''}</td>${kind==='work'?`<td>${esc((pdata.work_materials||[]).filter(m=>m.entry_id===e.id).map(m=>(pdata.resources.find(r=>r.id===m.resource_id)?.name||'Ресурс')+' · '+formatTableNumber(m.quantity)+' '+m.unit).join('; '))}</td>`:''}<td>${esc(e.conditions||'')}${e.quantity!=null?'<br>'+esc(formatTableNumber(e.quantity))+' '+esc(e.unit||''):''}</td><td>${esc(e.responsible_display||e.responsible||'Не указан')}</td><td class="work-links"><div class="record-link"><span class="record-link-label">Акт</span>${e.act_id?`<button class="link-button" data-preview="${e.act_id}">${esc((pdata.acts||[]).find(a=>a.id===e.act_id)?.act_num||e.act_id)}</button>`:'<span class="small">Не сформирован</span>'}</div><div class="record-link"><span class="record-link-label">Источник</span>${e.attachment_id?`<span class="cell-text" title="${esc(pdata.attachments.find(a=>a.id===e.attachment_id)?.title||'Архивный документ')}">${esc(pdata.attachments.find(a=>a.id===e.attachment_id)?.title||'Архивный документ')}</span>`:'<span class="small">Не указан</span>'}</div></td></tr>`;}).join('')||`<tr><td colspan="${columns}" class="empty">${pdata.workspace_entries.some(e=>e.kind===kind)?'По заданным условиям записей не найдено. <button type="button" class="secondary" data-reset-filters="'+kind+'">Сбросить фильтры</button>':'Записей пока нет.'}</td></tr>`;}

let entrySearchTimer;
function scheduleEntrySearch(kind){clearTimeout(entrySearchTimer);entrySearchTimer=setTimeout(()=>{if($('#entry-rows')&&$('#entry-search,[data-kind="'+kind+'"]'))updateEntryTable(kind);},180);}
function updateEntryTable(kind){$('#entry-rows').innerHTML=entryBody(kind);$('#table-count').dataset.total=String((kind==='incoming'?pdata.journals.incoming:pdata.workspace_entries.filter(e=>e.kind===kind)).length);$('#table-count').textContent='Показано '+filteredEntries(kind).length+' из '+(kind==='incoming'?pdata.journals.incoming:pdata.workspace_entries.filter(e=>e.kind===kind)).length;const bulk=$('#bulk-act');if(bulk)bulk.hidden=!selectedEntries.size;const count=$('#selected-count');if(count)count.textContent=selectedEntries.size?' · выбрано '+selectedEntries.size:'';}
function entryTable(kind){const f=tableFilters[kind];return `<div class="toolbar"><div class="table-actions"><button data-editor="${kind}">${icon('plus')}Добавить запись</button>${kind==='work'?'<button class="secondary" data-editor="act" id="bulk-act" '+(selectedEntries.size?'':'hidden')+'>Сформировать акт<span id="selected-count">'+(selectedEntries.size?' · выбрано '+selectedEntries.size:'')+'</span></button>':''}<button class="secondary" data-action="export-entries">Экспорт</button></div><input id="entry-search" data-filter="search" data-kind="${kind}" aria-label="Поиск записей" placeholder="Поиск по работам, месту, ответственному…" value="${esc(f.search)}"></div><div class="table-filters">${kind==='work'?`<label class="choice"><input type="checkbox" data-filter="unbound" data-kind="${kind}" ${f.unbound?'checked':''}>Только работы без актов</label>`:''}<label class="choice"><input type="checkbox" data-filter="group" data-kind="${kind}" ${f.group?'checked':''}>Группировать по дате</label><fieldset class="table-date-range"><legend>Дата</legend><label class="field"><span>С</span><input type="date" aria-label="Дата с" data-filter="from" data-kind="${kind}" value="${esc(f.from)}"></label><label class="field"><span>По</span><input type="date" aria-label="Дата по" data-filter="to" data-kind="${kind}" value="${esc(f.to)}"></label></fieldset><button type="button" class="secondary" data-reset-filters="${kind}">Сбросить фильтр</button></div><div class="table-count" id="table-count" hidden data-total="${pdata.workspace_entries.filter(e=>e.kind===kind).length}">Показано ${filteredEntries(kind).length} из ${pdata.workspace_entries.filter(e=>e.kind===kind).length}</div><div class="table-scroll"><table><thead><tr>${kind==='work'?'<th class="row-check"><span class="sr">Выбор</span></th>':''}<th>Дата</th><th>Описание</th>${kind==='work'?'<th>Использованные ресурсы</th>':''}<th>Условия / количество</th><th>Ответственный</th><th>Акт и источник</th></tr></thead><tbody id="entry-rows">${entryBody(kind)}</tbody></table></div>`;}
function input(name,label,value='',type='text',wide=false){return `<label class="field ${wide?'wide':''}"><span>${label}</span><input name="${esc(name)}" value="${esc(value)}" type="${type}" ${type==='number'?'step="any" min="0"':''} ${name==='title'||label.includes('*')?'required':''}></label>`;}
function entryEditor(kind){const e=editEntry?.kind===kind?editEntry:{};return kind==='work'?workEntryEditor(e):specializedEntryEditor(kind,e);}
function actForms(){return pdata.available_forms||pdata.forms;}
function actFormOptions(){return ['Комплект раздела','Дополнительные акты Минстроя','Ранее подключённые формы','Другие комплекты форм'].map(group=>{const forms=actForms().filter(f=>(f.choice_group||'Ранее подключённые формы')===group);return forms.length?`<optgroup label="${group}">${forms.map(f=>option(f.code,`${f.code} «${f.name}»`,'')).join('')}</optgroup>`:'';}).join('');}
function actEditor(){return card('Создать документ',`<form id="act-form"><div class="grid"><label class="field wide"><span>Форма документа</span><select name="act_type" id="act-type" required><option value="">Выберите форму…</option>${actFormOptions()}</select></label>${input('date_signed','Дата подписания','','date')}</div>${actPeopleSelects()}<p class="hint">Доступны акты, ведомости, протоколы, паспорта и другие готовые формы всех комплектов. Формы выбранного раздела показаны первыми. Подключится только выбранная форма; применимость определяйте по составу работ и проекту.</p><div id="act-fields"></div><h3 class="rep">Работы, включаемые в документ</h3><div class="check-list">${pdata.workspace_entries.filter(e=>e.kind==='work'&&!e.act_id).map(e=>`<label class="choice"><input type="checkbox" name="entry_ids" value="${e.id}" ${selectedEntries.has(e.id)?'checked':''}>${esc(e.entry_date)} · ${esc(e.title)}</label>`).join('')||'<span class="small">Можно создать документ без записей журнала.</span>'}</div><section id="act-resources" hidden><h3>Ресурсы</h3><div class="check-list">${pdata.resources.map(r=>`<label class="choice"><input type="checkbox" name="resource_ids" value="${r.id}" ${linkedActResourceIds([...selectedEntries]).has(r.id)?'checked':''}>${esc(r.name)}</label>`).join('')||'<span class="small">Ресурсы ещё не добавлены.</span>'}</div><h3>Подтверждённые факты монтажа</h3><div class="check-list">${pdata.workflow.fact_records.filter(f=>f.status==='confirmed').map(f=>`<label class="choice"><input type="checkbox" name="fact_ids" value="${f.id}">Факт № ${f.id} · Ресурс № ${f.resource_id} · ${esc(f.location)} · ${esc(f.quantity??'Количество неизвестно')}</label>`).join('')||'<span class="small">Подтверждённые факты ещё не внесены.</span>'}</div><p class="hint">Ресурсы выбранных фактов и записей работ должны входить в состав документа.</p></section><section id="act-schemes" hidden><h3>Исполнительные схемы</h3><div class="check-list">${pdata.schemes.map(s=>`<label class="choice"><input type="checkbox" name="scheme_ids" value="${s.id}">${esc(s.num)} · ${esc(s.name)}</label>`).join('')||'<span class="small">Схемы ещё не зарегистрированы.</span>'}</div></section><button type="submit">Создать документ</button> <button type="button" class="secondary" data-action="cancel-entry">Отменить ввод</button><p class="hint">Номер назначается автоматически. Выбранные записи связываются с документом; содержание полей нужно проверить. Проверка сведений и создание DOCX доступны в «Комплекте ИД».</p></form>`,'plus');}
async function refreshMeta(){meta=await api('/api/bootstrap');$('#object-select').innerHTML='<option value="">Выберите объект или создайте новый</option>'+meta.objects.map(o=>option(o.id,o.display_name||o.name,state.object.id)).join('');}
async function loadProject(pid,activate=false){
 const nextId=pid?Number(pid):null,restoreTables=tableLoading();
 try{
  const next=nextId?await api('/api/project?project_id='+nextId):null;
  if(activate&&nextId&&currentUser?.role!=='viewer')await api('/api/activate',{project_id:nextId});
  closeAgentHelp();selectedEntries.clear();projectId=nextId;pdata=next;editEntry=null;
 }catch(error){const select=$('#project-select');if(select){select.value=projectId||'';select.dispatchEvent(new Event('smart-sync'));}throw error;}
 finally{restoreTables();}
}
async function loadObject(id){
 try{
  const next=await api('/api/workspace'+(id?'?object_id='+id:''));
  const current=next.projects.find(p=>p.id===meta.active_project_id);
  await loadProject(current?.id||null);
  closeAgentHelp();state=next;orgIndex=0;pending=[];dirty=false;formDirty=false;
  $('#object-select').value=state.object.id||'';render();
 }catch(error){$('#object-select').value=state.object.id||'';$('#object-select').dispatchEvent(new Event('smart-sync'));throw error;}
}
async function save(){if(!validateInputs($('#content')))return;state=await api('/api/save',state);dirty=pending.length>0;await refreshMeta();if(projectId&&!state.projects.some(p=>p.id===projectId))await loadProject(null);if(pending.length&&!projectId)throw Error('Карточка сохранена. Выберите раздел для загрузки ожидающих файлов.');if(pending.length)await uploadPending();dirty=false;if(projectId)await loadProject(projectId);render();toast('Сведения сохранены в базе');}
function addFiles(files){for(const f of files){if(f.size>32*1024*1024){notice('Файл '+f.name+' больше 32 МБ. Добавьте его через file-add.');continue;}if(!pending.some(x=>x.name===f.name&&x.size===f.size))pending.push(f);}dirty=true;render();}
function readUploadContent(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(Error('Не удалось прочитать файл'));reader.readAsDataURL(file);});}
async function uploadFile(file,type){if(!file)throw Error('Выберите файл');if(file.size>32*1024*1024)throw Error('Файл больше 32 МБ: '+file.name);const content=await readUploadContent(file);return api('/api/upload',{project_id:projectId,name:file.name,content,doc_type:type});}
async function uploadPending(){while(pending.length){await uploadFile(pending[0],'rd');pending.shift();}}
async function exportHandoff(name){if(dirty)throw Error('Сначала сохраните карточку.');state=await api('/api/workspace?object_id='+state.object.id);const projects=await Promise.all(state.projects.filter(p=>p.id).map(p=>api('/api/project?project_id='+p.id)));downloadJson({...state,project_data:projects},name);}
function downloadJson(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function downloadRelease(id){const r=await fetch('/api/download?project_id='+projectId+'&release_id='+id,{headers:{'X-ITD-Token':token}});if(!r.ok)throw Error((await r.json()).error);const blob=await r.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;const rel=pdata.releases.find(x=>x.id===id);a.download=rel?.path.split(/[\\/]/).pop()||'Документ';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
document.addEventListener('input',e=>{const el=e.target;if(el.closest('#act-form')&&el.name==='date_signed')updateActAutomaticValues();if(el.closest('#entry-form, #incoming-day-form, #act-form, #fact-form, #manual-form, #review-form'))formDirty=true;if(el.dataset.path){put(el.dataset.path,el.type==='checkbox'?Number(el.checked):el.dataset.path.endsWith('order_attachment_id')?(el.value?Number(el.value):null):el.value||null);}if(el.dataset.filter==='search'){tableFilters[el.dataset.kind].search=el.value;scheduleEntrySearch(el.dataset.kind);}if(el.id==='object-search'){const tiles=[...document.querySelectorAll('[data-object-search]')];tiles.forEach(tile=>tile.hidden=!tile.dataset.objectSearch.includes(el.value.toLowerCase()));$('#object-empty').hidden=tiles.length===0||tiles.some(tile=>!tile.hidden);}});
document.addEventListener('change',e=>{const el=e.target;if(el.dataset.filter){tableFilters[el.dataset.kind][el.dataset.filter]=el.type==='checkbox'?el.checked:el.value;updateEntryTable(el.dataset.kind);}if(el.dataset.selectEntry){const id=Number(el.dataset.selectEntry);if(el.checked)selectedEntries.add(id);else selectedEntries.delete(id);updateEntryTable('work');}if(el.closest('#entry-form, #incoming-day-form, #act-form, #fact-form, #manual-form, #review-form'))formDirty=true;if(el.dataset.array){let old=get(el.dataset.array)||[];put(el.dataset.array,el.checked?[...old,el.value]:old.filter(v=>v!==el.value));render();}if(['object.developer_functions','object.control_self','object.control_external','object.author_supervision'].includes(el.dataset.path)){render();}if(el.id==='object-select')action(async()=>{if((dirty||formDirty)&&!await confirmWorkspace('Есть несохранённые изменения. Перейти к другому объекту?')){el.value=state.object.id||'';return;}await loadObject(el.value);navigate(state.object.id?'overview':'object');});if(el.id==='project-select')action(async()=>{if(formDirty){el.value=projectId||'';throw Error('Сначала сохраните запись или отмените ввод в форме ниже.');}if(pending.length&&projectId&&Number(el.value)!==projectId)throw Error('Сначала сохраните ожидающие файлы в выбранном разделе или уберите их из списка.');await loadProject(el.value,true);render();});if(el.id==='file-input')addFiles(el.files);if(el.id==='source-file')action(async()=>{if(dirty||formDirty)throw Error('Сначала сохраните изменения.');if(!projectId)throw Error('Выберите раздел');const type=$('#source-type').value;try{for(const file of el.files){if(file.size>32*1024*1024)throw Error('Файл больше 32 МБ: '+file.name);await uploadFile(file,type);}}finally{await loadProject(projectId);render();}toast('Файлы сохранены в папке раздела');});if(el.id==='act-type')renderActFields(el.value);if(el.matches('#act-form [name=resource_ids]'))el.dataset.manualChoice='1';if(el.closest('#act-form')&&['entry_ids','fact_ids'].includes(el.name))syncLinkedActResources();});
document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b||b.closest('#account-dialog,#prompt-dialog,#login-dialog'))return;
 if(b.hasAttribute('data-open-knowledge')||b.hasAttribute('data-dialog-close')||b.closest('#knowledge-dialog'))return;
 if(b.id==='account-open'||b.id==='theme-toggle'||b.classList.contains('swatch'))return;
 if(formDirty&&!b.closest('form')&&!b.form&&b.dataset.action!=='close-editor'){notice('Сначала сохраните запись или отмените ввод в форме ниже.');return;}
 if(b.dataset.step!==undefined){step=Number(b.dataset.step);editEntry=null;notice();render();return;}
 if(b.dataset.tab!==undefined){navigate(Number(b.dataset.tab)===0?'registry':idViews[Number(b.dataset.tab)]);return;}
 if(b.dataset.packagePanel){navigate(({registry:'registry',documents:'documents',check:'check',delivery:'delivery'})[b.dataset.packagePanel]);return;}
 if(b.hasAttribute('data-requirements-open')){const panel=$('#requirements-panel');panel.open=true;panel.scrollIntoView({block:'start'});panel.querySelector('summary').focus();return;}
 if(b.dataset.org!==undefined){orgIndex=Number(b.dataset.org);render();return;}
 if(b.dataset.removeRep!==undefined){state.participants[orgIndex].representatives.splice(Number(b.dataset.removeRep),1);dirty=true;render();return;}
 if(b.dataset.removeProject!==undefined){state.projects.splice(Number(b.dataset.removeProject),1);dirty=true;render();return;}
 if(b.dataset.removeFile!==undefined){pending.splice(Number(b.dataset.removeFile),1);render();return;}
 if(b.dataset.project){action(async()=>{await loadProject(b.dataset.project,true);render();});return;}
 if(b.dataset.schemeCard){if(formDirty)return;openManual('scheme-edit',b.dataset.schemeCard);return;}
 if(b.hasAttribute('data-registry-export')){action(async()=>{const r=await api('/api/registry/export',{project_id:projectId});await loadProject(projectId);render();await downloadRelease(r.release_id);});return;}
 if(b.dataset.download){action(()=>downloadRelease(Number(b.dataset.download)));return;}
 if(b.dataset.generate){action(async()=>{const r=await api('/api/generate',{project_id:projectId,act_id:Number(b.dataset.generate)});await loadProject(projectId);render();toast('Создан черновик DOCX, версия № '+r.release_id);});return;}
 if(b.dataset.editEntry||b.dataset.copyEntry){const entry={...pdata.workspace_entries.find(x=>x.id===Number(b.dataset.editEntry||b.dataset.copyEntry))};if(b.dataset.copyEntry){if(formDirty&&!await confirmWorkspace('Оставить изменения без сохранения и создать копию?'))return;delete entry.id;delete entry.revision;entry.act_id=null;entry.title='Копия: '+entry.title;}if(b.dataset.copyEntry&&$('#editor-dialog').open){editEntry=entry;formDirty=false;$('#editor-content').innerHTML=entryEditor(entry.kind);editorWindow.setTitle('Копия работы');decorateSelects();}else openEditor(entry.kind,entry);return;}
 if(b.id==='new-object'||b.dataset.action==='new-object'){action(async()=>{if((dirty||formDirty)&&!await confirmWorkspace('Оставить несохранённые изменения и открыть новый объект?'))return;await loadObject(null);$('#object-select').value='';navigate('object');});return;}
 if(b.dataset.view){navigate(b.dataset.view);return;}
 if(b.dataset.editor){if(b.dataset.editor==='cable')openEditor('work',{kind:'work',work_type:'cable'});else openEditor(b.dataset.editor);return;}
 if(b.dataset.openObject){action(async()=>{if((dirty||formDirty)&&!await confirmWorkspace('Оставить несохранённые изменения?'))return;await loadObject(b.dataset.openObject);navigate('overview');});return;}
 const a=b.dataset.action;
 if(a==='objects'){navigate('objects');return;}
 if(a==='close-editor'){closeEditor();return;}
 if(a==='remove-org'){state.participants.splice(orgIndex,1);orgIndex=Math.max(0,orgIndex-1);dirty=true;render();}
 if(a==='add-org'){state.participants.push({full_name:'',roles:[state.participants.some(o=>o.roles.includes('developer'))?'builder':'developer'],document_roles:[],representatives:[]});orgIndex=state.participants.length-1;dirty=true;render();}
 if(a==='add-rep'){state.participants[orgIndex].representatives.push({status:'Действует',document_roles:[]});dirty=true;render();}
 if(a==='add-project'){state.projects.push({section_code:'',code:'',name:'',form_set:null});dirty=true;render();}
 if(a==='back'){step=Math.max(0,step-1);render();}
 if(a==='next'){step=Math.min(3,step+1);render();window.scrollTo({top:0,behavior:'smooth'});}
 if(a==='save'||a==='finish')action(async()=>{await save();if(a==='finish'){await exportHandoff('Сведения ИТД — объект '+state.object.id+'.json');toast('Сохранено. JSON со сведениями подготовлен для агента.');}});
 if(a==='export')action(()=>exportConfiguration());
 if(a==='import')chooseConfiguration();
 if(a==='export-entries')downloadJson(filteredEntries(['work','incoming','journal'].includes(workspaceView)?workspaceView:'work'),'Записи журналов.json');
 if(a==='statement')action(async()=>{const r=await api('/api/statement',{project_id:projectId});await loadProject(projectId);render();toast('Ведомость создана, версия № '+r.release_id);});
 if(a==='cancel-entry')closeEditor();
});

document.addEventListener('submit',e=>{e.preventDefault();const form=e.target;if(form.closest('#account-dialog,#prompt-dialog,#login-dialog')||currentUser?.role==='viewer'||!validateInputs(form))return;action(async()=>{if(form.getAttribute('id')==='incoming-day-form'){await submitIncomingDay(form);return;}const fd=new FormData(form);if(form.id==='uploaded-act-form'){await saveUploadedAct(form);return;}if(form.id==='document-version-form'){await saveDocumentVersion();return;}if(form.getAttribute('id')==='resource-card-form'){await submitResourceCard(form);return;}if(form.getAttribute('id')==='resource-import-form'){await submitResourceImport(form);return;}if(['special-journal-form','ojr-title-form','act-status-form'].includes(form.getAttribute('id'))){await submitArchitectureForm(form);return;}if(form.getAttribute('id')==='manual-form'){await submitManual(form);return;}if(form.getAttribute('id')==='review-form'){await api('/api/review',{project_id:projectId,act_id:Number(form.dataset.act),note:fd.get('note'),confirmed:fd.has('confirmed')});formDirty=false;await previewAct(Number(form.dataset.act));toast('Подтверждение проверки сохранено');return;}if(form.getAttribute('id')==='entry-form'){const entry={...editEntry,...Object.fromEntries(fd),kind:form.dataset.kind};entry.work_fields={...(typeof editEntry?.work_fields==='string'?JSON.parse(editEntry.work_fields):editEntry?.work_fields||{}),...Object.fromEntries(Object.entries(entry).filter(([k])=>k.startsWith('work_')&&k!=='work_type'&&k!=='work_fields').map(([k,v])=>[k.slice(5),v||null]))};for(const k of Object.keys(entry))if(k.startsWith('work_')&&!['work_type','work_fields'].includes(k))delete entry[k];for(const k of ['supply_id','quality_review_id','org_id','person_id','entry_id'])if(k in entry.work_fields)entry.work_fields[k]=entry.work_fields[k]?Number(entry.work_fields[k]):null;entry.quantity=entry.quantity==null||entry.quantity===''?null:Number(entry.quantity);if(entry.kind==='work'){entry.materials=workMaterialsDraft;entry.responsible_id=Number(entry.responsible_id)||null;}for(const k of ['resource_id','attachment_id'])entry[k]=entry[k]?Number(entry[k]):null;if(!await saveDatedJournal('/api/entry',{project_id:projectId,entry},'entry'))return;toast('Запись сохранена');editEntry=null;}else if(form.getAttribute('id')==='act-form'){const fields=collectActFields(form,actForms().find(f=>f.code===fd.get('act_type')));const r=await api('/api/act',{project_id:projectId,act_type:fd.get('act_type'),date_signed:fd.get('date_signed')||null,signatories:selectedActPeople(form),organizations:selectedActOrganizations(form),fields,entry_ids:fd.getAll('entry_ids').map(Number),resource_ids:actLinkIds(form,fd,'act-resources','resource_ids'),scheme_ids:actLinkIds(form,fd,'act-schemes','scheme_ids'),fact_ids:actLinkIds(form,fd,'act-resources','fact_ids'),resource_removals:actResourceRemovals(form,fd),work_only:form.querySelector('#act-resources')?.hidden===true});toast('Документ создан');}else if(form.getAttribute('id')==='fact-form'){const fact=Object.fromEntries(fd);fact.resource_id=Number(fact.resource_id);fact.work_entry_id=Number(fact.work_entry_id)||null;fact.quantity=fact.quantity===''?null:Number(fact.quantity);fact.source_key=form.dataset.sourceKey;await api('/api/work-fact',{project_id:projectId,fact});toast('Факт сохранён без изменения итогового количества');}closeEditor(true);if(form.dataset.kind||form.getAttribute('id')==='act-form')await reloadJournalWorkspace();await loadProject(projectId);render();});});

window.addEventListener('beforeunload',e=>{if(dirty||formDirty){e.preventDefault();e.returnValue='';}});
async function startWorkspace(){window.ITDDesign?.setLoading(true);checkDatabaseStatus();setInterval(checkDatabaseStatus,15000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkDatabaseStatus();});
try{await refreshMeta();const active=meta.projects.find(p=>p.id===meta.active_project_id);await loadObject(active?.object_id||null);const view=new URLSearchParams(location.search).get('view');navigate(['objects','overview','object','participants','rd','permits','documents','registry','schemes','work','incoming','journal','cable','facts','check','delivery','manage','resources','ojr'].includes(view)?view:state.object.id?'overview':(meta.objects.length||currentUser?.role==='viewer')?'objects':'object');}catch(e){if(e.fields)showWorkspaceErrors(e.fields);notice(e.message);$('#content').textContent='Не удалось открыть базу. Проверьте подключение к серверу.';}finally{window.ITDDesign?.setLoading(false);}}
startAccount();

document.addEventListener('click',e=>{const b=e.target.closest('[data-reset-filters]');if(!b)return;const kind=b.dataset.resetFilters;tableFilters[kind]={search:'',unbound:false,group:false,from:'',to:''};render();});

document.addEventListener('click',e=>{
 const card=e.target.closest('[data-file-card]');if(card)openSourceFileCard(Number(card.dataset.fileCard));
 const remove=e.target.closest('[data-file-delete]');
 if(remove)action(()=>previewFiles('delete',Number(remove.dataset.fileDelete)));
 if(e.target.closest('[data-files-check]'))action(()=>previewFiles('check'));
 if(e.target.closest('[data-files-apply]'))action(async()=>{
  const types={};document.querySelectorAll('[data-plan-type]').forEach(el=>types[el.dataset.planType]=el.value);
  const result=await api('/api/files/apply',{...filePlan,types});
  closeEditor(true);filePlan=null;await loadProject(projectId);render();toast(result.cleanup_pending?'Записи обновлены. Очистка удалённых копий продолжится при следующей проверке.':'Файлы обновлены');
 });
});

document.addEventListener('change',handleActParticipantChange);
