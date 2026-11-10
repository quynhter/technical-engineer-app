"""Порядок документов комплекта и данные реестра для DOCX-шаблона."""

from datetime import date
import json

from .fields import merge_fields


GROUP_RANK = {"registry": 0, "order": 1, "act": 2, "statement": 3,
              "certificate": 4, "passport": 4, "scheme": 5, "other": 5, "rd": 6, "quality": 4, "contract": 5, "journal": 3}


def _references_number(fields):
    for field in fields:
        if field.get("state") in ("hidden", "not_applicable"):
            continue
        if field.get("source") == "act.act_num":
            return True
        if field.get("kind") == "table" and _references_number(field["fields"]):
            return True
    return False


def registry_rows(connection, project_id, *, registry_act_id=None, detailed=False):
    project = connection.execute("SELECT object_id, code FROM projects WHERE id=?", (project_id,)).fetchone()
    if project is None:
        raise ValueError("Раздел не найден")
    if registry_act_id is not None:
        selected = connection.execute(
            "SELECT 1 FROM acts a JOIN document_types t ON t.code=a.act_type "
            "WHERE a.id=? AND a.project_id=? AND a.is_active=1 AND t.form_group='registry'", (registry_act_id, project_id)
        ).fetchone()
        if selected is None:
            raise ValueError("Выбранный реестр не является активным реестром этого раздела")
    rows = []
    for act in connection.execute(
        "SELECT a.*, t.name AS type_name, t.form_group, t.fields AS form_fields, j.entry_kind, j.work_type FROM acts a "
        "JOIN document_types t ON t.code=a.act_type LEFT JOIN act_journals j ON j.act_id=a.id WHERE a.project_id=? AND a.is_active=1 ORDER BY a.id", (project_id,)
    ):
        # При формировании конкретного реестра его прежние альтернативные
        # экземпляры не включаются отдельными первыми строками.
        if act["form_group"] == "registry" and (detailed or registry_act_id is not None and act["id"] != registry_act_id):
            continue
        definitions = merge_fields(json.loads(act["form_fields"]), json.loads(act["fields"]))
        note = act["registry_note"] or ""
        document_date = act["date_signed"]
        if act["entry_kind"]:
            from .manual import entry_rows
            entries = entry_rows(connection, project_id, act["entry_kind"], act["work_type"])
            if not entries:
                continue
            document_date = entries[0]["entry_date"]
        if document_date is None:
            note = (note + "; " if note else "") + "Дата не указана"
        rows.append({"entity": "act", "id": act["id"], "name": act["type_name"],
                     "number": act["act_num"] if _references_number(definitions) else "",
                     "date": document_date, "sheets_count": act["sheets_count"],
                     "note": note, "group": act["form_group"]})
    attachment_ids = set()
    queries = [
        ("SELECT attachment_id FROM object_attachments WHERE object_id=?", project["object_id"]),
        ("SELECT attachment_id FROM project_attachments WHERE project_id=?", project_id),
        ("SELECT ra.attachment_id FROM resource_attachments ra JOIN resources r ON r.id=ra.resource_id WHERE r.project_id=?", project_id),
        ("SELECT sa.attachment_id FROM scheme_attachments sa JOIN schemes s ON s.id=sa.scheme_id WHERE s.project_id=?", project_id),
        ("SELECT aa.attachment_id FROM act_attachments aa JOIN acts a ON a.id=aa.act_id WHERE a.project_id=? AND a.is_active=1", project_id),
    ]
    for query, value in queries:
        attachment_ids.update(row[0] for row in connection.execute(query, (value,)))
    # Приказы действующих назначенных подписантов также входят в комплект.
    from .participants import participants_context
    for signer in participants_context(connection, project_id)["signatories"].values():
        if signer and signer["order_attachment_id"]:
            attachment_ids.add(signer["order_attachment_id"])
    import_sources = {row[0] for row in connection.execute(
        "SELECT attachment_id FROM resource_imports WHERE project_id=? AND attachment_id IS NOT NULL",
        (project_id,))}
    for attachment_id in sorted(attachment_ids - import_sources):
        doc = connection.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,)).fetchone()
        note = doc["note"] or ""
        if doc["doc_date"] is None:
            note = (note + "; " if note else "") + "Дата не указана"
        group = doc["file_kind"] or doc["doc_type"]
        name = f'Рабочая документация «{project["code"]}»' if group == "rd" else doc["title"]
        rows.append({"entity": "attachment", "id": doc["id"], "name": name,
                     "number": doc["doc_num"] or "", "date": doc["doc_date"],
                     "sheets_count": doc["sheets_count"], "note": note, "group": group})
    if detailed:
        for scheme in connection.execute('SELECT * FROM schemes WHERE project_id=?', (project_id,)):
            linked = connection.execute(
                'SELECT a.id, a.doc_date FROM scheme_attachments s JOIN attachments a ON a.id=s.attachment_id WHERE s.scheme_id=?',
                (scheme['id'],)).fetchall()
            if len(linked) == 1:
                rows = [row for row in rows if not (row['entity'] == 'attachment' and row['id'] == linked[0]['id'])]
            rows.append({'entity': 'scheme', 'id': scheme['id'], 'name': scheme['name'],
                         'number': scheme['num'], 'date': linked[0]['doc_date'] if len(linked) == 1 else None,
                         'sheets_count': scheme['sheets_count'], 'note': scheme['note'], 'group': 'scheme'})
    from .journals import automatic_journals
    for journal in automatic_journals(connection, project_id):
        if journal["project_id"] != project_id:
            continue
        rows.append({"entity": "journal", "id": journal["kind"], "name": journal["name"],
                     "number": "", "date": journal["date"], "sheets_count": None,
                     "note": "" if journal["date"] else "Дата не указана", "group": "journal"})
    def order(row):
        return (row["group"] != "registry", row["date"] is None, row["date"] or "",
                GROUP_RANK.get(row["group"], 99), row["entity"], row["id"])
    rows.sort(key=order)
    if detailed:
        page = 1
        for row in rows:
            sheets = row['sheets_count']
            row['pages'] = str(page) if page and sheets == 1 else (
                f'{page}–{page + sheets - 1}' if page and sheets else '')
            page = page + sheets if page and sheets else None
            date_text = date.fromisoformat(row['date']).strftime('%d.%m.%Y') if row['date'] else ''
            row['number_date'] = ' · '.join(part for part in (row['number'], date_text) if part)
            row['organization'] = ''
            if row['entity'] == 'act':
                organizations = connection.execute(
                    """SELECT DISTINCT o.full_name FROM act_signatories s
                       JOIN signatories p ON p.id=s.signatory_id JOIN organizations o ON o.id=p.org_id
                       WHERE s.act_id=? AND s.role_key IN ('work_performer','builder') ORDER BY o.full_name""",
                    (row['id'],)).fetchall()
                if len(organizations) == 1:
                    row['organization'] = organizations[0][0]
    return [{"no": index, **row} for index, row in enumerate(rows, 1)]
