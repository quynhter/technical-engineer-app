"""Содержательная подготовка ИТД. Источник и явные связи важнее догадок.

Факт — отдельный прирост смонтированного количества, не поставка и не итог.
Отчёты не являются нормативной экспертизой и не меняют деловые значения.
"""
import hashlib
import json
import math

from .changes import log_event
from .db import calendar_date, required_text
from .resources import quantity


def payload(data, allowed, required=()):
    if not isinstance(data, dict) or set(data) - set(allowed) or set(required) - set(data):
        raise ValueError('Неверный набор полей JSON: проверьте обязательные и неизвестные поля')
    return dict(data)


def row(c, table, record_id):
    # table задаётся только кодом, не данными JSON.
    if type(record_id) is not int or record_id <= 0:
        raise ValueError('ID должен быть положительным целым числом')
    result = c.execute(f'SELECT * FROM {table} WHERE id=?', (record_id,)).fetchone()
    if result is None:
        raise ValueError(f'{table}: запись {record_id} не найдена')
    return dict(result)


def same_project(c, table, record_id, project_id):
    result = row(c, table, record_id)
    if result['project_id'] != project_id:
        raise ValueError('Связанные записи должны относиться к одному разделу')
    return result


def text_fields(data, fields):
    for key in fields:
        data[key] = required_text(data.get(key), key)


def changed(c, table, record_id, before):
    after = row(c, table, record_id)
    log_event(c, 'workflow-update', entity=table, entity_id=record_id, before=before, after=after)
    return after


def expect(before, expected):
    if not isinstance(expected, dict) or not expected or any(k not in before or before[k] != v for k, v in expected.items()):
        raise ValueError('Ожидаемые значения не заданы или запись уже изменена')


def insert(c, table, data):
    keys = ','.join(data)
    record_id = c.execute(f"INSERT INTO {table} ({keys}) VALUES ({','.join('?' for _ in data)})", tuple(data.values())).lastrowid
    result = row(c, table, record_id)
    log_event(c, 'workflow-add', entity=table, entity_id=record_id, after=result)
    return result


def add_fact(c, project_id, data):
    row(c, 'projects', project_id)
    required = ('resource_id','source_key','location','work_description','source','reported_by','status')
    d = payload(data, (*required,'quantity','unit','start_date','end_date','attachment_id','work_entry_id'), required)
    resource = same_project(c, 'resources', d['resource_id'], project_id)
    if d.get('work_entry_id') is not None:
        work = same_project(c, 'workspace_entries', d['work_entry_id'], project_id)
        if work['kind'] != 'work':
            raise ValueError('Выберите запись о выполненной работе в ОЖР')
    text_fields(d, ('source_key','location','work_description','source','reported_by'))
    if d['status'] not in ('pending','confirmed'):
        raise ValueError('Новый факт должен быть pending или confirmed')
    d['quantity'] = quantity(d.get('quantity'), 'количество факта')
    d['unit'] = required_text(d.get('unit', resource['unit']), 'единица')
    if d['unit'] != resource['unit']:
        raise ValueError('Единица факта должна совпадать с ресурсом; пересчёт не выполняется')
    for key in ('start_date','end_date'):
        d[key] = calendar_date(d.get(key))
    if d['start_date'] and d['end_date'] and d['start_date'] > d['end_date']:
        raise ValueError('Начало работ позже окончания')
    if d.get('attachment_id') is not None:
        row(c, 'attachments', d['attachment_id'])
        if not c.execute('SELECT 1 FROM project_attachments WHERE project_id=? AND attachment_id=?', (project_id,d['attachment_id'])).fetchone():
            raise ValueError('Сначала свяжите источник факта с разделом через file-link')
    d['project_id'] = project_id
    existing = c.execute('SELECT * FROM work_facts WHERE project_id=? AND source_key=?', (project_id,d['source_key'])).fetchone()
    if existing:
        if all(existing[k] == v for k,v in d.items()):
            return {'duplicate':True, **dict(existing)}
        raise ValueError('source_key уже занят отличающимся фактом; не перезаписывайте источник')
    return insert(c, 'work_facts', d)


