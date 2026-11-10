"""Явные связи полей каталога с текущими карточками. Заполненный ручной текст сохраняется."""
from functools import lru_cache
import json
from pathlib import Path


FIELD_CONTINUATIONS = {
    'СП_77_А_2': {'t3_r0_c0': ['t3_r1_c0'], 't4_r0_c0': ['t4_r1_c0']},
    'СП_77_А_5': {'t6_r1_c0': ['t6_r2_c0']},
    'СП_70_Ф': {'t3_r0_c0': [f't3_r{i}_c0' for i in range(1, 5)]},
    **{f'СП_42_101_2003_{code}': {'t1_r0_c0': ['t1_r1_c0'], 't2_r0_c0': ['t2_r1_c0']}
       for code in ('Р', 'С', 'Т')},
}


@lru_cache(maxsize=1)
def field_bindings():
    return json.loads((Path(__file__).parents[1]/'forms'/'bindings.json').read_text(encoding='utf-8'))


def document_project(project, obj):
    """Город раздела уточняет город объекта; исходные карточки не меняются."""
    return {**project, 'city': project.get('city') or obj.get('city')}


def apply_form_defaults(code, fields):
    bindings=field_bindings().get(code,{})
    result=[]
    for field in fields:
        binding=bindings.get(field['key'])
        if binding and field['kind']=='literal' and field.get('value') in (None,'') and field.get('state') not in ('hidden','not_applicable'):
            field={k:v for k,v in field.items() if k not in ('value','source','role','template','presentation')}
            field={**field,**binding}
        result.append(field)
    for key, continuation in FIELD_CONTINUATIONS.get(code, {}).items():
        first = next((f for f in result if f['key'] == key), None)
        tail = [f for f in result if f['key'] in continuation]
        if first is None:
            continue
        values = [str(f['value']) for f in [first, *tail] if f.get('value') not in (None, '')]
        result = [f for f in result if f['key'] not in continuation]
        if tail and values and first['kind'] == 'literal':
            result[result.index(first)] = {**first, 'value': '\n'.join(values)}
    if code == 'РЕЕСТР_ИТД':
        for i, field in enumerate(result):
            if field['key'] == 'registry' and field['kind'] == 'table':
                columns = field['fields']
                keys = {column['key'] for column in columns}
                extra = [{'key': key, 'kind': 'reference', 'source': 'item.' + key}
                         for key in ('number_date', 'organization', 'pages') if key not in keys]
                result[i] = {**field, 'fields': columns + extra}
    return result


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
