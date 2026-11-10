"""Атомарное сохранение карточки ресурса, поступлений и самостоятельных фактов."""
import math

from .changes import update_record, log_event
from .db import atomic_operation, required_text
from .workflow import payload, same_project, expect, add_fact, set_fact_status


@atomic_operation
def save_card(c, pid, data):
    d = payload(data, ('id','changes','expected','supplies','facts'), ('id','changes','expected','supplies','facts'))
    resource = same_project(c, 'resources', d['id'], pid)
    expect(resource, d['expected'])
    if not isinstance(d['supplies'],list) or not isinstance(d['facts'],list):
        raise ValueError('Поступления и факты должны быть списками')
    if d['changes']:
        update_record(c,entity='resources',record_id=resource['id'],changes=d['changes'],expected=d['expected'])
    for table,items in (('supplies',d['supplies']),('work_facts',d['facts'])):
        ids = [item.get('id') for item in items if isinstance(item,dict) and item.get('id')]
        if len(ids) != len(set(ids)):
            raise ValueError('Одна запись указана несколько раз')
        for item in items:
            packet = payload(item, ('id','values','expected','reason','source_key'), ('values',))
            if not isinstance(packet['values'],dict):
                raise ValueError('Реквизиты строки должны быть объектом')
            # Ресурс и раздел задаются карточкой, а не редактируемой строкой.
            if set(packet['values']) & {'resource_id','project_id','source_key','id'}:
                raise ValueError('Нельзя перенести строку в другой ресурс или раздел')
            if table == 'supplies':
                save_supply(c,pid,resource['id'],packet)
            else:
                save_fact(c,pid,resource['id'],packet)
    return {'resource_id': resource['id'], 'saved':True}


def save_supply(c,pid,rid,packet):
    from .manual import add_supply, supply_values
    from .inventory import supply_used
    if not packet.get('id'):
        return add_supply(c,pid,dict(packet['values'],resource_id=rid,source_key=packet.get('source_key')))
    before = same_project(c,'supplies',packet['id'],pid)
    if before['resource_id'] != rid:
        raise ValueError('Поставка относится к другому ресурсу')
    expect(before,packet.get('expected'))
    if not isinstance(packet.get('expected'),dict) or 'revision' not in packet['expected']:
        raise ValueError('Нужна ожидаемая версия поставки')
    if before['status'] == 'void':
        raise ValueError('Отозванную поставку нельзя редактировать')
    reason = required_text(packet.get('reason'),'Основание изменения поставки')
    target = packet['values'].get('status')
    values = supply_values(c,pid,dict(packet['values'],resource_id=rid,source_key=before['source_key'],
                                     status=before['status'] if target=='void' else target))
    if target == 'void':
        values['status']='void'
        if not values.get('note'):
            values['note']=reason
    used = math.fsum(supply_used(c,before['id']))
    if used and (values['unit'] != before['unit'] or values['quantity'] is None or values['quantity']+1e-9 < used):
        raise ValueError('Количество поставки не может быть меньше уже использованного; единица должна сохраняться')
    editable = {k:v for k,v in values.items() if k not in ('project_id','resource_id','source_key')}
    c.execute('UPDATE supplies SET '+','.join(k+'=?' for k in editable)+',revision=revision+1 WHERE id=?',
              (*editable.values(),before['id']))
    after = dict(c.execute('SELECT * FROM supplies WHERE id=?',(before['id'],)).fetchone())
    log_event(c,'supply-edit',entity='supplies',entity_id=before['id'],before=before,after={'record':after,'reason':reason})
    return after


def save_fact(c,pid,rid,packet):
    if not packet.get('id'):
        return add_fact(c,pid,dict(packet['values'],resource_id=rid,source_key=packet.get('source_key')))
    before = same_project(c,'work_facts',packet['id'],pid)
    if before['resource_id'] != rid:
        raise ValueError('Факт относится к другому ресурсу')
    expect(before,packet.get('expected'))
    if packet.get('expected') != before:
        raise ValueError('Нужны все исходные сведения факта; обновите карточку')
    if c.execute('SELECT 1 FROM work_materials WHERE fact_id=?',(before['id'],)).fetchone():
        raise ValueError('Факт создан из работы: откройте исходную запись работы')
    reason = required_text(packet.get('reason'),'Основание изменения факта')
    fields = ('location','work_description','source','reported_by','quantity','unit','start_date','end_date','attachment_id')
    values = payload(packet['values'], (*fields,'status'), ('status',))
    if values['status']=='void' or all(values.get(k)==before.get(k) for k in fields):
        return set_fact_status(c,before['id'],{'status':values['status'],'reason':reason},{'status':before['status']})
    if before['status']=='void':
        raise ValueError('Отозванный факт нельзя редактировать')
    if c.execute('SELECT 1 FROM act_facts WHERE fact_id=?',(before['id'],)).fetchone():
        raise ValueError('Факт включён в акт: сначала измените состав фактов акта')
    # Исходный факт сохраняется: исправление — отзыв и отдельная запись с основанием.
    corrected = add_fact(c,pid,dict(values,resource_id=rid,source_key=packet.get('source_key'),
                                    work_entry_id=before['work_entry_id']))
    set_fact_status(c,before['id'],{'status':'void','reason':reason},{'status':before['status']})
    log_event(c,'fact-correction',entity='work_facts',entity_id=before['id'],before=before,
              after={'replacement_id':corrected['id'],'reason':reason})
    return corrected
