"""Выпуск в основную папку; собственные транзакции, отдельно от деловых правок."""
from pathlib import Path
import uuid

from . import releases


def generate_managed(connection, *, act_id, templates_dir, output=None, root=None, draft=True):
    from .acts import generate
    meta=connection.execute('SELECT a.*,t.name AS official_title,t.filename_title AS form_title,t.form_group FROM acts a JOIN document_types t ON a.act_type=t.code WHERE a.id=?',(act_id,)).fetchone()
    if meta is None:
        raise ValueError('Акт не найден')
    title=meta['filename_title'] or meta['act_num']
    target=(Path(output) if Path(output).is_absolute() else releases.workspace(connection)/output) if output else releases.default_output(connection,project_id=meta['project_id'],title=title,kind='docx',group=meta['form_group'],root=root,identity=act_id,draft=draft)
    staging=releases.service_directory(connection)/'work'/'.itd-staging'/(uuid.uuid4().hex+'.docx')
    result=generate(connection,act_id=act_id,templates_dir=templates_dir,output=staging,draft=draft)
    connection.commit()  # Выпуск сохранён до начала перемещений; доступен при сбое publish.
    published=releases.publish(connection,result['release_id'],target)
    return {**result,**published}


def statement_managed(connection, *, project_id, output=None, root=None, **options):
    from .statement import export_statement
    section=connection.execute('SELECT section_code FROM projects WHERE id=?',(project_id,)).fetchone()
    if section is None:raise ValueError('Раздел не найден')
    target=(Path(output) if Path(output).is_absolute() else releases.workspace(connection)/output) if output else releases.default_output(connection,project_id=project_id,title='Общая ведомость ресурсов '+section[0],kind='xlsx',group='statement',root=root)
    staging=releases.service_directory(connection)/'work'/'.itd-staging'/(uuid.uuid4().hex+'.xlsx')
    result=export_statement(connection,project_id=project_id,output=staging,**options)
    connection.commit()
    published=releases.publish(connection,result['release_id'],target)
    return {**result,**published}
