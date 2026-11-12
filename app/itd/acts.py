"""Формы и акты: текущие данные БД разрешаются при каждом формировании."""

import json
from pathlib import Path

from .db import calendar_date, required_text, atomic_operation
from .fields import merge_fields, resolve_fields, validate_fields
from .layout import path_component
from .participants import participants_context, short_fio


def register_form(connection, *, code, name, fields, form_group="act", filename_title=None):
    code = required_text(code, "тип документа")
    # Имя типа одновременно является переносимым именем файла шаблона.
    if path_component(code) != code:
        raise ValueError("Тип документа должен быть допустимым именем файла без расширения")
    validate_fields(fields)
    if form_group not in ("act", "statement", "registry"):
        raise ValueError("Группа формы: act, statement или registry")
    connection.execute(
        "INSERT INTO document_types (code, name, fields, form_group, filename_title) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(code) DO UPDATE SET name=excluded.name, fields=excluded.fields, form_group=excluded.form_group, filename_title=excluded.filename_title",
        (code, required_text(name, "название формы"), json.dumps(fields, ensure_ascii=False, allow_nan=False), form_group, filename_title),
    )


def add_act(connection, *, project_id, act_type, date_signed=None, fields=None):
    fields = [] if fields is None else validate_fields(fields)
    date_signed = calendar_date(date_signed)
    # Проверки до счётчика: неизвестная форма не должна занимать номер.
    project = connection.execute("SELECT section_code FROM projects WHERE id=?", (project_id,)).fetchone()
    if project is None:
        raise ValueError("Раздел РД не найден")
    if not connection.execute("SELECT 1 FROM document_types WHERE code=?", (act_type,)).fetchone():
        raise ValueError("Сначала зарегистрируйте тип документа")
    # SAVEPOINT сохраняет атомарность, в том числе если вызывающий код поймал исключение.
    connection.execute("SAVEPOINT create_act")
    try:
        connection.execute("INSERT OR IGNORE INTO document_counters VALUES (?, 0)", (project_id,))
        connection.execute("UPDATE document_counters SET last_number=last_number+1 WHERE project_id=?", (project_id,))
        number = connection.execute("SELECT last_number FROM document_counters WHERE project_id=?", (project_id,)).fetchone()[0]
        act_num = f"{number:02}/{project['section_code']}"
        cursor = connection.execute(
            "INSERT INTO acts (project_id, act_type, sequence_no, act_num, date_signed, fields) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, act_type, number, act_num, date_signed, json.dumps(fields, ensure_ascii=False, allow_nan=False)),
        )
        connection.execute("RELEASE create_act")
        return cursor.lastrowid
    except Exception:
        connection.execute("ROLLBACK TO create_act")
        connection.execute("RELEASE create_act")
        raise


def set_resources(connection, act_id, resource_ids):
    if connection.execute("SELECT 1 FROM act_execution_status WHERE act_id=? AND state='signed'",(act_id,)).fetchone():
        raise ValueError('Верните подписанный акт в подготовку перед изменением состава')
    if len(resource_ids) != len(set(resource_ids)):
        raise ValueError("Ресурс повторяется в составе акта")
    if not connection.execute("SELECT 1 FROM acts WHERE id=?", (act_id,)).fetchone():
        raise ValueError("Акт не найден")
    connection.execute("SAVEPOINT act_composition")
    try:
        connection.execute("DELETE FROM act_resources WHERE act_id=?", (act_id,))
        connection.executemany("INSERT INTO act_resources (act_id, resource_id, ordinal) VALUES (?, ?, ?)",
                               [(act_id, resource_id, index) for index, resource_id in enumerate(resource_ids, 1)])
        connection.execute("RELEASE act_composition")
    except Exception:
        connection.execute("ROLLBACK TO act_composition")
        connection.execute("RELEASE act_composition")
        raise


