"""Общие операции ручной формы и CLI. Без модели, SQL из входных данных и подписок."""
import json
import math
from pathlib import Path

from .changes import log_event, update_record
from .db import calendar_date, required_text
from .resources import quantity
from .workflow import row, same_project, payload, expect, insert


WORK_FIELDS = {
 'cable': {'line_number':'Номер линии', 'mark':'Марка, напряжение, сечение',
           'drum':'Барабан и длина', 'couplings':'Количество муфт',
           'temperature':'Температура при прокладке', 'heating':'Подогрев и длительность'},
 'general': {'location':'Место работ', 'method':'Метод выполнения', 'tests':'Испытания'}
}


def period(c, project_id, data):
    project = row(c, 'projects', project_id)
    d = payload(data, ('org_id','active_from','active_to','basis','expected'), ('org_id','basis'))
    if not c.execute('''SELECT 1 FROM object_participants WHERE object_id=? AND org_id=?
        UNION SELECT 1 FROM organization_assignments WHERE (object_id=? OR project_id=?) AND org_id=?''',
        (project['object_id'],d['org_id'],project['object_id'],project_id,d['org_id'])).fetchone():
        raise ValueError('Организация не назначена на объект или раздел')
    before = c.execute('SELECT * FROM participant_periods WHERE object_id=? AND org_id=?', (project['object_id'],d['org_id'])).fetchone()
    if before:
        expect(dict(before), d.get('expected'))
    elif d.get('expected'):
        raise ValueError('Период уже изменён или не найден')
    start, end = calendar_date(d.get('active_from')), calendar_date(d.get('active_to'))
    if start and end and start>end:
        raise ValueError('Начало участия позже окончания')
    values = dict(object_id=project['object_id'],org_id=d['org_id'], active_from=start, active_to=end,
                  basis=required_text(d['basis'],'основание периода'))
    if before:
        c.execute('UPDATE participant_periods SET active_from=?,active_to=?,basis=?,revision=revision+1 WHERE id=?',
                  (start,end,values['basis'],before['id']))
        result = row(c,'participant_periods',before['id'])
        log_event(c,'period-update',entity='participant_periods',entity_id=before['id'],before=dict(before),after=result)
        return result
    return insert(c,'participant_periods',values)


def supply_values(c, project_id, data):
    d = payload(data, ('resource_id','source_key','batch_num','supply_date','quantity','unit','supplier','source','attachment_id','status','note'),
                ('resource_id','source_key','source','status'))
    resource = same_project(c,'resources',d['resource_id'],project_id)
    for name in ('source_key','source'):
        d[name] = required_text(d[name],name)
    if d['status'] not in ('pending','accepted','rejected'):
        raise ValueError('Новая поставка: pending, accepted или rejected')
    d['quantity'] = quantity(d.get('quantity'),'количество поставки')
    d['unit'] = required_text(d.get('unit') or resource['unit'],'единица')
    if d['unit'] != resource['unit']:
        raise ValueError('Единица поставки должна совпадать с ресурсом')
    d['supply_date'] = calendar_date(d.get('supply_date'))
    if d.get('attachment_id') and not c.execute('SELECT 1 FROM project_attachments WHERE project_id=? AND attachment_id=?',(project_id,d['attachment_id'])).fetchone():
        raise ValueError('Источник поставки не связан с разделом')
    for key in ('batch_num','supplier','note'):
        if d.get(key) is not None and not isinstance(d[key],str):
            raise ValueError('Реквизит поставки должен быть текстом')
    d['project_id'] = project_id
    return d


def add_supply(c, project_id, data):
    d = supply_values(c, project_id, data)
    before = c.execute('SELECT * FROM supplies WHERE project_id=? AND source_key=?',(project_id,d['source_key'])).fetchone()
    if before:
        if all(before[k]==v for k,v in d.items()): return dict(before)
        raise ValueError('Ключ источника уже занят другой поставкой')
    return insert(c,'supplies',d)


