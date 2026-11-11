"""Подписи и контролы веб-формы; исходные настройки документов не меняются."""
import re

ROLE_LABELS = {
    'customer': 'Заказчик', 'builder_org': 'Лицо, осуществляющее строительство',
    'designer_org': 'Проектная организация', 'control_org': 'Организация строительного контроля заказчика',
    'designer_employer': 'Организация представителя проектировщика',
    'work_performer_employer': 'Организация исполнителя работ',
    'network_operator_employer': 'Эксплуатирующая организация',
}


def human_label(field, index=0):
    label = re.sub(r'{{.*?}}', ' ', field.get('label') or '')
    label = re.sub(r'\s+', ' ', label.replace('(', '').replace(')', '')).strip(' /:')
    prefix, sep, rest = label.partition(':')
    if sep and prefix in ROLE_LABELS:
        label = ROLE_LABELS[prefix] + ': ' + rest.strip()
    if not label or label == field.get('key'):
        return f'Дополнительное поле {index + 1}'
    return re.sub(r'[^\W\d_]', lambda match: match[0].upper(), label, count=1)


def input_type(field):
    if field.get('value_type') == 'date' or field.get('format'):
        return 'date'
    if field.get('value_type') == 'number':
        return 'number'
    if field.get('value_type') == 'text':
        return 'text'
    # Узкие признаки однотипных старых полей. Составные реквизиты остаются текстом.
    label = human_label(field).lower()
    if label == 'дата' or label.startswith('дата ') or (field.get('label') or '').lower().strip().endswith('(дата)'):
        return 'date'
    if (re.match(r'^(количество|кол-во|число|недостающее количество)\b', label)
            and not re.search(r'наименован|характерист|номер|№|\bтип\b|\bду\b|сечени|перечень', label)):
        return 'number'
    return 'text'


def describe_fields(fields):
    return [{**f, 'label': human_label(f, i), 'input_type': input_type(f),
             **({'fields': describe_fields(f['fields'])} if 'fields' in f else {})}
            for i, f in enumerate(fields)]


def table_headers(template):
    """Read header rows above each DOCX template loop, preserving merged cells."""
    from docx import Document
    from docx.table import _Cell

    headers = {}
    document = Document(template)
    from .template_objects import legacy_paths
    bindings = legacy_paths(__import__('pathlib').Path(template).stem)
    aliases = {}
    for paragraph in document.paragraphs:
        assignment = re.fullmatch(r'\s*{%p\s+set\s+(\w+)\s*=\s*(\w+)\s*%}\s*', paragraph.text)
        if assignment:
            aliases[assignment[1]] = aliases.get(assignment[2], assignment[2])
    for table in document.tables:
        rows = []
        vertical = {}
        docx_rows = list(table.rows)
        for index, row in enumerate(docx_rows):
            text = row.cells[0].text if row.cells else ''
            loop = re.fullmatch(r'\s*{%tr\s+for\s+\w+\s+in\s+([\w.]+)\s*%}\s*', text)
            if loop and index + 1 < len(docx_rows):
                # The editor has one column per data cell. A DOCX cell may
                # occupy several grid columns even when it holds a single field.
                boundaries = {0: 0}
                end = 0
                for number, cell in enumerate(docx_rows[index + 1]._tr.tc_lst, 1):
                    end += cell.grid_span
                    boundaries[end] = number
                while len(rows) > 1 and len(rows[0]) == 1 and rows[0][0]['span'] == end and rows[0][0]['rowspan'] == 1:
                    rows.pop(0)
                if all(cell['column'] in boundaries and cell['column'] + cell['span'] in boundaries
                       for header in rows for cell in header):
                    key = aliases.get(loop[1], loop[1])
                    headers[bindings.get(key, key)] = [
                        [{'label': cell['label'], 'rowspan': cell['rowspan'],
                          'span': boundaries[cell['column'] + cell['span']] - boundaries[cell['column']]}
                         for cell in header] for header in rows
                    ]
            cells = [(' '.join(_Cell(cell, table).text.split()), cell.grid_span, cell.vMerge)
                     for cell in row._tr.tc_lst]
            if any('{%' in label or '{{' in label for label, _, _ in cells):
                rows, vertical = [], {}
                continue
            if not any(label for label, _, _ in cells) or all(label.isdecimal() for label, _, _ in cells):
                continue
            column = 0
            header = []
            next_vertical = {}
            for label, span, merge in cells:
                if merge == 'continue' and column in vertical:
                    cell = vertical[column]
                    cell['rowspan'] += 1
                    next_vertical[column] = cell
                else:
                    cell = {'label': label, 'column': column, 'span': span, 'rowspan': 1}
                    header.append(cell)
                    if merge == 'restart':
                        next_vertical[column] = cell
                column += span
            rows.append(header)
            vertical = next_vertical
    return headers
