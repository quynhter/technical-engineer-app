"""Транзакционная модель локальной формы; используется также через CLI."""
import hashlib
import json

from .changes import log_event, update_record
from .db import DATE_FIELDS, add_object, add_project, calendar_date, required_text
from .participants import add_organization, add_signatory, assign

OBJECT_FIELDS = ('name construction_type city address permit_num permit_date permit_authority '
                 'expertise_num expertise_date expertise_authority work_start work_end gsn_case '
                 'developer_functions control_self control_external author_supervision').split()
OBJECT_FIELDS.append('display_name')
ORG_FIELDS = 'full_name short_name inn ogrn postal_code address phone email sro_info sro_ogrn sro_inn sro_certificate_num sro_certificate_date'.split()
REP_FIELDS = ('fio position last_name first_name middle_name nrs_id email authority_type authority_num '
              'authority_date order_doc status order_attachment_id').split()
ROLES = {'developer': 'Застройщик', 'operator': 'Эксплуатирующая организация / региональный оператор',
         'builder': 'Подрядчик', 'designer': 'Проектировщик', 'subcontractor': 'Субподрядчик',
         'gsn': 'Государственный строительный надзор', 'customer': 'Технический заказчик',
         'customer_control': 'Независимый строительный контроль', 'author_supervision': 'Авторский надзор'}
DOC_ROLES = {'customer': 'Заказчик', 'builder': 'Подрядчик', 'designer': 'Проектировщик',
             'customer_control': 'Строительный контроль заказчика',
             'builder_control': 'Строительный контроль подрядчика',
             'author_supervision': 'Авторский надзор', 'developer': 'Застройщик'}
DOC_ROLES.update(installer='Монтажная организация',recipient='Получатель',consignor='Отправитель',
                 work_performer='Исполнитель работ',foreman='Производитель работ',general_contractor='Генподрядчик',
                 commissioner='Пусконаладочная организация',inspector='Инспектор',worker='Исполнитель',
                 network_operator='Эксплуатирующая организация')

DOC_ROLES.update(subcontractor='Субподрядчик',site_manager='Начальник участка',
                 welding_supervisor='Руководитель сварочных работ',laboratory_head='Начальник лаборатории',
                 flaw_detector='Дефектоскопист',chief_engineer='Главный инженер монтажной организации',
                 commission_chair='Председатель комиссии от заказчика',gsn='Государственный строительный надзор',
                 supervisory='Представитель надзорной организации',material_custodian='Материально ответственное лицо',
                 crossing_owner='Представитель владельца пересекаемого объекта',ppr_designer='Разработчик ППР')


OTHER_SIGNER_ROLES = {f'other_{i}': f'Иное лицо {i}' for i in range(1, 4)}
DOC_ROLES.update(OTHER_SIGNER_ROLES)


def rows(c, query, args=()):
    return [dict(r) for r in c.execute(query, args)]


def snapshot(c, object_id=None):
    if object_id is None:
        return {'object': {}, 'participants': [], 'projects': [], 'token': None}
    obj = c.execute('SELECT * FROM objects WHERE id=?', (object_id,)).fetchone()
    if obj is None:
        raise ValueError('Объект не найден')
    people = rows(c, 'SELECT DISTINCT o.* FROM organizations o WHERE o.id IN '
                 '(SELECT org_id FROM object_participants WHERE object_id=? UNION '
                 'SELECT org_id FROM organization_assignments WHERE object_id=?) ORDER BY o.id', (object_id, object_id))
    for org in people:
        org['roles'] = [r[0] for r in c.execute(
            'SELECT role_key FROM object_participants WHERE object_id=? AND org_id=? ORDER BY role_key',
            (object_id, org['id']))]
        if not org['roles']:
            org['roles'] = [r[0] for r in c.execute(
                'SELECT role_key FROM organization_assignments WHERE object_id=? AND org_id=? ORDER BY role_key',
                (object_id, org['id']))]
        org['document_roles'] = [r[0] for r in c.execute(
            'SELECT role_key FROM organization_assignments WHERE object_id=? AND org_id=? ORDER BY role_key', (object_id, org['id']))]
        org['representatives'] = rows(c, 'SELECT * FROM signatories WHERE org_id=? ORDER BY id', (org['id'],))
        for rep in org['representatives']:
            rep['document_roles'] = [r[0] for r in c.execute(
                'SELECT role_key FROM signatory_assignments WHERE object_id=? AND signatory_id=? ORDER BY role_key', (object_id, rep['id']))]
    result = {'object': dict(obj), 'participants': people,
              'projects': rows(c, 'SELECT * FROM projects WHERE object_id=? ORDER BY id', (object_id,))}
    result['token'] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return result


