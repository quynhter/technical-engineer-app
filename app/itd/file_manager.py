"""Проверяемые операции с исходными файлами выбранного раздела."""
import hashlib
import hmac
import json
import os
import re
import threading
import uuid
from pathlib import Path

from . import archive
from .changes import log_event
from .db import connect
from .layout import path_component
from .paths import database_workspace, document_root, previous_itd_roots, relative_or_absolute

_LOCK = threading.RLock()
KINDS = ('contract', 'order', 'quality', 'scheme', 'rd', 'other')
REFERENCE_NAMES = {
    'signatories':'полномочия подписантов', 'object_attachments':'документы объекта',
    'resource_attachments':'документы ресурсов', 'scheme_attachments':'приложения схем',
    'act_attachments':'приложения актов', 'resource_sources':'источники спецификации',
    'specification_pending':'строки спецификации', 'work_facts':'факты монтажа',
    'package_requirements':'состав комплекта', 'quality_reviews':'проверки качества',
    'workspace_entries':'записи журналов', 'supplies':'поставки', 'resource_imports':'импорт ведомости',
}


def source_files(c, pid):
    return [dict(r) for r in c.execute('SELECT DISTINCT a.* FROM attachments a JOIN project_attachments p ON p.attachment_id=a.id WHERE p.project_id=? ORDER BY a.id', (pid,))]


def _folders(c, database, pid):
    p = c.execute('SELECT p.section_code,o.name,o.id AS object_id FROM projects p JOIN objects o ON o.id=p.object_id WHERE p.id=?', (pid,)).fetchone()
    if not p:
        raise ValueError('Выберите раздел')
    workspace = database_workspace(database)
    folder = document_root(workspace)/path_component(p['name'])/path_component(p['section_code'])
    for directory, marker, identity in ((folder.parent, '.itd-object.json', {'object_id': p['object_id']}), (folder, '.itd-project.json', {'project_id': pid})):
        _safe(workspace, directory)
        marker = directory/marker
        if marker.is_symlink():
            raise ValueError('Служебная привязка папки заменена ссылкой')
        if marker.exists() and json.loads(marker.read_text(encoding='utf-8')) != identity:
            raise ValueError('Папка закреплена за другим объектом или разделом')
    return workspace, [folder/'Исходные файлы', folder/'Рабочая документация']


def _safe(workspace, path):
    path = Path(path).absolute()
    roots = (workspace, document_root(workspace), *previous_itd_roots.get())
    base = next((root for root in roots if path.is_relative_to(root) and path.resolve().is_relative_to(root)), None)
    if base is None:
        raise ValueError('Путь файла находится вне рабочей папки')
    for part in (path, *path.parents):
        if part == base:
            break
        if part.is_symlink():
            raise ValueError('Ссылки вместо файлов и каталогов не обрабатываются')
    return path


def _state(workspace, path):
    _safe(workspace, path)
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError('Ожидался обычный файл: '+str(path.name))
    return archive.digest(path)


def _references(c, aid):
    refs = []
    for table, in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        for fk in c.execute(f'PRAGMA foreign_key_list("{table}")'):
            if fk['table'] == 'attachments':
                rows = [dict(r) for r in c.execute(f'SELECT * FROM "{table}" WHERE "{fk["from"]}"=?', (aid,))]
                if rows:
                    refs.append({'table': table, 'rows': rows})
    return refs


