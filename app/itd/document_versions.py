"""Карточки версий акта. Исторические версии не меняют текущий акт."""
import json
from .db import atomic_operation, calendar_date
from .workflow import same_project
from .changes import log_event, update_record


def required_roles(c, aid):
    from .fields import merge_fields
    a=c.execute('SELECT a.fields,d.fields AS defaults FROM acts a JOIN document_types d ON d.code=a.act_type WHERE a.id=?',(aid,)).fetchone()
    result=set()
    def visit(fields):
        for f in fields:
            if f.get('state') in ('hidden','not_applicable'): continue
            if f['kind']=='signatory' and f.get('required'): result.add(f['role'])
            if f.get('required') and f.get('source','').startswith('signatories.'): result.add(f['source'].split('.')[1])
            if f['kind']=='table': visit(f.get('fields',f.get('columns',[])))
    from .form_defaults import apply_form_defaults
    code=c.execute('SELECT act_type FROM acts WHERE id=?',(aid,)).fetchone()[0]
    visit(apply_form_defaults(code,merge_fields(json.loads(a['defaults']),json.loads(a['fields']))))
    return sorted(result)


def candidates(c,pid,*,fallback=True):
    from .ojr import directory
    from .workspace import DOC_ROLES, OTHER_SIGNER_ROLES
    from .participants import participants_context
    context = participants_context(c,pid)
    companies = context['organizations']
    result = {
        role: [{key: value for key, value in person.items() if key != 'role_key'} for person in assigned
               if person['status'] == 'Действует' and (role not in companies or person['org_id'] == companies[role]['id'])]
        for role, assigned in context['signatory_candidates'].items()
    }
    people = [p for p in directory(c,pid)['people'] if p['status'] == 'Действует']
    for role in DOC_ROLES:
        if role in OTHER_SIGNER_ROLES or fallback and not result.get(role):
            result[role] = people
    return result


def validate_signer(c,pid,identity,role,date=None):
    person=next((p for p in candidates(c,pid).get(role,[]) if p['id']==identity),None)
    if not person: raise ValueError('Выберите действующего представителя текущего объекта')
    if date:
        # Периоды организаций и полномочия не подменяются друг другом.
        from .ojr import roster
        rows=[p for p in roster(c,pid) if p['id']==identity]
        if rows and not any(p['id']==identity for p in roster(c,pid,date)): raise ValueError('Подписант вне периода участия')
    return {**person,'organization':dict(c.execute('SELECT * FROM organizations WHERE id=?',(person['org_id'],)).fetchone()),'fio_short':person['fio']}


def remember_fallback_roles(c,pid,people):
    """Запоминает проверенный выбор из общего списка в ролях участников объекта."""
    from .participants import assign
    from .ojr import object_id
    from .workspace import OTHER_SIGNER_ROLES
    assigned=candidates(c,pid,fallback=False)
    empty_roles={role for role,_ in people if role not in OTHER_SIGNER_ROLES and not assigned.get(role)}
    for role,identity in set(people):
        if role not in empty_roles:continue
        oid=object_id(c,pid)
        exists=c.execute('SELECT 1 FROM signatory_assignments WHERE object_id=? AND role_key=? AND signatory_id=?',
                         (oid,role,identity)).fetchone()
        if exists:continue
        assign(c,entity='signatory',entity_id=identity,role_key=role,object_id=oid,multiple=True)
        log_event(c,'signatory-role-auto-assigned',entity='signatories',entity_id=identity,
                  after={'object_id':oid,'role_key':role})


def card(c,aid):
    a=dict(c.execute('SELECT * FROM acts WHERE id=?',(aid,)).fetchone())
    from .act_participants import selections
    from .ojr import act_work_description
    return {'organizations':selections(c,aid),'work_description':act_work_description(c,aid),**{k:(json.loads(a[k]) if k=='fields' else a[k]) for k in ('date_signed','filename_title','registry_note','sheets_count','fields')}}


def decode(row):
    return {**dict(row),'card':json.loads(row['card_json']),'signers':json.loads(row['signers_json']),'snapshot':json.loads(row['snapshot_json']) if row['snapshot_json'] else None}


def versions(c,pid,aid):
    same_project(c,'acts',aid,pid)
    return [decode(r) for r in c.execute('SELECT * FROM document_versions WHERE act_id=? ORDER BY ordinal',(aid,))]


