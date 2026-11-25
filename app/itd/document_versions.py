"""Карточки версий акта. Исторические версии не меняют текущий акт."""
import json
from pathlib import Path
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
            if f.get('binding_role') and f.get('required'): result.add(f['binding_role'])
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
    if saved and all(s['signed'] for s in saved) and required - primary.keys():
        raise ValueError('Выберите подписантов всех обязательных ролей формы')
    completed = bool(saved) and not (required - primary.keys()) and all(s['signed'] for s in saved)
    signed_attachment = data.get('signed_attachment_id', current.get('signed_attachment_id'))
    if completed:
        if not signed_attachment:
            raise ValueError('Загрузите подписанный документ после подтверждения всех подписантов')
        attachment = c.execute('''SELECT a.* FROM attachments a JOIN project_attachments p ON p.attachment_id=a.id
                                  WHERE p.project_id=? AND a.id=?''', (pid, signed_attachment)).fetchone()
        if not attachment:
            raise ValueError('Подписанный файл не принадлежит текущему разделу')
        if Path(attachment['original_name']).suffix.lower() not in ('.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg'):
            raise ValueError('Загрузите подписанный документ в формате PDF, Word или изображения')
        from .archive import original_path, digest
        database = Path(c.execute('PRAGMA database_list').fetchone()[2])
        path = original_path(c, database.parent / 'archive', attachment['storage_path'])
        if not path.is_file() or not path.stat().st_size or digest(path) != attachment['sha256']:
            raise ValueError('Подписанный оригинал отсутствует или изменён')
        from .archive import link_file
        link_file(c, attachment_id=signed_attachment, entity='act', entity_id=aid)
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
    c.execute('UPDATE document_versions SET card_json=?,signers_json=?,snapshot_json=?,signed_attachment_id=?,revision=revision+1 WHERE id=?',
              (json.dumps({**card(c,aid),'work_description':data.get('work_description',old.get('work_description'))},ensure_ascii=False),json.dumps(saved,ensure_ascii=False),json.dumps(resolved,ensure_ascii=False),signed_attachment if completed else None,current['id']))
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


def checked_version(c, pid, data):
    items = versions(c, pid, data['act_id'])
    selected = next((v for v in items if v['id'] == data.get('id')), None)
    if selected is None or selected['revision'] != data.get('revision'):
        raise ValueError('Версия уже изменена. Обновите карточку')
    return items, selected


@atomic_operation
def delete(c, pid, data):
    items, selected = checked_version(c, pid, data)
    if len(items) == 1:
        raise ValueError('Нельзя удалить единственную версию документа')
    if data.get('expected') != [{'id': v['id'], 'revision': v['revision']} for v in items]:
        raise ValueError('Список версий изменён. Обновите карточку')
    aid = data['act_id']
    c.execute('DELETE FROM document_versions WHERE id=?', (selected['id'],))
    # Сначала уводим номера за прежний диапазон, чтобы не нарушить UNIQUE.
    remaining = [v for v in items if v['id'] != selected['id']]
    offset = max(v['ordinal'] for v in items)
    c.execute('UPDATE document_versions SET ordinal=ordinal+? WHERE act_id=?', (offset, aid))
    for number, version in enumerate(remaining, 1):
        c.execute('UPDATE document_versions SET ordinal=?,revision=revision+1 WHERE id=?', (number, version['id']))
    if selected['release_id']:
        from .releases import unselect_release
        unselect_release(c, selected['release_id'])
    if selected['id'] == items[-1]['id']:
        last = remaining[-1]
        # Восстанавливаем именно сохранённую карточку, а не создаём новую версию
        # из оставшихся текущих реквизитов удалённой версии.
        c.execute("UPDATE act_execution_status SET state='draft',revision=revision+1 WHERE act_id=?", (aid,))
        old = card(c, aid)
        restored = last['card']
        changes = {k: restored.get(k) for k in old if k not in ('organizations', 'work_description') and old[k] != restored.get(k)}
        if changes:
            update_record(c, entity='acts', record_id=aid, changes=changes)
        # Исторические назначения не требуют действующих сегодня полномочий.
        companies = {role: identity for role, identity in restored.get('organizations', {}).items()
                     if c.execute('SELECT 1 FROM organizations WHERE id=?', (identity,)).fetchone()}
        c.execute('DELETE FROM act_organizations WHERE act_id=?', (aid,))
        c.executemany('INSERT INTO act_organizations(act_id,role_key,org_id) VALUES(?,?,?)',
                      [(aid, role, identity) for role, identity in companies.items()])
        if companies != restored.get('organizations', {}):
            restored = {**restored, 'organizations': companies}
            c.execute('UPDATE document_versions SET card_json=? WHERE id=?', (json.dumps(restored, ensure_ascii=False), last['id']))
        c.execute('DELETE FROM act_signatories WHERE act_id=?', (aid,))
        people = {}
        for signer in last['signers']:
            if c.execute('SELECT 1 FROM signatories WHERE id=?', (signer['person_id'],)).fetchone():
                people.setdefault(signer['role'], signer)
        for role, signer in people.items():
            c.execute('INSERT INTO act_signatories(act_id,role_key,signatory_id) VALUES(?,?,?)', (aid, role, signer['person_id']))
        completed = bool(last['signers']) and all(s.get('signed') for s in last['signers'])
        if completed:
            snapshot_people = {}
            for signer in last['signers']:
                if signer.get('person'):
                    key = signer['role'] if signer['role'] not in snapshot_people else signer['role']+'__'+str(signer['person_id'])
                    snapshot_people[key] = signer['person']
            date = max(s['signed_date'] for s in last['signers'])
            payload = (aid, 'signed', restored.get('work_description') or '', 'Восстановление сохранённой версии',
                       json.dumps(snapshot_people, ensure_ascii=False), date)
            c.execute('''INSERT INTO act_execution_status(act_id,state,work_description,basis,signers_json,signed_date)
                         VALUES(?,?,?,?,?,?) ON CONFLICT(act_id) DO UPDATE SET state=excluded.state,
                         work_description=excluded.work_description,basis=excluded.basis,
                         signers_json=excluded.signers_json,signed_date=excluded.signed_date,revision=revision+1''', payload)
        else:
            c.execute('UPDATE act_execution_status SET work_description=?,signers_json=?,signed_date=NULL WHERE act_id=?',
                      (restored.get('work_description') or '', '{}', aid))
        if last['release_id']:
            # Выбор сохраняется даже для утратившегося файла: восстановление
            # карточки не утверждает его целостность; скачивание проверяет хеш.
            c.execute('UPDATE releases SET selected=0 WHERE act_id=?', (aid,))
            c.execute('UPDATE releases SET selected=1 WHERE id=?', (last['release_id'],))
    log_event(c, 'document-version-delete', entity='acts', entity_id=aid,
              before={'version_id': selected['id'], 'ordinal': selected['ordinal']},
              after={'version_ids': [v['id'] for v in remaining]})
    return versions(c, pid, aid)


