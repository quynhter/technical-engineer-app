"""Общий JSON-контракт DOCX: свойства предметных объектов вместо адресов ячеек.

Старые fields остаются форматом хранения карточки. Этот модуль строит их
печатное представление и не читает / не меняет БД самостоятельно.
"""
from copy import deepcopy
from datetime import date
from pathlib import Path
import json
import re

from .fields import MONTHS

CONTRACTS = Path(__file__).parents[1] / 'forms/template_contracts.json'
CONTEXT_KEY = '_template_context'
PATH = re.compile(r'[a-z][a-z_0-9]*(?:\.[a-z][a-z_0-9]*)*\Z')


def template_schema(code=None):
    """Публичный справочник без доступа к деловым данным."""
    from .workspace import OBJECT_FIELDS
    types = {
        'Date': list(date_object(None)),
        'Organisation': list(organisation_object()),
        'Representative': list(representative_object()),
        'Document': ['code', 'number', 'date', 'text'],
        'Object': [*OBJECT_FIELDS, 'id', 'text'],
        'Project': ['id', 'name', 'section_code', 'code', 'city', 'form_set', 'smr_start', 'smr_end',
                    'pnr_start', 'pnr_end', 'unit', 'designer', 'documentation', 'text'],
    }
    result = {'version': 2, 'types': types,
              'roots': {'object': 'Object', 'project': 'Project', 'document': 'Document',
                        'organisations': 'role_key → Organisation', 'representatives': 'role_key → Representative',
                        'recipient': 'Representative', 'consignor': 'Representative',
                        'companies': 'Organisation[]', 'form': 'Индивидуальные сведения формы'}}
    if code:
        if code not in contracts():
            raise ValueError('Форма отсутствует в справочнике шаблонов: ' + code)
        result.update(code=code, fields=contracts()[code])
    return result


def contracts():
    return json.loads(CONTRACTS.read_text(encoding='utf-8')) if CONTRACTS.exists() else {}


def legacy_paths(code):
    result = {}
    spec = field_contract(code)
    for key, binding in spec.items():
        result[binding['path']] = key
        for column, path in binding.get('columns', {}).items():
            result[binding['path'] + '.' + path] = key + '.' + column
        if key == 'pages':
            for attr in ('duplicates', 'volumes_info'):
                result[binding['path'] + '.' + attr] = key + '.' + attr
    def properties(value, prefix=''):
        for key, child in value.items():
            path = prefix + key
            yield path
            if isinstance(child, dict):
                yield from properties(child, path + '.')
    for key, binding in spec.items():
        path = binding['path']
        root = path.rsplit('.', 1)[0]
        if root in ('recipient', 'consignor') or root.startswith('representatives.') and root.count('.') == 1:
            for prop in properties(representative_object()):
                result.setdefault(root + '.' + prop, key)
    return result


def date_object(value):
    result = dict.fromkeys(('iso', 'text', 'day', 'month', 'month_number', 'year'), '')
    if not value:
        return result
    try:
        parsed = date.fromisoformat(str(value))
    except ValueError:
        result['text'] = str(value)
        return result
    return {'iso': parsed.isoformat(), 'text': parsed.strftime('%d.%m.%Y'),
            'day': f'{parsed.day:02}', 'month': MONTHS[parsed.month - 1],
            'month_number': f'{parsed.month:02}', 'year': str(parsed.year)}


def role_label(role):
    from .workspace import DOC_ROLES, ROLES
    return {**ROLES, **DOC_ROLES, 'technical_customer': 'Технический заказчик'}.get(role, role)


def organisation_object(value=None, role=''):
    value = value or {}
    names = ('id full_name short_name inn ogrn address postal_code phone email '
             'sro_info sro_ogrn sro_inn sro_certificate_num sro_certificate_date').split()
    result = {name: value.get(name) if value.get(name) is not None else '' for name in names}
    result['name'] = result['short_name'] or result['full_name']
    result.update(role_key=role, role=role_label(role) if role else '', text=result['name'])
    return result


def representative_object(value=None, role=''):
    value = value or {}
    names = ('id position last_name first_name middle_name fio fio_short nrs_id '
             'order_doc email authority_type authority_num authority_date').split()
    result = {name: value.get(name) if value.get(name) is not None else '' for name in names}
    result['fio'] = result['fio'] or ' '.join(result[k] for k in ('last_name', 'first_name', 'middle_name') if result[k])
    from .participants import short_fio
    result['fio_short'] = short_fio(result)
    result['organisation'] = organisation_object(value.get('organization') or value.get('organisation'), role)
    result['authority'] = {'type': result['authority_type'], 'number': result['authority_num'],
                           'date': date_object(result['authority_date']), 'text': result['order_doc']}
    result.update(role_key=role, role=role_label(role) if role else '', text=result['fio'])
    return result


def set_path(target, path, value):
    if not PATH.fullmatch(path):
        raise ValueError('Недопустимый путь свойства шаблона: ' + path)
    parts = path.split('.')
    for part in parts[:-1]:
        child = target.setdefault(part, {})
        if not isinstance(child, dict):
            raise ValueError('Свойство перекрывает объект шаблона: ' + path)
        target = child
    target[parts[-1]] = value


