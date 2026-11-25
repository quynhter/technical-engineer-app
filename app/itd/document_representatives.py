"""Подписанты, заданные ссылками полей на таблицу представителей."""
import json
import re

from .fields import DB_TOKEN, merge_fields


ROLE_PREFIX = 'representative_'
RECORD_SOURCE = re.compile(r'records\.signatories\.r([0-9]+)\.\w+\Z')


def representatives(fields, available=()):
    identities = set()
    unresolved = False

    def binding(identity):
        nonlocal unresolved
        if identity:
            identities.add(int(identity.removeprefix('r')))
        else:
            unresolved = True

    def visit_value(value):
        if isinstance(value, str):
            for table, identity, _ in DB_TOKEN.findall(value):
                if table == 'signatories':
                    binding(identity)
        elif isinstance(value, dict) and isinstance(value.get('__itd_source'), str):
            match = RECORD_SOURCE.fullmatch(value['__itd_source'])
            if match:
                binding(match[1])

    for field in fields:
        if field.get('state') in ('hidden', 'not_applicable'):
            continue
        if match := RECORD_SOURCE.fullmatch(field.get('source') or ''):
            binding(match[1])
        if field['kind'] == 'literal':
            visit_value(field.get('value'))
        if field['kind'] == 'table':
            columns = [column for column in field['fields']
                       if column.get('state') not in ('hidden', 'not_applicable')]
            if field.get('db_table') == 'signatories' and any(
                    column.get('source', '').startswith('item.') for column in columns):
                identities.update(available)
            for row in field.get('value') or []:
                if not isinstance(row, dict):
                    continue
                for column in columns:
                    source = column.get('source', '')
                    if source.startswith('item.'):
                        visit_value(row.get(source.removeprefix('item.')))
            nested, pending = representatives(columns, available)
            identities.update(nested)
            unresolved |= pending
    return identities, unresolved


def linked_people(c, pid, aid, *, frozen_fields=None):
    a = c.execute('''SELECT a.act_type,a.fields,d.fields AS defaults
                     FROM acts a JOIN document_types d ON d.code=a.act_type WHERE a.id=?''', (aid,)).fetchone()
    if not a['act_type'].startswith('TPL_'):
        return {}, False
    from .ojr import directory
    roster = directory(c, pid)
    organizations = {org['id']: org for org in roster['organizations']}
    fields = merge_fields(json.loads(a['defaults']), json.loads(a['fields'])) if frozen_fields is None else frozen_fields
    from .form_defaults import document_date_field
    signing_date = document_date_field(a['act_type'], fields)
    object_orgs = {row[0] for row in c.execute('''SELECT op.org_id FROM object_participants op
        JOIN projects p ON p.object_id=op.object_id WHERE p.id=?''', (pid,))}
    people = {person['id']: person for person in roster['people'] if person['org_id'] in object_orgs}
    identities, pending = representatives([field for field in fields if field is not signing_date], people)
    result = {}
    for identity in sorted(identities):
        person = people.get(identity)
        if person is None:
            pending = True
            continue
        result[f'{ROLE_PREFIX}{identity}'] = {
            **person, 'organization': organizations[person['org_id']], 'fio_short': person['fio'],
        }
    return result, pending


def validate_linked_signer(c, pid, identity, date):
    from .ojr import roster
    active = c.execute('''SELECT 1 FROM signatories s JOIN object_participants op ON op.org_id=s.org_id
        JOIN projects p ON p.object_id=op.object_id
        WHERE p.id=? AND s.id=? AND s.status='Действует' ''', (pid, identity)).fetchone()
    if not active:
        raise ValueError('Выберите действующего представителя текущего объекта')
    if date and any(p['id'] == identity for p in roster(c, pid)) and not any(
            p['id'] == identity for p in roster(c, pid, date)):
        raise ValueError('Подписант вне периода участия')
