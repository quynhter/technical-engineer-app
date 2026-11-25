"""Translate typed proposals into the same commands used by the РД forms."""
from contextlib import contextmanager
import json
import sqlite3

from .operations import run_web_operation
from ..workflow import row, same_project
from ..workspace import JournalDatesConfirmation

ACTIONS = {
    ('resources', 'add'): 'resource-add',
    ('special-journals', 'save'): 'special-journal-save',
    ('linked-journals', 'add'): 'journal-add',
    ('supplies', 'add'): 'supply-add',
    ('document-works', 'save'): 'act-entries',
    ('document-signatories', 'save'): 'act-signatories',
    ('document-status', 'save'): 'act-status',
    ('package-requirements', 'add'): 'requirement-add',
    ('deliveries', 'add'): 'delivery-add',
    ('object-units', 'add'): 'unit-add',
    ('document-forms', 'add'): 'form-connect',
}

ROUTES = {
    ('source-files', 'add'): ('/api/upload', None),
    ('incoming-control', 'save'): ('/api/incoming-day', 'day'),
    ('installation-facts', 'add'): ('/api/fact', 'fact'),
    ('installation-facts', 'from_work'): ('/api/work-fact', 'fact'),
    ('quality-reviews', 'add'): ('/api/quality', 'review'),
    ('documents', 'add'): ('/api/act', None),
    ('document-versions', 'ensure'): ('/api/versions/ensure', None),
    ('document-versions', 'edit'): ('/api/versions/save', None),
}

PATCH_TABLES = {
    'resources': 'resources', 'schemes': 'schemes', 'source-files': 'attachments',
    'documents': 'acts', 'project-details': 'projects',
}

JOURNALS = {'works': None, 'cable-works': None, 'ojr-personnel': '1', 'ojr-journals': '2',
            'ojr-control': '4', 'ojr-supervision': '6'}

REMOVALS = {
    'resources': 'resources', 'schemes': 'schemes', 'source-files': 'attachments',
    'incoming-control': 'workspace_entries', 'special-journals': 'special_journals',
    'supplies': 'supplies', 'installation-facts': 'work_facts', 'quality-reviews': 'quality_reviews',
    'documents': 'acts', 'package-requirements': 'package_requirements',
    'deliveries': 'deliveries', 'delivery-remarks': 'delivery_remarks',
    'object-units': 'object_units', 'participant-periods': 'participant_periods',
    **{name: 'workspace_entries' for name in JOURNALS},
}


def patch(c, project_id, table, data):
    identity = project_id if table == 'projects' else data['id']
    before = row(c, table, identity)
    changes = data['changes']
    if not changes:
        raise ValueError('Укажите хотя бы одно изменение')
    return {'entity': table, 'id': identity, 'changes': changes,
            'expected': {key: before[key] for key in changes}}


def check_entry(c, pid, data, kind, section=None, *, cable=False):
    if data.get('id'):
        before = same_project(c, 'workspace_entries', data['id'], pid)
        if (before['kind'] != kind or json.loads(before['work_fields']).get('journal_section') != section
                or cable and before['work_type'] != 'cable'):
            raise ValueError('Запись относится к другой таблице')
        data.setdefault('revision', before['revision'])
        return before


def remove(c, pid, name, data, action):
    table = REMOVALS[name]
    if name in JOURNALS or name == 'incoming-control':
        kind = 'work' if name in ('works', 'cable-works') else 'incoming' if name == 'incoming-control' else 'journal'
        check_entry(c, pid, data, kind, JOURNALS.get(name), cable=name == 'cable-works')
    if table in ('resources', 'schemes', 'supplies', 'work_facts', 'acts', 'package_requirements', 'deliveries'):
        same_project(c, table, data['id'], pid)
    if table == 'special_journals':
        journal = row(c, table, data['id'])
        if journal['object_id'] != row(c, 'projects', pid)['object_id']:
            raise ValueError('Журнал относится к другому объекту')
    if table == 'attachments' and not c.execute(
        'SELECT 1 FROM project_attachments WHERE project_id=? AND attachment_id=?', (pid, data['id'])
    ).fetchone():
        raise ValueError('Файл не связан с выбранным разделом')
    if table in ('quality_reviews', 'delivery_remarks'):
        entry = row(c, table, data['id'])
        parent, key = ('resources', 'resource_id') if table == 'quality_reviews' else ('deliveries', 'delivery_id')
        same_project(c, parent, entry[key], pid)
    request = {'entity': table, 'id': data['id']}
    view = action('delete-preview', request)
    return action('delete-apply', {**request, 'token': view['token']})


