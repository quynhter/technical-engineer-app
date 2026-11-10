"""Сохранение входного контроля за дату с отдельными строками ресурсов."""
import base64
import json
from pathlib import Path
import tempfile

from .archive import import_file, is_quality_file, link_file
from .db import atomic_operation, calendar_date, required_text
from .resources import quantity
from .workspace import extend_journal_dates, save_entry
from .workflow import add_quality_review, row, same_project


DOCUMENT_TYPES = {
    'passport': 'Паспорт',
    'conformity_certificate': 'Сертификат соответствия',
    'exemption_letter': 'Отказное письмо',
    'quality_certificate': 'Сертификат качества',
    'conformity_declaration': 'Декларация о соответствии',
    'state_registration': 'Свидетельство о гос. регистрации',
    'fire_certificate': 'Пожарный сертификат / декларация',
    'manual': 'Руководство по эксплуатации',
    'safety_data_sheet': 'Паспорт безопасности',
    'origin_certificate': 'Сертификат происхождения товара',
    'incoming_report': 'Акт входного контроля',
    'other': 'Другой документ',
}


@atomic_operation
def save_incoming_day(c, project_id, data, archive_root):
    date = calendar_date(required_text(data.get('date'), 'дата контроля'))
    items = data.get('resources')
    if not isinstance(items, list) or not items:
        raise ValueError('Добавьте хотя бы один ресурс')
    seen = set()
    edits = set()
    unchanged_resources = set()
    prepared = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Некорректный блок ресурса')
        resource = same_project(c, 'resources', item.get('resource_id'), project_id)
        rid = resource['id']
        if rid in seen:
            raise ValueError('Ресурс повторяется: ' + resource['name'])
        seen.add(rid)
        old = {}
        if item.get('id') is not None:
            old = same_project(c, 'workspace_entries', item['id'], project_id)
            if old['kind'] != 'incoming' or old['revision'] != item.get('revision') or old['id'] in edits:
                raise ValueError('Запись входного контроля изменилась. Откройте её заново.')
            edits.add(old['id'])
            if old['resource_id'] == rid and old['entry_date'] == date:
                unchanged_resources.add(rid)
        fields = json.loads(old.get('work_fields', '{}'))
        attachment = old.get('attachment_id')
        if old and old['resource_id'] != rid:
            fields.update(supply_id=None, quality_review_id=None)
            fields.pop('incoming_document_type', None)
            attachment = None
        result = item.get('result')
        if result not in ('pending', 'accepted', 'rejected'):
            raise ValueError('Выберите результат входного контроля')
        fields['incoming_result'] = result
        document_type = item.get('document_type')
        file = item.get('file')
        if (document_type or file) and document_type not in DOCUMENT_TYPES:
            raise ValueError('Выберите тип документа')
        upload = None
        if file is not None:
            if not isinstance(file, dict):
                raise ValueError('Некорректный файл')
            name = file['name']
            if not isinstance(name, str) or not name or '/' in name or '\\' in name or name in ('.', '..'):
                raise ValueError('Недопустимое имя файла')
            content = base64.b64decode(file['content'], validate=True)
            if not 0 < len(content) <= 32 * 1024 * 1024:
                raise ValueError('Размер файла должен быть больше нуля и не превышать 32 МБ')
            upload = name, content
        if document_type and (attachment or upload):
            fields['incoming_document_type'] = document_type
        review = item.get('review')
        if review is not None:
            if not isinstance(review, dict) or review.get('status') not in ('matches', 'mismatch', 'uncertain'):
                raise ValueError('Выберите результат сверки документа')
            if (upload and document_type == 'other') or (not upload and (
                    not attachment or not is_quality_file(row(c, 'attachments', attachment)))):
                raise ValueError('Для сверки приложите документ качества')
            review = {
                'status': review['status'],
                'checked_by': required_text(review.get('checked_by'), 'кто сверил документ'),
                'note': required_text(review.get('note'), 'что сверили в документе'),
            }
        details = item.get('details')
        if details is not None and not isinstance(details, str):
            raise ValueError('Примечание должно быть текстом')
        entry = dict(old, kind='incoming', entry_date=date, resource_id=rid, title=resource['name'],
                     unit=resource['unit'], quantity=quantity(item.get('quantity'), 'количество'),
                     details=details, work_fields=fields, attachment_id=attachment)
        prepared.append((entry, document_type, upload, review))

    for existing in c.execute("""SELECT id, resource_id FROM workspace_entries
        WHERE project_id=? AND kind='incoming' AND entry_date=?""", (project_id, date)):
        if existing['id'] not in edits and existing['resource_id'] in seen - unchanged_resources:
            raise ValueError('Этот ресурс уже записан во входном контроле за выбранную дату')

    extend_journal_dates(c, project_id, (date,), data.get('journal_dates_confirmation'))
    saved = []
    for entry, document_type, upload, review in prepared:
        if upload:
            name, content = upload
            with tempfile.TemporaryDirectory(prefix='itd-incoming-') as folder:
                source = Path(folder) / name
                source.write_bytes(content)
                archive_type = 'other' if document_type == 'other' else 'quality'
                attachment = import_file(c, archive_root=archive_root, source=source,
                                         doc_type=archive_type, title=name)['id']
            link_file(c, attachment_id=attachment, entity='project', entity_id=project_id)
            link_file(c, attachment_id=attachment, entity='resource', entity_id=entry['resource_id'])
            entry['attachment_id'] = attachment
            entry['work_fields'].pop('quality_review_id', None)
        if review:
            attachment = entry['attachment_id']
            link_file(c, attachment_id=attachment, entity='resource', entity_id=entry['resource_id'])
            saved_review = add_quality_review(c, project_id, dict(
                review, attachment_id=attachment, resource_id=entry['resource_id'],
                checked_date=date, source='Документ в записи входного контроля',
            ))
            entry['work_fields']['quality_review_id'] = saved_review['id']
        saved.append(save_entry(c, project_id, entry, sync_dates=False))
    return {'entries': saved}
