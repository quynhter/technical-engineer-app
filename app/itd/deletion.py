"""Предпросмотр и атомарное удаление по FK и живым ссылкам внутри JSON.

Обязательные дочерние ссылки удаляют строку, необязательные очищаются.
Архивные файлы и снимки выпущенных документов не переписываются.
"""
import hashlib
import json
from collections import defaultdict, deque

from .db import atomic_operation
from .changes import log_event

LABELS = {
    'objects':'Объекты', 'projects':'Разделы', 'resources':'Ресурсы', 'schemes':'Схемы',
    'organizations':'Организации', 'signatories':'Представители', 'workspace_entries':'Записи журналов',
    'work_facts':'Факты монтажа', 'supplies':'Поставки', 'quality_reviews':'Проверки качества',
    'acts':'Документы', 'releases':'Выпуски', 'attachments':'Исходные файлы',
    'special_journals':'Специальные журналы', 'object_units':'Части объекта',
    'participant_periods':'Периоды участия', 'package_requirements':'Требования к комплекту',
    'deliveries':'Передачи документов', 'delivery_remarks':'Замечания', 'delivery_events':'События передачи',
    'document_versions':'Версии документов', 'generated_documents':'Сведения о созданных файлах',
    'act_resources':'Ресурсы документов', 'act_schemes':'Схемы документов', 'act_facts':'Факты документов',
    'act_entry_sources':'Работы документов', 'act_materials':'Поставки документов',
    'work_materials':'Расход ресурсов', 'work_material_allocations':'Распределение поставок',
    'act_signatories':'Подписанты документов', 'act_organizations':'Организации документов',
    'act_execution_status':'Состояние подписания', 'organization_assignments':'Роли организаций',
    'signatory_assignments':'Роли представителей', 'object_participants':'Участники объекта',
    'resource_attachments':'Файлы ресурсов', 'resource_sources':'Источники ресурсов',
    'scheme_attachments':'Файлы схем', 'act_attachments':'Файлы документов',
    'project_attachments':'Файлы разделов', 'object_attachments':'Файлы объекта',
    'project_files':'Рабочие копии файлов', 'release_operations':'Операции с выпусками',
    'resource_imports':'Импорты ресурсов', 'resource_import_rows':'Строки импорта',
    'act_journals':'Подключения журналов', 'final_reviews':'Проверки документов',
    'specification_pending':'Вопросы по спецификации', 'document_counters':'Нумерация документов',
    'agent_state':'Контекст раздела',
}
ROOTS = {'objects','projects','resources','schemes','organizations','signatories','workspace_entries',
         'work_facts','supplies','quality_reviews','acts','releases','attachments','special_journals',
         'object_units','participant_periods','package_requirements','deliveries','delivery_remarks',
         'delivery_events','document_versions','organization_assignments','signatory_assignments'}
JSON_LINKS = {'org_id':'organizations','person_id':'signatories','entry_id':'workspace_entries',
              'supply_id':'supplies','quality_review_id':'quality_reviews'}

FIELD_LABELS = {'object_id':'Объект','project_id':'Раздел','resource_id':'Ресурс','scheme_id':'Схема',
    'act_id':'Документ','attachment_id':'Исходный файл','org_id':'Организация','person_id':'Представитель',
    'signatory_id':'Представитель','entry_id':'Запись журнала','work_entry_id':'Работа в ОЖР',
    'fact_id':'Факт монтажа','supply_id':'Поставка','release_id':'Выпуск','resolution_release_id':'Выпуск исправления',
    'generated_id':'Созданный файл','delivery_id':'Передача','quality_review_id':'Проверка качества',
    'keeper_id':'Ответственный за ведение','recipient_id':'Принявший журнал','responsible_id':'Ответственный',
    'designer_org_id':'Разработчик раздела','unit_id':'Часть объекта','order_attachment_id':'Основание полномочий'}


def _scope_label(c,row):
    if row.get('project_id'):
        p=c.execute('SELECT p.section_code,o.name FROM projects p JOIN objects o ON o.id=p.object_id WHERE p.id=?',(row['project_id'],)).fetchone()
        if p:return f'Объект «{p["name"]}». Раздел «{p["section_code"]}»'
    if row.get('object_id'):
        o=c.execute('SELECT name FROM objects WHERE id=?',(row['object_id'],)).fetchone()
        if o:return f'Объект «{o[0]}»'
    return ''


