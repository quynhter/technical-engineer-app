'use strict';

(() => {
 const dialog = document.getElementById('write-preview-dialog');
 const title = document.getElementById('write-preview-title');
 const content = document.getElementById('write-preview-content');
 const footer = document.getElementById('write-preview-footer');
 const endpoint = '/api/v1/write-previews';
 const sourceLabels = {assistant: 'Ассистент', mcp: 'MCP'};
 const actions = {insert: 'Добавление', update: 'Изменение', delete: 'Удаление'};
 const labels = {position: 'Позиция', name: 'Наименование', unit: 'Ед. изм.',
  quantity: 'Количество', reference: 'Документ или норма', category: 'Категория'};
 const time = new Intl.DateTimeFormat('ru-RU', {dateStyle:'short', timeStyle:'short'});
 const pendingFields = new Map();
 let context, view, request = 0, busy = false, offset = 0;
 const modal = createWorkspaceDialog('write-preview-dialog', {
  beforeClose: () => !busy,
  onClose: () => {
   request++;
   const target = context?.opener;
   const fromSection = Boolean(target?.hasAttribute('data-open-write-previews'));
   context = null;
   view = null;
   pendingFields.clear();
   content.replaceChildren();
   requestAnimationFrame(() => {
    const opener = target?.isConnected ? target : fromSection
     ? document.querySelector('[data-open-write-previews]') : null;
    opener?.focus();
   });
  }
 });

 function format(value){
  if(value == null)return '<span class="hint">Пусто</span>';
  if(typeof value === 'object')return '<pre>'+esc(JSON.stringify(value,null,2))+'</pre>';
  if(typeof value === 'number')return esc(formatTableNumber(value));
  return esc(value === true ? 'Да' : value === false ? 'Нет' : value);
 }

 function detail(change, index){
  const summary = actions[change.action]+' · '+change.label+' · '+(change.caption || change.id);
  return '<details class="ux-disclosure" data-write-change="'+index+'"><summary>'+esc(summary)+'</summary>'
   +'<div data-write-fields></div></details>';
 }

 function renderFields(fields, change){
  const compare = change.action === 'update';
  fields.innerHTML = (compare ? '<div class="write-preview-field-head" aria-hidden="true">'
     +'<span>Поле</span><span>Было</span><span>Будет</span></div>' : '')
   +'<dl class="write-preview-fields'+(compare ? ' write-preview-compare' : '')+'">'
   +change.fields.map(field => '<div class="write-preview-field"><dt>'+esc(field.label)+'</dt>'
    +(change.action === 'insert' ? '' : '<dd><span class="write-preview-value-label">Было</span>'+format(field.before)+'</dd>')
    +(change.action === 'delete' ? '' : '<dd><span class="write-preview-value-label">Будет</span>'+format(field.after)+'</dd>')
    +'</div>').join('')+'</dl>';
 }

 function renderChanges(){
  const target = content.querySelector('[data-write-changes]');
  const next = view.changes.slice(offset, offset+30);
  const old = offset;
  target.insertAdjacentHTML('beforeend',next.map((change,i)=>detail(change,old+i)).join(''));
  for(let i=old;i<old+next.length;i++){
   pendingFields.set(i,target.children[i].querySelector('[data-write-fields]'));
  }
  offset += next.length;
  const more = content.querySelector('[data-write-more]');
  more.hidden = offset >= view.changes.length;
  if(!more.hidden)more.textContent = 'Показать ещё '+Math.min(30, view.changes.length-offset);
 }

 function warning(item){
  const label = (item.row ? 'Строка '+item.row+'. ' : '') + item.message;
  const dates = item.dates?.map(date=>[date.scope, date.before, date.after].filter(Boolean).join(' · ')) || [];
  const details = [...dates,...(item.claims || []),...['before','after'].filter(key=>item[key]!=null)
   .map(key=>(key==='before'?'Было · ':'Будет · ')+item[key])];
  return '<li>'+esc(label)+(details.length ? '<ul>'+details.map(text=>'<li>'+esc(text)+'</li>').join('')+'</ul>' : '')+'</li>';
 }

 function actionsFor({back=false,apply=false,reload=false}={}){
  footer.innerHTML = '<div class="ux-form-actions">'
   +(back ? '<button type="button" class="secondary" data-write-back>К предпросмотрам</button>' : '')
   +'<button type="button" class="secondary" data-dialog-close>Закрыть</button>'
   +(apply ? '<button type="button" data-write-apply>Применить изменения</button>' : '')
   +(reload ? '<button type="button" data-write-reload>Проверить состояние</button>' : '')
   +'</div>';
  window.ITDDesign?.refresh();
 }

 function renderDetail(){
  const unavailable = view.applied ? 'Предпросмотр уже применён.' : view.expired
   ? 'Срок предпросмотра истёк. Подготовьте новый.' : view.applicable
   ? '' : 'Предпросмотр нельзя применить. Проверьте результаты.';
  const problems = view.checks.filter(check=>check.status === 'error');
  const spec = view.specification;
  const incomplete = new Set((spec?.rows || []).filter(row=>row.missing.length).map(row=>row.row));
  const warnings = view.warnings.filter(item=>!(incomplete.has(item.row)
   && item.message.startsWith('Строка не добавится.')));
  title.textContent = view.title;
  content.innerHTML = '<p class="write-preview-meta">Раздел '+esc(view.section)
   +' · '+esc(sourceLabels[view.source])+' · Действует до '+esc(time.format(new Date(view.expires_at)))+'</p>'
   + '<p data-write-status role="status">'+esc(unavailable)+'</p>'
   + (problems.length ? '<section class="workspace-stack"><h3>Ошибки проверки</h3><ul>'+problems.map(warning).join('')+'</ul></section>' : '')
   + (warnings.length ? '<section class="workspace-stack"><h3>Предупреждения</h3><ul>'+warnings.map(warning).join('')+'</ul></section>' : '')
   + (spec ? '<section class="workspace-stack" data-write-spec><h3>Спецификация</h3><p class="write-preview-meta">'+esc(spec.file.name)
     +' · <span class="write-preview-hash">SHA-256 '+esc(spec.file.sha256)+'</span></p>'
     +(incomplete.size ? '<p class="hint">Неполных позиций: '+incomplete.size+'. Их реквизиты перечислены в столбце «Проверка».</p>' : '')
     +journalTable([...Object.values(labels),'Источник в файле','Проверка'],spec.rows.map(row=>[
      ...Object.keys(labels).map(key=>format(row[key])),esc([row.page ? 'Страница '+row.page : '',row.sheet,row.locator].filter(Boolean).join(' · ')),
      esc(row.missing.length ? 'Уточнить: '+row.missing.join(', ') : 'Поля заполнены')]))+'</section>' : '')
   + '<section class="workspace-stack"><h3>Изменения ('+view.changes.length+')</h3><div class="workspace-stack" data-write-changes></div>'
   + '<button type="button" class="secondary" data-write-more hidden>Показать ещё</button></section>';
  offset = 0;
  renderChanges();
  if(spec)enhanceDataTable(content.querySelector('[data-write-spec] table'));
  actionsFor({back:context.list,apply:!unavailable});
 }

 function renderList(previews){
  content.innerHTML = previews.length ? '<ul class="file-list">'+previews.map(item =>
   '<li><div><strong>'+esc(item.title)+'</strong><small>'+esc(sourceLabels[item.source])+' · Действует до '
   +esc(time.format(new Date(item.expires_at)))+(item.applicable ? '' : ' · Требуется проверка')
   +'</small></div><button type="button" class="secondary" data-write-id="'+esc(item.preview_id)
   +'" aria-label="'+esc('Открыть предпросмотр «'+item.title+'»')+'">Открыть</button></li>').join('')
   +'</ul>' : '<p>Для этого раздела пока нет предпросмотров.</p>';
  actionsFor();
  [...content.querySelectorAll('[data-write-id]')].find(button=>button.dataset.writeId===context.selected)?.focus();
 }

 function getPreview(identity){
  const query = new URLSearchParams({project_id:String(context.projectId)});
  if(identity)query.set('preview_id',identity);
  return api(endpoint+'?'+query);
 }

 async function load(identity){
  const ticket = ++request;
  view = null;
  pendingFields.clear();
  title.textContent = identity ? 'Предпросмотр изменений' : 'Предпросмотры изменений';
  content.innerHTML = '<p role="status">Загрузка…</p>';
  content.scrollTop = 0;
  actionsFor({back:Boolean(identity&&context.list)});
  title.focus();
  try{
   const result = await getPreview(identity);
   if(ticket !== request)return;
   if(identity){view = result;context.selected = identity;renderDetail();}
   else renderList(result.previews);
  }catch(error){
   if(ticket !== request)return;
   content.innerHTML = '<p role="alert">'+esc(error.message)+'</p>';
  }
 }

 function open(project, identity, opener){
  if(!project || busy || dialog.open)return;
  if(registryDirty()){
   notice('Сначала сохраните или отмените открытые изменения.');
   return;
  }
  context = {projectId:project, list:!identity, opener};
  modal.open({focus:title});
  load(identity);
 }

 function showStatus(message, failed=false){
  const status = content.querySelector('[data-write-status]');
  status.textContent = message;
  status.setAttribute('role',failed ? 'alert' : 'status');
  if(failed){status.tabIndex = -1;status.focus();}
 }

 async function apply(button){
  if(busy || !view || registryDirty())return;
  const {preview_id, project_id, preview_hash} = view;
  busy = true;
  button.disabled = true;
  showStatus('Применяем изменения…');
  let applied = false;
  try{
   await api(endpoint+'/apply',{preview_id,project_id,preview_hash});
   applied = true;
  }catch(error){
   if(error.unknownResult){
    try{
     view = await getPreview(preview_id);
     applied = view.applied;
     if(!applied){
      pendingFields.clear();
      renderDetail();
      if(view.applicable && !view.expired)showStatus('Подтверждение пока не зарегистрировано. Проверьте данные перед повторной отправкой.',true);
     }
    }catch{
     actionsFor({back:context.list,reload:true});
     showStatus('Сервер не подтвердил результат. Проверьте состояние предпросмотра.',true);
    }
   }else if(error.code === 'preview_conflict'){
    actionsFor({back:context.list});
    showStatus(error.message,true);
   }else{
    button.disabled = false;
    showStatus(error.message,true);
   }
  }finally{
   busy = false;
  }
  if(!applied)return;
  modal.close();
  toast('Изменения применены');
  try{await refreshAfterWritePreview(project_id);}
  catch{notice('Изменения применены. Не удалось обновить сведения раздела.');}
 }

 dialog.addEventListener('toggle',event => {
  const panel = event.target;
  const index = Number(panel.dataset?.writeChange);
  if(!panel.open || !pendingFields.has(index))return;
  renderFields(pendingFields.get(index),view.changes[index]);
  pendingFields.delete(index);
 },true);
 dialog.addEventListener('click', event => {
  const button = event.target.closest('button');
  if(!button || busy)return;
  if(button.dataset.writeId)load(button.dataset.writeId);
  else if(button.hasAttribute('data-write-back'))load();
  else if(button.hasAttribute('data-write-reload'))load(view.preview_id);
  else if(button.hasAttribute('data-write-more')){
   const old = offset;
   renderChanges();
   window.ITDDesign?.refresh();
   requestAnimationFrame(()=>content.querySelector('[data-write-changes]')?.children[old]
    ?.querySelector('summary, button')?.focus());
  }
  else if(button.hasAttribute('data-write-apply'))apply(button);
 });
 document.addEventListener('click', event => {
  const button = event.target.closest('[data-open-write-previews]');
  if(button)open(projectId, null, button);
 });
 document.addEventListener('itd:write-preview-open', event => {
  open(event.detail.projectId, event.detail.previewId, event.detail.opener);
 });
})();
