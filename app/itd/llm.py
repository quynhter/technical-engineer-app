"""Server-only provider profiles and streaming adapters. Never log bodies or credentials."""
import json
import os
from pathlib import Path
from urllib.parse import quote, urlsplit
import uuid

import httpx2

PRESETS = {
    'openai': ('chat','https://api.openai.com/v1','OPENAI_API_KEY'),
    'anthropic': ('anthropic','https://api.anthropic.com/v1','ANTHROPIC_API_KEY'),
    'gemini': ('gemini','https://generativelanguage.googleapis.com/v1beta','GEMINI_API_KEY'),
    'deepseek': ('chat','https://api.deepseek.com/v1','DEEPSEEK_API_KEY'),
    'groq': ('chat','https://api.groq.com/openai/v1','GROQ_API_KEY'),
    'openrouter': ('chat','https://openrouter.ai/api/v1','OPENROUTER_API_KEY'),
    'xai': ('chat','https://api.x.ai/v1','XAI_API_KEY'),
    'mistral': ('chat','https://api.mistral.ai/v1','MISTRAL_API_KEY'),
    'ollama': ('chat','http://127.0.0.1:11434/v1','OLLAMA_API_KEY'),
}


def profiles(saved_path=None):
    configured = {name:{'protocol':protocol,'base_url':url,'api_key_env':env}
                  for name,(protocol,url,env) in PRESETS.items()}
    path = os.environ.get('ITD_LLM_CONFIG')
    if path:
        configured.update(json.loads(Path(path).read_text()))
    saved_path = Path(saved_path) if saved_path else Path(__file__).resolve().parents[2] / 'db/llm-providers.json'
    if saved_path.exists():
        configured.update(json.loads(saved_path.read_text()))
    result = {}
    for name,p in configured.items():
        if not isinstance(p,dict) or p.get('protocol') not in ('chat','anthropic','gemini'):
            raise ValueError('Проверьте серверную конфигурацию LLM')
        url = urlsplit(p.get('base_url',''))
        if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('Проверьте адрес провайдера')
        key = p.get('api_key') or os.environ.get(p.get('api_key_env',''), '')
        if key or p.get('allow_anonymous') is True:
            result[name] = {**p,'api_key':key}
    return result


def request(profile, model, system, history, tools):
    protocol = profile['protocol']
    definitions = [{'name':t.name,'description':t.description,'parameters':t.schema()} for t in tools]
    headers = {'Content-Type':'application/json'}
    key = profile['api_key']
    if protocol == 'chat':
        if key:
            headers['Authorization'] = 'Bearer '+key
        messages = [{'role':'system','content':system}]
        for message in history:
            value = {'role':message['role'],'content':message.get('content','')}
            if message.get('calls'):
                value['tool_calls'] = [{'id':c['id'],'type':'function','function':{'name':c['name'],'arguments':json.dumps(c['arguments'],ensure_ascii=False)}} for c in message['calls']]
                if message['calls'][0].get('reasoning_content'):
                    value['reasoning_content'] = message['calls'][0]['reasoning_content']
            if message['role']=='tool':
                value['tool_call_id'] = message['call_id']
            messages.append(value)
        body = {'model':model,'messages':messages,'stream':True}
        if definitions:
            body['tools'] = [{'type':'function','function':d} for d in definitions]
        return '/chat/completions', headers, body
    if protocol == 'anthropic':
        headers.update({'x-api-key':key,'anthropic-version':'2023-06-01'})
        messages = []
        for message in history:
            if message['role']=='tool':
                role, parts = 'user', [{'type':'tool_result','tool_use_id':message['call_id'],'content':message['content']}]
            else:
                role = message['role']
                parts = ([{'type':'text','text':message['content']}] if message.get('content') else [])
                parts += [{'type':'tool_use','id':c['id'],'name':c['name'],'input':c['arguments']} for c in message.get('calls',[])]
            if messages and messages[-1]['role']==role:
                messages[-1]['content'].extend(parts)
            else:
                messages.append({'role':role,'content':parts})
        body = {'model':model,'system':system,'messages':messages,'max_tokens':4096,'stream':True}
        if definitions:
            body['tools'] = [{'name':d['name'],'description':d['description'],'input_schema':d['parameters']} for d in definitions]
        return '/messages',headers,body
    headers['x-goog-api-key'] = key
    contents = []
    for message in history:
        role = 'model' if message['role']=='assistant' else 'user'
        if message['role']=='tool':
            response = {'name':message['name'],'response':{'result':message['content']}}
            if message.get('provider_id'):
                response['id'] = message['provider_id']
            parts = [{'functionResponse':response}]
        else:
            parts = ([{'text':message['content']}] if message.get('content') else [])
            parts += [c.get('raw') or {'functionCall':{'name':c['name'],'args':c['arguments']}} for c in message.get('calls',[])]
        if contents and contents[-1]['role']==role:
            contents[-1]['parts'].extend(parts)
        else:
            contents.append({'role':role,'parts':parts})
    body = {'systemInstruction':{'parts':[{'text':system}]},'contents':contents}
    if definitions:
        body['tools'] = [{'functionDeclarations':[{**{k:v for k,v in d.items() if k!='parameters'},'parametersJsonSchema':d['parameters']} for d in definitions]}]
    return '/models/'+quote(model,safe='')+':streamGenerateContent?alt=sse',headers,body