def set_supply(c, project_id, data):
    d = payload(data,('id','status','note','expected'),('id','status','note','expected'))
    before = same_project(c,'supplies',d['id'],project_id)
    expect(before,d['expected'])
    if 'revision' not in d['expected']: raise ValueError('Нужна ожидаемая revision')
    if d['status'] not in ('accepted','rejected','void') or before['status']=='void':
        raise ValueError('Недопустимый статус поставки')
    note = required_text(d['note'],'основание решения')
    c.execute('UPDATE supplies SET status=?,note=?,revision=revision+1 WHERE id=?',(d['status'],note,d['id']))
    result = row(c,'supplies',d['id'])
    log_event(c,'supply-status',entity='supplies',entity_id=d['id'],before=before,after=result)
    return result


def supply_balance(c,project_id):
    result=[]
    for r in c.execute('SELECT * FROM supplies WHERE project_id=? ORDER BY id',(project_id,)):
        from .inventory import supply_used
        used=math.fsum(supply_used(c,r['id']))
        result.append({**dict(r),'allocated':used,'remaining':None if r['quantity'] is None else r['quantity']-used})
    return result


def allocate(c,project_id,data):
    d=payload(data,('act_id','supply_id','quantity','expected'),('act_id','supply_id','quantity','expected'))
    act=same_project(c,'acts',d['act_id'],project_id)
    supply=same_project(c,'supplies',d['supply_id'],project_id)
    current=c.execute('SELECT quantity FROM act_materials WHERE act_id=? AND supply_id=?',(act['id'],supply['id'])).fetchone()
    expect({'quantity':current[0] if current else None},d['expected'])
    amount=quantity(d['quantity'],'количество в акте')
    if amount is None: raise ValueError('Нужно количество; 0 снимает выделение')
    if amount:
        if supply['status']!='accepted': raise ValueError('Для акта нужна принятая поставка')
        resource=same_project(c,'resources',supply['resource_id'],project_id)
        if supply['unit']!=resource['unit']: raise ValueError('Единица ресурса изменилась')
        if not act['is_active']: raise ValueError('Акт неактивен')
        if not c.execute('SELECT 1 FROM act_resources WHERE act_id=? AND resource_id=?',(act['id'],resource['id'])).fetchone():
            raise ValueError('Ресурс поставки отсутствует в акте')
        from .inventory import supply_used
        if c.execute('SELECT 1 FROM work_material_allocations w JOIN act_entry_sources e ON e.entry_id=w.entry_id WHERE e.act_id=? AND w.supply_id=?',(act['id'],supply['id'])).fetchone(): raise ValueError('Расход связанной работы уже учтён; повторное списание в акт не требуется')
        others=math.fsum(supply_used(c,supply['id'],exclude_act=act['id']))
        if supply['quantity'] is not None and amount+others>supply['quantity']+1e-9:
            raise ValueError('Количество превышает остаток поставки')
        c.execute('INSERT INTO act_materials VALUES(?,?,?) ON CONFLICT(act_id,supply_id) DO UPDATE SET quantity=excluded.quantity',(act['id'],supply['id'],amount))
    else:
        c.execute('DELETE FROM act_materials WHERE act_id=? AND supply_id=?',(act['id'],supply['id']))
    log_event(c,'act-material',entity='acts',entity_id=act['id'],before={'supply_id':supply['id'],'quantity':current[0] if current else None},after={'supply_id':supply['id'],'quantity':amount})
    return {'act_id':act['id'],'supply_id':supply['id'],'quantity':amount}


def entry_snapshot(entry, *, work_only=False):
    value = dict(entry)
    if work_only:
        value['_work_only'] = True
    return json.dumps(value,sort_keys=True,ensure_ascii=False)


def bind_entries(c,act_id,entry_ids, *, work_only=False):
    act=row(c,'acts',act_id)
    if len(set(entry_ids))!=len(entry_ids): raise ValueError('Повтор записи работ')
    for eid in entry_ids:
        entry=same_project(c,'workspace_entries',eid,act['project_id'])
        if entry['kind']!='work' or entry['act_id'] not in (None,act_id): raise ValueError('Работа уже связана с другим актом')
        if not work_only and entry['resource_id'] and not c.execute('SELECT 1 FROM act_resources WHERE act_id=? AND resource_id=?',(act_id,entry['resource_id'])).fetchone():
            raise ValueError('Ресурс записи работ отсутствует в составе акта')
        if entry['act_id'] is None:
            c.execute('UPDATE workspace_entries SET act_id=?,revision=revision+1 WHERE id=?',(act_id,eid))
        entry=row(c,'workspace_entries',eid)
        c.execute('INSERT INTO act_entry_sources VALUES(?,?,?)',(act_id,eid,entry_snapshot(entry, work_only=work_only)))


