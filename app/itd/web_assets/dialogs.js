'use strict';
// Общий жизненный цикл окон. Вложенный справочник не закрывает форму под ним.
function createWorkspaceDialog(id,{beforeClose=()=>true,onClose=()=>{}}={}){
 const dialog=document.getElementById(id);
 const heading=dialog.querySelector('.dialog-title');
 function setTitle(title){heading.textContent=title;}
 let pending=false;
 function close(force=false){
  if(!dialog.open)return true;
  if(!force){
   if(pending)return false;
   const allowed=beforeClose();
   if(allowed instanceof Promise){
    pending=true;
    allowed.then(value=>{if(value)close(true);}).finally(()=>pending=false);
    return false;
   }
   if(!allowed)return false;
  }
  if(!window.ITDDesign?.closeDialog(dialog))dialog.close();return true;
 }
 function open({title,focus}={}){
  if(title)setTitle(title);
  if(!dialog.open){if(window.ITDDesign?.openDialog)window.ITDDesign.openDialog(dialog);else dialog.showModal();dialog.scrollTop=0;}
  if(focus)focus.focus();
 }
 dialog.addEventListener('click',event=>{if(event.target.closest('[data-dialog-close]')?.closest('dialog')===dialog)close();});
 dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
 dialog.addEventListener('close',onClose);
 return {open,close,setTitle};
}
