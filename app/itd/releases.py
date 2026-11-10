"""Управление выбранными выпусками. Переносы имеют долговечный журнал восстановления.

Операции move/recover/publish владеют транзакциями и вызываются отдельно от
деловых правок. ФС и SQLite не атомарны: prepared фиксируется ДО изменения ФС.
"""
import json
import os
import errno
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from .paths import database_workspace, data_directory, document_root
from .archive import digest
from .changes import log_event
from .layout import path_component, check_path, create_layout


def workspace(connection):
    filename = connection.execute('PRAGMA database_list').fetchone()[2]
    return database_workspace(filename) if filename else Path.cwd()


def service_directory(connection):
    filename = connection.execute('PRAGMA database_list').fetchone()[2]
    return data_directory(filename) if filename else Path.cwd()


def stored_path(connection, path):
    path = Path(path).resolve()
    root = workspace(connection)
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)


def actual_path(connection, path):
    return Path(path) if Path(path).is_absolute() else workspace(connection) / path


def release_row(connection, release_id):
    row = connection.execute('SELECT * FROM releases WHERE id=?', (release_id,)).fetchone()
    if row is None:
        raise ValueError('Выпуск не найден')
    return dict(row)


def register_release(connection, *, project_id, act_id=None, generated_id=None, kind, title, path, mode='draft'):
    path = Path(path).resolve(strict=True)
    cursor = connection.execute('INSERT INTO releases(project_id,act_id,generated_id,kind,title,path,sha256,mode) VALUES (?,?,?,?,?,?,?,?)',
                               (project_id, act_id, generated_id, kind, title, stored_path(connection,path), digest(path), mode))
    log_event(connection, 'release-register', entity='releases', entity_id=cursor.lastrowid,
              after={'path':stored_path(connection,path), 'sha256':digest(path)})
    return cursor.lastrowid


def list_releases(connection, project_id=None):
    if project_id is not None and not connection.execute('SELECT 1 FROM projects WHERE id=?',(project_id,)).fetchone():
        raise ValueError('Раздел не найден')
    rows = connection.execute('SELECT * FROM releases' + (' WHERE project_id=?' if project_id else '') + ' ORDER BY id',
                              (project_id,) if project_id else ())
    result=[]
    for row in rows:
        row=dict(row)
        row['current_path']=str(actual_path(connection,row['path']))
        result.append(row)
    return result


def verify_releases(connection, project_id=None):
    result=[]
    for row in list_releases(connection,project_id):
        path=Path(row['current_path'])
        status='missing' if not path.is_file() else ('ok' if digest(path)==row['sha256'] else 'hash_mismatch')
        result.append({**row,'status':status})
    pending=[dict(r) for r in connection.execute(
        "SELECT op.* FROM release_operations op JOIN releases r ON r.id=op.release_id WHERE op.state='prepared'" +
        (' AND r.project_id=?' if project_id is not None else '') + ' ORDER BY op.id',
        (project_id,) if project_id is not None else ())]
    return {'releases':result,'unfinished_operations':pending,'ok':all(r['status']=='ok' for r in result) and not pending}


