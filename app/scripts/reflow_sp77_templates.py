"""Перевёрстка СП 77 без изменения ключей зарегистрированных форм.

Исходная рабочая редакция хранится в ZIP, нормативные источники и их хеши
остаются в catalog.json. Повторный запуск всегда начинает с этой редакции.
"""
from copy import deepcopy
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree as E

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'app/templates/СП 77.13330.2016'
ARCHIVE = ROOT / 'app/docs/template-layout/sp77-before-reflow.zip'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + NS['w'] + '}'
# Только содержательные таблицы. Индексы относятся к архивной редакции.
DATA = {'7': [(16, 23)], '8': [(18, 23), (28, 36)], '9': [],
        '10': [(10, 24)], '11': [], '13': [(6, 10)], '14': [(14, 18)],
        '15': [(9, 13)], '16': [(18, 24), (28, 36)], '17': [(12, 18)],
        '18': [(25, 31)], '19_ИЗМЕРЕНИЯ': [], '19_МУФТА': [(20, 29)],
        '19_УЧАСТОК': [(12, 20)], '24': [(14, 19)]}


def element(tag, **attrs):
    return E.Element(W + tag, {W + k: str(v) for k, v in attrs.items()})


def text(node):
    return ''.join(node.xpath('.//w:t/text()', namespaces=NS))


def paragraph(value, *, align='left', size=22, bold=False):
    p = element('p')
    pr = E.SubElement(p, W + 'pPr')
    pr.append(element('jc', val=align))
    pr.append(element('spacing', after=80, line=240, lineRule='auto'))
    r = E.SubElement(p, W + 'r')
    rp = E.SubElement(r, W + 'rPr')
    rp.append(element('rFonts', ascii='Times New Roman', hAnsi='Times New Roman', cs='Times New Roman'))
    rp.append(element('sz', val=size))
    if bold:
        rp.append(element('b'))
    t = E.SubElement(r, W + 't')
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = value
    return p


def fix_table(table):
    """Сетка и ширина ячеек согласованы, автоподбор по содержимому выключен."""
    grid = table.find(W + 'tblGrid')
    widths = [int(c.get(W + 'w')) for c in grid]
    pr = table.find(W + 'tblPr')
    if pr is None:
        pr = element('tblPr'); table.insert(0, pr)
    for tag in ('tblLayout', 'tblW'):
        for old in pr.findall(W + tag):
            pr.remove(old)
    pr.append(element('tblW', w=sum(widths), type='dxa'))
    pr.append(element('tblLayout', type='fixed'))
    rows = table.findall(W + 'tr')
    loop_index = next((i for i, row in enumerate(rows) if '{%tr for ' in text(row)), None)
    for index, row in enumerate(rows):
        rp = row.find(W + 'trPr')
        if rp is None:
            rp = element('trPr'); row.insert(0, rp)
        if rp.find(W + 'cantSplit') is None:
            rp.append(element('cantSplit'))
        if loop_index is not None and index < loop_index and rp.find(W + 'tblHeader') is None:
            rp.append(element('tblHeader'))
        pos = 0
        for cell in row.findall(W + 'tc'):
            cp = cell.find(W + 'tcPr')
            if cp is None:
                cp = element('tcPr'); cell.insert(0, cp)
            span = cp.find(W + 'gridSpan')
            count = int(span.get(W + 'val')) if span is not None else 1
            cw = cp.find(W + 'tcW')
            if cw is None:
                cw = element('tcW'); cp.insert(0, cw)
            cw.set(W + 'w', str(sum(widths[pos:pos + count])))
            cw.set(W + 'type', 'dxa')
            pos += count


