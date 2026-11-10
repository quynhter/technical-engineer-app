"""Подготовка предоставленных пустых форм СП; рабочая БД не используется.

DOCX: изменяется только document.xml, остальные части ZIP сохраняются.
XLSX: печатная сетка переводится в редактируемую таблицу Word с объединениями.
Поля не содержат предположений о фактических работах и полномочиях участников.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, Twips
from lxml import etree
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, range_boundaries

ROOT = Path(__file__).resolve().parents[2]
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
BLANK = re.compile(r'[_＿]{2,}|[.…]{5,}')


def source_label(source):
    return str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source)


def text(el):
    return ''.join(el.xpath('.//w:t/text()', namespaces=NS))


def clean(s):
    return re.sub(r'\s+', ' ', s).strip()


def handwritten_column(label):
    """Дата подписания — данные, а не место для рукописной подписи."""
    value = clean(label).lower()
    return 'подпис' in value and not re.search(r'дата\s+подписания', value)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def put(el, value):
    """Меняет текст первого абзаца, сохраняя свойства абзаца и первого run."""
    p = el if el.tag == qn('w:p') else el.find('w:p', NS)
    if p is None:
        p = etree.SubElement(el, qn('w:p'))
    runs = p.findall('w:r', NS)
    r = runs[0] if runs else etree.SubElement(p, qn('w:r'))
    if not runs:
        default=p.find('w:pPr/w:rPr',NS)
        if default is not None:r.append(deepcopy(default))
    for child in list(r):
        if child.tag != qn('w:rPr'):
            r.remove(child)
    t = etree.SubElement(r, qn('w:t'))
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = value
    for other in p.findall('w:r', NS)[1:]:
        for child in list(other):
            if child.tag != qn('w:rPr'):
                other.remove(child)


def visible_border(cell, sides=('bottom', 'top', 'left', 'right')):
    return any(cell.xpath(f'./w:tcPr/w:tcBorders/w:{side}[@w:val!="nil" and @w:val!="none"]', namespaces=NS) for side in sides)


def xlsx_to_docx(source, target):
    """Воспроизводит печатную область, пропорции столбцов и исходные объединения."""
    book = load_workbook(source, data_only=False)
    doc = Document()
    for sn, sheet in enumerate(book):
        if sn:
            doc.add_section()
        sec = doc.sections[-1]
        landscape = sheet.page_setup.orientation == 'landscape'
        sec.page_width, sec.page_height = (Inches(11.6929), Inches(8.2677)) if landscape else (Inches(8.2677), Inches(11.6929))
        m = sheet.page_margins
        sec.left_margin, sec.right_margin = Inches(m.left), Inches(m.right)
        sec.top_margin, sec.bottom_margin = Inches(m.top), Inches(m.bottom)
        sec.header_distance, sec.footer_distance = Inches(m.header), Inches(m.footer)
        areas = list(sheet.print_area.ranges) if hasattr(sheet.print_area, 'ranges') else []
        bounds = range_boundaries(str(areas[0])) if areas else (1, 1, sheet.max_column, sheet.max_row)
        c0, r0, c1, r1 = bounds
        widths = []
        for col in range(c0, c1 + 1):
            dim = next((v for v in sheet.column_dimensions.values() if v.min and v.min <= col <= v.max), None)
            width = dim.width if dim else sheet.sheet_format.defaultColWidth or 8.43
            widths.append((width * 7 + 5) * .75)
        available = (sec.page_width - sec.left_margin - sec.right_margin) / 12700
        factor = min(1., available / sum(widths))
        widths = [w * factor for w in widths]
        table = doc.add_table(rows=r1-r0+1, cols=c1-c0+1)
        table.autofit = False
        pr = table._tbl.tblPr
        margins = OxmlElement('w:tblCellMar')
        for side in ('top', 'bottom', 'left', 'right'):
            el = OxmlElement('w:' + side); el.set(qn('w:w'), '0'); el.set(qn('w:type'), 'dxa'); margins.append(el)
        pr.append(margins)
        for col, width in zip(table.columns, widths):
            col.width = Pt(width)
        # Cache original cells before merging: python-docx's merged-grid lookup is costly.
        flat = table._cells
        count = c1-c0+1
        cells = [flat[r*count:(r+1)*count] for r in range(r1-r0+1)]
        occupied = {}
        for merge in sorted(sheet.merged_cells.ranges, key=lambda x:(x.min_row,x.min_col)):
            if merge.min_row < r0 or merge.max_row > r1 or merge.min_col < c0 or merge.max_col > c1:
                continue
            cells[merge.min_row-r0][merge.min_col-c0].merge(cells[merge.max_row-r0][merge.max_col-c0])
            for r in range(merge.min_row,merge.max_row+1):
                for c in range(merge.min_col,merge.max_col+1):
                    occupied[r,c] = (merge.min_row,merge.min_col)
        # Excel allows unmerged labels to flow over empty cells. Word needs real spans.
        for r in range(r0,r1+1):
            for c in range(c0,c1+1):
                src=sheet.cell(r,c)
                if (r,c) in occupied or src.value is None or not isinstance(src.value,str): continue
                overflow=len(src.value)*(src.font.sz or 11)*.45*factor > widths[c-c0]*1.2
                if not overflow and (src.alignment.wrap_text or any(getattr(src.border,s).style for s in ('left','right','top','bottom'))): continue
                if src.alignment.horizontal == 'right':
                    start=c
                    while start>c0:
                        nxt=sheet.cell(r,start-1)
                        if (r,start-1) in occupied or nxt.value is not None or any(getattr(nxt.border,s).style for s in ('left','right','top','bottom')):break
                        start-=1
                    if start<c:
                        cells[r-r0][start-c0].merge(cells[r-r0][c-c0])
                        # Read style/value from the original right-aligned anchor.
                        sheet.cell(r,start).value=src.value
                        sheet.cell(r,start)._style=deepcopy(src._style)
                        for cc in range(start,c+1):occupied[r,cc]=(r,start)
                        continue
                end=c
                while end<c1:
                    nxt=sheet.cell(r,end+1)
                    if (r,end+1) in occupied or nxt.value is not None or (not overflow and any(getattr(nxt.border,s).style for s in ('left','right','top','bottom'))): break
                    end+=1
                    # Leave the rest of an underlined scalar row for its value.
                    if overflow and len(src.value)<60 and src.border.bottom.style and sum(widths[c-c0:end-c0+1]) >= len(src.value)*(src.font.sz or 11)*.5*factor+4:break
                if end>c:
                    cells[r-r0][c-c0].merge(cells[r-r0][end-c0])
                    for cc in range(c,end+1):occupied[r,cc]=(r,c)
        # Many downloaded forms draw a single answer line as separate narrow
        # spreadsheet cells. Turn each such line into one Word input cell.
        for r in range(r0,r1+1):
            c=c0
            while c<=c1:
                src=sheet.cell(r,c)
                eligible=(r,c) not in occupied and src.value is None and widths[c-c0]<20 and src.border.bottom.style
                if not eligible:c+=1;continue
                end=c
                while end<c1:
                    nxt=sheet.cell(r,end+1)
                    if (r,end+1) in occupied or nxt.value is not None or widths[end+1-c0]>=20 or not nxt.border.bottom.style:break
                    end+=1
                if end>c:
                    cells[r-r0][c-c0].merge(cells[r-r0][end-c0])
                    for cc in range(c,end+1):occupied[r,cc]=(r,c)
                c=end+1
        for rr,row in enumerate(table.rows):
            row.height = Pt((sheet.row_dimensions[rr+r0].height or sheet.sheet_format.defaultRowHeight or 15) * factor)
            for cc,cell in enumerate(cells[rr]):
                r,c=rr+r0,cc+c0
                if occupied.get((r,c),(r,c)) != (r,c):continue
                src=sheet.cell(r,c)
                p=cell.paragraphs[0]
                pf=p.paragraph_format
                pf.space_before=pf.space_after=Pt(0)
                pf.line_spacing=1.0
                run=p.add_run('' if src.value is None else str(src.value))
                font=run.font
                font.name=src.font.name or 'Arial'
                font.size=Pt((src.font.sz or 11)*factor)
                font.bold=src.font.b; font.italic=src.font.i
                if src.font.u:font.underline=True
                from docx.enum.text import WD_ALIGN_PARAGRAPH
                p.alignment={'center':WD_ALIGN_PARAGRAPH.CENTER,'right':WD_ALIGN_PARAGRAPH.RIGHT,'justify':WD_ALIGN_PARAGRAPH.JUSTIFY}.get(src.alignment.horizontal,WD_ALIGN_PARAGRAPH.LEFT)
                from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
                cell.vertical_alignment={'center':WD_CELL_VERTICAL_ALIGNMENT.CENTER,'bottom':WD_CELL_VERTICAL_ALIGNMENT.BOTTOM}.get(src.alignment.vertical,WD_CELL_VERTICAL_ALIGNMENT.TOP)
                borders=OxmlElement('w:tcBorders')
                for side in ('top','bottom','left','right'):
                    border=getattr(src.border,side)
                    # Merged borders may live on the opposite edge of a range.
                    if not border.style:
                        for merge in sheet.merged_cells.ranges:
                            if merge.min_row==r and merge.min_col==c:
                                edge=sheet.cell(merge.max_row if side=='bottom' else r, merge.max_col if side=='right' else c)
                                border=getattr(edge.border,side);break
                    if border.style:
                        el=OxmlElement('w:'+side);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'000000');borders.append(el)
                cell._tc.get_or_add_tcPr().append(borders)
        last=doc.add_paragraph()
        last.paragraph_format.space_before=last.paragraph_format.space_after=Pt(0)
        last.paragraph_format.line_spacing=Pt(1)
        last.add_run().font.size=Pt(1)
    target.parent.mkdir(parents=True,exist_ok=True)
    doc.save(target)


def adapt(source, target, code, evidence_dir):
    base = source
    if source.suffix == '.xlsx':
        base=evidence_dir / (code + '.source.docx')
        xlsx_to_docx(source,base)
    with ZipFile(base) as z:
        raw=z.read('word/document.xml')
        root=etree.fromstring(raw)
        styles=etree.fromstring(z.read('word/styles.xml'))
        parts={i.filename:hashlib.sha256(z.read(i)).hexdigest() for i in z.infolist()}
    fields=[]
    slots=[]

    def add(key,label,location,required=True):
        label=clean(label) or location
        field={'key':key,'label':label,'kind':'literal','required':required,'value':None}
        # Only unambiguous business references. Dates of work stay individual literals.
        normalized=label.lower().strip('(): .')
        ref={'объект':'object.name','наименование объекта':'object.name','наименование объекта строительства':'object.name','наименование строительного объекта':'object.name','шифр проекта':'project.code','проект №':'project.code','проект n':'project.code','город':'project.city','г':'project.city'}.get(normalized)
        if ref:
            field.update(kind='reference',source=ref);field.pop('value')
        fields.append(field);slots.append({'key':key,'location':location,'label':label})
        return '{{ '+key+' }}'

    # Text slots in any paragraph, including table cells and drawings.
    for pi,p in enumerate(root.xpath('.//w:p',namespaces=NS)):
        ts=p.xpath('.//w:t',namespaces=NS)
        full=''.join(t.text or '' for t in ts)
        matches=list(BLANK.finditer(full))
        if not matches:continue
        # Patching individual nodes preserves formatting and all nontext parts.
        offset=0
        for node in ts:
            original=node.text or ''
            def sub(m):
                key=f'p{pi}_{len(slots)+1}'
                label=clean(BLANK.sub('…',full))
                return add(key,label,f'абзац {pi}, позиция {offset+m.start()}')
            node.text=BLANK.sub(sub,original)
            offset+=len(original)

    tables=root.xpath('.//w:tbl',namespaces=NS)
    for ti,table in enumerate(tables):
        rows=table.findall('w:tr',NS)
        if source.suffix=='.xlsx':
            scalar_labels={'Проект N','Проект №','Объект','Монтажная организация','Регенерационный участок','Сведения о ремонте','Измерительные приборы','Контроль производился дефектоскопическим комплектом','Класс чувствительности контроля','Дефектоскопист','Удостоверение','Вид документации'}
            for ri,row in enumerate(rows):
                cells=row.findall('w:tc',NS)
                if len(cells)==1 and clean(text(cells[0])) in scalar_labels:
                    label=clean(text(cells[0]));key=f'x_{ti}_{ri}'
                    put(cells[0],label+'    '+add(key,label,f'таблица {ti}, строка {ri}, строковое поле'))
        grid_style=bool(table.xpath('./w:tblPr/w:tblBorders/w:insideV[@w:val!="nil" and @w:val!="none"]',namespaces=NS))
        style=table.xpath('./w:tblPr/w:tblStyle/@w:val',namespaces=NS)
        visited=set()
        while style and style[0] not in visited:
            visited.add(style[0])
            definition=styles.xpath('./w:style[@w:styleId=$name]',name=style[0],namespaces=NS)
            if not definition:break
            grid_style |= bool(definition[0].xpath('.//w:tblBorders/w:insideV[@w:val!="nil" and @w:val!="none"]',namespaces=NS))
            style=definition[0].xpath('./w:basedOn/@w:val',namespaces=NS)
        # Direct table formatting overrides the inherited table style, including
        # an explicit "none" used by layout tables and date/signature blocks.
        explicit=table.xpath('./w:tblPr/w:tblBorders/w:insideV',namespaces=NS)
        if explicit:
            grid_style=explicit[0].get(qn('w:val')) not in ('none','nil')
        # Split date cells in the top metadata block of the supplied forms.
        # Other dates (contracts, work, tests) deliberately remain individual.
        for ri,row in enumerate(rows[:10] if ti==0 else []):
            date_cells=row.findall('w:tc',NS)
            values=[clean(text(c)) for c in date_cells]
            quotes=[i for i,v in enumerate(values) if v in ('"','«','»')]
            if len(quotes)!=2 or '20' not in values or not any(v in ('г.','г') for v in values):continue
            first,second=quotes
            candidates=[(first+1,'day_2digits','День подписания'),(second+1,'month_genitive_ru','Месяц подписания'),(values.index('20')+1,'year_4digits','Год подписания')]
            if not all(i<len(values) and not values[i] for i,_,_ in candidates):continue
            for ci,fmt,label in candidates:
                key=f'date_{ri}_{ci}'
                fields.append({'key':key,'label':label,'kind':'reference','source':'act.date_signed','format':fmt,'required':True})
                slots.append({'key':key,'location':f'таблица {ti}, строка {ri}, ячейка {ci}','label':label})
                put(date_cells[ci],'{{ '+key+' }}')
            put(date_cells[values.index('20')],'')
        prev_heading=''
        for sibling in table.itersiblings(preceding=True):
            if clean(text(sibling)):
                prev_heading=clean(text(sibling))[-200:];break
        loop_rows=set()
        # A run of fully blank grid rows is a measurement/log table, not a signature.
        runs=[];current=[]
        for ri,row in enumerate(rows):
            cells=row.findall('w:tc',NS)
            blank=len(cells)>=3 and all(not clean(text(c)) for c in cells)
            grid=blank and (grid_style or all(visible_border(c,('left','right')) for c in cells))
            no_vertical=all(not c.xpath('./w:tcPr/w:vMerge',namespaces=NS) for c in cells)
            signature=ri>0 and 'подпис' in clean(text(rows[ri-1])).lower()
            if grid and no_vertical and not signature:
                if current and len(rows[current[-1]].findall('w:tc',NS))!=len(cells):runs.append(current);current=[]
                current.append(ri)
            else:
                if current:runs.append(current);current=[]
        if current:runs.append(current)
        for group in runs:
            first=group[0];row=rows[first];cells=row.findall('w:tc',NS)
            key=f'rows_{ti}_{first}'
            headers=[]
            for ci,cell in enumerate(cells):
                labels=[]
                for previous in rows[max(0,first-5):first]:
                    before=previous.findall('w:tc',NS)
                    if ci<len(before):
                        label=clean(text(before[ci]))
                        if label and not label.isdigit() and label not in labels: labels.append(label)
                label=' / '.join(labels)[-250:] or f'Графа {ci+1}'
                handwritten = handwritten_column(label)
                headers.append({'key':f'c{ci+1}','label':label,'kind':'reference','source':f'item.c{ci+1}','required':'примечан' not in label.lower() and not handwritten})
                if not handwritten:put(cell,'{{ item.c'+str(ci+1)+' }}')
            fields.append({'key':key,'label':prev_heading or f'Таблица {ti+1}','kind':'table','required':True,'value':None,'fields':headers})
            slots.append({'key':key,'location':f'таблица {ti}, строки {group}','label':' / '.join(h['label'] for h in headers)})
            start=deepcopy(row);end=deepcopy(row)
            for el in (start,end):
                for c in el.findall('w:tc',NS):put(c,'')
            put(start.findall('w:tc',NS)[0],'{%tr for item in '+key+' %}')
            put(end.findall('w:tc',NS)[0],'{%tr endfor %}')
            row.addprevious(start);row.addnext(end)
            for ri in group[1:]:table.remove(rows[ri])
            loop_rows.update(group)

        for ri,row in enumerate(rows):
            if ri in loop_rows:continue
            cells=row.findall('w:tc',NS)
            for ci,cell in enumerate(cells):
                if clean(text(cell)):continue
                if cell.xpath('./w:tcPr/w:vMerge[not(@w:val="restart")]',namespaces=NS):continue
                fixed_values=bool(cells and clean(text(cells[0])) in ('По проекту','Фактически') and ci>0)
                if not (grid_style or fixed_values or visible_border(cell,('bottom',))):continue
                below=[]
                if ri+1<len(rows):
                    next_cells=rows[ri+1].findall('w:tc',NS)
                    if ci<len(next_cells):below=[clean(text(next_cells[ci]))]
                before=[clean(text(c)) for c in cells[:ci] if clean(text(c))]
                caption=below[0] if below and below[0] else ''
                label=caption or (before[-1] if before else prev_heading)
                # Blank handwritten signature lines remain blank.
                if re.fullmatch(r'\(?подпис[ьиь]+\)?',caption.lower()) or ('подпис' in label.lower() and not any(s in label.lower() for s in ('фамил','ф.и.','должност','инициал'))):continue
                if 'Подписи' in text(table) and label.startswith('От '):continue
                key=f't{ti}_r{ri}_c{ci}'
                put(cell,add(key,label,f'таблица {ti}, строка {ri}, ячейка {ci}',required='примечан' not in label.lower()))
    if not fields:
        raise ValueError(f'Не найдены поля: {source}')
    if code=='СП_77_А_20':
        labels={'t2_r0_c0':'Недоделки, подлежащие устранению: строка 1',
                't2_r1_c0':'Недоделки, подлежащие устранению: строка 2',
                't2_r2_c0':'Недоделки, подлежащие устранению: строка 3',
                't3_r0_c1':'Представитель заказчика: должность и Ф.И.О.'}
        for field in fields:
            if field['key'] in labels:field['label']=labels[field['key']]
            if field['key'] in ('t2_r1_c0','t2_r2_c0'):field['required']=False
    if code=='СП_77_А_24':
        formats={'p32_1':('День подписания','day_2digits'),
                 'p32_2':('Месяц подписания','month_genitive_ru'),
                 'p32_3':('Год подписания','year_4digits')}
        labels={'t0_r10_c1':'Представитель генподрядчика (заказчика): должность и Ф.И.О.',
                't0_r12_c1':'Представитель монтажной организации: должность и Ф.И.О.',
                't0_r19_c1':'Представитель монтажной организации: должность и Ф.И.О.; подпись от руки',
                't0_r21_c1':'Представитель генподрядчика (заказчика): должность и Ф.И.О.; подпись от руки'}
        for field in fields:
            if field['key'] in formats:
                label,fmt=formats[field['key']]
                field.update(label=label,kind='reference',source='act.date_signed',format=fmt)
                field.pop('value',None)
            if field['key'] in labels:field['label']=labels[field['key']]
            if field['kind']=='table':
                field['label']='Выполненные работы и технические средства, переданные заказчику'
                for column,label in zip(field['fields'],('№ п/п','Выполненные и принятые заказчиком работы','Технические средства систем автоматизации, переданные заказчику','Примечание')):
                    column['label']=label
        for node in root.xpath('.//w:t',namespaces=NS):
            if node.text:node.text=node.text.replace('20{{ p32_3 }}','{{ p32_3 }}')
    # A fixed source row height must not clip a value or the draft diagnostic.
    for row in root.xpath('.//w:tr',namespaces=NS):
        if '{{' not in text(row):continue
        for height in row.xpath('./w:trPr/w:trHeight[@w:hRule="exact"]',namespaces=NS):
            height.set(qn('w:hRule'),'atLeast')
    target.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(base) as zin,ZipFile(target,'w') as zout:
        for info in zin.infolist():
            value=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True) if info.filename=='word/document.xml' else zin.read(info)
            zout.writestr(info,value)
    write_json(evidence_dir/(code+'.slots.json'),{'source':source_label(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'parts':parts,'slots':slots})
    return fields


def prepare(evidence_dir, source_dir, only_codes):
    if not source_dir.is_dir():
        raise ValueError('Укажите папку исходных форм, содержащую подпапки СП')
    if not only_codes:
        raise ValueError('Укажите коды форм, которые нужно подготовить')
    evidence_dir.mkdir(parents=True,exist_ok=True)
    catalog_path=ROOT/'app/templates/catalog.json'
    catalog=json.loads(catalog_path.read_text())
    known={f['code'] for f in catalog}
    seen={}
    report=[]
    for source in sorted(source_dir.glob('СП*/*')):
        if source.suffix not in ('.xlsx','.docx'):continue
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        if digest in seen:
            report.append({'source':source_label(source),'duplicate_of':seen[digest]});continue
        seen[digest]=source_label(source)
        if source.suffix=='.docx':
            d=Document(source);head=' '.join(p.text for p in d.paragraphs[:4])
        else:
            w=load_workbook(source);s=w.active
            head=' '.join(str(c.value) for row in s.iter_rows(min_row=1,max_row=3) for c in row if c.value is not None)
        appendix=re.search(r'Приложение\s+([А-ЯA-Zа-яa-z0-9.]+)',head)
        if not appendix:raise ValueError(f'Не найдено приложение: {source}')
        number=source.parent.name.split()[1].split('.')[0].replace('-','_')
        suffix=appendix.group(1).strip('.').replace('.','_')
        # Three distinct supplied forms all bear A.19. Keep explicit distinct codes.
        if suffix=='А_19':
            suffix += '_МУФТА' if 'муфту' in source.stem else '_УЧАСТОК' if 'участка' in source.stem else '_ИЗМЕРЕНИЯ'
        code='СП_'+number+'_'+suffix
        if code=='СП_77_А_21':
            report.append({'source':source_label(source),'preserved_template':'app/templates/СП 77.13330.2016/СП_77_А_21.docx','note':'Существующая рабочая форма сохранена; отдельная регистрация не заменяется.'})
            continue
        if only_codes and code not in only_codes:
            continue
        template=Path('app/templates')/source.parent.name/(code+'.docx')
        fields_path=Path('app/forms')/source.parent.name/(code+'.fields.json')
        fields=adapt(source,ROOT/template,code,evidence_dir)
        write_json(ROOT/fields_path,fields)
        entry={'code':code,'name':source.stem.replace(' (1)',''),'group':'statement' if source.stem.startswith(('Журнал','Ведомость','Опись','Список')) else 'act','set':source.parent.name,'template':str(template),'fields':str(fields_path),'source':source_label(source),'source_sha256':digest}
        if code in known:
            catalog=[entry if f['code']==code else f for f in catalog]
        else:catalog.append(entry);known.add(code)
        report.append(entry)
    write_json(catalog_path,catalog)
    write_json(evidence_dir/'report.json',report)
    for folder in sorted(source_dir.glob('СП*')):
        entries=[f for f in catalog if f.get('set')==folder.name]
        if only_codes and not any(f['code'] in only_codes for f in entries):
            continue
        lines=[f'# Поля предоставленных форм {folder.name}', '',
               'Шаблоны подготовлены по локальным пустым бланкам. Это адаптация исходников,',
               'а не проверка актуальности и применимости нормативного документа.',
               'Оригиналы сохраняются без изменений; SHA-256 указан в общем catalog.json.', '',
               'Регистрируйте только выбранные формы через form-register. Рабочая БД',
               'при подготовке библиотеки не изменяется. Замена существующей регистрации',
               'требует проверки её полей и согласования.', '',
               'Координаты t/r/c и p нумеруются с нуля в рабочем DOCX. Для XLSX это',
               'строки/ячейки преобразованной печатной сетки Word. Даты работ и испытаний',
               'задаются индивидуально; общие даты раздела автоматически не подставляются.',
               'Незаданные значения — null. Подпись от руки не генерируется. Сведения',
               'об участниках с составными подписями вводятся явно по источнику; назначения',
               'и полномочия из положения строки не выводятся. Таблицы измерений — value,',
               'а не resources; проектные количества не становятся фактом.', '',
               'Перед финалом подтвердите статические утверждения бланка и проверьте',
               'вёрстку на фактических данных. Произвольная длина полей меняет число страниц.', '']
        for f in entries:
            lines += [f'## {f["code"]} — {f["name"]}', '',f'Исходник: `{f["source"]}`.', '', '| Ключ | Назначение | Источник | Обязательное |','|---|---|---|---|']
            for field in json.loads((ROOT/f['fields']).read_text()):
                label=field['label'].replace('|','/').replace('\n',' ')
                origin=field.get('source','индивидуальное значение' if field['kind']!='table' else 'индивидуальные строки таблицы')
                lines.append(f'| `{field["key"]}` | {label} | {origin} | {"да" if field.get("required") else "нет"} |')
                for c in field.get('fields',[]):lines.append(f'| ↳ `{c["key"]}` | {c["label"].replace("|","/")} | {c["source"]} | {"да" if c.get("required") else "нет"} |')
            lines.append('')
        if folder.name=='СП 77.13330.2016':
            lines+=['## Сохранённая ведомость А.21','', 'Рабочий `СП_77_А_21.docx` и его настройки не заменены.',
                    'Три предоставленных исходника помечены приложением А.19; для них',
                    'использованы разные коды с суффиксами МУФТА, УЧАСТОК и ИЗМЕРЕНИЯ.',
                    'Обозначения внутри бланков сохранены, их нормативную нумерацию нужно',
                    'сверять при выборе формы. Повторно скачанный дубль ведомости удалён',
                    'по указанию пользователя; основной исходник сохранён.','']
        if folder.name=='СП 70.13330.2012':
            lines+=['Повторно скачанный дубль журнала болтовых соединений с «(1)» удалён', 'по указанию пользователя; основной исходник и шаблон сохранены.','']
        (ROOT/'app/templates'/folder.name/'ПОЛЯ.md').write_text('\n'.join(lines),encoding='utf-8')
    (evidence_dir/'artifact.md').write_text('# Контракт адаптации\n\n'
        'Каждый *.slots.json хранит путь и SHA-256 оригинала, хеши частей пакета и карту полей.\n'
        'DOCX: сохраняются все части ZIP кроме document.xml, все секции, стили, заголовки,\n'
        'изображения, исходные свойства абзацев и ячеек. Меняются только заполняемые места;\n'
        'серии пустых строк с сеткой заменяются штатным циклом docxtpl.\n'
        'XLSX: сохранены исходные объединения, пропорции ширин, ориентация, поля страницы,\n'
        'шрифты, выравнивание, границы и минимальные высоты строк; печатная сетка — таблица Word.\n'
        'При переносе подписи остаются пустыми. Excel-формулы не пересчитываются.\n'
        'Все таблицы/секции подлежат проверке рендером и изображениями.\n',encoding='utf-8')
    print(f'Подготовлено {sum("code" in r for r in report)} шаблонов; отчёт: {evidence_dir}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir',type=Path,required=True)
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--code',action='append',required=True,help='Подготовить только указанные коды; можно повторить')
    args=parser.parse_args()
    prepare(args.evidence_dir.resolve(), args.source_dir.resolve(), set(args.code))