def set_schemes(connection, act_id, scheme_ids):
    if connection.execute("SELECT 1 FROM act_execution_status WHERE act_id=? AND state='signed'",(act_id,)).fetchone():
        raise ValueError('Верните подписанный акт в подготовку перед изменением состава')
    if len(scheme_ids) != len(set(scheme_ids)):
        raise ValueError("Схема повторяется в составе акта")
    if not connection.execute("SELECT 1 FROM acts WHERE id=?", (act_id,)).fetchone():
        raise ValueError("Акт не найден")
    connection.execute("SAVEPOINT act_schemes_composition")
    try:
        connection.execute("DELETE FROM act_schemes WHERE act_id=?", (act_id,))
        connection.executemany("INSERT INTO act_schemes (act_id, scheme_id, ordinal) VALUES (?, ?, ?)",
                               [(act_id, scheme_id, index) for index, scheme_id in enumerate(scheme_ids, 1)])
        connection.execute("RELEASE act_schemes_composition")
    except Exception:
        connection.execute("ROLLBACK TO act_schemes_composition")
        connection.execute("RELEASE act_schemes_composition")
        raise


def build_context(connection, act_id, *, draft=True):
    act = connection.execute("SELECT * FROM acts WHERE id=?", (act_id,)).fetchone()
    if act is None:
        raise ValueError("Акт не найден")
    if not act["is_active"]:
        raise ValueError("Акт исключён из активного комплекта")
    project = dict(connection.execute("SELECT * FROM projects WHERE id=?", (act["project_id"],)).fetchone())
    obj = dict(connection.execute("SELECT * FROM objects WHERE id=?", (project["object_id"],)).fetchone())
    form = connection.execute("SELECT * FROM document_types WHERE code=?", (act["act_type"],)).fetchone()
    resources = [dict(row) for row in connection.execute(
        "SELECT r.* FROM act_resources ar JOIN resources r ON r.id=ar.resource_id WHERE ar.act_id=? ORDER BY ar.ordinal",
        (act_id,),
    )]
    from .resources import document_resource
    resources = [document_resource(connection,r) for r in resources]
    from .form_defaults import document_project
    roots = {"act": dict(act), "project": document_project(project, obj), "object": obj, "resources": resources}
    if connection.execute("SELECT 1 FROM sqlite_master WHERE name='act_entry_sources'").fetchone():
        from .manual import source_issues, journal_rows
        issues=source_issues(connection,act_id)
        if issues and not draft: raise ValueError('Источники акта изменились или поставки неприменимы; выполните повторную сверку: '+str(issues))
        roots['entries']=[{**dict(r),'work_fields':json.loads(r['work_fields'])} for r in connection.execute('SELECT e.* FROM workspace_entries e JOIN act_entry_sources s ON s.entry_id=e.id WHERE s.act_id=? ORDER BY e.entry_date,e.id',(act_id,))]
        roots['journal_rows']=journal_rows(connection,act_id)
        roots['materials']=[dict(r) for r in connection.execute('SELECT s.*,m.quantity AS act_quantity FROM act_materials m JOIN supplies s ON s.id=m.supply_id WHERE m.act_id=? ORDER BY s.id',(act_id,))]
        if project.get('unit_id'): roots['unit']=dict(connection.execute('SELECT * FROM object_units WHERE id=?',(project['unit_id'],)).fetchone())
        if project.get('designer_org_id'): roots['section_designer']=dict(connection.execute('SELECT * FROM organizations WHERE id=?',(project['designer_org_id'],)).fetchone())
    for resource in resources:
        resource["_source"] = [dict(row) for row in connection.execute("SELECT attachment_id,source_key,page,sheet,locator FROM resource_sources WHERE resource_id=?", (resource["id"],))]
    roots["schemes"] = [dict(row) for row in connection.execute(
        "SELECT s.* FROM act_schemes a JOIN schemes s ON s.id=a.scheme_id WHERE a.act_id=? ORDER BY a.ordinal", (act_id,))]
    # Старые базы читаются до явного обновления, новые формы могут использовать facts.
    roots["facts"] = []
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='act_facts'").fetchone():
        roots["facts"] = [dict(row) for row in connection.execute(
            "SELECT f.* FROM act_facts af JOIN work_facts f ON af.fact_id=f.id "
            "WHERE af.act_id=? AND f.status='confirmed' ORDER BY f.id", (act_id,))]
    roots.update(participants_context(connection, act["project_id"]))
    from .ojr import act_people,act_work_description,directory,participant_ids,roster
    roots['participant_ids'] = participant_ids(directory(connection, act["project_id"]))
    roots['work_summary']={'description':act_work_description(connection,act_id)}
    selected_people=act_people(connection,act_id)
    execution=connection.execute("SELECT signers_json FROM act_execution_status WHERE act_id=? AND state='signed'",(act_id,)).fetchone()
    if execution:
        selected_people=json.loads(execution['signers_json'])
    elif form['form_group']=='act':
        eligible={person['id'] for person in roster(connection,act['project_id'],act['date_signed'])}
        candidates=selected_people or roots['signatories']
        from .document_versions import candidates as role_candidates
        assigned=role_candidates(connection,act['project_id'])
        if not selected_people:
            for role,choices in role_candidates(connection,act['project_id'],fallback=False).items():
                if len(choices)==1 and role in roots['organizations']:
                    p=choices[0];candidates[role]={**p,'organization':roots['organizations'][role],'fio_short':short_fio(p)}
        selected_people={role:person if person and (person['id'] in eligible or any(p['id']==person['id'] for p in assigned.get(role,[]))) else None for role,person in candidates.items()}
    else:
        selected_people=selected_people or roots['signatories']
    roots['signatories']=selected_people
    roots['organizations'].update({role:person['organization'] for role,person in selected_people.items() if person})
    from .act_participants import apply_organizations
    apply_organizations(connection,act_id,roots)
    from .form_defaults import apply_form_defaults, documentation_context
    roots["project_documentation"] = documentation_context(connection, project, roots["organizations"])
    if form["form_group"] == "registry":
        from .registry import registry_rows
        roots["registry"] = registry_rows(connection, act["project_id"], registry_act_id=act_id, detailed=act["act_type"] == "РЕЕСТР_ИТД")
    fields = apply_form_defaults(act["act_type"], merge_fields(json.loads(form["fields"]), json.loads(act["fields"])))
    diagnostics = []
    context, missing = resolve_fields(fields, roots, draft=draft, diagnostics=diagnostics)
    # Дополнительные участники выбираются в карточке, хотя исходный бланк
    # обычно не содержит строк для них. Передаём только явный выбор акта.
    from .workspace import OTHER_SIGNER_ROLES
    explicit_people = act_people(connection, act_id)
    additional_signatories = [
        {'role': label, 'fio': short_fio(person), 'position': person['position'],
         'organization': person['organization'].get('short_name') or person['organization']['full_name'],
         'authority': person.get('order_doc') or ''}
        for role, label in OTHER_SIGNER_ROLES.items()
        if (person := explicit_people.get(role)) and not any(
            (f.get('role') == role or f.get('source', '').startswith('signatories.' + role + '.'))
            and f.get('state') not in ('hidden', 'not_applicable') for f in fields)
    ]
    if additional_signatories:
        context['_additional_signatories'] = additional_signatories
    from .titles import CODE, prepare_context
    if act["act_type"] == CODE:
        prepare_context(context)
    from .template_objects import CONTEXT_KEY, build_template_context
    template_context = build_template_context(act['act_type'], context, roots=roots, fields=fields)
    if template_context:
        context[CONTEXT_KEY] = template_context
    return {"context": context, "missing": missing, "act_num": act["act_num"],
            "act_type": act["act_type"], "draft": draft, "field_diagnostics": diagnostics}