def reflow(root, ranges):
    body = root.find(W + 'body')
    source = body.find(W + 'tbl')
    rows = source.findall(W + 'tr')
    starts = {a: b for a, b in ranges}
    index = body.index(source)
    output = []
    i = 0
    while i < len(rows):
        if i in starts:
            end = starts[i]
            table = deepcopy(source)
            for row in table.findall(W + 'tr'):
                table.remove(row)
            for row in rows[i:end + 1]:
                # Пустые строки печатной сетки Excel не являются строками
                # заголовка Word; вертикальные объединения продолжаются ниже.
                if not text(row).strip():
                    continue
                clone = deepcopy(row)
                # Excel rows had fixed print heights. Word rows grow with text.
                for height in clone.findall('w:trPr/w:trHeight', NS):
                    height.getparent().remove(height)
                table.append(clone)
            output.append(table)
            output.append(paragraph('', size=4))
            i = end + 1
            continue
        values = []
        for cell in rows[i].findall(W + 'tc'):
            merge = cell.find('w:tcPr/w:vMerge', NS)
            if merge is not None and merge.get(W + 'val') != 'restart':
                continue
            value = text(cell).strip()
            if value:
                values.append(value)
        value = ' '.join(values)
        if value:
            value = value.replace('(подпись)', '________________ (подпись)')
            align = 'right' if i < 2 else 'center' if i < 5 else 'left'
            output.append(paragraph(value, align=align, bold=2 <= i < 5))
        i += 1
    body.remove(source)
    for offset, node in enumerate(output):
        body.insert(index + offset, node)


def inline_dates(root):
    """День и год не должны зависеть от ширины узких ячеек исходного бланка."""
    for table in list(root.iter(W + 'tbl')):
        rows = table.findall(W + 'tr')
        value = text(table)
        if len(rows) != 1 or 'г.' not in value or '{%tr' in value:
            continue
        if len(re.findall(r'{{.*?}}', value)) < 3:
            continue
        values = [text(c).strip() for c in rows[0].findall(W + 'tc')]
        value = ' '.join(v for v in values if v)
        value = re.sub(r'"\s*({{.*?}})\s*"', r'«\1»', value)
        # В оригиналах «20» иногда выделено в отдельную ячейку перед годом.
        value = re.sub(r'\b20\s+({{.*?}})', r'20\1', value)
        parent = table.getparent()
        parent.replace(table, paragraph(value))






def main():
    if not ARCHIVE.exists():
        ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(ARCHIVE, 'w', ZIP_DEFLATED) as z:
            manifest = {}
            for path in sorted(FOLDER.glob('*.docx')):
                data = path.read_bytes()
                z.writestr(path.name, data)
                manifest[path.name] = hashlib.sha256(data).hexdigest()
            z.writestr('sha256.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    catalog = json.loads((ROOT / 'app/templates/catalog.json').read_text())
    with ZipFile(ARCHIVE) as originals:
        manifest = json.loads(originals.read('sha256.json'))
        for form in catalog:
            if not form['code'].startswith('СП_77_'):
                continue
            path = ROOT / form['template']
            fields = json.loads((ROOT / form['fields']).read_text())
            original = originals.read(path.name)
            if hashlib.sha256(original).hexdigest() != manifest[path.name]:
                raise ValueError('Нарушен хеш архивного шаблона: ' + path.name)
            with ZipFile(BytesIO(original)) as source:
                parts = [(info, source.read(info)) for info in source.infolist()]
            root = E.fromstring(dict((i.filename, data) for i, data in parts)['word/document.xml'])
            code = form['code'].removeprefix('СП_77_А_')
            if code in DATA:
                reflow(root, DATA[code])
            inline_dates(root)
            if code == '23':
                # Обязательный пустой абзац после таблицы подписей не должен
                # создавать отдельный чистый лист.
                body = root.find(W + 'body')
                last = body[-2]
                if last.tag == W + 'p' and not text(last).strip():
                    tail = paragraph('', size=2)
                    pr = tail.find(W + 'pPr')
                    spacing = pr.find(W + 'spacing')
                    spacing.set(W + 'after', '0')
                    spacing.set(W + 'line', '20')
                    spacing.set(W + 'lineRule', 'exact')
                    E.SubElement(pr, W + 'rPr').append(element('sz', val=2))
                    body.replace(last, tail)
            for table in root.iter(W + 'tbl'):
                fix_table(table)
            from prepare_object_templates import normalize_template
            from itd.template_objects import field_contract
            normalize_template(root, field_contract(form['code']))
            xml = E.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
            with ZipFile(path, 'w') as output:
                for info, data in parts:
                    output.writestr(info, xml if info.filename == 'word/document.xml' else data)


if __name__ == '__main__':
    main()
