import {AssistantNavItem,AssistantPanel} from './assistant.jsx';
import {createAdapters} from './adapters.jsx';
import {createPortal,flushSync} from 'react-dom';
import {createTableAdapter} from './astryx-tables.jsx';
import {Registry} from './registry.jsx';
import {SourceFiles} from './source-files.jsx';
import {ProjectRecords} from './project-records.jsx';
import {ManualRecords} from './manual-records.jsx';
import {WorkflowRecords} from './workflow-records.jsx';
import {JournalRecords} from './journal-records.jsx';
import {WorkRecords} from './work-records.jsx';
import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Theme} from '@astryxdesign/core/theme';
import {stoneTheme} from '@astryxdesign/theme-stone/built';
import {butterTheme} from '@astryxdesign/theme-butter/built';
import {gothicTheme} from '@astryxdesign/theme-gothic/built';
import {y2kTheme} from '@astryxdesign/theme-y2k/built';
import {neutralTheme} from '@astryxdesign/theme-neutral/built';
import {InternationalizationProvider} from '@astryxdesign/core/i18n';
import {AppShell,TopNav,TopNavHeading,Selector,SideNav,SideNavItem,SideNavSection,Button,TabList,Tab,TabMenu,Pagination,Breadcrumbs,BreadcrumbItem,Heading} from '@astryxdesign/core';
import ru from '@astryxdesign/core/locales/ru-RU.json';
import recipes from './primitives.json';
import headerLogo from '../../itd/web_assets/logo.svg';

import '@astryxdesign/core/reset.css';
import '@astryxdesign/core/astryx.css';
import '@astryxdesign/theme-neutral/theme.css';
import '@astryxdesign/theme-stone/theme.css';
import '@astryxdesign/theme-butter/theme.css';
import '@astryxdesign/theme-gothic/theme.css';
import '@astryxdesign/theme-y2k/theme.css';

import './workspace.css';
const islands=new Map();
const themes={neutral:neutralTheme,stone:stoneTheme,butter:butterTheme,gothic:gothicTheme,y2k:y2kTheme};
let selectedTheme="neutral";try{const saved=localStorage.getItem("itd.design.theme");if(themes[saved])selectedTheme=saved;}catch(_){}
function Providers({children}){return <Theme theme={themes[selectedTheme]} mode={document.documentElement.dataset.theme||'light'}><InternationalizationProvider locale="ru-RU" messages={{'ru-RU':ru}}>{children}</InternationalizationProvider></Theme>;}
// One provider owns <html>; portals share its context across legacy DOM slots.
// Independent root Themes previously removed global attributes when tabs unmounted.
const providerHost=document.createElement('div');providerHost.id='design-provider-root';document.body.append(providerHost);
const providerRoot=createRoot(providerHost);let nextIsland=0;
function renderIslands(){providerRoot.render(<Providers>{[...islands].map(([host,item])=>createPortal(item.element,host,item.key))}</Providers>);}
function mount(host,element){if(!host)return;let item=islands.get(host);if(!item){host.dataset.astryxIsland='';item={key:String(++nextIsland)};islands.set(host,item);}item.element=element;renderIslands();}
function cleanup(){let changed=false;for(const [host] of islands)if(!host.isConnected){islands.delete(host);changed=true;}if(changed)renderIslands();}

