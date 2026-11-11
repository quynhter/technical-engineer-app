"""Единый контракт всех поставляемых DOCX. Рабочие базы не открываются.

Архив предыдущих рабочих редакций + декларативные английские пути свойств.
Повторное применение сохранённого контракта не переименовывает свойства.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree as E

from itd.form_catalog import catalog, catalog_fields
from itd.form_defaults import apply_form_defaults
from itd.template_objects import CONTRACTS

ROOT = Path(__file__).resolve().parents[2]
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + NS['w'] + '}'
ARCHIVE = ROOT / 'app/docs/template-layout/before-object-contract.zip'
# Английские имена типов сведений; не транслитерация и не координаты Word.
LABELS = [
    (r'представител|члены комиссии|генподрядчик|субподрядчик', 'representative'),
    (r'заказчик', 'customer'), (r'авторск.*надзор', 'author_supervision'),
    (r'обозначение формы', 'form_reference'), (r'свидетельство', 'certificate'),
    (r'размер', 'dimensions'), (r'хладон', 'refrigerant'), (r'конденсат', 'condensate'),
    (r'перемычк', 'bonding'), (r'особенности', 'features'), (r'заземляющ', 'earthing'),
    (r'паспорт', 'passport'), (r'перечислить|название', 'description'),
    (r'начало|окончание|год выпуска', 'date'), (r'оптически.*лини', 'optical_lines'),
    (r'подразделение', 'division'), (r'точности', 'accuracy_class'),
    (r'недодел|недостат|неоконч|дефект', 'defects'),
    (r'примечан|замечан|дополнител', 'notes'),
    (r'заключени|решени|пригодност|годност', 'conclusion'),
    (r'приложен|прилагаем', 'attachments'),
    (r'сертификат|документ.*качеств|паспорт.*качеств', 'quality_documents'),
    (r'норматив|стандарт|ГОСТ|техническ.*услов', 'requirements'),
    (r'согласован|отступлен|отклонени', 'deviations'),
    (r'недостающее.*масл', 'missing_oil_quantity'),
    (r'масл', 'oil'), (r'электролит', 'electrolyte'),
    (r'заглуш', 'plugs'), (r'ремонт', 'repair'),
    (r'манометр|мегаомметр|измерительн.*прибор|контрольн.*прибор', 'instrument'),
    (r'газопровод|газооборудован', 'gas_pipeline'),
    (r'пусконалад|комплексн.*опробован', 'commissioning'),
    (r'прочност', 'strength'), (r'герметичност', 'tightness'),
    (r'плотност', 'density'), (r'падени.*давлен', 'pressure_drop'),
    (r'давлен', 'pressure'), (r'температур|°[СC]|º[СC]', 'temperature'),
    (r'напряжени|кВ|\bВ\b', 'voltage'), (r'сопротивлен', 'resistance'),
    (r'мощност', 'power'), (r'ёмкост|емкост', 'capacity'),
    (r'затухан', 'attenuation'), (r'расход', 'flow_rate'),
    (r'толщин', 'thickness'), (r'диаметр', 'diameter'),
    (r'сечени', 'cross_section'), (r'длин|протяж', 'length'),
    (r'высот|отметк|\bотм\.', 'elevation'), (r'глубин', 'depth'),
    (r'координат|ос[яьи]х|пикет', 'location'),
    (r'болт|анкер', 'bolts'), (r'заземлен|заземлён', 'earthing'),
    (r'изоляци', 'insulation'), (r'гидроизол', 'waterproofing'),
    (r'фундамент', 'foundation'), (r'бетон', 'concrete'),
    (r'опор', 'support'), (r'барабан|бухт', 'drum'),
    (r'муфт|компенсатор', 'joint'), (r'стык|соединен|соединён', 'connection'),
    (r'кабел|провод', 'cable'), (r'труб', 'pipe'),
    (r'свар|шв|клейм', 'welding'), (r'термообработ|прогрев|подогрев', 'heating'),
    (r'оборудован|агрегат|установк|прибор', 'equipment'),
    (r'материал|издели|ресурс', 'materials'),
    (r'конструкц|элемент', 'structure'), (r'покрыти|сло[еяй]', 'coating'),
    (r'срок|дата|число.*месяц|месяц.*год|начат|окончен', 'date'),
    (r'продолжительност|врем|выдержк|течение|\bч\b|\bмин\b', 'duration'),
    (r'количеств|кол.во|число|\bшт\b', 'quantity'),
    (r'объ[её]м', 'volume'), (r'процент|\b%', 'percentage'),
    (r'номер|№|\bN\b|шифр|буквенно', 'number'),
    (r'чертеж|чертёж|проект', 'design_documentation'),
    (r'организаци|предприяти|изготовител|завод', 'organisation'),
    (r'Ф.И.О|фамили|подпис|ответственн|руководител|производител.*работ', 'representative'),
    (r'должност', 'position'), (r'образован|специальност|разряд', 'qualification'),
    (r'помещени|сооружени|объект|место|площадк|адрес|участ', 'location'),
    (r'испытан|контрол|осмотр|проверк|принят', 'test'),
    (r'комплект', 'completeness'), (r'состояни', 'condition'),
    (r'метод|способ', 'method'), (r'марка|тип|модел', 'type'),
    (r'систем|сет[ьи]|ВЛ|ОЭТС', 'system'),
    (r'класс|категор', 'class'), (r'масса|вес', 'weight'),
    (r'работ', 'work'), (r'документаци', 'documentation'),
    (r'среда|среды', 'medium'), (r'шкала', 'scale'),
    (r'поз\.|позици', 'position_number'), (r'ОВ|волокон', 'fibre'),
]
TABLE_NAMES = {
    'И_1_13_07_03': ['design_changes'], 'И_1_13_07_04': ['defects'],
    'И_1_13_07_05': ['equipment'], 'И_1_13_07_06': ['defects'],
    'И_1_13_07_10': ['battery_measurements'], 'И_1_13_07_12': ['pressure_tests'],
    'И_1_13_07_15': ['cable_installation'], 'И_1_13_07_16': ['cable_joints'],
    'И_1_13_07_18': ['foundations'], 'И_1_13_07_19': ['connections'],
    'И_1_13_07_21': ['wire_measurements'], 'И_1_13_07_22': ['tensioning'],
    'И_1_13_07_24': ['earthing'],
    'СП_77_А_1': ['drawings'], 'СП_77_А_3': ['materials'], 'СП_77_А_4': ['fibre_measurements'],
    'СП_77_А_7': ['pressure_tests'], 'СП_77_А_8': ['instruments', 'tightness_tests'],
    'СП_77_А_13': ['welding'], 'СП_77_А_14': ['weld_inspections'], 'СП_77_А_15': ['specialists'],
    'СП_77_А_16': ['instruments', 'insulation_measurements'], 'СП_77_А_17': ['cable_heating'],
    'СП_77_А_18': ['pressure_tests'], 'СП_77_А_19_УЧАСТОК': ['fibre_measurements'],
    'СП_77_А_24': ['accepted_work'],
}
COLUMN_NAMES = {
    ('СП_77_А_19_УЧАСТОК', 'rows_0_18'): ['fibre_number', 'power_ab_input', 'power_ab_output', 'power_ba_input', 'power_ba_output', 'attenuation_db', 'measured_on'],
    ('СП_77_А_16', 'rows_0_22'): ['number', 'name', 'type', 'serial_number', 'scale', 'accuracy_class', 'notes'],
    ('СП_77_А_16', 'rows_0_33'): ['number', 'drawing_mark', 'cable_type', 'cores_and_cross_section', 'between_cores_mohm', 'to_ground_mohm', 'notes'],
    ('СП_77_А_8', 'rows_0_21'): ['number', 'name', 'type', 'serial_number', 'scale', 'accuracy_class', 'notes'],
    ('СП_77_А_7', 'rows_0_21'): ['number', 'name', 'inner_diameter_mm', 'length_mm', 'strength_pressure_mpa', 'tightness_pressure_mpa', 'notes'],
}
FIELD_NAMES = {
    **{(f'СП_42_101_2003_{code}', f't{table}_r2_c{col}'): 'form.ready_date.' + part
       for code, table in [('Т', 7), ('С', 7), ('Р', 11)]
       for col, part in [(2, 'day'), (4, 'month'), (6, 'year')]},
    **{('СП_72_Д', f't1_r0_c{col}'): 'form.signed_date.' + part
       for col, part in [(3, 'day'), (5, 'month'), (7, 'year')]},
    **{('СП_70_И', f't{table}_r0_c1'): f'form.attachments.document_{index}'
       for table, index in [(16, 1), (17, 2)]},
    ('СП_77_А_3', 't5_r0_c0'): 'form.specification_reference',
    **{('СП_77_А_22', f't9_r{row}_c1'): f'form.attachments.document_{row + 1}' for row in range(3)},
    **{('СП_77_А_23', f't4_r0_c{col}'): 'form.commission_order.date.' + part
       for col, part in [(1, 'day'), (3, 'month'), (5, 'year')]},
    ('СП_77_А_23', 't4_r0_c7'): 'form.commission_order.number',
    **{('СП_77_А_23', f't8_r0_c{col}'): 'form.' + period + '.' + part
       for col, period, part in [(1, 'work_start', 'day'), (3, 'work_start', 'month'), (5, 'work_start', 'year'),
                                  (7, 'work_end', 'day'), (9, 'work_end', 'month'), (11, 'work_end', 'year')]},
    ('СП_77_А_19_ИЗМЕРЕНИЯ', 't0_r26_c0'): 'form.acceptance_conclusion',
    ('СП_77_А_18', 't0_r37_c0'): 'form.explosion_zone',
    ('СП_40_102_2000_Е', 't5_r2_c3'): 'form.length_mm',
    ('СП_77_А_13', 't0_r19_c10'): 'form.installation_manager_date',
    **{('СП_77_А_19_МУФТА', f't0_r{row}_c{col}'): f'form.fibres.fibre_{row - 21}.attenuation_' + ('ab_db' if col == 1 else 'ba_db')
       for row in range(22, 30) for col in (1, 2)},
    **{('СП_77_А_15', f't0_r10_c{col}'): f'form.column_notes.' + name
       for col, name in enumerate(('number', 'full_name', 'speciality', 'qualification', 'stamp', 'certificate', 'test_log', 'signature'))},
    ('СП_68_Н', 't0_r68_c1'): 'form.additional_statement',
    ('СП_68_Н', 't0_r69_c1'): 'form.additional_statement_continuation',
}


def text(node):
    return ''.join(node.xpath('.//w:t/text()', namespaces=NS))


def name(label, *, default='additional_information'):
    clean = re.sub(r'{{.*?}}|{%.*?%}', '', label or '')
    if re.fullmatch(r'[a-z][a-z_0-9]*', clean):
        return clean
    if re.search(r'№ п|N п|Графа 1\b', clean, re.I):
        return 'number'
    found = []
    for pattern, token in LABELS:
        if token not in found and re.search(pattern, clean, re.I):
            found.append(token)
    return '_'.join(found[:3]) or default


def unique(path, used):
    base = path
    index = 2
    while path in used:
        path = f'{base}_{index}'; index += 1
    used.add(path)
    return path


def strip_aliases(root):
    aliases = {}
    for p in list(root.iter(W + 'p')):
        value = text(p)
        for alias, original in re.findall(r'{%\s*(?:p\s+)?set\s+(\w+)\s*=\s*([\w.]+)\s*%}', value):
            aliases[alias] = aliases.get(original, original)
        if re.fullmatch(r'\s*{%p\s+set.*?%}\s*', value):
            p.getparent().remove(p)
    def marker(match):
        value = match[0]
        if re.match(r'{%\s*set\b', value):
            return ''
        return re.sub(r'\b\w+(?:\.\w+)*', lambda m: aliases.get(m[0], m[0]), value)
    for t in root.iter(W + 't'):
        if t.text:
            t.text = re.sub(r'{{.*?}}|{%.*?%}', marker, t.text)


def field_hints(root, fields):
    """Печатная подпись уточняет технические ключи старого импортёра."""
    definitions = {f['key']: f for f in fields}
    result = {}
    seen = set()
    date_index = 0
    for node in [*root.iter(W + 'p'), *root.iter(W + 'tr')]:
        value = text(node)
        keys = re.findall(r'{{\s*(\w+)\s*}}', value)
        candidates = [k for k in keys if k in definitions and definitions[k]['kind'] == 'literal'
                      and re.fullmatch(r'[\s"«»….20г]*', definitions[k].get('label', ''), re.I)]
        if re.search(r'г\.', value) and len(candidates) >= 3:
            for start in range(0, len(candidates) - 2, 3):
                group = candidates[start:start + 3]
                if any(k in seen for k in group):
                    continue
                date_index += 1
                prefix = 'work_start' if re.search(r'начат|начал|\bс\s*[«"]', value, re.I) else 'work_end' if re.search(r'оконче|\bпо\s*[«"]', value, re.I) else 'test_date'
                if date_index > 1:
                    prefix += '_' + str(date_index)
                for key, part in zip(group, ('day', 'month', 'year')):
                    result[key] = 'form.' + prefix + '.' + part
                seen.update(group)
    for row in root.iter(W + 'tr'):
        raw = text(row)
        for key in re.findall(r'{{\s*(\w+)\s*}}', raw):
            if key not in definitions or key in result:
                continue
            field = definitions[key]
            if name(field.get('label')) != 'additional_information':
                continue
            context = re.sub(r'{{.*?}}|{%.*?%}', ' ', raw)
            readable = name(context)
            if readable == 'additional_information':
                for neighbour in (row.getprevious(), row.getnext()):
                    if neighbour is not None:
                        readable = name(text(neighbour))
                        if readable != 'additional_information':
                            break
            if readable != 'additional_information':
                result[key] = 'form.' + readable
    return result


def make_contract(code, fields, hints=None):
    used = set()
    result = {}
    table_names = iter(TABLE_NAMES.get(code, []))
    legacy_role = {'Заказчик': 'customer', 'Технический_заказчик': 'technical_customer',
                   'Генподрядчик': 'general_contractor', 'Подрядчик': 'builder'}
    for f in fields:
        key = f['key']; source = f.get('source', '')
        path = f.get('template_path')
        if path:
            used.add(path)
        elif f['kind'] == 'table':
            path = 'companies' if key == 'companies' else 'form.' + (key if not key.startswith('rows_') else next(table_names, name(f.get('label'), default='records')))
        elif source == 'act.date_signed':
            path = 'document.date.' + {'day_2digits': 'day', 'month_genitive_ru': 'month', 'year_4digits': 'year'}.get(f.get('format'), 'text')
        elif source == 'act.act_num':
            path = 'document.number'
        elif source.startswith('organizations.'):
            _, role, attr = source.split('.')
            path = 'organisations.' + legacy_role.get(role, role) + '.' + attr
        elif source.startswith('signatories.'):
            path = source.replace('signatories.', 'representatives.', 1).replace('.organization.', '.organisation.')
        elif source.startswith(('object.', 'project.')):
            path = source
        elif source.startswith('project_documentation.'):
            path = source.replace('project_documentation.', 'project.documentation.')
        elif f['kind'] == 'signatory':
            attr = 'fio_short' if f.get('presentation') == 'fio_short' else 'fio' if f.get('presentation', 'fio') == 'fio' and not f.get('template') else 'details'
            path = key + '.text' if key in ('recipient', 'consignor') else 'representatives.' + f['role'] + '.' + attr
        elif source.startswith('field_values.') and source.split('.')[1] in result:
            base = result[source.split('.')[1]]['path'].removeprefix('form.').replace('.', '_')
            path = 'form.' + ('actual_' if 'Фактически' in f.get('label', '') else 'repeated_') + base
        else:
            readable = key if not re.fullmatch(r'(?:p\d+_\d+|t\d+_r\d+_c\d+|x_\d+_\d+|date_\d+_\d+)', key) else name(f.get('label'))
            path = (hints or {}).get(key, 'form.' + readable)
        if (code, key) in FIELD_NAMES and not f.get('template_path'):
            path = FIELD_NAMES[(code, key)]
        if path in used and not f.get('template_path'):
            path = 'form.' + path.removeprefix('form.').replace('.', '_')
        if not f.get('template_path'):
            path = unique(path, used)
        binding = {'path': path}
        if f['kind'] == 'table':
            col_used = set()
            binding['columns'] = {}
            column_names = COLUMN_NAMES.get((code, key), [])
            for index, col in enumerate(f['fields']):
                key_col = col['key']
                label = col.get('label', '')
                attr = col.get('template_path') or (column_names[index] if index < len(column_names) else key_col if not re.fullmatch(r'c\d+', key_col) else name(label, default='value'))
                binding['columns'][key_col] = unique(attr, col_used)
        result[key] = binding
    return result


def normalize_template(root, spec):
    strip_aliases(root)
    stack = []
    for p in root.iter(W + 'p'):
        value = text(p)
        loop = re.search(r'{%\s*(?:tr\s+|p\s+)?for\s+(\w+)\s+in\s+(\w+)\s*%}', value)
        if loop:
            stack.append((loop[1], loop[2]))
        def marker(match):
            def replace(token):
                word = token[0]
                for var, table in reversed(stack):
                    if word.startswith(var + '.'):
                        col = word[len(var) + 1:]
                        return var + '.' + spec.get(table, {}).get('columns', {}).get(col, col)
                return spec.get(word, {}).get('path', word)
            return re.sub(r'\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', replace, match[0])
        for t in p.iter(W + 't'):
            if t.text:
                t.text = re.sub(r'{{.*?}}|{%.*?%}', marker, t.text)
                t.text = re.sub(r'20\s*({{\s*[a-z_0-9.]+\.year\s*}})', r'\1', t.text)
        if re.search(r'{%\s*(?:tr\s+|p\s+)?endfor\s*%}', value) and stack:
            stack.pop()
        nodes = list(p.iter(W + 't'))
        joined = ''.join(n.text or '' for n in nodes)
        removals = [(m.start(), m.end()) for m in re.finditer(r'20\s*(?={{\s*[a-z_0-9.]+\.year\s*}})', joined)]
        for start, end in reversed(removals):
            offset = 0
            for node in nodes:
                old = node.text or ''
                left, right = max(start - offset, 0), min(end - offset, len(old))
                if right > left:
                    node.text = old[:left] + old[right:]
                offset += len(old)


def write_template(path, spec, original=None):
    from app_layout_helper import fix_table, inline_dates
    from io import BytesIO
    with ZipFile(BytesIO(original) if original is not None else path) as z:
        parts = [(i, z.read(i)) for i in z.infolist()]
    updated = []
    for info, data in parts:
        if info.filename.startswith('word/') and info.filename.endswith('.xml') and (b'{{' in data or b'{%' in data or info.filename == 'word/document.xml'):
            root = E.fromstring(data)
            inline_dates(root)
            normalize_template(root, spec)
            if path.stem in {'СП_42_101_2003_П', 'СП_70_А', 'СП_73_Ж', 'СП_74_А', 'СП_76_Б'}:
                # У этих бланков пустой конечный абзац давал чистую страницу.
                body = root.find(W + 'body')
                if body is not None and len(body) > 1 and body[-2].tag == W + 'p' and not text(body[-2]).strip():
                    from app_layout_helper import paragraph, element
                    tail = paragraph('', size=2)
                    pr = tail.find(W + 'pPr')
                    spacing = pr.find(W + 'spacing')
                    spacing.set(W + 'after', '0'); spacing.set(W + 'line', '20'); spacing.set(W + 'lineRule', 'exact')
                    E.SubElement(pr, W + 'rPr').append(element('sz', val=2))
                    body.replace(body[-2], tail)
                    if path.stem == 'СП_74_А':
                        body.remove(tail)
            if path.stem == 'СП_70_А':
                # Разрыв отдельным абзацем мог переполнить предыдущую страницу
                # и оставить чистый лист перед списком персонала.
                body = root.find(W + 'body')
                for heading in list(body):
                    if heading.tag != W + 'p' or text(heading).strip() != 'СПИСОК':
                        continue
                    previous = heading.getprevious()
                    if previous is not None and not text(previous).strip() and previous.find('.//w:br[@w:type="page"]', NS) is not None:
                        body.remove(previous)
                        pr = heading.find(W + 'pPr')
                        if pr is None:
                            pr = E.Element(W + 'pPr'); heading.insert(0, pr)
                        if pr.find(W + 'pageBreakBefore') is None:
                            E.SubElement(pr, W + 'pageBreakBefore')
                for cached_break in root.iter(W + 'lastRenderedPageBreak'):
                    cached_break.getparent().remove(cached_break)
                for heading in list(body):
                    if heading.tag == W + 'p' and text(heading).strip() == 'СПИСОК':
                        previous = heading.getprevious()
                        while previous is not None and previous.tag == W + 'p' and not text(previous).strip():
                            body.remove(previous)
                            previous = heading.getprevious()
            if path.stem.startswith('МИНСТРОЙ_344_'):
                for run in root.iter(W + 'r'):
                    if '{{' not in text(run):
                        continue
                    pr = run.find(W + 'rPr')
                    if pr is None:
                        pr = E.Element(W + 'rPr'); run.insert(0, pr)
                    fonts = pr.find(W + 'rFonts')
                    if fonts is None:
                        fonts = E.SubElement(pr, W + 'rFonts')
                    for attr in list(fonts.attrib):
                        if attr.endswith('Theme'):
                            del fonts.attrib[attr]
                    for attr in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
                        fonts.set(W + attr, 'Times New Roman')
                    for prop in ('b', 'i'):
                        old = pr.find(W + prop)
                        if old is None:
                            old = E.SubElement(pr, W + prop)
                        old.set(W + 'val', '1')
            for table in root.iter(W + 'tbl'):
                fix_table(table)
                for height in table.findall('.//w:trPr/w:trHeight', NS):
                    height.set(W + 'hRule', 'atLeast')
            data = E.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        updated.append((info, data))
    with ZipFile(path, 'w') as z:
        for info, data in updated:
            z.writestr(info, data)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', action='store_true', help='Пересобрать контракт из архивной редакции; только для разработки миграции')
    args = parser.parse_args()
    import importlib.util
    import sys
    helper_spec = importlib.util.spec_from_file_location('app_layout_helper', ROOT / 'app/scripts/reflow_sp77_templates.py')
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    sys.modules['app_layout_helper'] = helper
    items = catalog()
    if not ARCHIVE.exists():
        ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(ARCHIVE, 'w', ZIP_DEFLATED) as z:
            manifest = {}
            for item in items:
                relative = item.get('template', 'app/templates/' + item['code'] + '.docx')
                path = ROOT / relative; data = path.read_bytes()
                z.writestr(relative, data)
                manifest[relative] = hashlib.sha256(data).hexdigest()
            z.writestr('sha256.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    contracts = {}
    for item in items:
        raw = catalog_fields(item)
        relative = item.get('template', 'app/templates/' + item['code'] + '.docx')
        original = None
        if args.rebuild:
            with ZipFile(ARCHIVE) as z:
                original = z.read(relative)
            for f in raw:
                f.pop('template_path', None)
                for col in f.get('fields', []):
                    col.pop('template_path', None)
        from io import BytesIO
        with ZipFile(BytesIO(original) if original is not None else ROOT / relative) as z:
            root = E.fromstring(z.read('word/document.xml'))
        strip_aliases(root)
        fields = apply_form_defaults(item['code'], raw)
        spec = make_contract(item['code'], fields, field_hints(root, fields))
        if item['code'] == 'ТИТУЛЬНЫЙ_ЛИСТ':
            spec.update(pages={'path': 'form.pages'}, contractors_info={'path': 'form.contractors_info'})
        contracts[item['code']] = spec
        for f in raw:
            f['template_path'] = spec[f['key']]['path']
            if f['kind'] == 'table':
                for col in f['fields']:
                    col['template_path'] = spec[f['key']]['columns'][col['key']]
        (ROOT / item['fields']).write_text(json.dumps(raw, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        path = ROOT / item.get('template', 'app/templates/' + item['code'] + '.docx')
        write_template(path, spec, original)
    CONTRACTS.write_text(json.dumps(contracts, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Унифицировано форм: {len(contracts)}')


if __name__ == '__main__':
    main()
