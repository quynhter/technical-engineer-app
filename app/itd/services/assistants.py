"""Personal chats in accounts, never in the business DB; explicit role-checked services."""
import hashlib
import json
from pathlib import Path
import sqlite3
from contextlib import closing

from pydantic import BaseModel, ConfigDict, Field

from ..assistant_files import read_attachments
from ..db import connect
from ..paths import ROOT
from ..tools import TOOLS, available
from .permissions import require
from .versions import skills_version


class AssistantInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: int | None = None
    name: str = Field(min_length=1, max_length=100)
    instruction: str = Field(default='', max_length=20000)
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=150)
    allowed_tools: list[str] = Field(default_factory=list)
    knowledge_bases: list[str] = Field(default_factory=list)
    active: bool = True
    skill_path: str = 'ai/skills/ai-technical-engineer/SKILL.md'


def skill_text(path):
    # Existing assistant cards retain their recorded skill reference after relocation.
    if path.startswith('skills/'):
        path = 'ai/' + path
    target = (ROOT / path).resolve()
    if not target.is_relative_to((ROOT/'ai/skills').resolve()) or target.suffix != '.md' or not target.is_file():
        raise ValueError('Недопустимая ссылка на навык')
    # References belong to the selected skill, without storing copies in the DB.
    refs = sorted((target.parent/'references').glob('*.md'))
    return '\n\n'.join(p.read_text() for p in (target, *refs))


def workspace(ctx):
    return hashlib.sha256(str(ctx.database.resolve()).encode()).hexdigest()


def context_name(ctx, thread):
    if thread.get('project_id'):
        with connect(ctx.database) as c:
            c.execute('PRAGMA query_only = ON')
            row = c.execute('SELECT o.name, p.section_code, p.name FROM projects p JOIN objects o ON o.id=p.object_id WHERE p.id=?', (thread['project_id'],)).fetchone()
        return ('Раздел '+row[1]+' «'+row[2]+'». '+row[0]) if row else 'раздел удалён'
    if thread.get('object_id'):
        with connect(ctx.database) as c:
            c.execute('PRAGMA query_only = ON')
            row = c.execute('SELECT name FROM objects WHERE id=?', (thread['object_id'],)).fetchone()
        return ('объект «'+row[0]+'»') if row else 'объект удалён'
    return 'все объекты'


def assistant_settings(row):
    value = decoded(row)
    # All assistants use the current registry and knowledge library. Legacy stored
    # subsets do not require a business or accounts DB write during a read.
    value['allowed_tools'] = [tool.name for tool in TOOLS]
    value['knowledge_bases'] = ['*']
    return value


def decoded(row):
    value = dict(row)
    if 'active' in value:
        value['active'] = bool(value['active'])
    for key in ('allowed_tools','knowledge_bases','tool_calls','events','attachments'):
        if key in value:
            value[key] = json.loads(value[key])
    return value


