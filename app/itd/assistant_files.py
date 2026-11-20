"""Read user-selected chat attachments without archiving them in the workspace."""
import base64
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from .readers import read_document

MAX_BYTES = 4 * 1024 * 1024
MAX_TEXT = 80000
TEXT_FORMATS = {'.txt', '.md', '.csv', '.tsv', '.json'}
OFFICE_FORMATS = {'.docx', '.xlsx'}


class AttachmentError(ValueError):
    """Messages here may be shown directly to the user."""


def attachment_text(data, suffix):
    if suffix in TEXT_FORMATS:
        return data.decode('utf-8-sig')
    if suffix in OFFICE_FORMATS:
        with ZipFile(BytesIO(data)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 16 * 1024 * 1024:
                raise AttachmentError('Распакованный документ слишком велик.')
    with TemporaryDirectory() as directory:
        path = Path(directory) / ('attachment' + suffix)
        path.write_bytes(data)
        parts = read_document(path)['parts']
    lines = []
    for part in parts:
        if 'text' in part and part['text'].strip():
            lines.append(part['text'])
        if 'values' in part:
            lines.append(json.dumps(part, ensure_ascii=False))
        for table in [part.get('rows', []), *part.get('tables', [])]:
            lines.extend('\t'.join(row) for row in table)
    return '\n'.join(lines)


def read_attachments(files):
    if not isinstance(files, list) or len(files) > 4:
        raise AttachmentError('К сообщению можно приложить до четырёх файлов.')
    result = []
    size = characters = 0
    for item in files:
        if not isinstance(item, dict):
            raise AttachmentError('Некорректное вложение.')
        name = item.get('name')
        if not isinstance(name, str) or not 1 <= len(name) <= 255:
            raise AttachmentError('Некорректное имя файла.')
        suffix = Path(name).suffix.lower()
        if suffix not in TEXT_FORMATS | OFFICE_FORMATS | {'.pdf'}:
            raise AttachmentError('Формат файла не поддерживается.')
        try:
            data = base64.b64decode(item['data'], validate=True)
        except (KeyError, ValueError, TypeError):
            raise AttachmentError('Не удалось прочитать вложение.') from None
        size += len(data)
        if size > MAX_BYTES:
            raise AttachmentError('Общий размер вложений превышает 4 МиБ.')
        try:
            content = attachment_text(data, suffix)
        except AttachmentError:
            raise
        except Exception:
            raise AttachmentError('Не удалось прочитать документ. Для текстовых файлов используйте UTF-8.') from None
        if not content.strip():
            raise AttachmentError('В документе нет текста для чтения.')
        characters += len(content)
        if characters > MAX_TEXT:
            raise AttachmentError('Текст вложений превышает 80 000 символов. Прикрепите фрагмент.')
        result.append({'name': name, 'text': content})
    return result