def run_row(c, ctx, actor, pid, name, data, warnings):
    op = data.pop('operation')

    def request(route, values, wrapper=None):
        def dispatch():
            return run_web_operation(ctx, actor, c, route, {'project_id': pid,
                                     **({wrapper: values} if wrapper else values)})
        if route == '/api/action':
            dated = values['action'] in ('special-journal-save', 'act-status')
            entry = values['data']
        else:
            dated = route in ('/api/entry', '/api/incoming-day')
            entry = values
        if dated:
            with savepoint(c, 'dates') as restore:
                try:
                    return dispatch()
                except JournalDatesConfirmation as error:
                    restore()
                    entry['journal_dates_confirmation'] = error.journal_dates
                    warnings.append({'message': 'Будут изменены даты производства работ.',
                                     'dates': error.journal_dates})
        return dispatch()

    def action(operation, values):
        return request('/api/action', {'action': operation, 'data': values})

    simple = ACTIONS.get((name, op))
    if simple:
        if name == 'special-journals' and data.get('id') and 'revision' not in data:
            data['revision'] = row(c, 'special_journals', data['id'])['revision']
        return action(simple, data)
    route = ROUTES.get((name, op))
    if route:
        if name == 'source-files':
            data.update(data.pop('file'))
        if name == 'incoming-control':
            for item in data['resources']:
                check_entry(c, pid, item, 'incoming')
        return request(route[0], data, route[1])
    if name == 'document-templates':
        from .preview_templates import run
        return run(c, ctx, actor, pid, op, data, warnings)
    if name == 'document-versions':
        from ..document_versions import versions
        existing = versions(c, pid, data['act_id'])
        if op == 'add':
            if not existing:
                existing = request('/api/versions/ensure', data)['versions']
            current = existing[-1]
            return request('/api/versions/create', {
                'act_id': data['act_id'], 'expected': {'id': data.get('id', current['id']),
                                                     'revision': data.get('revision', current['revision'])}})
        return request('/api/versions/delete', {**data, 'expected': [
            {key: row[key] for key in ('id', 'revision')} for row in existing]})
    if op == 'remove':
        return remove(c, pid, name, data, action)
    if name in PATCH_TABLES and op == 'edit' and name != 'schemes':
        return action('update', patch(c, pid, PATCH_TABLES[name], data))
    if name == 'schemes':
        file = data.pop('file', None)
        values = data if op == 'add' else patch(c, pid, 'schemes', data)
        return request('/api/scheme-save', {'action': 'scheme-add' if op == 'add' else 'update',
                                            'data': values, 'file': file})
    if name in JOURNALS:
        section = JOURNALS[name]
        data['kind'] = 'work' if section is None else 'journal'
        before = check_entry(c, pid, data, data['kind'], section, cable=name == 'cable-works')
        if name == 'cable-works':
            data['work_type'] = 'cable'
        if before:
            data = {**before, **data,
                    'work_fields': {**json.loads(before['work_fields']), **(data.get('work_fields') or {})}}
        if section:
            data['work_fields']['journal_section'] = section
        elif data.get('work_fields') is None:
            data.pop('work_fields', None)
        return request('/api/entry', data, 'entry')
    if name in ('supplies', 'installation-facts') and op == 'edit':
        identity = data.pop('resource_id')
        table = 'supplies' if name == 'supplies' else 'work_facts'
        before = same_project(c, table, data['id'], pid)
        expected = before if name == 'installation-facts' else {'revision': data.pop('revision')}
        packet = {**data, 'expected': expected}
        return action('resource-card-save', {'id': identity, 'changes': {}, 'expected': {'id': identity},
                      'supplies': [packet] if name == 'supplies' else [],
                      'facts': [packet] if name == 'installation-facts' else []})
    if name == 'supplies':
        return action('supply-set', {**data, 'expected': {'revision': data.pop('revision')}})
    if name == 'installation-facts':
        identity = data.pop('id')
        before = same_project(c, 'work_facts', identity, pid)
        return action('fact-set', {'id': identity, 'changes': data, 'expected': {'status': before['status']}})
    if name == 'document-composition':
        act = same_project(c, 'acts', data['act_id'], pid)
        expected = {key: [item[0] for item in c.execute(
            f'SELECT {column} FROM {table} WHERE act_id=? ORDER BY ordinal', (act['id'],))]
            for key, column, table in (('resources', 'resource_id', 'act_resources'),
                                       ('schemes', 'scheme_id', 'act_schemes'))}
        return action('act-composition', {**data, 'expected': expected})
    if name == 'document-allocations':
        before = c.execute('SELECT quantity FROM act_materials WHERE act_id=? AND supply_id=?',
                           (data['act_id'], data['supply_id'])).fetchone()
        return action('allocate', {**data, 'expected': {'quantity': before[0] if before else None}})
    if name == 'document-sources':
        expected = [dict(row) for row in c.execute(
            'SELECT * FROM act_entry_sources WHERE act_id=? ORDER BY entry_id', (data['act_id'],))]
        return action('sources-review', {**data, 'expected': expected})
    if name == 'document-reviews':
        warnings.append({'message': 'Сверьте деловые утверждения будущего документа с первоисточниками.'})
        result = request('/api/review', {**data, 'confirmed': True})
        if result['static_claims']:
            warnings.append({'message': 'Утверждения бланка для сверки.', 'claims': result['static_claims']})
        return result
    if name == 'package-requirements':
        identity = data['id']
        before = same_project(c, 'package_requirements', identity, pid)
        changes = data['changes']
        return action('requirement-set', {'id': identity, 'changes': changes,
                                          'expected': {key: before[key] for key in changes}})
    if name == 'deliveries':
        identity = data.pop('id')
        revision = data.pop('revision')
        return action('delivery-set', {'id': identity, 'changes': data, 'expected': {'revision': revision}})
    if name == 'delivery-remarks':
        if op == 'add':
            return action('remark-add', {'delivery_id': data.pop('delivery_id'), 'data': data})
        identity = data.pop('id')
        before = row(c, 'delivery_remarks', identity)
        return action('remark-resolve', {'id': identity, 'changes': data,
                                        'expected': {'status': before['status']}})
    project = row(c, 'projects', pid)
    if name == 'ojr-title':
        expected = [dict(row) for row in c.execute(
            'SELECT * FROM signatory_assignments WHERE object_id=? ORDER BY role_key',
            (project['object_id'],))]
        return request('/api/ojr-title', {**data, 'expected': expected})
    if name == 'participant-assignments':
        table, column = (('organization_assignments', 'org_id') if data['entity'] == 'organization'
                         else ('signatory_assignments', 'signatory_id'))
        scope_id = 'object_id' if data['scope'] == 'object' else 'project_id'
        expected = [row[0] for row in c.execute(
            f'SELECT {column} FROM {table} WHERE {scope_id}=? AND role_key=? ORDER BY id',
            (project['object_id'] if scope_id == 'object_id' else pid, data['role']))]
        return action('assign', {**data, 'expected': {'entity_ids': expected}})
    if name == 'participant-periods':
        before = c.execute('SELECT revision FROM participant_periods WHERE object_id=? AND org_id=?',
                           (project['object_id'], data['org_id'])).fetchone()
        return action('period-set', {**data, 'expected': {'revision': before[0]} if before else {}})
    if name == 'project-designer':
        return action('designer-add', {**data, 'expected_designer_org_id': project['designer_org_id']})
    raise ValueError('Неизвестная операция предпросмотра')


@contextmanager
def savepoint(c, name):
    c.execute('SAVEPOINT ' + name)
    def restore():
        c.execute('ROLLBACK TO ' + name)
    try:
        yield restore
    except Exception:
        restore()
        raise
    finally:
        c.execute('RELEASE ' + name)


@contextmanager
def protect_transaction(c):
    # A reusable domain command must never commit the surrounding batch.
    def authorize(code, arg, *_):
        return (sqlite3.SQLITE_DENY if code in (sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_ATTACH,
                                               sqlite3.SQLITE_DETACH)
                else sqlite3.SQLITE_OK)
    c.set_authorizer(authorize)
    try:
        yield
    finally:
        c.set_authorizer(None)
