"""Общий архив оригиналов, проверка целостности и связи с БД."""

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from .db import calendar_date, required_text


DOCUMENT_TYPES = ("order", "certificate", "passport", "rd", "scheme", "other", "contract", "quality")
LINKS = {
    "object": ("object_attachments", "object_id"),
    "project": ("project_attachments", "project_id"),
    "resource": ("resource_attachments", "resource_id"),
    "scheme": ("scheme_attachments", "scheme_id"),
    "act": ("act_attachments", "act_id"),
}


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def archived_path(archive_root, relative):
    root = Path(archive_root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Файл архива находится вне его корня")
    return path


def import_file(connection, *, archive_root, source, doc_type, title, doc_num=None, doc_date=None):
    if doc_type not in DOCUMENT_TYPES:
        raise ValueError("Неизвестный тип вложения")
    file_kind=doc_type if doc_type in ('contract','quality') else None
    stored_type='other' if file_kind else doc_type
    doc_date = calendar_date(doc_date)
    title = required_text(title, "название документа")
    source = Path(source).resolve(strict=True)
    root = Path(archive_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Сначала копия, затем её хеш: изменение исходника во время чтения
    # не приводит к хранению файла под хешем других байтов.
    handle, temp_name = tempfile.mkstemp(prefix=".import-", dir=root)
    os.close(handle)
    temp = Path(temp_name)
    try:
        shutil.copyfile(source, temp)
        sha = digest(temp)
        existing = connection.execute("SELECT * FROM attachments WHERE sha256=?", (sha,)).fetchone()
        if existing:
            stored = archived_path(root, existing["storage_path"])
            if not stored.exists():
                # Повторно предоставленный оригинал с тем же хешем может
                # восстановить потерянную копию без изменения реквизитов.
                stored.parent.mkdir(parents=True, exist_ok=True)
                os.link(temp, stored)
            if not stored.is_file() or digest(stored) != sha:
                raise ValueError("Архивная копия отсутствует или повреждена")
            # Повторный импорт не меняет реквизиты уже зарегистрированного файла.
            return {"id": existing["id"], "duplicate": True}
        suffix = source.suffix.lower()
        if not suffix or not all(char.isascii() and (char.isalnum() or char == ".") for char in suffix):
            suffix = ".bin"
        relative = Path(sha[:2]) / (sha + suffix)
        target = archived_path(root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if digest(target) != sha:
                raise ValueError("Коллизия или повреждение файла архива")
        else:
            os.link(temp, target)
        cursor = connection.execute(
            "INSERT INTO attachments (sha256, storage_path, original_name, byte_size, doc_type, title, doc_num, doc_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sha, relative.as_posix(), source.name, temp.stat().st_size, stored_type, title, doc_num, doc_date),
        )
        if file_kind:
            connection.execute('UPDATE attachments SET file_kind=? WHERE id=?',(file_kind,cursor.lastrowid))
        return {"id": cursor.lastrowid, "duplicate": False}
    finally:
        temp.unlink(missing_ok=True)


def link_file(connection, *, attachment_id, entity, entity_id):
    if entity not in LINKS:
        raise ValueError("Неизвестный тип связи вложения")
    table, column = LINKS[entity]
    connection.execute(f"INSERT OR IGNORE INTO {table} ({column}, attachment_id) VALUES (?, ?)",
                       (entity_id, attachment_id))
    return {"ok": True, "attachment_id": attachment_id, "entity": entity, "entity_id": entity_id}


def publish_project_file(connection, *, attachment_id, project_id, archive_root):
    """Пользовательская копия оригинала; архив и деловые связи не переписываются."""
    from .layout import project_directory, path_component, check_path
    from .paths import database_workspace, document_root, relative_or_absolute
    database = next((r[2] for r in connection.execute('PRAGMA database_list') if r[1]=='main'), '')
    if not database:
        raise ValueError('Для папок исходных файлов нужна файловая БД')
    item = connection.execute('SELECT * FROM attachments WHERE id=?',(attachment_id,)).fetchone()
    if item is None:
        raise ValueError('Исходный файл не найден')
    source = archived_path(archive_root,item['storage_path'])
    if not source.is_file() or digest(source)!=item['sha256']:
        raise ValueError('Архивная копия отсутствует или повреждена')
    workspace = database_workspace(database)
    root = document_root(workspace)
    if root.is_symlink():
        raise ValueError('Ссылка вместо корня ИТД')
    folder = project_directory(connection,project_id,root)
    folder /= 'Рабочая документация' if item['doc_type']=='rd' else 'Исходные файлы'
    if not folder.resolve().is_relative_to(root.resolve()):
        raise ValueError('Каталог исходных файлов находится вне корня ИТД')
    folder.mkdir(parents=True,exist_ok=True)
    budget = min(180, 239 - len(str(folder).encode('utf-16-le')) // 2)
    if budget < 24:
        raise ValueError('Сократите путь к папке ИТД: для имени исходного файла не осталось места')
    name = path_component(item['original_name'],preserve_end=True,max_bytes=budget)
    target = folder / name
    # Не затираем одноимённый файл другой редакции или пользовательские изменения.
    if target.is_symlink():
        raise ValueError('Вместо исходного файла обнаружена ссылка')
    if target.exists() and (not target.is_file() or digest(target)!=item['sha256']):
        original = Path(name)
        name = path_component(original.stem+' ['+item['sha256'][:12]+']'+original.suffix,preserve_end=True,max_bytes=budget)
        target = folder / name
    check_path(target)
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Путь исходного файла небезопасен')
    if target.exists():
        if not target.is_file() or digest(target)!=item['sha256']:
            raise ValueError('В папке уже есть другой файл с этим именем; он не заменён')
    else:
        handle, temp_name = tempfile.mkstemp(prefix='.itd-copy-',dir=folder)
        os.close(handle)
        temp=Path(temp_name)
        try:
            shutil.copyfile(source,temp)
            if digest(temp)!=item['sha256']:
                raise ValueError('Файл изменился при копировании')
            try:
                os.link(temp,target)
            except FileExistsError:
                if target.is_symlink() or not target.is_file() or digest(target)!=item['sha256']:
                    raise ValueError('Файл с этим именем появился при копировании; он не заменён')
        finally:
            temp.unlink(missing_ok=True)
    relative=relative_or_absolute(workspace,target)
    connection.execute('INSERT INTO project_files(project_id,attachment_id,path) VALUES(?,?,?) ON CONFLICT(project_id,path) DO UPDATE SET attachment_id=excluded.attachment_id',(project_id,attachment_id,relative))
    return relative


def file_type(item):
    kind=item['file_kind'] if 'file_kind' in item.keys() else None
    if kind:return kind
    return 'quality' if item['doc_type'] in ('certificate','passport') else item['doc_type']


def is_quality_file(item):
    return file_type(item)=='quality'
