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
    # Старые регистрации сохраняют подписи до исправления шапки DOCX.
    # Обновляем только заглушки, не затрагивая пользовательские названия.
    column_labels = {}
    if code == 'СП_77_А_16' and any(
            column.get('label') == f'Графа {index}'
            for field in fields if field['key'] == 'rows_0_33'
            for index, column in enumerate(field.get('fields', []), 1)):
        supplied = json.loads((Path(__file__).parents[1] / 'forms' /
                              'СП 77.13330.2016' / f'{code}.fields.json').read_text(encoding='utf-8'))
        column_labels = {column['key']: column['label'] for field in supplied
                         if field['key'] == 'rows_0_33' for column in field['fields']}
    result=[]
    for field in fields:
        if column_labels and field['key'] == 'rows_0_33':
            field = {**field, 'fields': [
                {**column, 'label': column_labels.get(column['key'], column['label'])}
                if column.get('label') == f'Графа {index}' else column
                for index, column in enumerate(field.get('fields', []), 1)]}
        # В прежней поставке год этой формы ошибочно повторял поле месяца.
        # Исправляем только точную старую привязку; ручной год сохраняется.
        if code == 'СП_72_Д' and field['key'] == 't1_r0_c7' and field.get('source') == 'field_values.t1_r0_c5':
            field = {**field, 'source': 'act.date_signed', 'format': 'year_4digits'}
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
