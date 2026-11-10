"""Импорт ведомости с явным сопоставлением колонок и предварительной проверкой."""
import base64
import csv
import hashlib
import io
import json
import math
import re
import secrets
import tempfile
import zipfile
from xml.etree import ElementTree
from pathlib import Path

from .db import required_text,atomic_operation
from .resources import CATEGORIES,add_resource,quantity

FIELDS={'name':'Наименование','unit':'Единица измерения','category':'Категория','spec_num':'Позиция спецификации',
        'type_mark':'Тип / марка','manufacturer':'Изготовитель','supplier':'Поставщик','serial_num':'Заводские номера',
        'qty_proj':'Количество по проекту','qty_received':'Приход','note':'Примечание'}
MAX_ROWS=10000
MAX_COLUMNS=100
MAX_CELLS=(MAX_ROWS+100)*MAX_COLUMNS


def validate_xlsx(content):
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            if sum(i.file_size for i in z.infolist())>64*1024*1024:
                raise ValueError('Распакованный Excel слишком велик')
            for name in z.namelist():
                if not name.startswith('xl/worksheets/') or not name.endswith('.xml'): continue
                count=0
                with z.open(name) as source:
                    for _, element in ElementTree.iterparse(source, events=('end',)):
                        if element.tag.rsplit('}',1)[-1]=='c':
                            count+=1
                            ref=element.get('r','')
                            match=re.fullmatch(r'([A-Z]{1,3})([0-9]{1,7})',ref)
                            if not match: raise ValueError('Некорректный адрес ячейки Excel')
                            column=0
                            for char in match[1]: column=column*26+ord(char)-64
                            if column>MAX_COLUMNS: raise ValueError('Допускается до 100 колонок')
                            if int(match[2])>MAX_ROWS+100 or count>MAX_CELLS:
                                raise ValueError('Слишком много строк или ячеек Excel')
                        element.clear()
    except (zipfile.BadZipFile, ElementTree.ParseError) as error:
        raise ValueError('Файл не является читаемой книгой XLSX') from error


def sheets(content,filename):
    suffix=Path(filename).suffix.lower()
    if suffix=='.csv': return ['CSV']
    if suffix!='.xlsx': raise ValueError('Загрузите .xlsx или .csv')
    validate_xlsx(content)
    from openpyxl import load_workbook
    book=load_workbook(io.BytesIO(content),read_only=True,data_only=False)
    try: return book.sheetnames
    finally: book.close()


def table(content,filename,sheet,header_row):
    if type(header_row) is not int or not 1<=header_row<=100: raise ValueError('Строка заголовков: от 1 до 100')
    if Path(filename).suffix.lower()=='.csv':
        try: text=content.decode('utf-8-sig')
        except UnicodeDecodeError: text=content.decode('cp1251')
        try: dialect=csv.Sniffer().sniff(text[:8192],delimiters=';,\t,')
        except csv.Error: dialect=csv.excel
        rows=[]
        for row in csv.reader(io.StringIO(text),dialect):
            if len(row)>MAX_COLUMNS: raise ValueError('Допускается до 100 колонок')
            rows.append(row)
            if len(rows)>MAX_ROWS+100: raise ValueError('Слишком много строк; предел — 10000')
    else:
        validate_xlsx(content)
        from openpyxl import load_workbook
        book=load_workbook(io.BytesIO(content),read_only=True,data_only=False)
        try:
            if sheet not in book.sheetnames: raise ValueError('Лист не найден')
            ws=book[sheet]
            if (ws.max_column or 0)>MAX_COLUMNS: raise ValueError('Допускается до 100 колонок')
            if (ws.max_row or 0)>MAX_ROWS+100: raise ValueError('Слишком много строк; предел — 10000')
            rows=[]
            cell_count=0
            # Bound iteration even if worksheet dimensions are missing or misleading.
            for cells in ws.iter_rows(max_col=MAX_COLUMNS+1):
                if cells[-1].value is not None: raise ValueError('Допускается до 100 колонок')
                cells=cells[:MAX_COLUMNS]
                cell_count+=len(cells)
                if cell_count>MAX_CELLS: raise ValueError('Слишком много ячеек')
                row=[]
                for cell in cells:
                    value=cell.value
                    if type(value) in (int,float) and math.isfinite(value) and value>=0 and value==int(value) and re.fullmatch(r'0+',cell.number_format or ''):
                        value=str(int(value)).zfill(len(cell.number_format))
                    row.append(value)
                while row and row[-1] is None: row.pop()
                rows.append(row)
                if len(rows)>MAX_ROWS+100: raise ValueError('Слишком много строк; предел — 10000')
        finally: book.close()
    if header_row>len(rows): raise ValueError('Строка заголовков отсутствует')
    headers=[str(v).strip() if v is not None else '' for v in rows[header_row-1]]
    if len(headers)>100: raise ValueError('Допускается до 100 колонок')
    return headers,[(n,row) for n,row in enumerate(rows[header_row:],header_row+1) if any(v not in (None,'') for v in row)]


