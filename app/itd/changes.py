"""Однозначные правки одной записи с проверкой и журналом до/после."""

import json

from .db import DATE_FIELDS, calendar_date, required_text
from .fields import validate_fields
from .resources import CATEGORIES, quantity


EDITABLE = {
    "releases": {"sheets_count"},
    "objects": {"name", "construction_type", "city", "address", "permit_num", "permit_date", "permit_authority",
                "expertise_num", "expertise_date", "expertise_authority", "work_start", "work_end", "gsn_case",
                "developer_functions", "control_self", "control_external", "author_supervision"},
    "projects": {"code", "name", "city", "gip", "inv_num", "contract_num", "contract_date", "form_set", "agent_context", *DATE_FIELDS},
    "resources": {"spec_num", "name", "short_name", "type_mark", "category", "serial_num", "manufacturer", "supplier",
                  "unit", "qty_proj", "qty_fact", "unit_weight", "note"},
    "schemes": {"num", "ref_code", "name", "sheets_count", "note"},
    "organizations": {"full_name", "short_name", "ogrn", "inn", "address", "phone", "sro_info", "postal_code", "email", "sro_ogrn", "sro_inn", "sro_certificate_num", "sro_certificate_date"},
    "signatories": {"org_id", "fio", "position", "last_name", "first_name", "middle_name", "order_doc", "order_attachment_id", "nrs_id", "status", "note", "email", "authority_type", "authority_num", "authority_date"},
    "acts": {"date_signed", "is_active", "fields", "sheets_count", "registry_note", "filename_title"},
    "attachments": {"title", "doc_num", "doc_date", "sheets_count", "note"},
}
EDITABLE['objects'].add('display_name')
EDITABLE['projects'].update(('unit_id','designer_org_id'))


def log_event(connection, operation, *, entity=None, entity_id=None, before=None, after=None):
    encode = lambda value: json.dumps(value, ensure_ascii=False, allow_nan=False) if value is not None else None
    connection.execute("INSERT INTO audit_events (operation, entity, entity_id, before_json, after_json) VALUES (?, ?, ?, ?, ?)",
                       (operation, entity, entity_id, encode(before), encode(after)))


def update_record(connection, *, entity, record_id, changes, expected=None):
    if entity not in EDITABLE or not isinstance(changes, dict) or not changes or set(changes) - EDITABLE[entity]:
        raise ValueError("Неверная сущность или недопустимые поля изменения")
    row = connection.execute(f"SELECT * FROM {entity} WHERE id=?", (record_id,)).fetchone()
    if row is None:
        raise ValueError("Запись не найдена")
    before = dict(row)
    if expected is not None:
        if not isinstance(expected, dict) or any(key not in before or before[key] != value for key, value in expected.items()):
            raise ValueError("Запись уже изменена или не соответствует ожидаемым значениям")
    if entity=='resources' and 'unit' in changes and changes['unit']!=before['unit'] and connection.execute('SELECT 1 FROM work_materials WHERE resource_id=?',(record_id,)).fetchone():
        raise ValueError('Единица ресурса уже используется в расходе работ')
    if entity=='acts' and set(changes)&{'fields','date_signed'} and connection.execute("SELECT 1 FROM act_execution_status WHERE act_id=? AND state='signed'",(record_id,)).fetchone():
        raise ValueError('Верните подписанный акт в подготовку перед изменением')
    normalized = dict(changes)
    for field, value in normalized.items():
        if field in DATE_FIELDS or field in ("date_signed", "doc_date", "contract_date", "permit_date", "expertise_date", "work_start", "work_end", "authority_date", "sro_certificate_date"):
            normalized[field] = calendar_date(value)
        elif field in ("qty_proj", "qty_fact", "unit_weight"):
            normalized[field] = quantity(value, field)
        elif field == "category" and value not in CATEGORIES:
            raise ValueError("Неверная категория ресурса")
        elif field == "filename_title" and value is not None:
            from .layout import filename_title
            if not isinstance(value,str):raise ValueError("Название файла: требуется текст")
            normalized[field] = filename_title(value)
        elif field == "fields":
            normalized[field] = json.dumps(validate_fields(value), ensure_ascii=False, allow_nan=False)
        elif field == "agent_context":
            if not isinstance(value, dict):
                raise ValueError("agent_context должен быть JSON-объектом")
            normalized[field] = json.dumps(value, ensure_ascii=False, allow_nan=False)
        elif field == "sheets_count" and value is not None:
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError("Количество листов должно быть положительным целым числом")
        elif field in ("control_self", "control_external", "author_supervision"):
            if type(value) not in (bool, int) or value not in (0, 1):
                raise ValueError("Флажок должен иметь значение 0 или 1")
        elif field == "is_active" and (type(value) not in (bool, int) or value not in (0, 1)):
            raise ValueError("is_active должен быть 0 или 1")
        elif field == "status" and value not in ("Действует", "Отозван"):
            raise ValueError("Неизвестный статус подписанта")
        elif field in ("name", "full_name", "fio", "position", "unit", "code", "num", "title"):
            if not isinstance(value, str):
                raise ValueError(f"{field}: требуется текст")
            normalized[field] = required_text(value, field)
        elif value is not None and field not in ("org_id", "order_attachment_id", "unit_id", "designer_org_id") and not isinstance(value, str):
            raise ValueError(f"{field}: требуется текст или null")
    if entity == "signatories" and normalized.get("order_attachment_id") is not None:
        order = connection.execute("SELECT doc_type FROM attachments WHERE id=?", (normalized["order_attachment_id"],)).fetchone()
        if order is None or order["doc_type"] != "order":
            raise ValueError("Нужен файл типа order")
    if entity == "objects":
        combined = {**before, **normalized}
        if combined["construction_type"] not in (None, "Строительство", "Реконструкция", "Капитальный ремонт", "Прочее"):
            raise ValueError("Неизвестный тип строительства")
        if combined["developer_functions"] not in (None, "self", "technical_customer"):
            raise ValueError("Неизвестная схема функций застройщика")
        if combined["work_start"] and combined["work_end"] and combined["work_start"] > combined["work_end"]:
            raise ValueError("Дата начала работ позже даты окончания")
    if entity == "projects":
        combined = {**before, **normalized}
        if combined.get('unit_id') is not None:
            unit = connection.execute('SELECT object_id FROM object_units WHERE id=?',(combined['unit_id'],)).fetchone()
            if unit is None or unit[0]!=combined['object_id']: raise ValueError('Часть объекта относится к другому объекту')
        if combined.get('designer_org_id') is not None:
            org_id=combined['designer_org_id']
            if not connection.execute('''SELECT 1 FROM object_participants WHERE object_id=? AND org_id=?
                UNION SELECT 1 FROM organization_assignments WHERE (object_id=? OR project_id=?) AND org_id=?''',
                (combined['object_id'],org_id,combined['object_id'],record_id,org_id)).fetchone():
                raise ValueError('Разработчик не назначен на объект или раздел')
        for prefix in ("smr", "pnr"):
            start, end = combined[prefix + "_start"], combined[prefix + "_end"]
            if start and end and start > end:
                raise ValueError("Начало работ раздела позже окончания")
    assignments = ", ".join(f"{field}=?" for field in normalized)
    connection.execute(f"UPDATE {entity} SET {assignments} WHERE id=?", (*normalized.values(), record_id))
    after = dict(connection.execute(f"SELECT * FROM {entity} WHERE id=?", (record_id,)).fetchone())
    log_event(connection, "record-update", entity=entity, entity_id=record_id, before=before, after=after)
    return {"before": before, "after": after}
