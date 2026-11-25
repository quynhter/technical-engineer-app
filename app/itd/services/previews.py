"""Private, expiring proposals. Only the authenticated web service can replay them."""
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import time
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from . import specification_preview
from .context import scope
from .permissions import require
from .preview_operations import protect_transaction, run_row, savepoint
from ..assistant_files import AttachmentError, MAX_BYTES
from ..db import connect
from ..deletion import FIELD_LABELS, LABELS, quote
from ..read_audit import record


TTL = 30 * 60
LOG = logging.getLogger('itd.db')
TRANSIENT_TABLES = {'audit_events', 'agent_state', 'removed_storage_files'}
TABLE_LABELS = {**LABELS, 'document_templates': 'Загруженные шаблоны', 'document_types': 'Формы',
                'files': 'Сохранённые файлы', 'project_attachments': 'Связи исходных файлов с разделом'}
COLUMN_LABELS = {**FIELD_LABELS, 'name': 'Наименование', 'title': 'Заголовок', 'id': 'Код записи',
                 'spec_num': 'Позиция', 'quantity': 'Количество', 'unit': 'Ед. изм.',
                 'qty_proj': 'Проектное количество', 'qty_fact': 'Фактическое количество',
                 'note': 'Примечание', 'status': 'Статус', 'revision': 'Ревизия',
                 'source': 'Источник', 'entry_date': 'Дата записи', 'work_fields': 'Поля журнала',
                 'fields': 'Поля формы', 'sha256': 'SHA-256', 'category': 'Категория',
                 'original_name': 'Имя оригинала', 'storage_path': 'Путь в архиве'}


class Confirmation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    project_id: int = Field(gt=0)
    preview_id: str = Field(pattern=r'^[0-9a-f]{32}$')
    preview_hash: str = Field(pattern=r'^[0-9a-f]{64}$')


class PreviewConflict(ValueError):
    """The submitted confirmation can no longer be used."""


