"""Read attachment rows and preserve their original locators for the receipt."""
import base64
import csv
import hashlib
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .. import archive, specification, storage
from ..assistant_files import (
    AttachmentError, MAX_BYTES, MAX_TEXT, OFFICE_FORMATS, TEXT_FORMATS,
    attachment_parts, parts_text,
)
from ..resources import quantity


HEADERS = {
    'position': ('позиция', 'поз', 'номер позиции', 'position', 'pos'),
    'name': ('наименование', 'название', 'name', 'наименование и техническая характеристика'),
    'unit': ('ед изм', 'единица измерения', 'единица', 'unit', 'ед'),
    'quantity': ('количество', 'кол во', 'кол', 'quantity', 'qty'),
    'reference': ('ссылка', 'документ', 'норма', 'норматив', 'обозначение документа', 'reference'),
}


def file_bytes(file):
    name = file['name']
    if (name in ('.', '..') or '/' in name or '\\' in name
            or any(ord(char) < 32 for char in name)):
        raise AttachmentError('Недопустимое имя файла.')
    try:
        content = base64.b64decode(file['content'], validate=True)
    except (ValueError, TypeError) as error:
        raise AttachmentError('Не удалось прочитать вложение.') from error
    if not 0 < len(content) <= MAX_BYTES:
        raise AttachmentError('Размер вложения должен быть больше нуля и не превышать 4 МиБ.')
    return content


def split_text(text):
    sample = '\n'.join(text.splitlines()[:20])
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters='\t;|,').delimiter
    except csv.Error:
        return [re.split(r'\t|;|\|| {2,}', line) for line in text.splitlines()]
    return csv.reader(text.splitlines(), delimiter=delimiter)


def tables(data, suffix):
    if suffix in TEXT_FORMATS:
        text = data.decode('utf-8-sig')
        return text, [(None, None, '', 1, split_text(text))]
    if suffix not in OFFICE_FORMATS | {'.pdf'}:
        raise AttachmentError('Формат файла не поддерживается.')
    parts = attachment_parts(data, suffix)
    groups = []
    sheets = {}
    for part in parts:
        if 'values' in part:
            sheets.setdefault(part['sheet'], []).append((part['row'], part['values']))
        if part.get('rows'):
            groups.append((None, None, f"Таблица {part['block']}, ", 1, part['rows']))
        if part.get('page') and part.get('text', '').strip():
            groups.append((part['page'], None, '', 1, split_text(part['text'])))
    groups.extend((None, sheet, '', None, rows) for sheet, rows in sheets.items())
    return parts_text(parts), groups


def mapped_rows(groups):
    for page, sheet, prefix, start, rows in groups:
        mapping = {}
        for number, cells in (enumerate(rows, start) if start is not None else rows):
            cells = [str(cell).strip() if cell is not None else '' for cell in cells]
            if not any(cells):
                continue
            keys = [re.sub(r'[^\w]+', ' ', cell.casefold()).strip() for cell in cells]
            header = {field: keys.index(key) for field, names in HEADERS.items()
                      for key in names if key in keys}
            if 'name' in header and len(header) >= 2:
                mapping = header
                continue
            # A header is optional for the five-column exchange layout.
            columns = mapping or dict(zip(HEADERS, range(5)))
            row = {field: cells[index] for field, index in columns.items() if index < len(cells)}
            yield dict(row, page=page, sheet=sheet, locator=f'{prefix}строка {number}')


def resolve_file(file, actor, attachments):
    if 'attachment_id' in file:
        if actor.source != 'assistant' or file['attachment_id'] not in (attachments or {}):
            raise AttachmentError('Выберите исходное вложение этого чата.')
        file = attachments[file['attachment_id']]
    content = file_bytes(file)
    if 'sha256' in file and hashlib.sha256(content).hexdigest() != file['sha256']:
        raise AttachmentError('Хеш исходного вложения не совпадает.')
    return {'name': file['name'], 'content': file['content']}, content


