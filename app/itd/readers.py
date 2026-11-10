"""Извлечение текста и таблиц для последующего чтения моделью.

Не интерпретирует произвольный чертёж как готовую спецификацию.
"""

from pathlib import Path
import json

from .archive import digest


def page_selection(value, count):
    if value is None:
        return list(range(1, count+1))
    selected = set()
    try:
        for item in value.split(','):
            bounds = [int(n) for n in item.strip().split('-')]
            if len(bounds) not in (1,2) or bounds[0]<1 or bounds[-1]>count or bounds[0]>bounds[-1]:
                raise ValueError()
            selected.update(range(bounds[0],bounds[-1]+1))
    except (ValueError, AttributeError):
        raise ValueError('Страницы: например 1,3-7; номера должны быть в пределах PDF') from None
    return sorted(selected)


def read_document(path, *, scan_dir=None, pages=None, dpi=144, overview=False):
    path = Path(path).resolve(strict=True)
    result = {"source": str(path), "sha256": digest(path), "parts": []}
    suffix = path.suffix.lower()
    if suffix != '.pdf' and (pages is not None or scan_dir is not None or overview or dpi != 144):
        raise ValueError('Выбор страниц, обзор, DPI и рендер страниц доступны только для PDF')
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(path)
        if not isinstance(dpi,int) or isinstance(dpi,bool) or not 36 <= dpi <= 300:
            raise ValueError('DPI должен быть целым числом от 36 до 300')
        result['pdf_page_count'] = len(reader.pages)
        selected = page_selection(pages, len(reader.pages))
        for index in selected:
            page = reader.pages[index-1]
            text = page.extract_text() or ""
            item = {"page": index, "text": text[:500] if overview else text, "characters":len(text),
                    "rotation": page.rotation, "needs_visual_review": True, "text_layer_empty":not text.strip()}
            result["parts"].append(item)
        reader.close()
        # Текстовый слой может быть неполным даже на странице с текстом.
        # По запросу готовим изображения всех страниц, а не только пустых.
        if scan_dir is not None:
            try:
                import pymupdf
            except ImportError as error:
                raise ValueError("Для изображений PDF установите pymupdf из requirements.txt") from error
            output = Path(scan_dir)
            output.mkdir(parents=True, exist_ok=True)
            cache = output / (result['sha256'] + f'-{dpi}dpi.json')
            manifest = json.loads(cache.read_text()) if cache.exists() else {}
            with pymupdf.open(path) as document:
                for item in result['parts']:
                    index = item['page']
                    target = output / f"{result['sha256']}-{dpi}dpi-page-{index:04}.png"
                    if target.exists() and manifest.get(str(index)) != digest(target):
                        raise ValueError('Кеш изображения изменён или не зарегистрирован; выберите новый каталог рендера')
                    if not target.exists():
                        document[index-1].get_pixmap(dpi=dpi).save(target)
                    manifest[str(index)] = digest(target)
                    temp = cache.with_suffix('.tmp')
                    temp.write_text(json.dumps(manifest), encoding='utf-8')
                    temp.replace(cache)
                    item['image'] = str(target.resolve())
            result['render_dpi'] = dpi
        result['notes'] = 'page — страница PDF, sheet — обозначение листа, locator — строка/место. Текст не подтверждает полноту таблиц. pdf_page_count не является sheets_count.'
    elif suffix == ".docx":
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        document = Document(path)
        # Сохраняем порядок абзацев и таблиц, а не собираем все таблицы в конец.
        for index, element in enumerate(document.element.body, 1):
            if element.tag.endswith("}p"):
                result["parts"].append({"block": index, "text": Paragraph(element, document).text})
            elif element.tag.endswith("}tbl"):
                table = Table(element, document)
                result["parts"].append({"block": index, "rows": [[cell.text for cell in row.cells] for row in table.rows]})
        for index, section in enumerate(document.sections, 1):
            for kind in ("header", "footer", "first_page_header", "first_page_footer"):
                part = getattr(section, kind)
                if part.is_linked_to_previous:
                    continue
                result["parts"].append({"section": index, "kind": kind,
                                        "text": "\n".join(paragraph.text for paragraph in part.paragraphs),
                                        "tables": [[[cell.text for cell in row.cells] for row in table.rows] for table in part.tables]})
        result["notes"] = "Номера печатных страниц и содержимое графических штампов требуют визуальной сверки."
    elif suffix == ".xlsx":
        from openpyxl import load_workbook
        book = load_workbook(path, read_only=True, data_only=False)
        try:
            for sheet in book:
                for index, row in enumerate(sheet.iter_rows(), 1):
                    values = [cell.value.isoformat() if hasattr(cell.value, "isoformat") else cell.value for cell in row]
                    if any(value is not None for value in values):
                        result["parts"].append({"sheet": sheet.title, "row": index, "values": values})
        finally:
            book.close()
        result["notes"] = "Формулы сохранены как исходные выражения, их результат не вычислялся."
    else:
        raise ValueError("Поддерживаются PDF, DOCX и XLSX")
    return result