def _safe_destination(connection, destination, suffix, *, allowed_existing=None):
    root=workspace(connection)
    raw=Path(destination)
    if not raw.is_absolute():
        raw=root/raw
    # Не позволяем служебным маркерам и симлинкам стать назначением.
    if any(p.is_symlink() for p in [raw,*raw.parents]):
        raise ValueError('Символические ссылки в пути назначения запрещены')
    destination=raw.resolve()
    if destination.is_relative_to(root):
        relative = destination.relative_to(root)
        if not relative.parts or relative.parts[0] in ('archive','templates','itd','tests','.git','core','misc','app','skills','logs'):
            raise ValueError('Назначение в защищённом каталоге')
    elif destination.is_relative_to(document_root(root)):
        relative = destination.relative_to(document_root(root))
    else:
        raise ValueError('Назначение должно находиться внутри рабочей папки или папки ИТД')
    if relative.parts and relative.parts[0] in ('data', 'db') and not (
        destination.is_relative_to(service_directory(connection)/'История выпусков')
        or destination.is_relative_to(service_directory(connection)/'work'/'.itd-staging')
    ):
        raise ValueError('Назначение в защищённом каталоге данных')
    if destination.name.startswith('.') or destination.suffix.lower()!=suffix.lower():
        raise ValueError('Нельзя менять тип файла или использовать служебное имя')
    if path_component(destination.stem)!=destination.stem:
        raise ValueError('Недопустимое имя; используйте безопасное краткое название')
    check_path(destination)
    # Коллизии имён учитываются без регистра и на Linux.
    if destination.parent.exists():
        for sibling in destination.parent.iterdir():
            if sibling.name.casefold()==destination.name.casefold() and sibling != allowed_existing:
                raise FileExistsError(f'Назначение занято: {sibling}')
    return destination


def _finish(connection, operation_id):
    op=connection.execute('SELECT * FROM release_operations WHERE id=?',(operation_id,)).fetchone()
    if op is None or op['state']!='prepared':
        return {'operation_id':operation_id,'state':op['state'] if op else 'missing'}
    source=actual_path(connection,op['old_path'])
    target=actual_path(connection,op['new_path'])
    row=release_row(connection,op['release_id'])
    _safe_destination(connection,target,source.suffix,allowed_existing=target)
    if source.is_symlink() or any(p.is_symlink() for p in source.parents):
        raise ValueError('Исходный путь содержит символическую ссылку')
    if source.exists() and (not source.is_file() or digest(source)!=op['sha256']):
        raise ValueError('Исходный файл изменён; восстановление остановлено')
    if target.exists() and (not target.is_file() or digest(target)!=op['sha256']):
        raise ValueError('Назначение занято другим содержимым; восстановление остановлено')
    if not source.exists() and not target.exists():
        raise ValueError('Оба пути отсутствуют; требуется сверка истории')
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        # Сначала исключительное создание ссылки: существующий файл не перезаписывается.
        # При сбое между link/unlink оба пути обнаруживаются через prepared.
        try:
            os.link(source,target)
        except OSError as error:
            if error.errno != errno.EXDEV:
                raise
            descriptor,name=tempfile.mkstemp(prefix=f'.itd-move-{operation_id}-',suffix='.tmp',dir=target.parent)
            temporary=Path(name)
            try:
                with source.open('rb') as src, os.fdopen(descriptor,'wb') as dst:
                    shutil.copyfileobj(src,dst)
                    dst.flush()
                    os.fsync(dst.fileno())
                if digest(temporary)!=op['sha256']:
                    raise ValueError('Исходник изменился при копировании')
                os.link(temporary,target)
            finally:
                temporary.unlink(missing_ok=True)
    if source.exists():
        source.unlink()
    connection.execute('UPDATE releases SET path=? WHERE id=?',(op['new_path'],row['id']))
    if row['generated_id']:
        connection.execute('UPDATE generated_documents SET output_path=? WHERE id=?',(op['new_path'],row['generated_id']))
    connection.execute("UPDATE release_operations SET state='done',result='verified' WHERE id=?",(operation_id,))
    log_event(connection,'release-move',entity='releases',entity_id=row['id'],
              before={'path':op['old_path'],'sha256':op['sha256']},after={'path':op['new_path'],'sha256':op['sha256'],'operation_id':operation_id,'result':'done'})
    connection.commit()
    return {'operation_id':operation_id,'state':'done','release_id':row['id'],'output':str(target)}


