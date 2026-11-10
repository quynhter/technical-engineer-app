"""Воспроизводимая карта схемы и контрактов форм; рабочие БД не открываются.

Запуск из корня: PYTHONPATH=app .venv/bin/python app/scripts/audit_relationships.py
Для обновления карты добавьте --write-map. Код выхода 1 означает ошибки контракта.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from string import Formatter
import tempfile
from zipfile import ZipFile

from docxtpl import DocxTemplate
from jinja2 import Environment, nodes
from lxml import etree

from itd.acts import add_act, build_context, find_template, register_form
from itd.db import add_object, add_project, connect, initialize
from itd.docx_render import render_docx
from itd.fields import PRESENTATIONS, SEMANTIC_SOURCES, validate_fields
from itd.form_catalog import catalog, catalog_fields
from itd.form_defaults import FIELD_CONTINUATIONS, apply_form_defaults, field_bindings
from itd.titles import CODE as TITLE_CODE, ROLES as TITLE_ROLES, prepare_context
from itd.workspace import DOC_ROLES, ROLES

ROOT = Path(__file__).resolve().parents[2]
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
TABLE_LABELS = {
    'objects': 'Объекты', 'projects': 'Разделы РД', 'resources': 'Ресурсы',
    'schemes': 'Схемы', 'organizations': 'Участники: организации',
    'signatories': 'Участники: представители', 'object_participants': 'Роли участников объекта',
    'organization_assignments': 'Назначения организаций для документов',
    'signatory_assignments': 'Назначения представителей для документов',
    'workspace_entries': 'Записи ОЖР / ЖВК / работ', 'work_facts': 'Факт монтажа',
    'work_materials': 'Ресурсы записи работ', 'work_material_allocations': 'Списание поставок',
    'supplies': 'Поставки', 'quality_reviews': 'Проверки документов качества',
    'special_journals': 'Специальные журналы', 'acts': 'Основные документы',
    'document_versions': 'Карточки версий документов', 'document_types': 'Зарегистрированные формы',
    'releases': 'Выпуски файлов', 'generated_documents': 'История генерации DOCX',
    'attachments': 'Архив исходных файлов', 'project_files': 'Файлы раздела',
    'package_requirements': 'Состав комплекта', 'deliveries': 'Сдача',
    'users': 'Пользователи', 'settings': 'Выбранная БД и рабочая папка',
    'document_roots': 'Разрешённые рабочие папки', 'knowledge_entries': 'Фрагменты нормативов',
    'knowledge_meta': 'Манифест индекса', 'knowledge_fts': 'Полнотекстовый поиск',
}
DIRECT_ROOTS = {'object': 'objects', 'project': 'projects', 'act': 'acts',
                'unit': 'object_units', 'section_designer': 'organizations'}
LIST_ROOTS = {'resources': 'resources', 'schemes': 'schemes', 'facts': 'work_facts',
              'entries': 'workspace_entries', 'materials': 'supplies',
              'companies': 'organizations', 'participation_periods': 'participant_periods'}
REGISTRY_FIELDS = {'no', 'entity', 'id', 'name', 'number', 'date', 'sheets_count',
                   'note', 'group', 'pages', 'number_date', 'organization'}
DOC_FIELDS = {'code': ['projects.code'], 'designer_name': ['projects.designer_org_id', 'organizations.full_name'],
              'description': ['projects.code', 'projects.designer_org_id', 'organizations.full_name'],
              'section_description': ['projects.name', 'projects.code'],
              'object_and_project': ['objects.name', 'projects.code'],
              'object_description': ['objects.name', 'objects.address']}
TITLE_DERIVED = {'contractors_info', 'pages', 'pages.duplicates', 'pages.volumes_info'}
TITLE_CONTROLS = {'copies', 'volumes', 'font'}
REGISTRY_CONTEXT_ONLY = {'registry.number', 'registry.date', 'registry.note'}


def unprinted_reason(code, path, field):
    if code == TITLE_CODE and path in TITLE_CONTROLS:
        return 'Управляет prepare_context / оформлением DOCX'
    if code == 'РЕЕСТР_ИТД' and path in REGISTRY_CONTEXT_ONLY:
        return 'В контексте реестра, отдельно не печатается'
    label = field.get('label', '').lower()
    if '.' in path and 'подпис' in label and not re.search(r'дата\s+подписания', label):
        return 'Рукописная подпись: ячейка DOCX оставлена пустой'
    raise ValueError(f'{path}: определение поля не используется в DOCX')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def md(value):
    return str(value if value is not None else '—').replace('|', '&#124;').replace('\n', '<br>')


def link(path):
    return f'[{path}]({str(path).replace(" ", "%20")})'


def schema(c):
    result = {}
    for row in c.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        name = row[0]
        if name.startswith('knowledge_fts_'):
            continue
        result[name] = {'sql': row[1], 'columns': [dict(r) for r in c.execute(f'PRAGMA table_info("{name}")')],
                        'fks': [dict(r) for r in c.execute(f'PRAGMA foreign_key_list("{name}")')],
                        'indexes': [dict(r) for r in c.execute(f'PRAGMA index_list("{name}")')],
                        'extras': [dict(r) for r in c.execute("SELECT type,name,sql FROM sqlite_master WHERE tbl_name=? AND type IN ('trigger','index') AND sql IS NOT NULL ORDER BY type,name", (name,))]}
    return result


def auxiliary_schema():
    """Извлекаем именно DDL из кода; ни аккаунты, ни индекс пользователя не открываем."""
    result = {}
    for module in ('accounts', 'knowledge'):
        tree = ast.parse((ROOT / f'app/itd/{module}.py').read_text())
        statements = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args:
                arg = node.args[0]
                if node.func.attr in ('execute', 'executescript') and isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.lstrip().startswith(('CREATE TABLE', 'CREATE VIRTUAL TABLE')):
                        statements.append(arg.value)
        with sqlite3.connect(':memory:') as c:
            c.row_factory = sqlite3.Row
            for sql in statements:
                c.executescript(sql)
            result[module] = schema(c)
    return result


def template_contract(path):
    """Разбираем Jinja AST после той же нормализации docxtpl, что при выпуске.

    Имена циклов приводятся к ключу таблицы: item.c1 → rows_x.c1.
    Проверяются все XML-части Word, включая колонтитулы и текстовые блоки.
    """
    refs = defaultdict(set)
    locations = defaultdict(set)
    document = DocxTemplate(path)

    def expression(node):
        if isinstance(node, nodes.Name):
            return node.name
        if isinstance(node, nodes.Getattr):
            base = expression(node.node)
            return base + '.' + node.attr if base else None
        if isinstance(node, nodes.Getitem) and isinstance(node.arg, nodes.Const):
            base = expression(node.node)
            return base + '.' + str(node.arg.value) if base else None
        return None

    def visit(node, aliases, part):
        if isinstance(node, nodes.For):
            visit(node.iter, aliases, part)
            scope = dict(aliases)
            base = expression(node.iter)
            if base:
                first, _, tail = base.partition('.')
                base = aliases.get(first, first) + ('.' + tail if tail else '')
            if isinstance(node.target, nodes.Name) and base:
                scope[node.target.name] = base
            for child in node.body:
                visit(child, scope, part)
            for child in node.else_:
                visit(child, aliases, part)
            return
        path = expression(node)
        if path and getattr(node, 'ctx', 'load') == 'load':
            first, _, tail = path.partition('.')
            if first != 'loop':
                refs[aliases.get(first, first) + ('.' + tail if tail else '')].add(part)
            return
        for child in node.iter_child_nodes():
            visit(child, aliases, part)

    with ZipFile(path) as z:
        for part in sorted(z.namelist()):
            if not part.startswith('word/') or not part.endswith('.xml'):
                continue
            xml = z.read(part).decode('utf-8')
            if '{{' not in xml and '{%' not in xml:
                continue
            visit(Environment().parse(document.patch_xml(xml)), {}, part)
            root = etree.fromstring(xml.encode())
            scopes = [{}]
            for paragraph in root.findall('.//w:p', NS):
                text = ''.join(paragraph.itertext())
                for marker in re.findall(r'{{.*?}}|{%.*?%}', text, re.S):
                    end = re.match(r'{%\s*(?:tr\s+|p\s+)?endfor\b', marker)
                    if end:
                        if len(scopes) > 1:
                            scopes.pop()
                        continue
                    loop = re.match(r'{%\s*(?:tr\s+|p\s+)?for\s+(\w+)\s+in\s+([\w.]+)', marker)
                    aliases = scopes[-1]
                    expression_text = loop[2] if loop else marker
                    for key in re.findall(r'\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', expression_text):
                        first, _, tail = key.partition('.')
                        key = aliases.get(first, first) + ('.' + tail if tail else '')
                        if key in refs:
                            locations[key].add(part + ':' + root.getroottree().getpath(paragraph))
                    if loop:
                        first, _, tail = loop[2].partition('.')
                        target = aliases.get(first, first) + ('.' + tail if tail else '')
                        scopes.append({**aliases, loop[1]: target})
    return dict(refs), dict(locations)


def flatten(fields, prefix=''):
    for field in fields:
        path = prefix + field['key']
        yield path, field
        if field['kind'] == 'table':
            yield from flatten(field['fields'], path + '.')


def source_columns(source, schemas, item_source=None):
    """Возвращает физические колонки и описание для фактического источника."""
    source = SEMANTIC_SOURCES.get(source, source)
    bits = source.split('.')
    root = bits[0]
    table = None
    column = None
    description = source
    if root in DIRECT_ROOTS and len(bits) == 2:
        table, column = DIRECT_ROOTS[root], bits[1]
    elif root == 'organizations' and len(bits) == 3:
        table, column = 'organizations', bits[2]
        description += f' (роль {bits[1]}; назначение объекта → раздела → документа)'
    elif root == 'signatories' and len(bits) >= 3:
        table, column = ('organizations', bits[3]) if len(bits) == 4 and bits[2] == 'organization' else ('signatories', bits[2])
        if column == 'fio_short':
            return ['signatories.last_name', 'signatories.first_name', 'signatories.middle_name', 'signatories.fio'], description + ' (сокращение ФИО)'
    elif root == 'project_documentation' and len(bits) == 2 and bits[1] in DOC_FIELDS:
        return DOC_FIELDS[bits[1]], description + ' (вычисляется form_defaults.documentation_context)'
    elif root == 'item' and item_source in LIST_ROOTS and len(bits) == 2:
        table, column = LIST_ROOTS[item_source], bits[1]
        if item_source == 'companies' and column in ('role', 'name'):
            return (['organization_assignments.role_key'] if column == 'role' else ['organizations.short_name', 'organizations.full_name']), description
        if item_source == 'materials' and column == 'act_quantity':
            return ['act_materials.quantity'], description
    elif root in LIST_ROOTS and len(bits) == 1:
        return [], source + f' (строки {LIST_ROOTS[root]}; состав и отбор описаны выше)'
    elif root == 'registry' and len(bits) == 1:
        return [], 'registry_rows: акты, схемы, вложения и автоматические журналы раздела'
    elif root == 'item' and item_source == 'registry' and len(bits) == 2 and bits[1] in REGISTRY_FIELDS:
        return [], source + ' (вычисляемая колонка registry_rows; см. контракт реестра)'
    elif root == 'item' and item_source == '<manual>' and len(bits) == 2:
        return [], source + ' (ячейка строки, введённой в acts.fields[].value)'
    elif source == 'row.number':
        return [], 'Порядковый номер строки, начиная с 1; не ID БД'
    elif root == 'field_values' and len(bits) == 2:
        return [], 'Уже разрешённое поле ' + bits[1] + ' этой же формы'
    else:
        raise ValueError('Неописанный источник: ' + source)
    if table not in schemas or column not in {c['name'] for c in schemas[table]['columns']}:
        raise ValueError(f'Несуществующая колонка: {table}.{column} ({source})')
    columns = [f'{table}.{column}']
    if source == 'project.city':
        columns.append('objects.city')
        description += ' (город раздела, иначе город объекта)'
    return columns, description


def audit_form(item, schemas, c, project_id, tmp):
    raw = catalog_fields(item)
    validate_fields(raw)
    fields = apply_form_defaults(item['code'], raw)
    validate_fields(fields)
    template = find_template(ROOT / 'app/templates', item['code'])
    if item.get('template') and template.resolve() != (ROOT / item['template']).resolve():
        raise ValueError('Каталог указывает другой шаблон')
    refs, locations = template_contract(template)
    definitions = dict(flatten(fields))
    allowed = set(definitions)
    if item['code'] == TITLE_CODE:
        allowed |= TITLE_DERIVED
    unknown = set(refs) - allowed
    if unknown:
        raise ValueError('Маркеры DOCX без определения: ' + ', '.join(sorted(unknown)))
    bindings = field_bindings().get(item['code'], {})
    if set(bindings) - {f['key'] for f in raw}:
        raise ValueError('Карта bindings ссылается на отсутствующее поле')
    rows = []

    def inspect(fs, prefix='', item_source=None):
        seen = set()
        for field in fs:
            path = prefix + field['key']
            columns, desc = [], ''
            source = field.get('source')
            if source:
                columns, desc = source_columns(source, schemas, item_source)
                if source.startswith('field_values.') and source.split('.')[1] not in seen:
                    raise ValueError(f'{path}: ссылка field_values не на предыдущее поле')
            elif field['kind'] == 'signatory':
                pattern = field.get('template', PRESENTATIONS[field.get('presentation', 'fio')])
                attrs = [name for _, name, _, _ in Formatter().parse(pattern) if name]
                for attr in attrs:
                    normalized = 'signatories.' + field['role'] + '.' + attr.removeprefix('signatory.') if attr.startswith('signatory.') else 'organizations.' + field['role'] + '.' + attr.removeprefix('organization.')
                    cols, _ = source_columns(normalized, schemas)
                    columns.extend(cols)
                desc = 'Роль ' + field['role'] + '; представление ' + pattern
            elif field['kind'] == 'table':
                desc = 'Ручные строки: acts.fields[].value; измерения/результаты не берутся из спецификации'
            else:
                desc = ('Ручное значение: acts.fields[].value' if field.get('value') in (None, '') else 'Значение по умолчанию: ' + json.dumps(field.get('value'), ensure_ascii=False))
            used = path in refs
            status = 'DOCX' if used else unprinted_reason(item['code'], path, field)
            if field.get('role_slot'):
                desc += '; требуется выбор ' + field['role_slot'] + ': ' + ', '.join(field.get('role_options', []))
            rows.append({'path': path, 'field': field, 'columns': sorted(set(columns)), 'description': desc,
                         'used': used, 'status': status})
            if field['kind'] == 'table':
                inspect(field['fields'], path + '.', field.get('source', '<manual>'))
            seen.add(field['key'])
    inspect(fields)
    register_form(c, code=item['code'], name=item['name'], fields=raw, form_group=item['group'])
    aid = add_act(c, project_id=project_id, act_type=item['code'])
    prepared = build_context(c, aid)
    render_docx(template, prepared['context'], tmp / (item['code'] + '-draft.docx'), draft=True)
    # Непустые строки принудительно исполняют тела всех циклов под StrictUndefined.
    def filled(fs):
        context = {}
        for f in fs:
            if f['kind'] == 'table':
                context[f['key']] = [filled(f['fields'])]
            elif f.get('format') or f.get('value_type') == 'date':
                context[f['key']] = '2026-11-10'
            elif f['kind'] == 'literal' and f.get('value') is not None:
                context[f['key']] = f['value']
            else:
                context[f['key']] = 'Тест ' + f['key']
        return context
    context = filled(fields)
    if item['code'] == TITLE_CODE:
        context['year'] = 2026
        prepare_context(context)
    output = tmp / (item['code'] + '-filled.docx')
    render_docx(template, context, output)
    with ZipFile(output) as z:
        for name in z.namelist():
            if name.startswith('word/') and name.endswith('.xml'):
                xml = z.read(name)
                etree.fromstring(xml)
                if b'{{' in xml or b'{%' in xml:
                    raise ValueError('Необработанный тег в ' + name)
    source = ROOT / item['source'] if item.get('source') else None
    provenance = 'Не указан в каталоге (общая форма)'
    if source:
        provenance = 'Исходник отсутствует в этой копии проекта; хеш не перепроверен'
        if source.is_file():
            if digest(source) != item['source_sha256']:
                raise ValueError('Хеш исходника отличается от catalog.json')
            provenance = 'SHA-256 исходника совпадает'
    return {'item': item, 'raw': raw, 'fields': fields, 'rows': rows, 'refs': refs, 'locations': locations,
            'template': template.relative_to(ROOT).as_posix(), 'template_sha': digest(template),
            'provenance': provenance, 'missing': prepared['missing']}


def run_audit():
    errors, forms = [], []
    items = catalog()
    if len(items) != len({item['code'] for item in items}):
        errors.append('Дубли кодов в объединённом каталоге')
    extras = auxiliary_schema()
    with tempfile.TemporaryDirectory(prefix='itd-map-') as directory:
        tmp = Path(directory)
        db = tmp / 'audit.sqlite'
        initialize(db)
        with connect(db) as c:
            tables = schema(c)
            oid = add_object(c, 'Проверочный объект карты')
            pid = add_project(c, object_id=oid, section_code='ТЕСТ', code='ТЕСТ-РД', name='Тестовый раздел')
            for item in items:
                try:
                    forms.append(audit_form(item, tables, c, pid, tmp))
                except Exception as error:
                    errors.append(item['code'] + ': ' + str(error))
            fk_errors = list(c.execute('PRAGMA foreign_key_check'))
            if fk_errors:
                errors.append('foreign_key_check: ' + repr([tuple(r) for r in fk_errors]))
            integrity = c.execute('PRAGMA integrity_check').fetchone()[0]
            if integrity != 'ok':
                errors.append('integrity_check: ' + integrity)
    expected_docx = {item['code'] + '.docx' for item in items}
    actual_docx = list((ROOT / 'app/templates').rglob('*.docx'))
    if len({p.name for p in actual_docx}) != len(actual_docx):
        errors.append('Повторяющиеся имена DOCX')
    for path in actual_docx:
        if path.name not in expected_docx:
            errors.append('DOCX вне каталога: ' + str(path.relative_to(ROOT)))
    expected_fields = {item['fields'] for item in items}
    for path in (ROOT / 'app/forms').rglob('*.fields.json'):
        if path.relative_to(ROOT).as_posix() not in expected_fields:
            errors.append('Определение полей вне каталога: ' + str(path.relative_to(ROOT)))
    for code in set(field_bindings()) - {i['code'] for i in items}:
        errors.append('bindings для неизвестной формы: ' + code)
    warnings = []
    absent = sum(f['provenance'].startswith('Исходник отсутствует') for f in forms)
    if absent:
        warnings.append(f'Исходников нет по путям каталога: {absent}; их хеши и соответствие бланкам не подтверждены')
    legacy = sorted(set(TITLE_ROLES.values()) - set(DOC_ROLES))
    if legacy:
        warnings.append('Прежние роли титульника требуют сопоставления с ролями веб-карточки: ' + ', '.join(legacy))
    handwritten = sum(row['status'].startswith('Рукописная') for form in forms for row in form['rows'])
    if handwritten:
        warnings.append(f'Непечатаемых колонок блоков подписей: {handwritten}; введённый в них текст не выводится')
    return {'tables': tables, 'auxiliary': extras, 'forms': forms, 'errors': errors, 'warnings': warnings}


def render_map(result):
    tables, forms = result['tables'], result['forms']
    rows = [row for form in forms for row in form['rows']]
    counts = Counter(row['field']['kind'] for row in rows)
    reverse = defaultdict(list)
    for form in forms:
        for row in form['rows']:
            for col in row['columns']:
                reverse[col].append(form['item']['code'] + '.' + row['path'])
    lines = ['# Карта данных, полей и шаблонов ИТД', '',
             'Снимок структуры на 10.11.2026. Карта построена по миграциям и исполняемым контрактам этой копии проекта. '
             'Рабочие БД и документы пользователя не открывались и не изменялись.', '',
             '## Навигация', '',
             '- [Итоги и границы проверки](#audit)', '- [Экран → сущности → документы](#screens)',
             '- [Порядок разрешения полей](#resolution)', '- [Все таблицы и колонки](#schema)',
             '- [Источники и обратные связи](#sources)', '- [Все шаблоны и каждое поле](#forms)',
             '- [Общая ведомость XLSX](#xlsx)', '- [Как обновить карту](#update)', '',
             '<a id="audit"></a>', '## Итоги проверки', '',
             f'- Основная БД: таблиц — **{len(tables)}**, колонок — **{sum(len(t["columns"]) for t in tables.values())}**, '
             f'компонентов внешних ключей — **{sum(len(t["fks"]) for t in tables.values())}**; миграции 001–021.',
             f'- Форм / DOCX / JSON-определений — **{len(forms)}**, включая титульник и две общие формы из `form_catalog.catalog()`.',
             f'- **{len(rows)} эффективных определений**, включая каждую колонку вложенных таблиц: ' + ', '.join(f'{k}: {v}' for k, v in sorted(counts.items())) + '.',
             f'- Ошибок проверенных контрактов: **{len(result["errors"])}**. '
             'Проверены уникальность кодов и файлов, ключи bindings, существование колонок источников, порядок field_values, '
             'Jinja AST всех XML-частей DOCX, поля циклов, два рендера каждой формы (контекст пустого тестового объекта и непустые синтетические строки), '
             'целостность XML результата, SQLite integrity_check и foreign_key_check на тестовой БД.',
             '- Результаты штатных тестов и ограничения их запуска фиксируются в CHANGELOG.md; аудит запускается отдельно.', '',
             '### Что не означает «всё автоматически связано»', '',
             f'- **{sum(r["field"]["kind"] == "literal" and r["field"].get("value") in (None, "") for r in rows)} пустых literal-полей** '
             'ожидают индивидуальные сведения. Это явный ручной ввод в `acts.fields`, а не потерянная связь. '
             'Нельзя достоверно вывести результаты измерений, заключения, даты испытаний и объёмы из спецификации.',
             f'- **{sum(r["field"]["kind"] == "table" and "value" in r["field"] for r in rows)} ручных таблиц** '
             'хранят строки в `acts.fields[].value`. Каждая их ячейка перечислена ниже. Пустое обязательное значение блокирует финал.',
             '- `role_slot` — намеренно незавершённый выбор роли по варианту бланка; варианты указаны у соответствующих полей. '
             'Несколько представителей одной роли требуют выбора в документе.',
             '- Не каждое поле БД печатается в документе: ключи, ревизии, хеши, пути и служебные состояния поддерживают учёт. '
             'У каждой колонки ниже показаны прямые потребители форм; «нет прямой привязки» не означает ошибку.',
             '- Карта относится к поставляемым определениям. В рабочей БД `document_types.fields`, `acts.fields`, назначения и карточки версий '
             'могут отличаться; без выбора рабочей БД и объекта их содержание не проверялось.',
             '- Семантическое соответствие каждого пустого места оригиналу и применимость нормативов не доказываются рендером. '
             'Наличие исходников и проверка их SHA-256 указаны отдельно для каждой формы. Постраничная визуальная сверка всех исходников в этот аудит не входит.', '',
             '- Все 89 исходников из catalog.json отсутствуют по указанным путям в этой копии проекта. '
             'Их хеши сохранены как происхождение, но повторно не подтверждены. '
             'Визуальный рендер исправленной формы СП_70_А также не выполнен: встроенный LibreOffice '
             'не запускается из-за отсутствия версии CURL_OPENSSL_4 у системной libcurl.so.4. '
             'Два рендера в итогах означают подстановку Jinja в DOCX, а не визуализацию страниц.', '',
             '### Выявленные особенности', '',
             '- Исправлен разрыв `СП_70_А.rows_9_2.c3`: «Дата подписания акта» была определена в JSON, '
             'но отсутствовала в строке DOCX. Теперь маркер печатается и поле обязательно; '
             'генератор исходных форм отличает дату подписания от места для подписи. '
             'В ZIP шаблона изменён только word/document.xml, остальные части сохранены побайтно. '
             'Исходный бланк и зарегистрированные настройки рабочих БД не изменялись.',
             '- 16 дочерних колонок блоков подписей намеренно остаются пустыми в DOCX. '
             'Их JSON-определения существуют, но введённый в них текст не печатается. '
             'Точные ключи и подписи перечислены ниже со статусом «Рукописная подпись». '
             'Некоторые подписи совмещены с ФИО/должностью в заголовке; автоматическое заполнение '
             'этих частей требует отдельной сверки бланка с оригиналом.',
             '- В README шаблонов была ссылка на отсутствующий `audit_form_bindings.py` и несуществующий `app/.venv`. '
             'Ссылка заменена действующим аудитом `audit_relationships.py` и корневой `.venv`.',
             '- У общего реестра `registry.number`, `registry.date`, `registry.note` остаются в контексте, '
             'но текущий DOCX их отдельно не печатает; номер и дата объединены в `number_date`. '
             '`registry.organization` вычисляется только при единственном исполнителе ролей `work_performer` / `builder`; '
             'пустое значение не заменяется произвольной организацией.',
             '- У титульника `copies`, `volumes`, `font` — управляющие поля. `pages` и `contractors_info` '
             'создаются `titles.prepare_context`, хотя их нет в JSON. Это проверенное исключение, а не неопределённые маркеры.',
             '- Титульник по умолчанию использует прежние русские ключи ролей (`Заказчик`, `Технический_заказчик`, '
             '`Генподрядчик`, `Подрядчик`). Веб-карточка участников использует английские ключи; '
             'для этих назначений при создании титульника требуется явное сопоставление `roles` в `titles.add_title`. '
             'Без него необязательные организации могут быть пустыми. Автоматическое переименование ролей здесь не выполнялось.', '',
             '<a id="screens"></a>', '## Экран → сущности → документы', '',
             '| Раздел интерфейса | Хранилище и связи | Использование |', '|---|---|---|',
             '| Объект, реквизиты, разрешения | objects → projects; object_units | object.*, project.*, unit.*; реестр и титульник |',
             '| Участники | organizations → signatories; object_participants; organization_assignments; signatory_assignments; participant_periods | organizations.<роль>.*, signatories.<роль>.*, companies; выбор акта через act_organizations / act_signatories |',
             '| РД, исходные файлы | attachments; object_attachments / project_attachments; project_files | project_documentation; реестр; контроль SHA-256 и оригинала |',
             '| Ресурсы | resources → resource_sources / resource_attachments; resource_imports / resource_import_rows; specification_pending | act_resources → resources; ведомости DOCX и XLSX; качество |',
             '| Схемы | schemes → scheme_attachments; act_schemes | schemes в контексте акта; реестр; связь не подставляет схему в произвольное пустое поле |',
             '| Поставки, входной контроль | supplies; quality_reviews; workspace_entries(kind=incoming), work_fields | materials через act_materials; ЖВК из journals.journal_data |',
             '| ОЖР, работы, ЖПК | workspace_entries → work_materials → work_facts; work_material_allocations → supplies | act_entry_sources → entries; act_facts → facts; journal_rows по mapping |',
             '| Специальные журналы | special_journals → организации / представители / акт | раздел 2 ОЖР; автоматические журналы — представления, не отдельные таблицы |',
             '| Основные документы | document_types → acts → состав и участники; document_versions | JSON defaults → overrides → bindings → resolve_fields → DOCX |',
             '| Выпуск, реестр, сдача | generated_documents → releases; final_reviews; package_requirements; deliveries → delivery_events / delivery_remarks | точный файл, хеш, выбранный выпуск, комплект, передача |',
             '| Настройки и вход | отдельная БД accounts: users / settings / document_roots | выбор рабочей БД; правами управляет сервер, без FK на участников строительства |', '',
             '<a id="resolution"></a>', '## Порядок разрешения полей', '',
             '```mermaid', 'flowchart LR', '  C["catalog.json + две общие формы"] --> T["document_types.fields"]',
             '  T --> M["merge_fields: overrides акта по key"]', '  A["acts.fields"] --> M',
             '  M --> D["apply_form_defaults + bindings.json"]', '  DB["карточки БД + состав + выбранные участники"] --> R["roots build_context"]',
             '  D --> F["resolve_fields"]', '  R --> F', '  F --> P["prepare_context для титульника"]',
             '  P --> DOCX["StrictUndefined DOCX"]', '  DOCX --> G["generated_documents → releases → document_versions"]', '```', '',
             '1. `form_catalog.catalog()` добавляет к 89 записям файла каталога `СП_77_А_21` и `РЕЕСТР_ИТД`. '
             'Код формы совпадает с именем единственного DOCX и `acts.act_type → document_types.code`.',
             '2. JSON регистрируется в `document_types.fields`. `acts.fields` заменяет определения по `key`, '
             'а не только значения: тип, source, required и формат также входят в определение.',
             '3. `apply_form_defaults` связывает только пустые literal-поля из bindings. Непустой ручной текст, '
             'пользовательские ссылки, hidden и not_applicable сохраняются. FIELD_CONTINUATIONS объединяет продолжения; '
             'исходные удалённые ключи перечислены у формы.',
             '4. `build_context` читает актуальные карточки, выбранные ресурсы/схемы/факты и участников. '
             'Назначение раздела перекрывает объект; явный выбор акта уточняет его. Для подписанного акта используется signers_json. '
             'Организация и представитель проверяются на совместимость общей службой.',
             '5. `reference` читает source; `literal` читает value; `signatory` форматирует выбранного представителя и его организацию; '
             '`table` разрешает каждую дочернюю колонку с item и row.number. `field_values.X` обращается только к уже разрешённому полю '
             'в текущем проходе. Форматы дат применяются после чтения источника.',
             '6. Пропуски required блокируют финальный контекст. В черновике выводится тире. '
             'Поля hidden/not_applicable дают пустую строку/таблицу; неприменимость требует reason.',
             '7. Проверка статических утверждений привязана к хешам шаблона и контекста (`final_reviews`). '
             'История выпуска сохраняет контекст и хеш файла; версии связываются с точным release/attachment.',
             '8. `resources.document_resource` вычисляет количество для DOCX и XLSX при каждом построении: '
             'явный итог resources.qty_fact имеет приоритет; если его нет, используются только confirmed-факты ресурса. '
             'При неизвестном количестве хотя бы одного подтверждённого прироста итог остаётся неизвестным. '
             'Нулевой итог сохраняется; pending/void не суммируются; БД итогов не переписывается. '
             'Скачивание последней неподписанной версии заново выпускает документ с текущими источниками. '
             'Скачивание исторической или подписанной версии возвращает точный сохранённый файл.', '',
             '### Удаление связанных записей', '',
             '`deletion.py` строит и проверяет план перед подтверждением. Обязательная FK-ссылка '
             '(NOT NULL или PK) удаляет дочернюю строку, необязательная очищается. Назначения '
             'объекта/раздела удаляются при удалении уровня, поскольку CHECK требует ровно один уровень. '
             'Составные FK обрабатываются вместе. JSON-ссылки work_fields на person_id/org_id '
             'обязательны для персонала ОЖР и удаляют его строку; supply_id, quality_review_id, entry_id очищаются. '
             'Явные ссылки Organisation.ID/Representative.ID в полях acts каскадно удаляют документ '
             'при required и очищаются при необязательном поле; черновые карточки версий синхронизируются. '
             'Архивные файлы и снимки выпущенных версий остаются историей. План содержит каждую удаляемую '
             'и изменяемую строку, объект/раздел и основание. Подтверждение связано с путём БД, '
             'выбранной записью и состоянием всех затронутых строк; изменение связей требует нового плана. '
             'Применение атомарно, проверяет foreign_key_check и обновляет ревизии очищенных записей.', '',
             '<a id="schema"></a>', '## Все таблицы и колонки', '',
             'Схема снята с новой временной БД после применения всех миграций. Для каждого поля показаны тип, '
             'NOT NULL, порядок в PK, DEFAULT, FK и прямые потребители формы. CHECK, UNIQUE, составные ключи, '
             'индексы и триггеры приведены точным DDL. Для INTEGER PRIMARY KEY SQLite может показывать notnull=0; '
             'это не отменяет свойства первичного ключа.', '']
    groups = [('Основная БД ИТД', tables)] + [(f'Отдельная БД: {module}', s) for module, s in result['auxiliary'].items()]
    modules = {p.stem: p.read_text() for p in (ROOT / 'app/itd').glob('*.py')}
    for title, group in groups:
        lines += ['### ' + title, '']
        if title.endswith('knowledge'):
            lines += ['`knowledge_fts` — виртуальная FTS5-таблица. Её внутренние shadow-таблицы управляются SQLite и не являются деловыми сущностями. '
                      'Связь knowledge_entries.id ↔ knowledge_fts.id логическая, без FK.', '']
        for name, table in group.items():
            lines += [f'<a id="table-{name}"></a>', f'#### {name} — {TABLE_LABELS.get(name, "Связующая / служебная сущность")}', '']
            consumers = [link(f'app/itd/{module}.py') for module, text in modules.items() if re.search(r'\b' + re.escape(name) + r'\b', text)]
            lines += ['Упоминания таблицы в Python (статический указатель, включая SQL; динамические обращения см. сервисы): ' + ', '.join(consumers) + '.', '',
                      '| Колонка | SQL-тип; ограничения | FK / прямые поля форм |', '|---|---|---|']
            for col in table['columns']:
                constraints = [col['type'] or 'ANY']
                if col['notnull']: constraints.append('NOT NULL')
                if col['pk']: constraints.append('PK #' + str(col['pk']))
                if col['dflt_value'] is not None: constraints.append('DEFAULT ' + col['dflt_value'])
                targets = [f'FK #{fk["id"]}.{fk["seq"]} → {fk["table"]}.{fk["to"]}; DELETE {fk["on_delete"]}, UPDATE {fk["on_update"]}' for fk in table['fks'] if fk['from'] == col['name']]
                uses = reverse[name + '.' + col['name']]
                targets.append(f'Прямые привязки: {len(uses)}; [список](#source-{name}-{col["name"]})' if uses else 'Нет прямой привязки поля каталога; служебное/учётное поле или косвенное использование в сервисе')
                lines.append('| `' + col['name'] + '` | ' + md('; '.join(constraints)) + ' | ' + md('<br>'.join(targets)) + ' |')
            lines += ['', '<details><summary>Точный DDL таблицы, индексов и триггеров</summary>', '', '```sql', table['sql'] + ';']
            for index in table['indexes']:
                if index['name'].startswith('sqlite_autoindex'):
                    lines.append('-- ' + index['name'] + ': реализует PK/UNIQUE из CREATE TABLE')
            for extra in table['extras']:
                lines.append(extra['sql'] + ';')
            lines += ['```', '', '</details>', '']
    lines += ['<a id="sources"></a>', '## Источники и обратные связи', '',
              'Ниже обратный индекс **прямых** источников: физическая колонка → код формы.ключ. '
              'Для вычисляемых источников включены известные составляющие. Составы актов, условия отбора, FK '
              'и JSON-снимки — косвенные зависимости, они описаны в таблицах и порядке разрешения. '
              'Ручное значение сохраняется в acts.fields и не требует отдельной физической колонки.', '']
    for col, uses in sorted(reverse.items()):
        lines += [f'<a id="source-{col.replace(".", "-")}"></a>', f'### `{col}`', '', ', '.join('`' + x + '`' for x in uses), '']
    lines += ['### Корни контекста build_context', '', '| Источник | Отбор / происхождение |', '|---|---|',
              '| object / project / act | Карточка акта → раздел → объект; project.city с fallback objects.city |',
              '| resources | Только act_resources, ORDER BY ordinal; _source из resource_sources (attachment_id, source_key, page, sheet, locator) |',
              '| schemes | Только act_schemes, ORDER BY ordinal |',
              '| facts | act_facts → work_facts, только status=confirmed, ORDER BY f.id |',
              '| entries | act_entry_sources → workspace_entries, по entry_date,id; work_fields разобран из JSON |',
              '| materials | act_materials → supplies; quantity поставки и отдельная act_quantity; это не resources |',
              '| journal_rows | manual.journal_rows: act_journals.mapping + записи выбранного kind/work_type |',
              '| unit / section_designer | projects.unit_id / designer_org_id; корень существует только при выбранной связи |',
              '| organizations / signatories | Назначения объекта → раздела → выбора в акте; roles — ключи, не названия |',
              '| participant_ids | ojr.directory текущего объекта; Organisation.ID / Representative.ID, явный ~default=role |',
              '| companies | Представление назначений: role, name=(short_name или full_name), остальные реквизиты organizations |',
              '| participation_periods | Все participant_periods объекта |',
              '| work_summary.description | ojr.act_work_description из связанных работ / фактов |',
              '| project_documentation | code, designer_name, description, section_description, object_and_project, object_description; form_defaults.documentation_context |',
              '| registry | Только для form_group=registry; registry.registry_rows |',
              '| field_values / item / row | Создаёт resolve_fields; порядок полей / текущая строка / порядковый номер |', '',
              'Семантические псевдонимы: ' + '; '.join(f'`{k}` → `{v}`' for k, v in SEMANTIC_SOURCES.items()) + '.', '',
              '### Колонки вычисляемого реестра', '',
              '`no` — нумерация после сортировки; `entity/id/group` — идентичность и тип строки; '
              '`name` — document_types.name / attachments.title / schemes.name / имя журнала; '
              '`number` — acts.act_num, если форма ссылается на номер, либо attachments.doc_num / schemes.num; '
              '`date` — acts.date_signed, дата первой записи журнала, attachments.doc_date либо дата единственного файла схемы; '
              '`sheets_count` — acts/attachments/schemes.sheets_count; `note` — registry_note / note и диагностика даты. '
              '`number_date` объединяет номер и дату; `pages` вычисляет страницы по количеству листов (после неизвестного количества диапазоны пусты); '
              '`organization` — единственная организация выбранных подписантов work_performer/builder. '
              'Импортные спецификации исключены; дублированные файлы схем объединяются только при однозначной связи.', '',
              '### Роли документов', '', '| Ключ | Название |', '|---|---|']
    for key, label in sorted(DOC_ROLES.items()):
        lines.append(f'| `{key}` | {md(label)} |')
    lines += ['', 'Роли карточки объекта (`object_participants`) не равнозначны назначениям документов: ' + '; '.join(f'`{k}` — {v}' for k, v in ROLES.items()) + '.', '',
              '<a id="forms"></a>', '## Все шаблоны и каждое поле', '',
              'В таблицах перечислены **все эффективные определения**, в том числе дочерние колонки и непечатаемые поля. '
              'Имена вида tN_rN_cN — ключи генератора; фактическое местоположение подтверждено разбором DOCX. '
              'Для table.key дочерняя колонка имеет путь `table.key`; item в Jinja — локальная переменная цикла. '
              'Колонка «части DOCX» показывает все части, где найдено обращение. '
              'Полные XPath каждого маркера доступны в JSON-отчёте аудита через `--json`. '
              'Обязательность и формат берутся после применения defaults; пустые ручные поля не считаются автоматически заполненными.', '',
              '| Код | Название | Полей с вложенными колонками |', '|---|---|---|']
    for index, form in enumerate(forms, 1):
        item = form['item']
        lines.append(f'| [{item["code"]}](#form-{index}) | {md(item["name"])} | {len(form["rows"])} |')
    for index, form in enumerate(forms, 1):
        item = form['item']
        lines += ['', f'<a id="form-{index}"></a>', f'### {item["code"]} — {item["name"]}', '',
                  f'Группа: `{item["group"]}`. DOCX: {link(form["template"])}. Определения: {link(item["fields"])}.', '',
                  f'SHA-256 рабочего DOCX: `{form["template_sha"]}`.', '']
        if item.get('source'):
            lines += [f'Оригинал по каталогу: {link(item["source"])}. SHA-256: `{item["source_sha256"]}`. {form["provenance"]}.', '']
        else:
            lines += [form['provenance'] + '; см. app/templates/README.md.', '']
        lines += ['| Поле / колонка | Подпись | Вид; required; формат | Источник / назначение | Использование; части DOCX |', '|---|---|---|---|---|']
        for row in form['rows']:
            f, path = row['field'], row['path']
            flags = [f['kind'], 'required=' + str(f.get('required', False)).lower()]
            flags += [k + '=' + str(f[k]) for k in ('format', 'value_type', 'state', 'reason') if k in f]
            parts = sorted(form['refs'].get(path, []))
            desc = row['description']
            if row['columns']:
                desc += ' ← ' + ', '.join(row['columns'])
            lines.append('| `' + path + '` | ' + md(f.get('label', '—')) + ' | ' + md('; '.join(flags)) + ' | ' + md(desc) + ' | ' + md(row['status'] + ('; ' + ', '.join(parts) if parts else '')) + ' |')
        continuation = FIELD_CONTINUATIONS.get(item['code'], {})
        if continuation:
            lines += ['', 'Объединение исходных полей (хвостовые ключи удалены из эффективного контекста): ' + '; '.join(f'`{key}` ← ' + ', '.join(f'`{tail}`' for tail in tails) for key, tails in continuation.items()) + '.']
            removed = {key for keys in continuation.values() for key in keys}
            lines += ['', '| Исходное поле продолжения | Подпись | Исходное определение |', '|---|---|---|']
            for path, field in flatten(form['raw']):
                if path in removed:
                    lines.append('| `' + path + '` | ' + md(field.get('label', '—')) + ' | ' + md(json.dumps(field, ensure_ascii=False)) + ' |')
        if item['code'] == TITLE_CODE:
            lines += ['', 'Дополнительные вычисленные поля DOCX: `pages[].duplicates`, `pages[].volumes_info`, '
                      '`contractors_info`. Контракт задаёт `titles.prepare_context`; copies × volumes определяет число страниц.']
    lines += ['', '<a id="xlsx"></a>', '## Общая ведомость XLSX', '',
              'Шаблон: ' + link('app/templates/Ведомость оборудования и материалов.xlsx') + '. '
              'Это отдельный контракт `statement.py` / `statement.mjs`; он не связан с document_types и не использует Jinja.', '',
              '| Ячейка / колонка с 8-й строки | Источник |', '|---|---|',
              '| B3 | objects.name по projects.object_id |', '| B4 | projects.name + projects.code (section_label) |',
              '| A | resources.spec_num |', '| B | resources.category |', '| C | resources.name |',
              '| D | resources.type_mark |', '| E | resources.serial_num |', '| F | resources.unit |',
              '| G | resources.qty_proj |', '| H | resources.qty_fact; если итог не внесён — сумма подтверждённых work_facts.quantity того же ресурса при известных количествах и совпадающей единице |',
              '| I | resource_attachments → attachments: title, doc_num, doc_date; certificate/passport или file_kind=quality |', '',
              'Ресурсы отбираются по project_id, ORDER BY id. Результат регистрируется в releases(kind=xlsx, act_id=NULL). '
              'Листы/строки образца, ширины и объединения — оформление; данные начинают записываться с 8-й строки.', '',
              '### JSON-связи и поля журналов', '',
              '- `workspace_entries.work_fields` — расширяемый JSON, не отдельная SQL-таблица. '
              'Базовые поля работ: cable(line_number, mark, drum, couplings, temperature, heating), '
              'general(location, method, tests). Для ОЖР journal_section выбирает раздел; '
              'раздел 1: organization, person, org_id, person_id, start_date, end_date, scope, authority; '
              'раздел 2: issued_date, keeper, transfer_date, recipient; '
              'разделы 4/6: defects, deadline, resolved_date, resolved_by. '
              'Разделы 3/5 собираются из работ и документов. Входной контроль использует incoming_result, '
              'entry_id, supply_id, quality_review_id и дополнительные описания. ID в JSON — логические связи, '
              'проверяются journals.validate_entry, а не SQL FK. Полный JSON допускает дополнительные скалярные ключи; '
              'закрытого исчерпывающего SQL-списка для него нет.',
              '- `acts.fields` / `document_types.fields` — упорядоченные массивы определений; '
              '`key, label, kind, required, source/value, fields, role, template/presentation, format, value_type, state, reason` '
              'определяют разрешение. `role_slot/role_options` обслуживают выбор варианта бланка.',
              '- `document_versions.card_json`, `signers_json`, `snapshot_json` и `act_execution_status.signers_json` '
              'хранят карточки и снимки. `generated_documents.context_json` — контекст конкретного выпуска. '
              'Это копии значений на момент события, а не живые FK на все вложенные реквизиты.',
              '- `act_entry_sources.source_json` — снимок записи работ для обнаружения изменений; '
              '`act_journals.mapping` — сопоставление полей журнала; '
              '`resource_import_rows.data_json` и `specification_pending.item_json` — импортные строки; '
              '`projects.agent_context`, `audit_events.before_json/after_json`, `file_operations.moves_json` — служебные состояния.', '',
              '<a id="update"></a>', '## Как обновить карту', '',
              '```bash', 'PYTHONPATH=app .venv/bin/python app/scripts/audit_relationships.py',
              'PYTHONPATH=app .venv/bin/python app/scripts/audit_relationships.py --write-map',
              'PYTHONPATH=app .venv/bin/python app/scripts/audit_relationships.py --json /tmp/itd-relationships.json',
              'PYTHONPATH=app .venv/bin/python -m unittest discover -s app/tests -v', '```', '',
              'Аудит создаёт БД и результаты рендеринга только во временном каталоге. '
              'Код выхода ненулевой при ошибке контракта. MAP.md обновляется только при успешной проверке; '
              'при изменениях SQL, кода контекста, каталога, bindings или DOCX обновляйте карту и выполняйте тесты. '
              'Новые вычисляемые источники нужно явно добавить в проверяемый контракт скрипта. '
              'Для фактической БД требуется отдельно согласовать БД и объект; эта карта не удостоверяет её содержимое.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-map', action='store_true')
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    result = run_audit()
    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=lambda obj: sorted(obj) if isinstance(obj, set) else str(obj)) + '\n')
    print(f'Таблиц ИТД: {len(result["tables"])}; форм проверено: {len(result["forms"])}; ошибок: {len(result["errors"])}')
    for error in result['errors']:
        print('ОШИБКА:', error)
    for warning in result['warnings']:
        print('ОГРАНИЧЕНИЕ:', warning)
    if result['errors']:
        return 1
    if args.write_map:
        (ROOT / 'MAP.md').write_text(render_map(result), encoding='utf-8')
        print('MAP.md обновлён')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
