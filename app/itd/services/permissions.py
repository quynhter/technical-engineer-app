"""A closed operation catalogue and a single role check for all entry points."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Policy:
    role: str
    write: bool


RANK = {'viewer': 0, 'editor': 1, 'admin': 2}

LIST_ENTITIES = ('objects', 'projects', 'resources', 'schemes', 'document_types', 'acts',
                 'organizations', 'signatories', 'attachments', 'audit_events',
                 'generated_documents', 'resource_sources', 'organization_assignments',
                 'signatory_assignments', 'work_facts', 'package_requirements', 'quality_reviews',
                 'deliveries', 'delivery_events', 'delivery_remarks')


def require(actor, role):
    if actor is None or actor.role not in RANK or RANK[actor.role] < RANK[role]:
        raise PermissionError('Требуется роль администратора' if role == 'admin'
                              else 'Наблюдателю доступен просмотр сведений')


ACTION_READS = {'context', 'delete-preview', 'resource-import-preview'}


WORKSPACE_ACTIONS = [
    'act-composition',
    'act-entries',
    'act-signatories',
    'act-status',
    'allocate',
    'assign',
    'context',
    'delete-apply',
    'delete-preview',
    'delivery-add',
    'delivery-set',
    'designer-add',
    'document-version-ensure',
    'document-version-save',
    'entry-save',
    'fact-add',
    'fact-set',
    'form-connect',
    'journal-add',
    'period-set',
    'quality-review-add',
    'remark-add',
    'remark-resolve',
    'requirement-add',
    'requirement-set',
    'resource-add',
    'resource-card-save',
    'resource-import-commit',
    'resource-import-preview',
    'resource-import-stage',
    'scheme-add',
    'sources-review',
    'special-journal-save',
    'supply-add',
    'supply-set',
    'unit-add',
    'update',
]


def action_policy(action):
    if action not in WORKSPACE_ACTIONS:
        raise ValueError('Неизвестная ручная операция')
    return Policy('viewer', False) if action in ACTION_READS else Policy('editor', True)

CLI_COMMANDS = {
    'act-add',
    'act-context',
    'act-facts',
    'act-resources',
    'act-review',
    'act-schemes',
    'assign',
    'backup',
    'delivery-add',
    'delivery-set',
    'doctor',
    'fact-add',
    'fact-set',
    'fact-summary',
    'file-add',
    'file-link',
    'folders',
    'form-register',
    'generate',
    'init',
    'knowledge-export',
    'knowledge-index',
    'knowledge-search',
    'knowledge-show',
    'knowledge-status',
    'knowledge-validate',
    'list',
    'object-add',
    'organization-add',
    'package-export',
    'package-matrix',
    'project-activate',
    'project-add',
    'project-check',
    'project-context',
    'quality-review-add',
    'read-document',
    'record-update',
    'registry-data',
    'release-list',
    'release-move',
    'release-publish',
    'release-reconcile',
    'release-recover',
    'release-rename',
    'release-select',
    'release-unselect',
    'release-verify',
    'remark-add',
    'remark-resolve',
    'requirement-add',
    'requirement-set',
    'resource-add',
    'scheme-add',
    'signatory-add',
    'spec-compare',
    'spec-import',
    'statement-xlsx',
    'template-schema',
    'title-add',
    'title-config',
    'web',
    'workflow-context',
    'workspace-action',
    'workspace-save',
}

CLI_READS = {
    'list', 'act-context', 'registry-data', 'backup', 'fact-summary',
    'package-matrix', 'project-check', 'workflow-context', 'spec-compare',
    'release-list', 'release-verify', 'project-context', 'title-config', 'package-export',
    'doctor', 'read-document', 'template-schema', 'knowledge-status', 'knowledge-search',
    'knowledge-show', 'knowledge-validate', 'knowledge-index', 'knowledge-export',
}


def cli_policy(args):
    if args.command not in CLI_COMMANDS:
        raise ValueError('Неизвестная команда')
    if args.command == 'workspace-action':
        return action_policy(args.action)
    read = args.command in CLI_READS or (args.command == 'release-reconcile' and not args.apply)
    role = 'viewer' if read else 'editor'
    if args.command in ('backup', 'package-export'):
        role = 'editor'
    if args.command in ('init', 'web'):
        role = 'admin'
    if args.command == 'list' and getattr(args, 'entity', None) == 'audit_events':
        role = 'admin'
    return Policy(role, not read)


WEB_READS = {
    '/api/status': 'viewer', '/api/bootstrap': 'viewer', '/api/workspace': 'viewer',
    '/api/project': 'viewer', '/api/context': 'viewer', '/api/knowledge': 'viewer',
    '/api/configuration': 'editor', '/api/download': 'editor', '/api/original': 'editor',
    '/api/package': 'editor',
}

ACCOUNT_POLICIES = {
    'list': Policy('admin', False), 'profile': Policy('viewer', True),
    'rotate-self': Policy('viewer', True), 'create': Policy('admin', True),
    'role': Policy('admin', True), 'delete': Policy('admin', True),
    'rotate-user': Policy('admin', True),
}
WEB_POSTS = {
    '/api/configuration/preview', '/api/save', '/api/activate', '/api/upload',
    '/api/incoming-day', '/api/entry', '/api/action', '/api/review', '/api/fact',
    '/api/work-fact', '/api/fact-status', '/api/quality', '/api/act', '/api/generate',
    '/api/registry/export', '/api/statement', '/api/ojr-title', '/api/files/plan',
    '/api/files/apply', '/api/files/recover', '/api/versions/list', '/api/versions/ensure',
    '/api/versions/create', '/api/versions/save', '/api/versions/delete',
    '/api/versions/regenerate', '/api/resource-import/stage',
    '/api/resource-import/preview', '/api/resource-import/commit',
}


def web_policy(route, data=None, *, read=False):
    if read:
        if route not in WEB_READS:
            raise ValueError('Страница не найдена')
        return Policy(WEB_READS[route], False)
    if route not in WEB_POSTS:
        raise ValueError('Неизвестная операция')
    data = data or {}
    if route == '/api/action':
        policy = action_policy(data.get('action'))
        # Preserve the existing HTTP viewer contract (only context is exposed).
        return Policy('viewer' if data.get('action') == 'context' else 'editor', policy.write)
    return Policy('editor', route not in {
        '/api/versions/list', '/api/resource-import/preview', '/api/configuration/preview',
        '/api/files/plan',
    })
