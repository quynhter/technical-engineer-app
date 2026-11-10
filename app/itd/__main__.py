"""Запуск: python -m itd --db /путь/itd.db <команда>."""

import argparse
import json
import sqlite3
from pathlib import Path

from .paths import default_database, default_templates
from .db import DATE_FIELDS, add_object, add_project, connect, initialize
from .resources import CATEGORIES, add_resource, add_scheme
from .acts import add_act, build_context, generate, register_form, set_resources, set_schemes
from .layout import create_layout
from .archive import DOCUMENT_TYPES, LINKS, import_file, link_file
from .participants import add_organization, add_signatory, assign
from .changes import EDITABLE, log_event, update_record
from .registry import registry_rows
from .readers import read_document
from .specification import import_specification
from .statement import export_statement


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Локальные инструменты ИТД")
    from . import __version__
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--db", type=Path, default=default_database())
    parser.add_argument("--agent", action="store_true", help="Отметить вызов из ИИ-агента в журнале")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Применить миграции")
    for name in ('knowledge-status', 'knowledge-validate', 'knowledge-index', 'knowledge-search', 'knowledge-show', 'knowledge-export'):
        from .knowledge import default_root
        knowledge = commands.add_parser(name, help="Локальная база нормативных знаний")
        knowledge.add_argument('--root', type=Path, default=default_root())
        if name == 'knowledge-search':
            knowledge.add_argument('--query', default='')
            for option in ('corpus', 'clause', 'work', 'form'):
                knowledge.add_argument('--' + option)
            knowledge.add_argument('--kind', choices=('chunk', 'rule'))
            knowledge.add_argument('--limit', type=int, default=10)
        elif name == 'knowledge-show':
            knowledge.add_argument('--id', required=True)
        elif name == 'knowledge-export':
            knowledge.add_argument('--output', type=Path, required=True)
    web = commands.add_parser("web", help="Открыть локальную форму ИТД")
    web.add_argument("--port", type=int, default=None, help="Порт (по умолчанию 8765 или свободный); 0 — свободный")
    web.add_argument("--no-browser", action="store_true")
    wizard = commands.add_parser("workspace-save", help="Сохранить JSON локальной формы атомарно")
    wizard.add_argument("--data", type=Path, required=True)
    manual = commands.add_parser('workspace-action', help='Общие ручные операции веб/CLI')
    manual.add_argument('--project-id',type=int,required=True)
    manual.add_argument('--action',required=True)
    manual.add_argument('--data',type=Path,required=True)
    doctor = commands.add_parser("doctor", help="Импорт зависимостей и smoke-проверки")
    doctor.add_argument("--renderer", help="Путь доступного LibreOffice, включая управляемую среду")
    reader = commands.add_parser("read-document", help="Извлечь текст и таблицы PDF/DOCX/XLSX")
    reader.add_argument("--file", type=Path, required=True)
    reader.add_argument("--render-pages", type=Path, help="Изображения всех страниц PDF для модели")
    reader.add_argument("--pages", help="Страницы PDF, например 1,4-7")
    reader.add_argument("--dpi", type=int, default=144)
    reader.add_argument("--overview", action="store_true", help="Обзор состава PDF без полного текста")
    reader.add_argument("--output", type=Path, help="Сохранить JSON вместо вывода содержимого в чат")
    obj = commands.add_parser("object-add", help="Создать объект")
    obj.add_argument("--name", required=True)
    project = commands.add_parser("project-add", help="Создать раздел РД объекта")
    project.add_argument("--object-id", type=int, required=True)
    project.add_argument("--section", required=True)
    project.add_argument("--code", required=True)
    project.add_argument("--name", required=True)
    project.add_argument("--city")
    for field in DATE_FIELDS:
        project.add_argument("--" + field.replace("_", "-"))
    resource = commands.add_parser("resource-add", help="Добавить позицию спецификации")
    resource.add_argument("--project-id", type=int, required=True)
    resource.add_argument("--name", required=True)
    resource.add_argument("--unit", required=True)
    resource.add_argument("--category", required=True, choices=CATEGORIES)
    for field in ("spec_num", "short_name", "type_mark", "manufacturer", "supplier", "note"):
        resource.add_argument("--" + field.replace("_", "-"))
    resource.add_argument("--serial", dest="serial_numbers", action="append")
    for field in ("qty_proj", "qty_fact", "unit_weight"):
        resource.add_argument("--" + field.replace("_", "-"), type=float)
    scheme = commands.add_parser("scheme-add", help="Зарегистрировать исполнительную схему")
    scheme.add_argument("--project-id", type=int, required=True)
    scheme.add_argument("--num", required=True)
    scheme.add_argument("--name", required=True)
    scheme.add_argument("--ref-code")
    scheme.add_argument("--sheets-count", type=int)
    scheme.add_argument("--note")
    form = commands.add_parser("form-register", help="Зарегистрировать тип документа и поля формы")
    form.add_argument("--type", required=True)
    form.add_argument("--name", required=True)
    form.add_argument("--filename-title", help="Краткое имя файла, отдельно от полного названия")
    form.add_argument("--fields", type=Path, required=True)
    form.add_argument("--group", choices=("act", "statement", "registry"), default="act")
    act = commands.add_parser("act-add", help="Создать акт с внутренним номером")
    act.add_argument("--project-id", type=int, required=True)
    act.add_argument("--type", required=True)
    act.add_argument("--date-signed")
    act.add_argument("--fields", type=Path)
    title = commands.add_parser("title-add", help="Создать титульник из БД и настроек TitleGenerator")
    title.add_argument("--project-id", type=int, required=True)
    title.add_argument("--data", type=Path, required=True)
    title_config = commands.add_parser("title-config", help="Сохранить конфигурацию титульника в JSON")
    title_config.add_argument("--act-id", type=int, required=True)
    title_config.add_argument("--output", type=Path, required=True)
    composition = commands.add_parser("act-resources", help="Задать состав ресурсов акта в нужном порядке")
    composition.add_argument("--act-id", type=int, required=True)
    composition.add_argument("--resource-id", type=int, action="append", default=[])
    scheme_composition = commands.add_parser("act-schemes", help="Задать схемы акта в нужном порядке")
    scheme_composition.add_argument("--act-id", type=int, required=True)
    scheme_composition.add_argument("--scheme-id", type=int, action="append", default=[])
    context = commands.add_parser("act-context", help="Собрать поля акта из текущих данных БД")
    context.add_argument("--act-id", type=int, required=True)
    context.add_argument("--final", action="store_true")
    context.add_argument("--templates", type=Path, default=default_templates())
    review = commands.add_parser("act-review", help="Записать подтверждённую проверку статических утверждений")
    review.add_argument("--act-id", type=int, required=True)
    review.add_argument("--templates", type=Path, default=default_templates())
    review.add_argument("--note", required=True)
    review.add_argument("--confirmed", action="store_true", required=True)
    render = commands.add_parser("generate", help="Сформировать DOCX из БД по шаблону act_type.docx")
    render.add_argument("--act-id", type=int, required=True)
    render.add_argument("--templates", type=Path, default=default_templates())
    render.add_argument("--output", type=Path)
    render.add_argument("--root", type=Path, help="Корень ИТД для автоматического имени")
    render.add_argument("--final", action="store_true")
    layout = commands.add_parser("folders", help="Создать папки раздела внутри корня ИТД")
    layout.add_argument("--project-id", type=int, required=True)
    layout.add_argument("--root", type=Path, required=True)
    for command, help_text in (("organization-add", "Добавить организацию из JSON"),
                               ("signatory-add", "Добавить подписанта из JSON")):
        participant = commands.add_parser(command, help=help_text)
        participant.add_argument("--data", type=Path, required=True)
    assignment = commands.add_parser("assign", help="Назначить участника на объект или раздел")
    assignment.add_argument("--entity", choices=("organization", "signatory"), required=True)
    assignment.add_argument("--entity-id", type=int, required=True)
    assignment.add_argument("--role", required=True)
    scope = assignment.add_mutually_exclusive_group(required=True)
    scope.add_argument("--object-id", type=int)
    scope.add_argument("--project-id", type=int)
    archive = commands.add_parser("file-add", help="Сохранить оригинал в общий архив")
    archive.add_argument("--file", type=Path, required=True)
    archive.add_argument("--archive", type=Path)
    archive.add_argument("--type", choices=DOCUMENT_TYPES, required=True)
    archive.add_argument("--title", required=True)
    archive.add_argument("--num")
    archive.add_argument("--date")
    link = commands.add_parser("file-link", help="Связать архивный файл с записью БД")
    link.add_argument("--attachment-id", type=int, required=True)
    link.add_argument("--entity", choices=tuple(LINKS), required=True)
    link.add_argument("--entity-id", type=int, required=True)
    link.add_argument("--archive", type=Path, help="Архив оригиналов; по умолчанию рядом с БД")
    revision = commands.add_parser("record-update", help="Изменить одну запись по ID с журналом до/после")
    revision.add_argument("--entity", choices=tuple(EDITABLE), required=True)
    revision.add_argument("--id", dest="record_id", type=int, required=True)
    revision.add_argument("--data", type=Path, required=True)
    revision.add_argument("--expected", type=Path)
    specification = commands.add_parser("spec-import", help="Импортировать прочитанные позиции из JSON с источниками")
    specification.add_argument("--project-id", type=int, required=True)
    specification.add_argument("--attachment-id", type=int, required=True)
    specification.add_argument("--data", type=Path, required=True)
    registry = commands.add_parser("registry-data", help="Получить строки реестра раздела")
    registry.add_argument("--project-id", type=int, required=True)
    registry.add_argument("--registry-act-id", type=int)
    statement = commands.add_parser("statement-xlsx", help="Общая ведомость ресурсов раздела")
    statement.add_argument("--project-id", type=int, required=True)
    statement.add_argument("--output", type=Path)
    statement.add_argument("--root", type=Path)
    statement.add_argument("--node")
    statement.add_argument("--node-modules", type=Path)
    statement.add_argument("--preview-dir", type=Path)
    backup = commands.add_parser("backup", help="Согласованная резервная копия SQLite")
    backup.add_argument("--output", type=Path, required=True)
    listing = commands.add_parser("list", help="Вывести объекты или разделы в JSON")
    listing.add_argument("entity", choices=("objects", "projects", "resources", "schemes", "document_types", "acts", "organizations", "signatories", "attachments", "audit_events", "generated_documents", "resource_sources", "organization_assignments", "signatory_assignments", "work_facts", "package_requirements", "quality_reviews", "deliveries", "delivery_events", "delivery_remarks"))
    listing.add_argument("--project-id", type=int, help="Отбор ресурсов/схем по разделу")
    for name in ("release-list", "release-verify", "project-context"):
        command = commands.add_parser(name)
        command.add_argument("--project-id", type=int)
    moving = commands.add_parser("release-move", aliases=["release-rename"])
    moving.add_argument("--release-id", type=int, required=True)
    moving.add_argument("--output", type=Path, required=True)
    recovery = commands.add_parser("release-recover")
    recovery.add_argument("--operation-id", type=int, required=True)
    selecting = commands.add_parser("release-select")
    selecting.add_argument("--release-id", type=int, required=True)
    publishing = commands.add_parser("release-publish", help="Продолжить публикацию сохранённого выпуска после сбоя")
    publishing.add_argument("--release-id", type=int, required=True)
    publishing.add_argument("--output", type=Path, required=True)
    package = commands.add_parser("package-export")
    package.add_argument("--project-id", type=int, required=True)
    package.add_argument("--output", type=Path, required=True)
    reconciliation = commands.add_parser("release-reconcile")
    reconciliation.add_argument("--data", type=Path, required=True)
    reconciliation.add_argument("--apply", action="store_true")
    reconciliation.add_argument("--from-relocations", action="store_true", help="Только построить план из original_path/history_path/sha256")
    activate = commands.add_parser("project-activate")
    activate.add_argument("--project-id", type=int, required=True)
    for name in ("fact-add", "requirement-add", "quality-review-add", "delivery-add"):
        command = commands.add_parser(name)
        command.add_argument("--project-id", type=int, required=True)
        command.add_argument("--data", type=Path, required=True)
    for name, key in (("fact-set", "fact-id"), ("requirement-set", "requirement-id"),
                      ("delivery-set", "delivery-id"), ("remark-resolve", "remark-id")):
        command = commands.add_parser(name)
        command.add_argument("--"+key, type=int, required=True)
        command.add_argument("--data", type=Path, required=True)
        command.add_argument("--expected", type=Path, required=True)
    remark = commands.add_parser("remark-add")
    remark.add_argument("--delivery-id", type=int, required=True)
    remark.add_argument("--data", type=Path, required=True)
    facts = commands.add_parser("act-facts")
    facts.add_argument("--act-id", type=int, required=True)
    facts.add_argument("--fact-id", type=int, action="append", default=[])
    for name in ("fact-summary", "package-matrix", "project-check", "workflow-context"):
        command = commands.add_parser(name)
        command.add_argument("--project-id", type=int, required=True)
        command.add_argument("--output", type=Path)
    comparison = commands.add_parser("spec-compare", help="Сравнить JSON двух редакций без импорта")
    comparison.add_argument("--project-id", type=int, required=True)
    comparison.add_argument("--old-attachment-id", type=int, required=True)
    comparison.add_argument("--new-attachment-id", type=int, required=True)
    comparison.add_argument("--old-data", type=Path, required=True)
    comparison.add_argument("--data", type=Path, required=True)
    comparison.add_argument("--complete", action="store_true", help="Новая редакция прочитана полностью")
    comparison.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    agent_run = vars(args).pop('agent')
    agent_log = None
    try:
        if agent_run:
            import logging
            from .logging_setup import configure
            from .paths import ROOT
            configure(ROOT / 'logs')
            agent_log = logging.getLogger('itd.ai')
            agent_log.info('Агент запустил команду %s', args.command)
        if args.command.startswith('knowledge-'):
            from . import knowledge
            index = knowledge.default_index(args.db)
            if args.command in ('knowledge-status', 'knowledge-validate'):
                result = knowledge.status(args.root, index)
            elif args.command == 'knowledge-index':
                result = knowledge.build_index(args.root, index)
            elif args.command == 'knowledge-show':
                result = knowledge.show(args.root, index, args.id)
            elif args.command == 'knowledge-export':
                result = knowledge.export_entries(args.root, args.output)
            else:
                result = knowledge.search(args.root, index, args.query, corpus=args.corpus,
                                          kind=args.kind, clause=args.clause, work=args.work,
                                          form=args.form, limit=args.limit)
        elif args.command == "web":
            from .web import serve
            serve(args.db, args.port, not args.no_browser)
            return
        elif args.command == "init":
            args.db.parent.mkdir(parents=True, exist_ok=True)
            initialize(args.db)
            result = {"ok": True, "db": str(args.db)}
        elif args.command == "doctor":
            from .doctor import diagnose
            result = diagnose(args.renderer)
        elif args.command == "read-document":
            result = read_document(args.file, scan_dir=args.render_pages, pages=args.pages, dpi=args.dpi, overview=args.overview)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("x", encoding="utf-8") as handle:
                    json.dump(result, handle, ensure_ascii=False, indent=2)
                result = {"output": str(args.output.resolve()), "parts": len(result["parts"]), "sha256": result["sha256"]}
        else:
            if not args.db.is_file():
                raise ValueError("БД не найдена. Сначала выполните init.")
            with connect(args.db) as connection:
                if args.command == "workspace-save":
                    from .workspace import save_workspace
                    result = save_workspace(connection, read_json(args.data))
                elif args.command == 'workspace-action':
                    from .manual import execute
                    result = execute(connection,args.project_id,args.action,read_json(args.data))
                elif args.command in ("fact-add", "requirement-add", "quality-review-add", "delivery-add"):
                    from . import workflow
                    operation = {"fact-add":workflow.add_fact, "requirement-add":workflow.add_requirement,
                                 "quality-review-add":workflow.add_quality_review, "delivery-add":workflow.add_delivery}[args.command]
                    result = operation(connection, args.project_id, read_json(args.data))
                elif args.command in ("fact-set", "requirement-set", "delivery-set", "remark-resolve"):
                    from . import workflow
                    operation, record_id = {
                        "fact-set":(workflow.set_fact_status, getattr(args,"fact_id",None)),
                        "requirement-set":(workflow.set_requirement,getattr(args,"requirement_id",None)),
                        "delivery-set":(workflow.set_delivery,getattr(args,"delivery_id",None)),
                        "remark-resolve":(workflow.resolve_remark,getattr(args,"remark_id",None))}[args.command]
                    result = operation(connection, record_id, read_json(args.data), read_json(args.expected))
                elif args.command == "remark-add":
                    from .workflow import add_remark
                    result = add_remark(connection, args.delivery_id, read_json(args.data))
                elif args.command == "act-facts":
                    from .workflow import link_facts
                    result = link_facts(connection, args.act_id, args.fact_id)
                elif args.command in ("fact-summary", "package-matrix", "project-check", "workflow-context"):
                    from . import workflow
                    operation = {"fact-summary":workflow.fact_summary, "package-matrix":workflow.matrix,
                                 "project-check":workflow.report, "workflow-context":workflow.workflow_context}[args.command]
                    result = operation(connection, args.project_id)
                elif args.command == "spec-compare":
                    from .revision_compare import compare
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
                    from .titles import add_title
                    result = add_title(connection, args.project_id, read_json(args.data))
                elif args.command == "title-config":
                    from .titles import export_config
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
                    from .acts import find_template, template_claims
                    result = build_context(connection, args.act_id, draft=not args.final)
                    try:
                        result["static_claims_to_review"] = template_claims(find_template(args.templates, result["act_type"]))
                    except ValueError as error:
                        result["template_review_error"] = str(error)
                elif args.command == "act-review":
                    from .acts import review_act
                    result = review_act(connection, args.act_id, args.templates, args.note)
                elif args.command == "generate":
                    from .managed import generate_managed
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
                        from .archive import publish_project_file
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
                    from .managed import statement_managed
                    result = statement_managed(connection, project_id=args.project_id, output=args.output, root=args.root,
                                               node=args.node, node_modules=args.node_modules, preview_dir=args.preview_dir)
                elif args.command in ("release-list", "release-verify"):
                    from .releases import list_releases, verify_releases
                    result = (list_releases if args.command == "release-list" else verify_releases)(connection, args.project_id)
                elif args.command in ("release-move", "release-rename", "release-publish"):
                    from .releases import move_release, publish
                    result = (publish if args.command == "release-publish" else move_release)(connection, args.release_id, args.output)
                elif args.command == "release-recover":
                    from .releases import recover
                    result = recover(connection, args.operation_id)
                elif args.command == "release-select":
                    from .releases import select_release
                    select_release(connection, args.release_id)
                    result = {"selected": args.release_id}
                elif args.command == "release-reconcile":
                    from .releases import reconcile, plan_relocations
                    if args.from_relocations and args.apply:
                        raise ValueError("Сначала сохраните и согласуйте точный план")
                    result = plan_relocations(connection, read_json(args.data)) if args.from_relocations else reconcile(connection, read_json(args.data), apply=args.apply)
                elif args.command == "package-export":
                    from .releases import export_package
                    result = export_package(connection, args.project_id, args.output)
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
                        from .workspace import snapshot, rows
                        result["participants_card"] = snapshot(connection, row["object_id"])["participants"]
                        result["workspace_entries"] = rows(connection, "SELECT * FROM workspace_entries WHERE project_id=? ORDER BY id", (project_id,))
                    result["agent_context"] = json.loads(result["agent_context"])
                    from .knowledge import default_root, default_index
                    result['knowledge'] = {'root': str(default_root()), 'index': str(default_index(args.db)),
                                           'search_command': 'knowledge-search',
                                           'usage': 'Искать по работам, затем проверить оригинал и применимость; согласованные основания сохранять в agent_context.'}
                    result["pending"] = [dict(r) for r in connection.execute("SELECT * FROM specification_pending WHERE project_id=? AND status='pending' ORDER BY id",(project_id,))]
                    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='work_facts'").fetchone():
                        from .workflow import workflow_context
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
                else:
                    # Таблица выбирается только из фиксированного списка argparse.
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
                if args.command not in ("list", "act-context", "registry-data", "backup", "record-update", "generate",
                                        "fact-summary", "package-matrix", "project-check", "workflow-context", "spec-compare"):
                    log_event(connection, args.command, after={"arguments": {key: str(value) if isinstance(value, Path) else value
                                                                             for key, value in vars(args).items() if key != "db"},
                                                              "result": result})
                if args.command in ("fact-summary", "package-matrix", "project-check", "workflow-context", "spec-compare") and args.output:
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    with args.output.open("x", encoding="utf-8") as handle:
                        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
                    result = {"output": str(args.output.resolve())}
    except (ValueError, sqlite3.Error, OSError, ImportError, RuntimeError) as error:
        if agent_log:
            agent_log.warning('Команда агента %s завершилась ошибкой %s', args.command, type(error).__name__)
        parser.exit(1, f"Ошибка: {error}\n")
    if agent_log:
        agent_log.info('Команда агента %s завершена', args.command)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