@dataclass(frozen=True)
class Prepared:
    view: dict
    payload: dict


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def checksum(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def read_only(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    return closing(connection)


def database_identity(database):
    stat = database.stat()
    return checksum([str(database.resolve()), stat.st_dev, stat.st_ino])


def snapshot(connection):
    tables = connection.execute(
        "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    result = {}
    for (table,) in tables:
        if table in TRANSIENT_TABLES:
            continue
        columns = list(connection.execute('PRAGMA table_info(' + quote(table) + ')'))
        keys = [col['name'] for col in sorted(columns, key=lambda col: col['pk']) if col['pk']]
        if table == 'files':
            # Storage UUIDs are generated independently on preview and replay.
            keys = ['project_id', 'attachment_id', 'release_id']
        ordering = ','.join(quote(key) for key in keys) if keys else 'rowid'
        records = connection.execute(f'SELECT {"" if keys else "rowid AS __rowid,"}* '
                                     f'FROM {quote(table)} ORDER BY {ordering}')
        result[table] = {
            tuple(row[key] for key in keys or ('__rowid',)): {
                key: (value if not isinstance(value, bytes) else {'sha256': hashlib.sha256(value).hexdigest(),
                                                                 'bytes': len(value)})
                for key, value in dict(row).items()
            } for row in records
        }
    return result


def state_hash(state):
    digest = hashlib.sha256()
    for table, rows in state.items():
        digest.update(encode(table).encode() + b'\n')
        for identity, record in rows.items():
            digest.update(encode([identity, record]).encode() + b'\n')
    return digest.hexdigest()


def shown(row, table):
    hidden = {'__rowid', 'created_at'}
    if table == 'files':
        hidden.add('id')
    parsed = {}
    for key, value in (row or {}).items():
        if key in hidden:
            continue
        if isinstance(value, str) and (key.endswith('_json') or key in ('fields', 'work_fields', 'mapping')):
            try:
                value = json.loads(value)
            except ValueError:
                pass
        parsed[key] = value
    return parsed


def changes(before, after):
    result = []
    for table, old_rows in before.items():
        new_rows = after[table]
        for identity in dict.fromkeys((*old_rows, *new_rows)):
            old = shown(old_rows.get(identity), table)
            new = shown(new_rows.get(identity), table)
            if old == new:
                continue
            fields = [
                {'name': key, 'label': COLUMN_LABELS.get(key, key), 'before': old.get(key), 'after': new.get(key)}
                for key in dict.fromkeys((*old, *new))
                if old.get(key) != new.get(key)
            ]
            result.append({'table': table, 'label': TABLE_LABELS.get(table, table),
                           'id': old.get('id', new.get('id', ' / '.join(str(v) for v in identity if v is not None))),
                           'caption': next((name for key in ('name', 'title', 'original_name', 'act_num', 'description')
                                            if isinstance(name := (new or old).get(key), str) and name), None),
                           'action': 'update' if old and new else 'insert' if new else 'delete',
                           'fields': fields})
    if len(result) > 5000 or len(encode(result).encode()) > 8 * 1024 * 1024:
        raise ValueError('Изменений слишком много для одного предпросмотра.')
    return result


@contextmanager
def shadow(ctx):
    """SQLite backup includes the committed WAL snapshot. Domain files stay isolated."""
    with TemporaryDirectory(prefix='itd-write-preview-') as folder:
        database = Path(folder) / 'preview.db'
        with read_only(ctx.database) as source, closing(sqlite3.connect(database)) as target:
            source.backup(target)
        staged = ctx.model_copy(update={'database': database, 'root': Path(folder) / 'ИТД',
                                        'previous_roots': ()})
        with connect(database, cleanup_removed_files=False) as connection:
            connection.preview_origin = ctx.database
            yield connection, staged


def resolve_batch_files(rows, actor, attachments, *, incoming):
    total = 0
    for row in rows:
        for item in row.get('resources', []) if incoming else (row,):
            if item.get('file') is None:
                continue
            item['file'], content = specification_preview.resolve_file(item['file'], actor, attachments)
            total += len(content)
            if total > MAX_BYTES:
                raise AttachmentError('Общий размер вложений превышает 4 МиБ.')


def run(c, ctx, actor, payload, *, dry_run):
    name = payload['tool'].removeprefix('preview-')
    pid = payload['project_id']
    checks, warnings = [], []
    with scope(ctx, actor), protect_transaction(c):
        if name == 'specification':
            report = specification_preview.save(c, ctx, pid, payload['specification'])
            by_key = set(report['pending'])
            for row in payload['specification_rows']:
                if row['source_key'] in by_key and not row['missing']:
                    warnings.append({'row': row['row'], 'message': 'Позиция уже существует. Нужна сверка редакции.'})
                elif row['missing']:
                    warnings.append({'row': row['row'], 'message': 'Строка не добавится. Уточните: ' + ', '.join(row['missing']) + '.'})
            if report['duplicates']:
                warnings.append({'message': f"Уже зарегистрировано строк: {len(report['duplicates'])}."})
            return [{'status': 'ok', 'message': 'Файл и позиции проверены.'}], warnings
        for index, row in enumerate(payload['rows'], 1):
            notes = []
            try:
                with savepoint(c, 'preview_row'):
                    run_row(c, ctx, actor, pid, name, json.loads(encode(row)), notes)
            except (ValueError, sqlite3.IntegrityError) as error:
                if not dry_run:
                    raise
                message = str(error) if isinstance(error, ValueError) else 'Нарушена целостность или уникальность записи.'
                checks.append({'row': index, 'status': 'error', 'message': message})
            else:
                checks.append({'row': index, 'status': 'ok', 'message': 'Проверено.'})
                warnings.extend({'row': index, **note} for note in notes)
    return checks, warnings


def prepare(ctx, actor, name, label, data, *, versions, attachments=None):
    require(actor, 'editor')
    if actor.source not in ('assistant', 'mcp'):
        raise PermissionError('Предпросмотр доступен через ассистент или MCP.')
    pid = data.project_id
    identity = uuid4().hex
    payload = {'tool': name, 'project_id': pid, 'preview_id': identity,
               'db_identity': database_identity(ctx.database), 'namespace': ctx.accounts_namespace,
               'owner': str(actor.user_id), 'source': actor.source, 'versions': versions}
    preview_warnings = []
    if name == 'preview-specification':
        spec, rows, preview_warnings = specification_preview.prepare(data, actor, attachments)
        payload.update(specification=spec, specification_rows=rows)
    else:
        payload['rows'] = data.model_dump(mode='json', exclude_unset=True)['rows']
        resolve_batch_files(payload['rows'], actor, attachments, incoming=name == 'preview-incoming-control')
        if name == 'preview-document-templates':
            from .preview_templates import assign_codes
            assign_codes(payload['rows'])
    with shadow(ctx) as (c, staged):
        if not c.execute('SELECT 1 FROM schema_migrations WHERE version=25').fetchone():
            raise ValueError('Сначала обновите схему выбранной БД до миграции 025.')
        section = c.execute('SELECT name, section_code FROM projects WHERE id=?', (pid,)).fetchone()
        if not section:
            raise ValueError('Раздел РД не найден.')
        before = snapshot(c)
        checks, warnings = run(c, staged, actor, payload, dry_run=True)
        delta = changes(before, snapshot(c))
    payload.update(state_hash=state_hash(before), checked_warnings=warnings, expires_at=int(time.time()) + TTL)
    section_label = f"{section['section_code']} «{section['name']}»"
    applicable = bool(delta) and all(check['status'] == 'ok' for check in checks)
    view = {'dry_run': True, 'preview_id': identity, 'project_id': pid, 'tool': name,
            'section': section_label, 'title': label, 'source': actor.source, 'applicable': applicable, 'checks': checks,
            'warnings': [*({'message': warning} for warning in preview_warnings), *warnings],
            'changes': delta, 'expires_at': datetime.fromtimestamp(payload['expires_at'], timezone.utc).isoformat()}
    if name == 'preview-specification':
        view['specification'] = {'rows': rows, 'file': {key: spec['file'][key] for key in ('name', 'sha256')}}
    return Prepared(view, payload)


def proposal_path(database):
    return Path(str(database.resolve()) + '.previews.sqlite3')


def persist(database, prepared, audit):
    """Store private payload and preview audit under the same SQLite transaction."""
    path = proposal_path(database)
    if path.is_symlink():
        raise OSError('Недопустимый файл предпросмотров.')
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        pass
    else:
        os.close(fd)
    audit.execute('ATTACH DATABASE ? AS proposals', (str(path),))
    audit.execute('''CREATE TABLE IF NOT EXISTS proposals.write_previews (
        id TEXT PRIMARY KEY, namespace TEXT NOT NULL, owner TEXT NOT NULL, project_id INTEGER NOT NULL,
        expires_at INTEGER NOT NULL, hash TEXT NOT NULL, payload TEXT NOT NULL, view TEXT NOT NULL)''')
    audit.execute('''CREATE INDEX IF NOT EXISTS proposals.write_previews_owner
                     ON write_previews(namespace, owner, project_id, expires_at)''')
    payload, view = prepared.payload, prepared.view
    audit.execute('DELETE FROM proposals.write_previews WHERE expires_at <= ?', (int(time.time()),))
    audit.execute('INSERT INTO proposals.write_previews VALUES (?,?,?,?,?,?,?,?)', (
        payload['preview_id'], payload['namespace'], payload['owner'], payload['project_id'],
        payload['expires_at'], checksum([payload, view]), encode(payload), encode(view)))


def web_only(actor):
    require(actor, 'editor')
    if actor.source != 'web':
        raise PermissionError('Предпросмотр подтверждается в веб-интерфейсе.')


def find_proposal(ctx, actor, project_id, identity, *, include_payload=False):
    path = proposal_path(ctx.database)
    if not path.is_file():
        return None
    with read_only(path) as c:
        if not c.execute("SELECT 1 FROM sqlite_schema WHERE name='write_previews'").fetchone():
            return None
        columns = 'expires_at, hash, view, payload' if include_payload else 'expires_at, hash, view'
        return c.execute(f'''SELECT {columns} FROM write_previews
                            WHERE id=? AND namespace=? AND owner=? AND project_id=?''',
                         (identity, ctx.accounts_namespace, str(actor.user_id), project_id)).fetchone()


def list_proposals(ctx, actor, project_id):
    path = proposal_path(ctx.database)
    if not path.is_file():
        return []
    fields = ('tool', 'title', 'section', 'source', 'applicable', 'expires_at')
    with read_only(path) as c:
        if not c.execute("SELECT 1 FROM sqlite_schema WHERE name='write_previews'").fetchone():
            return []
        c.execute('ATTACH DATABASE ? AS business', (ctx.database.resolve().as_uri() + '?mode=ro',))
        c.execute('PRAGMA query_only=ON')
        # Exclude receipts before limiting the list. SQLite returns only display fields.
        rows = c.execute('''SELECT p.id, json_extract(p.view, ?, ?, ?, ?, ?, ?) AS summary
            FROM write_previews p
            WHERE p.namespace=? AND p.owner=? AND p.project_id=? AND p.expires_at>?
              AND NOT EXISTS (SELECT 1 FROM business.audit_events e WHERE e.preview_id=p.id)
            ORDER BY p.expires_at DESC, p.rowid DESC LIMIT 100''',
            (*('$.' + key for key in fields), ctx.accounts_namespace, str(actor.user_id),
             project_id, int(time.time())))
        return [{'preview_id': row['id'], 'project_id': project_id,
                 **dict(zip(fields, json.loads(row['summary']), strict=True))} for row in rows]


def record_applied(c, actor, payload):
    """The unique audit event is also the single-use receipt in the same commit."""
    meta = payload['versions']
    c.execute('''INSERT INTO audit_events
        (operation,entity,entity_id,actor_id,actor_role,source,result,preview_id,
         knowledge_version,skills_version,index_status)
        VALUES ('write-preview-apply','projects',?,?,?,'web','success',?,?,?,?)''',
        (payload['project_id'], str(actor.user_id), actor.role, payload['preview_id'],
         meta['knowledge_version'], meta['skills_version'], meta['index_status']))


def is_applied(c, identity):
    return bool(c.execute('SELECT 1 FROM audit_events WHERE preview_id=?', (identity,)).fetchone())


def rollback_files(c):
    from ..custom_templates import write_file
    for _, _, path, previous in reversed(c.template_changes):
        write_file(path, previous)
    c.template_changes.clear()
    for original in reversed(c.preview_new_originals):
        original.unlink(missing_ok=True)


def cleanup_storage(c):
    from ..storage import cleanup_removed
    try:
        if c.execute('SELECT 1 FROM removed_storage_files LIMIT 1').fetchone():
            cleanup_removed(c)
    except (OSError, sqlite3.Error, ValueError):
        c.rollback()
        LOG.warning('Предпросмотр применён. Очистка storage ожидает повтора.')


def get(ctx, actor, project_id, identity=None):
    web_only(actor)
    if not identity:
        return {'previews': list_proposals(ctx, actor, project_id)}
    stored = find_proposal(ctx, actor, project_id, identity)
    if stored is None:
        raise ValueError('Предпросмотр недоступен для этого раздела и пользователя.')
    with read_only(ctx.database) as c:
        return {**json.loads(stored['view']), 'preview_hash': stored['hash'],
                'expired': stored['expires_at'] <= int(time.time()), 'applied': is_applied(c, identity)}


def apply(ctx, actor, data):
    from ..tools import versions

    identity = None
    project_id = 0
    payload = {}
    with scope(ctx, actor):
        try:
            web_only(actor)
            try:
                confirmation = Confirmation.model_validate(data)
            except ValueError as error:
                raise ValueError('Некорректное подтверждение предпросмотра.') from error
            identity, project_id = confirmation.preview_id, confirmation.project_id
            stored = find_proposal(ctx, actor, project_id, identity, include_payload=True)
            if stored is None:
                raise PreviewConflict('Предпросмотр недоступен для этого раздела и пользователя.')
            payload, view = json.loads(stored['payload']), json.loads(stored['view'])
            if not hmac.compare_digest(stored['hash'], confirmation.preview_hash) or \
                    not hmac.compare_digest(stored['hash'], checksum([payload, view])):
                raise PreviewConflict('Хеш предпросмотра устарел. Откройте предпросмотр заново.')
            with connect(ctx.database, transaction=False, cleanup_removed_files=False) as c:
                c.execute('BEGIN IMMEDIATE')
                c.preview_new_originals = []
                try:
                    if (stored['expires_at'] != payload['expires_at']
                            or payload['expires_at'] <= int(time.time())):
                        raise PreviewConflict('Срок предпросмотра истёк. Подготовьте новый.')
                    if is_applied(c, identity):
                        raise PreviewConflict('Предпросмотр уже применён.')
                    if not view['applicable']:
                        raise PreviewConflict('Исправьте ошибки или подготовьте предпросмотр с изменениями.')
                    before = snapshot(c)
                    if (payload['db_identity'] != database_identity(ctx.database)
                            or state_hash(before) != payload['state_hash']):
                        raise PreviewConflict('Данные изменились после предпросмотра. Подготовьте новый.')
                    _, warnings = run(c, ctx, actor, payload, dry_run=False)
                    if changes(before, snapshot(c)) != view['changes'] or warnings != payload['checked_warnings']:
                        raise PreviewConflict('Результат изменился после предпросмотра. Подготовьте новый.')
                    record_applied(c, actor, payload)
                    c.commit()
                except Exception:
                    rollback_files(c)
                    raise
                cleanup_storage(c)
        except Exception as error:
            meta = payload.get('versions')
            if not meta:
                try:
                    meta = versions(ctx)
                except Exception:
                    meta = {key: 'unavailable' for key in ('knowledge_version', 'skills_version', 'index_status')}
            record(ctx.database, 'write-preview-apply', project_id=project_id, release_ids=[],
                   source=actor.source, user_id=actor.user_id, result='denied' if isinstance(error, PermissionError)
                   else 'rejected' if isinstance(error, ValueError) else 'error', versions=meta, preview_id=identity)
            raise
    return {'applied': True, 'preview_id': identity, 'project_id': project_id, 'changes': len(view['changes'])}