@atomic_operation
def ensure(c,pid,aid):
    existing=versions(c,pid,aid)
    if existing:
        last=existing[-1]
        live=card(c,aid)
        if any(last['card'].get(k,{} if k=='organizations' else None)!=v for k,v in live.items() if k!='work_description'):
            if last['release_id']:
                c.execute('INSERT INTO document_versions(act_id,ordinal,card_json,signers_json) VALUES(?,?,?,?)',(aid,last['ordinal']+1,json.dumps(live,ensure_ascii=False),json.dumps([{**s,'signed':False,'signed_date':None} for s in last['signers']],ensure_ascii=False)))
            else:
                c.execute('UPDATE document_versions SET card_json=?,revision=revision+1 WHERE id=?',(json.dumps(live,ensure_ascii=False),last['id']))
            return versions(c,pid,aid)
        return existing
    state=c.execute('SELECT * FROM act_execution_status WHERE act_id=?',(aid,)).fetchone()
    people=[]
    for r in c.execute('SELECT s.role_key,p.* FROM act_signatories s JOIN signatories p ON p.id=s.signatory_id WHERE act_id=?',(aid,)):
        people.append({'role':r['role_key'],'person_id':r['id'],'person':dict(r),'signed':bool(state and state['state']=='signed'),'signed_date':state['signed_date'] if state else None})
    releases=c.execute('SELECT r.*,g.context_json FROM releases r LEFT JOIN generated_documents g ON g.id=r.generated_id WHERE r.act_id=? ORDER BY r.created_at,r.id',(aid,)).fetchall()
    for ordinal,r in enumerate(releases,1):
        historical={k:None for k in card(c,aid)};historical.update(fields=[],filename_title=r['title'],sheets_count=r['sheets_count'])
        c.execute('INSERT INTO document_versions(act_id,ordinal,card_json,signers_json,release_id,snapshot_json) VALUES(?,?,?,?,?,?)',
                  (aid,ordinal,json.dumps(historical,ensure_ascii=False),'[]',r['id'],r['context_json']))
    c.execute('INSERT INTO document_versions(act_id,ordinal,card_json,signers_json) VALUES(?,?,?,?)',
              (aid,len(releases)+1,json.dumps(card(c,aid),ensure_ascii=False),json.dumps(people,ensure_ascii=False)))
    return versions(c,pid,aid)


@atomic_operation
def create(c,pid,aid,expected):
    current=ensure(c,pid,aid)[-1]
    if expected!={'id':current['id'],'revision':current['revision']}: raise ValueError('Версии уже изменены. Обновите карточку')
    status=c.execute('SELECT * FROM act_execution_status WHERE act_id=?',(aid,)).fetchone()
    if status and status['state']=='signed':
        from .ojr import sign_act
        sign_act(c,pid,{'act_id':aid,'state':'draft','basis':'Создание следующей версии пользователем','expected_revision':status['revision']})
    signers=[{**s,'signed':False,'signed_date':None} for s in current['signers']
             if c.execute('SELECT 1 FROM signatories WHERE id=?',(s['person_id'],)).fetchone()]
    c.execute('INSERT INTO document_versions(act_id,ordinal,card_json,signers_json) VALUES(?,?,?,?)',
              (aid,current['ordinal']+1,json.dumps(card(c,aid),ensure_ascii=False),json.dumps(signers,ensure_ascii=False)))
    log_event(c,'document-version-add',entity='acts',entity_id=aid,after={'ordinal':current['ordinal']+1})
    return versions(c,pid,aid)


