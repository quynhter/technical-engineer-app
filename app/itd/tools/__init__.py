"""Transport-independent, role-checked catalogue of read tools."""
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .. import knowledge
from ..read_audit import record
from ..services.context import scope
from ..services.knowledge import execute as knowledge_execute
from ..services.operations import execute_cli
from ..services.permissions import RANK, require
from ..services.queries import query_web
from ..services.versions import skills_version


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class ProjectInput(EmptyInput):
    project_id: int = Field(gt=0)


class SearchInput(EmptyInput):
    query: str = Field(default='', max_length=500)
    corpus: str | None = None
    kind: Literal['chunk', 'rule'] | None = None
    clause: str | None = None
    work: str | None = None
    form: str | None = None
    limit: int = Field(default=10, ge=1, le=100)


class ShowInput(EmptyInput):
    id: str = Field(min_length=1, max_length=2048)


def versions(ctx):
    state = knowledge_execute(ctx, 'knowledge-status', SimpleNamespace(root=knowledge.default_root()))
    return {'knowledge_version': state['fingerprint'], 'skills_version': skills_version(),
            'index_status': state['index_status']}


def cli(command, **fixed):
    def run(ctx, actor, data):
        return execute_cli(ctx, actor, SimpleNamespace(command=command, output=None,
                                                       **fixed, **data.model_dump()))
    return run


def knowledge_tool(command):
    def run(ctx, actor, data):
        return execute_cli(ctx, actor, SimpleNamespace(command=command, root=knowledge.default_root(),
                                                       **data.model_dump()))
    return run


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input: type[BaseModel]
    role: Literal['viewer', 'editor', 'admin']
    access: Literal['read', 'write']
    service: Callable

    def schema(self):
        return self.input.model_json_schema()


TOOLS = (
    Tool('objects-list', 'Список объектов.', EmptyInput, 'viewer', 'read',
         cli('list', entity='objects', project_id=None)),
    Tool('projects-list', 'Список разделов РД.', EmptyInput, 'viewer', 'read',
         cli('list', entity='projects', project_id=None)),
    Tool('project-context', 'Сведения о разделе и текущем состоянии.', ProjectInput, 'viewer', 'read',
         cli('project-context')),
    Tool('project-records', 'Ведомости, журналы, ресурсы и документы раздела.', ProjectInput, 'viewer', 'read',
         lambda ctx, actor, data: query_web(ctx, actor, '/api/project', {'project_id': [str(data.project_id)]})),
    Tool('knowledge-search', 'Поиск FTS5; вывод совпадает с CLI.', SearchInput, 'viewer', 'read',
         knowledge_tool('knowledge-search')),
    Tool('knowledge-show', 'Полный фрагмент знаний по ID из поиска; вывод CLI.', ShowInput, 'viewer', 'read',
         knowledge_tool('knowledge-show')),
    Tool('knowledge-status', 'Состояние общего индекса и исходных знаний.', EmptyInput, 'viewer', 'read',
         knowledge_tool('knowledge-status')),
    Tool('release-list', 'Статус зарегистрированных выпусков раздела.', ProjectInput, 'viewer', 'read',
         cli('release-list')),
    Tool('project-check', 'Отчёт связей и готовности раздела без исправлений.', ProjectInput, 'viewer', 'read',
         cli('project-check')),
)


def available(actor, *, allowed=None):
    require(actor, 'viewer')
    return tuple(tool for tool in TOOLS if RANK[actor.role] >= RANK[tool.role]
                 and (tool.access != 'write' or RANK[actor.role] >= RANK['editor'])
                 and (allowed is None or tool.name in allowed))


def documentation():
    """The Markdown table is generated from the same definitions as MCP schemas."""
    lines = ['| Инструмент | Описание | Вход | Роль | Класс |',
             '|---|---|---|---|---|']
    for tool in TOOLS:
        fields = ', '.join(tool.schema()['properties']) or '—'
        lines.append(f'| `{tool.name}` | {tool.description} | {fields} | {tool.role} | {tool.access} |')
    return '\n'.join(lines)


def invoke(ctx, actor, name, arguments, *, allowed=None, knowledge_bases=None):
    """Validate before dispatch. No output is returned without a successful sidecar audit."""
    meta = {'knowledge_version': 'unavailable', 'skills_version': skills_version(), 'index_status': 'unavailable'}
    tool = next((item for item in TOOLS if item.name == name), None)
    project_id = 0
    outcome = 'error'
    try:
        require(actor, 'viewer')
        meta = versions(ctx)
        if tool is None:
            raise ValueError('Unknown tool')
        if tool not in available(actor, allowed=allowed):
            raise PermissionError('Unavailable tool')
        data = tool.input.model_validate(arguments)
        if knowledge_bases is not None and name.startswith('knowledge-'):
            if not knowledge_bases:
                raise PermissionError('Knowledge disabled')
            if name == 'knowledge-search' and data.corpus not in knowledge_bases:
                raise PermissionError('Choose an allowed corpus')
            if name == 'knowledge-show' and data.id.split('/')[0] not in knowledge_bases:
                raise PermissionError('Corpus unavailable')
        project_id = getattr(data, 'project_id', 0)
        if not ctx.database.is_file():
            raise ValueError('Business database missing')
        value = tool.service(ctx, actor, data)
        if name == 'knowledge-status' and knowledge_bases is not None:
            value['corpora'] = {k:v for k,v in value['corpora'].items() if k in knowledge_bases}
            value['entries'] = sum(v.get('chunks',0)+v.get('rules',0) for v in value['corpora'].values())
        # Search/show may have built the shared derived index.
        if tool.name in ('knowledge-search', 'knowledge-show'):
            meta['index_status'] = 'ready'
        response = {'data': value, **meta}
        outcome = 'success'
    except PermissionError:
        outcome = 'denied'
        response = {'error': {'code': 'forbidden', 'message': 'Инструмент недоступен.'}, **meta}
    except (ValidationError, ValueError, KeyError, TypeError):
        response = {'error': {'code': 'invalid_input', 'message': 'Проверьте параметры и целостность знаний.'}, **meta}
    except Exception:
        response = {'error': {'code': 'operation_failed', 'message': 'Операция не завершена.'}, **meta}
    with scope(ctx, actor):
        record(ctx.database, tool.name if tool else 'unknown-tool', project_id=project_id,
               release_ids=[], source=actor.source, user_id=actor.user_id,
               result=outcome, versions=meta)
    return response