def quote(value):
    return '"'+value.replace('"','""')+'"'


def _scope(c,pid,table,identity):
    if not isinstance(table,str) or table not in ROOTS or type(identity) is not int or identity<=0:
        raise ValueError('Недопустимая запись для удаления')
    project=c.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
    if not project:raise ValueError('Раздел не найден')
    row=c.execute(f'SELECT rowid AS __rowid,* FROM {quote(table)} WHERE id=?',(identity,)).fetchone()
    if not row:raise ValueError('Запись уже удалена или не найдена')
    row=dict(row);oid=project['object_id']
    if table=='objects':valid=identity==oid
    elif table=='projects':valid=row['object_id']==oid
    elif 'project_id' in row and row['project_id'] is not None:
        valid=bool(c.execute('SELECT 1 FROM projects WHERE id=? AND object_id=?',(row['project_id'],oid)).fetchone())
    elif 'object_id' in row:valid=row['object_id']==oid
    elif table in ('organizations','signatories'):
        from .ojr import directory
        valid=identity in {r['id'] for r in directory(c,pid)['organizations' if table=='organizations' else 'people']}
    elif table=='attachments':
        valid=bool(c.execute('''SELECT 1 FROM project_attachments pa JOIN projects p ON p.id=pa.project_id WHERE pa.attachment_id=? AND p.object_id=?
            UNION SELECT 1 FROM object_attachments WHERE attachment_id=? AND object_id=?
            UNION SELECT 1 FROM resource_attachments ra JOIN resources r ON r.id=ra.resource_id JOIN projects p ON p.id=r.project_id WHERE ra.attachment_id=? AND p.object_id=?
            UNION SELECT 1 FROM act_attachments aa JOIN acts a ON a.id=aa.act_id JOIN projects p ON p.id=a.project_id WHERE aa.attachment_id=? AND p.object_id=?
            UNION SELECT 1 FROM scheme_attachments sa JOIN schemes s ON s.id=sa.scheme_id JOIN projects p ON p.id=s.project_id WHERE sa.attachment_id=? AND p.object_id=?''', (identity,oid)*5).fetchone())
    else:
        parent={'quality_reviews':('resources','resource_id'), 'document_versions':('acts','act_id'),
                'delivery_events':('deliveries','delivery_id'),'delivery_remarks':('deliveries','delivery_id')}.get(table)
        if not parent:raise ValueError('Не удалось определить раздел записи')
        _scope(c,pid,parent[0],row[parent[1]]);valid=True
    if not valid:raise ValueError('Запись не относится к выбранному объекту')
    return row


def _caption(table,row):
    name=next((str(row[k]) for k in ('act_num','name','full_name','fio','title','work_description','description','role_key','num','source_key') if row.get(k)),None)
    identity=row.get('id',row['__rowid'])
    return f'№ {identity}'+(f' «{name}»' if name else '')


