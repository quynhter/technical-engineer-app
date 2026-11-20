import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from '../dependencies.mjs';
const asset=name=>readFileSync(new URL('../../../app/itd/web_assets/'+name,import.meta.url),'utf8');
const source=asset('app.js'),preview=source.slice(source.indexOf('let filePlan=null;'),source.indexOf('\nfunction workPage()'));
test('file recovery requires confirmation and requests a fresh plan in both themes',async()=>{
 for(const theme of ['light','dark'])for(const confirmed of [false,true]){
  const dom=new JSDOM(`<html data-theme="${theme}"><body><div id="editor-content"></div></body></html>`,{runScripts:'outside-only'}),w=dom.window,calls=[];
  w.eval(`var dirty=false,formDirty=false,projectId=1,$=s=>document.querySelector(s),esc=String,decorateSelects=()=>{},openEditor=()=>{},editorWindow={setTitle:()=>{}};`);
  w.confirmWorkspace=async()=>confirmed;
  let plans=0;
  w.api=async(path,body)=>{
   calls.push({path,body});
   if(path==='/api/files/plan'&&plans++===0)throw Error('Сначала выполните восстановление файлов');
   return {plan:{actions:[],blocked:[]}};
  };
  w.eval(preview+'\nwindow.previewFiles=previewFiles;');
  await w.previewFiles('check');
  assert.deepEqual(calls.map(c=>c.path),confirmed?['/api/files/plan','/api/files/recover','/api/files/plan']:['/api/files/plan']);
  if(confirmed){
   assert.equal(calls[1].body.confirmed,true);
   assert.equal(calls[1].body.project_id,1);
   const button=w.document.querySelector('[data-dialog-close]');button.focus();assert.equal(w.document.activeElement,button);
  }
  dom.window.close();
 }
});
test('file plan errors unrelated to recovery never trigger a recovery write',async()=>{
 const dom=new JSDOM('',{runScripts:'outside-only'}),w=dom.window;
 w.eval('var dirty=false,formDirty=false,projectId=1;');
 const calls=[];w.api=async(path)=>{calls.push(path);throw Error('Выберите раздел');};
 w.eval(preview+'\nwindow.previewFiles=previewFiles;');
 await assert.rejects(w.previewFiles('check'),/Выберите раздел/);
 assert.deepEqual(calls,['/api/files/plan']);dom.window.close();
});
