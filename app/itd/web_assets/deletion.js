'use strict';
function inferRowRecord(row){
 if(row.dataset.recordEntity&&row.dataset.recordId)return {entity:row.dataset.recordEntity,id:Number(row.dataset.recordId)};
 const sources=[['[data-edit-entry]','workspace_entries','editEntry'],['[data-journal-edit]','workspace_entries','journalEdit'],
  ['[data-special-edit]','special_journals','specialEdit'],['[data-version-act]','acts','versionAct'],
  ['[data-resource-card]','resources','resourceCard'],['[data-scheme-card]','schemes','schemeCard'],
  ['[data-file-card]','attachments','fileCard'],['[data-download]','releases','download']];
 for(const [selector,entity,key] of sources){const control=row.querySelector(selector);if(control)return {entity,id:Number(control.dataset[key])};}
 return null;
}
function enhanceRowDeletion(table){
 if(typeof currentUser==='undefined'||currentUser?.role==='viewer'||!table.closest('#content')||table.closest('form,[data-version-table]'))return;
 const rows=[...table.tBodies[0].rows].filter(row=>!row.classList.contains('date-group')&&row.querySelectorAll('td').length>1);
 const records=rows.map(row=>[row,inferRowRecord(row)]);
 if(!records.some(([,record])=>record?.id>0))return;
 let heading=table.tHead.querySelector('[data-delete-column]');
 if(!heading){
  heading=document.createElement('th');heading.dataset.deleteColumn='';heading.textContent='Действия';
  table.tHead.rows[0].insertBefore(heading,table.tHead.querySelector('[data-table-fill]'));
 }
 for(const [row,record] of records){
  let cell=row.querySelector('[data-delete-cell]');
  if(cell)continue;
  cell=document.createElement('td');cell.dataset.deleteCell='';
  if(record?.id>0){
   const button=document.createElement('button');button.type='button';button.className='ghost danger';
   button.textContent='Удалить';button.dataset.recordDelete=record.entity;button.dataset.recordId=record.id;
   button.setAttribute('aria-label','Удалить запись');cell.append(button);
  }
  row.insertBefore(cell,row.querySelector('[data-table-fill]'));
 }
 // Заголовки групп учитывают дополнительную колонку и общий заполнитель.
 for(const row of table.tBodies[0].rows)if(row.cells.length===1&&row.cells[0].colSpan>1)row.cells[0].colSpan=table.tHead.rows[0].cells.length;
}
function recordDeleteButton(entity,id){
 return typeof currentUser!=='undefined'&&currentUser?.role!=='viewer'&&id?`<button type="button" class="ghost danger" data-record-delete="${esc(entity)}" data-record-id="${esc(id)}">Удалить</button>`:'';
}
let recordDeleteWindow=null;
async function previewRecordDeletion(entity,id){
 if(dirty||formDirty)throw Error('Сначала сохраните изменения.');
 if(!projectId)throw Error('Выберите раздел объекта.');
 const pid=projectId,objectId=state.object.id;
 const plan=await api('/api/action',{project_id:pid,action:'delete-preview',data:{entity,id}});
 let dialog=document.getElementById('record-delete-dialog');
 if(!dialog){
  dialog=document.createElement('dialog');dialog.id='record-delete-dialog';dialog.className='workspace-dialog';
  dialog.setAttribute('aria-labelledby','record-delete-title');
  dialog.innerHTML='<div class="dialog-bar"><h2 id="record-delete-title" class="dialog-title">Удаление записи</h2><button type="button" class="secondary" data-dialog-close aria-label="Закрыть">×</button></div><div class="dialog-content"></div>';
  document.body.append(dialog);recordDeleteWindow=createWorkspaceDialog(dialog.id);
 }
 const groups=[['delete','Будут удалены'],['clear','Будут очищены ссылки']];
 dialog.querySelector('.dialog-content').innerHTML=`<p>Удаление выбранной записи и обязательных дочерних записей нельзя отменить. Проверьте весь список последствий.</p>${groups.map(([action,label])=>{
  const items=plan.items.filter(item=>item.action===action);if(!items.length)return '';
  return `<section class="delete-plan-section"><h3>${label}: ${items.length}</h3><ul class="delete-plan-list">${items.map(item=>`<li><strong>${esc(item.entity)}. ${esc(item.name)}</strong>${item.scope?`<p>${esc(item.scope)}</p>`:''}<p class="hint">${esc(item.reason)}</p></li>`).join('')}</ul></section>`;
 }).join('')}<p class="hint">${esc(plan.archive_note)}</p><p role="alert" data-delete-error></p><div class="ux-form-actions"><button type="button" class="secondary danger" data-confirm-record-delete>Удалить</button><button type="button" class="secondary" data-dialog-close>Отмена</button></div>`;
 dialog.querySelector('[data-confirm-record-delete]').addEventListener('click',async event=>{
  const button=event.currentTarget;button.disabled=true;
  try{
   if(pid!==projectId||objectId!==state.object.id)throw Error('Выбран другой объект или раздел. Откройте предупреждение заново.');
   await api('/api/action',{project_id:pid,action:'delete-apply',data:{entity,id,token:plan.token}});
   recordDeleteWindow.close(true);closeEditor(true);formDirty=false;documentVersionState=null;
   await refreshMeta();
   if(meta.objects.some(o=>o.id===objectId)){
    state=await api('/api/workspace?object_id='+objectId);
    await loadProject(state.projects.some(p=>p.id===pid)?pid:state.projects[0]?.id||null);
   }else{state={object:{},participants:[],projects:[],token:null};await loadProject(null);workspaceView='objects';}
   render();toast('Запись удалена. Связанные данные обновлены.');
  }catch(error){dialog.querySelector('[data-delete-error]').textContent=error.message;button.disabled=false;}
 });
 recordDeleteWindow.open({focus:dialog.querySelector('.ux-form-actions [data-dialog-close]')});
}
document.addEventListener('click',event=>{
 const button=event.target.closest('[data-record-delete]');if(!button)return;
 event.preventDefault();action(()=>previewRecordDeletion(button.dataset.recordDelete,Number(button.dataset.recordId)));
});