def add_fact_from_work(c, project_id, data):
    required = ('work_entry_id', 'resource_id', 'source_key', 'status')
    values = payload(data, (*required, 'quantity'), required)
    if type(values['work_entry_id']) is not int or values['work_entry_id'] <= 0:
        raise ValueError('Выберите запись о выполненной работе в ОЖР')
    work = same_project(c, 'workspace_entries', values['work_entry_id'], project_id)
    if work['kind'] != 'work':
        raise ValueError('Выберите запись о выполненной работе в ОЖР')
    return add_fact(c, project_id, dict(values,
        location=work['details'] or 'Не указано',
        work_description=work['title'],
        start_date=work['entry_date'],
        end_date=work['entry_date'],
        source=f"Запись ОЖР № {work['id']}",
        reported_by=work['responsible'] or 'Не указан',
    ))


def set_fact_status(c, fact_id, data, expected):
    if c.execute('SELECT 1 FROM work_materials WHERE fact_id=?',(fact_id,)).fetchone():
        raise ValueError('Факт связан со списанием: измените использованные ресурсы в записи работы')
    before = row(c, 'work_facts', fact_id)
    expect(before, expected)
    d = payload(data, ('status','reason'), ('status',))
    if d['status'] == 'void' and before['status'] != 'void':
        reason = required_text(d.get('reason'), 'причина отзыва')
    elif d['status'] == 'confirmed' and before['status'] == 'pending':
        required_text(d.get('reason'), 'источник подтверждения факта')
        reason = None
    else:
        raise ValueError('Разрешены pending → confirmed и отзыв в void; для исправления создайте новую запись')
    c.execute('UPDATE work_facts SET status=?,void_reason=? WHERE id=?', (d['status'],reason,fact_id))
    if d['status'] == 'confirmed':
        log_event(c, 'fact-confirmation', entity='work_facts', entity_id=fact_id,
                  after={'source':d['reason']})
    return changed(c, 'work_facts', fact_id, before)


def fact_summary(c, project_id):
    row(c, 'projects', project_id)
    result = []
    for r in c.execute('SELECT * FROM resources WHERE project_id=? ORDER BY id', (project_id,)):
        facts = [dict(f) for f in c.execute('SELECT * FROM work_facts WHERE resource_id=? ORDER BY id', (r['id'],))]
        confirmed = [f for f in facts if f['status']=='confirmed']
        complete = bool(confirmed) and all(f['quantity'] is not None and f['unit']==r['unit'] for f in confirmed)
        try:
            total = math.fsum(f['quantity'] for f in confirmed) if complete else None
        except OverflowError as error:
            raise ValueError(f"Сумма фактов ресурса {r['id']} выходит за диапазон чисел") from error
        result.append({'resource_id':r['id'], 'unit':r['unit'], 'qty_fact':r['qty_fact'],
                       'confirmed_total':total, 'confirmed_ids':[f['id'] for f in confirmed],
                       'pending_ids':[f['id'] for f in facts if f['status']=='pending'],
                       'unknown_quantity_ids':[f['id'] for f in confirmed if f['quantity'] is None],
                       'note':'Сумма только внесённых приростов; полнота факта по разделу не подтверждается'})
    return result


