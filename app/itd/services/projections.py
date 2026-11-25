"""Read projections shared by HTTP and future tools, with explicit connections."""
import json
from ..workspace import DOC_ROLES, ROLES, rows
from ..paths import default_templates

def bootstrap(c):
    from ..resources import CATEGORIES
    active = c.execute('SELECT project_id FROM agent_state WHERE id=1').fetchone()
    return {'objects': rows(c, 'SELECT id,name,display_name FROM objects ORDER BY id'),
            'projects': rows(c, 'SELECT id,object_id,name,code FROM projects ORDER BY id'),
            'active_project_id': active[0] if active else None,
            'roles': ROLES, 'document_roles': DOC_ROLES,'categories':CATEGORIES}

def project_data(c, project_id):
    from ..participants import participants_context
    from ..workflow import workflow_context, report
    project = c.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
    if project is None:
        raise ValueError('Раздел не найден')
    from ..registry import registry_rows
    result = {'project': dict(project), 'registry': registry_rows(c, project_id, detailed=True)}
    for table in ('resources', 'schemes', 'acts', 'workspace_entries', 'releases'):
        result[table] = rows(c, f'SELECT * FROM {table} WHERE project_id=? ORDER BY id', (project_id,))
    result['attachments'] = rows(c, '''SELECT a.* FROM attachments a WHERE a.id IN (
        SELECT attachment_id FROM project_attachments WHERE project_id=?
        UNION SELECT ra.attachment_id FROM resource_attachments ra JOIN resources r ON r.id=ra.resource_id WHERE r.project_id=?
        UNION SELECT aa.attachment_id FROM act_attachments aa JOIN acts a ON a.id=aa.act_id WHERE a.project_id=?
        UNION SELECT sa.attachment_id FROM scheme_attachments sa JOIN schemes s ON s.id=sa.scheme_id WHERE s.project_id=?
        UNION SELECT attachment_id FROM object_attachments WHERE object_id=?
        ) ORDER BY a.id''', (project_id, project_id, project_id, project_id, project['object_id']))
    result['scheme_files'] = rows(c, """SELECT s.scheme_id,a.id,a.original_name FROM scheme_attachments s
        JOIN attachments a ON a.id=s.attachment_id JOIN schemes sc ON sc.id=s.scheme_id
        WHERE sc.project_id=? ORDER BY a.id""", (project_id,))
    from ..custom_templates import list_templates, schema
    result['templates'] = list_templates(c)
    result['template_schema'] = schema(c)
    result['forms'] = rows(c, 'SELECT * FROM document_types ORDER BY name')
    from ..file_manager import source_files
    result['source_files']=source_files(c,project_id)
    result['project_attachment_ids'] = [r[0] for r in c.execute('SELECT attachment_id FROM project_attachments WHERE project_id=?', (project_id,))]
    for form in result['forms']:
        form['fields'] = json.loads(form['fields'])
    result['participants'] = participants_context(c, project_id)
    result['form_roots'] = {'project': dict(project),
        'object': dict(c.execute('SELECT * FROM objects WHERE id=?', (project['object_id'],)).fetchone()),
        **result['participants']}
    from ..field_ui import describe_fields
    from ..form_defaults import apply_form_defaults, documentation_context,field_bindings,document_project
    result['form_roots']['project'] = document_project(dict(project), result['form_roots']['object'])
    result['form_roots']['project_documentation'] = documentation_context(c, dict(project), result['participants']['organizations'])
    from ..document_bindings import catalog
    result['binding_sources']=catalog(c,project_id)
    result['form_bindings']=field_bindings()
    from ..form_defaults import date_groups
    result['date_groups'] = date_groups()
    from ..document_versions import candidates
    from ..act_participants import organization_candidates
    result['participant_choices']={'people':candidates(c,project_id),'organizations':organization_candidates(c,project_id)}
    for form in result['forms']:
        form['fields']=apply_form_defaults(form['code'],form['fields'])
        form['ui_fields'] = describe_fields(apply_form_defaults(form['code'], form['fields']))
    result['workflow'] = workflow_context(c, project_id)
    result['check'] = report(c, project_id)
    result['quality_reviews'] = rows(c, 'SELECT q.* FROM quality_reviews q JOIN resources r ON r.id=q.resource_id WHERE r.project_id=? ORDER BY q.id', (project_id,))
    result['delivery_events'] = rows(c, 'SELECT e.* FROM delivery_events e JOIN deliveries d ON d.id=e.delivery_id WHERE d.project_id=? ORDER BY e.id', (project_id,))
    result['pending'] = rows(c, "SELECT * FROM specification_pending WHERE project_id=? AND status='pending' ORDER BY id", (project_id,))
    result['act_facts'] = rows(c, 'SELECT af.* FROM act_facts af JOIN acts a ON a.id=af.act_id WHERE a.project_id=? ORDER BY af.act_id,af.fact_id', (project_id,))
    result['resource_attachments'] = rows(c, 'SELECT ra.* FROM resource_attachments ra JOIN resources r ON r.id=ra.resource_id WHERE r.project_id=? ORDER BY ra.resource_id,ra.attachment_id', (project_id,))
    from ..manual import context
    result['manual']=context(c,project_id)
    from ..journals import journal_data
    result['journals'] = journal_data(c, project_id)
    from ..ojr import participant_ids
    result['form_roots']['participant_ids'] = participant_ids(result['journals']['directory'])
    from ..inventory import balances,work_materials
    result['inventory']=balances(c,project_id)
    result['work_materials']=work_materials(c,project_id)
    result['act_originals']=rows(c,'SELECT DISTINCT f.* FROM act_attachments x JOIN attachments f ON f.id=x.attachment_id JOIN acts a ON a.id=x.act_id WHERE a.project_id=? AND a.is_active=1',(project_id,))
    result['act_signatories']=rows(c,'SELECT s.* FROM act_signatories s JOIN acts a ON a.id=s.act_id WHERE a.project_id=?',(project_id,))
    result['act_statuses']=rows(c,'SELECT s.* FROM act_execution_status s JOIN acts a ON a.id=s.act_id WHERE a.project_id=?',(project_id,))
    people={p['id']:p for p in result['journals']['directory']['people']}
    for entry in result['workspace_entries']:
        person=people.get(entry.get('responsible_id'))
        if person: entry['responsible_display']=person['position']+'. '+person['fio']

    from ..form_catalog import catalog, available_forms
    result['catalog']=catalog()
    result['available_forms']=available_forms(c,project_id)
    result['act_resources']=rows(c,'SELECT ar.* FROM act_resources ar JOIN acts a ON a.id=ar.act_id WHERE a.project_id=? ORDER BY ar.ordinal',(project_id,))
    result['act_schemes']=rows(c,'SELECT s.* FROM act_schemes s JOIN acts a ON a.id=s.act_id WHERE a.project_id=? ORDER BY s.ordinal',(project_id,))
    from ..ojr import act_work_description
    for act in result['acts']:
        act['work_description']=act_work_description(c,act['id'])
        act['fields_json']=act['fields']
        act['fields']=json.loads(act['fields'])
    return result