def _build(c, database, pid, purpose, aid):
    if purpose not in ('check', 'delete'):
        raise ValueError('Неизвестная операция с файлами')
    workspace, folders = _folders(c, database, pid)
    records = source_files(c, pid)
    if purpose == 'delete':
        records = [r for r in records if r['id'] == aid]
        if not records:
            raise ValueError('Файл не связан с выбранным разделом')
    disk = {}
    if purpose in ('check', 'delete'):
        def scan(folder):
            _safe(workspace, folder)
            if not folder.exists():
                return
            for path in sorted(folder.iterdir()):
                if path.name.startswith('.'):
                    continue
                _safe(workspace, path)
                if path.is_dir():
                    scan(path)
                elif path.is_file():
                    disk[relative_or_absolute(workspace,path)] = archive.digest(path)
                else:
                    raise ValueError('Не удалось проверить файл: '+path.name)
        for folder in folders:
            scan(folder)
    tree = document_root(workspace)
    relative_folders = [folder.relative_to(tree) for folder in folders]
    mapped_folders = [root / relative for root in (tree, workspace/'ИТД', *previous_itd_roots.get())
                      for relative in relative_folders]
    actions, blocked, snapshot = [], [], []
    known = {r['sha256']: dict(r) for r in c.execute('SELECT * FROM attachments ORDER BY id')}
    for r in records:
        mappings = [dict(m) for m in c.execute('SELECT * FROM project_files WHERE attachment_id=? AND project_id=? ORDER BY path', (r['id'], pid))]
        if any(not any((workspace/m['path']).is_relative_to(folder) for folder in mapped_folders) for m in mappings):
            raise ValueError('Привязка файла находится вне стандартных папок раздела')
        states = {m['path']: _state(workspace, workspace/m['path']) for m in mappings}
        archived = archive.archived_path(Path(database).parent/'archive', r['storage_path'])
        _safe(workspace,Path(database).parent/'archive'/r['storage_path'])
        archive_state = _state(workspace, archived)
        refs = _references(c, r['id'])
        snapshot.append({'record': r, 'mappings': mappings, 'states': states, 'archive': archive_state, 'refs': refs})
        matching = [p for p, sha in disk.items() if sha == r['sha256']]
        if purpose == 'check' and matching:
            if archive_state is None:
                actions.append({'action':'repair','id':r['id'],'name':r['original_name'],'path':matching[0],'sha256':r['sha256'],'type':archive.file_type(r)})
            elif archive_state != r['sha256']:
                blocked.append({'id':r['id'],'name':r['original_name'],'reason':'Архивная копия изменена. Требуется ручная проверка.'})
            continue
        if purpose == 'check' and not mappings and archive_state == r['sha256']:
            actions.append({'action': 'restore', 'id': r['id'], 'name': r['original_name'], 'type': archive.file_type(r)})
            continue
        if purpose == 'check' and any(sha == r['sha256'] for sha in states.values()):
            continue
        # Resource links also survive deletion of incoming journal entries.
        # An explicit file deletion may clear these links in this section;
        # reconciliation and references to actual business records stay protected.
        resource_ids = [row['resource_id'] for ref in refs if ref['table'] == 'resource_attachments' for row in ref['rows']]
        local_resources = {row[0] for row in c.execute('SELECT id FROM resources WHERE project_id=?', (pid,))}
        clear_resource_links = purpose == 'delete' and set(resource_ids) <= local_resources
        removable = {'project_attachments', 'project_files'}
        if clear_resource_links:
            removable.add('resource_attachments')
        protected = [ref['table'] for ref in refs if ref['table'] not in removable]
        if protected:
            blocked.append({'id': r['id'], 'name': r['original_name'], 'reason': 'Используется в записях ИТД: '+', '.join(REFERENCE_NAMES.get(table,'связанные записи') for table in protected)})
            continue
        if any(sha is not None and sha != r['sha256'] for sha in states.values()) or archive_state not in (None, r['sha256']):
            blocked.append({'id': r['id'], 'name': r['original_name'], 'reason': 'Содержимое изменено. Файл сохранён для ручной проверки.'})
            continue
        shared = any(row['project_id'] != pid for ref in refs for row in ref['rows'] if ref['table'] in ('project_attachments', 'project_files'))
        paths = sorted(set([p for p, sha in states.items() if sha == r['sha256']]+matching))
        if not shared and archive_state:
            paths.append(str(archived.relative_to(workspace)))
        actions.append({'action': 'detach' if shared else 'remove', 'id': r['id'], 'name': r['original_name'], 'paths': paths, 'sha256': r['sha256'], 'type': archive.file_type(r)})
        if clear_resource_links and resource_ids:
            actions[-1]['unlink_resources'] = sorted(resource_ids)
    if purpose == 'check':
        for path, sha in disk.items():
            existing = known.get(sha)
            tracked = c.execute('SELECT attachment_id FROM project_files WHERE project_id=? AND path=?', (pid, path)).fetchone()
            if tracked and existing and tracked[0] == existing['id']:
                continue
            actions.append({'action': 'add', 'name': Path(path).name, 'path': path, 'sha256': sha,
                            'type': archive.file_type(existing) if existing else ('rd' if (workspace/path).is_relative_to(folders[1]) else 'other'),
                            'existing': existing['id'] if existing else None})
    # Includes every dependency and byte hash used to decide a destructive action.
    stamp = hashlib.sha256(_encode({'snapshot': snapshot, 'disk': disk, 'known': list(known.values())})).hexdigest()
    return {'project_id': pid, 'purpose': purpose, 'attachment_id': aid, 'actions': actions, 'blocked': blocked, 'stamp': stamp}