def move_release(connection, release_id, destination, *, after_file_operation=None):
    row=release_row(connection,release_id)
    source=actual_path(connection,row['path'])
    destination=Path(destination)
    if not destination.is_absolute():
        destination=workspace(connection)/destination
    if source.resolve()==destination.resolve():
        if not source.is_file() or digest(source)!=row['sha256']:
            raise ValueError('Отсутствующий или изменённый файл')
        return {'release_id':release_id,'state':'unchanged','output':str(source)}
    if not source.is_file() or source.is_symlink() or digest(source)!=row['sha256']:
        raise ValueError('Исходный выпуск отсутствует или его хеш не совпадает')
    if source.suffix.lower() not in ('.docx','.xlsx') or source.name.startswith('.'):
        raise ValueError('Служебные файлы не являются выпусками')
    destination=_safe_destination(connection,destination,source.suffix)
    if connection.execute("SELECT 1 FROM release_operations WHERE release_id=? AND state='prepared'",(release_id,)).fetchone():
        raise ValueError('Есть незавершённый перенос; выполните release-recover')
    cursor=connection.execute("INSERT INTO release_operations(release_id,old_path,new_path,sha256,state) VALUES (?,?,?,?,'prepared')",
                             (release_id,row['path'],stored_path(connection,destination),row['sha256']))
    op_id=cursor.lastrowid
    log_event(connection,'release-move-prepared',entity='releases',entity_id=release_id,
              before={'path':row['path']},after={'path':stored_path(connection,destination),'operation_id':op_id,'sha256':row['sha256']})
    connection.commit()
    # Инъекция сбоя только для тестов восстановления после фактического переноса.
    if after_file_operation:
        destination.parent.mkdir(parents=True,exist_ok=True)
        os.link(source,destination)
        source.unlink()
        after_file_operation()
    return recover(connection,op_id)


def recover(connection, operation_id):
    try:
        return _finish(connection,operation_id)
    except Exception as error:
        connection.rollback()
        connection.execute("UPDATE release_operations SET result=? WHERE id=? AND state='prepared'", (str(error),operation_id))
        log_event(connection,'release-move-failed',after={'operation_id':operation_id,'result':str(error)})
        connection.commit()
        raise


def select_release(connection, release_id):
    row=release_row(connection,release_id)
    path=actual_path(connection,row['path'])
    if not path.is_file() or digest(path)!=row['sha256']:
        raise ValueError('Нельзя выбрать отсутствующий или изменённый выпуск')
    if connection.execute("SELECT 1 FROM release_operations WHERE state='prepared' AND release_id=?",(release_id,)).fetchone():
        raise ValueError('Сначала завершите перенос')
    before=[r[0] for r in connection.execute('SELECT id FROM releases WHERE selected=1 AND project_id=? AND (act_id=? OR (act_id IS NULL AND ? IS NULL AND kind=?))',
                                           (row['project_id'],row['act_id'],row['act_id'],row['kind']))]
    for previous in before:
        connection.execute('UPDATE releases SET selected=0 WHERE id=?',(previous,))
    connection.execute('UPDATE releases SET selected=1 WHERE id=?',(release_id,))
    log_event(connection,'release-select',entity='releases',entity_id=release_id,before={'release_ids':before},after={'release_id':release_id})