def _build(c,pid,table,identity):
    root=_scope(c,pid,table,identity)
    tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    columns={t:{r['name']:dict(r) for r in c.execute(f'PRAGMA table_info({quote(t)})')} for t in tables}
    incoming=defaultdict(list)
    for child in tables:
        groups=defaultdict(list)
        for fk in c.execute(f'PRAGMA foreign_key_list({quote(child)})'):groups[fk['id']].append(dict(fk))
        for group in groups.values():
            group.sort(key=lambda f:f['seq'])
            incoming[group[0]['table']].append((child,group))
    json_incoming=defaultdict(list)
    for entry in c.execute('SELECT rowid AS __rowid,* FROM workspace_entries'):
        entry=dict(entry);fields=json.loads(entry['work_fields'] or '{}')
        for col,parent in JSON_LINKS.items():
            if type(fields.get(col)) is int:json_incoming[(parent,fields[col])].append(entry)
    deleted={};updated={};reasons={};queue=deque()

    def remove(t,row,reason):
        key=(t,row['__rowid'])
        if key not in deleted:
            deleted[key]=row;reasons[key]=reason;queue.append(key)
        updated.pop(key,None)

    def change(t,row,values,reason):
        key=(t,row['__rowid'])
        if key in deleted:return
        if key not in updated:updated[key]={'before':row,'values':{},'reasons':[]}
        updated[key]['values'].update(values)
        if reason not in updated[key]['reasons']:updated[key]['reasons'].append(reason)

    remove(table,root,'Выбранная запись')
    while queue:
        parent_key=queue.popleft();parent,row=parent_key[0],deleted[parent_key]
        for child,group in incoming[parent]:
            targets=[f['to'] for f in group]
            if any(v is None for v in targets):
                targets=[v['name'] for v in sorted(columns[parent].values(),key=lambda v:v['pk']) if v['pk']]
            where=' AND '.join(quote(f['from'])+'=?' for f in group)
            values=[row[col] for col in targets]
            children=c.execute(f'SELECT rowid AS __rowid,* FROM {quote(child)} WHERE {where}',values).fetchall()
            fields=[f['from'] for f in group]
            mandatory=any(columns[child][col]['notnull'] or columns[child][col]['pk'] for col in fields)
            # Назначение допускает ровно один уровень. Потеря уровня удаляет назначение.
            if child in ('organization_assignments','signatory_assignments') and set(fields)&{'project_id','object_id'}:mandatory=True
            reason=f'{LABELS.get(parent,parent)} {_caption(parent,row)}. '+', '.join(FIELD_LABELS.get(col,'Связь') for col in fields)
            for item in children:
                item=dict(item)
                if mandatory:remove(child,item,reason)
                else:change(child,item,{col:None for col in fields},reason)
        # Живые связи журналов хранятся в work_fields, а не в FK.
        for item in json_incoming.get((parent,row.get('id')),[]):
            item=dict(item);key=('workspace_entries',item['__rowid'])
            current=updated.get(key,{}).get('values',{}).get('work_fields',item['work_fields'])
            fields=json.loads(current or '{}');matches=[k for k,t in JSON_LINKS.items() if t==parent and fields.get(k)==row.get('id')]
            if not matches:continue
            reason=f'{LABELS.get(parent,parent)} {_caption(parent,row)}. '+', '.join(FIELD_LABELS.get(col,'Связь') for col in matches)
            if fields.get('journal_section')=='1' and set(matches)&{'person_id','org_id'}:
                remove('workspace_entries',item,reason)
            else:
                for col in matches:fields[col]=None
                change('workspace_entries',item,{'work_fields':json.dumps(fields,ensure_ascii=False)},reason)
        if parent in ('organizations','signatories'):
            # Явные ссылки на идентификаторы в полях бланка.
            prefix='Organisation' if parent=='organizations' else 'Representative'
            def clean_fields(fields):
                result=[];required=False;changed=False
                for f in fields:
                    f=dict(f)
                    if (f.get('source') or '').startswith(f'{prefix}.{row["id"]}.'):
                        changed=True;required=required or bool(f.get('required') and f.get('state') not in ('hidden','not_applicable'))
                        for k in ('source','role','presentation','template'):f.pop(k,None)
                        f.update(kind='literal',value=None)
                    for col in ('fields','columns'):
                        if isinstance(f.get(col),list):
                            f[col],req,diff=clean_fields(f[col]);required|=req;changed|=diff
                    result.append(f)
                return result,required,changed
            for item in c.execute('SELECT rowid AS __rowid,* FROM acts'):
                item=dict(item);key=('acts',item['__rowid'])
                original=updated.get(key,{}).get('values',{}).get('fields',item['fields'])
                from .fields import merge_fields
                defaults=c.execute('SELECT fields FROM document_types WHERE code=?',(item['act_type'],)).fetchone()
                effective=merge_fields(json.loads(defaults['fields']),json.loads(original or '[]'))
                fields,required,diff=clean_fields(effective)
                if diff:
                    reason=f'{LABELS[parent]} {_caption(parent,row)}. Поля документа'
                    if required:remove('acts',item,reason)
                    else:change('acts',item,{'fields':json.dumps(fields,ensure_ascii=False)},reason)
            for item in c.execute('SELECT rowid AS __rowid,* FROM document_versions WHERE release_id IS NULL AND attachment_id IS NULL'):
                item=dict(item);key=('document_versions',item['__rowid']);values=updated.get(key,{}).get('values',{})
                card=json.loads(values.get('card_json',item['card_json']));signers=json.loads(values.get('signers_json',item['signers_json']))
                before=json.dumps([card,signers],sort_keys=True)
                if parent=='organizations':card['organizations']={k:v for k,v in card.get('organizations',{}).items() if v!=row['id']}
                else:signers=[s for s in signers if s.get('person_id')!=row['id']]
                fields,required,diff=clean_fields(card.get('fields',[]))
                if diff:card['fields']=fields
                if required:remove('document_versions',item,'Обязательное поле версии')
                elif before!=json.dumps([card,signers],sort_keys=True):
                    change('document_versions',item,{'card_json':json.dumps(card,ensure_ascii=False),'signers_json':json.dumps(signers,ensure_ascii=False)},'Участник удалён. Необязательная ссылка версии очищается')
    # Удаляем ссылки из текущей карточки версии, когда они очищены в акте.
    for (t,rid),change_item in list(updated.items()):
        if t=='acts' and 'fields' in change_item['values']:
            for item in c.execute('SELECT rowid AS __rowid,* FROM document_versions WHERE act_id=? AND release_id IS NULL AND attachment_id IS NULL',(rid,)):
                item=dict(item);key=('document_versions',item['__rowid']);card=json.loads(updated.get(key,{}).get('values',{}).get('card_json',item['card_json']))
                card['fields']=json.loads(change_item['values']['fields'])
                change('document_versions',item,{'card_json':json.dumps(card,ensure_ascii=False)},'Обновлены ссылки в полях документа')
    # Ревизии защищают открытые формы от перезаписи очищенных ссылок.
    for (t,_),item in updated.items():
        if 'revision' in columns[t]:item['values']['revision']=item['before']['revision']+1
    return deleted,updated,reasons


