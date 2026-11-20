"""Chats, streams and access boundaries, with disposable data and fake providers."""
import asyncio
import json
from pathlib import Path
import tempfile
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from itd import knowledge, llm, tools
from itd.assistant_runtime import Runtime
from itd.http_api import create_app
from itd.server_state import WorkspaceState
from itd.services.context import Actor, ServiceContext
from itd.services.assistants import Chats
from itd.db import connect, add_object, add_project

PROFILE = {'protocol':'chat','base_url':'http://127.0.0.1:1/v1','api_key':'test-secret-not-real'}


class AssistantTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='itd-assistant-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = WorkspaceState(self.root/'test.db')
        self.state.prepare()
        self.ctx = ServiceContext(database=self.state.database)
        self.admin = Actor(user_id=1,role='admin',source='assistant',on_behalf_of=1)
        user = self.state.accounts.create({'first_name':'Тест','last_name':'Чат','role':'viewer'})
        self.uid = user['user']['id']
        self.viewer = Actor(user_id=self.uid,role='viewer',source='assistant',on_behalf_of=self.uid)
        self.session = self.state.accounts.login(user['code'])['session']
        self.headers = {'X-ITD-Token':self.session}
        self.chats = Chats(self.state.accounts)
        self.addCleanup(patch.stopall)
        patch('itd.llm.profiles',return_value={'test':PROFILE}).start()
        kb = self.root/'sources'
        (kb/'test').mkdir(parents=True)
        (kb/'test'/'sample.md').write_text('---\ndoc_id: "TEST"\nclause: "1"\nwork_types: []\nitd_forms: []\nkeywords: []\n---\nУчебная проверка.\n')
        patch('itd.knowledge.default_root',return_value=kb).start()
        with connect(self.ctx.database) as c:
            oid = add_object(c,'Учебный объект')
            self.pid = add_project(c,object_id=oid,section_code='ЭОМ',code='CHAT',name='Секретное имя раздела fixture-9384')
        self.aid = self.chats.save(self.admin,{'name':'Инженер','provider':'test','model':'fixture',
            'allowed_tools':['objects-list','knowledge-search'],'knowledge_bases':['test']},{'test':PROFILE})['id']
        self.thread = self.chats.create(self.ctx,self.viewer,{'assistant_id':self.aid,'project_id':self.pid})

    def test_attachment_only_turn_reaches_provider_and_history(self):
        histories = []
        async def provider(profile, model, system, history, permitted):
            histories.append(history)
            yield 'delta', 'Получено'
        async def run():
            runtime = Runtime(self.state.accounts)
            data = {'thread_id':self.thread['id'], 'text':'', 'request_key':'file',
                    'attachments':[{'name':'акт.txt', 'data':'Zml4dHVyZQ=='}]}
            with patch('itd.llm.stream', provider):
                result = await runtime.start(self.ctx,self.viewer,data,lambda:self.viewer)
                await runtime.tasks[result['message_id']]
        asyncio.run(run())
        self.assertIn('fixture', histories[0][-1]['content'])
        messages = self.chats.history(self.ctx,self.viewer,self.thread['id'])['messages']
        self.assertEqual(messages[0]['attachments'], [{'name':'акт.txt','text':'fixture'}])
        with self.assertRaises(ValueError):
            self.chats.start(self.ctx,self.viewer,self.thread['id'],'','bad',
                             [{'name':'bad.pdf','data':'!'}])
        self.assertEqual(len(self.chats.history(self.ctx,self.viewer,self.thread['id'])['messages']),2)

    def test_ownership_workspace_admin_and_skill_versions(self):
        self.assertEqual(self.thread['skill_version'],tools.skills_version())
        with self.assertRaises(PermissionError):
            self.chats.history(self.ctx,self.admin,self.thread['id'])
        with self.assertRaises(PermissionError):
            self.chats.thread(self.ctx.model_copy(update={'database':self.root/'other.db'}),self.viewer,self.thread['id'])
        with self.assertRaises(PermissionError):
            self.chats.save(self.viewer,{}, {'test':PROFILE})
        with patch('itd.services.assistants.skills_version',return_value='new-version'):
            new = self.chats.create(self.ctx,self.viewer,{'assistant_id':self.aid})
            self.assertEqual(new['skill_version'],'new-version')
            self.assertNotEqual(self.chats.thread(self.ctx,self.viewer,self.thread['id'])['skill_version'],'new-version')
            with self.assertRaises(ValueError):
                self.chats.start(self.ctx,self.viewer,self.thread['id'],'x','x')
        with self.assertRaises(ValueError):
            self.chats.save(self.admin,{'name':'bad','provider':'test','model':'x','skill_path':'README.md'}, {'test':PROFILE})

    def test_existing_and_new_assistants_use_all_tools_and_knowledge_without_read_writes(self):
        with self.state.accounts.connect() as c, c:
            c.execute("UPDATE assistants SET allowed_tools='[]', knowledge_bases='[]' WHERE id=?", (self.aid,))
        with self.state.accounts.connect() as c:
            before = list(c.iterdump())
        assistant = self.chats.assistants(self.viewer)[0]
        self.assertEqual(set(assistant['allowed_tools']), {t.name for t in tools.TOOLS})
        self.assertEqual(assistant['knowledge_bases'], ['*'])
        with self.state.accounts.connect() as c:
            self.assertEqual(before, list(c.iterdump()))
        seen = []
        async def provider(profile, model, system, history, permitted):
            seen.append((system, {t.name for t in permitted}))
            if len(seen) == 1:
                yield 'call', {'id':'all-knowledge', 'name':'knowledge-search', 'arguments':{'query':'проверка'}}
            else:
                yield 'delta', 'Проверено по всей базе'
        async def run():
            runtime = Runtime(self.state.accounts)
            with patch('itd.llm.stream', provider):
                result = await runtime.start(self.ctx, self.viewer,
                    {'thread_id':self.thread['id'], 'text':'Проверить всю базу', 'request_key':'all-library'}, lambda:self.viewer)
                await runtime.tasks[result['message_id']]
        asyncio.run(run())
        result = self.chats.history(self.ctx, self.viewer, self.thread['id'])['messages'][-1]
        self.assertIn('data', result['tool_calls'][0]['result'])
        self.assertIn('Используется вся база знаний', seen[0][0])
        self.assertEqual(seen[0][1], {t.name for t in tools.available(self.viewer)})

    def test_context_name_rename_and_delete_are_owner_only(self):
        self.assertEqual(self.chats.history(self.ctx,self.viewer,self.thread['id'])['context'],'Раздел ЭОМ «Секретное имя раздела fixture-9384». Учебный объект')
        self.assertEqual(self.chats.rename(self.ctx,self.viewer,self.thread['id'],'  Новое имя  ')['title'],'Новое имя')
        self.assertEqual(self.chats.thread(self.ctx,self.viewer,self.thread['id'])['title'],'Новое имя')
        with self.assertRaises(ValueError):
            self.chats.rename(self.ctx,self.viewer,self.thread['id'],'   ')
        with self.assertRaises(PermissionError):
            self.chats.rename(self.ctx,self.admin,self.thread['id'],'Чужое')
        with self.assertRaises(PermissionError):
            self.chats.delete(self.ctx,self.admin,self.thread['id'])
        self.chats.delete(self.ctx,self.viewer,self.thread['id'])
        with self.assertRaises(PermissionError):
            self.chats.thread(self.ctx,self.viewer,self.thread['id'])

    def test_stream_persists_messages_tool_results_and_never_changes_business_db(self):
        with connect(self.ctx.database) as c:
            before = list(c.iterdump())
        seen = []
        async def provider(profile,model,system,history,permitted):
            seen.append((system,{t.name for t in permitted}))
            if len(seen)==1:
                yield 'call',{'id':'call1','name':'objects-list','arguments':{}}
            else:
                yield 'delta','Проверено '
                yield 'delta','по инструменту.'
        async def run():
            runtime = Runtime(self.state.accounts)
            with patch('itd.llm.stream',provider):
                result = await runtime.start(self.ctx,self.viewer,{'thread_id':self.thread['id'],'text':'Мой вопрос','request_key':'request-1'},lambda:self.viewer)
                await runtime.tasks[result['message_id']]
                duplicate = await runtime.start(self.ctx,self.viewer,{'thread_id':self.thread['id'],'text':'Мой вопрос','request_key':'request-1'},lambda:self.viewer)
                self.assertTrue(duplicate['existing'])
        asyncio.run(run())
        messages = self.chats.history(self.ctx,self.viewer,self.thread['id'])['messages']
        self.assertEqual(len(messages),2)
        self.assertEqual(messages[-1]['text'],'Проверено по инструменту.')
        self.assertEqual(messages[-1]['status'],'complete')
        self.assertIn('data',messages[-1]['tool_calls'][0]['result'])
        self.assertEqual(seen[0][1],{t.name for t in tools.available(self.viewer)})
        self.assertNotIn('Учебный объект',seen[0][0])
        self.assertNotIn('Секретное имя раздела fixture-9384',seen[0][0])
        with connect(self.ctx.database) as c:
            self.assertEqual(before,list(c.iterdump()))

    def test_explicit_tool_restrictions_and_unknown_model_calls_are_rejected(self):
        denied = tools.invoke(self.ctx,self.viewer,'knowledge-search',{'query':'x','corpus':'other'},allowed=['knowledge-search'],knowledge_bases=['test'])
        self.assertEqual(denied['error']['code'],'forbidden')
        denied = tools.invoke(self.ctx,self.viewer,'objects-list',{},allowed=[])
        self.assertEqual(denied['error']['code'],'forbidden')
        count = 0
        async def provider(*args):
            nonlocal count
            count += 1
            if count==1:
                yield 'call',{'id':'denied','name':'unknown-tool','arguments':{}}
            else:
                yield 'delta','Недоступно'
        async def run():
            runtime = Runtime(self.state.accounts)
            with patch('itd.llm.stream',provider):
                r = await runtime.start(self.ctx,self.viewer,{'thread_id':self.thread['id'],'text':'Запрос','request_key':'denied'},lambda:self.viewer)
                await runtime.tasks[r['message_id']]
        asyncio.run(run())
        result = self.chats.history(self.ctx,self.viewer,self.thread['id'])['messages'][-1]['tool_calls'][0]['result']
        self.assertEqual(result['error']['code'],'invalid_input')

    def test_cancellation_preserves_partial_text_and_startup_recovers_interrupted_turn(self):
        async def run():
            runtime = Runtime(self.state.accounts)
            ready = asyncio.Event()
            async def provider(*args):
                yield 'delta','Сохранённая часть'
                ready.set()
                await asyncio.Event().wait()
            with patch('itd.llm.stream',provider):
                result = await runtime.start(self.ctx,self.viewer,{'thread_id':self.thread['id'],'text':'Вопрос','request_key':'cancel'},lambda:self.viewer)
                await ready.wait()
                task = runtime.tasks[result['message_id']]
                await runtime.cancel(self.ctx,self.viewer,self.thread['id'])
                await task
        asyncio.run(run())
        message = self.chats.history(self.ctx,self.viewer,self.thread['id'])['messages'][-1]
        self.assertEqual((message['text'],message['status']),('Сохранённая часть','cancelled'))
        self.chats.start(self.ctx,self.viewer,self.thread['id'],'Следующий','restart')
        self.state.accounts.initialize()
        self.assertEqual(self.chats.history(self.ctx,self.viewer,self.thread['id'])['messages'][-1]['status'],'interrupted')

    def test_http_foreign_thread_and_admin_configuration(self):
        with TestClient(create_app(self.state),base_url='http://127.0.0.1:8765') as c:
            self.assertEqual(c.get('/api/v1/assistants',headers=self.headers).status_code,200)
            self.assertEqual(c.get('/api/v1/assistant/admin',headers=self.headers).status_code,403)
            self.assertEqual(c.post('/api/v1/assistant/config',headers=self.headers,json={}).status_code,403)
            admin_session = self.state.accounts.session(1)
            self.assertEqual(c.get('/api/v1/assistant/thread?thread_id='+str(self.thread['id']),headers={'X-ITD-Token':admin_session}).status_code,403)
            self.assertEqual(c.post('/api/v1/assistant/threads',headers=self.headers,json={'assistant_id':self.aid,'role':'admin'}).status_code,400)

    def test_http_stream_reader_disconnect_does_not_lose_generation(self):
        async def provider(*args):
            yield 'delta','Начало'
            await asyncio.sleep(0.05)
            yield 'delta',' и конец'
        with patch('itd.llm.stream',provider), TestClient(create_app(self.state),base_url='http://127.0.0.1:8765') as c:
            result = c.post('/api/v1/assistant/messages',headers=self.headers,json={'thread_id':self.thread['id'],'text':'Вопрос','request_key':'http'}).json()
            # Deliberately do not open an SSE reader until the background turn completes.
            async def complete():
                task = c.app.state.assistant_runtime.tasks.get(result['message_id'])
                if task:
                    await task
            c.portal.call(complete)
            for _ in range(2):
                response = c.get('/api/v1/assistant/events?thread_id='+str(self.thread['id'])+'&message_id='+str(result['message_id']),headers=self.headers)
                self.assertIn('Начало и конец',response.text)
                self.assertIn('"status": "complete"',response.text)
            self.assertEqual(len(self.chats.history(self.ctx,self.viewer,self.thread['id'])['messages']),2)

    def test_provider_protocols_headers_and_no_key_in_url(self):
        history = [{'role':'user','content':'Вопрос'}]
        for protocol in ('chat','anthropic','gemini'):
            endpoint,headers,body = llm.request({**PROFILE,'protocol':protocol},'fixture', 'Instruction',history,tools.available(self.viewer))
            self.assertNotIn(PROFILE['api_key'],endpoint)
            self.assertNotIn(PROFILE['api_key'],json.dumps(body))
            self.assertIn(PROFILE['api_key'],str(headers))

    def test_provider_exceptions_and_personal_content_are_never_logged(self):
        secret = 'fixture-secret-key'
        personal = 'Фамилия-9384 Адрес-4821'
        async def provider(*args):
            raise ValueError(secret+' '+personal)
            yield
        async def run():
            runtime = Runtime(self.state.accounts)
            with patch('itd.llm.stream',provider):
                result = await runtime.start(self.ctx,self.viewer,{'thread_id':self.thread['id'],'text':personal,'request_key':'private'},lambda:self.viewer)
                await runtime.tasks[result['message_id']]
        with patch('logging.Logger._log') as logger:
            asyncio.run(run())
        output = str(logger.call_args_list)
        self.assertNotIn(secret,output)
        self.assertNotIn(personal,output)
        response = self.chats.history(self.ctx,self.viewer,self.thread['id'])['messages'][-1]
        self.assertEqual(response['status'],'error')
        self.assertNotIn(secret,json.dumps(response))
        self.assertNotIn(personal,json.dumps(response))

    def test_provider_fragmented_tool_streams_and_interrupted_stream(self):
        import httpx2
        original = httpx2.AsyncClient
        samples = {
            'chat':[{'choices':[{'delta':{'content':'Текст'}}]},
                    {'choices':[{'delta':{'tool_calls':[{'index':0,'id':'c1','function':{'name':'objects-list','arguments':'{'}}]}}]},
                    {'choices':[{'delta':{'tool_calls':[{'index':0,'function':{'arguments':'}'}}]},'finish_reason':'tool_calls'}]}],
            'anthropic':[{'type':'content_block_start','index':0,'content_block':{'type':'tool_use','id':'c1','name':'objects-list'}},
                         {'type':'content_block_delta','index':0,'delta':{'type':'input_json_delta','partial_json':'{}'}},
                         {'type':'message_stop'}],
            'gemini':[{'candidates':[{'content':{'parts':[{'functionCall':{'id':'c1','name':'objects-list','args':{}},'thoughtSignature':'signature'}]},'finishReason':'STOP'}]}],
        }
        async def run():
            for protocol,events in samples.items():
                data = ''.join('data: '+json.dumps(e)+'\n\n' for e in events)
                transport = httpx2.MockTransport(lambda req:httpx2.Response(200,text=data))
                with patch('itd.llm.httpx2.AsyncClient',side_effect=lambda **kw:original(transport=transport,**kw)):
                    result = [v async for v in llm.stream({**PROFILE,'protocol':protocol},'fixture','system',[{'role':'user','content':'Тест'}],[])]
                call = next(v for kind,v in result if kind=='call')
                self.assertEqual((call['name'],call['arguments']),('objects-list',{}))
                if protocol=='gemini':
                    self.assertEqual(call['raw']['thoughtSignature'],'signature')
            transport = httpx2.MockTransport(lambda req:httpx2.Response(200,text='data: {"choices":[{"delta":{"content":"часть"}}]}\n\n'))
            with patch('itd.llm.httpx2.AsyncClient',side_effect=lambda **kw:original(transport=transport,**kw)):
                with self.assertRaises(ValueError):
                    _ = [v async for v in llm.stream(PROFILE,'fixture','system',[],[])]
        asyncio.run(run())

    def test_server_only_custom_provider_config(self):
        # Use the real loader despite the fixture's general profiles stub.
        loader = self.__class__.real_profiles
        path = self.root/'providers.json'
        path.write_text(json.dumps({'own':{'protocol':'chat','base_url':'http://127.0.0.1:11434/v1','allow_anonymous':True}}))
        with patch.dict(os.environ,{'ITD_LLM_CONFIG':str(path)},clear=True):
            self.assertEqual(set(loader()),{'own'})


AssistantTests.real_profiles = staticmethod(llm.profiles)


if __name__=='__main__':
    unittest.main()