def default_output(connection, *, project_id, title, kind, group, root=None, identity=None, draft=True):
    root=Path(root) if root else document_root(workspace(connection))
    if not root.is_absolute():
        root=workspace(connection)/root
    if not (root.resolve().is_relative_to(workspace(connection)) or root == document_root(workspace(connection))):
        raise ValueError('Корень выдачи должен находиться внутри рабочей папки проекта')
    base=Path(create_layout(connection,project_id,root)['directory'])
    groups={'registry':'01_Реестр','act':'03_Акты','statement':'04_Ведомости'}
    directory=base/groups[group]
    if group=='act':
        directory=directory/('Черновики' if draft else 'Выдача')
    budget=min(180-len(kind)-1,240-len(str(directory).encode('utf-16-le'))//2-len(kind)-2)
    if budget<16:raise ValueError('Сократите путь к папке ИТД: для имени документа не осталось места')
    stem=path_component(title,max_bytes=budget)
    target=directory/(stem+'.'+kind)
    # Различаем документы, но не добавляем номер нового выпуска в основное имя.
    for row in connection.execute('SELECT * FROM releases WHERE project_id=?',(project_id,)):
        same_doc=(row['act_id']==identity) if identity is not None else row['kind']==kind and row['act_id'] is None
        if not same_doc and actual_path(connection,row['path']).name.casefold()==target.name.casefold():
            target=target.with_name(path_component(stem+f' — документ {identity}',max_bytes=budget)+'.'+kind)
            break
    return check_path(target)


def publish(connection, release_id, target):
    """Убирает только выбранный прежний выпуск того же документа, затем выбирает новый."""
    row=release_row(connection,release_id)
    target=Path(target)
    if not target.is_absolute():
        target=workspace(connection)/target
    if actual_path(connection,row['path']).resolve()==target.resolve():
        move_release(connection,release_id,target)
        select_release(connection,release_id)
        connection.commit()
        return {'release_id':release_id,'output':str(target),'selected':True}
    previous=connection.execute('SELECT * FROM releases WHERE selected=1 AND project_id=? AND id<>? AND (act_id=? OR (act_id IS NULL AND ? IS NULL AND kind=?))',
                                (row['project_id'],release_id,row['act_id'],row['act_id'],row['kind'])).fetchone()
    # Проверяем новое назначение до перемещения истории: разрешено занять лишь путь прежнего выбранного выпуска.
    if target.exists() and (previous is None or actual_path(connection,previous['path']).resolve()!=target.resolve()):
        raise FileExistsError(f'Назначение занято: {target}')
    target=_safe_destination(connection,target,actual_path(connection,row['path']).suffix,
                             allowed_existing=actual_path(connection,previous['path']) if previous else None)
    if previous:
        old=actual_path(connection,previous['path'])
        history=service_directory(connection)/'История выпусков'/str(previous['id'])/(path_component(old.stem)+old.suffix)
        if old.resolve()!=history.resolve():
            move_release(connection,previous['id'],history)
    source=actual_path(connection,row['path'])
    move_release(connection,release_id,target)
    select_release(connection,release_id)
    connection.commit()
    staging=service_directory(connection)/'work'/'.itd-staging'
    if source.parent == staging:
        for directory in (staging,staging.parent):
            try:
                directory.rmdir()
            except OSError:
                break
    return {'release_id':release_id,'output':str(target),'selected':True}


def export_package(connection, project_id, output):
    output=Path(output).resolve()
    if output.exists():
        raise FileExistsError('Архив уже существует')
    rows=connection.execute('SELECT r.* FROM releases r LEFT JOIN acts a ON a.id=r.act_id WHERE r.project_id=? AND r.selected=1 AND (r.act_id IS NULL OR a.is_active=1)',(project_id,)).fetchall()
    if not rows:
        raise ValueError('Не выбраны выпуски для выдачи')
    manifest=[]
    seen=set()
    for r in rows:
        path=actual_path(connection,r['path'])
        if not path.is_file() or digest(path)!=r['sha256']:
            raise ValueError(f'Файл отсутствует или изменён: {path}')
        # Те же имена, что в основной папке. Группа исключает смешение разных документов.
        group='04_Ведомости' if r['kind']=='xlsx' else '03_Акты'
        if r['act_id']:
            form=connection.execute('SELECT t.form_group FROM acts a JOIN document_types t ON a.act_type=t.code WHERE a.id=?',(r['act_id'],)).fetchone()[0]
            group={'registry':'01_Реестр','statement':'04_Ведомости','act':'03_Акты'}[form]
        if group=='03_Акты':
            group += '/'+('Черновики' if r['mode']=='draft' else 'Выдача')
        member=group+'/'+path.name
        if member.casefold() in seen:
            raise ValueError('Совпали имена выбранных документов; задайте содержательное различие')
        seen.add(member.casefold())
        manifest.append({'release_id':r['id'],'title':r['title'],'file':member,'sha256':r['sha256'],'mode':r['mode']})
    manifest.sort(key=lambda m:(m['file'].split('/')[0],m['release_id']))
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as handle:
        try:
            with ZipFile(handle,'w',compression=ZIP_DEFLATED) as z:
                for item in manifest:
                    row=release_row(connection,item['release_id'])
                    z.write(actual_path(connection,row['path']),item['file'])
                z.writestr('manifest.json',json.dumps({'project_id':project_id,'releases':manifest},ensure_ascii=False,indent=2))
        except Exception:
            output.unlink(missing_ok=True)
            raise
    log_event(connection,'package-export',after={'project_id':project_id,'output':str(output),'releases':manifest})
    return {'output':str(output),'releases':manifest,'note':'Только выбранные сформированные выпуски; исходные приложения в ZIP не добавляются.'}


def reconcile(connection, items, *, apply=False):
    """Явный точный план для ранее перемещённых файлов. По умолчанию только сверка."""
    if not isinstance(items,list) or not items:
        raise ValueError('Ожидается непустой список release_id, old_path, new_path, sha256')
    plan=[]
    seen=set()
    for item in items:
        if set(item)!={'release_id','old_path','new_path','sha256'} or item['release_id'] in seen:
            raise ValueError('Неверный или повторный элемент плана')
        seen.add(item['release_id'])
        row=release_row(connection,item['release_id'])
        target=actual_path(connection,item['new_path']).resolve()
        if row['path']!=item['old_path'] or row['sha256']!=item['sha256']:
            raise ValueError('План устарел')
        if not target.is_relative_to(workspace(connection)) or target.name.startswith('.'):
            raise ValueError('Недопустимое назначение сверки')
        _safe_destination(connection,target,actual_path(connection,row['path']).suffix,allowed_existing=target)
        if not target.is_file() or digest(target)!=row['sha256']:
            raise ValueError('Новый путь отсутствует или хеш не совпадает')
        old=actual_path(connection,row['path'])
        if old.exists() and old.resolve()!=target:
            if old.resolve().is_relative_to(workspace(connection)):
                raise ValueError('Прежний файл ещё существует: используйте release-move')
            if not old.is_file() or digest(old)!=row['sha256']:
                raise ValueError('Исходная копия вне рабочей папки изменилась')
        plan.append({**item,'new_path':stored_path(connection,target)})
    if apply:
        for item in plan:
            row=release_row(connection,item['release_id'])
            connection.execute('UPDATE releases SET path=? WHERE id=?',(item['new_path'],row['id']))
            if row['generated_id']:
                connection.execute('UPDATE generated_documents SET output_path=? WHERE id=?',(item['new_path'],row['generated_id']))
            log_event(connection,'release-reconcile',entity='releases',entity_id=row['id'],before={'path':item['old_path']},after=item)
    return {'applied':apply,'plan':plan}


def plan_relocations(connection, movements):
    """Преобразовать старый файл original_path/history_path в проверяемый точный план.

    Ничего не переносит и не изменяет. Незарегистрированные файлы явно исключены.
    """
    if not isinstance(movements,list):raise ValueError('Ожидается массив перемещений')
    known=list_releases(connection)
    plan=[];ignored=[]
    for item in movements:
        if not isinstance(item,dict) or not {'original_path','history_path','sha256'}<=set(item):
            raise ValueError('Нужны original_path, history_path, sha256')
        matches=[r for r in known if actual_path(connection,r['path'])==Path(item['original_path']) and r['sha256']==item['sha256']]
        if len(matches)>1:raise ValueError('Несколько выпусков совпали; укажите release_id вручную')
        if not matches:
            ignored.append({'path':item['original_path'],'reason':'not_registered_release'})
            continue
        row=matches[0]
        plan.append({'release_id':row['id'],'old_path':row['path'],'new_path':item['history_path'],'sha256':row['sha256']})
    return {'applied':False,'plan':plan,'ignored':ignored,'instruction':'Согласуйте точный plan и передайте только этот массив в release-reconcile --data; сначала без --apply.'}
