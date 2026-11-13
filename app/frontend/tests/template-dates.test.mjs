import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const root=new URL('../../../',import.meta.url);
const groups=JSON.parse(fs.readFileSync(new URL('app/forms/date_groups.json',root)));
const context=vm.createContext({pdata:{date_groups:groups}});
vm.runInContext(fs.readFileSync(new URL('app/itd/web_assets/act-fields.js',root),'utf8'),context);
const normalize=(code,fields)=>context.normalizeDateFields(code,fields);
test('split dates use one calendar input and derive the remaining print parts',()=>{
 for(const [code,list] of Object.entries(groups))for(const group of list){
  const fields=Object.values(group.parts).map(key=>({key,kind:'literal',value:null,label:'"'}));
  const result=normalize(code,fields);
  assert.equal(result.filter(f=>f.kind==='literal').length,group.source?0:1,code);
  assert.deepEqual(JSON.parse(JSON.stringify(result)),JSON.parse(JSON.stringify(normalize(code,result))),code);
  assert.ok(result.every(f=>f.input_type==='date'&&f.label===group.label));
  result[0]={...result[0],kind:'literal',value:'2024-02-29'};
  const manual=normalize(code,result);
  assert.equal(manual[0].value,'2024-02-29');
  assert.equal(manual[1].source,'date_inputs.'+group.parts.day);
 }
});
test('legacy values retain their text after merging calendar metadata',()=>{
 const fields=normalize('СП_77_А_5',Object.values(groups['СП_77_А_5'][0].parts).map(key=>({key,kind:'literal',value:null})));
 const values=['07','мая','2025'];
 const legacy=normalize('СП_77_А_5',fields.map((f,i)=>({...f,kind:'literal',value:values[i]})));
 assert.deepEqual(Array.from(legacy,f=>f.value),values);
 assert.ok(legacy.every(f=>!f.format&&!f.value_type&&!f.input_type));
});

test('calendar input has a visible label, accepts focus and saves ISO in both themes',async()=>{
 const {JSDOM}=await import('jsdom');
 const source=fs.readFileSync(new URL('app/itd/web_assets/act-fields.js',root),'utf8');
 for(const theme of ['light','dark']){
  const dom=new JSDOM(`<html data-theme="${theme}"><body><form id="act-form"><div id="act-fields"></div></form></body></html>`,{runScripts:'outside-only'});
  const w=dom.window,group=groups['СП_77_А_8'][0];
  const definition={code:'СП_77_А_8',name:'Проверка даты',fields:Object.values(group.parts).map(key=>({key,kind:'literal',value:null,required:true}))};
  Object.assign(w,{pdata:{date_groups:groups},meta:{document_roles:{}},$:s=>w.document.querySelector(s),esc:v=>String(v??''),cleanFieldLabel:v=>v,actForms:()=>[definition],decorateSelects:()=>{},versionTables:()=>''});
  w.eval(source+'\nactInputRoots=()=>({});Object.assign(window,{renderActFields,collectActFields});');w.renderActFields(definition.code);
  const input=w.document.querySelector('input[type=date]');
  assert.equal(w.document.querySelectorAll('input').length,1);
  assert.equal(input.closest('label').querySelector('span').textContent,'Дата документа *');
  input.focus();assert.equal(w.document.activeElement,input);
  input.value='2024-02-29';
  const saved=w.collectActFields(w.document.querySelector('form'),definition);
  assert.equal(saved.length,1);assert.equal(saved[0].value,'2024-02-29');
  assert.equal(saved[0].format,'day_2digits');assert.equal(saved[0].value_type,'date');
  dom.window.close();
 }
});
