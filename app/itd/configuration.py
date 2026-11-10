"""Обмен настройками вкладок; импорт готовит проверяемую карточку без записи в БД."""
from copy import deepcopy
from .workspace import snapshot, OBJECT_FIELDS, ORG_FIELDS, REP_FIELDS
from .db import DATE_FIELDS

PERMITS = ('permit_num','permit_date','permit_authority','expertise_num','expertise_date','expertise_authority')
PARTICIPANT_FLAGS = ('developer_functions','control_self','control_external','author_supervision')
PROJECT_FIELDS = ('section_code','code','name','city','gip','inv_num','form_set',*DATE_FIELDS)
SCOPES = ('object','rd','participants','permits')


def pick(record, keys):
    return {k: record.get(k) for k in keys}


def export_configuration(c, oid, scope):
    if scope not in SCOPES: raise ValueError('Неизвестная вкладка экспорта')
    state = snapshot(c, oid)
    if scope == 'rd':
        values = {'projects':[dict(id=p['id'], **pick(p,PROJECT_FIELDS)) for p in state['projects']]}
    elif scope == 'participants':
        values = {'participants':[], 'object':pick(state['object'],PARTICIPANT_FLAGS)}
        for org in state['participants']:
            row = pick(org,('id',*ORG_FIELDS,'roles','document_roles'))
            row['representatives']=[pick(p,('id',*REP_FIELDS,'document_roles')) for p in org['representatives']]
            values['participants'].append(row)
    else:
        keys = PERMITS if scope == 'permits' else [k for k in OBJECT_FIELDS if k not in (*PERMITS,*PARTICIPANT_FLAGS)]
        values = {'object':pick(state['object'],keys)}
    return dict(format='itd-configuration',version=1,scope=scope,object_id=oid,data=values)


def prepare_import(c, oid, scope, document):
    if not isinstance(document,dict) or document.get('format')!='itd-configuration' or document.get('version')!=1:
        raise ValueError('Выберите файл, созданный кнопкой «Экспорт» этой вкладки')
    if scope not in SCOPES or document.get('scope')!=scope: raise ValueError('Файл относится к другой вкладке')
    # ID и ссылки архивных приказов не переносим между объектами автоматически.
    if document.get('object_id')!=oid: raise ValueError('Конфигурация относится к другому объекту')
    current=snapshot(c,oid); candidate=deepcopy(current)
    allowed=export_configuration(c,oid,scope)['data']; incoming=document.get('data')
    if not isinstance(incoming,dict) or set(incoming)!=set(allowed): raise ValueError('Неверный состав конфигурации')
    def merge(target, source, keys):
        if not isinstance(source,dict) or set(source)-set(keys): raise ValueError('Недопустимые поля конфигурации')
        target.update(source)
    if 'object' in incoming: merge(candidate['object'],incoming['object'],allowed['object'])
    if scope=='rd':
        if not isinstance(incoming['projects'],list): raise ValueError('Ожидается список разделов')
        known={p['id']:p for p in candidate['projects']}; seen=set()
        for p in incoming['projects']:
            if not isinstance(p,dict) or p.get('id') not in known or p['id'] in seen: raise ValueError('Неизвестный или повторяющийся раздел')
            seen.add(p['id']); merge(known[p['id']],p,('id',*PROJECT_FIELDS))
            if known[p['id']]['section_code']!=next(x['section_code'] for x in current['projects'] if x['id']==p['id']):
                raise ValueError('Обозначение существующего раздела нельзя изменить импортом')
    if scope=='participants':
        if not isinstance(incoming['participants'],list): raise ValueError('Ожидается список участников')
        known={p['id']:p for p in candidate['participants']};seen=set()
        for org in incoming['participants']:
            if not isinstance(org,dict) or org.get('id') not in known or org['id'] in seen: raise ValueError('Неизвестный или повторяющийся участник')
            seen.add(org['id']); target=known[org['id']]; reps={p['id']:p for p in target['representatives']}
            merge(target,{k:v for k,v in org.items() if k!='representatives'},('id',*ORG_FIELDS,'roles','document_roles'))
            rep_seen=set()
            for rep in org.get('representatives',[]):
                if not isinstance(rep,dict) or rep.get('id') not in reps or rep['id'] in rep_seen: raise ValueError('Неизвестный или повторяющийся представитель')
                rep_seen.add(rep['id']); merge(reps[rep['id']],rep,('id',*REP_FIELDS,'document_roles'))
    changes=[]
    def diff(a,b,path=''):
        if isinstance(a,dict) and isinstance(b,dict):
            for k in b: diff(a.get(k),b[k],path+'.'+k if path else k)
        elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
            for i,(x,y) in enumerate(zip(a,b)): diff(x,y,f'{path}[{i+1}]')
        elif a!=b: changes.append({'field':path,'before':a,'after':b})
    diff(current,candidate)
    return {'state':candidate,'changes':changes}