def link_facts(c, act_id, fact_ids):
    act = row(c, 'acts', act_id)
    if len(set(fact_ids)) != len(fact_ids):
        raise ValueError('Повтор ID факта')
    for fact_id in fact_ids:
        fact = same_project(c, 'work_facts', fact_id, act['project_id'])
        if fact['status'] != 'confirmed':
            raise ValueError('К акту можно привязать только подтверждённый факт')
        if not c.execute('SELECT 1 FROM act_resources WHERE act_id=? AND resource_id=?', (act_id,fact['resource_id'])).fetchone():
            raise ValueError('Ресурс факта отсутствует в составе акта')
    before = [r[0] for r in c.execute('SELECT fact_id FROM act_facts WHERE act_id=? ORDER BY fact_id', (act_id,))]
    c.execute('DELETE FROM act_facts WHERE act_id=?', (act_id,))
    c.executemany('INSERT INTO act_facts VALUES (?,?)', ((act_id,f) for f in fact_ids))
    log_event(c, 'act-facts', entity='acts', entity_id=act_id, before=before, after=fact_ids)
    return {'act_id':act_id, 'fact_ids':fact_ids}


REQUIREMENT_FIELDS = ('title','work_scope','basis','kind','act_type','attachment_type','act_id','attachment_id','scheme_id','release_id','state','reason')


def validate_requirement(c, project_id, d):
    text_fields(d, ('title','work_scope','basis'))
    kind = d['kind']
    if kind not in ('act','attachment','scheme','xlsx') or d.get('state','required') not in ('required','not_applicable'):
        raise ValueError('Неверный вид или состояние требования')
    if d.get('state') == 'not_applicable':
        d['reason'] = required_text(d.get('reason'), 'основание неприменимости')
    allowed_target = {'act':'act_id','attachment':'attachment_id','scheme':'scheme_id','xlsx':'release_id'}[kind]
    for field in ('act_id','attachment_id','scheme_id','release_id'):
        if d.get(field) is not None and field != allowed_target:
            raise ValueError('Вид требования не соответствует привязке')
    if d.get('act_type') is not None:
        if kind != 'act' or not c.execute('SELECT 1 FROM document_types WHERE code=?', (d['act_type'],)).fetchone():
            raise ValueError('Неверная форма требования')
    if d.get('attachment_type') is not None and (kind!='attachment' or d['attachment_type'] not in ('order','certificate','passport','rd','scheme','other')):
        raise ValueError('Неверный тип приложения')
    target = d.get(allowed_target)
    if target is not None:
        if kind=='attachment':
            item = row(c, 'attachments', target)
            if not c.execute('SELECT 1 FROM project_attachments WHERE project_id=? AND attachment_id=?', (project_id,target)).fetchone():
                raise ValueError('Сначала свяжите приложение с разделом через file-link')
            if d.get('attachment_type') and item['doc_type']!=d['attachment_type']:
                raise ValueError('Тип приложения не соответствует требованию')
        else:
            item = same_project(c, {'act':'acts','scheme':'schemes','xlsx':'releases'}[kind], target, project_id)
            if kind=='act' and d.get('act_type') and item['act_type']!=d['act_type']:
                raise ValueError('Форма акта не соответствует требованию')
            if kind=='xlsx' and item['kind']!='xlsx':
                raise ValueError('Требуется выпуск XLSX')
    return d


def add_requirement(c, project_id, data):
    row(c, 'projects', project_id)
    d = payload(data, REQUIREMENT_FIELDS, ('title','work_scope','basis','kind'))
    validate_requirement(c, project_id, d)
    return insert(c, 'package_requirements', {'project_id':project_id, **d})


def set_requirement(c, requirement_id, data, expected):
    before = row(c, 'package_requirements', requirement_id)
    expect(before, expected)
    d = payload(data, REQUIREMENT_FIELDS)
    if not d:
        raise ValueError('Изменения не заданы')
    normalized = validate_requirement(c, before['project_id'], {**before, **d})
    d = {k:normalized[k] for k in d}
    c.execute('UPDATE package_requirements SET '+','.join(f'{k}=?' for k in d)+' WHERE id=?', (*d.values(), requirement_id))
    return changed(c, 'package_requirements', requirement_id, before)