async def stream(profile, model, system, history, tools):
    endpoint, headers, body = request(profile, model, system, history, tools)
    calls = {}
    reasoning = ''
    finished = False
    async with httpx2.AsyncClient(timeout=httpx2.Timeout(120,connect=15), follow_redirects=False, trust_env=False) as client:
        async with client.stream('POST',profile['base_url'].rstrip('/')+endpoint,headers=headers,json=body) as response:
            if response.status_code != 200:
                raise ValueError('Провайдер отклонил запрос. Проверьте настройки сервера.')
            async for line in response.aiter_lines():
                if not line.startswith('data:'):
                    continue
                data = line[5:].strip()
                if data=='[DONE]':
                    finished = True
                    break
                event = json.loads(data)
                if 'error' in event or event.get('type')=='error':
                    raise ValueError('Ошибка потока провайдера')
                if profile['protocol']=='chat':
                    choice = (event.get('choices') or [{}])[0]
                    if choice.get('finish_reason'):
                        if choice['finish_reason'] in ('length','content_filter'):
                            raise ValueError('Ответ провайдера ограничен')
                        finished = True
                    delta = choice.get('delta',{})
                    reasoning += delta.get('reasoning_content') or ''
                    if delta.get('content'):
                        yield 'delta',delta['content']
                    for item in delta.get('tool_calls') or []:
                        value = calls.setdefault(item['index'],{'id':'','name':'','arguments':''})
                        value['id'] += item.get('id','')
                        value['name'] += item.get('function',{}).get('name','')
                        value['arguments'] += item.get('function',{}).get('arguments','')
                elif profile['protocol']=='anthropic':
                    if event.get('delta',{}).get('stop_reason')=='max_tokens':
                        raise ValueError('Ответ провайдера ограничен')
                    if event.get('type')=='message_stop':
                        finished = True
                    if event.get('type')=='content_block_start' and event['content_block']['type']=='tool_use':
                        block = event['content_block']
                        calls[event['index']] = {'id':block['id'],'name':block['name'],'arguments':''}
                    delta = event.get('delta',{})
                    if delta.get('type')=='text_delta':
                        yield 'delta',delta['text']
                    if delta.get('type')=='input_json_delta':
                        calls[event['index']]['arguments'] += delta['partial_json']
                else:
                    candidate = (event.get('candidates') or [{}])[0]
                    if candidate.get('finishReason'):
                        if candidate['finishReason']!='STOP':
                            raise ValueError('Ответ провайдера ограничен')
                        finished = True
                    for part in candidate.get('content',{}).get('parts',[]):
                        if 'text' in part and not part.get('thought'):
                            yield 'delta',part['text']
                        if 'functionCall' in part:
                            call = part['functionCall']
                            cid = call.get('id') or uuid.uuid4().hex
                            calls[cid] = {'id':cid,'name':call['name'],'arguments':call.get('args',{}),
                                          'raw':part,'provider_id':call.get('id')}
    if not finished:
        raise ValueError('Поток провайдера прерван')
    for value in calls.values():
        if reasoning:
            value['reasoning_content'] = reasoning
        if isinstance(value['arguments'],str):
            value['arguments'] = json.loads(value['arguments'] or '{}')
        if not value['id']:
            value['id'] = uuid.uuid4().hex
        yield 'call',value