def stage(c,pid,data):
    filename=required_text(data.get('filename'),'Имя файла')
    if Path(filename).name!=filename or '\\' in filename: raise ValueError('Некорректное имя файла')
    content=base64.b64decode(data['content'],validate=True)
    if not content or len(content)>8*1024*1024: raise ValueError('Размер ведомости — до 8 МБ')
    names=sheets(content,filename)
    identity=secrets.token_urlsafe(24)
    c.execute('INSERT INTO resource_imports(id,project_id,filename,sha256,content) VALUES(?,?,?,?,?)',
              (identity,pid,filename,hashlib.sha256(content).hexdigest(),content))
    return inspect(c,pid,dict(import_id=identity,sheet=names[0],header_row=1))


def inspect(c,pid,data):
    record=c.execute('SELECT * FROM resource_imports WHERE id=? AND project_id=?',(data.get('import_id'),pid)).fetchone()
    if not record: raise ValueError('Файл импорта не найден в этом разделе')
    names=sheets(record['content'],record['filename'])
    sheet=data.get('sheet') or names[0];header=data.get('header_row',1)
    headers,raw=table(record['content'],record['filename'],sheet,header)
    mapping=data.get('mapping',{})
    if not isinstance(mapping,dict) or set(mapping)-set(FIELDS): raise ValueError('Неизвестные поля сопоставления')
    if any(type(v) is not int or not 0<=v<len(headers) for v in mapping.values()) or len(set(mapping.values()))!=len(mapping):
        raise ValueError('Каждая колонка должна быть сопоставлена одному полю')
    defaults=data.get('defaults',{})
    if not isinstance(defaults,dict) or set(defaults)-{'category','unit'} or any(v is not None and not isinstance(v,str) for v in defaults.values()): raise ValueError('Неверные значения по умолчанию')
    category_map=data.get('category_map',{})
    if not isinstance(category_map,dict) or any(not isinstance(k,str) or v not in CATEGORIES for k,v in category_map.items()):
        raise ValueError('Сопоставьте категории файла с категориями ресурсов')
    category_values=sorted({str(row[mapping['category']]).strip() for _,row in raw if 'category' in mapping and mapping['category']<len(row) and row[mapping['category']] not in (None,'')})
    preview=[]
    for number,row in raw:
        values={k:(row[i] if i<len(row) else None) for k,i in mapping.items()}
        errors=[]
        for key in FIELDS:
            v=values.get(key)
            if key in ('qty_proj','qty_received'):
                try:
                    if isinstance(v,str): v=v.replace('\u00a0','').replace(' ','').replace(',','.') or None
                    values[key]=quantity(v,FIELDS[key])
                except ValueError as e: errors.append(str(e))
            else:
                if v is not None: values[key]=str(v).strip() or None
        for key in ('name','unit','category'):
            if not values.get(key): values[key]=defaults.get(key) or None
            if not values.get(key): errors.append('Не заполнено: '+FIELDS[key])
        if values.get('category') in category_map: values['category']=category_map[values['category']]
        if values.get('category') and values['category'] not in CATEGORIES: errors.append('Категория не входит в четыре разрешённые категории')
        # Формулы не исполняются и не превращаются в реквизиты/количества.
        if any(isinstance(row[i],str) and row[i].startswith('=') for i in mapping.values() if i<len(row)):
            errors.append('В сопоставленной ячейке формула; замените её значением в копии ведомости')
        existing=c.execute('SELECT * FROM resource_import_rows WHERE project_id=? AND sha256=? AND sheet=? AND row_num=?',
            (pid,record['sha256'],sheet,number)).fetchone()
        encoded=json.dumps(values,ensure_ascii=False,sort_keys=True,allow_nan=False)
        if existing and existing['data_json']!=encoded: errors.append('Эта строка уже импортирована с другим сопоставлением; повторная запись не разрешена')
        preview.append({'row':number,'values':values,'errors':errors,'duplicate':bool(existing)})
    result={'import_id':record['id'],'filename':record['filename'],'sha256':record['sha256'],'sheets':names,'sheet':sheet,
            'header_row':header,'headers':headers,'category_values':category_values,'sample':[[str(v) if v is not None else '' for v in row] for _,row in raw[:10]],
            'fields':FIELDS,'rows':preview,'count':len(preview),'valid':bool(preview) and all(not r['errors'] for r in preview),
            'new_count':sum(not r['duplicate'] for r in preview)}
    payload={'sha256':record['sha256'],'sheet':sheet,'header_row':header,'rows':preview}
    result['preview_token']=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return result