@atomic_operation
def generate(connection, *, act_id, templates_dir, output, draft=True):
    from .docx_render import render_docx
    from jinja2 import TemplateError
    from .document_versions import prepare_generation
    prepare_generation(connection,act_id)
    prepared = build_context(connection, act_id, draft=draft)
    template = find_template(templates_dir, prepared["act_type"])
    from .archive import digest
    from .changes import log_event
    template_sha = digest(template)
    claims = template_claims(template)
    if not draft and claims:
        review = connection.execute("SELECT * FROM final_reviews WHERE act_id=?", (act_id,)).fetchone()
        if review is None or review["template_sha256"] != template_sha or review["context_sha256"] != context_digest(prepared["context"]):
            raise ValueError("Перед финалом требуется act-review: проверьте статические утверждения шаблона и текущие данные")
    try:
        from .titles import CODE
        render_docx(template, prepared["context"], output, draft=draft,
                    font=prepared["context"]["font"] if prepared["act_type"] == CODE else None)
    except TemplateError as error:
        raise ValueError(f"Ошибка полей или разметки шаблона: {error}") from error
    cursor = connection.execute(
        "INSERT INTO generated_documents (act_id, output_path, sha256, mode, context_json, template_sha256) VALUES (?, ?, ?, ?, ?, ?)",
        (act_id, str(Path(output).resolve()), digest(output), "draft" if draft else "final",
         json.dumps(prepared["context"], ensure_ascii=False, allow_nan=False), template_sha),
    )
    from .releases import register_release
    meta = connection.execute("SELECT a.project_id,t.name FROM acts a JOIN document_types t ON t.code=a.act_type WHERE a.id=?", (act_id,)).fetchone()
    release_id = register_release(connection, project_id=meta["project_id"], act_id=act_id, generated_id=cursor.lastrowid,
                                  kind="docx", title=meta["name"], path=output, mode="draft" if draft else "final")
    from .document_versions import attach_release
    attach_release(connection,act_id,release_id)
    log_event(connection, "generate", entity="acts", entity_id=act_id,
              after={"output": str(Path(output).resolve()), "draft": draft})
    return {**prepared, "output": str(Path(output).resolve()), "release_id": release_id,
            "static_claims_to_review": claims}