def prepare(data, actor, attachments):
    packet = data.model_dump(mode='json', exclude_unset=True)
    if actor.source == 'assistant' and 'attachment_id' not in packet['attachment']:
        raise AttachmentError('Используйте идентификатор исходного вложения чата.')
    file, content = resolve_file(packet['attachment'], actor, attachments)
    checksum = hashlib.sha256(content).hexdigest()
    suffix = Path(file['name']).suffix.lower()
    try:
        text, groups = tables(content, suffix)
    except AttachmentError:
        raise
    except Exception as error:
        raise AttachmentError('Не удалось прочитать документ. Для текстовых файлов используйте UTF-8.') from error
    if not text.strip():
        raise AttachmentError('В документе нет текста для чтения.')
    if len(text) > MAX_TEXT:
        raise AttachmentError('Текст вложения превышает 80 000 символов. Прикрепите фрагмент.')
    rows = packet.get('rows')
    warnings = []
    if rows is None:
        if suffix == '.json':
            from pydantic import TypeAdapter
            from ..tools.preview_schemas import SpecificationLine
            try:
                parsed = TypeAdapter(list[SpecificationLine]).validate_python(json.loads(text))
                rows = [item.model_dump(exclude_unset=True) for item in parsed]
            except ValueError as error:
                raise AttachmentError('JSON спецификации должен содержать массив строк с полями позиции.') from error
        else:
            from itertools import islice
            rows = list(islice(mapped_rows(groups), 501))
    else:
        warnings.append('Сверьте распознанные строки, ссылки и категории с оригиналом.')
    if not rows or len(rows) > 500:
        raise AttachmentError('Нужно от 1 до 500 строк спецификации. Укажите строки или приложите фрагмент.')
    items = []
    view = []
    keys = set()
    for number, row in enumerate(rows, 1):
        values = {key: (row.get(key) or '').strip() for key in ('position', 'name', 'unit', 'reference')}
        raw = row.get('quantity')
        try:
            amount = quantity(raw.replace(' ', '').replace('\u00a0', '').replace(',', '.') if isinstance(raw, str) else raw,
                              'количество')
        except ValueError:
            amount = None
        values['quantity'] = amount
        category = row.get('category') or packet.get('category')
        issues = [label for key, label in (('position', 'позиция'), ('name', 'наименование'),
                  ('unit', 'единица измерения'), ('reference', 'ссылка на документ или норму')) if not values[key]]
        if amount is None:
            issues.append('количество')
        if not category:
            issues.append('категория ресурса')
        locator = {key: row.get(key) for key in ('page', 'sheet', 'locator')}
        stable = (locator['page'], locator['sheet'], locator['locator'] or values['position'] or str(number))
        source_key = 'spec:' + hashlib.sha256(repr(stable).encode()).hexdigest()
        if source_key in keys:
            issues.append('уникальное место в источнике')
            source_key += f':{number}'
        keys.add(source_key)
        view.append(dict(values, **locator, row=number, source_key=source_key,
                         category=category, missing=issues))
        items.append(dict(source_key=source_key, verified=not issues, **locator,
                          resource={'spec_num': values['position'], 'name': values['name'],
                                    'unit': values['unit'], 'qty_proj': amount,
                                    'category': category, 'note': values['reference']},
                          reason='Нужно уточнить: ' + ', '.join(issues) if issues else None))
    return {'file': {'name': file['name'], 'content': file['content'], 'sha256': checksum},
            'items': items}, view, warnings


def save(c, ctx, project_id, packet):
    file = packet['file']
    content = file_bytes(file)
    if hashlib.sha256(content).hexdigest() != file['sha256']:
        raise ValueError('Хеш исходного вложения не совпадает.')
    with TemporaryDirectory(prefix='itd-spec-source-') as folder:
        source = Path(folder) / file['name']
        source.write_bytes(content)
        identity = archive.import_file(c, archive_root=ctx.database.parent / 'archive',
                                       source=source, doc_type='rd', title=file['name'])['id']
    result = specification.import_specification(c, project_id=project_id,
                                                attachment_id=identity, items=packet['items'])
    item = c.execute('SELECT * FROM attachments WHERE id=?', (identity,)).fetchone()
    storage.store_attachment(c, project_id, item,
                             archive.archived_path(ctx.database.parent / 'archive', item['storage_path']))
    return result
