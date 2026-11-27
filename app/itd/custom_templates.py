"""Настраиваемые бланки DOCX и источники подстановки."""
import base64
import io
import json
import re
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from xml.etree import ElementTree
from .acts import register_form
from .document_bindings import COLUMNS, EXCLUDE, TABLES, value_type

NAME = r'[A-Za-z][A-Za-z0-9_]*'
TEMPLATE_CODE = re.compile(r'TPL_[a-f0-9]{32}')
MARKER = re.compile(r'{{\s*(' + NAME + r'(?:\.' + NAME + r')*)\s*}}')
LOOP = re.compile(r'{%\s*(?:tr\s+)?for\s+(' + NAME + r')\s+in\s+(' + NAME + r')\s*%}')
END = re.compile(r'{%\s*(?:tr\s+)?endfor\s*%}')
IF_FIELD = re.compile(r'{%\s*if\s+(' + NAME + r')\s*%}')
END_IF = re.compile(r'{%\s*endif\s*%}')
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def table_rows(root, part_name, *, include_single=False):
    """Associate implicit row templates with their collection in document order."""
    for index, table in enumerate(root.iter(W+'tbl'), 1):
        for row in table.findall(W+'tr'):
            cells = row.findall(W+'tc')
            texts = [' '.join(''.join(t.text or '' for t in p.iter(W+'t'))
                              for p in cell.findall(W+'p')) for cell in cells]
            marked_cells = [text for text in texts if MARKER.search(text)]
            markers = MARKER.findall(' '.join(marked_cells))
            # A layout cell can contain several placeholders, even across paragraphs.
            if not include_single and len(marked_cells) < 2:
                continue
            prefixes = {key.split('.')[0] for key in markers if '.' in key}
            if len(prefixes) == 1 and not any(key.count('.') > 1 for key in markers):
                prefix = next(iter(prefixes))
                if prefix in ('object', 'project', 'objects', 'projects', 'form', 'document'):
                    continue
                source = prefix
            elif not prefixes and set(markers) - {'serial_number'} and ('serial_number' in markers or
                                   len(cells) == 1 or sum(bool(MARKER.search(text)) for text in texts) > 1):
                part = part_name.rsplit('/', 1)[-1].split('.')[0]
                source = f'table_{index}' if part == 'document' else f'table_{part}_{index}'
            else:
                continue
            if include_single or len({key.removeprefix(source+'.') for key in markers}) > 1:
                yield row, source