def matrix(c, project_id):
    row(c, 'projects', project_id)
    result = []
    for r in c.execute('SELECT * FROM package_requirements WHERE project_id=? ORDER BY id', (project_id,)):
        d = dict(r); status = 'missing'; release = None
        if r['state']=='not_applicable':
            status = 'not_applicable'
        elif r['kind']=='act' and r['act_id'] is not None:
            act = row(c,'acts',r['act_id'])
            release = c.execute('SELECT * FROM releases WHERE act_id=? AND selected=1', (act['id'],)).fetchone()
            status = 'inactive' if not act['is_active'] else ('prepared' if release is None else release['mode'])
        elif r['kind']=='attachment' and r['attachment_id'] is not None:
            status = 'file_present'
        elif r['kind']=='scheme' and r['scheme_id'] is not None:
            status = 'registered'
        elif r['kind']=='xlsx' and r['release_id'] is not None:
            release = row(c,'releases',r['release_id'])
            status = release['mode'] if release['selected'] else 'unselected'
        d['availability'] = status
        if release:
            d['release_id'] = release['id']
            delivery = c.execute('SELECT * FROM deliveries WHERE release_id=? ORDER BY id DESC LIMIT 1', (release['id'],)).fetchone()
            d['latest_delivery'] = dict(delivery) if delivery else None
        try:
            validate_requirement(c, project_id, dict(r))
        except ValueError as error:
            d['availability'] = 'binding_mismatch'
            d['binding_error'] = str(error)
        result.append(d)
    return {'project_id':project_id,'requirements':result,'scope':'Только явно согласованный перечень; наличие файла не подтверждает его пригодность', 'configured':bool(result)}


def resource_fingerprint(resource):
    d = {k:resource[k] for k in ('name','type_mark','serial_num','manufacturer','unit')}
    return hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def add_quality_review(c, project_id, data):
    d = payload(data, ('resource_id','attachment_id','status','checked_by','checked_date','source','note'), ('resource_id','attachment_id','status','checked_by','checked_date','source','note'))
    resource = same_project(c,'resources',d['resource_id'],project_id)
    attachment = row(c,'attachments',d['attachment_id'])
    from .archive import is_quality_file
    if not is_quality_file(attachment):
        raise ValueError('Для проверки нужен документ, подтверждающий качество')
    if not c.execute('SELECT 1 FROM resource_attachments WHERE resource_id=? AND attachment_id=?',(resource['id'],attachment['id'])).fetchone():
        raise ValueError('Сначала свяжите документ качества с ресурсом')
    if d['status'] not in ('matches','mismatch','uncertain'):
        raise ValueError('Неверный результат проверки качества')
    text_fields(d, ('checked_by','source','note'))
    d['checked_date'] = calendar_date(d['checked_date'])
    if d['checked_date'] is None:
        raise ValueError('Нужна дата проверки')
    d.update(resource_sha256=resource_fingerprint(resource), attachment_sha256=attachment['sha256'])
    return insert(c,'quality_reviews',d)


