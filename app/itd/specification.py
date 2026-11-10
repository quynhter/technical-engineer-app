"""Импорт прочитанных позиций с происхождением и защитой от дублей."""

from .resources import add_resource
import json


def save_pending(connection, project_id, attachment_id, item):
    connection.execute("INSERT INTO specification_pending(project_id,attachment_id,source_key,item_json) VALUES (?,?,?,?) "
                       "ON CONFLICT(project_id,attachment_id,source_key) DO UPDATE SET item_json=excluded.item_json WHERE status='pending'",
                       (project_id,attachment_id,item["source_key"],json.dumps(item,ensure_ascii=False,allow_nan=False)))



def import_specification(connection, *, project_id, attachment_id, items):
    source = connection.execute("SELECT doc_type FROM attachments WHERE id=?", (attachment_id,)).fetchone()
    if source is None or source["doc_type"] != "rd":
        raise ValueError("Сначала зарегистрируйте исходную РД в архиве с типом rd")
    if not isinstance(items, list):
        raise ValueError("Спецификация должна быть JSON-массивом")
    connection.execute("INSERT OR IGNORE INTO project_attachments (project_id, attachment_id) VALUES (?, ?)", (project_id, attachment_id))
    from inspect import signature
    allowed = set(signature(add_resource).parameters) - {"connection", "project_id"}
    report = {"imported": [], "duplicates": [], "pending": []}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("source_key"), str) or not item["source_key"].strip():
            raise ValueError("Каждой позиции нужен source_key — устойчивый идентификатор строки источника")
        existing = connection.execute(
            "SELECT resource_id FROM resource_sources WHERE project_id=? AND attachment_id=? AND source_key=?",
            (project_id, attachment_id, item["source_key"]),
        ).fetchone()
        if existing:
            report["duplicates"].append(existing["resource_id"])
            continue
        if item.get("verified") is not True:
            save_pending(connection, project_id, attachment_id, item)
            report["pending"].append(item["source_key"])
            continue
        data = item.get("resource")
        if not isinstance(data, dict) or set(data) - allowed or not {"name", "unit", "category"} <= set(data):
            raise ValueError("Неверный набор полей resource")
        if data.get("qty_fact") is not None:
            raise ValueError("Из спецификации РД нельзя устанавливать факт монтажа")
        page = item.get("page")
        if page is not None and (isinstance(page, bool) or not isinstance(page, int) or page <= 0):
            raise ValueError("Номер страницы должен быть положительным целым числом")
        # Замена редакции с уже имеющейся позицией требует решения пользователя.
        if data.get("spec_num") and connection.execute(
            "SELECT 1 FROM resources WHERE project_id=? AND spec_num=?", (project_id, data["spec_num"])
        ).fetchone():
            save_pending(connection, project_id, attachment_id, {**item, "reason": "Позиция уже есть: требуется согласование редакции или совпадения"})
            report["pending"].append(item["source_key"])
            continue
        resource_id = add_resource(connection, project_id=project_id, **data)
        connection.execute(
            "INSERT INTO resource_sources (project_id, resource_id, attachment_id, source_key, page, sheet, locator) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, resource_id, attachment_id, item["source_key"], page, item.get("sheet"), item.get("locator")),
        )
        report["imported"].append(resource_id)
        connection.execute("UPDATE specification_pending SET status='resolved' WHERE project_id=? AND attachment_id=? AND source_key=?",
                           (project_id,attachment_id,item["source_key"]))
    return report