function primitive(node,key){
 const attrs=recipes[key];if(!attrs)return;
 if(node.dataset.primitive===key&&(!attrs.content||node.querySelector('[data-itd-button-body]')))return;
 const previous=recipes[node.dataset.primitive];if(previous?.class)node.classList.remove(...previous.class.split(' ').filter(Boolean));
 if(attrs.class)node.classList.add(...attrs.class.split(' ').filter(Boolean));
 for(const [name,value] of Object.entries(attrs))if(!['class','style','content'].includes(name))node.setAttribute(name,value);
 if(attrs.style){const template=document.createElement('span');template.setAttribute('style',attrs.style);for(const property of Array.from(template.style))node.style.setProperty(property,template.style.getPropertyValue(property));}
 if(attrs.content){const body=document.createElement('template');body.innerHTML=attrs.content;const walker=document.createTreeWalker(body.content,NodeFilter.SHOW_TEXT);let text;while(text=walker.nextNode())if(text.textContent==='__ITD_LABEL__'){const slot=text.parentElement;slot.dataset.itdButtonBody='';slot.replaceChildren(...node.childNodes);break;}node.replaceChildren(body.content);}
 node.dataset.primitive=key;
}
function isReactOwned(node){const island=node.closest?.('[data-astryx-island]');return island&&!(node.closest('[data-native-content]')&&island.contains(node.closest('[data-native-content]')))&&(island.id!=='shell-root'||!node.closest('.workspace-content'));}
function enhancePrimitives(){
 for(const button of document.querySelectorAll('button')){
  if(isReactOwned(button)||button.matches('.brand,.account-avatar,.object-tile,.journal-task,.cell-open,.record-name,.journey-link,.link-button,.table-sort,.table-chip')||button.closest('.org-list,.tabs,.panel-nav,.journal-sections'))continue;
  primitive(button,'button-'+(button.classList.contains('danger')?'destructive':button.classList.contains('ghost')?'ghost':button.classList.contains('secondary')?'secondary':'primary'));
 }
 for(const [selector,key] of [['.card:not(details)','card'],['.pill','badge'],['.table-scroll table','table']])document.querySelectorAll(selector).forEach(node=>{if(!isReactOwned(node)&&!node.closest('.knowledge-text')&&!(key==='table'&&(node.closest('[data-document-table]')||node.closest('form'))))primitive(node,key);});
 for(const node of document.querySelectorAll('h1,h2,h3,h4'))if(!isReactOwned(node))primitive(node,'heading-'+node.tagName.slice(1));
}
const selectHosts=new WeakMap();
function NativeSelector({select,label,value:externalValue}){
 const [value,setValue]=useState(externalValue),[disabled,setDisabled]=useState(select.disabled),ref=React.useRef(null);
 React.useEffect(()=>{const observer=new MutationObserver(()=>setDisabled(select.disabled));observer.observe(select,{attributes:true,attributeFilter:['disabled']});return()=>observer.disconnect();},[select]);
 React.useEffect(()=>setValue(externalValue),[externalValue]);
 React.useEffect(()=>{const sync=()=>setValue(select.value);select.addEventListener('change',sync);select.addEventListener('smart-sync',sync);select.focus=()=>ref.current?.focus();return()=>{select.removeEventListener('change',sync);select.removeEventListener('smart-sync',sync);};},[select]);
 const convert=o=>({value:o.value,label:o.textContent,disabled:o.disabled});
 const options=[...select.children].map(child=>child.tagName==='OPTGROUP'?{type:'section',title:child.label,options:[...child.children].map(convert)}:convert(child));
 return <Selector label={label} isLabelHidden options={options} value={value} isDisabled={disabled} hasSearch={select.options.length>6} searchPlaceholder="Найти…" width="100%" ref={ref} onChange={value=>{if(select.disabled)return;select.value=value;setValue(value);select.dispatchEvent(new Event('input',{bubbles:true}));select.dispatchEvent(new Event('change',{bubbles:true}));}}/>;
}
function enhanceSelect(select){
 if(select.multiple||isReactOwned(select))return;
 let host=selectHosts.get(select);
 if(!host){
  const owner=select.closest('label.field');if(owner){const field=document.createElement('div');for(const a of owner.attributes)if(a.name!=='for')field.setAttribute(a.name,a.value);field.append(...owner.childNodes);owner.replaceWith(field);}
  const label=select.getAttribute('aria-label')||select.closest('.field')?.querySelector('span')?.textContent||document.querySelector(`label[for="${select.id}"]`)?.textContent||'Выберите значение';
  select.setAttribute('aria-label',label.trim());select.hidden=true;select.tabIndex=-1;select.setAttribute('aria-hidden','true');
  host=document.createElement('div');host.className='select-island';host._nativeSelect=select;select.after(host);selectHosts.set(select,host);
 }
 mount(host,<NativeSelector select={select} label={select.getAttribute('aria-label')} value={select.value}/>);
}
function enhanceTabs(){
 for(const host of document.querySelectorAll('.tabs,.panel-nav,.journal-sections')){
  if(host.hasAttribute('data-astryx-island'))continue;
  const buttons=[...host.children].filter(n=>n.tagName==='BUTTON');if(!buttons.length)continue;
  const workspace=host.closest('.id-workspace');
  if(workspace){
   let row=workspace.querySelector('.workspace-tab-row');
   if(!row){
    row=document.createElement('div');
    row.className='workspace-tab-row';
    host.before(row);
   }
   row.append(host);
  }
  const label=host.getAttribute('aria-label')||'Разделы';
  const options=buttons.map((button,i)=>({value:String(i),label:button.textContent.trim()}));
  const active=buttons.findIndex(button=>button.matches('.active,[aria-current]'));
  // Keep the native commands connected for delegated navigation and form guards.
  const commands=document.createElement('div');
  commands.hidden=true;
  commands.append(...buttons);
  host.append(commands);
  mount(host,<TabList value={String(Math.max(active,0))} onChange={value=>buttons[Number(value)].click()} size="lg" aria-label={label}>
   <TabMenu label={label} options={options}/>
  </TabList>);
 }
}
function SectionTabs({label,value,items,onChange}){
 return <TabList value={value} onChange={onChange} size="lg" aria-label={label}>{items.map(item=>item.options?<TabMenu key={item.label} label={item.label} options={item.options}/>:<Tab key={item.value} value={item.value} label={item.label}/>)}</TabList>;
}
function glyph(markup){return <span className="nav-glyph" aria-hidden="true" dangerouslySetInnerHTML={{__html:markup}}/>;}
const nativeContentNodes=['#breadcrumbs','.context','main'].map(sel=>document.querySelector(sel)).filter(Boolean);
const shellHost=document.createElement('div');shellHost.id='shell-root';document.body.prepend(shellHost);
const workspaceStatus=document.getElementById('workspace-status'),statusSlots=new Set();
const statusParking=document.createElement('div');statusParking.hidden=true;document.body.append(statusParking);if(workspaceStatus)statusParking.append(workspaceStatus);
function WorkspaceStatus(){const ref=React.useRef(null);React.useLayoutEffect(()=>{const slot=ref.current;statusSlots.add(slot);if(workspaceStatus)slot.append(workspaceStatus);return()=>{statusSlots.delete(slot);if(workspaceStatus?.parentElement===slot){const next=[...statusSlots].find(node=>node.isConnected);(next||statusParking).append(workspaceStatus);}};},[]);return <div className="nav-status" data-native-content="" ref={ref}/>;}
function NativeContent(){const ref=React.useRef(null);React.useLayoutEffect(()=>{if(ref.current)ref.current.append(...nativeContentNodes);},[]);return <div className="workspace-content" ref={ref}/>;}
function changeTheme(value){selectedTheme=value;try{localStorage.setItem('itd.design.theme',value);}catch(_){}document.dispatchEvent(new Event('itd:appearance'));}
const accountNodes=['session-logout','session-resume'].map(id=>document.getElementById(id)).filter(Boolean);
const accountParking=document.createElement('div');accountParking.hidden=true;accountParking.id='account-control-storage';document.body.append(accountParking);
function AccountControl(){
 const ref=React.useRef(null);
 React.useLayoutEffect(()=>{const slot=ref.current;slot.append(...accountNodes);return()=>{for(const node of accountNodes)if(node.parentElement===slot)accountParking.append(node);};},[]);
 return <div className="account-control" ref={ref} data-native-content=""/>;
}
function ConnectionIndicator(){
 const ref=React.useRef(null);
 React.useLayoutEffect(()=>{const indicator=document.getElementById('database-status');if(indicator)ref.current.append(indicator);return()=>{if(indicator)statusParking.append(indicator);};},[]);
 return <span className="brand-connection" ref={ref} data-native-content=""/>;
}
function Header(){const [,redraw]=useState(0);React.useEffect(()=>{const refresh=()=>redraw(n=>n+1);document.addEventListener('itd:appearance',refresh);return()=>document.removeEventListener('itd:appearance',refresh);},[]);return <TopNav label="АСУПС" heading={<TopNavHeading heading={<span className="brand-title" title="Автоматизированная система управления процессом стройки">АСУПС<ConnectionIndicator/></span>} logo={<span className="workspace-logo" aria-hidden="true" dangerouslySetInnerHTML={{__html:headerLogo}}/>}/>} endContent={<div className="header-actions"><Selector label="Тема оформления" isLabelHidden variant="ghost" value={selectedTheme} options={Object.keys(themes).map(value=>({value,label:({neutral:'Neutral',stone:'Stone',butter:'Butter',gothic:'Gothic',y2k:'Y2K'})[value]}))} onChange={changeTheme}/><Button label={document.documentElement.dataset.theme==='dark'?'Светлая тема':'Тёмная тема'} variant="ghost" onClick={()=>document.dispatchEvent(new Event('itd:theme-toggle'))}/><AccountControl/></div>}/>;}
function WorkspaceShell({rail,view,assistant}){const [isOpen,onOpenChange]=useState(false);React.useEffect(()=>onOpenChange(false),[view]);React.useEffect(()=>{const close=()=>onOpenChange(false);document.addEventListener('itd:assistant-open',close);document.addEventListener('itd:assistant-admin',close);return()=>{document.removeEventListener('itd:assistant-open',close);document.removeEventListener('itd:assistant-admin',close);};},[]);return <AppShell variant="section" contentPadding={0} topNav={<Header/>} sideNav={rail} mobileNav={{breakpoint:'md',isOpen,onOpenChange}}><div className="assistant-workspace"><NativeContent/><AssistantPanel key={(assistant?.workspaceId||'')+':'+(assistant?.userId||'')} config={assistant}/></div></AppShell>;}
function renderNav(items,view,go,trail=[],assistant){
 const objectPicker=document.getElementById('overview-object-picker');
 if(objectPicker)objectPicker.hidden=view!=='overview';
 const rail=<SideNav className="workspace-nav" aria-label="Рабочее пространство" footer={<WorkspaceStatus/>} collapsible resizable={{defaultWidth:244,minWidth:160,maxWidth:340,autoSaveId:"itd.workspace.nav"}}><SideNavSection title="Объект">{items.map(([key,label,svg])=><SideNavItem key={key} label={label} title={label} icon={glyph(svg)} isSelected={view===key||key==='registry'&&['documents','schemes','resources','incoming','facts','check','delivery'].includes(view)||key==='ojr'&&['journal','cable','work'].includes(view)} onClick={()=>go(key)}/>)}</SideNavSection><SideNavSection title="Инструменты"><SideNavItem label="Все объекты" title="Все объекты" icon={glyph('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>')} isSelected={view==='objects'} onClick={()=>go('objects')}/><AssistantNavItem config={assistant}/><SideNavItem label="Настройки" title="Настройки" isSelected={view==='account'} data-account-open="" icon={glyph('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>')} onClick={()=>document.getElementById('account-open')?.click()}/></SideNavSection></SideNav>;
 mount(shellHost,<WorkspaceShell rail={rail} view={view} assistant={assistant}/>);

 const crumbs=document.getElementById('breadcrumbs');if(crumbs)mount(crumbs,<Breadcrumbs aria-label="Путь страницы">{trail.map((crumb,i)=>i<trail.length-1&&crumb.view?<BreadcrumbItem key={i} onClick={()=>go(crumb.view)}>{crumb.label}</BreadcrumbItem>:<BreadcrumbItem key={i} isCurrent>{crumb.label}</BreadcrumbItem>)}</Breadcrumbs>);schedule();
}
let pending=false;
function schedule(){if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;observer.disconnect();cleanup();adapters.enhance();enhancePrimitives();enhanceTabs();observe();});}
const observer=new MutationObserver(records=>{if(records.some(r=>r.target===document.body?[...r.addedNodes].some(node=>node.matches?.('.workspace-dialog')):!isReactOwned(r.target)))schedule();});
function observe(){observer.observe(document.body,{childList:true});for(const dialog of document.querySelectorAll('.workspace-dialog'))observer.observe(dialog,{childList:true,subtree:true,characterData:true});for(const id of ['content','editor-content','editor-footer','actions','knowledge-results','prompt-content','login-form','notice','editor-notice']){const host=document.getElementById(id);if(host)observer.observe(host,{childList:true,subtree:true,characterData:true});}}
const adapters=createAdapters({mount,primitive,isReactOwned,flush:()=>flushSync(renderIslands)});
const enhanceTable=createTableAdapter(mount);
window.ITDDesign={renderSectionTabs:(host,props)=>mount(host,<SectionTabs {...props}/>),renderManualRecords:(host,props)=>mount(host,<ManualRecords key={props.workspaceId+":"+props.projectId+":"+props.role} {...props}/>),renderWorkflowRecords:(host,props)=>mount(host,<WorkflowRecords key={props.workspaceId+":"+props.projectId+":"+props.role+":"+props.kind} {...props}/>),renderJournalRecords:(host,props)=>mount(host,<JournalRecords key={props.workspaceId+":"+props.projectId+":"+props.role+":"+props.section} {...props}/>),renderNav,enhanceSelect,enhanceTable,renderRegistry:(host,props)=>mount(host,<Registry {...props}/>),renderSourceFiles:(host,props)=>mount(host,<SourceFiles {...props}/>),renderProjectRecords:(host,props)=>mount(host,<ProjectRecords {...props}/>),renderWorkRecords:(host,props)=>mount(host,<WorkRecords key={props.workspaceId+":"+props.projectId+":"+props.role} {...props}/>),refresh:schedule,openDialog:adapters.openDialog,closeDialog:adapters.closeDialog,setLoading:adapters.setLoading};
document.addEventListener('itd:appearance',renderIslands);
observe();schedule();
