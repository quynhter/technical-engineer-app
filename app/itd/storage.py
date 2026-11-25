"""Файлы рабочего пространства. Имя для скачивания хранится отдельно от ID."""
from pathlib import Path
from uuid import uuid4
import shutil

from .archive import digest
from .layout import path_component
from .paths import database_workspace


def directory(c):
    database = c.execute('PRAGMA database_list').fetchone()[2]
    return database_workspace(database) / 'storage'


def store(c, project_id, source, name, *, attachment_id=None, release_id=None, act_id=None):
    source = Path(source)
    root = directory(c)
    if root.is_symlink():
        raise ValueError('Ссылка вместо каталога storage')
    root.mkdir(parents=True, exist_ok=True)
    identity = uuid4().hex
    target = root / identity
    checksum = digest(source)
    try:
        with source.open('rb') as reader, target.open('xb') as writer:
            shutil.copyfileobj(reader, writer)
        if digest(target) != checksum:
            raise ValueError('Файл изменился при сохранении')
        c.execute("""INSERT INTO files(id,project_id,name,sha256,act_id,attachment_id,release_id)
            VALUES(?,?,?,?,?,?,?)""",(identity,project_id,name,checksum,act_id,attachment_id,release_id))
        if hasattr(c,'new_storage_files'):
            c.new_storage_files.append((identity,target))
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def store_attachment(c, pid, item, path):
    row = c.execute('SELECT id FROM files WHERE project_id=? AND attachment_id=?',(pid,item['id'])).fetchone()
    if row:
        target = directory(c)/row[0]
        if not target.exists() and getattr(c, 'preview_origin', None):
            target = database_workspace(c.preview_origin) / 'storage' / row[0]
        if not target.is_file() or digest(target)!=item['sha256']:
            raise ValueError('Файл в storage отсутствует или повреждён')
        return target
    return store(c,pid,path,item['original_name'],attachment_id=item['id'])


def publish_stored(c, release_id, title, *, selected=True):
    from .releases import release_row, actual_path, stored_path, select_release
    r = release_row(c,release_id)
    staging = actual_path(c,r['path'])
    name = path_component(title)+'.'+r['kind']
    path = store(c,r['project_id'],staging,name,release_id=release_id,act_id=r['act_id'])
    c.execute('UPDATE releases SET path=? WHERE id=?',(stored_path(c,path),release_id))
    if r['generated_id']:
        c.execute('UPDATE generated_documents SET output_path=? WHERE id=?',(str(path),r['generated_id']))
    if selected:
        select_release(c,release_id)
    c.commit()
    staging.unlink(missing_ok=True)
    return {'release_id':release_id,'output':str(path),'selected':selected}


def import_existing(c):
    """Перенос сохранённых байтов при обновлении, прежние пути доступны старым выпускам."""
    from .archive import archived_path
    from .releases import actual_path
    archive = Path(c.execute('PRAGMA database_list').fetchone()[2]).parent / 'archive'
    for row in c.execute("""SELECT a.*,p.project_id FROM project_attachments p JOIN attachments a ON a.id=p.attachment_id
            LEFT JOIN files f ON f.attachment_id=a.id AND f.project_id=p.project_id WHERE f.id IS NULL"""):
        source = archived_path(archive,row['storage_path'])
        if source.is_file() and digest(source)==row['sha256']:
            store_attachment(c,row['project_id'],row,source)
    for row in c.execute("""SELECT r.* FROM releases r LEFT JOIN files f ON f.release_id=r.id WHERE f.id IS NULL"""):
        source = actual_path(c,row['path'])
        if source.is_file() and digest(source)==row['sha256']:
            store(c,row['project_id'],source,source.name,release_id=row['id'],act_id=row['act_id'])


def cleanup_removed(c):
    import re
    for row in c.execute('SELECT * FROM removed_storage_files').fetchall():
        if not re.fullmatch('[0-9a-f]{32}',row['id']):
            raise ValueError('Повреждён идентификатор файла storage')
        target = directory(c)/row['id']
        if target.parent.is_symlink():
            raise ValueError('Ссылка вместо каталога storage')
        if target.exists():
            if target.is_symlink() or digest(target)!=row['sha256']:
                continue
            target.unlink(missing_ok=True)
        c.execute('DELETE FROM removed_storage_files WHERE id=?',(row['id'],))
    c.commit()
