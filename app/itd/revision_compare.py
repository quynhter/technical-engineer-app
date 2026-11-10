"""Сравнение прочитанных редакций; не импортирует и не исправляет ресурсы."""
from collections import defaultdict
from inspect import signature

from .resources import add_resource, quantity, CATEGORIES
from .workflow import row, payload


FIELDS = tuple(k for k in signature(add_resource).parameters if k not in ('connection','project_id','qty_fact'))


def index(items):
    if not isinstance(items,list):
        raise ValueError('Редакция должна быть массивом specification.json')
    result = defaultdict(list)
    uncertain = []
    keys = set()
    for item in items:
        d = payload(item, ('source_key','verified','resource','page','sheet','locator','reason'), ('source_key',))
        key = d['source_key']
        if not isinstance(key,str) or not key.strip() or key in keys:
            raise ValueError('Нужны непустые уникальные source_key внутри каждой редакции')
        keys.add(key)
        if d.get('verified') is not True:
            uncertain.append(key)
            continue
        r = payload(d.get('resource'), (*FIELDS,'qty_fact'), ('name','unit','category'))
        if r.get('qty_fact') is not None:
            raise ValueError('Спецификация не подтверждает факт монтажа')
        r.pop('qty_fact',None)
        for field in ('name','unit'):
            if not isinstance(r[field],str) or not r[field].strip(): raise ValueError('Неверное имя или единица ресурса')
        if r['category'] not in CATEGORIES: raise ValueError('Неверная категория')
        for field in ('qty_proj','unit_weight'):
            if field in r: r[field] = quantity(r[field],field)
        for field,value in r.items():
            if field == 'serial_numbers':
                if value is not None and (not isinstance(value,list) or any(not isinstance(v,str) or not v.strip() for v in value)):
                    raise ValueError('serial_numbers должен быть списком непустых строк')
            elif field not in ('qty_proj','unit_weight') and value is not None and not isinstance(value,str):
                raise ValueError(f'{field}: требуется текст или null')
        # Позиция спецификации стабильнее номера страницы/строки новой редакции.
        identity = 'position:'+r['spec_num'] if r.get('spec_num') else 'source:'+key
        result[identity].append({**d,'resource':r})
    return result,uncertain


def compare(c,project_id,old_attachment_id,new_attachment_id,old_items,new_items,*,complete=False):
    row(c,'projects',project_id)
    if old_attachment_id==new_attachment_id: raise ValueError('Редакции должны иметь разные ID оригиналов')
    for aid in (old_attachment_id,new_attachment_id):
        if row(c,'attachments',aid)['doc_type']!='rd': raise ValueError('Обе редакции должны иметь тип rd')
    old,uo=index(old_items); new,un=index(new_items)
    out={'project_id':project_id,'old_attachment_id':old_attachment_id,'new_attachment_id':new_attachment_id,
         'added':[],'changed':[],'removed_candidates':[],'unchanged':[], 'ambiguous':[],
         'unverified':{'old':uo,'new':un},'applied':False}
    for key in sorted(set(old)|set(new)):
        a=old.get(key,[]); b=new.get(key,[])
        if len(a)>1 or len(b)>1:
            out['ambiguous'].append({'identity':key,'old_keys':[i['source_key'] for i in a],'new_keys':[i['source_key'] for i in b]})
            continue
        item={'identity':key,'old_source_key':a[0]['source_key'] if a else None,'new_source_key':b[0]['source_key'] if b else None}
        resource_ids=[]
        if a:
            resource_ids=[r[0] for r in c.execute('SELECT resource_id FROM resource_sources WHERE project_id=? AND attachment_id=? AND source_key=?',(project_id,old_attachment_id,a[0]['source_key']))]
        item['resource_ids']=resource_ids
        item['act_ids']=sorted({r[0] for rid in resource_ids for r in c.execute('SELECT act_id FROM act_resources WHERE resource_id=?',(rid,))})
        item['scheme_ids']=sorted({r[0] for aid in item['act_ids'] for r in c.execute('SELECT scheme_id FROM act_schemes WHERE act_id=?',(aid,))})
        item['release_ids']=sorted({r[0] for rid in resource_ids for r in c.execute("SELECT id FROM releases WHERE project_id=? AND (kind='xlsx' OR act_id IN (SELECT act_id FROM act_resources WHERE resource_id=?))",(project_id,rid))})
        if not a:
            out['added'].append({**item,'new':b[0]})
        elif not b:
            out['removed_candidates'].append({**item,'old':a[0],'reliable':complete and not un})
        else:
            delta={f:{'old':a[0]['resource'].get(f),'new':b[0]['resource'].get(f)} for f in FIELDS if a[0]['resource'].get(f)!=b[0]['resource'].get(f)}
            if delta: out['changed'].append({**item,'changes':delta})
            else: out['unchanged'].append(item)
    out['limitations']=[
        'Сравниваются переданные JSON двух оригиналов, не текущие исправленные пользователем строки БД.',
        'removed_candidates — только кандидаты: исключение требует полного чтения новой редакции и согласования.',
        'Дубли позиций не сопоставляются автоматически; без spec_num используется source_key, который мог измениться.',
        'Влияние на схемы показано через связи актов; содержание чертежей и полнота связей не проверяются.'
    ]
    return out