def source_issues(c,act_id):
    act=row(c,'acts',act_id); result=[]
    from .inventory import material_issues
    entries={r[0] for r in c.execute('SELECT entry_id FROM act_entry_sources WHERE act_id=? UNION SELECT m.entry_id FROM work_materials m JOIN act_facts f ON f.fact_id=m.fact_id WHERE f.act_id=?',(act_id,act_id))}
    result.extend({**issue,'act_id':act_id} for issue in material_issues(c,act['project_id']) if issue['entry_id'] in entries)
    for src in c.execute('SELECT * FROM act_entry_sources WHERE act_id=?',(act_id,)):
        entry=row(c,'workspace_entries',src['entry_id'])
        frozen=json.loads(src['source_json'])
        work_only=frozen.pop('_work_only',False)
        if not work_only and entry['resource_id'] and not c.execute('SELECT 1 FROM act_resources WHERE act_id=? AND resource_id=?',(act_id,entry['resource_id'])).fetchone():
            result.append({'code':'entry_resource_missing','entry_id':entry['id'],'act_id':act_id})
        if entry['act_id']!=act_id or any(entry.get(k)!=v for k,v in frozen.items()):
            result.append({'code':'entry_source_changed','entry_id':entry['id'],'act_id':act_id})
    for m in c.execute('SELECT m.*,s.resource_id,s.status,s.unit FROM act_materials m JOIN supplies s ON s.id=m.supply_id WHERE act_id=?',(act_id,)):
        resource=row(c,'resources',m['resource_id'])
        if m['status']!='accepted' or m['unit']!=resource['unit'] or not c.execute('SELECT 1 FROM act_resources WHERE act_id=? AND resource_id=?',(act_id,m['resource_id'])).fetchone():
            result.append({'code':'act_material_invalid','act_id':act_id,'supply_id':m['supply_id']})
        supply=row(c,'supplies',m['supply_id'])
        total=math.fsum(x[0] for x in c.execute('SELECT m.quantity FROM act_materials m JOIN acts a ON a.id=m.act_id WHERE supply_id=? AND a.is_active=1',(m['supply_id'],)))
        if supply['quantity'] is not None and total>supply['quantity']+1e-9:
            result.append({'code':'supply_overallocated','act_id':act_id,'supply_id':m['supply_id']})
    return result


def refresh_sources(c,project_id,data):
    d=payload(data,('act_id','reason','expected'),('act_id','reason','expected'))
    same_project(c,'acts',d['act_id'],project_id)
    reason=required_text(d['reason'],'основание повторной сверки')
    before=[dict(r) for r in c.execute('SELECT * FROM act_entry_sources WHERE act_id=? ORDER BY entry_id',(d['act_id'],))]
    if before!=d['expected']: raise ValueError('Источники акта уже изменены')
    for src in before:
        entry=same_project(c,'workspace_entries',src['entry_id'],project_id)
        if entry['act_id']!=d['act_id']: raise ValueError('Связь работы с актом изменилась')
        work_only = json.loads(src['source_json']).get('_work_only', False)
        if not work_only and entry['resource_id'] and not c.execute('SELECT 1 FROM act_resources WHERE act_id=? AND resource_id=?',(d['act_id'],entry['resource_id'])).fetchone():
            raise ValueError('Ресурс работы отсутствует в акте')
        c.execute('UPDATE act_entry_sources SET source_json=? WHERE act_id=? AND entry_id=?',(entry_snapshot(entry, work_only=work_only),d['act_id'],entry['id']))
    log_event(c,'act-sources-review',entity='acts',entity_id=d['act_id'],before=before,after={'reason':reason})
    return {'act_id':d['act_id'],'reviewed':True}