def report(c, project_id):
    row(c,'projects',project_id)
    from .inventory import material_issues
    findings = material_issues(c,project_id)
    def issue(code, **details): findings.append({'code':code, **details})
    if c.execute("SELECT 1 FROM sqlite_master WHERE name='act_entry_sources'").fetchone():
        from .manual import source_issues, supply_balance
        for act in c.execute('SELECT id FROM acts WHERE project_id=? AND is_active=1',(project_id,)):
            findings.extend(source_issues(c,act['id']))
            signed=row(c,'acts',act['id'])['date_signed']
            if signed:
                from .participants import participants_context
                pc=participants_context(c,project_id)
                used_orgs={o['id'] for o in pc['organizations'].values()}
                used_orgs.update(s['org_id'] for s in pc['signatories'].values() if s)
                for period in pc['participation_periods']:
                    if period['org_id'] in used_orgs and ((period['active_from'] and signed<period['active_from']) or (period['active_to'] and signed>period['active_to'])):
                        issue('participant_outside_period',act_id=act['id'],org_id=period['org_id'])
        for supply in supply_balance(c,project_id):
            if supply['remaining'] is not None and supply['remaining'] < -1e-9:
                issue('supply_overallocated',supply_id=supply['id'])
    for s in fact_summary(c,project_id):
        rid = s['resource_id']
        if s['pending_ids']: issue('facts_pending',resource_id=rid,fact_ids=s['pending_ids'])
        if s['unknown_quantity_ids']: issue('fact_quantity_unknown',resource_id=rid,fact_ids=s['unknown_quantity_ids'])
        if s['confirmed_total'] is not None and s['qty_fact'] is not None and not math.isclose(s['confirmed_total'],s['qty_fact'],rel_tol=1e-9,abs_tol=1e-9):
            issue('fact_total_differs',**s)
    for fact in c.execute("""SELECT f.*, EXISTS(SELECT 1 FROM work_materials m WHERE m.fact_id=f.id) AS from_work
        FROM work_facts f WHERE f.project_id=? AND f.status!='void' ORDER BY f.id""", (project_id,)):
        # Earlier versions stored the single OJR date as the end of work.
        if fact['end_date'] is None or (fact['start_date'] is None and not fact['from_work']):
            issue('fact_dates_incomplete',fact_id=fact['id'])
        if fact['unit'] != row(c,'resources',fact['resource_id'])['unit']:
            issue('fact_unit_changed',fact_id=fact['id'])
    for r in c.execute('SELECT * FROM resources WHERE project_id=? ORDER BY id',(project_id,)):
        if r['qty_fact'] is None: issue('qty_fact_unknown',resource_id=r['id'])
        elif r['qty_proj'] is not None and r['qty_fact'] > r['qty_proj']: issue('fact_exceeds_project',resource_id=r['id'])
        attachments = c.execute("SELECT a.* FROM resource_attachments ra JOIN attachments a ON a.id=ra.attachment_id WHERE ra.resource_id=? AND (a.doc_type IN ('certificate','passport') OR a.file_kind='quality') ORDER BY a.id",(r['id'],)).fetchall()
        if not attachments: issue('quality_document_missing',resource_id=r['id'])
        for a in attachments:
            review = c.execute('SELECT * FROM quality_reviews WHERE resource_id=? AND attachment_id=? ORDER BY id DESC LIMIT 1',(r['id'],a['id'])).fetchone()
            status = 'unreviewed' if review is None else review['status']
            if review and (review['resource_sha256']!=resource_fingerprint(r) or review['attachment_sha256']!=a['sha256']): status='stale'
            if status!='matches': issue('quality_'+status,resource_id=r['id'],attachment_id=a['id'],review_id=review['id'] if review else None)
    for act in c.execute('SELECT * FROM acts WHERE project_id=? AND is_active=1 ORDER BY id',(project_id,)):
        facts = c.execute('SELECT f.* FROM act_facts af JOIN work_facts f ON f.id=af.fact_id WHERE af.act_id=? ORDER BY f.id',(act['id'],)).fetchall()
        resources = {r[0] for r in c.execute('SELECT resource_id FROM act_resources WHERE act_id=?',(act['id'],))}
        for f in facts:
            if f['status']!='confirmed': issue('act_fact_not_confirmed',act_id=act['id'],fact_id=f['id'])
            if f['resource_id'] not in resources: issue('act_fact_resource_missing',act_id=act['id'],fact_id=f['id'])
            if f['unit']!=row(c,'resources',f['resource_id'])['unit']: issue('fact_unit_changed',fact_id=f['id'])
            if act['date_signed'] and f['end_date'] and act['date_signed'] < f['end_date']: issue('act_signed_before_work_end',act_id=act['id'],fact_id=f['id'])
        missing = sorted(resources-{f['resource_id'] for f in facts if f['status']=='confirmed'})
        if missing: issue('act_facts_missing',act_id=act['id'],resource_ids=missing)
        from .acts import build_context
        try:
            context = build_context(c,act['id'],draft=True)
            if context.get('missing'): issue('act_required_fields_missing',act_id=act['id'],fields=context['missing'])
            selected = c.execute('SELECT r.id,g.context_json FROM releases r JOIN generated_documents g ON g.id=r.generated_id WHERE r.act_id=? AND r.selected=1', (act['id'],)).fetchone()
            if selected and json.loads(selected['context_json']) != context['context']:
                issue('release_context_changed',act_id=act['id'],release_id=selected['id'])
        except ValueError as error:
            issue('act_context_error',act_id=act['id'],message=str(error))
    m = matrix(c,project_id)
    if not m['configured']: issue('requirements_not_configured')
    for req in m['requirements']:
        if req['availability'] in ('missing','inactive','unselected','binding_mismatch'): issue('requirement_'+req['availability'],requirement_id=req['id'])
    pending = [r[0] for r in c.execute("SELECT id FROM specification_pending WHERE project_id=? AND status='pending'",(project_id,))]
    if pending: issue('specification_pending',pending_ids=pending)
    for delivery in c.execute('SELECT * FROM deliveries WHERE project_id=? ORDER BY id',(project_id,)):
        for remark in c.execute("SELECT id FROM delivery_remarks WHERE delivery_id=? AND status='open'",(delivery['id'],)):
            issue('open_remark',delivery_id=delivery['id'],remark_id=remark['id'])
    return {'project_id':project_id,'findings':findings,'matrix':m,'limitations':[
        'Проверяются внесённые данные и явные связи. Отсутствие замечаний не подтверждает полноту или нормативное соответствие.',
        'Сумма фактов охватывает только внесённые приросты. Даты работ в произвольных fields и содержание схем автоматически не распознаются.',
        'Наличие схем и необходимость конкретных документов контролируются по согласованной матрице, без универсального требования схемы к каждому акту.'
    ]}