def clean(data, fields):
    result = {k: data[k] for k in fields if k in data}
    for key, value in result.items():
        if key in ('unit_id','designer_org_id','order_attachment_id'):
            if value is not None and (type(value) is not int or value<=0): raise ValueError('Нужен положительный ID или null')
        elif key in ('control_self', 'control_external', 'author_supervision'):
            if type(value) not in (bool, int) or value not in (0, 1):
                raise ValueError('Флажок должен иметь значение 0 или 1')
            result[key] = int(value)
        else:
            if value is not None and not isinstance(value, str):
                raise ValueError(f'{key}: требуется текст')
            result[key] = value.strip() or None if isinstance(value, str) else value
            if key.endswith('_date') or key in ('work_start', 'work_end', *DATE_FIELDS):
                result[key] = calendar_date(result[key])
    return result


def patch(c, table, record_id, values):
    before = dict(c.execute(f'SELECT * FROM {table} WHERE id=?', (record_id,)).fetchone())
    changes = {k: v for k, v in values.items() if before[k] != v}
    if changes:
        update_record(c, entity=table, record_id=record_id, changes=changes,
                      expected={k: before[k] for k in changes})


class WorkspaceValidationError(ValueError):
    def __init__(self, fields):
        self.fields=fields
        labels=list(dict.fromkeys(f['label'] for f in fields))
        message=('Пожалуйста, заполните поле «'+labels[0]+'».' if len(labels)==1 else
                 'Пожалуйста, заполните поля:\n'+'\n'.join('• «'+label+'»' for label in labels))
        super().__init__(message)


def validate_workspace_required(data):
    """Список пропусков до записи, в том числе на других страницах карточки."""
    missing=[]
    def need(value,path,label):
        if value is None or isinstance(value,str) and not value.strip():missing.append({'path':path,'label':label})
    need(data.get('object',{}).get('name'),'object.name','Полное наименование объекта')
    for i,org in enumerate(data.get('participants',[])):
        need(org.get('full_name'),f'participants.{i}.full_name',f'Полное наименование организации {i+1}')
        for j,rep in enumerate(org.get('representatives',[])):
            fio=rep.get('fio') or ' '.join(rep.get(k) or '' for k in ('last_name','first_name','middle_name'))
            need(fio,f'participants.{i}.representatives.{j}.fio',f'ФИО представителя {j+1} организации {i+1}')
            need(rep.get('position'),f'participants.{i}.representatives.{j}.position',f'Должность представителя {j+1} организации {i+1}')
    for i,project in enumerate(data.get('projects',[])):
        for key,label in [('section_code','Обозначение раздела'),('code','Шифр РД'),('name','Полное название раздела')]:
            need(project.get(key),f'projects.{i}.{key}',f'{label} {i+1}')
    if missing:raise WorkspaceValidationError(missing)


