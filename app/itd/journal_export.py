"""Печатные журналы по сохранённым данным объекта и раздела."""
from .journals import journal_data

FORMS = {'ojr':('ОЖР','Общий журнал работ'),
         'incoming':('СП_48_И','Журнал входного контроля'),
         'cable':('И_1_13_07_18','Журнал прокладки кабелей')}


def ojr_roots(connection, project_id):
    journal = journal_data(connection,project_id)
    roots = {'section'+key:[{**row,**row.get('resolved_fields',{})} for row in records]
                    for key,records in journal['sections'].items()}
    from .workspace import DOC_ROLES, ROLES
    roots.update(
        work_start=journal['construction_dates']['start'],work_end=journal['construction_dates']['end'],
        assignments=[{'role':DOC_ROLES.get(item['role_key'],item['role_key']),
                      'org':(item.get('organization') or {}).get('full_name',''),
                      'person':(item.get('person') or {}).get('fio',''),
                      'basis':(item.get('person') or {}).get('order_doc','')}
                     for item in journal['title_assignments']],
        participants=[{'org':item['full_name'],'roles':', '.join(ROLES.get(r,r) for r in item['roles']),
                       'people':', '.join(p['fio'] for p in item['representatives'] if p.get('fio'))}
                      for item in journal['participants']])
    for old in roots['section2']:
        old.setdefault('name',old.get('title'))
    for record in journal['special']:
        roots['section2'].append({**record, 'keeper':(record.get('keeper') or {}).get('fio',''),
                                        'recipient':(record.get('recipient') or {}).get('fio','')})
    return roots


def export(c, project_id, kind, templates, output):
    from .acts import find_template
    from .docx_render import render_docx
    from .fields import resolve_fields, formatted
    from .form_catalog import catalog, catalog_fields
    from .form_defaults import apply_form_defaults, document_project
    from .participants import participants_context
    from .template_objects import build_template_context, CONTEXT_KEY

    if kind not in FORMS:
        raise ValueError('Выберите журнал')
    code, name = FORMS[kind]
    item = next(form for form in catalog() if form['code']==code)
    project = c.execute('SELECT * FROM projects WHERE id=?',(project_id,)).fetchone()
    if project is None:
        raise ValueError('Раздел не найден')
    project = dict(project)
    obj = dict(c.execute('SELECT * FROM objects WHERE id=?',(project['object_id'],)).fetchone())
    roots = {'project':document_project(project,obj), 'object':obj, 'act':{}, **participants_context(c,project_id)}
    fields = apply_form_defaults(code,catalog_fields(item))
    if kind=='ojr':
        roots['ojr'] = ojr_roots(c,project_id)
    else:
        journal = journal_data(c,project_id)
        if kind=='incoming':
            entries = journal['incoming']
            rows = incoming_rows(c, entries)
            dates = [entry['entry_date'] for entry in entries if entry['entry_date']]
            values = {
                't0_r2_c1': obj.get('address'),
                't0_r4_c1': (roots['organizations'].get('builder') or {}).get('full_name'),
            }
            for keys, value in [(('t1_r0_c1','t1_r0_c3','t1_r0_c5'),min(dates,default=None)),
                                (('t1_r2_c1','t1_r2_c3','t1_r2_c5'),max(dates,default=None))]:
                for key, fmt in zip(keys,('day_2digits','month_genitive_ru','year_4digits')):
                    values[key] = formatted(value, {'format':fmt})
            for index, field in enumerate(fields):
                if field['key'] in values:
                    fields[index] = {'key':field['key'],'kind':'literal','value':values[field['key']]}
        else:
            rows = cable_rows([entry for entry in journal['sections']['3']
                               if entry['project_id']==project_id and entry['work_type']=='cable'])
        table = next(field for field in fields if field['kind']=='table')
        table.pop('source',None)
        table['value'] = rows
    context, _ = resolve_fields(fields, roots, draft=True)
    context[CONTEXT_KEY] = build_template_context(code,context,roots=roots,fields=fields)
    render_docx(find_template(templates,code),context,output,draft=True)
    return name+'.docx'


def cells(values):
    return {'c'+str(i): value for i,value in enumerate(values,1)}


def incoming_rows(c, entries):
    results = {'accepted':'Принято','rejected':'Не принято','pending':'Проверка не завершена'}
    rows = []
    for no, entry in enumerate(entries,1):
        resource, supply, fields = entry.get('resource') or {}, entry.get('supply') or {}, entry['work_fields']
        quantity = entry['quantity'] if entry['quantity'] is not None else supply.get('quantity')
        unit = entry.get('unit') or supply.get('unit') or resource.get('unit')
        attachment = c.execute('SELECT title,doc_num FROM attachments WHERE id=?',(entry['attachment_id'],)).fetchone()
        rows.append(cells([no,formatted_date(entry['entry_date']),
                           resource.get('name') or entry['title'],
                           ' '.join(str(x) for x in (quantity,unit) if x not in (None,'')),
                           supply.get('supplier') or resource.get('supplier'),
                           ' '.join(x for x in attachment if x) if attachment else '',
                           results.get(fields.get('incoming_result','pending')), '', '', '']))
    return rows


def cable_rows(entries):
    rows = []
    for entry in entries:
        fields = entry['work_fields']
        person = entry.get('responsible_person') or {}
        rows.append(cells([formatted_date(entry['entry_date']),fields.get('line_number'),
                           fields.get('mark'),entry.get('quantity'),fields.get('drum'),
                           fields.get('couplings'),fields.get('temperature'),fields.get('heating'),
                           person.get('fio') or entry.get('responsible')]))
    return rows


def formatted_date(value):
    from .fields import formatted
    return formatted(value, {'format':'date_ru'})
