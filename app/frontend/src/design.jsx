import {createAdapters} from './adapters.jsx';
import {createPortal,flushSync} from 'react-dom';
import {createTableAdapter} from './astryx-tables.jsx';
import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Theme} from '@astryxdesign/core/theme';
import {stoneTheme} from '@astryxdesign/theme-stone/built';
import {matchaTheme} from '@astryxdesign/theme-matcha/built';
import {butterTheme} from '@astryxdesign/theme-butter/built';
import {gothicTheme} from '@astryxdesign/theme-gothic/built';
import {y2kTheme} from '@astryxdesign/theme-y2k/built';
import {neutralTheme} from '@astryxdesign/theme-neutral/built';
import {InternationalizationProvider} from '@astryxdesign/core/i18n';
import {AppShell,TopNav,TopNavHeading,Selector,SideNav,SideNavItem,SideNavSection,Button,TabList,Tab,Pagination,Breadcrumbs,BreadcrumbItem,Dialog,DialogHeader,TextInput,EmptyState,Kbd,DropdownMenu,Heading} from '@astryxdesign/core';
import ru from '@astryxdesign/core/locales/ru-RU.json';
import recipes from './primitives.json';

import '@astryxdesign/core/reset.css';
import '@astryxdesign/core/astryx.css';
import '@astryxdesign/theme-neutral/theme.css';
import '@astryxdesign/theme-stone/theme.css';
import '@astryxdesign/theme-matcha/theme.css';
import '@astryxdesign/theme-butter/theme.css';
import '@astryxdesign/theme-gothic/theme.css';
import '@astryxdesign/theme-y2k/theme.css';

