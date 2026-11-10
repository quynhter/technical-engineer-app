"""Позиции спецификации и исполнительные схемы.

Серийные номера сохраняются в одной строке ресурса, по одному на строку текста.
Количество по проекту не считается фактом монтажа.
"""

import math
import sqlite3

from .db import required_text


CATEGORIES = (
    "Шкафы, пульты, клеммные и распределительные коробки",
    "Приборы и средства автоматизации",
    "Материалы для монтажа приборов и средств автоматизации",
    "Кабельная продукция",
)


def quantity(value: float | None, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{label}: требуется число, а не логическое значение")
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError(f"{label}: требуется конечное неотрицательное число") from error
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{label}: требуется конечное неотрицательное число")
    return result


def add_resource(
    connection: sqlite3.Connection, *, project_id: int, name: str, unit: str, category: str,
    spec_num: str | None = None, short_name: str | None = None,
    type_mark: str | None = None,
    serial_numbers: list[str] | None = None, manufacturer: str | None = None,
    supplier: str | None = None, qty_proj: float | None = None,
    qty_fact: float | None = None, unit_weight: float | None = None,
    note: str | None = None,
) -> int:
    if category not in CATEGORIES:
        raise ValueError("Категория ресурса должна быть одной из четырёх: " + "; ".join(CATEGORIES))
    if serial_numbers is not None and not isinstance(serial_numbers, list):
        raise ValueError("Заводские номера передаются списком строк")
    serials = []
    for serial in serial_numbers or []:
        if not isinstance(serial, str):
            raise ValueError("Заводской номер должен быть строкой")
        serials.append(required_text(serial, "заводской номер"))
    cursor = connection.execute(
        "INSERT INTO resources (project_id, spec_num, name, short_name, type_mark, "
        "category, serial_num, manufacturer, supplier, unit, qty_proj, qty_fact, unit_weight, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (project_id, spec_num, required_text(name, "ресурс"), short_name, type_mark,
         category, "\n".join(serials) or None, manufacturer, supplier,
         required_text(unit, "единица измерения"), quantity(qty_proj, "проектное количество"),
         quantity(qty_fact, "фактическое количество"), quantity(unit_weight, "масса"), note),
    )
    return cursor.lastrowid


def add_scheme(
    connection: sqlite3.Connection, *, project_id: int, num: str, name: str,
    ref_code: str | None = None, sheets_count: int | None = None, note: str | None = None,
) -> int:
    if sheets_count is not None and (
        isinstance(sheets_count, bool) or not isinstance(sheets_count, int) or sheets_count <= 0
    ):
        raise ValueError("Количество листов должно быть положительным целым числом")
    cursor = connection.execute(
        "INSERT INTO schemes (project_id, num, name, ref_code, sheets_count, note) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (project_id, required_text(num, "номер схемы"), required_text(name, "название схемы"),
         ref_code, sheets_count, note),
    )
    return cursor.lastrowid


def document_resource(connection, resource):
    """Количество для документов: внесённый итог либо подтверждённые приросты."""
    result = dict(resource)
    if result['qty_fact'] is not None:
        return result
    facts = list(connection.execute("SELECT quantity,unit FROM work_facts WHERE resource_id=? AND status='confirmed'", (result['id'],)))
    if facts and all(f['quantity'] is not None and f['unit'] == result['unit'] for f in facts):
        result['qty_fact'] = math.fsum(f['quantity'] for f in facts)
    return result