def regenerate(c, pid, data, templates_dir):
    """Обновить черновик из БД; исторический/подписанный файл — из снимка."""
    import uuid
    from . import releases
    from .acts import find_template, build_context
    from .archive import digest
    from .docx_render import render_docx
    items, selected = checked_version(c, pid, data)
    if selected['attachment_id'] and not selected['release_id']:
        raise ValueError('Загруженный оригинал нельзя пересоздать из шаблона')
    if not selected['snapshot'] and selected['id'] != items[-1]['id']:
        raise ValueError('Для этой исторической версии не сохранён контекст печати')
    if not selected['release_id'] and selected['id'] == items[-1]['id']:
        prepare_generation(c, data['act_id'])
        selected = versions(c, pid, data['act_id'])[-1]
    act = same_project(c, 'acts', data['act_id'], pid)
    form = c.execute('SELECT * FROM document_types WHERE code=?', (act['act_type'],)).fetchone()
    old_release = c.execute('SELECT * FROM releases WHERE id=?', (selected['release_id'],)).fetchone()
    draft = not old_release or old_release['mode'] == 'draft'
    status = c.execute('SELECT state FROM act_execution_status WHERE act_id=?', (act['id'],)).fetchone()
    refresh = selected['id'] == items[-1]['id'] and draft and not (status and status['state'] == 'signed')
    context = (build_context(c, act['id'], draft=draft)['context'] if refresh else
               selected['snapshot'] or build_context(c, act['id'], draft=draft)['context'])
    template = find_template(templates_dir, act['act_type'])
    if old_release:
        old_template = c.execute('SELECT template_sha256 FROM generated_documents WHERE id=?', (old_release['generated_id'],)).fetchone()
        if old_template and old_template[0] != digest(template):
            raise ValueError('Шаблон изменён после выпуска. Создайте новую версию')
    staging = releases.service_directory(c) / 'work' / '.itd-staging' / (uuid.uuid4().hex+'.docx')
    try:
        with _generation_transaction(c):
            from .titles import CODE
            render_docx(template, context, staging, draft=draft, font=context.get('font') if act['act_type'] == CODE else None)
            gid = c.execute('''INSERT INTO generated_documents(act_id,output_path,sha256,mode,context_json,template_sha256)
                               VALUES(?,?,?,?,?,?)''', (act['id'], str(staging), digest(staging), 'draft' if draft else 'final', json.dumps(context, ensure_ascii=False), digest(template))).lastrowid
            rid = releases.register_release(c, project_id=pid, act_id=act['id'], generated_id=gid,
                                           kind='docx', title=form['name'], path=staging, mode='draft' if draft else 'final')
            c.execute('UPDATE document_versions SET release_id=?,snapshot_json=?,revision=revision+1 WHERE id=?',
                      (rid, json.dumps(context, ensure_ascii=False), selected['id']))
            log_event(c, 'document-version-regenerate', entity='acts', entity_id=act['id'],
                      after={'version_id': selected['id'], 'release_id': rid})
    except Exception:
        staging.unlink(missing_ok=True)
        raise
    c.commit()
    from .storage import publish_stored
    published = publish_stored(c,rid,selected['card'].get('filename_title') or form['name'],
                               selected=selected['id']==items[-1]['id'])
    return {'versions': versions(c, pid, act['id']), 'release_id': rid, 'output': published['output']}



# Локальная атомарная часть регенерации; publish ведёт собственный журнал ФС.
from contextlib import contextmanager

@contextmanager
def _generation_transaction(c):
    c.execute('SAVEPOINT regenerate_version')
    try:
        yield
        c.execute('RELEASE regenerate_version')
    except Exception:
        c.execute('ROLLBACK TO regenerate_version')
        c.execute('RELEASE regenerate_version')
        raise
