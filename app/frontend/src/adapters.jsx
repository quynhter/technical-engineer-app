import React,{useEffect,useLayoutEffect,useRef,useState} from 'react';
import {Banner,ClickableCard,Collapsible,DateInput,Dialog,Skeleton} from '@astryxdesign/core';

// These slots retain business DOM, listeners, validation and native FormData.
export function NativeContent({nodes,version}){
 const ref=useRef(null);
 useLayoutEffect(()=>{if(ref.current)ref.current.append(...nodes);},[nodes,version]);
 return <div data-native-content="" ref={ref}/>;
}
export function createAdapters({mount,primitive,isReactOwned,flush}){
 const dates=new WeakMap(),cards=new WeakSet(),banners=new WeakMap(),dialogs=new WeakMap();
 function fieldLabel(input){return input.getAttribute('aria-label')||input.labels?.[0]?.querySelector('span')?.textContent||input.labels?.[0]?.textContent||input.placeholder||'Дата';}
 function unnestLabel(input){const owner=input.closest('label.field');if(!owner)return;const field=document.createElement('div');for(const a of owner.attributes)if(a.name!=='for')field.setAttribute(a.name,a.value);field.append(...owner.childNodes);owner.replaceWith(field);}
 function NativeDate({input}){
  const [value,setValue]=useState(input.value||undefined),[disabled,setDisabled]=useState(input.disabled),ref=useRef(null);
  useEffect(()=>{const sync=()=>{setValue(input.value||undefined);setDisabled(input.disabled);};const observer=new MutationObserver(sync);observer.observe(input,{attributes:true,attributeFilter:['disabled','value','readonly','min','max']});input.addEventListener('change',sync);input.addEventListener('smart-sync',sync);const focus=input.focus;input.focus=()=>ref.current?.focus();return()=>{observer.disconnect();input.removeEventListener('change',sync);input.removeEventListener('smart-sync',sync);input.focus=focus;};},[input]);
  return <DateInput ref={ref} label={input.getAttribute('aria-label')} isLabelHidden value={value} min={input.min||undefined} max={input.max||undefined} isDisabled={disabled||input.readOnly} size="md" width="100%" format={iso=>iso.split('-').reverse().join('.')} onChange={next=>{input.value=next||'';setValue(next);input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));}}/>;
 }
 function enhanceFields(){
  for(const input of document.querySelectorAll('input:not([type=hidden],[type=checkbox],[type=radio],[type=file]),textarea')){
   if(isReactOwned(input)||input.hidden)continue;
   if(input.type==='date'){
    input.setAttribute('aria-label',fieldLabel(input).trim());unnestLabel(input);input.hidden=true;input.tabIndex=-1;input.setAttribute('aria-hidden','true');const host=document.createElement('div');host.className='date-island';host._nativeInput=input;input.after(host);dates.set(input,host);mount(host,<NativeDate input={input}/>);continue;
   }
   const multiline=input.tagName==='TEXTAREA';
   if(!input.parentElement.classList.contains('itd-field-control')){
    const wrapper=document.createElement('div');wrapper.className='itd-field-control';input.before(wrapper);wrapper.append(input);primitive(wrapper,multiline?'textarea-wrapper':'input-wrapper');
   }
   primitive(input,multiline?'textarea':'input');
  }
 }
 function enhanceCards(){for(const source of document.querySelectorAll('button.object-tile,button.journal-task')){
  if(cards.has(source)||isReactOwned(source))continue;cards.add(source);const content=source.cloneNode(true);if(source.classList.contains('object-tile'))content.querySelector('.tile-icon')?.remove();source.hidden=true;const host=document.createElement('div');host.className='clickable-card-host';source.after(host);
  mount(host,<ClickableCard label={source.querySelector('strong')?.textContent||source.textContent.trim()} padding={4} variant="bordered" width="100%" onClick={()=>source.click()}><div className="clickable-card-content" dangerouslySetInnerHTML={{__html:content.innerHTML}}/></ClickableCard>);
 }}
 function enhanceDisclosures(){for(const source of document.querySelectorAll('details:not(.agent-help,.help-tip)')){
  if(isReactOwned(source)||source.closest('.astryx-data-view')||source.querySelector(':scope > summary button,:scope > summary input'))continue;
  const summary=source.querySelector(':scope > summary');if(!summary)continue;
  const nodes=[...source.childNodes].filter(node=>node!==summary),host=document.createElement('div');for(const attr of source.attributes)if(attr.name!=='open')host.setAttribute(attr.name,attr.value);host.dataset.disclosure='';host.classList.add('disclosure-adapter');let open=source.open;
  source.replaceWith(host);
  const render=()=>mount(host,<Collapsible trigger={summary.textContent.trim()} isOpen={open} onOpenChange={value=>{host.open=value;}} density="compact"><NativeContent nodes={nodes}/></Collapsible>);
  Object.defineProperty(host,'open',{get:()=>open,set:value=>{open=Boolean(value);render();host.dispatchEvent(new Event('toggle'));}});render();
 }}
 function enhanceBanners(){for(const source of document.querySelectorAll('#notice,#editor-notice,.account-message')){
  const message=source.textContent.trim();let entry=banners.get(source);
  if(!entry){const host=document.createElement('div');host.className='banner-slot';source.after(host);source.hidden=true;entry={host};banners.set(source,entry);}
  if(entry.message===message)continue;entry.message=message;entry.host.hidden=!message;if(message)mount(entry.host,<Banner status={/ошиб|не удалось|недопуст|нельзя|не ответил/i.test(message)?'error':/сохран|обновлен|скопир/i.test(message)?'success':'info'} title={message} container="card"/>);
 }}
 function DialogBridge({source,open}){const nodes=useRef([source]),scroll=useRef(null);useLayoutEffect(()=>{if(open&&scroll.current)scroll.current.scrollTop=0;},[open]);return <Dialog className="itd-dialog" isOpen={open} onOpenChange={value=>{if(!value)source.dispatchEvent(new Event('cancel',{cancelable:true}));}} width={source.classList.contains('workspace-dialog--wide')?1080:source.classList.contains('workspace-dialog--settings')?620:source.classList.contains('workspace-dialog--compact')?460:840} maxHeight="90dvh" padding={0} purpose="form" aria-labelledby={source.getAttribute('aria-labelledby')}><div className="dialog-scroll-content" ref={scroll}><NativeContent nodes={nodes.current} version={open}/></div></Dialog>;}
 function openDialog(source){
  let entry=dialogs.get(source);if(!entry){const anchor=document.createComment('workspace dialog'),host=document.createElement('div');source.before(anchor,host);entry={anchor,host};dialogs.set(source,entry);source.classList.add('dialog-bridge-source');source.setAttribute('role','presentation');source.setAttribute('aria-modal','false');}
  source.setAttribute('open','');mount(entry.host,<DialogBridge source={source} open/>);flush();
 }
 function closeDialog(source){const entry=dialogs.get(source);if(!entry)return false;source.removeAttribute('open');entry.anchor.after(source);mount(entry.host,<DialogBridge source={source} open={false}/>);source.dispatchEvent(new Event('close'));return true;}
 function setLoading(active,target=document.getElementById('content')){
  if(!target)return;let host=target.previousElementSibling;if(!host?.classList.contains('loading-skeleton')){host=document.createElement('div');host.className='loading-skeleton';host.setAttribute('role','status');host.setAttribute('aria-label','Загрузка');target.before(host);}
  host.hidden=!active;target.setAttribute('aria-busy',String(active));if(active)mount(host,<><Skeleton width="45%" height={24}/><Skeleton width="75%" height={16}/><Skeleton width="100%" height={80}/></>);
 }
 return {enhance(){enhanceDisclosures();enhanceCards();enhanceFields();enhanceBanners();},openDialog,closeDialog,setLoading};
}