def save_workspace(c, data):
    """Все поля мастера сохраняются атомарно; удаление по отсутствию не выполняется."""
    if not isinstance(data, dict):
        raise ValueError('Ожидается объект JSON')
    validate_workspace_required(data)
    obj = data.get('object', {})
    object_id = obj.get('id')
    before = snapshot(c, object_id)
    if object_id and data.get('token') != before['token']:
        raise ValueError('Данные уже изменены. Обновите страницу и повторите правку.')
    values = clean(obj, OBJECT_FIELDS)
    required_text(values.get('name'), 'полное название объекта')
    if values.get('construction_type') not in (None, 'Строительство', 'Реконструкция', 'Капитальный ремонт', 'Прочее'):
        raise ValueError('Неизвестный тип строительства')
    if values.get('developer_functions') not in (None, 'self', 'technical_customer'):
        raise ValueError('Неизвестная схема функций застройщика')
    if values.get('work_start') and values.get('work_end') and values['work_start'] > values['work_end']:
        raise ValueError('Дата начала работ позже даты окончания')
    if object_id is None:
        object_id = add_object(c, values['name'])
    patch(c, 'objects', object_id, values)
    known = {p['id']: p for p in before['participants']}
    participants = data.get('participants', [])
    assigned_orgs = set()
    for org in participants:
        org_id = org.get('id')
        if org_id is not None and org_id not in known:
            raise ValueError('Организация не принадлежит выбранному объекту')
        values = clean(org, ORG_FIELDS)
        required_text(values.get('full_name'), 'наименование организации')
        roles = org.get('roles', [])
        if not roles or any(r not in ROLES and r not in (known.get(org_id, {}).get('roles', [])) for r in roles):
            raise ValueError('Выберите тип организации')
        if org_id is None:
            org_id = add_organization(c, full_name=values['full_name'])
        patch(c, 'organizations', org_id, values)
        # Изменение списка типов — явная часть сохраняемой формы; прежние назначения документов отдельны.
        c.execute('DELETE FROM object_participants WHERE object_id=? AND org_id=?', (object_id, org_id))
        for role in roles:
            c.execute('INSERT INTO object_participants(object_id,org_id,role_key) VALUES(?,?,?)', (object_id, org_id, role))
        for role in org.get('document_roles', []):
            if role in assigned_orgs:
                raise ValueError('На одну роль документа выбраны две организации')
            assigned_orgs.add(role)
        old_org_roles = known.get(org.get('id'), {}).get('document_roles', [])
        _assign_roles(c, 'organization', org_id, object_id, org.get('document_roles', []), old_org_roles)
        rep_ids = {r['id'] for r in known.get(org.get('id'), {}).get('representatives', [])}
        for rep in org.get('representatives', []):
            rep_id = rep.get('id')
            if rep_id is not None and rep_id not in rep_ids:
                raise ValueError('Представитель не принадлежит организации')
            previous = next((r for r in known.get(org.get('id'), {}).get('representatives', []) if r['id'] == rep_id), {})
            values = clean(rep, REP_FIELDS)
            names_changed = any(k in values and values[k] != previous.get(k) for k in ('last_name', 'first_name', 'middle_name'))
            if not values.get('fio') or (names_changed and values.get('fio') == previous.get('fio')):
                values['fio'] = ' '.join(values.get(k) or '' for k in ('last_name', 'first_name', 'middle_name')).strip()
            required_text(values.get('fio'), 'ФИО представителя')
            required_text(values.get('position'), 'должность представителя')
            if values.get('authority_type') not in (None, 'Приказ', 'Распоряжение', 'Доверенность', 'Указания', 'Постановления и решения'):
                raise ValueError('Неизвестный распорядительный документ')
            authority_fields = ('authority_type', 'authority_num', 'authority_date')
            if any(values.get(k) for k in authority_fields) or any(
                k in values and previous.get(k) != values[k] for k in authority_fields
            ):
                values['order_doc'] = ' '.join(x for x in (values.get('authority_type'),
                    ('№ ' + values['authority_num']) if values.get('authority_num') else None,
                    ('от ' + values['authority_date']) if values.get('authority_date') else None) if x) or None
            if rep_id is None:
                rep_id = add_signatory(c, org_id=org_id, fio=values['fio'], position=values['position'])
            patch(c, 'signatories', rep_id, values)
            old = next((r['document_roles'] for r in known.get(org.get('id'), {}).get('representatives', []) if r['id'] == rep_id), [])
            _assign_roles(c, 'signatory', rep_id, object_id, rep.get('document_roles', []), old)
    known_projects = {p['id']: p for p in before['projects']}
    for project in data.get('projects', []):
        pid = project.get('id')
        fields = clean(project, ('section_code', 'code', 'name', 'city', 'gip', 'inv_num', 'form_set', 'unit_id', 'designer_org_id', *DATE_FIELDS))
        if pid is None:
            pid = add_project(c, object_id=object_id, **{k: fields.get(k) for k in ('section_code', 'code', 'name', 'city')})
        elif pid not in known_projects:
            raise ValueError('Раздел не принадлежит объекту')
        elif fields.get('section_code') != known_projects[pid]['section_code']:
            raise ValueError('Изменение обозначения существующего раздела выполняется отдельно')
        patch(c, 'projects', pid, {k: v for k, v in fields.items() if k != 'section_code'})
    log_event(c, 'workspace-save', entity='objects', entity_id=object_id,
              before={'token': before['token']}, after={'source': 'Локальная форма пользователя'})
    return snapshot(c, object_id)


