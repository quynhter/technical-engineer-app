import {tableValue} from './table-values.js';
export function findingPresentation(pdata){
const displayTableDate=value=>tableValue(value);
const actName=a=>pdata.forms?.find(f=>f.code===a.act_type)?.name||a.act_type;
function resourceLabel(id){
 const r=pdata.resources.find(r=>r.id===Number(id));
 if(!r)return 'Ресурс недоступен (ID '+id+')';
 const parts=[r.spec_num?'Поз. '+r.spec_num:null,r.name,r.type_mark].filter(Boolean);
 return parts.map((part,index)=>index===parts.length-1?part:String(part).trimEnd().replace(/\.+$/,'')).join('. ');
}
function factLabel(id){
 const f=pdata.workflow.fact_records.find(f=>f.id===Number(id));
 return f?[resourceLabel(f.resource_id),f.work_description,f.location].filter(Boolean).join('. '):'Запись монтажа недоступна (ID '+id+')';
}
function findingDetails(f){
 const labels={resource_id:'Материал / оборудование',resource_ids:'Материалы / оборудование',fact_id:'Монтаж',fact_ids:'Монтаж',act_id:'Акт',release_id:'Файл',attachment_id:'Исходный файл',review_id:'Контроль качества',requirement_id:'Документ комплекта',delivery_id:'Передача',remark_id:'Замечание',pending_ids:'Вопросы по спецификации',fields:'Поля',message:'Описание',confirmed_total:'Подтверждено записями',qty_fact:'Итог ведомости',unit:'Единица',confirmed_ids:'Подтверждённые записи',unknown_quantity_ids:'Монтаж с неизвестным количеством',note:'Пояснение'};
 const find=(rows,id)=>rows?.find(r=>r.id===Number(id));
 const display=(key,id)=>{
  if(['resource_id','resource_ids'].includes(key))return resourceLabel(id);
  if(['fact_id','fact_ids','confirmed_ids','unknown_quantity_ids'].includes(key))return factLabel(id);
  if(key==='act_id'){const a=find(pdata.acts,id);return a?a.act_num+' «'+actName(a)+'»':'Акт недоступен';}
  if(key==='attachment_id')return find(pdata.attachments,id)?.title||'Исходный файл недоступен';
  if(key==='release_id')return find(pdata.releases,id)?.title||'Версия файла недоступна';
  if(key==='requirement_id')return find(pdata.workflow.matrix.requirements,id)?.title||'Документ комплекта недоступен';
  if(key==='delivery_id')return find(pdata.workflow.deliveries,id)?.recipient||'Передача недоступна';
  if(key==='remark_id')return find(pdata.workflow.remarks,id)?.description||'Замечание недоступно';
  if(key==='review_id'){const q=find(pdata.quality_reviews,id);return q?[resourceLabel(q.resource_id),q.checked_date,q.checked_by].filter(Boolean).join('. '):'Проверка недоступна';}
  if(key==='supply_id'){const s=find(pdata.manual?.supplies,id);return s?[resourceLabel(s.resource_id),s.batch_num,s.supply_date].filter(Boolean).join('. '):'Поставка недоступна';}
  if(key==='entry_id')return find(pdata.workspace_entries,id)?.title||'Запись работ недоступна';
  return typeof id==='object'?JSON.stringify(id):id??'Неизвестно';
 };
 return Object.entries(f).filter(([k])=>k!=='code').map(([k,v])=>(labels[k]||({supply_id:'Поставка',entry_id:'Работа'})[k]||k)+': '+(Array.isArray(v)?v.map(id=>display(k,id)).join('; '):display(k,v))).join('. ');
}
function findingDestination(code){
 if(code==='requirements_not_configured'||code.startsWith('requirement_'))return ['requirements','Состав комплекта'];
 if(code==='open_remark')return ['delivery','Замечания'];
 if(code.startsWith('quality_')||code==='work_supply_invalid'||code==='supply_overallocated')return ['incoming','Входной контроль'];
 if(code.startsWith('fact_')||code.startsWith('facts_')||code==='qty_fact_unknown'||code==='specification_pending')return ['resources','Ресурсы и монтаж'];
 return ['documents','Документы'];
}
return {findingDetails,findingDestination,resourceLabel};
}
export function findingResource(f,project){return f.resource_id||(f.resource_ids||[])[0]||project.workflow.fact_records.find(item=>item.id===Number(f.fact_id||(f.fact_ids||[])[0]))?.resource_id;}