import './workspace.css';
const islands=new Map();
const themes={neutral:neutralTheme,stone:stoneTheme,matcha:matchaTheme,butter:butterTheme,gothic:gothicTheme,y2k:y2kTheme};
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
  if(isReactOwned(button)||button.matches('.swatch,.brand,.account-avatar,.object-tile,.journal-task,.cell-open,.record-name,.journey-link,.link-button,.table-sort,.table-chip')||button.closest('.org-list,.tabs,.panel-nav,.journal-sections'))continue;
  primitive(button,'button-'+(button.classList.contains('danger')?'destructive':button.classList.contains('ghost')?'ghost':button.classList.contains('secondary')?'secondary':'primary'));
 }
 for(const [selector,key] of [['.card:not(details)','card'],['.pill','badge'],['.table-scroll table','table']])document.querySelectorAll(selector).forEach(node=>{if(!isReactOwned(node))primitive(node,key);});
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
  const items=buttons.map((b,i)=>({label:b.textContent.trim(),value:String(i),selected:b.classList.contains('active')||b.hasAttribute('aria-current'),attrs:Object.fromEntries([...b.attributes].filter(a=>a.name.startsWith('data-')&&!['data-primitive','data-variant','data-size','data-elevation','data-astryx-pressable'].includes(a.name)).map(a=>[a.name,a.value]))}));
  function Tabs(){const [value,setValue]=useState(items.find(x=>x.selected)?.value||'0');return <TabList value={value} onChange={setValue} size="lg" hasDivider aria-label={host.getAttribute('aria-label')||'Разделы'}>{items.map(item=><Tab key={item.value} value={item.value} label={item.label} {...item.attrs}/>)}</TabList>;}
  host.replaceChildren();mount(host,<Tabs/>);
 }
}
let navigation=[],navigate=()=>{};
function glyph(markup){return <span className="nav-glyph" aria-hidden="true" dangerouslySetInnerHTML={{__html:markup}}/>;}
const legacyNodes=['.context','#breadcrumbs','main'].map(sel=>document.querySelector(sel)).filter(Boolean);
const oldHeader=document.querySelector('.topbar');if(oldHeader){oldHeader.hidden=true;oldHeader.id='legacy-controls';}
const oldNav=document.getElementById('steps');if(oldNav)oldNav.hidden=true;
const shellHost=document.createElement('div');shellHost.id='shell-root';document.body.prepend(shellHost);
const workspaceStatus=document.getElementById('workspace-status'),statusSlots=new Set();
const statusParking=document.createElement('div');statusParking.hidden=true;document.body.append(statusParking);if(workspaceStatus)statusParking.append(workspaceStatus);
function WorkspaceStatus(){const ref=React.useRef(null);React.useLayoutEffect(()=>{const slot=ref.current;statusSlots.add(slot);if(workspaceStatus)slot.append(workspaceStatus);return()=>{statusSlots.delete(slot);if(workspaceStatus?.parentElement===slot){const next=[...statusSlots].find(node=>node.isConnected);(next||statusParking).append(workspaceStatus);}};},[]);return <div className="nav-status" data-native-content="" ref={ref}/>;}
function LegacyContent(){const ref=React.useRef(null);React.useLayoutEffect(()=>{if(ref.current)ref.current.append(...legacyNodes);},[]);return <div className="workspace-content" ref={ref}/>;}
function changeTheme(value){selectedTheme=value;try{localStorage.setItem('itd.design.theme',value);}catch(_){}document.dispatchEvent(new Event('itd:appearance'));}
const accountNodes=['account-open','session-resume'].map(id=>document.getElementById(id)).filter(Boolean);
const accountParking=document.getElementById('legacy-controls')||document.body;
function AccountControl(){
 const ref=React.useRef(null),[avatar,setAvatar]=useState({html:'',label:'Профиль'});
 React.useLayoutEffect(()=>{const source=accountNodes.find(node=>node.id==='account-open');if(!source)return;const slot=ref.current;slot.append(...accountNodes);const sync=()=>setAvatar({html:source.innerHTML,label:source.getAttribute('aria-label')||'Профиль'});const observer=new MutationObserver(sync);observer.observe(source,{childList:true,subtree:true,attributes:true,attributeFilter:['aria-label']});sync();return()=>{observer.disconnect();for(const node of accountNodes)if(node.parentElement===slot)accountParking.append(node);};},[]);
 function profile(section){document.getElementById('account-open')?.click();if(!section)return;const content=document.getElementById('account-content');const focus=()=>{const target=content?.querySelector(section);if(!target)return false;target.scrollIntoView({block:'start'});return true;};if(!focus()&&content){const observer=new MutationObserver(()=>{if(focus())observer.disconnect();});observer.observe(content,{childList:true,subtree:true});setTimeout(()=>observer.disconnect(),5000);}}
 const items=[{label:'Настройки профиля',onClick:()=>profile()},...(document.body.dataset.role==='admin'?[{label:'Пользователи',onClick:()=>profile('[data-account-action="role"]')},{label:'Локальные данные',onClick:()=>profile('[data-account-action="settings"]')}]:[]),{type:'divider'},{label:'База знаний',onClick:()=>document.getElementById('knowledge-open')?.click()}];
 return <div className="account-control"><div className="profile-source" ref={ref}/><DropdownMenu items={items} alignment="end" renderTrigger={props=><Button {...props} label={avatar.label} icon={<span dangerouslySetInnerHTML={{__html:avatar.html}}/>} isIconOnly className="account-avatar" variant="ghost"/>}/></div>;
}
function SectionSearch(){return <Button className="workspace-search-button" label="Найти раздел" icon={glyph('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg>')} endContent={<Kbd keys="mod+k"/>} variant="secondary" onClick={()=>document.dispatchEvent(new Event('itd:search'))}/>;}
function Header(){const [,redraw]=useState(0);React.useEffect(()=>{const refresh=()=>redraw(n=>n+1);document.addEventListener('itd:appearance',refresh);return()=>document.removeEventListener('itd:appearance',refresh);},[]);return <TopNav label="ИТД" heading={<TopNavHeading heading="ИТД" logo={<img src="/logo.svg" alt="" width="30" height="30"/>}/>} centerContent={<SectionSearch/>} endContent={<div className="header-actions"><Selector label="Тема оформления" isLabelHidden variant="ghost" value={selectedTheme} options={Object.keys(themes).map(value=>({value,label:({neutral:'Neutral',stone:'Stone',matcha:'Matcha',butter:'Butter',gothic:'Gothic',y2k:'Y2K'})[value]}))} onChange={changeTheme}/><Button label={document.documentElement.dataset.theme==='dark'?'Светлая тема':'Тёмная тема'} variant="ghost" onClick={()=>document.getElementById('theme-toggle')?.click()}/><AccountControl/></div>}/>;}
function WorkspaceShell({rail,view}){const [isOpen,onOpenChange]=useState(false);React.useEffect(()=>onOpenChange(false),[view]);return <AppShell variant="section" contentPadding={0} topNav={<Header/>} sideNav={rail} mobileNav={{breakpoint:'md',isOpen,onOpenChange}}><LegacyContent/></AppShell>;}
function renderNav(items,view,go){
 navigation=items;navigate=go;
 const rail=<SideNav className="workspace-nav" aria-label="Рабочее пространство" footer={<WorkspaceStatus/>} resizable={{defaultWidth:244,minWidth:220,maxWidth:340}}><SideNavSection title="Объект">{items.map(([key,label,svg])=><SideNavItem key={key} label={label} title={label} icon={glyph(svg)} isSelected={view===key||key==='registry'&&['documents','schemes','resources','ojr','journal','work','incoming','facts','check','delivery'].includes(view)} onClick={()=>go(key)}/>)}</SideNavSection><SideNavSection title="Инструменты"><SideNavItem label="Все объекты" isSelected={view==='objects'} onClick={()=>go('objects')}/><SideNavItem label="База знаний" onClick={()=>document.getElementById('knowledge-open')?.click()}/></SideNavSection></SideNav>;
 mount(shellHost,<WorkspaceShell rail={rail} view={view}/>);
 const label=items.find(([key])=>key===view)?.[1]||({objects:'Все объекты',resources:'Ресурсы',ojr:'Общий журнал работ',journal:'Журналы',check:'Проверка',delivery:'Сдача',work:'Работы',incoming:'Входной контроль'})[view]||'Исполнительная документация';
 const crumbs=document.getElementById('breadcrumbs');if(crumbs)mount(crumbs,<Breadcrumbs aria-label="Путь страницы"><BreadcrumbItem onClick={()=>go('objects')}>Объекты</BreadcrumbItem><BreadcrumbItem isCurrent>{label}</BreadcrumbItem></Breadcrumbs>);schedule();
}
function CommandPalette(){
 const [open,setOpen]=useState(false),[query,setQuery]=useState('');
 React.useEffect(()=>{const show=()=>{setQuery('');setOpen(true);};const key=e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();show();}};document.addEventListener('keydown',key);document.addEventListener('itd:search',show);return()=>{document.removeEventListener('keydown',key);document.removeEventListener('itd:search',show);};},[]);
 const items=navigation.filter(([,label])=>label.toLocaleLowerCase('ru').includes(query.toLocaleLowerCase('ru')));
 return <Dialog isOpen={open} onOpenChange={setOpen} width={560} padding={0} aria-label="Быстрый переход"><div className="command-content"><DialogHeader className="command-header" hasDivider={false} title="Быстрый переход" onOpenChange={setOpen}/><TextInput label="Найти раздел" isLabelHidden value={query} onChange={setQuery} placeholder="Объект, участники, документация…" size="lg"/><div className="command-results">{items.map(([key,label,svg])=><Button key={key} label={label} icon={glyph(svg)} variant="ghost" width="100%" onClick={()=>{setOpen(false);navigate(key);}}/>)}{!items.length&&<EmptyState title="Ничего не найдено" description="Попробуйте другое название раздела."/>}</div><div className="command-shortcuts"><span><Kbd keys="escape"/> Закрыть</span><span aria-hidden="true">·</span><span><Kbd keys="mod+k"/> Открыть</span></div></div></Dialog>;
}
let pending=false;
function schedule(){if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;observer.disconnect();cleanup();adapters.enhance();enhancePrimitives();enhanceTabs();observe();});}
const observer=new MutationObserver(records=>{if(records.some(r=>!isReactOwned(r.target)))schedule();});
function observe(){for(const id of ['content','editor-content','editor-footer','actions','knowledge-results','account-content','prompt-content','login-form','notice','editor-notice']){const host=document.getElementById(id);if(host)observer.observe(host,{childList:true,subtree:true,characterData:true});}}
const adapters=createAdapters({mount,primitive,isReactOwned,flush:()=>flushSync(renderIslands)});
const enhanceTable=createTableAdapter(mount);
window.ITDDesign={renderNav,enhanceSelect,enhanceTable,refresh:schedule,openDialog:adapters.openDialog,closeDialog:adapters.closeDialog,setLoading:adapters.setLoading};
document.addEventListener('itd:appearance',renderIslands);
mount(document.getElementById('command-root'),<CommandPalette/>);observe();schedule();
