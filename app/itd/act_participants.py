"""Участники документа: роли с приоритетом раздела, явный выбор организации."""
from .participants import participants_context
from .workflow import same_project
from .db import atomic_operation
from .changes import log_event


def organization_candidates(c,pid):
    context=participants_context(c,pid);result={role:[org] for role,org in context['organizations'].items()}
    for role,people in context['signatory_candidates'].items():
        if role in result:continue
        ids={p['org_id'] for p in people if p['status']=='Действует'}
        result[role]=[dict(c.execute('SELECT * FROM organizations WHERE id=?',(i,)).fetchone()) for i in sorted(ids)]
    project=c.execute('SELECT designer_org_id FROM projects WHERE id=?',(pid,)).fetchone()
    if project['designer_org_id']:
        result['designer']=[dict(c.execute('SELECT * FROM organizations WHERE id=?',(project['designer_org_id'],)).fetchone())]
    # При пустом списке роли представитель выбирается из всех участников объекта.
    from .document_versions import candidates
    from .ojr import directory
    from .workspace import DOC_ROLES
    assigned=candidates(c,pid,fallback=False)
    available=directory(c,pid)
    active_orgs={p['org_id'] for p in available['people'] if p['status']=='Действует'}
    for role in DOC_ROLES:
        if not assigned.get(role):
            ids=active_orgs | {o['id'] for o in result.get(role,[])}
            result[role]=[o for o in available['organizations'] if o['id'] in ids]
    return result


def selections(c,aid):
    return {r['role_key']:r['org_id'] for r in c.execute('SELECT * FROM act_organizations WHERE act_id=?',(aid,))}


@atomic_operation
def set_organizations(c,pid,aid,values):
    same_project(c,'acts',aid,pid)
    if not isinstance(values,dict):raise ValueError('Организации должны быть сопоставлены ролям')
    from .workspace import DOC_ROLES
    available=organization_candidates(c,pid)
    for role,identity in values.items():
        if role not in DOC_ROLES or type(identity) is not int or identity not in {o['id'] for o in available.get(role,[])}:
            raise ValueError('Выберите организацию с соответствующей ролью в «Участниках»')
    before=selections(c,aid)
    c.execute('DELETE FROM act_organizations WHERE act_id=?',(aid,))
    c.executemany('INSERT INTO act_organizations VALUES(?,?,?)',[(aid,r,i) for r,i in values.items()])
    if before!=values:log_event(c,'act-organizations',entity='acts',entity_id=aid,before=before,after=values)


def apply_organizations(c,aid,roots):
    for role,identity in selections(c,aid).items():
        roots['organizations'][role]=dict(c.execute('SELECT * FROM organizations WHERE id=?',(identity,)).fetchone())