def preview(c,pid,table,identity):
    deleted,updated,reasons=_build(c,pid,table,identity)
    database=c.execute('PRAGMA database_list').fetchone()[2]
    encode=lambda value:json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    signature=encode([database,pid,table,identity,[[t,r,row] for (t,r),row in sorted(deleted.items())],
                      [[t,r,item] for (t,r),item in sorted(updated.items())]])
    token=hashlib.sha256(signature.encode()).hexdigest()
    items=[]
    for (t,r),row in sorted(deleted.items()):
        items.append({'action':'delete','table':t,'entity':LABELS.get(t,t),'id':row.get('id',r),
                      'name':_caption(t,row),'reason':reasons[(t,r)],'project_id':row.get('project_id'),'scope':_scope_label(c,row)})
    for (t,r),item in sorted(updated.items()):
        items.append({'action':'clear','table':t,'entity':LABELS.get(t,t),'id':item['before'].get('id',r),
                      'name':_caption(t,item['before']),'fields':list(item['values']),
                      'reason':'. '.join(item['reasons']),'project_id':item['before'].get('project_id'),'scope':_scope_label(c,item['before'])})
    return {'entity':table,'id':identity,'token':token,'items':items,
            'delete_count':len(deleted),'clear_count':len(updated),
            'archive_note':'Архивные файлы и сохранённые снимки выпущенных документов не изменяются.'}


@atomic_operation
def apply(c,pid,table,identity,token):
    plan=preview(c,pid,table,identity)
    if not isinstance(token,str) or token!=plan['token']:
        raise ValueError('Связи или данные изменились. Откройте предупреждение заново и проверьте последствия')
    deleted,updated,_=_build(c,pid,table,identity)
    # Все промежуточные состояния остаются внутри одной транзакции.
    c.execute('PRAGMA defer_foreign_keys=ON')
    for (t,r),item in updated.items():
        values=item['values']
        c.execute(f'UPDATE {quote(t)} SET '+','.join(quote(k)+'=?' for k in values)+' WHERE rowid=?',(*values.values(),r))
    for t,r in deleted:c.execute(f'DELETE FROM {quote(t)} WHERE rowid=?',(r,))
    if c.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Нарушена связь данных. Удаление отменено')
    log_event(c,'records-delete',entity=table,entity_id=identity,
              after={'deleted':plan['delete_count'],'cleared':plan['clear_count'],
                     'records':[{'table':i['table'],'id':i['id'],'action':i['action']} for i in plan['items']]})
    return {'deleted':plan['delete_count'],'cleared':plan['clear_count']}
