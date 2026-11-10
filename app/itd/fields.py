"""Проверка и разрешение упорядоченных полей формы без исполнения кода."""

from datetime import date
import re
import math
from string import Formatter

from .db import calendar_date


KEY = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
PATH_KEY = re.compile(r"(?:[^\W\d]|_)\w*\Z")
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря")
FORMATS = {None, "date_ru", "day_2digits", "month_genitive_ru", "year_4digits"}
PRESENTATIONS = {
    "fio": "{signatory.fio}",
    "fio_short": "{signatory.fio_short}",
    "position_org_fio": "{signatory.position} {organization.short_name} {signatory.fio}",
    "position_org_fio_nrs": "{signatory.position} {organization.short_name} {signatory.fio}, номер в НРС №{signatory.nrs_id}",
}


SEMANTIC_SOURCES = {
    'Object.City': 'object.city',
    'Object.Name': 'object.name',
    'Project.ShortName': 'project.section_code',
    'Project.Name': 'project.name',
    'Project.Cipher': 'project.code',
}
PARTICIPANT_SOURCE = re.compile(
    r'(?P<entity>Organisation|Representative)\.(?P<identity>Id|[1-9][0-9]*)\.'
    r'(?P<attribute>Name|Inn|ShortName|Position|Organisation\.ShortName)'
    r'(?:~default=(?P<role>[A-Za-z_][A-Za-z_0-9]*))?\Z'
)
PARTICIPANT_ATTRIBUTES = {
    'Organisation': {'Name': 'full_name', 'Inn': 'inn', 'ShortName': 'short_name'},
    'Representative': {'Name': 'fio', 'Position': 'position', 'Organisation.ShortName': 'organization.short_name'},
}


def source_path(value):
    if not isinstance(value, str):
        return False
    match = PARTICIPANT_SOURCE.fullmatch(value)
    if match:
        return match['attribute'] in PARTICIPANT_ATTRIBUTES[match['entity']]
    return all(PATH_KEY.fullmatch(part) for part in value.split("."))


def validate_fields(fields):
    if not isinstance(fields, list):
        raise ValueError("fields должен быть упорядоченным JSON-массивом")
    keys = set()
    for field in fields:
        if not isinstance(field, dict) or not isinstance(field.get("key"), str) or not KEY.fullmatch(field["key"]):
            raise ValueError("Каждому полю нужен корректный key латиницей")
        if field["key"] in keys:
            raise ValueError(f"Повтор поля: {field['key']}")
        keys.add(field["key"])
        if field.get("state") not in (None, "hidden", "not_applicable"):
            raise ValueError("Неизвестное состояние поля")
        if field.get("state") == "not_applicable" and not field.get("reason"):
            raise ValueError("Для неприменимого поля укажите reason")
        if field.get("kind") not in ("literal", "reference", "table", "signatory"):
            raise ValueError(f"Неизвестный kind поля {field['key']}")
        if not isinstance(field.get("required", False), bool):
            raise ValueError("required должен быть логическим значением")
        if field.get("format") not in FORMATS:
            raise ValueError(f"Неизвестный формат: {field.get('format')}")
        if field.get("value_type") not in (None, "text", "date", "number"):
            raise ValueError("Неизвестный тип значения")
        if field["kind"] in ("reference", "table"):
            if field["kind"] == "table" and "value" in field:
                if "source" in field:
                    raise ValueError("Таблица должна задавать только source или value")
                if field["value"] is not None and not isinstance(field["value"], list):
                    raise ValueError("value таблицы должен быть массивом или null")
                validate_fields(field.get("fields"))
                continue
            source = field.get("source")
            if not source_path(source):
                raise ValueError(f"Неверный источник поля {field['key']}")
        if field["kind"] == "table":
            validate_fields(field.get("fields"))
        if field["kind"] == "signatory":
            if not isinstance(field.get("role"), str) or not field["role"].strip():
                raise ValueError("Для подписанта требуется роль")
            pattern = field.get("template", PRESENTATIONS.get(field.get("presentation", "fio")))
            if not isinstance(pattern, str):
                raise ValueError("Неизвестное представление подписанта")
            for _, name, spec, conversion in Formatter().parse(pattern):
                if name is not None and (not source_path(name) or spec or conversion):
                    raise ValueError("В представлении разрешены только ссылки вида {signatory.fio}")
    return fields


def merge_fields(defaults, overrides):
    validate_fields(defaults)
    validate_fields(overrides)
    result = {field["key"]: field for field in defaults}
    for field in overrides:
        result[field["key"]] = field
    return list(result.values())


def lookup(source, roots):
    source = SEMANTIC_SOURCES.get(source, source)
    value = roots
    match = PARTICIPANT_SOURCE.fullmatch(source)
    if match:
        entity, identity, attribute, role = (match[k] for k in ('entity', 'identity', 'attribute', 'role'))
        value = roots.get('participant_ids', {}).get(entity, {}).get(identity)
        if not value and role:
            collection = 'organizations' if entity == 'Organisation' else 'signatories'
            value = roots.get(collection, {}).get(role)
        source = PARTICIPANT_ATTRIBUTES[entity].get(attribute, '')
    for component in source.split("."):
        if not isinstance(value, dict) or component not in value:
            return None
        value = value[component]
    return value