def _assign_roles(c, entity, entity_id, object_id, roles, old):
    if any(role not in DOC_ROLES and role not in old for role in roles):
        raise ValueError('Неизвестная роль в документах')
    table, col = ('organization_assignments', 'org_id') if entity == 'organization' else ('signatory_assignments', 'signatory_id')
    for role in set(old) - set(roles):
        c.execute(f'DELETE FROM {table} WHERE object_id=? AND {col}=? AND role_key=?', (object_id, entity_id, role))
    for role in roles:
        if entity == 'signatory':
            assign(c, entity=entity, entity_id=entity_id, role_key=role, object_id=object_id, multiple=True)
            continue
        existing = c.execute(f'SELECT {col} FROM {table} WHERE object_id=? AND role_key=?', (object_id, role)).fetchone()
        if existing and existing[0] != entity_id:
            raise ValueError(f'Роль {role} уже назначена. Сначала снимите прежнее назначение и сохраните.')
        assign(c, entity=entity, entity_id=entity_id, role_key=role, object_id=object_id)


class JournalDatesConfirmation(ValueError):
    def __init__(self, changes):
        super().__init__('Дата записи раньше начала работ. Подтвердите перенос начала.')
        self.journal_dates = changes


def extend_journal_dates(c, project_id, dates, confirmation=None):
    dates = [value for value in dates if value]
    if not dates:
        return
    first, last = min(dates), max(dates)
    project = c.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
    obj = c.execute('SELECT * FROM objects WHERE id=?', (project['object_id'],)).fetchone()
    scopes = (
        ('objects', obj, 'work_start', 'work_end', 'Объект'),
        ('projects', project, 'smr_start', 'smr_end', 'Раздел · СМР'),
    )
    changes = []
    for _, row, start, _, label in scopes:
        if row[start] and first < row[start]:
            changes.append({'scope': label, 'id': row['id'], 'before': row[start], 'after': first})
    if changes and changes != confirmation:
        raise JournalDatesConfirmation(changes)
    for table, row, start, end, _ in scopes:
        values = {start: min(row[start] or first, first), end: max(row[end] or last, last)}
        patch(c, table, row['id'], values)


