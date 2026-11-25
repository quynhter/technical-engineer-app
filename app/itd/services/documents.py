"""Internal domain orchestration formerly embedded in the HTTP handler."""
import base64
import json
from pathlib import Path
import tempfile
from ..workspace import save_workspace, save_entry

def mutate(c, route, data, ctx):
    if route == '/api/configuration/preview':
        from ..configuration import prepare_import
        return prepare_import(c,data.get('object_id'),data.get('scope'),data.get('document'))
    if route == '/api/save':
        return save_workspace(c, data)
    pid = data.get('project_id')
    if not c.execute('SELECT 1 FROM projects WHERE id=?', (pid,)).fetchone():
        raise ValueError('Сначала сохраните и выберите раздел РД')
    if route.startswith('/api/versions/'):
        from .. import document_versions as versions
        aid=data.get('act_id')
        if route=='/api/versions/list':
            from ..act_participants import organization_candidates
            from ..acts import find_template
            from ..field_ui import table_headers
            from ..workflow import same_project
            act = same_project(c, 'acts', aid, pid)
            try:
                template = find_template(ctx.templates, act['act_type'])
            except ValueError:
                headers = {}
            else:
                headers = table_headers(template)
            from ..document_bindings import catalog
            return {'binding_sources':catalog(c,pid,aid),'versions':versions.versions(c,pid,aid),'candidates':versions.candidates(c,pid),
                    'required_roles':versions.required_roles(c,aid),'organization_candidates':organization_candidates(c,pid),
                    'table_headers':headers}
        if route=='/api/versions/ensure': return {'versions':versions.ensure(c,pid,aid)}
        if route=='/api/versions/create': return {'versions':versions.create(c,pid,aid,data.get('expected'))}
        if route=='/api/versions/save': return {'versions':versions.save(c,pid,data)}
        if route=='/api/versions/delete': return {'versions':versions.delete(c,pid,data)}
        if route=='/api/versions/regenerate':
            return versions.regenerate(c,pid,data,ctx.templates)
        raise ValueError('Неизвестное действие с версиями')
    if route.startswith('/api/resource-import/'):
        from .. import resource_import
        operation=route.rsplit('/',1)[-1]
        if operation=='stage': return resource_import.stage(c,pid,data)
        if operation=='preview': return resource_import.inspect(c,pid,data)
        if operation=='commit': return resource_import.commit(c,pid,data,ctx.database.parent/'archive')
        raise ValueError('Неизвестная операция импорта')
    if route == '/api/ojr-title':
        from ..ojr import save_title
        return save_title(c,pid,data)
    if route == '/api/activate':
        c.execute('INSERT INTO agent_state VALUES(1,?) ON CONFLICT(id) DO UPDATE SET project_id=excluded.project_id', (pid,))
        return {'project_id': pid}
    if route.startswith('/api/templates/'):
        from ..custom_templates import template_operation
        return template_operation(c, route.rsplit('/',1)[-1], data, ctx.templates)
    if route == '/api/scheme-save':
        from ..manual import execute
        action = data['action']
        values = data['data']
        if action != 'scheme-add' and not (action == 'update' and values.get('entity') == 'schemes'):
            raise ValueError('Выберите схему')
        result = execute(c, pid, action, values)
        if data.get('file'):
            from ..archive import link_file
            attachment = mutate(c, '/api/upload', {**data['file'], 'project_id': pid, 'doc_type': 'scheme'}, ctx)
            link_file(c, attachment_id=attachment['id'], entity='scheme',
                      entity_id=result['id'] if action=='scheme-add' else values['id'])
        return result
    if route == '/api/upload':
        from ..archive import import_file, link_file
        name = data.get('name', '')
        if not name or '/' in name or '\\' in name or name in ('.', '..'):
            raise ValueError('Недопустимое имя файла')
        doc_type = data.get('doc_type', 'rd')
        with tempfile.TemporaryDirectory(prefix='itd-upload-') as folder:
            source = Path(folder) / name
            source.write_bytes(base64.b64decode(data['content'], validate=True))
            result = import_file(c, archive_root=ctx.database.parent / 'archive', source=source,
                                 doc_type=doc_type, title=data.get('title') or name)
            # Хеш-дубликат с другим типом не должен становиться иной категорией оригинала.
            stored = c.execute('SELECT * FROM attachments WHERE id=?', (result['id'],)).fetchone()
            from ..archive import file_type
            expected_type='quality' if doc_type in ('certificate','passport') else doc_type
            if file_type(stored) != expected_type:
                raise ValueError('Этот оригинал уже зарегистрирован с другим типом; уточните его назначение')
            link_file(c, attachment_id=result['id'], entity='project', entity_id=pid)
            from ..archive import archived_path
            from ..storage import store_attachment
            path = archived_path(ctx.database.parent/'archive',stored['storage_path'])
            result['project_path'] = str(store_attachment(c,pid,stored,path))
            result['sha256'] = stored['sha256']
            return result
    if route == '/api/incoming-day':
        from ..incoming import save_incoming_day
        return save_incoming_day(c, pid, data['day'], ctx.database.parent / 'archive')
    if route == '/api/entry':
        return save_entry(c, pid, data['entry'])
    if route == '/api/action':
        from ..manual import execute
        return execute(c,pid,data['action'],data.get('data',{}))
    if route == '/api/review':
        from ..acts import review_act
        from ..workflow import same_project
        same_project(c,'acts',data['act_id'],pid)
        if data.get('confirmed') is not True: raise ValueError('Нужно явное подтверждение деловых утверждений')
        return review_act(c,data['act_id'],ctx.templates,data['note'])
    if route == '/api/fact':
        from ..workflow import add_fact
        return add_fact(c, pid, data['fact'])
    if route == '/api/work-fact':
        from ..workflow import add_fact_from_work
        return add_fact_from_work(c, pid, data['fact'])
    if route == '/api/fact-status':
        from ..workflow import same_project, set_fact_status
        same_project(c, 'work_facts', data['fact_id'], pid)
        return set_fact_status(c, data['fact_id'], data['changes'], data['expected'])
    if route == '/api/quality':
        from ..workflow import add_quality_review, same_project
        from ..archive import link_file
        review = data['review']
        same_project(c, 'resources', review['resource_id'], pid)
        if not c.execute('''SELECT 1 FROM project_attachments WHERE project_id=? AND attachment_id=?
            UNION SELECT 1 FROM resource_attachments WHERE resource_id=? AND attachment_id=?''',
            (pid, review['attachment_id'], review['resource_id'], review['attachment_id'])).fetchone():
            raise ValueError('Документ качества не связан с разделом')
        # Явный выбор пары ресурс/документ и результат сверки — одна транзакция.
        link_file(c, attachment_id=review['attachment_id'], entity='resource', entity_id=review['resource_id'])
        return add_quality_review(c, pid, review)
    if route == '/api/act':
        from ..acts import add_act, set_resources, set_schemes
        entry_ids = data.get('entry_ids', [])
        for eid in entry_ids:
            if not c.execute("SELECT 1 FROM workspace_entries WHERE id=? AND project_id=? AND kind='work' AND act_id IS NULL", (eid, pid)).fetchone():
                raise ValueError('Работа уже связана с актом либо относится к другому разделу')
        from ..fields import formatted
        for field in data.get('fields', []):
            if field.get('kind') == 'literal' and not field.get('expression') and field.get('value') not in (None, ''):
                formatted(field['value'], field)
        for removal in data.get('resource_removals', []):
            eid = removal['id']
            if eid not in entry_ids:
                raise ValueError('Материалы можно убрать только из выбранной записи ОЖР')
            entry = dict(c.execute('SELECT * FROM workspace_entries WHERE id=?', (eid,)).fetchone())
            removed = set(removal['resource_ids'])
            if removed.intersection(data.get('resource_ids', [])):
                raise ValueError('Материал одновременно выбран и снят')
            entry['revision'] = removal['revision']
            entry['materials'] = [dict(row) for row in c.execute(
                'SELECT resource_id, quantity FROM work_materials WHERE entry_id=?', (eid,))
                if row['resource_id'] not in removed]
            if entry['resource_id'] in removed:
                entry.update(resource_id=None, quantity=None, unit=None)
            save_entry(c, pid, entry, sync_dates=False)
        from ..form_catalog import ensure_act_form
        ensure_act_form(c, pid, data['act_type'])
        fields=data.get('fields', [])
        form_fields=json.loads(c.execute('SELECT fields FROM document_types WHERE code=?',(data['act_type'],)).fetchone()[0])
        description=next((f for f in form_fields if f['key']=='work_description'),None)
        if entry_ids and description and not any(f['key']=='work_description' and f.get('value') not in (None,'') for f in fields):
            fields=[f for f in fields if f['key']!='work_description']+[{'key':'work_description','kind':'reference','source':'work_summary.description','required':description.get('required',False)}]
        act_id = add_act(c, project_id=pid, act_type=data['act_type'], date_signed=data.get('date_signed') or None, fields=fields)
        set_resources(c, act_id, data.get('resource_ids', []))
        set_schemes(c, act_id, data.get('scheme_ids', []))
        from ..workflow import link_facts
        link_facts(c, act_id, data.get('fact_ids', []))
        resources = set(data.get('resource_ids', []))
        from ..manual import bind_entries
        from ..fields import merge_fields, uses_resource_sources
        from ..form_defaults import apply_form_defaults
        effective = apply_form_defaults(data['act_type'], merge_fields(form_fields, fields))
        work_only = data.get('work_only') is True and not uses_resource_sources(effective)
        bind_entries(c,act_id,entry_ids,work_only=work_only)
        # Списание уже произошло в работе. Акт получает те же факты.
        facts=set(data.get('fact_ids',[]))
        for eid in ([] if work_only else entry_ids):
            facts.update(r[0] for r in c.execute('SELECT fact_id FROM work_materials WHERE entry_id=?',(eid,)))
        link_facts(c,act_id,list(facts))
        if 'organizations' in data:
            from ..act_participants import set_organizations
            set_organizations(c,pid,act_id,data['organizations'])
        if 'signatories' in data:
            from ..ojr import set_act_people
            set_act_people(c,pid,act_id,data['signatories'])
        if data.get('attachment_id'):
            from ..archive import link_file
            from ..document_versions import ensure
            attachment_id=data['attachment_id']
            if not c.execute('SELECT 1 FROM project_attachments WHERE project_id=? AND attachment_id=?',(pid,attachment_id)).fetchone(): raise ValueError('Документ не принадлежит разделу')
            link_file(c,attachment_id=attachment_id,entity='act',entity_id=act_id)
            version=ensure(c,pid,act_id)[-1]
            c.execute('UPDATE document_versions SET attachment_id=? WHERE id=?',(attachment_id,version['id']))
        return {'act_id': act_id}
    if route == '/api/generate':
        act = c.execute('SELECT id FROM acts WHERE id=? AND project_id=?', (data.get('act_id'), pid)).fetchone()
        if not act:
            raise ValueError('Акт не принадлежит разделу')
        from ..managed import generate_managed
        # Веб-интерфейс выпускает черновик; финал проходит штатную содержательную проверку.
        return generate_managed(c, act_id=act[0], templates_dir=ctx.templates, storage=True, draft=not data.get('final',False))
    if route == '/api/registry/export':
        from ..acts import add_act
        from ..form_catalog import connect_form
        from ..managed import generate_managed
        code = 'РЕЕСТР_ИТД'
        if not c.execute('SELECT 1 FROM document_types WHERE code=?', (code,)).fetchone():
            connect_form(c, code)
        registry = c.execute(
            'SELECT id FROM acts WHERE project_id=? AND act_type=? AND is_active=1 ORDER BY id DESC LIMIT 1',
            (pid, code)).fetchone()
        act_id = registry[0] if registry else add_act(c, project_id=pid, act_type=code)
        return generate_managed(c, act_id=act_id, templates_dir=ctx.templates, storage=True, draft=True)
    if route == '/api/statement':
        from ..managed import statement_managed
        return statement_managed(c, project_id=pid, storage=True)
    raise ValueError('Неизвестная операция')
