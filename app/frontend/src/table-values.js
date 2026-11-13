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
