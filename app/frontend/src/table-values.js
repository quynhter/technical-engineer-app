export function filterValue(text,type){
 if(type==='number'){
  const value=text.replace(/\s/g,'').replace(',','.');
  return /^[-+]?\d+(\.\d+)?$/.test(value)?Number(value):null;
 }
 if(type==='date'){
  const value=/^\d{2}\.\d{2}\.\d{4}$/.test(text)?text.split('.').reverse().join('-'):text;
  if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return null;
  const date=new Date(value+'T00:00:00');
  return Number.isNaN(date.getTime())?null:date;
 }
 return text;
}

export function installedValue(resource,summary){
 if(resource.qty_fact!=null)return {value:resource.qty_fact,label:'Итог ведомости'};
 if(summary?.confirmed_ids?.length)return {value:summary.confirmed_total,label:'По подтверждённым записям'};
 return {value:null,label:'Не внесено'};
}
export function tableValue(value){
 if(value==null)return 'Не указано';
 if(typeof value==='number'&&Number.isFinite(value))return new Intl.NumberFormat('ru-RU',{maximumFractionDigits:3,useGrouping:false}).format(value);
 return /^\d{4}-\d{2}-\d{2}$/.test(value)?value.split('-').reverse().join('.'):value;
}
