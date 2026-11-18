import test from 'node:test';
import assert from 'node:assert/strict';
import {createApiClient} from '../src/api-v1.mjs';

test('v1 requests use the current session, parse errors and never retry writes',async()=>{
 const calls=[];let token='first',expired=0;
 const api=createApiClient({getToken:()=>token,onSessionExpired:()=>expired++,fetchImpl:async(path,options)=>{
  calls.push({path,options});return {ok:false,status:403,json:async()=>({error:{code:'session_expired',message:'Войдите снова'},session_expired:true})};
 }});
 await assert.rejects(api.json('/registry/export',{project_id:7}),error=>error.code==='session_expired'&&error.message==='Войдите снова');
 assert.equal(expired,1);assert.equal(calls.length,1);assert.equal(calls[0].path,'/api/v1/registry/export');assert.equal(calls[0].options.method,'POST');
 token='second';await assert.rejects(api.json('/project?project_id=7'));assert.equal(calls[1].options.headers['X-ITD-Token'],'second');
 const unknown=createApiClient({getToken:()=>token,fetchImpl:async()=>{throw Error('offline');}});
 await assert.rejects(unknown.json('/registry/export',{project_id:7}),error=>error.unknownResult&&error.message.includes('Проверьте данные'));
 const truncated=createApiClient({getToken:()=>token,fetchImpl:async()=>({ok:true,json:async()=>{throw SyntaxError('truncated response');}})});
 await assert.rejects(truncated.json('/registry/export',{project_id:7}),error=>error.unknownResult&&error.message.includes('Проверьте данные'));
});

test('v1 file downloads preserve the server filename and ignore unsafe API paths',async()=>{
 const blob=new Blob(['docx']);const api=createApiClient({getToken:()=>'',fetchImpl:async()=>({ok:true,headers:new Headers({'Content-Disposition':"attachment; filename*=UTF-8''"+encodeURIComponent('Акт № 2.docx')}),blob:async()=>blob})});
 const file=await api.download('/download?project_id=7&release_id=2');assert.equal(file.blob,blob);assert.equal(file.filename,'Акт № 2.docx');
 const zip=await api.download('/package?project_id=7',{filename:'ИТД — актуальные файлы.zip'});assert.equal(zip.filename,'ИТД — актуальные файлы.zip');
 await assert.rejects(api.json('//other.test/api'));await assert.rejects(api.json('https://other.test'));
});
