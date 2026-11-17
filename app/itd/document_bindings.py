"""Источники функции f: только деловые записи текущего объекта/раздела.

Имена таблиц заданы здесь, а не принимаются от клиента. Никакого SQL от клиента.
Существующие source и представления подписантов остаются прежними.
"""
from .workflow import same_project

TABLES = {
    'objects': 'Объект', 'projects': 'Раздел РД', 'acts': 'Документы',
    'organizations': 'Организации', 'signatories': 'Представители',
    'resources': 'Ресурсы', 'schemes': 'Схемы', 'workspace_entries': 'Записи журналов',
    'work_facts': 'Факты монтажа', 'supplies': 'Поставки', 'object_units': 'Части объекта',
}
COLUMNS = {
    'name': 'Наименование', 'city': 'Город', 'address': 'Адрес', 'code': 'Шифр',
    'section_code': 'Код раздела', 'full_name': 'Полное наименование', 'short_name': 'Краткое наименование',
    'fio': 'ФИО', 'position': 'Должность', 'inn': 'ИНН', 'ogrn': 'ОГРН', 'kpp': 'КПП',
    'order_doc': 'Основание полномочий', 'nrs_id': 'Номер в НРС', 'act_num': 'Номер документа',
    'date_signed': 'Дата подписания', 'filename_title': 'Название файла', 'registry_note': 'Примечание реестра',
    'sheets_count': 'Количество листов', 'description': 'Описание', 'type_mark': 'Тип / марка',
    'serial_num': 'Заводской номер', 'unit': 'Единица измерения', 'quantity': 'Количество',
    'qty_proj': 'Количество по проекту', 'qty_fact': 'Фактическое количество', 'spec_num': 'Позиция спецификации',
    'entry_date': 'Дата записи', 'work_description': 'Наименование работ и место', 'work_date': 'Дата работ',
    'act_type': 'Форма документа', 'author_supervision': 'Авторский надзор',
    'authority_date': 'Дата основания полномочий', 'authority_num': 'Номер основания полномочий',
    'authority_type': 'Вид основания полномочий', 'batch_num': 'Номер партии', 'category': 'Категория',
    'conditions': 'Условия производства работ', 'construction_type': 'Вид строительства',
    'contract_date': 'Дата договора', 'contract_num': 'Номер договора', 'control_external': 'Внешний стройконтроль',
    'control_self': 'Собственный стройконтроль', 'details': 'Подробности', 'developer_functions': 'Функции застройщика',
    'display_name': 'Название в интерфейсе', 'email': 'Электронная почта', 'end_date': 'Дата окончания',
    'expertise_authority': 'Орган экспертизы', 'expertise_date': 'Дата заключения экспертизы',
    'expertise_num': 'Номер заключения экспертизы', 'first_name': 'Имя', 'last_name': 'Фамилия',
    'middle_name': 'Отчество', 'form_set': 'Комплект форм', 'genplan_num': 'Номер генплана',
    'gip': 'Главный инженер проекта', 'gsn_case': 'Номер дела ГСН', 'inv_num': 'Инвентарный номер',
    'kind': 'Вид записи', 'location': 'Место работ', 'manufacturer': 'Изготовитель', 'note': 'Примечание',
    'num': 'Номер', 'permit_authority': 'Орган выдачи разрешения', 'permit_date': 'Дата разрешения',
    'permit_num': 'Номер разрешения', 'phone': 'Телефон', 'pnr_end': 'Окончание ПНР', 'pnr_start': 'Начало ПНР',
    'postal_code': 'Почтовый индекс', 'ref_code': 'Код ссылки', 'reported_by': 'Кем переданы сведения',
    'responsible': 'Ответственный', 'sequence_no': 'Порядковый номер', 'smr_end': 'Окончание СМР',
    'smr_start': 'Начало СМР', 'source': 'Источник сведений', 'sro_certificate_date': 'Дата выписки СРО',
    'sro_certificate_num': 'Номер выписки СРО', 'sro_info': 'Сведения о СРО', 'sro_inn': 'ИНН СРО',
    'sro_ogrn': 'ОГРН СРО', 'start_date': 'Дата начала', 'status': 'Статус', 'supplier': 'Поставщик',
    'supply_date': 'Дата поставки', 'unit_weight': 'Масса единицы', 'void_reason': 'Причина отмены',
    'work_end': 'Окончание работ', 'work_start': 'Начало работ', 'work_type': 'Вид работ',
    'doc_num': 'Номер документа', 'doc_date': 'Дата документа', 'number': 'Номер', 'title': 'Название',
}
# Не показываем служебные JSON, хеши, файловые пути и идентификаторы связей.
EXCLUDE = {'id', 'fields', 'agent_context', 'created_at', 'updated_at', 'revision', 'is_active', 'work_fields', 'source_key'}


def records(c, pid):
    project = c.execute('SELECT * FROM projects WHERE id=?', (pid,)).fetchone()
    if not project:
        raise ValueError('Раздел не найден')
    oid = project['object_id']
    result = {}
    for table in TABLES:
        if table == 'objects':
            rows = c.execute('SELECT * FROM objects WHERE id=?', (oid,))
        elif table == 'projects':
            rows = c.execute('SELECT * FROM projects WHERE id=?', (pid,))
        elif table == 'object_units':
            rows = c.execute('SELECT * FROM object_units WHERE object_id=?', (oid,))
        elif table == 'organizations':
            rows = c.execute('SELECT DISTINCT o.* FROM organizations o JOIN object_participants p ON p.org_id=o.id WHERE p.object_id=?', (oid,))
        elif table == 'signatories':
            rows = c.execute('SELECT DISTINCT s.* FROM signatories s JOIN object_participants p ON p.org_id=s.org_id WHERE p.object_id=?', (oid,))
        else:
            rows = c.execute(f'SELECT * FROM {table} WHERE project_id=? ORDER BY id', (pid,))
        result[table] = {'r'+str(row['id']): {
            key: row[key] for key in row.keys()
            if key not in EXCLUDE and (key == 'nrs_id' or not key.endswith(('_id', '_json', '_path', '_sha256')))
            and (row[key] is None or isinstance(row[key], (str, int, float)))
        } for row in rows}
    return result


def value_type(key, value):
    if 'date' in key or key in ('smr_start', 'smr_end', 'pnr_start', 'pnr_end', 'work_start', 'work_end'):
        return 'date'
    return 'number' if isinstance(value, (int, float)) or key in ('qty_proj', 'qty_fact', 'quantity', 'sheets_count', 'unit_weight') else 'text'


def catalog(c, pid, aid=None):
    values = records(c, pid)
    items = []
    for table, rows in values.items():
        for identity, row in rows.items():
            title = next((str(row[k]) for k in ('act_num', 'full_name', 'fio', 'name', 'title', 'entry_date') if row.get(k)), identity[1:])
            for key, value in row.items():
                # Для текущего объекта/раздела связь следует за карточкой, а не ID.
                root = {'objects': 'object', 'projects': 'project'}.get(table)
                source = f'{root}.{key}' if root else f'records.{table}.{identity}.{key}'
                items.append({'source': source, 'group': TABLES[table],
                              'label': f'{title} → {COLUMNS.get(key, key)}', 'value': value, 'value_type': value_type(key, value)})
    if aid is not None:
        act = same_project(c, 'acts', aid, pid)
        items += [{'source': 'act.'+key, 'group': 'Текущий документ',
                   'label': label, 'value': act[key], 'value_type': value_type(key, act[key])}
                  for key, label in COLUMNS.items() if key in act.keys() and key not in ('id', 'fields')]
    return items
