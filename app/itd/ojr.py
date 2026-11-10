"""Объектный ОЖР: единый реестр журналов, персонал и подтверждение подписания."""
import json

from .changes import log_event
from .db import calendar_date,required_text,atomic_operation
from .workflow import same_project


def object_id(c,pid):
    row=c.execute('SELECT object_id FROM projects WHERE id=?',(pid,)).fetchone()
    if not row: raise ValueError('Раздел РД не найден')
    return row[0]


def directory(c,pid):
    oid=object_id(c,pid)
    # В том числе назначения участников в отдельных разделах объекта.
    orgs=[dict(r) for r in c.execute('''SELECT o.* FROM organizations o WHERE o.id IN (
        SELECT org_id FROM object_participants WHERE object_id=? UNION
        SELECT org_id FROM organization_assignments WHERE object_id=? OR project_id IN (SELECT id FROM projects WHERE object_id=?)
        ) ORDER BY o.full_name''',(oid,oid,oid))]
    ids={o['id'] for o in orgs}
    people=[dict(r) for r in c.execute('SELECT * FROM signatories ORDER BY fio') if r['org_id'] in ids]
    return {'organizations':orgs,'people':people}


def participant_ids(directory):
    organizations = {str(org['id']): org for org in directory['organizations']}
    people = {str(person['id']): {**person, 'organization': organizations.get(str(person['org_id']))}
              for person in directory['people']}
    return {'Organisation': organizations, 'Representative': people}


def construction_dates(c,pid):
    """Живые границы дат разделов; самостоятельные реквизиты объекта не переписываются."""
    oid=object_id(c,pid)
    projects=c.execute('SELECT smr_start,smr_end,pnr_start,pnr_end FROM projects WHERE object_id=?',(oid,)).fetchall()
    starts=[r[k] for r in projects for k in ('smr_start','pnr_start') if r[k]]
    ends=[r[k] for r in projects for k in ('smr_end','pnr_end') if r[k]]
    obj=c.execute('SELECT work_start,work_end FROM objects WHERE id=?',(oid,)).fetchone()
    return {'start':min(starts) if starts else obj['work_start'],
            'end':max(ends) if ends else obj['work_end']}


def title_assignments(c,pid):
    """Все явные назначения объекта и его разделов, включая несколько лиц одной роли."""
    oid=object_id(c,pid)
    result=[]
    scopes=[('object_id',oid,None)]+[('project_id',p['id'],p['section_code']) for p in
        c.execute('SELECT id,section_code FROM projects WHERE object_id=? ORDER BY id',(oid,))]
    for scope,identity,section in scopes:
        orgs={r['role_key']:dict(c.execute('SELECT * FROM organizations WHERE id=?',(r['org_id'],)).fetchone())
              for r in c.execute(f'SELECT * FROM organization_assignments WHERE {scope}=?',(identity,))}
        seen=set()
        for r in c.execute(f'SELECT * FROM signatory_assignments WHERE {scope}=? ORDER BY role_key,id',(identity,)):
            person=dict(c.execute('SELECT * FROM signatories WHERE id=?',(r['signatory_id'],)).fetchone())
            org=dict(c.execute('SELECT * FROM organizations WHERE id=?',(person['org_id'],)).fetchone())
            result.append({'record_entity':'signatory_assignments','record_id':r['id'],'role_key':r['role_key'],'person':person,'organization':org,'section_code':section})
            seen.add(r['role_key'])
        for role,org in orgs.items():
            if role not in seen:
                assignment=c.execute(f'SELECT id FROM organization_assignments WHERE {scope}=? AND role_key=?',(identity,role)).fetchone()
                result.append({'record_entity':'organization_assignments','record_id':assignment['id'],'role_key':role,'person':None,'organization':org,'section_code':section})
    return result