def entry_rows(c,project_id,kind='work',work_type=None):
    records=[]
    for r in c.execute('SELECT * FROM workspace_entries WHERE project_id=? AND kind=? ORDER BY entry_date IS NULL,entry_date,id',(project_id,kind)):
        if work_type and r['work_type']!=work_type: continue
        records.append({**dict(r),'work_fields':json.loads(r['work_fields'])})
    return records


def journal_rows(c,act_id):
    cfg=c.execute('SELECT j.*,a.project_id FROM act_journals j JOIN acts a ON a.id=j.act_id WHERE act_id=?',(act_id,)).fetchone()
    if not cfg: return []
    from .fields import lookup
    mapping=json.loads(cfg['mapping'])
    return [{key:lookup(path,{'entry':e}) for key,path in mapping.items()} for e in entry_rows(c,cfg['project_id'],cfg['entry_kind'],cfg['work_type'])]


def journal_add(c,project_id,data):
    d=payload(data,('act_type','entry_kind','work_type','table_key','mapping','date_signed'),('act_type','entry_kind','table_key','mapping'))
    if d['entry_kind'] not in ('work','incoming','journal'): raise ValueError('Неизвестный вид записей')
    if not isinstance(d['mapping'],dict) or not d['mapping']: raise ValueError('Нужно сопоставление колонок журнала')
    from .fields import source_path
    for key,path in d['mapping'].items():
        if not source_path(path) or not path.startswith('entry.') or not source_path(key) or '.' in key: raise ValueError('Некорректная колонка журнала')
    form=c.execute('SELECT * FROM document_types WHERE code=?',(d['act_type'],)).fetchone()
    if not form: raise ValueError('Сначала подключите выбранную форму')
    field=next((f for f in json.loads(form['fields']) if f['key']==d['table_key'] and f['kind']=='table'),None)
    if field is None: raise ValueError('В форме нет выбранной таблицы')
    column_keys={f['key'] for f in field['fields']}
    if set(d['mapping'])-column_keys: raise ValueError('Колонка отсутствует в таблице формы')
    field=dict(field);field.pop('value',None);field['source']='journal_rows'
    from .acts import add_act
    aid=add_act(c,project_id=project_id,act_type=d['act_type'],date_signed=d.get('date_signed'),fields=[field])
    c.execute('INSERT INTO act_journals VALUES(?,?,?,?)',(aid,d['entry_kind'],d.get('work_type'),json.dumps(d['mapping'],ensure_ascii=False)))
    from .ojr import save_special
    special=save_special(c,project_id,{'name':form['name']})
    c.execute('UPDATE special_journals SET act_id=? WHERE id=?',(aid,special['id']))
    return {'act_id':aid}


def context(c,project_id):
    project=row(c,'projects',project_id)
    return {'supplies':supply_balance(c,project_id),
      'requirements_records':[dict(r) for r in c.execute('SELECT * FROM package_requirements WHERE project_id=?',(project_id,))],
      'org_assignments':[dict(r) for r in c.execute('SELECT * FROM organization_assignments WHERE object_id=? OR project_id=?',(project['object_id'],project_id))],
      'sig_assignments':[dict(r) for r in c.execute('SELECT * FROM signatory_assignments WHERE object_id=? OR project_id=?',(project['object_id'],project_id))],
      'allocations':[dict(r) for r in c.execute('SELECT m.* FROM act_materials m JOIN acts a ON a.id=m.act_id WHERE a.project_id=?',(project_id,))],
      'periods':[dict(r) for r in c.execute('SELECT * FROM participant_periods WHERE object_id=?',(project['object_id'],))],
      'units':[dict(r) for r in c.execute('SELECT * FROM object_units WHERE object_id=?',(project['object_id'],))],
      'sources':[dict(r) for r in c.execute('SELECT s.* FROM act_entry_sources s JOIN acts a ON a.id=s.act_id WHERE a.project_id=? ORDER BY s.entry_id',(project_id,))],
      'journals':[dict(r) for r in c.execute('SELECT j.* FROM act_journals j JOIN acts a ON a.id=j.act_id WHERE a.project_id=?',(project_id,))]}


