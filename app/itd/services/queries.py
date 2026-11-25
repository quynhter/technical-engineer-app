"""Read operations and verified file delivery, independent of HTTP response IO."""
from dataclasses import dataclass
from pathlib import Path
import tempfile
from types import SimpleNamespace

from ..db import connect
from .operations import operation
from .permissions import web_policy, require
from .projections import bootstrap, project_data


@dataclass(frozen=True)
class FileResult:
    content: bytes
    mime: str
    filename: str


def download(connection, project_id, release_id):
    from ..archive import digest
    from ..releases import workspace
    release = connection.execute('SELECT * FROM releases WHERE id=? AND project_id=?',
                                 (release_id, project_id)).fetchone()
    if release is None:
        raise ValueError('Опубликованный выпуск не найден')
    path = Path(release['path'])
    if not path.is_absolute():
        path = workspace(connection) / path
    if not path.is_file() or digest(path) != release['sha256']:
        raise ValueError('Проверка целостности выпуска не пройдена')
    file = connection.execute('SELECT name FROM files WHERE release_id=?',(release_id,)).fetchone()
    return FileResult(path.read_bytes(), 'application/octet-stream', file[0] if file else path.name)


def query_web(ctx, actor, route, query, *, revision=None):
    policy = web_policy(route, read=True)
    with operation(ctx, actor, route, policy):
        if route == '/api/knowledge':
            from ..knowledge import default_root
            from .knowledge import execute
            first = lambda key: query.get(key, [None])[0]
            args = SimpleNamespace(root=default_root(), id=first('id'), query=first('query'),
                                   corpus=first('corpus'), kind=first('kind'), limit=20,
                                   clause=None, work=None, form=None)
            command = 'knowledge-show' if 'id' in query else (
                'knowledge-search' if 'query' in query else 'knowledge-status')
            return execute(ctx, command, args)
        with connect(ctx.database) as c:
            c.execute('PRAGMA query_only = ON')
            if route == '/api/status':
                c.execute('SELECT id FROM objects LIMIT 1').fetchone()
                return {'database': 'ready', 'agent': {'mode': 'external_chat', 'activity': 'unknown'}}
            if route == '/api/bootstrap':
                return bootstrap(c)
            if route == '/api/configuration':
                from ..configuration import export_configuration
                return export_configuration(c, int(query['object_id'][0]), query['scope'][0])
            if route == '/api/workspace':
                from ..workspace import snapshot
                return snapshot(c, int(query['object_id'][0])) if 'object_id' in query else snapshot(c)
            if route == '/api/project':
                pid = int(query['project_id'][0])
                if not c.execute('SELECT 1 FROM projects WHERE id=?', (pid,)).fetchone():
                    raise ValueError('Раздел не найден')
                if revision is not None and query.get('revision', [None])[0] == revision:
                    return {'unchanged': True, '_revision': revision}
                return {**project_data(c, pid), '_revision': revision}
            if route == '/api/journal-docx':
                from ..journal_export import export
                with tempfile.TemporaryDirectory(prefix='itd-journal-') as folder:
                    output = Path(folder)/'journal.docx'
                    filename = export(c,int(query['project_id'][0]),query['kind'][0],ctx.templates,output)
                    return FileResult(output.read_bytes(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',filename)
            if route == '/api/download':
                return download(c, int(query['project_id'][0]), int(query['release_id'][0]))
            if route == '/api/context':
                from ..acts import build_context, find_template, template_claims, context_digest
                from ..workflow import same_project
                from ..document_preview import preview_fields
                from ..manual import source_issues
                from ..field_ui import table_headers
                from ..archive import digest
                aid, pid = int(query['act_id'][0]), int(query['project_id'][0])
                same_project(c, 'acts', aid, pid)
                result = build_context(c, aid, draft=True)
                result['form_name'], result['preview_fields'] = preview_fields(c, aid)
                result['source_issues'] = source_issues(c, aid)
                try:
                    template = find_template(ctx.templates, result['act_type'])
                    result['table_headers'] = table_headers(template)
                    result['static_claims'] = template_claims(template)
                    review = c.execute('SELECT * FROM final_reviews WHERE act_id=?', (aid,)).fetchone()
                    result['review_current'] = bool(review and review['template_sha256'] == digest(template)
                                                   and review['context_sha256'] == context_digest(result['context']))
                except ValueError as error:
                    result['template_error'] = str(error)
                return result
            if route == '/api/original':
                from ..archive import archived_path, digest
                pid, aid = int(query['project_id'][0]), int(query['attachment_id'][0])
                originals = project_data(c, pid)['attachments']
                item = next((a for a in originals if a['id'] == aid), None)
                if item is None:
                    raise ValueError('Оригинал не связан с разделом')
                from ..storage import directory
                stored = c.execute('SELECT id FROM files WHERE project_id=? AND attachment_id=?',(pid,aid)).fetchone()
                path = directory(c)/stored[0] if stored else archived_path(ctx.database.parent / 'archive', item['storage_path'])
                if not path.is_file() or digest(path) != item['sha256']:
                    raise ValueError('Целостность оригинала не подтверждена')
                return FileResult(path.read_bytes(), 'application/octet-stream', item['original_name'])
            if route == '/api/package':
                from ..releases import build_package, build_project_zip
                from ..read_audit import record
                pid = int(query['project_id'][0])
                with tempfile.TemporaryDirectory(prefix='itd-package-') as folder:
                    target = Path(folder) / 'ИТД.zip'
                    result = (build_project_zip(c, pid, target) if query.get('layout')==['project']
                              else build_package(c, pid, target, include_originals=True))
                    record(ctx.database, 'package-download', project_id=pid,
                           release_ids=[item['release_id'] for item in result['releases']],
                           source=actor.source, user_id=actor.user_id)
                    return FileResult(target.read_bytes(), 'application/zip', 'ИТД.zip')
            raise ValueError('Страница не найдена')


def check_workspace_switch(ctx, actor):
    require(actor, 'admin')
    with connect(ctx.database) as c:
        c.execute('PRAGMA query_only = ON')
        if c.execute("SELECT 1 FROM file_operations WHERE state='pending'").fetchone():
            raise ValueError('Сначала завершите восстановление операции с исходными файлами')
        if c.execute("SELECT 1 FROM release_operations WHERE state='prepared'").fetchone():
            raise ValueError('Сначала завершите восстановление выпуска документа')