def signatory_value(field, roots, draft, path):
    person = roots.get("signatories", {}).get(field["role"])
    if person is None:
        return None, []
    pattern = field.get("template", PRESENTATIONS.get(field.get("presentation", "fio")))
    pieces = []
    missing = []
    for literal, name, _, _ in Formatter().parse(pattern):
        pieces.append(literal)
        if name is not None:
            value = lookup(name, {"signatory": person, "organization": person.get("organization", {})})
            if value is None or value == "":
                if field.get("required", False):
                    missing.append(path + "." + name)
                value = "[УТОЧНИТЬ]" if draft and field.get("required", False) else ""
            pieces.append(str(value))
    return "".join(pieces), missing


def formatted(value, field):
    if value is None or value == "":
        return value
    fmt = field.get("format")
    if field.get("value_type") == "number" and (
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
    ):
        raise ValueError("Числовое поле должно содержать конечное число")
    if field.get("value_type") == "text" and not isinstance(value, str):
        raise ValueError("Текстовое поле должно содержать строку")
    if fmt is not None or field.get("value_type") == "date":
        if not isinstance(value, str):
            raise ValueError("Значение даты должно быть строкой ГГГГ-ММ-ДД")
        value = calendar_date(value)
        parsed = date.fromisoformat(value)
        return {
            None: value, "date_ru": parsed.strftime("%d.%m.%Y"),
            "day_2digits": f"{parsed.day:02}", "month_genitive_ru": MONTHS[parsed.month - 1],
            "year_4digits": f"{parsed.year:04}",
        }[fmt]
    return value


def resolve_fields(fields, roots, *, draft=True, prefix="", diagnostics=None):
    """Вернуть контекст и список пропусков; обязательные пропуски блокируют финал."""
    validate_fields(fields)
    context = {}
    roots={**roots,"field_values":context}
    missing = []
    for field in fields:
        key = field["key"]
        path = prefix + key
        if field.get("state") in ("hidden", "not_applicable"):
            context[key] = [] if field["kind"] == "table" else ""
            if diagnostics is not None:
                diagnostics.append({"path": path, "state": field["state"], "reason": field.get("reason")})
            continue
        if field["kind"] == "signatory":
            value, gaps = signatory_value(field, roots, draft, path)
            missing.extend(gaps)
            if diagnostics is not None:
                diagnostics.extend({"path": gap, "label": field.get("label", key), "required": True,
                                    "source": "signatories." + field["role"], "state": "missing"} for gap in gaps)
        else:
            value = field.get("value") if field["kind"] == "literal" or (
                field["kind"] == "table" and "value" in field
            ) else lookup(field["source"], roots)
        if field["kind"] == "table":
            if value is not None and not isinstance(value, list):
                raise ValueError(f"Источник таблицы {path} должен содержать массив")
            rows = []
            for index, item in enumerate(value or [], 1):
                if not isinstance(item, dict):
                    raise ValueError(f"Строка {path} должна быть объектом")
                row, gaps = resolve_fields(field["fields"], {**roots, "item": item, "row": {"number": index}},
                                           draft=draft, prefix=f"{path}[{index}].", diagnostics=diagnostics)
                rows.append(row)
                missing.extend(gaps)
            value = rows
        else:
            value = formatted(value, field)
        empty = value is None or value == "" or value == [] or (isinstance(value, str) and not value.strip())
        if empty:
            if diagnostics is not None:
                diagnostics.append({"path": path, "label": field.get("label", key),
                                    "required": field.get("required", False), "state": "missing" if field.get("required", False) else "optional_empty",
                                    "source": field.get("source", "signatories." + field["role"] if field.get("role") else "literal"),
                                    "row_source": roots.get("item", {}).get("_source")})
            if field.get("required", False):
                missing.append(path)
            if field["kind"] != "table":
                value = "[УТОЧНИТЬ]" if draft and field.get("required", False) else ""
            elif draft and field.get("required", False):
                placeholder, _ = resolve_fields(field["fields"], {**roots, "item": {}, "row": {}}, draft=True)
                value = [placeholder]
            else:
                value = []
        context[key] = value
    if missing and not draft:
        raise ValueError("Не заполнены обязательные поля: " + ", ".join(missing))
    return context, missing


RESOURCE_SOURCES = {'resources', 'materials', 'work_materials', 'facts'}


def uses_resource_sources(fields):
    for field in fields:
        if field.get('state') in ('hidden', 'not_applicable'):
            continue
        if field.get('source', '').partition('.')[0] in RESOURCE_SOURCES:
            return True
        if field.get('kind') == 'table' and uses_resource_sources(field['fields']):
            return True
    return False
