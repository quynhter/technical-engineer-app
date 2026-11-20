import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from '../dependencies.mjs';
const source=readFileSync(new URL('../../../app/itd/web_assets/app.js',import.meta.url),'utf8');
const callbacks=source.slice(source.indexOf('function registryToken()'),source.indexOf('\nfunction objectsPage()'));
const packagePage=source.slice(source.indexOf('function packagePage()'),source.indexOf('\nconst sourceTypeNames='));

test('workspace mounts the API registry and preserves document destinations with dirty/session guards',async()=>{
 const dom=new JSDOM('<div id="registry-app"></div>',{runScripts:'outside-only'}),w=dom.window,calls=[];let mounted;
 w.$=s=>w.document.querySelector(s);w.ITDDesign={renderRegistry:(host,props)=>{mounted=props;assert.equal(host.id,'registry-app');}};
 Object.assign(w,{token:'current-session',projectId:7,pdata:{acts:[]},currentUser:{role:'editor',workspace_id:'workspace-a'},dirty:false,formDirty:false,sessionSuspended:false,packagePanel:'registry',action:fn=>fn(),notice:text=>calls.push(['notice',text]),suspendWorkspace:()=>{},previewAct:id=>calls.push(['preview',id]),openDocumentVersions:id=>calls.push(['versions',id]),openManual:(kind,id)=>calls.push([kind,id]),openSourceFileCard:id=>calls.push(['original',id]),downloadRelease:id=>calls.push(['download',id]),navigate:view=>calls.push(['navigate',view])});
 w.eval(callbacks+packagePage+'\nwindow.mountRegistry=mountRegistry;window.packagePage=packagePage;');
 assert.match(w.packagePage(),/id="registry-app"/);assert.doesNotMatch(w.packagePage(),/data-registry-export|data-registry-zip|<table/);
 w.mountRegistry();assert.equal(mounted.projectId,7);assert.equal(mounted.workspaceId,'workspace-a');assert.equal(mounted.getToken(),'current-session');
 w.token='renewed';assert.equal(mounted.getToken(),'renewed');
 for(const [entity,id] of [['act',2],['scheme',3],['attachment',4],['release',5],['journal','incoming'],['journal','ojr'],['journal','cable']])await mounted.onOpen({entity,id});
 assert.deepEqual(calls,[['versions',2],['scheme-edit',3],['original',4],['download',5],['navigate','journal'],['navigate','ojr'],['navigate','cable']]);
 calls.length=0;w.currentUser.role='viewer';await mounted.onOpen({entity:'act',id:2});assert.deepEqual(calls,[['preview',2]]);
 for(const key of ['dirty','formDirty','sessionSuspended']){calls.length=0;w[key]=true;assert.equal(mounted.isDirty(),true);await mounted.onOpen({entity:'act',id:2});assert.equal(calls.length,1);assert.equal(calls[0][0],'notice');w[key]=false;}
 mounted.onChanged({registry:[]});assert.equal(w.pdata.registry.length,0);
 w.projectId=8;mounted.onChanged({registry:['stale']});assert.equal(w.pdata.registry.length,0);
 w.projectId=7;w.currentUser.workspace_id='other-db';mounted.onChanged({registry:['stale']});assert.equal(w.pdata.registry.length,0);
 dom.window.close();
});

test('cable journal opens the native work form with the cable type and the selected record',()=>{
 const dom=new JSDOM('<div id="cable-app"></div>',{runScripts:'outside-only'}),w=dom.window,calls=[];let mounted;
 w.$=s=>w.document.querySelector(s);w.ITDDesign={renderProjectRecords:(host,props)=>mounted=props};
 Object.assign(w,{projectId:7,pdata:{},currentUser:{role:'editor',workspace_id:'one'},openEditor:(kind,item)=>calls.push({kind,item}),suspendWorkspace:()=>{}});
 w.eval(callbacks+'\nwindow.mountCable=mountCable;');w.mountCable();assert.equal(mounted.kind,'cable');mounted.onCreate();assert.equal(calls[0].kind,'work');assert.equal(calls[0].item.work_type,'cable');
 mounted.onOpen({id:1},{workspace_entries:[{id:1,kind:'work',work_type:'cable'}]});assert.equal(calls[1].kind,'work');assert.equal(calls[1].item.id,1);dom.window.close();
});

test('workspace rendering retains the table host for data updates and replaces it on project changes',()=>{
 const dom=new JSDOM('<main><div id="sidebar"></div><div id="content"></div><div id="actions"></div></main>',{runScripts:'outside-only'}),w=dom.window,d=w.document;
 w.$=selector=>d.querySelector(selector);
 Object.assign(w,{workspaceView:'schemes',step:3,projectId:7,currentUser:{role:'editor',workspace_id:'db'},journalSection:'3',packagePanel:'registry',resourcePanel:'list',dirty:false,state:{object:{id:1}},navigate:()=>{},crumbTrail:()=>[],icon:()=>'',orgSidebar:()=>'',decorateSelects:()=>{},objectPage:()=>'',participantsPage:()=>'',rdPage:()=>'',manualPage:()=>'',idPage:()=>'<h1>Схемы</h1><div id="schemes-app"></div>'});
 for(const name of ['mountRegistry','mountSourceFiles','mountSchemes','mountDocuments','mountResources','mountFacts','mountIncoming','mountCable','mountWork','mountJournal','mountWorkflow','mountManual','mountSectionTabs'])w[name]=()=>{const host=d.querySelector('#schemes-app');if(host){host.dataset.astryxIsland='';host.textContent='Таблица';}};
 const renderSource=source.slice(source.indexOf('let renderedTableContext=null;'),source.indexOf('function registryToken()'));
 w.eval(renderSource);w.render();const host=d.querySelector('#schemes-app'),heading=d.querySelector('h1');w.render();assert.equal(d.querySelector('#schemes-app'),host);assert.equal(d.querySelector('h1'),heading);
 w.projectId=8;w.render();assert.notEqual(d.querySelector('#schemes-app'),host);dom.window.close();
});