@atomic_operation
def commit(c,pid,data,archive_root):
    view=inspect(c,pid,data)
    if data.get('preview_token')!=view['preview_token']: raise ValueError('Предпросмотр изменился. Проверьте строки ещё раз')
    if not view['valid']: raise ValueError('Исправьте ошибки всех строк перед импортом')
    has_receipts=any(r['values'].get('qty_received') is not None and not r['duplicate'] for r in view['rows'])
    if has_receipts and data.get('confirm_receipts') is not True: raise ValueError('Подтвердите, что колонка «Приход» содержит реально принятые количества')
    record=c.execute('SELECT * FROM resource_imports WHERE id=?',(view['import_id'],)).fetchone()
    attachment=record['attachment_id']
    if attachment is None:
        from .archive import import_file,link_file
        with tempfile.TemporaryDirectory(prefix='itd-resource-import-') as folder:
            path=Path(folder)/record['filename'];path.write_bytes(record['content'])
            imported=import_file(c,archive_root=archive_root,source=path,doc_type='other',title=record['filename'])
        attachment=imported['id'];link_file(c,attachment_id=attachment,entity='project',entity_id=pid)
        c.execute('UPDATE resource_imports SET attachment_id=? WHERE id=?',(attachment,view['import_id']))
    ids=[]
    from .manual import add_supply
    for row in view['rows']:
        if row['duplicate']: continue
        v=dict(row['values']);received=v.pop('qty_received',None);serial=v.pop('serial_num',None)
        rid=add_resource(c,project_id=pid,serial_numbers=serial.splitlines() if serial else None,**v)
        c.execute('INSERT INTO resource_sources(project_id,resource_id,attachment_id,source_key,sheet,locator) VALUES(?,?,?,?,?,?)',
                  (pid,rid,attachment,f"table:{view['sheet']}:header:{view['header_row']}:row:{row['row']}",view['sheet'],f"Строка {row['row']}"))
        if received is not None:
            add_supply(c,pid,dict(resource_id=rid,source_key=f"excel:{view['sha256']}:{view['sheet']}:{row['row']}",quantity=received,
                unit=v['unit'],supplier=v.get('supplier'),status='accepted',attachment_id=attachment,
                source=f"{view['filename']}, {view['sheet']}, строка {row['row']}; приход подтверждён пользователем"))
        # qty_fact остаётся неизвестным: проект/приход не подтверждают монтаж.
        c.execute('INSERT INTO resource_import_rows VALUES(?,?,?,?,?,?,?)',(pid,view['sha256'],view['sheet'],view['header_row'],row['row'],rid,
            json.dumps(row['values'],ensure_ascii=False,sort_keys=True,allow_nan=False)))
        ids.append(rid)
    from .changes import log_event
    log_event(c,'resource-import',entity='projects',entity_id=pid,after={'resource_ids':ids,'attachment_id':attachment,'sha256':view['sha256']})
    from .archive import publish_project_file
    project_path=publish_project_file(c,attachment_id=attachment,project_id=pid,archive_root=archive_root)
    return {'project_path':project_path,'imported':len(ids),'skipped':len(view['rows'])-len(ids),'resource_ids':ids,'attachment_id':attachment}