def context_digest(context):
    import hashlib
    return hashlib.sha256(json.dumps(context, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def template_claims(template):
    """Подсказки для проверки бланка, а не автоматическая нормативная экспертиза."""
    from docx import Document
    import re
    document = Document(template)
    texts = [p.text for p in document.paragraphs]
    texts += [c.text for t in document.tables for r in t.rows for c in r.cells]
    return list(dict.fromkeys(t for t in texts if re.search(r"соответств|выполнен|поврежден|готов|дефект|испытан|допуска|не обнаруж|удовлетвор", t, re.I)))


def review_act(connection, act_id, templates_dir, note):
    from .archive import digest
    prepared = build_context(connection, act_id, draft=False)
    template = find_template(templates_dir, prepared["act_type"])
    connection.execute("INSERT INTO final_reviews VALUES (?,?,?,?) ON CONFLICT(act_id) DO UPDATE SET template_sha256=excluded.template_sha256,context_sha256=excluded.context_sha256,note=excluded.note",
                       (act_id, digest(template), context_digest(prepared["context"]), required_text(note, "основание проверки")))
    from .changes import log_event
    log_event(connection, "act-review", entity="acts", entity_id=act_id, after={"template_sha256": digest(template), "note": note})
    return {"act_id": act_id, "static_claims": template_claims(template), "reviewed": True}


def find_template(templates_dir, act_type):
    """Найти единственный шаблон типа во всём каталоге, включая подпапки."""
    if path_component(act_type) != act_type:
        raise ValueError("Недопустимый тип документа")
    root = Path(templates_dir).resolve()
    filename = act_type + ".docx"
    matches = sorted(path for path in root.rglob("*.docx")
                     if path.name == filename and path.is_file()
                     and path.resolve().is_relative_to(root))
    if not matches:
        raise ValueError(f"Шаблон не найден: {filename}")
    if len(matches) != 1:
        raise ValueError("Несколько шаблонов одного типа: " + ", ".join(str(p.relative_to(root)) for p in matches))
    return matches[0]
