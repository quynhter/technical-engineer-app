"""Однократная адаптация исходного TitleGenerator, без изменения оригинала.

Запуск: python app/scripts/prepare_title_template.py --source template.docx
Фиксированные фигуры заменены растущими таблицами наклеек.
"""
import argparse
from pathlib import Path


def prepare(source, output):
    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt, RGBColor
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

    document = Document(source)
    body = document._element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)
    section = document.sections[0]
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(22)
    section.left_margin = Mm(25)
    section.right_margin = Mm(20)
    # Оригинал содержит город и год в колонтитулах. Повторяем на всех листах.
    for kind in ("header", "first_page_header", "even_page_header",
                 "footer", "first_page_footer", "even_page_footer"):
        part = getattr(section, kind)
        if "footer" in kind:
            for child in list(part._element):
                part._element.remove(child)
            p = part.add_paragraph()
            p.alignment = 1
            p.add_run("{{ city }}, {{ year }} г.").font.size = Pt(12)
            continue
        for p in part.paragraphs:
            for r in p.runs:
                r.text = r.text.replace("{city}", "{{ city }}").replace("{year}", "{{ year }}")
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(13)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.05

    def paragraph(text, *, size=14, before=0, after=6, align=1, bold=False, style=None):
        p = document.add_paragraph(style=style)
        p.alignment = align
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        r = p.add_run(text)
        r.font.size = Pt(size)
        r.font.color.rgb = RGBColor(0, 0, 0)
        r.bold = bold
        return p

    paragraph("{%p for page in pages %}")
    paragraph("{{ page.duplicates }}", size=12, align=2, after=18)
    paragraph("Исполнительно-техническая документация", size=19, bold=True,
              after=30, style="Title")
    table = document.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Mm(65)
    table.columns[1].width = Mm(100)
    for label, key in (("Заказчик", "client"), ("Технический заказчик", "tech_client"),
                       ("Генподрядная организация", "gen_contractor"),
                       ("Подрядная организация", "sub_contractor")):
        cells = table.add_row().cells
        for cell, text in zip(cells, (label, "{{ " + key + " }}")):
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(8)
            p.add_run(text).font.size = Pt(12)
    for label, key in (("Объект", "object"), ("Раздел", "project"), ("Шифр", "cifr")):
        paragraph(label, size=15, before=22, after=8, bold=True)
        paragraph("{{ " + key + " }}", size=14)
    paragraph("{{ page.volumes_info }}", size=14, before=22)
    paragraph("{%p if labels %}")
    document.add_page_break()
    for index, width in enumerate((110, 110, 155)):
        table = document.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        table.columns[0].width = Mm(width)
        cell = table.cell(0, 0)
        cell.width = Mm(width)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        borders = OxmlElement("w:tcBorders")
        for side in ("top", "left", "bottom", "right"):
            e = OxmlElement("w:" + side)
            for k, v in (("val", "single"), ("sz", "8"), ("color", "000000")):
                e.set(qn("w:" + k), v)
            borders.append(e)
        cell._tc.get_or_add_tcPr().append(borders)
        margins = OxmlElement("w:tcMar")
        for side in ("top", "left", "bottom", "right"):
            margin = OxmlElement("w:" + side)
            margin.set(qn("w:w"), "100")
            margin.set(qn("w:type"), "dxa")
            margins.append(margin)
        cell._tc.get_or_add_tcPr().append(margins)
        table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        texts = ["Исполнительная документация ({{ page.duplicates }})",
                 "{{ contractors_info }}", "{{ object }}"]
        if index == 1:
            texts.append("{{ project }}")
        texts += ["{{ cifr }}", "{{ page.volumes_info }}"]
        for i, text in enumerate(texts):
            p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
            p.alignment = 1
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            p.add_run(text).font.size = Pt(10 if index == 0 else 11)
        paragraph("", size=8, after=14)
    paragraph("{%p endif %}")
    paragraph("{%p if not loop.last %}")
    document.add_page_break()
    paragraph("{%p endif %}")
    paragraph("{%p endfor %}")
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("app/templates/Титульники/ТИТУЛЬНЫЙ_ЛИСТ.docx"))
    args = parser.parse_args()
    prepare(args.source, args.output)
