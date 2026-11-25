"""Явные связи полей каталога с текущими карточками. Заполненный ручной текст сохраняется."""
from functools import lru_cache
import json
from pathlib import Path
import re

from .db import calendar_date


def document_date_field(code, fields):
    if code.startswith('TPL_'):
        return next((field for field in fields if field['key'] == 'date' and
                     not field.get('marker_path') and field['kind'] != 'table'), None)
    return None


def legacy_document_date(field):
    if field and field['kind'] == 'literal':
        value = field.get('value')
        if isinstance(value, str) and re.fullmatch(r'\d{2}\.\d{2}\.\d{4}', value):
            value = '-'.join(reversed(value.split('.')))
        try:
            return calendar_date(value)
        except ValueError:
            pass
    return None


@lru_cache(maxsize=1)
def field_bindings():
    return json.loads((Path(__file__).parents[1]/'forms'/'bindings.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def date_groups():
    return json.loads((Path(__file__).parents[1]/'forms'/'date_groups.json').read_text(encoding='utf-8'))


def apply_date_fields(code, fields):
    """Одна календарная дата вместо трёх строк; старый ручной текст сохраняется."""
    groups = date_groups().get(code, [])
    definitions = {f['key']: f for f in fields}
    updates = {}
    formats = {'day': 'day_2digits', 'month': 'month_genitive_ru', 'year': 'year_4digits'}
    for group in groups:
        parts = group['parts']
        first = definitions.get(parts['day'])
        if not first:
            continue
        legacy = any(f.get('kind') == 'literal' and f.get('value') not in (None, '')
                     and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(f['value']))
                     for key in parts.values() if (f := definitions.get(key)))
        for part, key in parts.items():
            if key not in definitions:
                continue
            field = definitions[key]
            label = group['label'] + (' — ' + {'day': 'день', 'month': 'месяц', 'year': 'год'}[part] if legacy else '')
            if legacy:
                if field['kind'] == 'literal' and field.get('value') not in (None, ''):
                    field = {k: v for k, v in field.items() if k not in ('format', 'value_type', 'input_type', 'date_group')}
                updates[key] = {**field, 'label': label}
                continue
            # Ручная календарная дата выше автоматической связи раздела.
            source = (None if first['kind'] == 'literal' and first.get('value') else group.get('source'))
            if first.get('binding_explicit'):
                source = first.get('source') if first['kind'] == 'reference' else None
            if not source and first['kind'] == 'reference' and not first.get('date_group'):
                source = first.get('source')
            field = {k: v for k, v in field.items() if k not in ('source', 'value', 'input_type')}
            if source:
                field.update(kind='reference', source=source)
            elif part == 'day':
                field.update(kind='literal', value=first.get('value'))
            else:
                field.update(kind='reference', source='date_inputs.' + parts['day'])
            updates[key] = {**field, 'label': label, 'value_type': 'date', 'format': formats[part],
                            'date_group': parts['day']}
    return [updates.get(f['key'], f) for f in fields]


def document_project(project, obj):
    """Город раздела уточняет город объекта; исходные карточки не меняются."""
    return {**project, 'city': project.get('city') or obj.get('city')}


def apply_form_defaults(code, fields):
    bindings=field_bindings().get(code,{})
    result=[]
    for field in fields:
        binding=bindings.get(field['key'])
        if binding and field['kind']=='literal' and field.get('value') in (None,'') and not field.get('binding_explicit') and field.get('state') not in ('hidden','not_applicable'):
            field={k:v for k,v in field.items() if k not in ('value','source','role','template','presentation')}
            field={**field,**binding}
        result.append(field)
    if code == 'РЕЕСТР_ИТД':
        for i, field in enumerate(result):
            if field['key'] == 'registry' and field['kind'] == 'table':
                columns = field['fields']
                keys = {column['key'] for column in columns}
                extra = [{'key': key, 'kind': 'reference', 'source': 'item.' + key}
                         for key in ('number_date', 'organization', 'pages') if key not in keys]
                result[i] = {**field, 'fields': columns + extra}
    return apply_date_fields(code, result)


def documentation_context(connection, project, organizations):
    if project.get('designer_org_id'):
        row=connection.execute('SELECT full_name FROM organizations WHERE id=?',(project['designer_org_id'],)).fetchone()
        designer=row['full_name'] if row else None
    else:
        designer=organizations.get('designer',{}).get('full_name')
    obj=connection.execute('SELECT name,address FROM objects WHERE id=?',(project['object_id'],)).fetchone()
    code=project.get('code');name=project.get('name');object_name=obj['name'] if obj else None;address=obj['address'] if obj else None
    return {'code':code,'designer_name':designer,
            'description':f'{code}, {designer}' if code and designer else None,
            'section_description':f'{name}, {code}' if name and code else None,
            'object_and_project':f'{object_name}, {code}' if object_name and code else None,
            'object_description':f'{object_name}, {address}' if object_name and address and address not in object_name else object_name}