class Chats:
    def __init__(self, accounts):
        self.accounts = accounts

    def assistants(self, actor, *, admin=False):
        require(actor, 'admin' if admin else 'viewer')
        with self.accounts.connect() as c:
            return [assistant_settings(r) for r in c.execute('SELECT * FROM assistants' + ('' if admin else ' WHERE active=1') + ' ORDER BY id')]

    def save(self, actor, data, providers):
        require(actor, 'admin')
        value = AssistantInput.model_validate(data)
        if value.provider not in providers or set(value.allowed_tools)-{t.name for t in TOOLS}:
            raise ValueError('Проверьте провайдера и инструменты')
        if any(not isinstance(s,str) or '/' in s or len(s)>150 for s in value.knowledge_bases):
            raise ValueError('Проверьте корпуса знаний')
        skill_text(value.skill_path)
        fields = value.model_dump(exclude={'id'})
        fields['active'] = int(value.active)
        fields['allowed_tools'] = [tool.name for tool in TOOLS]
        fields['knowledge_bases'] = ['*']
        for key in ('allowed_tools','knowledge_bases'):
            fields[key] = json.dumps(fields[key])
        fields['skill_version'] = skills_version()
        with self.accounts.connect() as c, c:
            if value.id is None:
                aid = c.execute('INSERT INTO assistants('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')', tuple(fields.values())).lastrowid
            else:
                aid = value.id
                if not c.execute('UPDATE assistants SET '+','.join(k+'=?' for k in fields)+' WHERE id=?', (*fields.values(),aid)).rowcount:
                    raise ValueError('Ассистент не найден')
        return {'id':aid}

    def thread(self, ctx, actor, thread_id):
        require(actor, 'viewer')
        if type(thread_id) is not int or thread_id < 1:
            raise ValueError('Неверный чат')
        with self.accounts.connect() as c:
            row = c.execute('SELECT * FROM threads WHERE id=? AND user_id=? AND workspace=?',
                            (thread_id,actor.user_id,workspace(ctx))).fetchone()
        if row is None:
            raise PermissionError('Чат недоступен')
        return dict(row)

    def threads(self, ctx, actor):
        require(actor, 'viewer')
        with self.accounts.connect() as c:
            return [dict(r) for r in c.execute('SELECT * FROM threads WHERE user_id=? AND workspace=? ORDER BY id DESC', (actor.user_id,workspace(ctx)))]

    def create(self, ctx, actor, data):
        require(actor, 'viewer')
        if set(data)-{'assistant_id','object_id','project_id','title'}:
            raise ValueError('Неизвестные поля чата')
        if type(data.get('assistant_id')) is not int:
            raise ValueError('Неверный ассистент')
        assistant = next((a for a in self.assistants(actor) if a['id']==data.get('assistant_id')), None)
        if assistant is None:
            raise PermissionError('Ассистент недоступен')
        pid, oid = data.get('project_id'), data.get('object_id')
        with closing(sqlite3.connect(ctx.database.resolve().as_uri()+'?mode=ro', uri=True)) as c:
            if pid is not None:
                if type(pid) is not int:
                    raise ValueError('Неверный раздел')
                row = c.execute('SELECT object_id FROM projects WHERE id=?', (pid,)).fetchone()
                if not row or oid is not None and oid != row[0]:
                    raise ValueError('Неверный контекст')
                oid = row[0]
            if oid is not None and (type(oid) is not int or not c.execute('SELECT 1 FROM objects WHERE id=?',(oid,)).fetchone()):
                raise ValueError('Объект не найден')
        title = str(data.get('title') or 'Новый чат')[:150]
        with self.accounts.connect() as c, c:
            tid = c.execute('INSERT INTO threads(assistant_id,user_id,workspace,object_id,project_id,title,skill_path,skill_version) VALUES(?,?,?,?,?,?,?,?)',
                (assistant['id'],actor.user_id,workspace(ctx),oid,pid,title,assistant['skill_path'],skills_version())).lastrowid
        return self.thread(ctx,actor,tid)

    def history(self, ctx, actor, thread_id):
        thread = self.thread(ctx, actor, thread_id)
        with self.accounts.connect() as c:
            messages = [decoded(r) for r in c.execute('SELECT * FROM messages WHERE thread_id=? ORDER BY id', (thread_id,))]
        return {'thread':thread,'messages':messages,'context':context_name(ctx,thread)}

    def rename(self, ctx, actor, thread_id, title):
        self.thread(ctx, actor, thread_id)
        title = str(title or '').strip()[:150]
        if not title:
            raise ValueError('Укажите название чата')
        with self.accounts.connect() as c, c:
            c.execute('UPDATE threads SET title=? WHERE id=? AND user_id=? AND workspace=?', (title,thread_id,actor.user_id,workspace(ctx)))
        return {'id':thread_id,'title':title}

    def delete(self, ctx, actor, thread_id):
        self.thread(ctx, actor, thread_id)
        with self.accounts.connect() as c, c:
            if c.execute("SELECT 1 FROM messages WHERE thread_id=? AND status='running'", (thread_id,)).fetchone():
                raise ValueError('Дождитесь завершения ответа или отмените его')
            c.execute('DELETE FROM messages WHERE thread_id=?', (thread_id,))
            c.execute('DELETE FROM threads WHERE id=? AND user_id=? AND workspace=?', (thread_id,actor.user_id,workspace(ctx)))
        return {'id':thread_id,'deleted':True}

    def start(self, ctx, actor, thread_id, text, request_key, attachments=None):
        thread = self.thread(ctx, actor, thread_id)
        if thread['skill_version'] != skills_version():
            raise ValueError('Версия навыка этого чата недоступна. Создайте новый чат.')
        if not isinstance(text,str) or len(text) > 20000 or (not text.strip() and not attachments) or not isinstance(request_key,str) or not 1 <= len(request_key) <= 80:
            raise ValueError('Проверьте сообщение')
        assistant = next((a for a in self.assistants(actor) if a['id']==thread['assistant_id']), None)
        if assistant is None:
            raise PermissionError('Ассистент отключён')
        files = read_attachments([] if attachments is None else attachments)
        with self.accounts.connect() as c, c:
            c.execute('BEGIN IMMEDIATE')
            prior = c.execute('SELECT id FROM messages WHERE thread_id=? AND request_key=?',(thread_id,request_key)).fetchone()
            if prior:
                return {'message_id':prior[0]+1,'existing':True}
            if c.execute("SELECT 1 FROM messages WHERE thread_id=? AND status='running'",(thread_id,)).fetchone():
                raise ValueError('Дождитесь ответа или отмените генерацию')
            c.execute("INSERT INTO messages(thread_id,sender,text,status,request_key,attachments) VALUES(?,'user',?,'complete',?,?)", (thread_id,text,request_key,json.dumps(files,ensure_ascii=False)))
            mid = c.execute("INSERT INTO messages(thread_id,sender,status) VALUES(?,'assistant','running')",(thread_id,)).lastrowid
        return {'message_id':mid,'existing':False}

    def update(self, message_id, *, text, calls, events, status):
        # Internal worker only; user-facing access always goes through thread().
        with self.accounts.connect() as c, c:
            c.execute('UPDATE messages SET text=?,tool_calls=?,events=?,status=? WHERE id=?',
                      (text,json.dumps(calls,ensure_ascii=False),json.dumps(events,ensure_ascii=False),status,message_id))