def release_for_delivery(c, release_id, project_id=None):
    release = row(c,'releases',release_id)
    if project_id is not None and release['project_id']!=project_id:
        raise ValueError('Выпуск относится к другому разделу')
    if release['mode']!='final':
        raise ValueError('Для официальной передачи нужен финальный выпуск')
    # Проверяем реальные байты, не только наличие записи в БД.
    from .releases import actual_path
    path = actual_path(c,release['path'])
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=release['sha256']:
        raise ValueError('Файл выпуска отсутствует или изменён; выполните release-verify')
    return release


def event_data(data):
    text_fields(data,('source','note'))
    data['event_date'] = calendar_date(data.get('event_date'))
    if data['event_date'] is None: raise ValueError('Нужна дата события')


def add_delivery(c,project_id,data):
    d = payload(data,('release_id','recipient','event_date','source','note'),('release_id','recipient','event_date','source','note'))
    release_for_delivery(c,d['release_id'],project_id)
    text_fields(d,('recipient',)); event_data(d)
    result = insert(c,'deliveries',{'project_id':project_id,'release_id':d['release_id'],'recipient':d['recipient'],'status':'sent'})
    insert(c,'delivery_events',{'delivery_id':result['id'],'release_id':d['release_id'],'status':'sent','revision':1, **{k:d[k] for k in ('event_date','source','note')}})
    return result


