"""Service entry points: trusted context + actor + validated input -> result."""
from contextlib import contextmanager
import json
import logging
from pathlib import Path
from types import SimpleNamespace

from ..changes import log_event
from ..db import connect, initialize
from .context import OperationInput, WorkspaceActionInput, scope
from .permissions import cli_policy, require, web_policy, action_policy


LOG = logging.getLogger('itd.db')


def audit_subject(args, result):
    tables = {'object-add': 'objects', 'project-add': 'projects', 'resource-add': 'resources',
              'scheme-add': 'schemes', 'organization-add': 'organizations',
              'signatory-add': 'signatories', 'act-add': 'acts'}
    if args.command in tables and isinstance(result, dict) and type(result.get('id')) is int:
        return tables[args.command], result['id']
    if args.command == 'record-update':
        return args.entity, args.record_id
    for key, table in (('release_id', 'releases'), ('act_id', 'acts'), ('resource_id', 'resources'),
                       ('project_id', 'projects'), ('object_id', 'objects')):
        value = getattr(args, key, None)
        if type(value) is int:
            return table, value
    return None, None


@contextmanager
def operation(ctx, actor, name, policy):
    try:
        require(actor, policy.role)
    except PermissionError:
        LOG.warning('Операция %s источник %s актор %s результат denied', name,
                    actor.source if actor else 'unknown', actor.user_id if actor else 'unknown')
        raise
    with scope(ctx, actor):
        try:
            yield
        except Exception as error:
            LOG.warning('Операция %s источник %s актор %s результат %s',
                        name, actor.source, actor.user_id, type(error).__name__)
            raise
        else:
            LOG.info('Операция %s источник %s актор %s результат success',
                     name, actor.source, actor.user_id)


def _workspace_action(ctx, actor, connection, project_id, action, data):
    request = WorkspaceActionInput(project_id=project_id, action=action, data=data)
    require(actor, action_policy(request.action).role)
    from ..manual import execute
    return execute(connection, request.project_id, request.action, request.data)


def execute_cli(ctx, actor, args):
    # Database selection is trusted context, never an operation argument.
    args = SimpleNamespace(**{**vars(args), 'db': ctx.database})
    policy = cli_policy(args)
    with operation(ctx, actor, args.command, policy):
        if args.command.startswith('knowledge-'):
            from .knowledge import execute
            return execute(ctx, args.command, args)
        if args.command == 'template-schema':
            from ..template_objects import template_schema
            return template_schema(args.form_code)
        if args.command == 'init':
            ctx.database.parent.mkdir(parents=True, exist_ok=True)
            initialize(ctx.database)
            return {'ok': True, 'db': str(ctx.database)}
        if args.command == 'doctor':
            from ..doctor import diagnose
            return diagnose(args.renderer)
        if args.command == 'read-document':
            from ..readers import read_document
            result = read_document(args.file, scan_dir=args.render_pages, pages=args.pages,
                                   dpi=args.dpi, overview=args.overview)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open('x', encoding='utf-8') as handle:
                    json.dump(result, handle, ensure_ascii=False, indent=2)
                return {'output': str(args.output.resolve()), 'parts': len(result['parts']),
                        'sha256': result['sha256']}
            return result
        if not ctx.database.is_file():
            raise ValueError('БД не найдена. Сначала выполните init.')
        with connect(ctx.database) as connection:
            if policy.write and 'actor_id' not in {row[1] for row in connection.execute('PRAGMA table_info(audit_events)')}:
                raise ValueError('Требуется миграция 023: выполните init с явно выбранной --db')
            if not policy.write:
                connection.execute('PRAGMA query_only = ON')
            if args.command == 'workspace-action':
                from .cli_operations import read_json
                result = _workspace_action(ctx, actor, connection, args.project_id,
                                          args.action, read_json(args.data))
            else:
                from .cli_operations import dispatch
                result = dispatch(connection, args, ctx, actor)
            if policy.write:
                entity, entity_id = audit_subject(args, result)
                log_event(connection, args.command, entity=entity, entity_id=entity_id)
            if args.command in ('fact-summary', 'package-matrix', 'project-check',
                                'workflow-context', 'spec-compare') and args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open('x', encoding='utf-8') as handle:
                    json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
                result = {'output': str(args.output.resolve())}
            return result


def execute_web(ctx, actor, route, data):
    request = OperationInput(operation=route, data=data)
    policy = web_policy(request.operation, request.data)
    with operation(ctx, actor, route, policy):
        if route.startswith('/api/files/'):
            from ..file_manager import make_plan, apply_plan, recover_files
            if route.endswith('/plan'):
                return make_plan(ctx.database, data.get('project_id'), data.get('purpose', 'check'),
                                 data.get('attachment_id'), ctx.settings['plan_secret'])
            if route.endswith('/recover'):
                if data.get('confirmed') is not True:
                    raise ValueError('Подтвердите восстановление файлов')
                result = recover_files(ctx.database, data.get('project_id'))
            else:
                result = apply_plan(ctx.database, data.get('plan'), data.get('token'),
                                    data.get('types', {}), ctx.settings['plan_secret'])
            with connect(ctx.database) as connection:
                log_event(connection, route, entity='projects', entity_id=data.get('project_id'))
            return result
        with connect(ctx.database) as connection:
            if not policy.write:
                connection.execute('PRAGMA query_only = ON')
            before = connection.total_changes
            if route == '/api/action':
                result = _workspace_action(ctx, actor, connection, data.get('project_id'),
                                          data.get('action'), data.get('data', {}))
            else:
                from .documents import mutate
                result = mutate(connection, route, data, ctx)
            if policy.write and connection.total_changes > before:
                log_event(connection, route, entity='projects', entity_id=data.get('project_id'))
            return result


def legacy_mutate(connection, route, data, database=None, templates=None):
    """Compatibility for trusted in-process callers with an existing DB connection.

    HTTP requests use execute_web with a freshly authenticated actor instead.
    This is a low-level domain helper, like acts.add_act, not a service entry point.
    """
    from .context import ServiceContext
    from .documents import mutate
    if database is None:
        database = connection.execute('PRAGMA database_list').fetchone()[2]
    kwargs = {'database': Path(database)}
    if templates is not None:
        kwargs['templates'] = templates
    return mutate(connection, route, data, ServiceContext(**kwargs))