def _binary_snapshot(value):
    # Linked import records contain BLOBs. Fingerprint their bytes without
    # copying binary content into JSON or dropping it from stale-plan checks.
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {'$binary': {'sha256': hashlib.sha256(value).hexdigest(), 'size': len(value)}}
    raise TypeError(f'Object of type {type(value).__name__} is not JSON serializable')


def _encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=_binary_snapshot).encode()


def _signature(plan, secret):
    return hmac.new(secret.encode(), _encode(plan), hashlib.sha256).hexdigest()


def _recover(c, database):
    workspace = database_workspace(database)
    for row in c.execute("SELECT * FROM file_operations WHERE state IN ('pending','applied')").fetchall():
        if not re.fullmatch(r'[0-9a-f]{32}',row['id']):
            raise ValueError('Повреждён идентификатор операции восстановления')
        stage = Path(database).parent/'work'/'file-operations'/row['id']
        _safe(workspace, stage)
        for move in json.loads(row['moves_json']):
            if not re.fullmatch(r'[0-9]+-[0-9]+',move['saved']):
                raise ValueError('Повреждён путь восстановления')
            original = _safe(workspace, workspace/move['path'])
            if not any(original.is_relative_to(root) for root in (document_root(workspace), workspace/'ИТД', *previous_itd_roots.get(), Path(database).parent/'archive')):
                raise ValueError('Восстановление разрешено только для исходных файлов')
            saved = _safe(workspace, stage/move['saved'])
            if not saved.exists():
                continue
            if _state(workspace, saved) != move['sha256']:
                raise ValueError('Файл восстановления изменён; требуется ручная проверка')
            if row['state'] == 'applied':
                saved.unlink()
            elif not original.exists():
                original.parent.mkdir(parents=True, exist_ok=True)
                # link is exclusive: never replace a concurrently created user file.
                os.link(saved, original)
                saved.unlink()
            else:
                raise ValueError('Восстановление ожидает освобождения пути: '+move['path'])
        if row['state'] == 'pending':
            c.execute("UPDATE file_operations SET state='rolled_back' WHERE id=?", (row['id'],))
        if stage.exists() and not any(stage.iterdir()):
            stage.rmdir()
    c.commit()


def make_plan(database, project_id, purpose='check', attachment_id=None, secret=''):
    with _LOCK, connect(database, transaction=False) as c:
        _recover(c, database)
        plan = _build(c, database, project_id, purpose, attachment_id)
        return {'plan': plan, 'token': _signature(plan, secret)}


