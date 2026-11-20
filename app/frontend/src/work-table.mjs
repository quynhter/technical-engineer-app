import {tableValue} from './table-values.js';

export const workLabels=['Дата','Наименование работы','Описание','Использованные ресурсы','Условия','Количество','Единица измерения','Ответственный','Акт','Источник'];
export function workSources(entry,project){
 return {act:entry.act_id?String(project.acts?.find(act=>act.id===entry.act_id)?.act_num||entry.act_id):null,
  attachment:entry.attachment_id?(project.attachments?.find(file=>file.id===entry.attachment_id)?.title||'Архивный документ'):null};
}
export function workValues(entry,project){
 const sources=workSources(entry,project);
 const materials=(project.work_materials||[]).filter(item=>item.entry_id===entry.id).map(item=>(project.resources?.find(resource=>resource.id===item.resource_id)?.name||'Ресурс')+'. '+tableValue(item.quantity)+' '+(item.unit||'')).join('; ');
 return [entry.entry_date?tableValue(entry.entry_date):'Не указана',entry.title||'',entry.details||'',materials,
  entry.conditions||'',entry.quantity!=null?tableValue(entry.quantity):'',entry.unit||'',entry.responsible_display||entry.responsible||'Не указан',
  sources.act||'Не сформирован',sources.attachment||'Не указан'];
}
export function workSearch(entry,project){return workValues(entry,project).join(' ').toLocaleLowerCase('ru').replaceAll('ё','е');}
export function workRows(project,{unbound=false,from='',to='',query=''}={}){
 const term=query.trim().toLocaleLowerCase('ru').replaceAll('ё','е');
 return (project.workspace_entries||[]).filter(entry=>entry.kind==='work'&&(!unbound||!entry.act_id)&&(!from||entry.entry_date&&entry.entry_date>=from)&&(!to||entry.entry_date&&entry.entry_date<=to)&&(!term||workSearch(entry,project).includes(term))).sort((a,b)=>(b.entry_date||'').localeCompare(a.entry_date||'')||b.id-a.id);
}
export function workCsv(entries,project){return '\ufeff'+[workLabels,...entries.map(entry=>workValues(entry,project))].map(row=>row.map(value=>'"'+String(value??'').replace(/^[=+\-@\t\r]/,"'$&").replaceAll('"','""')+'"').join(';')).join('\r\n');}
