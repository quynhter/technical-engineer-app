"""Authenticated chat routes; SSE observes durable state and owns no generation task."""
import asyncio
import json

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

from .assistant_files import AttachmentError, MAX_BYTES
from .assistant_runtime import Runtime
from . import llm, tools
from .services.context import Actor
from .services.permissions import require
from .services import providers


def install(app, state):
    from .http_api import check_site, request_credentials, authenticate, context, failure, SECURITY_HEADERS
    runtime = Runtime(state.accounts)
    app.state.assistant_runtime = runtime

    def principal(token, bearer, workspace_id):
        user = authenticate(state,token,bearer=bearer)
        if user['workspace_id'] != workspace_id:
            raise PermissionError('Рабочее пространство изменилось')
        return Actor(user_id=user['id'],role=user['role'],source='assistant',on_behalf_of=user['id'])

    def prepare(request):
        check_site(request)
        token,bearer = request_credentials(request)
        with state.workspace_scope(write=False) as database:
            ctx = context(state,database)
            workspace_id = state.workspace_id
        return ctx, principal(token,bearer,workspace_id), lambda:principal(token,bearer,workspace_id)

    async def handle(request: Request):
        try:
            ctx,actor,refresh = await run_in_threadpool(prepare,request)
            route = request.url.path.rsplit('/',1)[-1]
            if request.method=='GET':
                if route=='assistants':
                    result = await run_in_threadpool(runtime.chats.assistants,actor)
                    configured = llm.profiles(runtime.provider_path)
                    result = [a for a in result if a['provider'] in configured]
                    result = [{k:v for k,v in a.items() if k not in ('instruction',)} for a in result]
                elif route=='admin':
                    require(actor,'admin')
                    result = {'assistants':await run_in_threadpool(runtime.chats.assistants,actor,admin=True),
                              'providers':list(llm.profiles(runtime.provider_path)),
                              'provider_profiles':providers.settings(actor,runtime.provider_path),
                              'provider_presets':[{'name':n,'protocol':p[0],'base_url':p[1]} for n,p in llm.PRESETS.items()],
                              'tools':[{'name':t.name,'description':t.description} for t in tools.TOOLS]}
                elif route=='threads':
                    result = await run_in_threadpool(runtime.chats.threads,ctx,actor)
                elif route=='thread':
                    result = await run_in_threadpool(runtime.chats.history,ctx,actor,int(request.query_params['thread_id']))
                elif route=='events':
                    tid,mid = int(request.query_params['thread_id']),int(request.query_params['message_id'])
                    await run_in_threadpool(runtime.chats.thread,ctx,actor,tid)
                    async def events():
                        previous = None
                        while True:
                            try:
                                current = await run_in_threadpool(refresh)
                                history = await run_in_threadpool(runtime.chats.history,ctx,current,tid)
                                message = next(m for m in history['messages'] if m['id']==mid)
                            except Exception:
                                yield 'event: error\ndata: {"error":"Чат недоступен"}\n\n'
                                return
                            value = json.dumps(message,ensure_ascii=False)
                            if value!=previous:
                                yield 'id: '+str(len(message['events']))+'\nevent: snapshot\ndata: '+value+'\n\n'
                                previous = value
                            if message['status']!='running':
                                return
                            await asyncio.sleep(0.15)
                    return StreamingResponse(events(),media_type='text/event-stream',headers={**SECURITY_HEADERS,'X-Accel-Buffering':'no'})
                else:
                    raise ValueError('Маршрут не найден')
            else:
                if request.headers.get('content-type','').split(';')[0]!='application/json':
                    raise ValueError('Требуется JSON')
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > (MAX_BYTES * 4 // 3 + 160000 if route == 'messages' else 64000):
                        raise ValueError('Запрос слишком большой')
                data = json.loads(body)
                if not isinstance(data,dict):
                    raise ValueError('Требуется объект')
                if route=='provider':
                    result = await run_in_threadpool(providers.save,actor,runtime.provider_path,data)
                elif route=='config':
                    result = await run_in_threadpool(runtime.chats.save,actor,data,llm.profiles(runtime.provider_path))
                elif route=='threads':
                    result = await run_in_threadpool(runtime.chats.create,ctx,actor,data)
                elif route=='messages':
                    result = await runtime.start(ctx,actor,data,refresh)
                elif route=='cancel':
                    result = await runtime.cancel(ctx,actor,data.get('thread_id'))
                elif route=='thread-title':
                    result = await run_in_threadpool(runtime.chats.rename,ctx,actor,data.get('thread_id'),data.get('title'))
                elif route=='thread-delete':
                    result = await run_in_threadpool(runtime.chats.delete,ctx,actor,data.get('thread_id'))
                else:
                    raise ValueError('Маршрут не найден')
            return JSONResponse(result,headers=SECURITY_HEADERS)
        except AttachmentError as error:
            return JSONResponse({'error':{'code':'attachment_error','message':str(error)}},status_code=400,headers=SECURITY_HEADERS)
        except Exception as error:
            # Pydantic and provider errors may contain input values. Keep them out of responses/logs.
            if isinstance(error,PermissionError):
                from .accounts import SessionExpired
                if isinstance(error,SessionExpired):
                    return failure(request,error)
                return failure(request,PermissionError('Чат недоступен'))
            return JSONResponse({'error':{'code':'assistant_error','message':'Не удалось выполнить действие. Проверьте настройки и доступ.'}},status_code=400,headers=SECURITY_HEADERS)

    for route in ('assistants','assistant/admin','assistant/threads','assistant/thread','assistant/events'):
        app.add_api_route('/api/v1/'+route,handle,methods=['GET'])
    for route in ('provider','config','threads','messages','cancel','thread-title','thread-delete'):
        app.add_api_route('/api/v1/assistant/'+route,handle,methods=['POST'])
    return runtime