def roster(c,pid,date=None):
    oid=object_id(c,pid)
    found={}
    for row in c.execute("SELECT e.* FROM workspace_entries e JOIN projects p ON p.id=e.project_id WHERE p.object_id=? AND e.kind='journal'",(oid,)):
        w=json.loads(row['work_fields'])
        if w.get('journal_section')!='1' or not w.get('person_id'): continue
        person=c.execute('SELECT * FROM signatories WHERE id=?',(w['person_id'],)).fetchone()
        if not person or person['status']!='Действует': continue
        if date and ((w.get('start_date') and date<w['start_date']) or (w.get('end_date') and date>w['end_date'])): continue
        org=c.execute('SELECT * FROM organizations WHERE id=?',(person['org_id'],)).fetchone()
        found[person['id']]={**dict(person),'organization':dict(org),'roster_entry_id':row['id'],
                             'start_date':w.get('start_date'),'end_date':w.get('end_date'),'scope':w.get('scope')}
    return list(found.values())


def validate_executor(c,pid,person_id,date=None):
    if type(person_id) is not int: raise ValueError('Выберите исполнителя из раздела 1 ОЖР')
    person=next((p for p in roster(c,pid,date) if p['id']==person_id),None)
    if not person: raise ValueError('Исполнитель не внесён в раздел 1 ОЖР, отозван или вне периода участия')
    return person


