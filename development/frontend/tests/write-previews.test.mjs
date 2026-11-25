import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFile} from 'node:fs/promises';
import {JSDOM} from '../dependencies.mjs';

const assets=new URL('../../../app/itd/web_assets/',import.meta.url);
const [html,dialogs,script]=await Promise.all(['index.html','dialogs.js','write-previews.js'].map(
 file=>readFile(new URL(file,assets),'utf8')));
const tick=()=>new Promise(resolve=>setTimeout(resolve,30));
const endpoint='/api/v1/write-previews';
const preview={
 project_id:1,preview_id:'sample',preview_hash:'hash',section:'ЭОМ «Учебный»',title:'Ведомость ресурсов',
 source:'assistant',expires_at:'2026-11-25T13:00:00Z',applicable:true,checks:[],warnings:[],
 changes:[{action:'update',label:'Ресурсы',id:1,fields:[{label:'Наименование',before:'Старое',after:'Новое'}]}],
};

function setup(t,request){
 const dom=new JSDOM(html,{runScripts:'outside-only',pretendToBeVisual:true,url:'http://localhost/'});
 t.after(()=>dom.window.close());
 const w=dom.window,d=w.document;
 const dialog=d.getElementById('write-preview-dialog');
 dialog.showModal=()=>dialog.setAttribute('open','');
 dialog.close=()=>{dialog.removeAttribute('open');dialog.dispatchEvent(new w.Event('close'));};
 const opener=d.createElement('button');
 d.body.append(opener);
 const toasts=[],refreshes=[];
 Object.assign(w,{
  registryDirty:()=>false,notice:()=>{},toast:value=>toasts.push(value),
  refreshAfterWritePreview:async id=>refreshes.push(id),
  api:request,esc:value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
 });
 w.eval(dialogs+'\n'+script);
 const open=()=>d.dispatchEvent(new w.CustomEvent('itd:write-preview-open',{
  detail:{projectId:1,previewId:'sample',opener},
 }));
 return {w,d,dialog,opener,open,toasts,refreshes};
}

test('Сравнение раскрывается по требованию, устаревшее подтверждение убирает кнопку отправки',async t=>{
 let submissions=0;
 const {w,d,dialog,open,opener}=setup(t,async(path,data)=>{
  if(!data)return preview;
  assert.equal(path,endpoint+'/apply');
  submissions++;
  throw Object.assign(Error('Данные изменились. Подготовьте новый.'),{code:'preview_conflict'});
 });
 open();
 await tick();
 const details=dialog.querySelector('[data-write-change]');
 assert.equal(details.querySelector('[data-write-fields]').textContent,'');
 details.open=true;
 details.dispatchEvent(new w.Event('toggle'));
 assert.match(details.textContent,/БылоСтарое/);
 assert.match(details.textContent,/БудетНовое/);
 dialog.querySelector('[data-write-apply]').click();
 await tick();
 assert.equal(submissions,1);
 assert.equal(dialog.querySelector('[data-write-apply]'),null);
 assert.equal(d.activeElement,dialog.querySelector('[role="alert"]'));
 dialog.dispatchEvent(new w.Event('cancel',{cancelable:true}));
 await tick();
 assert.equal(d.activeElement,opener);
});

test('Потерянный ответ проверяется чтением без повторной отправки изменений',async t=>{
 let submissions=0,reads=0;
 const {dialog,open,toasts,refreshes}=setup(t,async(path,data)=>{
  if(data){
   submissions++;
   throw Object.assign(Error('Обрыв соединения'),{unknownResult:true});
  }
  return {...preview,applied:++reads>1};
 });
 open();
 await tick();
 dialog.querySelector('[data-write-apply]').click();
 await tick();
 assert.deepEqual({submissions,reads},{submissions:1,reads:2});
 assert.deepEqual(toasts,['Изменения применены']);
 assert.deepEqual(refreshes,[1]);
 assert.equal(dialog.open,false);
});