def _save_entry(c, project_id, data, *, sync_dates):
    if not c.execute('SELECT 1 FROM projects WHERE id=?', (project_id,)).fetchone():
        raise ValueError('Выберите раздел')
    fields = clean(data, ('kind', 'entry_date', 'title', 'details', 'conditions', 'responsible', 'unit','work_type'))
    work_fields=data.get('work_fields',{})
    if isinstance(work_fields,str):
        work_fields=json.loads(work_fields)
    if not isinstance(work_fields,dict) or any(not isinstance(k,str) or (v is not None and not isinstance(v,(str,int,float))) or isinstance(v,bool) for k,v in work_fields.items()):
        raise ValueError('Индивидуальные поля работ должны содержать текст или числа')
    fields['work_fields']=json.dumps(work_fields,ensure_ascii=False,allow_nan=False)
    if fields.get('kind') not in ('work', 'incoming', 'journal'):
        raise ValueError('Неизвестный журнал')
    required_text(fields.get('title'), 'описание записи')
    from .resources import quantity
    fields['quantity'] = quantity(data.get('quantity'), 'quantity')
    for key, table in (('resource_id', 'resources'), ('act_id', 'acts')):
        fields[key] = data.get(key) or None
        if fields[key] and not c.execute(f'SELECT 1 FROM {table} WHERE id=? AND project_id=?', (fields[key], project_id)).fetchone():
            raise ValueError('Связанная запись относится к другому разделу')
    fields['attachment_id'] = data.get('attachment_id') or None
    if fields['attachment_id'] and not c.execute('SELECT 1 FROM project_attachments WHERE project_id=? AND attachment_id=?', (project_id, fields['attachment_id'])).fetchone():
        raise ValueError('Файл не связан с выбранным разделом')
    person_id=data.get('responsible_id') or None
    fields['responsible_id']=person_id
    if fields['kind']=='work' and person_id:
        from .ojr import validate_executor
        person=validate_executor(c,project_id,person_id,fields.get('entry_date'))
        fields['responsible']=person['fio']
    if fields['kind']=='work' and fields.get('responsible') and not person_id:
        old_person=c.execute('SELECT responsible,responsible_id FROM workspace_entries WHERE id=? AND project_id=?',(data.get('id'),project_id)).fetchone()
        if not old_person or old_person['responsible']!=fields['responsible']:
            raise ValueError('Выберите ответственного исполнителя из раздела 1 ОЖР')
    entry_id = data.get('id')
    from .journals import validate_entry
    validate_entry(c, project_id, fields['kind'], work_fields, fields['resource_id'])
    fields['work_fields'] = json.dumps(work_fields, ensure_ascii=False, allow_nan=False)
    if entry_id:
        old = c.execute('SELECT * FROM workspace_entries WHERE id=? AND project_id=?', (entry_id, project_id)).fetchone()
        if old is None or old['revision'] != data.get('revision'):
            raise ValueError('Запись журнала уже изменена или не найдена')
        if fields['kind'] != old['kind']:
            raise ValueError('Нельзя менять вид существующей записи')
        if old['act_id']:
            if c.execute("SELECT 1 FROM act_execution_status WHERE act_id=? AND state='signed'",(old['act_id'],)).fetchone():
                raise ValueError('Верните подписанный акт в подготовку перед изменением связанной работы')
            if fields['act_id']!=old['act_id']: raise ValueError('Нельзя снять связь работы с актом обычной правкой записи')
            required_text(data.get('change_reason'),'основание изменения работы, включённой в акт')
        fields['revision'] = old['revision'] + 1
        c.execute('UPDATE workspace_entries SET ' + ','.join(k+'=?' for k in fields) + ' WHERE id=?', (*fields.values(), entry_id))
    else:
        old = None
        fields['project_id'] = project_id
        entry_id = c.execute('INSERT INTO workspace_entries (' + ','.join(fields) + ') VALUES (' + ','.join('?' for _ in fields) + ')', tuple(fields.values())).lastrowid
    result = dict(c.execute('SELECT * FROM workspace_entries WHERE id=?', (entry_id,)).fetchone())
    if result['kind']=='work':
        from .inventory import save_materials
        materials=data.get('materials')
        if materials is None:
            materials=[dict(r) for r in c.execute('SELECT resource_id,quantity FROM work_materials WHERE entry_id=?',(entry_id,))]
        save_materials(c,result,materials,previous_entry=dict(old) if old else None)
    log_event(c, 'workspace-entry', entity='workspace_entries', entity_id=entry_id, before=dict(old) if old else None, after=result)
    if old and old['act_id']:
        log_event(c,'entry-change-reason',entity='workspace_entries',entity_id=entry_id,after={'reason':data['change_reason']})
    if sync_dates:
        actual_dates = ('issued_date', 'transfer_date', 'resolved_date')
        if work_fields.get('journal_section') != '1':
            actual_dates += ('start_date', 'end_date')
        extend_journal_dates(c, project_id,
            [result['entry_date'], *(work_fields.get(key) for key in actual_dates)],
            data.get('journal_dates_confirmation'))
    return result


def save_entry(c, project_id, data, *, sync_dates=True):
    c.execute('SAVEPOINT workspace_entry_save')
    try:
        result=_save_entry(c,project_id,data,sync_dates=sync_dates)
        c.execute('RELEASE workspace_entry_save')
        return result
    except Exception:
        c.execute('ROLLBACK TO workspace_entry_save')
        c.execute('RELEASE workspace_entry_save')
        raise
