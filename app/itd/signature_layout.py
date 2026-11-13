"""Дополнительные подписи наследуют сетку и оформление подписей бланка."""
from copy import deepcopy
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


def _text(element, value):
    texts = list(element.iter(qn('w:t')))
    if texts:
        texts[0].text = value.split('\n')[0]
        texts[0].set(qn('xml:space'), 'preserve')
        for node in texts[1:]:
            node.text = ''
        from docx.oxml import OxmlElement
        anchor = texts[0]
        for line in value.split('\n')[1:]:
            br = OxmlElement('w:br'); anchor.addnext(br)
            node = OxmlElement('w:t'); br.addnext(node); node.text = line
            node.set(qn('xml:space'), 'preserve'); anchor = node
    else:
        from docx.oxml import OxmlElement
        paragraph = next(element.iter(qn('w:p')), None)
        if paragraph is None:
            paragraph = OxmlElement('w:p'); element.append(paragraph)
        run = OxmlElement('w:r'); paragraph.append(run)
        node = OxmlElement('w:t'); run.append(node); node.text = value


def append_signatories(document, people):
    if not people:
        return
    body = document._element.body
    # Последний блок используется только при наличии признаков подписи.
    tables = [t for t in document.tables if any(
        word in ' '.join(c.text.lower() for r in t.rows for c in r.cells)
        for word in ('подпись', 'представитель'))]
    source = tables[-1] if tables else None
    for person in people:
        details = ', '.join(filter(None, [person.get(k) for k in
                                         ('position', 'organization', 'fio', 'authority')]))
        if source is None:
            paragraph = document.add_paragraph(person['role'] + ':')
            paragraph.paragraph_format.keep_with_next = True
            document.add_paragraph(details + '    ____________ (подпись)')
            continue
        clone = deepcopy(source._tbl)
        if len(source.rows) > 3:
            # Некоторые бланки целиком состоят из одной таблицы. Повторяем
            # только последние строки подписи, а не весь акт с измерениями.
            rows = list(clone.iterchildren(qn('w:tr')))
            signature = [i for i, row in enumerate(rows)
                         if 'подпись' in ''.join(row.itertext()).lower()]
            end = signature[-1] if signature else len(rows) - 1
            start = max(0, end - 1)
            for index, row in enumerate(rows):
                if not start <= index <= end:
                    clone.remove(row)
            for cell in clone.findall(qn('w:tr'))[0].findall(qn('w:tc')):
                _text(cell, '')
        body.insert(len(body) - 1, clone)
        table = Table(clone, document)
        # Две колонки: название роли слева, реквизиты и подпись справа (СП 77 А.3).
        if len(table.rows) == 1 and len(table.rows[0].cells) == 2:
            _text(table.cell(0, 0)._tc, person['role'] + ':')
            _text(table.cell(0, 1)._tc, details + '\n____________ (подпись)')
        elif len(table.rows) == 3 and len(table.rows[0].cells) == 3:
            # СП 77 А.5: две колонки подписантов, между ними промежуток.
            # Последовательные пары оформляются ниже отдельным общим блоком.
            body.remove(clone)
            break
        else:
            # Формы Минстроя: отдельный заголовок, ФИО слева, подпись справа.
            heading = source._tbl.getprevious()
            if len(source.rows) <= 3 and heading is not None and heading.tag == qn('w:p'):
                title = deepcopy(heading)
                _text(title, person['role'] + ':')
                clone.addprevious(title)
                Paragraph(title, document).paragraph_format.keep_with_next = True
            else:
                title = document.add_paragraph(person['role'] + ':')
                clone.addprevious(title._p)
            _text(table.cell(0, 0)._tc, details)
            # Остальные строки подписи и подписи-подсказки остаются как в бланке.
    else:
        return
    # СП 77 А.5 — две подписи в строке и третья на следующей строке.
    for offset in range(0, len(people), 2):
        clone = deepcopy(source._tbl)
        body.insert(len(body) - 1, clone)
        table = Table(clone, document)
        for index, column in enumerate((0, 2)):
            person = people[offset + index] if offset + index < len(people) else None
            details = ', '.join(filter(None, [person.get(k) for k in
                                ('position', 'organization', 'fio', 'authority')])) if person else ''
            _text(table.cell(0, column)._tc, person['role'] + ':\n' + details if person else '')
            _text(table.cell(1, column)._tc, '')
            _text(table.cell(2, column)._tc, '(подпись)' if person else '')
