"""Install the shipped document templates during database preparation."""
import base64
from hashlib import sha256
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from ..changes import log_event
from ..custom_templates import TEMPLATE_CODE, field_shape, inspect_doc, template_operation, write_file
from ..db import connect
from ..paths import default_templates
from .context import Actor, ServiceContext
from .operations import operation
from .permissions import Policy


def read_bundle(path):
    def content(archive, item):
        value = archive.read(item['path'])
        if sha256(value).hexdigest() != item['sha256']:
            raise ValueError(f'Нарушена целостность файла архива: {item["path"]}')
        return value

    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            if len({item.filename for item in members}) != len(members) or sum(
                item.file_size for item in members
            ) > 64 * 1024 * 1024:
                raise ValueError('Недопустимый состав архива шаблонов')
            manifest = json.loads(archive.read('manifest.json'))
            if manifest['format'] != 1:
                raise ValueError('Неизвестный формат архива шаблонов')
            native = [(item['path'], content(archive, item)) for item in manifest['native']]
            templates = [(item, content(archive, item)) for item in manifest['templates']]
            keys = {(item['form_set'], item['original_name']) for item, _ in templates}
            if len(keys) != len(templates):
                raise ValueError('В архиве повторяются пользовательские шаблоны')
            if any(not isinstance(group, str) or not group.strip() or not isinstance(name, str)
                   or not name.lower().endswith('.docx') or '/' in name or '\\' in name
                   for group, name in keys):
                raise ValueError('Недопустимое имя пользовательского шаблона в архиве')
            return native, templates
    except (BadZipFile, KeyError, TypeError) as error:
        raise ValueError('Не удалось прочитать архив шаблонов') from error


def _extract_native(native, directory):
    paths = []
    for location, data in native:
        path = Path(location)
        if ('\\' in location or len(path.parts) != 2
                or (path.parts[0], path.suffix) not in {('templates', '.docx'), ('forms', '.xlsx')}):
            raise ValueError('Недопустимый путь штатного файла в архиве шаблонов')
        folder = directory if path.parts[0] == 'templates' else directory.parent / 'forms'
        paths.append((folder / path.name, data))
    for path, data in paths:
        if not path.exists() and not path.is_symlink():
            path.parent.mkdir(parents=True, exist_ok=True)
            write_file(path, data)


def _install_template(connection, directory, item, data):
    key = item['form_set'], item['original_name']
    installed = connection.execute('''SELECT b.*, t.deleted, t.revision AS current_revision
        FROM bundled_document_templates b JOIN document_templates t USING(code)
        WHERE b.form_set=? AND b.original_name=?''', key).fetchone()
    if installed:
        if installed['deleted'] or installed['revision'] != installed['current_revision']:
            return False
        path = _template_file(directory, installed['code'])
        if path.is_symlink():
            return False
        predecessors = item.get('replaces', {})
        if (installed['sha256'] in predecessors
                and _unused_with_original_fields(connection, installed['code'], predecessors[installed['sha256']])):
            _replace_installed(connection, directory, path, installed, item, data)
        elif not path.exists() and installed['sha256'] == item['sha256']:
            write_file(path, data)
        return False

    existing = connection.execute('''SELECT code, revision, deleted FROM document_templates
        WHERE form_set=? AND original_name=? ORDER BY deleted, revision DESC, code LIMIT 1''', key).fetchone()
    if existing:
        code, revision = existing['code'], existing['revision']
        path = _template_file(directory, code)
        digest = (item['sha256'] if not existing['deleted'] and path.is_file() and not path.is_symlink()
                  and sha256(path.read_bytes()).hexdigest() == item['sha256'] else None)
    else:
        payload = {**item, 'content': base64.b64encode(data).decode()}
        code = template_operation(connection, 'save', payload, directory)['code']
        revision, digest = 1, item['sha256']
    connection.execute('''INSERT INTO bundled_document_templates(form_set,original_name,code,sha256,revision)
        VALUES (?,?,?,?,?)''', (*key, code, digest, revision))
    return existing is None


def _replace_installed(connection, directory, path, installed, item, data):
    payload = {**item, 'code': installed['code'], 'revision': installed['revision']}
    digest = item['sha256']
    if not path.exists():
        payload['content'] = base64.b64encode(data).decode()
    elif path.is_file():
        content = path.read_bytes()
        if sha256(content).hexdigest() == installed['sha256']:
            if installed['sha256'] != digest:
                payload['content'] = base64.b64encode(data).decode()
        elif installed['sha256'] == digest:
            # A settings-only correction can keep an edited DOCX with extra fields.
            try:
                detected = inspect_doc(content)
            except ValueError:
                return
            bundled = {field['key']: field for field in item['fields']}
            if field_shape([field for field in detected if field['key'] in bundled]) != field_shape(item['fields']):
                return
            payload['fields'] = [bundled.get(field['key'], field) for field in detected]
            digest = None
        else:
            return
    else:
        return
    template_operation(connection, 'save', payload, directory)
    connection.execute('UPDATE bundled_document_templates SET sha256=?,revision=revision+1 WHERE code=?',
                       (digest, installed['code']))


def _unused_with_original_fields(connection, code, digest):
    row = connection.execute('''SELECT fields FROM document_types WHERE code=?
        AND NOT EXISTS (SELECT 1 FROM acts WHERE act_type=document_types.code)''', (code,)).fetchone()
    return row is not None and sha256(row['fields'].encode()).hexdigest() == digest


def _template_file(directory, code):
    if not TEMPLATE_CODE.fullmatch(code):
        raise ValueError('Недопустимый код шаблона в БД')
    return directory / (code + '.docx')


def install_bundle(database, path, directory=None):
    native, templates = read_bundle(path)
    directory = directory or default_templates()
    directory.mkdir(parents=True, exist_ok=True)
    _extract_native(native, directory)
    ctx = ServiceContext(database=database, templates=directory)
    actor = Actor(user_id='template-bundle', role='admin', source='background')
    name = 'install-template-bundle'
    with operation(ctx, actor, name, Policy('admin', True)), connect(
        database, transaction=False, cleanup_removed_files=False,
    ) as connection:
        connection.execute('BEGIN IMMEDIATE')
        installed = sum(_install_template(connection, directory, item, value) for item, value in templates)
        if connection.total_changes:
            log_event(connection, name, entity='document_templates')
    return installed
