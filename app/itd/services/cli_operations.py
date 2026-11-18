"""Internal implementation of the preserved CLI command contract."""
import json
import sqlite3
from pathlib import Path

from ..paths import default_database, default_templates
from ..db import DATE_FIELDS, add_object, add_project, connect, initialize
from ..resources import CATEGORIES, add_resource, add_scheme
from ..acts import add_act, build_context, generate, register_form, set_resources, set_schemes
from ..layout import create_layout
from ..archive import DOCUMENT_TYPES, LINKS, import_file, link_file
from ..participants import add_organization, add_signatory, assign
from ..changes import EDITABLE, log_event, update_record
from ..registry import registry_rows
from ..readers import read_document
from ..specification import import_specification
from ..statement import export_statement



def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def dispatch(connection, args, ctx, actor):
    if args.command == "workspace-save":
        from ..workspace import save_workspace
        result = save_workspace(connection, read_json(args.data))
    elif args.command == 'workspace-action':
        from ..manual import execute
        result = execute(connection,args.project_id,args.action,read_json(args.data))
    elif args.command in ("fact-add", "requirement-add", "quality-review-add", "delivery-add"):
        from .. import workflow
        operation = {"fact-add":workflow.add_fact, "requirement-add":workflow.add_requirement,
                     "quality-review-add":workflow.add_quality_review, "delivery-add":workflow.add_delivery}[args.command]
        result = operation(connection, args.project_id, read_json(args.data))
    elif args.command in ("fact-set", "requirement-set", "delivery-set", "remark-resolve"):
        from .. import workflow
        operation, record_id = {
            "fact-set":(workflow.set_fact_status, getattr(args,"fact_id",None)),
            "requirement-set":(workflow.set_requirement,getattr(args,"requirement_id",None)),
            "delivery-set":(workflow.set_delivery,getattr(args,"delivery_id",None)),
            "remark-resolve":(workflow.resolve_remark,getattr(args,"remark_id",None))}[args.command]
        result = operation(connection, record_id, read_json(args.data), read_json(args.expected))
    elif args.command == "remark-add":
        from ..workflow import add_remark
        result = add_remark(connection, args.delivery_id, read_json(args.data))
    elif args.command == "act-facts":
        from ..workflow import link_facts
        result = link_facts(connection, args.act_id, args.fact_id)
    elif args.command in ("fact-summary", "package-matrix", "project-check", "workflow-context"):
        from .. import workflow
        operation = {"fact-summary":workflow.fact_summary, "package-matrix":workflow.matrix,
                     "project-check":workflow.report, "workflow-context":workflow.workflow_context}[args.command]
        result = operation(connection, args.project_id)
    elif args.command == "spec-compare":
        from ..revision_compare import compare
        result = compare(connection, args.project_id, args.old_attachment_id, args.new_attachment_id,
                         read_json(args.old_data), read_json(args.data), complete=args.complete)
    elif args.command == "object-add":
        result = {"id": add_object(connection, args.name)}
    elif args.command == "project-add":
        result = {"id": add_project(
            connection, object_id=args.object_id, section_code=args.section,
            code=args.code, name=args.name, city=args.city,
            **{field: getattr(args, field) for field in DATE_FIELDS},
        )}
    elif args.command in ("resource-add", "scheme-add"):
        values = {key: value for key, value in vars(args).items()
                  if key not in ("db", "command")}
        operation = add_resource if args.command == "resource-add" else add_scheme
        result = {"id": operation(connection, **values)}
    elif args.command == "form-register":
        register_form(connection, code=args.type, name=args.name, fields=read_json(args.fields), form_group=args.group, filename_title=args.filename_title)
        result = {"ok": True, "act_type": args.type, "template": args.type + ".docx"}
    elif args.command == "title-add":
        from ..titles import add_title
        result = add_title(connection, args.project_id, read_json(args.data))
    elif args.command == "title-config":
        from ..titles import export_config
        result = export_config(connection, args.act_id)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
        result = {"output": str(args.output.resolve())}
    elif args.command == "act-add":
        act_id = add_act(connection, project_id=args.project_id, act_type=args.type,
                         date_signed=args.date_signed, fields=read_json(args.fields) if args.fields else None)
        row = connection.execute("SELECT id, act_num FROM acts WHERE id=?", (act_id,)).fetchone()
        result = dict(row)
    elif args.command == "act-resources":
        set_resources(connection, args.act_id, args.resource_id)
        result = {"ok": True, "act_id": args.act_id, "resource_ids": args.resource_id}
    elif args.command == "act-schemes":
        set_schemes(connection, args.act_id, args.scheme_id)
        result = {"ok": True, "act_id": args.act_id, "scheme_ids": args.scheme_id}
    elif args.command == "act-context":
        from ..acts import find_template, template_claims
        result = build_context(connection, args.act_id, draft=not args.final)
        if args.objects:
            from ..template_objects import CONTEXT_KEY
            result['context'] = result['context'].get(CONTEXT_KEY, result['context'])
        try:
            result["static_claims_to_review"] = template_claims(find_template(args.templates, result["act_type"]))
        except ValueError as error:
            result["template_review_error"] = str(error)
    elif args.command == "act-review":
        from ..acts import review_act
        result = review_act(connection, args.act_id, args.templates, args.note)
    elif args.command == "generate":
        from ..managed import generate_managed
        result = generate_managed(connection, act_id=args.act_id, templates_dir=args.templates,
                                  output=args.output, root=args.root, draft=not args.final)
    elif args.command == "folders":
        result = create_layout(connection, args.project_id, args.root)
    elif args.command in ("organization-add", "signatory-add"):
        values = read_json(args.data)
        if not isinstance(values, dict):
            raise ValueError("Реквизиты должны быть JSON-объектом")
        operation = add_organization if args.command == "organization-add" else add_signatory
        import inspect
        allowed = set(inspect.signature(operation).parameters) - {"connection"}
        if set(values) - allowed:
            raise ValueError("Неизвестные реквизиты: " + ", ".join(sorted(set(values) - allowed)))
        required = {key for key, param in inspect.signature(operation).parameters.items()
                    if param.kind == param.KEYWORD_ONLY and param.default is param.empty}
        if required - set(values):
            raise ValueError("Не заполнены реквизиты: " + ", ".join(sorted(required - set(values))))
        result = {"id": operation(connection, **values)}
    elif args.command == "assign":
        assign(connection, entity=args.entity, entity_id=args.entity_id, role_key=args.role,
               object_id=args.object_id, project_id=args.project_id)
        result = {"ok": True}
    elif args.command == "file-add":
        result = import_file(connection, archive_root=args.archive or args.db.resolve().parent / "archive",
                             source=args.file, doc_type=args.type, title=args.title,
                             doc_num=args.num, doc_date=args.date)
    elif args.command == "file-link":
        result = link_file(connection, attachment_id=args.attachment_id, entity=args.entity, entity_id=args.entity_id)
        project_id = args.entity_id if args.entity=='project' else None
        if args.entity in ('resource','act','scheme'):
            table={'resource':'resources','act':'acts','scheme':'schemes'}[args.entity]
            project_id=connection.execute(f'SELECT project_id FROM {table} WHERE id=?',(args.entity_id,)).fetchone()[0]
        if project_id is not None:
            from ..archive import publish_project_file
            result['project_path'] = publish_project_file(connection,attachment_id=args.attachment_id,project_id=project_id,archive_root=args.archive or args.db.resolve().parent/'archive')
    elif args.command == "record-update":
        result = update_record(connection, entity=args.entity, record_id=args.record_id,
                               changes=read_json(args.data), expected=read_json(args.expected) if args.expected else None)
    elif args.command == "spec-import":
        result = import_specification(connection, project_id=args.project_id,
                                      attachment_id=args.attachment_id, items=read_json(args.data))
    elif args.command == "registry-data":
        result = registry_rows(connection, args.project_id, registry_act_id=args.registry_act_id)
    elif args.command == "statement-xlsx":
        from ..managed import statement_managed
        result = statement_managed(connection, project_id=args.project_id, output=args.output, root=args.root,
                                   node=args.node, node_modules=args.node_modules, preview_dir=args.preview_dir)
    elif args.command in ("release-list", "release-verify"):
        from ..releases import list_releases, verify_releases
        result = (list_releases if args.command == "release-list" else verify_releases)(connection, args.project_id)
    elif args.command in ("release-move", "release-rename", "release-publish"):
        from ..releases import move_release, publish
        result = (publish if args.command == "release-publish" else move_release)(connection, args.release_id, args.output)
    elif args.command == "release-recover":
        from ..releases import recover
        result = recover(connection, args.operation_id)
    elif args.command == "release-select":
        from ..releases import select_release
        select_release(connection, args.release_id)
        result = {"selected": args.release_id}
    elif args.command == 'release-unselect':
        from ..releases import unselect_release
        result = unselect_release(connection,args.release_id)
    elif args.command == "release-reconcile":
        from ..releases import reconcile, plan_relocations
        if args.from_relocations and args.apply:
            raise ValueError("Сначала сохраните и согласуйте точный план")
        result = plan_relocations(connection, read_json(args.data)) if args.from_relocations else reconcile(connection, read_json(args.data), apply=args.apply)
    elif args.command == "package-export":
        from ..releases import export_package
        result = export_package(connection, args.project_id, args.output, include_originals=args.include_originals,
                                source=actor.source)
    elif args.command == "project-activate":
        if not connection.execute("SELECT 1 FROM projects WHERE id=?", (args.project_id,)).fetchone():
            raise ValueError("Раздел не найден")
        connection.execute("INSERT INTO agent_state VALUES(1,?) ON CONFLICT(id) DO UPDATE SET project_id=excluded.project_id", (args.project_id,))
        result = {"project_id": args.project_id}
    elif args.command == "project-context":
        project_id = args.project_id
        if project_id is None:
            state = connection.execute("SELECT project_id FROM agent_state WHERE id=1").fetchone()
            if state is None:
                raise ValueError("Активный раздел не выбран: укажите --project-id или project-activate")
            project_id = state[0]
        row = connection.execute("SELECT p.*,o.name AS object_name FROM projects p JOIN objects o ON p.object_id=o.id WHERE p.id=?",(project_id,)).fetchone()
        if row is None:raise ValueError("Раздел не найден")
        result = dict(row)
        result["object"] = dict(connection.execute("SELECT * FROM objects WHERE id=?", (row["object_id"],)).fetchone())
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='object_participants'").fetchone():
            from ..workspace import snapshot, rows
            result["participants_card"] = snapshot(connection, row["object_id"])["participants"]
            result["workspace_entries"] = rows(connection, "SELECT * FROM workspace_entries WHERE project_id=? ORDER BY id", (project_id,))
        result["agent_context"] = json.loads(result["agent_context"])
        from ..knowledge import default_root, default_index
        result['knowledge'] = {'root': str(default_root()), 'index': str(default_index(args.db)),
                               'search_command': 'knowledge-search',
                               'usage': 'Искать по работам, затем проверить оригинал и применимость; согласованные основания сохранять в agent_context.'}
        result["pending"] = [dict(r) for r in connection.execute("SELECT * FROM specification_pending WHERE project_id=? AND status='pending' ORDER BY id",(project_id,))]
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='work_facts'").fetchone():
            from ..workflow import workflow_context
            result["workflow"] = workflow_context(connection, project_id)
    elif args.command == "backup":
        target = args.output.resolve()
        if target == args.db.resolve():
            raise ValueError("Резервная копия не может перезаписать исходную БД")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb"):
            pass
        try:
            with sqlite3.connect(target) as destination:
                connection.backup(destination)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        result = {"output": str(target), "note": "Архив приложений копируется отдельно"}
    elif args.command == 'list':
        from .permissions import LIST_ENTITIES
        if args.entity not in LIST_ENTITIES:
            raise ValueError('Неизвестная таблица просмотра')
        where = ""
        parameters = ()
        if args.project_id is not None:
            if args.entity not in ("resources", "schemes", "acts", "work_facts", "package_requirements", "deliveries"):
                raise ValueError("--project-id применим только к таблицам с прямой принадлежностью разделу")
            where = " WHERE project_id = ?"
            parameters = (args.project_id,)
        result = [dict(row) for row in connection.execute(
            f"SELECT * FROM {args.entity}{where} ORDER BY id", parameters
        )]
    else:
        raise ValueError('Команда не является деловой операцией')
    return result
