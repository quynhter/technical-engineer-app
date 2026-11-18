export class ApiError extends Error{
 constructor(message,{status=0,code,fields,unknownResult=false}={}){super(message);this.name='ApiError';Object.assign(this,{status,code,fields,unknownResult});}
}
export function saveFile({blob,filename}){
 const url=URL.createObjectURL(blob),anchor=document.createElement('a');
 anchor.href=url;anchor.download=filename;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export function createApiClient({getToken,fetchImpl=globalThis.fetch,onSessionExpired=()=>{}}){
 async function request(path,data,{signal,binary=false,filename}={}){
  if(!path.startsWith('/')||path.startsWith('//'))throw Error('Недопустимый путь API');
  const controller=new AbortController(),forward=()=>controller.abort(signal.reason);
  if(signal?.aborted)forward();else signal?.addEventListener('abort',forward,{once:true});
  const timer=setTimeout(()=>controller.abort(),data===undefined?30000:120000);
  try{
   let response;
   try{response=await fetchImpl('/api/v1'+path,{method:data===undefined?'GET':'POST',headers:{'X-ITD-Token':getToken(),...(data===undefined?{}:{'Content-Type':'application/json'})},body:data===undefined?undefined:JSON.stringify(data),signal:controller.signal});}
   catch(error){if(signal?.aborted)throw error;throw new ApiError(data===undefined?'Не удалось получить ответ сервера. Повторите загрузку.':'Результат операции неизвестен. Проверьте данные перед повторной отправкой.',{unknownResult:data!==undefined});}
   if(!response.ok){const value=await response.json().catch(()=>({}));if(response.status===403&&value.session_expired)onSessionExpired();throw new ApiError(value.error?.message||value.error||'Не удалось выполнить запрос',{status:response.status,code:value.error?.code,fields:value.fields});}
   if(!binary)return await response.json();
   const encoded=response.headers.get('Content-Disposition')?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
   if(!filename&&encoded){try{filename=decodeURIComponent(encoded);}catch(_){/* Keep the safe fallback. */}}
   return {blob:await response.blob(),filename:(filename||'Документ').split(/[\\/]/).pop()||'Документ'};
  }catch(error){
   if(error instanceof ApiError||signal?.aborted)throw error;
   throw new ApiError(data===undefined?'Не удалось получить ответ сервера. Повторите загрузку.':'Результат операции неизвестен. Проверьте данные перед повторной отправкой.',{unknownResult:data!==undefined});
  }finally{clearTimeout(timer);signal?.removeEventListener('abort',forward);}
 }
 return {json:(path,data,options)=>request(path,data,options),download:(path,options)=>request(path,undefined,{...options,binary:true})};
}
