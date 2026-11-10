"""Живые представления журналов. Данные источников не копируются в новые записи."""
import json

from .db import calendar_date

SECTIONS = {
    '1': 'Инженерно-технический персонал',
    '2': 'Специальные журналы и авторский надзор',
    '3': 'Выполнение работ',
    '4': 'Строительный контроль',
    '5': 'Исполнительная документация',
    '6': 'Государственный строительный надзор',
}
DATE_KEYS = ('start_date', 'end_date', 'issued_date', 'transfer_date', 'deadline', 'resolved_date')
SECTION_FIELDS = {
    '1': {'organization', 'person', 'org_id', 'person_id', 'start_date', 'end_date', 'scope', 'authority'},
    '2': {'issued_date', 'keeper', 'transfer_date', 'recipient'},
    '4': {'defects', 'deadline', 'resolved_date', 'resolved_by'},
    '6': {'defects', 'deadline', 'resolved_date', 'resolved_by'},
}
SECTION_ONLY_FIELDS = set().union(*SECTION_FIELDS.values())


def validate_entry(c, project_id, kind, fields, resource_id):
    section = fields.get('journal_section')
    if section and (kind != 'journal' or section not in ('1', '2', '4', '6')):
        raise ValueError('Для разделов 3 и 5 используются работы и документы из БД')
    if kind == 'journal':
        for key in SECTION_ONLY_FIELDS - SECTION_FIELDS.get(section, set()):
            fields.pop(key, None)
    for key in DATE_KEYS:
        if key in fields:
            fields[key] = calendar_date(fields[key])
    if fields.get('start_date') and fields.get('end_date') and fields['start_date'] > fields['end_date']:
        raise ValueError('Начало участия позже окончания')
    if section=='1' and not fields.get('person_id'):
        raise ValueError('Выберите работника из единого справочника для раздела 1 ОЖР')
    if section=='1' and fields.get('person_id') and not fields.get('org_id'):
        person=c.execute('SELECT org_id FROM signatories WHERE id=?',(fields['person_id'],)).fetchone()
        if person: fields['org_id']=person['org_id']
    for key in ('org_id', 'person_id'):
        value = fields.get(key)
        if value in (None, ''):
            continue
        if kind != 'journal' or section != '1' or type(value) is not int or value <= 0:
            raise ValueError('Участник персонала должен содержать положительный ID')
        from .ojr import directory
        participants=directory(c,project_id)
        allowed=[r['id'] for r in participants['organizations' if key=='org_id' else 'people']]
        if value not in allowed:
            raise ValueError('Участник не относится к объекту')
    if fields.get('org_id') and fields.get('person_id'):
        if c.execute('SELECT org_id FROM signatories WHERE id=?', (fields['person_id'],)).fetchone()[0] != fields['org_id']:
            raise ValueError('Работник не относится к выбранной организации')
    if 'incoming_result' in fields and (kind != 'incoming' or fields['incoming_result'] not in ('pending','accepted','rejected')):
        raise ValueError('Выберите итог входного контроля: pending, accepted или rejected')
    work_id = fields.get('entry_id')
    if work_id is not None:
        if kind != 'incoming' or type(work_id) is not int or not c.execute(
            "SELECT 1 FROM workspace_entries WHERE id=? AND project_id=? AND kind='work'", (work_id, project_id)
        ).fetchone():
            raise ValueError('Выберите запись о выполненной работе этого раздела')
    supply = fields.get('supply_id')
    review = fields.get('quality_review_id')
    for key, value in (('supply_id', supply), ('quality_review_id', review)):
        if value in (None, ''):
            if key in fields:
                fields[key] = None
            continue
        if kind != 'incoming' or type(value) is not int or value <= 0:
            raise ValueError('Связь входного контроля должна содержать положительный ID')
        if key == 'supply_id':
            record = c.execute('SELECT resource_id FROM supplies WHERE id=? AND project_id=?', (value, project_id)).fetchone()
        else:
            record = c.execute('SELECT q.resource_id FROM quality_reviews q JOIN resources r ON r.id=q.resource_id WHERE q.id=? AND r.project_id=?', (value, project_id)).fetchone()
        if not record or record['resource_id'] != resource_id:
            raise ValueError('Поставка или проверка качества должна относиться к выбранному ресурсу раздела')