def execute(c,project_id,action,data):
    """Одна разрешённая операция по точным ID; используется CLI и HTTP."""
    project=row(c,'projects',project_id)
    if not isinstance(data,dict): raise ValueError('Ожидается объект данных')
    if action=='context': return context(c,project_id)
    if action in ('delete-preview','delete-apply'):
        from . import deletion
        allowed=('entity','id','token') if action=='delete-apply' else ('entity','id')
        d=payload(data,allowed,allowed)
        if action=='delete-preview':return deletion.preview(c,project_id,d['entity'],d['id'])
        return deletion.apply(c,project_id,d['entity'],d['id'],d['token'])
    if action=='resource-card-save':
        from .resource_card import save_card
        return save_card(c,project_id,data)
    if action.startswith('resource-import-'):
        from . import resource_import
        operation=action.removeprefix('resource-import-')
        if operation=='stage': return resource_import.stage(c,project_id,data)
        if operation=='preview': return resource_import.inspect(c,project_id,data)
        if operation=='commit':
            database=Path(c.execute('PRAGMA database_list').fetchone()[2])
            return resource_import.commit(c,project_id,data,database.parent/'archive')
        raise ValueError('Неизвестная операция импорта')

    if action=='special-journal-save':
        from .ojr import save_special
        return save_special(c,project_id,data)
    if action=='act-signatories':
        from .ojr import set_act_people
        return set_act_people(c,project_id,data['act_id'],data['signatories'])
    if action=='act-status':
        from .ojr import sign_act
        return sign_act(c,project_id,data)
    if action in ('document-version-ensure', 'document-version-save'):
        from . import document_versions
        same_project(c, 'acts', data['act_id'], project_id)
        if action == 'document-version-ensure':
            return document_versions.ensure(c, project_id, data['act_id'])
        return document_versions.save(c, project_id, data)

    if action=='assign':
        from .participants import assign
        from .workspace import DOC_ROLES
        d=payload(data,('entity','entity_id','role','scope','expected','mode'),('entity','entity_id','role','scope','expected'))
        if d['entity'] not in ('organization','signatory') or d['scope'] not in ('object','project') or d['role'] not in DOC_ROLES:
            raise ValueError('Неверное назначение')
        oid=d['entity_id'] if d['entity']=='organization' else row(c,'signatories',d['entity_id'])['org_id']
        if not c.execute('''SELECT 1 FROM object_participants WHERE object_id=? AND org_id=?
            UNION SELECT 1 FROM organization_assignments WHERE (object_id=? OR project_id=?) AND org_id=?''',
            (project['object_id'],oid,project['object_id'],project_id,oid)).fetchone(): raise ValueError('Участник не принадлежит объекту')
        table,col=('organization_assignments','org_id') if d['entity']=='organization' else ('signatory_assignments','signatory_id')
        scope,scope_id=('object_id',project['object_id']) if d['scope']=='object' else ('project_id',project_id)
        old=[r[0] for r in c.execute(f'SELECT {col} FROM {table} WHERE {scope}=? AND role_key=? ORDER BY id',(scope_id,d['role']))]
        expected={'entity_ids':old} if 'entity_ids' in d['expected'] else {'entity_id':old[0] if len(old)==1 else None}
        if d['expected']!=expected or (len(old)>1 and 'entity_ids' not in d['expected']): raise ValueError('Назначение уже изменено')
        if d.get('mode') not in (None,'add','replace','remove'): raise ValueError('Неизвестный способ назначения')
        if d.get('mode')=='remove':
            c.execute(f'DELETE FROM {table} WHERE {scope}=? AND role_key=? AND {col}=?',(scope_id,d['role'],d['entity_id']))
        else:
            assign(c,entity=d['entity'],entity_id=d['entity_id'],role_key=d['role'],multiple=d['entity']=='signatory' and d.get('mode')=='add',**{scope:scope_id})
        log_event(c,'manual-assign',entity=table,after=d)
        return {'assigned':True}
    if action=='supply-add': return add_supply(c,project_id,data)
    if action=='supply-set': return set_supply(c,project_id,data)
    if action=='allocate': return allocate(c,project_id,data)
    if action=='period-set': return period(c,project_id,data)
    if action=='sources-review': return refresh_sources(c,project_id,data)
    if action=='journal-add': return journal_add(c,project_id,data)
    if action=='entry-save':
        from .workspace import save_entry
        return save_entry(c,project_id,data)
    if action=='resource-add':
        from .resources import add_resource
        return {'id':add_resource(c,project_id=project_id,**data)}
    if action=='scheme-add':
        from .resources import add_scheme
        return {'id':add_scheme(c,project_id=project_id,**data)}
    if action=='unit-add':
        d=payload(data,('name','code','genplan_num'),('name',));d['name']=required_text(d['name'],'наименование части объекта')
        return insert(c,'object_units',{'object_id':project['object_id'],**d})
    if action=='designer-add':
        from .participants import add_organization
        name=required_text(data.get('name'),'разработчик')
        oid=add_organization(c,full_name=name)
        c.execute("INSERT INTO object_participants(object_id,org_id,role_key) VALUES(?,?,'designer')",(project['object_id'],oid))
        update_record(c,entity='projects',record_id=project_id,changes={'designer_org_id':oid},expected={'designer_org_id':data.get('expected_designer_org_id')})
        return {'id':oid}
    if action=='update':
        entity=data['entity'];rid=data['id']
        if entity in ('resources','schemes','acts'): same_project(c,entity,rid,project_id)
        elif entity=='projects' and rid==project_id: pass
        elif entity=='objects' and rid==project['object_id']: pass
        elif entity=='attachments':
            if not c.execute('SELECT 1 FROM project_attachments WHERE project_id=? AND attachment_id=?',(project_id,rid)).fetchone(): raise ValueError('Оригинал не связан с разделом')
        else: raise ValueError('Сущность или область изменения недоступна')
        if not isinstance(data.get('expected'),dict) or not data['expected']: raise ValueError('Нужны ожидаемые значения')
        return update_record(c,entity=entity,record_id=rid,changes=data['changes'],expected=data['expected'])
    if action=='form-connect':
        from .form_catalog import connect_form
        return connect_form(c, data.get('code'))
    from . import workflow as w
    if action in ('requirement-add','delivery-add','fact-add','quality-review-add'):
        return {'requirement-add':w.add_requirement,'delivery-add':w.add_delivery,'fact-add':w.add_fact,'quality-review-add':w.add_quality_review}[action](c,project_id,data)
    if action in ('requirement-set','delivery-set','fact-set','remark-resolve'):
        table,fn={'requirement-set':('package_requirements',w.set_requirement),'delivery-set':('deliveries',w.set_delivery),'fact-set':('work_facts',w.set_fact_status),'remark-resolve':('delivery_remarks',w.resolve_remark)}[action]
        if table=='delivery_remarks':
            r=row(c,table,data['id']);same_project(c,'deliveries',r['delivery_id'],project_id)
        else: same_project(c,table,data['id'],project_id)
        return fn(c,data['id'],data['changes'],data['expected'])
    if action=='remark-add':
        same_project(c,'deliveries',data['delivery_id'],project_id)
        return w.add_remark(c,data['delivery_id'],data['data'])
    if action=='act-entries':
        same_project(c,'acts',data['act_id'],project_id);bind_entries(c,data['act_id'],data['entry_ids']);return {'act_id':data['act_id']}
    if action=='act-composition':
        same_project(c,'acts',data['act_id'],project_id)
        before={'resources':[r[0] for r in c.execute('SELECT resource_id FROM act_resources WHERE act_id=? ORDER BY ordinal',(data['act_id'],))],
                'schemes':[r[0] for r in c.execute('SELECT scheme_id FROM act_schemes WHERE act_id=? ORDER BY ordinal',(data['act_id'],))]}
        if data.get('expected')!=before: raise ValueError('Состав акта уже изменён')
        from .acts import set_resources,set_schemes
        for rid in data['resources']: same_project(c,'resources',rid,project_id)
        for sid in data['schemes']: same_project(c,'schemes',sid,project_id)
        set_resources(c,data['act_id'],data['resources']);set_schemes(c,data['act_id'],data['schemes'])
        log_event(c,'manual-composition',entity='acts',entity_id=data['act_id'],before=before,after=data)
        return {'act_id':data['act_id']}
    raise ValueError('Неизвестная ручная операция')
