"""Переносимая структура каталогов ИТД."""

import re
import json
import hashlib
import unicodedata
from pathlib import Path


GROUPS = ("01_Реестр", "02_Приказы", "03_Акты", "04_Ведомости",
          "05_Сертификаты и паспорта", "06_РД", "07_Схемы")
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                    *(f"LPT{i}" for i in range(1, 10))}


def path_component(value, *, preserve_end=False, max_bytes=180):
    value = unicodedata.normalize("NFC", value)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip().rstrip(". ")
    if not value or value in (".", ".."):
        raise ValueError("Пустое имя каталога после удаления недопустимых символов")
    if value.split(".")[0].upper() in WINDOWS_RESERVED:
        value = "_" + value
    if len(value.encode("utf-8")) > max_bytes:
        tail = "~" + hashlib.sha256(value.encode()).hexdigest()[:10]
        if preserve_end:
            budget=max_bytes-len(tail)-1
            start=round(budget*.6)
            raw=value.encode('utf-8')
            value=raw[:start].decode('utf-8',errors='ignore')+tail+'~'+raw[-(budget-start):].decode('utf-8',errors='ignore')
        else:
            value = value.encode("utf-8")[:max_bytes-len(tail)].decode("utf-8", errors="ignore").rstrip(". ") + tail
    return value


def check_path(path):
    """Общий переносимый предел: компонент 255 байт, полный путь 240 UTF-16 единиц."""
    path = Path(path).absolute()
    if len(str(path).encode("utf-16-le")) // 2 > 240 or len(str(path).encode()) > 4000:
        raise ValueError("Слишком длинный полный путь: сократите корневой каталог или имя")
    for part in path.parts[1:]:
        if len(part.encode()) > 255:
            raise ValueError("Слишком длинный компонент пути")
        if path_component(part) != part:
            raise ValueError("Компонент пути несовместим с переносимым именем: " + part)
    return path


def project_directory(connection, project_id, root):
    project = connection.execute(
        "SELECT p.section_code, o.id AS object_id, o.name FROM projects p JOIN objects o ON o.id=p.object_id WHERE p.id=?", (project_id,)
    ).fetchone()
    if project is None:
        raise ValueError("Раздел РД не найден")
    root = Path(root).resolve()
    folder = root / path_component(project["name"]) / path_component(project["section_code"])
    check_path(folder / max(GROUPS, key=len))
    if not folder.resolve().is_relative_to(root):
        raise ValueError("Каталог находится вне корня ИТД")
    for directory, marker_name, identity in (
        (folder.parent, ".itd-object.json", {"object_id": project["object_id"]}),
        (folder, ".itd-project.json", {"project_id": project_id}),
    ):
        directory.mkdir(parents=True, exist_ok=True)
        marker = directory / marker_name
        if marker.exists():
            if json.loads(marker.read_text(encoding="utf-8")) != identity:
                raise ValueError(f"Каталог уже закреплён за другим объектом или разделом: {directory}")
        else:
            with marker.open("x", encoding="utf-8") as handle:
                json.dump(identity, handle, ensure_ascii=False)
    return folder


def create_layout(connection, project_id, root):
    root = Path(root).resolve()
    folder = project_directory(connection, project_id, root)
    for group in GROUPS:
        target = folder / group
        if not target.resolve().is_relative_to(root):
            raise ValueError("Ссылка каталога ведёт вне корня ИТД")
        target.mkdir(parents=True, exist_ok=True)
    for name in ('Черновики', 'Выдача'):
        target = folder / '03_Акты' / name
        check_path(target)
        if not target.resolve().is_relative_to(root):
            raise ValueError("Ссылка каталога ведёт вне корня ИТД")
        target.mkdir(parents=True, exist_ok=True)
    return {"directory": str(folder), "groups": list(GROUPS)}


def filename_title(value):
    """Переносимое короткое имя документа без расширения."""
    try:
        return path_component(value.strip() or 'Документ', max_bytes=160)
    except ValueError:
        return 'Документ'