@atomic_operation
def save(c,pid,data):
    from .workspace import OTHER_SIGNER_ROLES

    aid=data['act_id']; existing=versions(c,pid,aid)
    if not existing: raise ValueError('Сначала откройте карточку версии')
    current=existing[-1]
    if data.get('id')!=current['id'] or data.get('revision')!=current['revision']: raise ValueError('Версия уже изменена или является исторической')
    values=data.get('card',{}); old=card(c,aid)
    if set(values)-set(old): raise ValueError('Недопустимые поля карточки')
    status=c.execute('SELECT * FROM act_execution_status WHERE act_id=?',(aid,)).fetchone()
    if status and status['state']=='signed': raise ValueError('Создайте следующую версию для изменения подписанного документа')
    if any(current['card'].get(k,{} if k=='organizations' else None)!=v for k,v in old.items() if k!='work_description'):
        raise ValueError('Акт изменён вне карточки версии. Закройте окно и обновите сведения')
    changes={k:v for k,v in values.items() if k not in ('work_description','organizations') and v!=old[k]}
    if current['release_id'] and changes: raise ValueError('Для изменения созданного файла добавьте следующую версию')
    if changes: update_record(c,entity='acts',record_id=aid,changes=changes,expected={k:c.execute('SELECT fields FROM acts WHERE id=?',(aid,)).fetchone()[0] if k=='fields' else old[k] for k in changes})
    from .act_participants import set_organizations
    companies=values.get('organizations',old['organizations'])
    if current['release_id'] and companies!=old['organizations']:raise ValueError('Для изменения организации созданного файла добавьте следующую версию')
    set_organizations(c,pid,aid,companies)
    people=data.get('signers',[])
    if not isinstance(people,list):raise ValueError('Ожидается список подписантов')
    primary={}; saved=[];seen=set()
    for s in people:
        role=s['role'];identity=s['person_id']
        if role in OTHER_SIGNER_ROLES and role in primary:
            raise ValueError('Для каждой из трёх строк «Иное лицо» выберите одного представителя')
        if (role,identity) in seen: raise ValueError('Подписант повторяется в одной роли')
        seen.add((role,identity))
        person=validate_signer(c,pid,identity,role,s.get('signed_date'))
        if role in companies and person['org_id']!=companies[role]:raise ValueError('Организация и представитель одной роли должны совпадать')
        signed=s.get('signed') is True
        date=calendar_date(s.get('signed_date') or None)
        if signed and not date:raise ValueError('Для отметки «Подписан» укажите дату')
        primary.setdefault(role,identity)
        saved.append({'role':role,'person_id':identity,'person':person,'signed':signed,'signed_date':date if signed else None})
    if current['release_id'] and {(s['role'],s['person_id']) for s in saved}!={(s['role'],s['person_id']) for s in current['signers']}:
        raise ValueError('Для изменения подписантов созданного файла добавьте следующую версию')
    from .ojr import set_act_people, sign_act
    remember_fallback_roles(c,pid,[(s['role'],s['person_id']) for s in saved])
    set_act_people(c,pid,aid,primary)
    required = set(required_roles(c,aid))
    required_signers = [s for s in saved if not required or s['role'] in required]
    if saved and all(s['signed'] for s in saved) and required - primary.keys():
        raise ValueError('Выберите подписантов всех обязательных ролей формы')
    if required_signers and not (required - primary.keys()) and all(s['signed'] for s in required_signers):
        signed = [s for s in saved if s['signed']]
        name = c.execute('SELECT d.name FROM document_types d JOIN acts a ON a.act_type=d.code WHERE a.id=?', (aid,)).fetchone()[0]
        sign_act(c,pid,{'act_id':aid,'state':'signed','signed_date':max(s['signed_date'] for s in signed),'basis':'Подписание версии подтверждено пользователем','work_description':data.get('work_description') or name,'expected_revision':status['revision'] if status else 0})
        signed_people={}
        for s in signed:
            key=s['role'] if s['role'] not in signed_people else s['role']+'__'+str(s['person_id'])
            signed_people[key]=s['person']
        c.execute('UPDATE act_execution_status SET signers_json=? WHERE act_id=?',(json.dumps(signed_people,ensure_ascii=False),aid))
    from .acts import build_context
    resolved=current['snapshot'] if current['release_id'] and current['snapshot'] else build_context(c,aid,draft=True)['context']
    c.execute('UPDATE document_versions SET card_json=?,signers_json=?,snapshot_json=?,revision=revision+1 WHERE id=?',
              (json.dumps({**card(c,aid),'work_description':data.get('work_description',old.get('work_description'))},ensure_ascii=False),json.dumps(saved,ensure_ascii=False),json.dumps(resolved,ensure_ascii=False),current['id']))
    log_event(c,'document-version-save',entity='acts',entity_id=aid,after={'version_id':current['id']})
    return versions(c,pid,aid)


def attach_release(c,aid,rid):
    act=c.execute('SELECT project_id FROM acts WHERE id=?',(aid,)).fetchone()
    if not act:raise ValueError('Акт не найден')
    pid=act[0]
    current=ensure(c,pid,aid)[-1]
    if current['release_id'] and current['release_id']!=rid:
        # Новый файл получает собственную карточку; подписи файла не переносятся.
        create(c,pid,aid,{'id':current['id'],'revision':current['revision']})
        current=versions(c,pid,aid)[-1]
    c.execute('UPDATE document_versions SET release_id=?,card_json=?,snapshot_json=?,revision=revision+1 WHERE id=?',
              (rid,json.dumps(card(c,aid),ensure_ascii=False),c.execute('SELECT context_json FROM generated_documents g JOIN releases r ON r.generated_id=g.id WHERE r.id=?',(rid,)).fetchone()[0],current['id']))


def prepare_generation(c,aid):
    act=c.execute('SELECT project_id FROM acts WHERE id=?',(aid,)).fetchone()
    if not act:raise ValueError('Акт не найден')
    pid=act[0]
    current=ensure(c,pid,aid)[-1]
    if current['release_id']:
        create(c,pid,aid,{'id':current['id'],'revision':current['revision']})

    current=versions(c,pid,aid)[-1]
    # Общие операции CLI могут менять выбор вне карточки версии. Состав
    # новой печати и её карточки должен совпадать, включая необязательные роли.
    from .ojr import act_people
    explicit = act_people(c, aid)
    primary = {}
    for signer in current['signers']:
        primary.setdefault(signer['role'], signer['person_id'])
    if explicit and primary != {role: person['id'] for role, person in explicit.items()}:
        selected = [{'role': role, 'person_id': person['id'], 'person': person,
                     'signed': False, 'signed_date': None} for role, person in explicit.items()]
        c.execute('UPDATE document_versions SET signers_json=?,revision=revision+1 WHERE id=?',
                  (json.dumps(selected,ensure_ascii=False),current['id']))
        current=versions(c,pid,aid)[-1]
    # Неоднозначная роль остаётся пустой; единственный участник подставляется явно.
    if not current['signers']:
        from .ojr import act_people
        from .participants import participants_context
        people=act_people(c,aid) or participants_context(c,pid)['signatories']
        selected=[]
        for role in required_roles(c,aid):
            person=people.get(role)
            if person:
                selected.append({'role':role,'person_id':person['id'],'person':person,'signed':False,'signed_date':None})
        c.execute('UPDATE document_versions SET signers_json=? WHERE id=?',(json.dumps(selected,ensure_ascii=False),current['id']))