def inspect_doc(data):
    try:
        with ZipFile(io.BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 64*1024*1024:
                raise ValueError('Слишком большой распакованный DOCX')
            if 'word/document.xml' not in archive.namelist():
                raise ValueError('Выберите документ DOCX')
            fields = {}
            conditions = set()
            for name in archive.namelist():
                if not name.startswith('word/') or not name.endswith('.xml'):
                    continue
                root = ElementTree.fromstring(archive.read(name))
                row_fields = {}
                for tr, source in table_rows(root, name):
                    for cell in tr.findall(W+'tc'):
                        row_fields.update(dict.fromkeys(cell.findall(W+'p'), source))
                loop = None
                for para in root.iter(W+'p'):
                    text = ''.join(t.text or '' for t in para.iter(W+'t'))
                    condition_depth = 0
                    for tag in re.findall(r'{{.*?}}|{%.*?%}', text):
                        if match := LOOP.fullmatch(tag):
                            if loop: raise ValueError('Вложенные циклы не поддерживаются')
                            loop = match.groups()
                            fields.setdefault(loop[1], {'key':loop[1], 'kind':'table','source':loop[1],'fields':[]})
                        elif END.fullmatch(tag):
                            loop = None
                        elif match := IF_FIELD.fullmatch(tag):
                            conditions.add(match[1])
                            condition_depth += 1
                        elif END_IF.fullmatch(tag):
                            if not condition_depth:
                                raise ValueError('Условие и его конец должны находиться в одном абзаце')
                            condition_depth -= 1
                        elif match := MARKER.fullmatch(tag):
                            key = match[1]
                            table = loop
                            if table is None and para in row_fields:
                                table = (row_fields[para],row_fields[para])
                            if table:
                                fields.setdefault(table[1],{'key':table[1],'kind':'table','source':table[1],'fields':[]})
                                col = key.removeprefix(table[0]+'.')
                                if '.' in col: raise ValueError('Некорректное поле строки')
                                cols = fields[table[1]]['fields']
                                if not any(f['key']==col for f in cols):
                                    cols.append({'key':col,'kind':'reference','source':'row.number' if col=='serial_number' else 'item.'+col,'expression':col!='serial_number'})
                            else:
                                if key == 'serial_number':
                                    continue
                                path = key
                                if '.' in key:
                                    key = 'field_' + path.encode().hex()
                                field = {'key':key,'kind':'literal','value':'','expression':True}
                                if key == 'date':
                                    field.update(label='Дата подписания', value_type='date', mask='dd.mm.yyyy')
                                if key == 'act_num':
                                    field.update(label='Номер документа')
                                if key != path:
                                    field.update(marker_path=path,label=path)
                                fields.setdefault(key,field)
                        else:
                            raise ValueError('Документ содержит неподдерживаемое выражение')
                    if condition_depth:
                        raise ValueError('Условие и его конец должны находиться в одном абзаце')
                if loop: raise ValueError('Не найден конец таблицы')
            if not conditions.issubset(key for key, field in fields.items() if field['kind'] == 'literal'):
                raise ValueError('Условие должно ссылаться на обычное поле бланка')
            return list(fields.values())
    except (BadZipFile, ElementTree.ParseError) as error:
        raise ValueError('Не удалось прочитать DOCX') from error


def schema(c):
    return {table:{'label':label,'columns':[
        {'key':r['name'],'label':COLUMNS.get(r['name'],r['name']),
         'type':value_type(r['name'],0 if r['type'] in ('INTEGER','REAL') else '')}
        for r in c.execute(f'PRAGMA table_info({table})')
        if r['name'] not in EXCLUDE and (r['name']=='nrs_id' or not r['name'].endswith(('_id','_json','_path','_sha256')))]}
        for table,label in TABLES.items()}


def list_templates(c):
    return [dict(r,fields=json.loads(r['fields'])) for r in c.execute("""SELECT t.*,d.name,d.fields
        FROM document_templates t JOIN document_types d USING(code) WHERE t.deleted=0 ORDER BY t.form_set,d.name""")]


def write_file(path, content):
    import tempfile
    from pathlib import Path
    if content is None:
        path.unlink(missing_ok=True)
        return
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as temp:
        staged = Path(temp.name)
    try:
        staged.write_bytes(content)
        staged.replace(path)
    finally:
        staged.unlink(missing_ok=True)


def change_file(c, directory, code, revision, content):
    path = directory/(code+'.docx')
    if path.is_symlink():
        raise ValueError('Недопустимый путь шаблона')
    previous = path.read_bytes() if path.exists() else None
    if hasattr(c,'template_changes'):
        c.template_changes.append((code,revision,path,previous))
    write_file(path,content)


def restore_rolled_back_changes(c):
    for code,revision,path,previous in reversed(c.template_changes):
        saved = c.execute('SELECT revision FROM document_templates WHERE code=?',(code,)).fetchone()
        if not saved or saved[0]<revision:
            write_file(path,previous)


def field_shape(fields):
    return [(field['key'], field_shape(field['fields']) if field['kind'] == 'table' else None) for field in fields]


def template_operation(c, op, data, directory):
    from .db import required_text
    code = data.get('code')
    if code:
        row = c.execute('SELECT * FROM document_templates WHERE code=? AND deleted=0',(code,)).fetchone()
        if not row or not TEMPLATE_CODE.fullmatch(code): raise ValueError('Шаблон не найден')
    if op in ('download','delete') and not code:
        raise ValueError('Выберите шаблон')
    if op=='download':
        return {'content':base64.b64encode((directory/(code+'.docx')).read_bytes()).decode(),'name':row['original_name']}
    content = base64.b64decode(data['content'], validate=True) if data.get('content') else None
    detected = inspect_doc(content) if content is not None else None
    if op=='inspect':
        if detected is None:
            if not code:
                raise ValueError('Добавьте DOCX')
            detected = inspect_doc((directory/(code+'.docx')).read_bytes())
        return {'fields':detected,'schema':schema(c),'row_detection_version':2}
    if code and data.get('revision') != row['revision']: raise ValueError('Шаблон уже изменён')
    if op=='delete':
        c.execute('UPDATE document_templates SET deleted=1,revision=revision+1 WHERE code=?',(code,))
        if not c.execute('SELECT 1 FROM acts WHERE act_type=?',(code,)).fetchone():
            change_file(c,directory,code,row['revision']+1,None)
        return {'ok':True}
    name = required_text(data.get('name'),'наименование')
    form_set = required_text(data.get('form_set'),'комплект форм')
    filename = required_text(data.get('original_name'),'файл шаблона')
    if not filename.lower().endswith('.docx'):
        raise ValueError('Выберите документ DOCX')
    if not code and content is None: raise ValueError('Добавьте DOCX')
    if detected is None:
        detected = inspect_doc((directory/(code+'.docx')).read_bytes())
    if field_shape(detected)!=field_shape(data['fields']):
        raise ValueError('Поля настройки не совпадают с полями файла')
    code = code or getattr(c, 'preview_template_code', None) or 'TPL_'+uuid4().hex
    register_form(c,code=code,name=name,fields=data['fields'],form_group='act')
    c.execute("""INSERT INTO document_templates(code,form_set,original_name) VALUES(?,?,?)
        ON CONFLICT(code) DO UPDATE SET form_set=excluded.form_set,original_name=excluded.original_name,
        revision=revision+1""",(code,form_set,filename))
    if content is not None:
        change_file(c,directory,code,row['revision']+1 if data.get('code') else 1,content)
    return {'code':code}
