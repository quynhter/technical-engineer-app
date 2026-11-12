"""Ресурсы работ и остатки по ранее зарегистрированным поставкам."""
import math
import json

from .changes import log_event
from .db import required_text
from .resources import quantity


def supply_used(c, supply_id, *, exclude_entry=None, exclude_act=None):
    work = math.fsum(r[0] for r in c.execute('SELECT quantity FROM work_material_allocations WHERE supply_id=? AND entry_id!=?', (supply_id, exclude_entry or -1)))
    # Прежние самостоятельные выделения в акты занимают остаток. Новые работы
    # передают свои факты в акт, не создавая вторую строку act_materials.
    acts = math.fsum(r[0] for r in c.execute('''SELECT m.quantity FROM act_materials m JOIN acts a ON a.id=m.act_id
        WHERE m.supply_id=? AND m.act_id!=? AND a.is_active=1''', (supply_id, exclude_act or -1)))
    return work, acts


def balances(c, project_id):
    result=[]
    controls={}
    for entry in c.execute("SELECT resource_id,work_fields FROM workspace_entries WHERE project_id=? AND kind='incoming' ORDER BY id",(project_id,)):
        fields=json.loads(entry['work_fields'] or '{}')
        if fields.get('supply_id'):
            controls[(entry['resource_id'],fields['supply_id'])]=fields.get('incoming_result','pending')
    for r in c.execute('SELECT * FROM resources WHERE project_id=? ORDER BY id', (project_id,)):
        supplies=c.execute("SELECT * FROM supplies WHERE project_id=? AND resource_id=? AND status='accepted'", (project_id,r['id'])).fetchall()
        valid=[s for s in supplies if s['unit']==r['unit']]
        unknown=any(s['quantity'] is None or s['unit']!=r['unit'] for s in supplies)
        received=None if unknown else math.fsum(s['quantity'] for s in valid)
        used=math.fsum(x[0] for x in c.execute('SELECT quantity FROM work_materials WHERE resource_id=?', (r['id'],)))
        reserved=math.fsum(supply_used(c,s['id'])[1] for s in valid)
        delivered=list(c.execute("SELECT * FROM supplies WHERE project_id=? AND resource_id=? AND status!='void'",(project_id,r['id'])))
        controlled=[s for s in delivered if s['status']=='accepted' and controls.get((r['id'],s['id']))=='accepted']
        def total(items):
            return None if any(s['quantity'] is None or s['unit']!=r['unit'] for s in items) else math.fsum(s['quantity'] for s in items)
        rejected=[s for s in delivered if s['status']=='rejected' or controls.get((r['id'],s['id']))=='rejected']
        result.append({**dict(r),'delivered':total(delivered),'control_accepted':total(controlled),
                       'awaiting_control':len(delivered)-len(controlled)-len(rejected),'control_rejected':len(rejected),
                       'received':received,'consumed':used,'reserved':reserved,
                       'remaining':None if received is None else received-used-reserved,
                       'unknown_receipts':unknown})
    return result


def save_materials(c, entry, materials, previous_entry=None):
    """Внешняя транзакция save_entry атомарно сохраняет запись, ресурсы и факт."""
    if not isinstance(materials,list): raise ValueError('Использованные ресурсы должны быть списком')
    if entry['kind']!='work' and materials: raise ValueError('Ресурсы указываются только в записи работы')
    old={r['resource_id']:dict(r) for r in c.execute('SELECT * FROM work_materials WHERE entry_id=?',(entry['id'],))}
    wanted={}
    for item in materials:
        if not isinstance(item,dict) or set(item)-{'resource_id','quantity'}: raise ValueError('Некорректная строка использованных ресурсов')
        rid=item.get('resource_id'); amount=quantity(item.get('quantity'),'Использовано')
        if type(rid) is not int or rid in wanted or amount is None or amount<=0: raise ValueError('Выберите уникальный ресурс и положительное количество')
        r=c.execute('SELECT * FROM resources WHERE id=? AND project_id=?',(rid,entry['project_id'])).fetchone()
        if not r: raise ValueError('Ресурс относится к другому разделу')
        wanted[rid]=(dict(r),amount)
    if wanted:
        required_text(entry.get('details'),'Место работ для факта монтажа')
        required_text(entry.get('responsible'),'Ответственный исполнитель')
        required_text(entry.get('entry_date'),'Дата выполнения работ')
    from .workflow import add_fact,set_fact_status
    for rid in set(old)|set(wanted):
        previous=old.get(rid); target=wanted.get(rid)
        if previous and target and previous['quantity']==target[1] and previous['unit']==target[0]['unit']:
            fact=c.execute('SELECT * FROM work_facts WHERE id=?',(previous['fact_id'],)).fetchone()
            if fact['status']=='confirmed' and (previous_entry or {}).get('responsible_id')==entry.get('responsible_id') and all(fact[k]==entry[v] for k,v in [('location','details'),('work_description','title'),('end_date','entry_date')]):
                continue
        if previous:
            if c.execute('SELECT 1 FROM act_facts WHERE fact_id=?',(previous['fact_id'],)).fetchone():
                raise ValueError('Факт монтажа уже включён в акт. Сначала измените состав фактов акта')
            fact=c.execute('SELECT status FROM work_facts WHERE id=?',(previous['fact_id'],)).fetchone()
            c.execute('DELETE FROM work_materials WHERE entry_id=? AND resource_id=?',(entry['id'],rid))
            if fact['status']!='void': set_fact_status(c,previous['fact_id'],{'status':'void','reason':f"Изменена запись работы № {entry['id']}"},{'status':fact['status']})
        if not target: continue
        r,amount=target
        fact=add_fact(c,entry['project_id'],dict(resource_id=rid,source_key=f"work:{entry['id']}:revision:{entry['revision']}:resource:{rid}",
            quantity=amount,unit=r['unit'],location=entry['details'],work_description=entry['title'],work_entry_id=entry['id'],
            start_date=entry['entry_date'],end_date=entry['entry_date'],
            source=f"Использованные ресурсы записи работы № {entry['id']}",reported_by=entry['responsible'],status='confirmed'))
        c.execute('INSERT INTO work_materials VALUES(?,?,?,?,?)',(entry['id'],rid,amount,r['unit'],fact['id']))
    log_event(c,'work-materials',entity='workspace_entries',entity_id=entry['id'],before=list(old.values()),after=materials)


def work_materials(c,project_id):
    return [dict(r) for r in c.execute('''SELECT m.* FROM work_materials m JOIN workspace_entries e ON e.id=m.entry_id WHERE e.project_id=? ORDER BY e.id,m.resource_id''',(project_id,))]


def material_issues(c,project_id):
    result=[]
    for a in c.execute('''SELECT w.*,s.status,s.unit AS supply_unit,s.quantity AS supply_quantity,r.unit AS resource_unit
        FROM work_material_allocations w JOIN workspace_entries e ON e.id=w.entry_id
        JOIN supplies s ON s.id=w.supply_id JOIN resources r ON r.id=w.resource_id WHERE e.project_id=?''',(project_id,)):
        if a['status']!='accepted' or a['supply_unit']!=a['resource_unit'] or a['supply_quantity'] is None or math.fsum(supply_used(c,a['supply_id']))>a['supply_quantity']+1e-9:
            result.append({'code':'work_supply_invalid','entry_id':a['entry_id'],'resource_id':a['resource_id'],'supply_id':a['supply_id']})
    return result
