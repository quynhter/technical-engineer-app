"""Титульники TitleGenerator: настройки в fields, реквизиты из текущей БД."""

import json
import math

from .fields import source_path

CODE = "ТИТУЛЬНЫЙ_ЛИСТ"
NAME = "Титульный лист исполнительной документации и наклейки"
ROLES = {"client": "Заказчик", "tech_client": "Технический_заказчик",
         "gen_contractor": "Генподрядчик", "sub_contractor": "Подрядчик"}
SOURCES = {"object": "object.name", "project": "project.name", "cifr": "project.code",
           "city": "project.city", **{k: f"organizations.{v}.full_name" for k, v in ROLES.items()}}
FONTS = ("Arial", "GOST type B")


def integer(value, name, low, high):
    # Старый GTK SpinButton сохранял целые значения как f64.
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or int(value) != value or not low <= value <= high):
        raise ValueError(f"{name}: требуется целое число от {low} до {high}")
    return int(value)


def settings(data):
    if not isinstance(data, dict):
        raise ValueError("Настройки титульника должны быть JSON-объектом")
    unknown = set(data) - {*SOURCES, "year", "copies", "volumes", "font", "font_index", "labels", "roles"}
    if unknown:
        raise ValueError("Неизвестные настройки титульника: " + ", ".join(sorted(unknown)))
    font = data.get("font")
    index = integer(data.get("font_index", 0), "font_index", 0, 1)
    if font == "GOST Type B":
        font = FONTS[1]
    if font is None:
        font = FONTS[index]
    if font not in FONTS or ("font_index" in data and font != FONTS[index]):
        raise ValueError("Шрифт: Arial или GOST type B; font и font_index должны совпадать")
    labels = data.get("labels", True)
    if not isinstance(labels, bool):
        raise ValueError("labels должен быть true или false")
    year = data.get("year")
    return {"year": integer(year, "year", 1900, 2100) if year is not None else None,
            "copies": integer(data.get("copies", 1), "copies", 1, 50),
            "volumes": integer(data.get("volumes", 1), "volumes", 1, 50),
            "font": font, "labels": labels}


def default_fields():
    return ([{"key": key, "kind": "reference", "source": source,
              "required": key in ("object", "project", "cifr", "city"), "value_type": "text"}
             for key, source in SOURCES.items()]
            + [{"key": key, "kind": "literal", "value": value, "required": key == "year"}
               for key, value in settings({}).items()])


def prepare_context(context):
    # Проверяется и при повторном выпуске после record-update.
    options = settings({key: context[key] for key in ("copies", "volumes", "font", "labels")})
    year = context.get("year")
    if year not in (None, "", "[УТОЧНИТЬ]"):
        context["year"] = integer(year, "year", 1900, 2100)
    context.update(options | {"year": context.get("year", "")})
    context["contractors_info"] = " | ".join(context.get(key, "") for key in
                                             ("gen_contractor", "sub_contractor") if context.get(key))
    context["pages"] = [
        {"duplicates": "Оригинал" if copy == 1 else f"{copy} экз.",
         "volumes_info": f"Том {volume} из {options['volumes']}" if options["volumes"] > 1 else ""}
        for copy in range(1, options["copies"] + 1)
        for volume in range(1, options["volumes"] + 1)
    ]
    return context


def add_title(connection, project_id, data):
    from .acts import add_act, register_form
    from .fields import lookup
    from .participants import participants_context

    options = settings(data)
    project = connection.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if project is None:
        raise ValueError("Раздел РД не найден")
    roots = {"project": dict(project), "object": dict(connection.execute(
        "SELECT * FROM objects WHERE id=?", (project["object_id"],)).fetchone()),
        **participants_context(connection, project_id)}
    roles = data.get("roles", {})
    if not isinstance(roles, dict) or set(roles) - set(ROLES):
        raise ValueError("roles: допустимы client, tech_client, gen_contractor, sub_contractor")
    sources = dict(SOURCES)
    for key, role in roles.items():
        if not isinstance(role, str) or not source_path(role) or "." in role:
            raise ValueError("Роль должна быть одним идентификатором без пробелов и точек")
        sources[key] = f"organizations.{role}.full_name"
    conflicts = []
    for key, source in sources.items():
        if key not in data:
            continue
        supplied = data[key]
        if not isinstance(supplied, str):
            raise ValueError(f"{key}: требуется строка")
        if supplied and supplied != lookup(source, roots):
            conflicts.append(key)
    if conflicts:
        raise ValueError("Конфигурация отличается от БД: " + ", ".join(conflicts)
                         + ". Сначала согласуйте реквизиты/назначения либо выберите точные roles")
    defaults = default_fields()
    registered = connection.execute("SELECT * FROM document_types WHERE code=?", (CODE,)).fetchone()
    if registered and (json.loads(registered["fields"]) != defaults or registered["form_group"] != "act"
                       or registered["name"] != NAME or registered["filename_title"] != "Титульные листы и наклейки"):
        raise ValueError("Форма титульника уже настроена иначе: согласуйте её изменение")
    if not registered:
        register_form(connection, code=CODE, name=NAME, fields=defaults,
                      filename_title="Титульные листы и наклейки")
    fields = [{"key": key, "kind": "literal", "value": value, "required": key == "year"}
              for key, value in options.items()]
    fields += [{**field, "source": sources[field["key"]]} for field in defaults
               if field["key"] in roles]
    act_id = add_act(connection, project_id=project_id, act_type=CODE, fields=fields)
    return {"act_id": act_id, "act_type": CODE, "settings": options}


def export_config(connection, act_id):
    from .acts import build_context
    from .fields import merge_fields
    row = connection.execute("SELECT a.*,t.fields AS defaults FROM acts a JOIN document_types t ON t.code=a.act_type WHERE a.id=?", (act_id,)).fetchone()
    if row is None or row["act_type"] != CODE:
        raise ValueError("Титульник не найден")
    context = build_context(connection, act_id)["context"]
    # Не сохраняем маркер черновика как деловое значение.
    result = {key: ("" if context[key] == "[УТОЧНИТЬ]" else context[key]) for key in SOURCES}
    result.update({key: context[key] for key in ("year", "copies", "volumes", "labels")})
    if result["year"] == "[УТОЧНИТЬ]":
        result["year"] = None
    result["font_index"] = FONTS.index(context["font"])
    result["roles"] = {}
    for field in merge_fields(json.loads(row["defaults"]), json.loads(row["fields"])):
        if field["key"] in ROLES:
            parts = field.get("source", "").split(".")
            if len(parts) != 3 or parts[0] != "organizations" or parts[2] != "full_name":
                raise ValueError("Нельзя экспортировать нестандартный источник участника")
            result["roles"][field["key"]] = parts[1]
    return result
