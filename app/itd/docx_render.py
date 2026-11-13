"""Подстановка подготовленного контекста в DOCX.

Этот слой не читает БД самостоятельно: контекст должен собираться отдельным
слоем из актуальных данных и проверенных правил полей формы.
"""

import json
import os
import tempfile
import re
from pathlib import Path


def _date_centuries(document, code, context):
    """Убирает печатное «20» только перед подставляемым полным годом даты."""
    from .form_defaults import date_groups
    from .template_objects import field_contract
    from .fields import lookup
    from docx.oxml.ns import qn
    spec = field_contract(code)
    paths = {'document.date.year'}
    paths.update(spec[g['parts']['year']]['path'] for g in date_groups().get(code, [])
                 if g['parts']['year'] in spec)
    paths = {p for p in paths if re.fullmatch(r'\d{4}', str(lookup(p, context) or ''))}
    if not paths:
        return
    marker = r'{{\s*(?:' + '|'.join(re.escape(p) for p in paths) + r')\s*}}'
    texts = list(document._element.iter(qn('w:t')))
    for index, node in enumerate(texts):
        value = node.text or ''
        value = re.sub(r'20\s*(?=' + marker + ')', '', value)
        if re.search(r'20\s*$', value) and re.match(r'\s*' + marker, ''.join(t.text or '' for t in texts[index + 1:index + 8])):
            value = re.sub(r'20\s*$', '', value)
        node.text = value


def _draft_display(value):
    if isinstance(value, str):
        return value.replace("[УТОЧНИТЬ]", "—")
    if isinstance(value, list):
        return [_draft_display(item) for item in value]
    if isinstance(value, dict):
        return {key: _draft_display(item) for key, item in value.items()}
    return value


def render_docx(template: str | Path, context: dict, output: str | Path, *, draft=False, font=None) -> Path:
    from docxtpl import DocxTemplate
    from jinja2 import StrictUndefined
    from jinja2.sandbox import SandboxedEnvironment

    template = Path(template).resolve()
    output = Path(output).resolve()
    if template == output:
        raise ValueError("Результат не может перезаписать шаблон")
    if output.exists():
        raise FileExistsError(f"Результат уже существует: {output}")
    if not isinstance(context, dict):
        raise ValueError("Контекст должен быть JSON-объектом")
    # Допускается только JSON: не передаём шаблону объекты БД, функции или классы.
    context = json.loads(json.dumps(context, ensure_ascii=False, allow_nan=False))
    from .template_objects import render_context, display_object
    context = render_context(template.stem, context)
    if draft:
        context = _draft_display(context)
    class TemplateEnvironment(SandboxedEnvironment):
        def getattr(self, obj, attribute):
            # Свойство JSON-объекта имеет приоритет над методом dict (items и др.).
            if isinstance(obj, dict) and attribute in obj:
                return obj[attribute]
            return super().getattr(obj, attribute)

    environment = TemplateEnvironment(undefined=StrictUndefined, autoescape=True, finalize=display_object)
    environment.globals.clear()
    document = DocxTemplate(template)
    document.init_docx()
    _date_centuries(document.docx, template.stem, context)
    document.render(context, jinja_env=environment, autoescape=True)
    from .signature_layout import append_signatories
    append_signatories(document.docx, context.get('_additional_signatories', []))
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=".itd-", suffix=".docx", dir=output.parent)
    os.close(handle)
    temp_path = Path(temp_name)
    try:
        document.save(temp_path)
        if font is not None:
            # Включая стили, колонтитулы, текстовые блоки и кириллицу.
            from zipfile import ZipFile, ZIP_DEFLATED
            from lxml import etree
            from docx.oxml.ns import qn
            with ZipFile(temp_path) as archive:
                parts = [(info, archive.read(info)) for info in archive.infolist()]
            with ZipFile(temp_path, "w", compression=ZIP_DEFLATED) as archive:
                for info, content in parts:
                    if info.filename.startswith("word/") and info.filename.endswith(".xml"):
                        root = etree.fromstring(content)
                        for element in root.iter(qn("w:rFonts")):
                            for key in list(element.attrib):
                                if key.endswith("Theme"):
                                    del element.attrib[key]
                            for key in ("ascii", "hAnsi", "eastAsia", "cs"):
                                element.set(qn("w:" + key), font)
                        content = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
                    archive.writestr(info, content)
        # Публикуем готовый файл без перезаписи существующего результата,
        # включая случай появления файла после первоначальной проверки.
        os.link(temp_path, output)
    finally:
        temp_path.unlink(missing_ok=True)
    return output
