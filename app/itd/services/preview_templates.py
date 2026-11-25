"""Use the template editor with a private copy during proposal validation."""
import json
import shutil
from uuid import uuid4

from .operations import run_web_operation
from ..archive import digest


def assign_codes(rows):
    for row in rows:
        if row['operation'] == 'add':
            row['_new_code'] = 'TPL_' + uuid4().hex


def run(c, ctx, actor, pid, op, data, warnings):
    original = ctx.templates
    directory = original if not getattr(c, 'preview_origin', None) else ctx.database.parent / 'templates'
    template_ctx = ctx.model_copy(update={'templates': directory})
    code = data.get('code') or data.pop('_new_code')
    path = directory / (code + '.docx')
    if path.is_symlink():
        raise ValueError('Недопустимый путь шаблона.')
    if directory != original:
        directory.mkdir(exist_ok=True)
        existing = original / path.name
        if not path.exists() and existing.is_file():
            if existing.is_symlink():
                raise ValueError('Недопустимый путь шаблона.')
            shutil.copyfile(existing, path)

    def form(action, payload):
        return run_web_operation(template_ctx, actor, c, '/api/templates/' + action,
                                 {'project_id': pid, **payload})

    before = digest(path) if path.is_file() else None
    if op == 'remove':
        result = form('delete', data)
    else:
        file = data.pop('file', None)
        custom_fields = data.get('fields')
        if file:
            data.update(original_name=file['name'], content=file['content'])
        if op == 'edit':
            existing = c.execute('''SELECT t.*,d.name,d.fields FROM document_templates t
                JOIN document_types d USING(code) WHERE code=? AND deleted=0''', (code,)).fetchone()
            if existing is None:
                raise ValueError('Шаблон не найден.')
            defaults = {key: existing[key] for key in ('name', 'form_set', 'original_name')}
            data = {**defaults, 'fields': json.loads(existing['fields']), **data}
        if custom_fields is None and (file or data.get('fields') is None):
            data['fields'] = form('inspect', data)['fields']
        c.preview_template_code = code if op == 'add' else None
        try:
            result = form('save', data)
        finally:
            c.preview_template_code = None
    after = digest(path) if path.is_file() else None
    if before or after:
        warnings.append({'message': 'SHA-256 файла шаблона.', 'before': before, 'after': after})
    return result
