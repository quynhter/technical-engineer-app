"""Подписи веб-предпросмотра; не меняют поля формы и печатный контекст."""
import json
import re

from .fields import merge_fields
from .field_ui import human_label
from .form_defaults import apply_form_defaults


def preview_fields(connection, act_id):
    act = connection.execute('SELECT act_type,fields FROM acts WHERE id=?', (act_id,)).fetchone()
    form = connection.execute('SELECT name,fields FROM document_types WHERE code=?', (act['act_type'],)).fetchone()
    defaults = json.loads(form['fields'])
    labels = {f['key']: f for f in defaults}

    def describe(field, index):
        base = labels.get(field['key'], {})
        label = human_label({**base, **field}, index)
        source = field.get('source') or base.get('source', '')
        if field['kind'] == 'table':
            group = 'Таблицы и перечни'
        elif source.startswith('act.') or field.get('value_type') == 'date' or field.get('format'):
            group = 'Номер и даты'
        elif field['kind'] == 'signatory' or source.startswith(('signatories.', 'organizations.')) or re.search(r'Ф\.?И\.?О|подпис|представител', label, re.I):
            group = 'Участники и подписанты'
        elif source.startswith(('object.', 'project.', 'unit.', 'section_designer.', 'project_documentation.')):
            group = 'Объект и раздел'
        else:
            group = 'Содержание акта'
        return {'key': field['key'], 'label': label, 'group': group,
                'kind': field['kind'], 'required': field.get('required', False),
                'format': field.get('format'),
                'state': field.get('state'), 'reason': field.get('reason'),
                'columns': [describe(col, i) for i, col in enumerate(field.get('fields', []))]}

    fields = apply_form_defaults(act['act_type'], merge_fields(defaults, json.loads(act['fields'])))
    return form['name'], [describe(f, i) for i, f in enumerate(fields)]