def apply_plan(database, plan, token, types, secret):
    if not isinstance(plan, dict) or not isinstance(token, str) or not hmac.compare_digest(_signature(plan, secret), token):
        raise ValueError('Недействительный план проверки файлов')
    if not isinstance(types, dict) or any(v not in KINDS for v in types.values()):
        raise ValueError('Неизвестный тип файла')
    with _LOCK, connect(database, transaction=False) as c:
        _recover(c, database)
        current = _build(c, database, plan['project_id'], plan['purpose'], plan['attachment_id'])
        if current != plan:
            raise ValueError('Файлы или записи изменились. Повторите проверку.')
        workspace = database_workspace(database)
        op = uuid.uuid4().hex
        stage = Path(database).parent/'work'/'file-operations'/op
        moves = [{'path': path, 'sha256': a['sha256'], 'saved': str(i)+'-'+str(j)} for i, a in enumerate(plan['actions']) for j, path in enumerate(a.get('paths', []))]
        for move in moves:
            if (workspace / move['path']).stat().st_dev != Path(database).parent.stat().st_dev:
                raise ValueError('Для безопасного удаления файлов папка ИТД и БД должны находиться на одном томе')
        c.execute("INSERT INTO file_operations(id,state,moves_json) VALUES(?,'pending',?)", (op, json.dumps(moves)))
        c.commit()
        try:
            c.execute('BEGIN IMMEDIATE')
            if _build(c, database, plan['project_id'], plan['purpose'], plan['attachment_id']) != plan:
                raise ValueError('Файлы изменились. Повторите проверку.')
            if moves:
                _safe(workspace, stage)
                stage.mkdir(parents=True)
            for move in moves:
                source = _safe(workspace, workspace/move['path'])
                if _state(workspace, source) != move['sha256']:
                    raise ValueError('Файл изменён во время удаления')
                os.replace(source, stage/move['saved'])
                if archive.digest(stage/move['saved']) != move['sha256']:
                    raise ValueError('Файл изменён во время удаления')
            for a in plan['actions']:
                pid = plan['project_id']
                if a['action'] in ('remove', 'detach'):
                    before = dict(c.execute('SELECT * FROM attachments WHERE id=?', (a['id'],)).fetchone())
                    c.execute('DELETE FROM project_files WHERE project_id=? AND attachment_id=?', (pid, a['id']))
                    c.execute('DELETE FROM project_attachments WHERE project_id=? AND attachment_id=?', (pid, a['id']))
                    for resource_id in a.get('unlink_resources', []):
                        c.execute('DELETE FROM resource_attachments WHERE resource_id=? AND attachment_id=?', (resource_id, a['id']))
                    if a['action'] == 'remove':
                        c.execute('DELETE FROM attachments WHERE id=?', (a['id'],))
                    log_event(c, 'file-'+a['action'], entity='attachments', entity_id=a['id'], before=before, after={'project_id': pid})
                elif a['action'] == 'repair':
                    original=c.execute('SELECT storage_path FROM attachments WHERE id=?',(a['id'],)).fetchone()
                    target=archive.archived_path(Path(database).parent/'archive',original[0])
                    _safe(workspace,target)
                    source=_safe(workspace,workspace/a['path'])
                    if _state(workspace,source)!=a['sha256']:
                        raise ValueError('Исходный файл изменился')
                    # Make an independent temporary copy, then publish without replacement.
                    import shutil
                    import tempfile
                    target.parent.mkdir(parents=True,exist_ok=True)
                    fd,temp_name=tempfile.mkstemp(prefix='.repair-',dir=target.parent)
                    os.close(fd)
                    temp=Path(temp_name)
                    try:
                        shutil.copyfile(source,temp)
                        if archive.digest(temp)!=a['sha256']:
                            raise ValueError('Файл изменился при восстановлении архива')
                        os.link(temp,target)
                    finally:
                        temp.unlink(missing_ok=True)
                elif a['action'] == 'restore':
                    archive.publish_project_file(c, attachment_id=a['id'], project_id=pid, archive_root=Path(database).parent/'archive')
                elif a['action'] == 'add':
                    source = _safe(workspace, workspace/a['path'])
                    if _state(workspace, source) != a['sha256']:
                        raise ValueError('Файл изменился при добавлении')
                    kind = a['type'] if a['existing'] or a['type'] == 'rd' else types.get(a['path'], a['type'])
                    result = archive.import_file(c, archive_root=Path(database).parent/'archive', source=source, doc_type=kind, title=a['name'])
                    if c.execute('SELECT sha256 FROM attachments WHERE id=?', (result['id'],)).fetchone()[0] != a['sha256']:
                        raise ValueError('Файл изменился при импорте')
                    archive.link_file(c, attachment_id=result['id'], entity='project', entity_id=pid)
                    c.execute('INSERT INTO project_files VALUES(?,?,?) ON CONFLICT(project_id,path) DO UPDATE SET attachment_id=excluded.attachment_id', (pid, result['id'], a['path']))
            log_event(c, 'file-check', entity='projects', entity_id=plan['project_id'], after=plan['actions'])
            c.execute("UPDATE file_operations SET state='applied' WHERE id=?", (op,))
            c.commit()
        except Exception:
            c.rollback()
            _recover(c, database)
            raise
        try:
            _recover(c, database)
            cleanup_pending = False
        except OSError:
            cleanup_pending = True
        return {'ok': True, 'changed': len(plan['actions']), 'blocked': len(plan['blocked']), 'cleanup_pending': cleanup_pending}