def field_contract(code, fields=None):
    result = deepcopy(contracts().get(code, {}))
    for field in fields or []:
        if field.get('template_path'):
            binding = result.setdefault(field['key'], {})
            if 'path' not in binding:
                binding['path'] = field['template_path']
            elif binding['path'] != field['template_path']:
                binding.setdefault('aliases', []).append(field['template_path'])
            if field['kind'] == 'table':
                registered = {col['key']: col.get('template_path', col['key']) for col in field['fields']}
                if 'columns' not in binding:
                    binding['columns'] = registered
                else:
                    binding['column_aliases'] = registered
    return result


def build_template_context(code, values, *, roots=None, fields=None):
    """Единая модель для всех форм; значения карточки имеют приоритет над БД."""
    roots = roots or {}
    spec = field_contract(code, fields)
    if not spec and not roots:
        return {}
    from .workspace import DOC_ROLES, ROLES, OBJECT_FIELDS
    organisations = roots.get('organizations', {})
    people = roots.get('signatories', {})
    roles = set(DOC_ROLES) | set(ROLES) | set(organisations) | set(people) | {'technical_customer'}
    roles.update(binding['path'].split('.')[1] for binding in spec.values()
                 if binding['path'].startswith(('representatives.', 'organisations.')))
    obj = deepcopy(roots.get('object', {}))
    project = deepcopy(roots.get('project', {}))
    act = roots.get('act', {})
    result = {
        'object': {**dict.fromkeys([*OBJECT_FIELDS, 'id'], ''), **{k: v if v is not None else '' for k, v in obj.items()}},
        'project': {**dict.fromkeys(('id', 'name', 'code', 'section_code', 'city'), ''),
                    **{k: v if v is not None else '' for k, v in project.items()}},
        'document': {'number': act.get('act_num') or '', 'date': date_object(act.get('date_signed')),
                     'code': code, 'text': act.get('act_num') or ''},
        'organisations': {r: organisation_object(organisations.get(r), r) for r in roles},
        'representatives': {r: representative_object(people.get(r), r) for r in roles},
        'form': {},
    }
    unit = {k: v if v is not None else '' for k, v in roots.get('unit', {}).items()}
    unit.setdefault('name', '')
    unit.setdefault('text', unit['name'])
    result['project']['unit'] = unit
    result['project']['designer'] = organisation_object(roots.get('section_designer'), 'designer')
    documentation = roots.get('project_documentation', {})
    result['project']['documentation'] = {key: documentation.get(key) or '' for key in
        ('code', 'designer_name', 'description', 'section_description', 'object_and_project', 'object_description')}
    for field, binding in spec.items():
        if field not in values:
            continue
        value = deepcopy(values[field])
        if 'columns' in binding:
            rows = []
            for row in value or []:
                converted = deepcopy(row)
                for key, path in binding['columns'].items():
                    if key in row:
                        set_path(converted, path, row[key])
                for key, path in binding.get('column_aliases', {}).items():
                    if key in row:
                        set_path(converted, path, row[key])
                rows.append(converted)
            value = rows
        set_path(result, binding['path'], value)
        for path in binding.get('aliases', []):
            set_path(result, path, value)
        if binding['path'].endswith('.year') and isinstance(value, str) and re.fullmatch(r'\d{2}', value):
            set_path(result, binding['path'], '20' + value)
    for field in fields or []:
        if field.get('kind') == 'signatory':
            role = field['role']
            person = result['representatives'].setdefault(role, representative_object(people.get(role), role))
            # Разные представления одного лица не переписывают его свойства.
            if field['key'] in ('recipient', 'consignor'):
                alias = deepcopy(person)
                alias['text'] = values.get(field['key'], '')
                result[field['key']] = alias
    for alias in ('recipient', 'consignor'):
        person = deepcopy(result['representatives'].get(alias, representative_object(role=alias)))
        person.update(result.get(alias, {}))
        person['text'] = values.get(alias, person['text'])
        result[alias] = person
    for key in ('object', 'project'):
        result[key].setdefault('name', '')
        result[key].setdefault('text', result[key]['name'])
    result['companies'] = [organisation_object(org, role) for role, org in organisations.items()]
    # Вызов рендера с готовым плоским контекстом (без БД) также поддерживается.
    if not organisations and isinstance(values.get('companies'), list):
        result['companies'] = deepcopy(values['companies'])
    for org in result['organisations'].values():
        org['name'] = org.get('short_name') or org.get('full_name') or ''
        org['text'] = org['name']
    for person in [*result['representatives'].values(), result['recipient'], result['consignor']]:
        org = person['organisation']
        org['name'] = org.get('short_name') or org.get('full_name') or ''
        org['text'] = org['name']
    return result


def render_context(code, values):
    result = deepcopy(values)
    model = result.pop(CONTEXT_KEY, None)
    if model is None:
        model = build_template_context(code, result)
    result.update(model)
    return result


def display_object(value):
    """{{ recipient }} — удобное представление, {{ recipient.position }} — свойство."""
    if isinstance(value, dict) and 'text' in value:
        return value['text']
    return value