def journal_data(c, project_id):
    project = c.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
    if project is None:
        raise ValueError('Раздел не найден')
    entries = []
    for row in c.execute('''SELECT e.*,p.section_code,p.code AS project_code FROM workspace_entries e
            JOIN projects p ON p.id=e.project_id WHERE p.object_id=?
            ORDER BY e.entry_date IS NULL,e.entry_date,e.id''', (project['object_id'],)):
        entry = {**dict(row), 'work_fields': json.loads(row['work_fields'])}
        fields = dict(entry['work_fields'])
        entry['resolved_fields'] = fields
        if entry['kind'] == 'journal' and fields.get('journal_section') == '1':
            for key, query, target in (
                ('org_id', 'SELECT full_name FROM organizations WHERE id=?', 'organization'),
                ('person_id', "SELECT fio || ' · ' || position FROM signatories WHERE id=?", 'person')):
                linked = c.execute(query, (fields.get(key),)).fetchone()
                if linked:
                    fields[target] = linked[0]
            signer=c.execute('SELECT position,order_doc FROM signatories WHERE id=?',(fields.get('person_id'),)).fetchone()
            if signer:
                fields['position']=signer['position'];fields['authority']=signer['order_doc']
        if entry['kind']=='work':
            person=c.execute('SELECT fio,position,order_doc FROM signatories WHERE id=?',(entry.get('responsible_id'),)).fetchone()
            entry['responsible_person']=dict(person) if person else None
            entry['materials']=[dict(m) for m in c.execute('SELECT m.*,r.name FROM work_materials m JOIN resources r ON r.id=m.resource_id WHERE m.entry_id=?',(entry['id'],))]
        entries.append(entry)
    sections = {key: [] for key in SECTIONS}
    legacy = []
    for entry in entries:
        if entry['kind'] == 'work':
            sections['3'].append(entry)
        elif entry['kind'] == 'journal':
            section = entry['work_fields'].get('journal_section')
            (sections[section] if section in ('1', '2', '4', '6') else legacy).append(entry)
    # Это текущий список документов, а не утверждение о подписании/приёмке.
    documents = [dict(r) for r in c.execute('''SELECT a.*,d.name AS form_name,p.section_code FROM acts a
        JOIN projects p ON p.id=a.project_id JOIN document_types d ON d.code=a.act_type
        WHERE p.object_id=? AND a.is_active=1 ORDER BY a.date_signed IS NULL,a.date_signed,a.id''', (project['object_id'],))]
    from .ojr import special_rows,roster,directory
    registry=special_rows(c,project_id)
    sections['5'] = []
    for document in documents:
        status=c.execute("SELECT * FROM act_execution_status WHERE act_id=? AND state='signed'",(document['id'],)).fetchone()
        if status:
            sections['5'].append({**document,'work_description':status['work_description'],'date_signed':status['signed_date'],
                                 'signed_by':list(json.loads(status['signers_json']).values())})

    connected = [dict(r) for r in c.execute('''SELECT j.*,a.project_id,a.act_num,a.date_signed,d.name,p.section_code
        FROM act_journals j JOIN acts a ON a.id=j.act_id JOIN document_types d ON d.code=a.act_type
        JOIN projects p ON p.id=a.project_id WHERE p.object_id=? AND a.is_active=1 ORDER BY a.id''', (project['object_id'],))]
    incoming = []
    for entry in entries:
        if entry['kind'] != 'incoming' or entry['project_id'] != project_id:
            continue
        data = entry['work_fields']
        resource = c.execute('SELECT * FROM resources WHERE id=?', (entry['resource_id'],)).fetchone()
        supply = c.execute('SELECT * FROM supplies WHERE id=? AND project_id=? AND resource_id=?',
                           (data.get('supply_id'), project_id, entry['resource_id'])).fetchone()
        review = c.execute('SELECT * FROM quality_reviews WHERE id=? AND resource_id=?',
                           (data.get('quality_review_id'), entry['resource_id'])).fetchone()
        review = dict(review) if review else None
        if review:
            from .workflow import resource_fingerprint
            attachment = c.execute('SELECT sha256 FROM attachments WHERE id=?', (review['attachment_id'],)).fetchone()
            review['is_current'] = bool(resource and attachment and
                review['resource_sha256'] == resource_fingerprint(resource) and
                review['attachment_sha256'] == attachment['sha256'])
        incoming.append({**entry, 'resource': dict(resource) if resource else None,
                         'supply': dict(supply) if supply else None, 'quality_review': review})
    from .workspace import snapshot
    from .ojr import title_assignments, construction_dates
    from .incoming import DOCUMENT_TYPES
    return {'object': dict(c.execute('SELECT * FROM objects WHERE id=?', (project['object_id'],)).fetchone()),
            'automatic': automatic_journals(c, project_id),
            'incoming_document_types': DOCUMENT_TYPES,
            'participants': snapshot(c, project['object_id'])['participants'],
            'title_assignments': title_assignments(c, project_id),
            'construction_dates': construction_dates(c, project_id),
            'sections': sections, 'section_names': SECTIONS, 'legacy': legacy,
            'connected': connected, 'incoming': incoming, 'incoming_queue': incoming_queue(c,project_id,incoming), 'special':registry,'roster':roster(c,project_id),
            'directory':directory(c,project_id),'draft_documents':documents,
            'title_signatories':[dict(r) for r in c.execute('SELECT * FROM signatory_assignments WHERE object_id=? ORDER BY role_key',(project['object_id'],))],
            'title_organizations':[dict(r) for r in c.execute('SELECT * FROM organization_assignments WHERE object_id=? ORDER BY role_key',(project['object_id'],))]}


