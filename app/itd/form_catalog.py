"""Каталог для явного выбора формы; регистрация только при создании документа."""
import json
from pathlib import PurePosixPath

from .acts import register_form
from .field_ui import describe_fields
from .form_defaults import apply_form_defaults
from .paths import default_templates


def catalog():
    items = json.loads((default_templates() / 'catalog.json').read_text())
    return items + [{'code': 'СП_77_А_21', 'name': 'Ведомость смонтированных технических средств автоматизации',
                     'group': 'statement', 'template': 'app/templates/СП 77.13330.2016/СП_77_А_21.docx',
                     'fields': 'app/forms/СП_77_А_21.fields.json'},
                    {'code': 'РЕЕСТР_ИТД', 'name': 'Реестр исполнительной документации',
                     'group': 'registry', 'fields': 'app/forms/РЕЕСТР_ИТД.fields.json'}]


def catalog_fields(item):
    return json.loads((default_templates().parent.parent / item['fields']).read_text())


def connect_form(c, code):
    if c.execute('SELECT 1 FROM document_types WHERE code=?', (code,)).fetchone():
        raise ValueError('Форма уже зарегистрирована; существующие настройки сохранены')
    item = next((f for f in catalog() if f['code'] == code), None)
    if item is None:
        raise ValueError('Форма отсутствует в каталоге')
    register_form(c, code=code, name=item['name'], form_group=item['group'], fields=catalog_fields(item))
    return {'code': code}


def available_forms(c, project_id):
    from .document_guidance import guidance_for
    project = c.execute('SELECT form_set FROM projects WHERE id=?', (project_id,)).fetchone()
    if project is None:
        raise ValueError('Раздел не найден')
    registered = {r['code']: dict(r) for r in c.execute('SELECT * FROM document_types ORDER BY name')}
    result = []
    for item in catalog():
        form_set = PurePosixPath(item.get('template', '')).parent.name
        selected = bool(project['form_set'] and form_set == project['form_set'])
        additional = form_set == 'Приказ Минстроя №344_пр'
        existing = registered.pop(item['code'], None)
        form = {**existing, 'fields': json.loads(existing['fields'])} if existing else {
            'code': item['code'], 'name': item['name'], 'form_group': item['group'], 'fields': catalog_fields(item)}
        result.append({**form, 'registered': bool(existing), 'form_set': form_set,
                       'guidance': guidance_for(item['code']),
                       'choice_group': 'Комплект раздела' if selected else 'Дополнительные акты Минстроя' if additional else 'Ранее подключённые формы' if existing else 'Другие комплекты форм'})
    result.extend({**r, 'fields': json.loads(r['fields']), 'registered': True,
                   'choice_group': 'Ранее подключённые формы'} for r in registered.values())
    for form in result:
        form['fields']=apply_form_defaults(form['code'],form['fields'])
        form['ui_fields'] = describe_fields(form['fields'])
    return result


def ensure_act_form(c, project_id, code):
    # Наличие регистрации означает, что индивидуальные настройки уже согласованы.
    if c.execute('SELECT 1 FROM document_types WHERE code=?', (code,)).fetchone():
        return
    if not any(f['code'] == code for f in available_forms(c, project_id)):
        raise ValueError('Выберите форму из каталога документов')
    connect_form(c, code)