def set_delivery(c,delivery_id,data,expected):
    before = row(c,'deliveries',delivery_id); expect(before,expected)
    if 'revision' not in expected: raise ValueError('Укажите ожидаемую revision')
    d = payload(data,('status','release_id','event_date','source','note'),('status','event_date','source','note'))
    event_data(d)
    transitions = {'sent':('remarks','accepted'),'remarks':('corrected',),'corrected':('sent',),'accepted':()}
    if d['status'] not in transitions[before['status']]: raise ValueError('Недопустимый переход стадии сдачи')
    last = c.execute('SELECT event_date FROM delivery_events WHERE delivery_id=? ORDER BY revision DESC LIMIT 1',(delivery_id,)).fetchone()
    if d['event_date'] < last[0]: raise ValueError('Дата события раньше предыдущего события')
    if d['status'] in ('corrected','accepted') and c.execute("SELECT 1 FROM delivery_remarks WHERE delivery_id=? AND status='open'",(delivery_id,)).fetchone():
        raise ValueError('Сначала закройте каждое открытое замечание')
    latest_resolution = c.execute('SELECT MAX(resolution_date) FROM delivery_remarks WHERE delivery_id=?', (delivery_id,)).fetchone()[0]
    if d['status'] in ('corrected','accepted') and latest_resolution and d['event_date'] < latest_resolution:
        raise ValueError('Дата события раньше устранения замечаний')
    release_id = d.get('release_id',before['release_id'])
    if release_id!=before['release_id'] and d['status']!='corrected': raise ValueError('Заменить выпуск можно при устранении замечаний')
    release_for_delivery(c,release_id,before['project_id'])
    revision = before['revision']+1
    c.execute('UPDATE deliveries SET status=?,release_id=?,revision=? WHERE id=?',(d['status'],release_id,revision,delivery_id))
    insert(c,'delivery_events',{'delivery_id':delivery_id,'release_id':release_id,'status':d['status'],'revision':revision, **{k:d[k] for k in ('event_date','source','note')}})
    return changed(c,'deliveries',delivery_id,before)


def add_remark(c,delivery_id,data):
    delivery = row(c,'deliveries',delivery_id)
    if delivery['status']!='remarks': raise ValueError('Сначала зарегистрируйте возврат с замечаниями через delivery-set')
    d = payload(data,('description','source'),('description','source')); text_fields(d,('description','source'))
    return insert(c,'delivery_remarks',{'delivery_id':delivery_id,'release_id':delivery['release_id'],**d})


def resolve_remark(c,remark_id,data,expected):
    before = row(c,'delivery_remarks',remark_id); expect(before,expected)
    if before['status']!='open': raise ValueError('Замечание уже закрыто')
    d = payload(data,('resolution','resolution_source','resolution_date','resolution_release_id'),('resolution','resolution_source','resolution_date','resolution_release_id'))
    text_fields(d,('resolution','resolution_source'))
    d['resolution_date'] = calendar_date(d['resolution_date'])
    if not d['resolution_date']: raise ValueError('Нужна дата устранения')
    delivery = row(c,'deliveries',before['delivery_id'])
    release_for_delivery(c,d['resolution_release_id'],delivery['project_id'])
    last_event = c.execute('SELECT MAX(event_date) FROM delivery_events WHERE delivery_id=?',(delivery['id'],)).fetchone()[0]
    if d['resolution_date'] < last_event: raise ValueError('Устранение раньше получения замечаний')
    c.execute("UPDATE delivery_remarks SET status='resolved',"+','.join(f'{k}=?' for k in d)+' WHERE id=?',(*d.values(),remark_id))
    return changed(c,'delivery_remarks',remark_id,before)


def workflow_context(c,project_id):
    return {'facts':fact_summary(c,project_id),'matrix':matrix(c,project_id),
            'fact_records':[dict(r) for r in c.execute('SELECT * FROM work_facts WHERE project_id=? ORDER BY id',(project_id,))],
            'deliveries':[dict(r) for r in c.execute('SELECT * FROM deliveries WHERE project_id=? ORDER BY id',(project_id,))],
            'remarks':[dict(r) for r in c.execute('SELECT r.* FROM delivery_remarks r JOIN deliveries d ON d.id=r.delivery_id WHERE d.project_id=? ORDER BY r.id',(project_id,))]}