def automatic_journals(c, project_id):
    """Переходы к живым журналам, без создания копий, форм или деловых записей."""
    from .ojr import object_id
    oid = object_id(c, project_id)
    work = c.execute("""SELECT count(*) AS count, min(e.entry_date) AS date
        FROM workspace_entries e JOIN projects p ON p.id=e.project_id
        WHERE p.object_id=? AND e.kind IN ('work','journal')""", (oid,)).fetchone()
    signed = c.execute("""SELECT count(*) AS count, min(s.signed_date) AS date
        FROM act_execution_status s JOIN acts a ON a.id=s.act_id
        JOIN projects p ON p.id=a.project_id WHERE p.object_id=? AND a.is_active=1 AND s.state='signed'""", (oid,)).fetchone()
    special = c.execute("""SELECT count(*) AS count, min(coalesce(issued_date, transfer_date)) AS date
        FROM special_journals WHERE object_id=?""", (oid,)).fetchone()
    result = []
    sources = (work, signed, special)
    count = sum(row['count'] for row in sources)
    if count:
        result.append({'kind':'ojr','name':'Общий журнал работ (ОЖР)', 'project_id':project_id,
                       'section_code':None,'count':count,
                       'date':min((row['date'] for row in sources if row['date']), default=None)})
    for kind, name, condition in (
        ('incoming', 'Журнал входного контроля (ЖВК)', "e.kind='incoming'"),
        ('cable', 'Журнал прокладки кабеля (ЖПК)', "e.kind='work' AND e.work_type='cable'"),
    ):
        for row in c.execute(f"""SELECT p.id,p.section_code,count(*) AS count,min(e.entry_date) AS date
            FROM workspace_entries e JOIN projects p ON p.id=e.project_id
            WHERE p.object_id=? AND {condition} GROUP BY p.id ORDER BY p.id""", (oid,)):
            result.append({'kind':kind,'name':name,'project_id':row['id'],
                           'section_code':row['section_code'],'count':row['count'],'date':row['date']})
    return result


def incoming_queue(c, project_id, incoming):
    """Очередь по точной поставке. Приёмка поставки не означает завершение контроля."""
    latest = {}
    for entry in sorted(incoming,key=lambda e:e['id']):
        if entry.get('supply'):
            latest[entry['supply']['id']] = entry
    result = []
    for row in c.execute("SELECT s.*,r.name AS resource_name,r.type_mark FROM supplies s JOIN resources r ON r.id=s.resource_id WHERE s.project_id=? AND s.status!='void' ORDER BY s.supply_date IS NULL,s.supply_date,s.id",(project_id,)):
        supply = dict(row)
        entry = latest.get(supply['id'])
        outcome = entry['work_fields'].get('incoming_result','pending') if entry else None
        status = 'rejected' if supply['status']=='rejected' or outcome=='rejected' else 'accepted' if outcome=='accepted' and supply['status']=='accepted' else 'awaiting_receipt' if outcome=='accepted' else 'in_progress' if entry else 'not_checked'
        if status != 'accepted':
            result.append({**supply,'control_status':status,'entry_id':entry['id'] if entry else None})
    return result
