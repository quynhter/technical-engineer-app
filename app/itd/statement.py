"""Общая ведомость ресурсов раздела: SQLite → JSON → XLSX."""

import json
import os
import shutil
import subprocess
import tempfile
import math
from copy import copy
from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "Ведомость оборудования и материалов.xlsx"
HEADERS = ["Позиция", "Категория", "Наименование", "Марка, тип", "Заводские номера",
           "Ед. изм.", "Кол-во, по проекту", "Кол-во, по факту", "Документы качества"]


def _layout(payload):
    """Общая оценка переносов для обоих движков, включая объединённую шапку."""
    from openpyxl import load_workbook
    book = load_workbook(TEMPLATE)
    sheet = book.active
    widths = [sheet.sheet_format.defaultColWidth or 13] * 9
    for dim in sheet.column_dimensions.values():
        for index in range(dim.min - 1, min(dim.max, 9)):
            widths[index] = dim.width
    def height(values, spans, minimum):
        lines = max(sum(max(1, math.ceil(len(line) / max(4, width - 2)))
                        for line in str(value if value is not None else "").split("\n"))
                    for value, width in zip(values, spans))
        return max(minimum, lines * 15 + 6)
    result = {"row_heights": [height(row, widths, 28) for row in payload["rows"]],
              "object_height": height([payload["object_name"]], [sum(widths[1:])], 21),
              "section_height": height([payload["section_label"]], [sum(widths[1:])], 21),
              "header_height": height(HEADERS, widths, 32)}
    book.close()
    return result


def _portable_export(payload, target):
    """Резервный движок для окружений без настроенного @oai/artifact-tool."""
    from openpyxl import load_workbook
    book = load_workbook(TEMPLATE)
    sheet = book.active
    layout = payload.get("layout") or _layout(payload)
    for address, value in (("B3", payload["object_name"]), ("B4", payload["section_label"])):
        sheet[address] = value
        sheet[address].data_type = "s"
        alignment = copy(sheet[address].alignment)
        alignment.wrap_text = True
        sheet[address].alignment = alignment
    sheet.row_dimensions[3].height = layout["object_height"]
    sheet.row_dimensions[4].height = layout["section_height"]
    sheet.row_dimensions[6].height = layout["header_height"]
    styles = [copy(sheet.cell(8, col)._style) for col in range(1, 10)]
    for index, row in enumerate(payload["rows"], 8):
        for column, value in enumerate(row, 1):
            cell = sheet.cell(index, column, value)
            cell._style = copy(styles[column - 1])
            if isinstance(value, str):
                cell.data_type = "s"
                cell.number_format = "@"
            elif column in (7, 8):
                cell.number_format = "General"
        sheet.row_dimensions[index].height = layout["row_heights"][index - 8]
    if not payload["rows"]:
        sheet["C8"] = "Ресурсы пока не внесены"
        sheet.row_dimensions[8].height = 28
    sheet.freeze_panes = "A8"
    book.save(target)
    book.close()


def statement_data(connection, project_id):
    project = connection.execute(
        "SELECT p.*, o.name AS object_name FROM projects p JOIN objects o ON o.id=p.object_id WHERE p.id=?", (project_id,)
    ).fetchone()
    if project is None:
        raise ValueError("Раздел не найден")
    from .resources import document_resource
    rows = []
    for resource in connection.execute("SELECT * FROM resources WHERE project_id=? ORDER BY id", (project_id,)):
        resource = document_resource(connection,resource)
        quality = []
        for attachment in connection.execute(
            "SELECT a.* FROM resource_attachments ra JOIN attachments a ON a.id=ra.attachment_id "
            "WHERE ra.resource_id=? AND (a.doc_type IN ('certificate', 'passport') OR a.file_kind='quality') ORDER BY a.doc_date, a.id", (resource["id"],)
        ):
            description = attachment["title"]
            if attachment["doc_num"]:
                description += " №" + attachment["doc_num"]
            if attachment["doc_date"]:
                description += " от " + attachment["doc_date"]
            quality.append(description)
        rows.append([resource["spec_num"],
                     resource["category"], resource["name"], resource["type_mark"], resource["serial_num"],
                     resource["unit"], resource["qty_proj"], resource["qty_fact"], "\n".join(quality) or None])
    return {"project_id": project_id, "section": project["section_code"], "object_name": project["object_name"],
            "project_code": project["code"],
            "section_label": (project["name"] or project["section_code"]) + " (" + project["code"] + ")",
            "headers": HEADERS, "rows": rows}


def export_statement(connection, *, project_id, output, node=None, node_modules=None, preview_dir=None):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Результат уже существует: {output}")
    configured = bool(node or node_modules or os.environ.get("ITD_NODE") or os.environ.get("ITD_NODE_MODULES"))
    executable = node or os.environ.get("ITD_NODE") or shutil.which("node")
    if configured and not executable:
        raise ValueError("Для выбранного XLSX-движка нужен Node.js; задайте --node или ITD_NODE")
    payload = statement_data(connection, project_id)
    payload["template_path"] = str(TEMPLATE)
    payload["layout"] = _layout(payload)
    environment = os.environ.copy()
    if node_modules:
        environment["ITD_NODE_MODULES"] = str(Path(node_modules).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".itd-xlsx-", dir=output.parent) as directory:
        directory = Path(directory)
        data = directory / "input.json"
        data.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        target = directory / "statement.xlsx"
        if configured:
            command = [str(executable), str(Path(__file__).with_name("statement.mjs")), str(data), str(target)]
            if preview_dir:
                command.append(str(Path(preview_dir).resolve()))
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=environment)
            if result.returncode:
                raise ValueError("Ошибка XLSX-движка. Нужен @oai/artifact-tool; проверьте ITD_NODE_MODULES.\n" + result.stderr[-2000:])
        else:
            if preview_dir:
                raise ValueError("Рендер XLSX требует настройки ITD_NODE и ITD_NODE_MODULES")
            _portable_export(payload, target)
        os.link(target, output)
    from .releases import register_release
    release_id = register_release(connection, project_id=project_id, kind="xlsx", title="Общая ведомость ресурсов " + payload["section"], path=output)
    return {"output": str(output), "rows": len(payload["rows"]), "project_id": project_id,
            "engine": "artifact-tool" if configured else "openpyxl", "release_id": release_id}
