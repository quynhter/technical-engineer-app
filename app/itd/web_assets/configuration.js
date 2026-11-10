'use strict';
const configurationNames={object:'Объект',rd:'Разделы рабочей документации',participants:'Участники',permits:'Разрешительная документация'};
let configurationPreview=null;
async function exportConfiguration(){
 if(dirty||formDirty)throw Error('Сначала сохраните изменения.');
 if(!state.object.id)throw Error('Сначала сохраните объект.');
 if(!configurationNames[workspaceView]){if(!projectId)throw Error('Выберите рабочий раздел.');const section=await api('/api/project?project_id='+projectId);downloadJson({format:'itd-documentation',version:1,object:{id:state.object.id,name:state.object.name},project_data:section},'Исполнительная документация.json');return;}
 const value=await api('/api/configuration?object_id='+state.object.id+'&scope='+workspaceView);
 downloadJson(value,configurationNames[workspaceView]+'.json');
}
function chooseConfiguration(){
 if(dirty||formDirty){notice('Сначала сохраните изменения.');return;}
 const picker=document.createElement('input');picker.type='file';picker.accept='.json,application/json';
 picker.addEventListener('change',()=>action(async()=>{
  const file=picker.files[0];if(!file)return;if(file.size>8*1024*1024)throw Error('Конфигурация больше 8 МБ');
  let document;try{document=JSON.parse(await file.text());}catch(_){throw Error('Не удалось прочитать JSON. Выберите экспортированную конфигурацию.');}
  configurationPreview=await api('/api/configuration/preview',{object_id:state.object.id,scope:workspaceView,document});
  openEditor('manual');editorWindow.setTitle('Импорт: '+configurationNames[workspaceView]);
  $('#editor-content').innerHTML=`<p>Проверьте изменения перед применением.</p>${journalTable(['Поле','Сейчас','После импорта'],configurationPreview.changes.map(c=>[esc(c.field),esc(JSON.stringify(c.before)),esc(JSON.stringify(c.after))]))}<p class="table-total">Всего изменений: ${configurationPreview.changes.length}</p><div class="ux-form-actions"><button type="button" data-config-apply ${configurationPreview.changes.length?'':'disabled'}>Применить и сохранить</button><button type="button" class="secondary" data-action="cancel-entry">Отмена</button></div>`;
 }));picker.click();
}
document.addEventListener('click',e=>{if(!e.target.closest('[data-config-apply]'))return;action(async()=>{
 if(!configurationPreview)return;
 state=await api('/api/save',configurationPreview.state);configurationPreview=null;dirty=false;formDirty=false;closeEditor(true);
 await refreshMeta();await loadObject(state.object.id);render();toast('Конфигурация импортирована');
});});