@atomic_operation
def save_special(c,pid,data):
    oid=object_id(c,pid);before=None
    if data.get('id'):
        before=c.execute('SELECT * FROM special_journals WHERE id=? AND object_id=?',(data['id'],oid)).fetchone()
        if not before or before['revision']!=data.get('revision'): raise ValueError('Журнал уже изменён или относится к другому объекту')
    d=directory(c,pid);orgs={o['id']:o for o in d['organizations']};people={p['id']:p for p in d['people']}
    values={k:data.get(k) or None for k in ('org_id','keeper_id','recipient_id','note')}
    values.update(name=required_text(data.get('name'),'Наименование специального журнала'),
                  issued_date=calendar_date(data.get('issued_date') or None),transfer_date=calendar_date(data.get('transfer_date') or None))
    if values['issued_date'] and values['transfer_date'] and values['issued_date']>values['transfer_date']: raise ValueError('Передача журнала раньше выдачи')
    if values['org_id'] and values['org_id'] not in orgs: raise ValueError('Организация журнала не относится к объекту')
    for key in ('keeper_id','recipient_id'):
        if values[key] and (values[key] not in people or people[values[key]]['status']!='Действует'): raise ValueError('Представитель журнала не относится к объекту или отозван')
    if values['keeper_id']:
        org=people[values['keeper_id']]['org_id']
        if values['org_id'] and values['org_id']!=org: raise ValueError('Ответственный за журнал не относится к организации')
        values['org_id']=org
    if before:
        c.execute('UPDATE special_journals SET '+','.join(k+'=?' for k in values)+',revision=revision+1 WHERE id=?',(*values.values(),before['id']))
        identity=before['id']
    else:
        values.update(object_id=oid,project_id=pid)
        identity=c.execute('INSERT INTO special_journals('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',tuple(values.values())).lastrowid
    result=dict(c.execute('SELECT * FROM special_journals WHERE id=?',(identity,)).fetchone())
    from .workspace import extend_journal_dates
    extend_journal_dates(c, result['project_id'], (result['issued_date'], result['transfer_date']),
                         data.get('journal_dates_confirmation'))
    log_event(c,'special-journal-save',entity='special_journals',entity_id=identity,before=dict(before) if before else None,after=result)
    return result


def special_rows(c,pid):
    result=[]
    for row in c.execute('SELECT * FROM special_journals WHERE object_id=? ORDER BY issued_date IS NULL,issued_date,id',(object_id(c,pid),)):
        value=dict(row)
        for col,table,key in [('org_id','organizations','organization'),('keeper_id','signatories','keeper'),('recipient_id','signatories','recipient')]:
            linked=c.execute(f'SELECT * FROM {table} WHERE id=?',(row[col],)).fetchone()
            value[key]=dict(linked) if linked else None
        result.append(value)
    return result


@atomic_operation
def set_act_people(c,pid,aid,people):
    same_project(c,'acts',aid,pid)
    signed=c.execute("SELECT 1 FROM act_execution_status WHERE act_id=? AND state='signed'",(aid,)).fetchone()
    if signed: raise ValueError('Сначала верните подписанный акт в подготовку с указанием основания')
    if not isinstance(people,dict): raise ValueError('Подписанты должны быть сопоставлены ролям')
    from .workspace import DOC_ROLES
    for role,identity in people.items():
        if role not in DOC_ROLES: raise ValueError('Неизвестная роль подписанта')
        try:
            from .document_versions import validate_signer
            person=validate_signer(c,pid,identity,role)
        except ValueError:
            person=validate_executor(c,pid,identity)
            from .participants import participants_context
            assigned=participants_context(c,pid)['organizations'].get(role)
            if assigned and assigned['id']!=person['org_id']: raise ValueError('Организация подписанта не совпадает с назначенной организацией роли')
        selected_org=c.execute('SELECT org_id FROM act_organizations WHERE act_id=? AND role_key=?',(aid,role)).fetchone()
        if selected_org and selected_org['org_id']!=person['org_id']:raise ValueError('Представитель не принадлежит выбранной организации этой роли')
    from .document_versions import remember_fallback_roles
    remember_fallback_roles(c,pid,list(people.items()))
    c.execute('DELETE FROM act_signatories WHERE act_id=?',(aid,))
    c.executemany('INSERT INTO act_signatories VALUES(?,?,?)',[(aid,r,i) for r,i in people.items()])
    log_event(c,'act-signatories',entity='acts',entity_id=aid,after=people)
    return {'act_id':aid,'signatories':people}


def act_people(c,aid):
    result={}
    for row in c.execute('SELECT * FROM act_signatories WHERE act_id=?',(aid,)):
        p=dict(c.execute('SELECT * FROM signatories WHERE id=?',(row['signatory_id'],)).fetchone())
        p['organization']=dict(c.execute('SELECT * FROM organizations WHERE id=?',(p['org_id'],)).fetchone())
        p['fio_short']=p['fio']
        result[row['role_key']]=p
    return result


@atomic_operation
def sign_act(c,pid,data):
    act=same_project(c,'acts',data['act_id'],pid)
    old=c.execute('SELECT * FROM act_execution_status WHERE act_id=?',(act['id'],)).fetchone()
    if data.get('expected_revision')!=(old['revision'] if old else 0): raise ValueError('Статус акта уже изменён')
    state=data.get('state')
    if state not in ('draft','signed'): raise ValueError('Неизвестный статус акта')
    basis=required_text(data.get('basis'),'Основание статуса')
    desc=required_text(act_work_description(c,act['id']) or data.get('work_description') or (old['work_description'] if old else None),'Наименование работ и место')
    date=calendar_date(data.get('signed_date') or None)
    if old and old['state']=='signed' and state=='draft':
        c.execute("UPDATE act_execution_status SET state='draft' WHERE act_id=?",(act['id'],))
    if 'signatories' in data:
        current={r['role_key']:r['signatory_id'] for r in c.execute('SELECT * FROM act_signatories WHERE act_id=?',(act['id'],))}
        if data['signatories']!=current:
            set_act_people(c,pid,act['id'],data['signatories'])
    people=act_people(c,act['id'])
    if state=='signed':
        if not act['is_active'] or not date or not people: raise ValueError('Для подписания нужны активный акт, дата и выбранные подписанты')
        for role,p in people.items():
            try:
                from .document_versions import validate_signer
                validate_signer(c,pid,p['id'],role,date)
            except ValueError:
                validate_executor(c,pid,p['id'],date)
        from .document_versions import required_roles
        if set(required_roles(c,act['id']))-people.keys(): raise ValueError('Выберите подписантов всех обязательных ролей формы')
        from .workspace import extend_journal_dates
        extend_journal_dates(c, pid, (date,), data.get('journal_dates_confirmation'))
        c.execute('UPDATE acts SET date_signed=? WHERE id=?',(date,act['id']))
    values=(state,desc,basis,json.dumps(people,ensure_ascii=False),date if state=='signed' else None)
    if old:
        c.execute('UPDATE act_execution_status SET state=?,work_description=?,basis=?,signers_json=?,signed_date=?,revision=revision+1 WHERE act_id=?',(*values,act['id']))
    else: c.execute('INSERT INTO act_execution_status(act_id,state,work_description,basis,signers_json,signed_date) VALUES(?,?,?,?,?,?)',(act['id'],*values))
    log_event(c,'act-execution-status',entity='acts',entity_id=act['id'],before=dict(old) if old else None,after={'state':state,'basis':basis,'signed_date':date})
    return dict(c.execute('SELECT * FROM act_execution_status WHERE act_id=?',(act['id'],)).fetchone())


@atomic_operation
def save_title(c,pid,data):
    """Выбранные роли сохраняются общими назначениями объекта, без копий реквизитов."""
    from .participants import assign
    from .workspace import DOC_ROLES
    oid=object_id(c,pid);d=directory(c,pid)
    people={p['id']:p for p in d['people']};orgs={o['id']:o for o in d['organizations']}
    current=[dict(r) for r in c.execute('SELECT * FROM signatory_assignments WHERE object_id=? ORDER BY role_key',(oid,))]
    expected=data.get('expected')
    if expected!=current: raise ValueError('Назначения уже изменились. Обновите титульный лист')
    selected=data.get('signatories',{});organizations=data.get('organizations',{})
    if not isinstance(selected,dict) or not isinstance(organizations,dict) or (set(selected)|set(organizations))-set(DOC_ROLES): raise ValueError('Некорректные роли титульного листа')
    for role in set(selected)|set(organizations):
        identity=selected.get(role);org=organizations.get(role)
        if identity:
            if identity not in people or people[identity]['status']!='Действует': raise ValueError('Выберите действующего представителя объекта')
            person=people[identity]
            if org and org!=person['org_id']: raise ValueError('Представитель не относится к организации роли')
            org=person['org_id']
            assign(c,entity='signatory',entity_id=identity,role_key=role,object_id=oid)
        else: c.execute('DELETE FROM signatory_assignments WHERE object_id=? AND role_key=?',(oid,role))
        if org:
            if org not in orgs: raise ValueError('Организация не относится к объекту')
            assign(c,entity='organization',entity_id=org,role_key=role,object_id=oid)
        elif role in organizations: c.execute('DELETE FROM organization_assignments WHERE object_id=? AND role_key=?',(oid,role))
    log_event(c,'ojr-title-assignments',entity='objects',entity_id=oid,after={'signatories':selected,'organizations':organizations})
    return {'saved':True}


def act_work_description(c,aid):
    entries=c.execute('SELECT e.title,e.details FROM workspace_entries e JOIN act_entry_sources s ON s.entry_id=e.id WHERE s.act_id=? ORDER BY e.entry_date,e.id',(aid,)).fetchall()
    if entries: return '; '.join(' · '.join(v for v in (e['title'],e['details']) if v) for e in entries)
    from .fields import merge_fields
    row=c.execute('SELECT a.fields,d.fields AS definitions FROM acts a JOIN document_types d ON d.code=a.act_type WHERE a.id=?',(aid,)).fetchone()
    if row:
        fields=merge_fields(json.loads(row['definitions']),json.loads(row['fields']))
        for key in ('works_description','work_description','works_name','work_name','hidden_works','construction_name','construction_description','works'):
            field=next((f for f in fields if f['key']==key and f.get('kind')=='literal'),None)
            if field and isinstance(field.get('value'),str) and field['value'].strip(): return field['value']
    return None
