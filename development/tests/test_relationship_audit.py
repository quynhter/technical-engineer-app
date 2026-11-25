"""Аудит должен ловить оборванные связи даже в пустых таблицах DOCX."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

from docx import Document
from itd.fields import resolve_fields
from itd.form_catalog import catalog, catalog_fields
from itd.form_defaults import apply_form_defaults

ROOT = Path(__file__).resolve().parents[2]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


audit = module('relationship_audit', 'development/scripts/audit_relationships.py')


class RelationshipAuditTests(unittest.TestCase):
    def test_named_fields_resolve_to_legacy_keys_and_table_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'named.docx'
            document = Document()
            for text in ('{%p set Объект = t0_r7_c1 %}', '{{ Объект }}',
                         '{%p set Измерения = rows_0_18 %}', '{% for item in Измерения %}',
                         '{% set Номер_ОВ = item.c1 %}{{ Номер_ОВ }}', '{% endfor %}'):
                document.add_paragraph(text)
            document.save(path)
            refs, locations = audit.template_contract(path)
            self.assertEqual(set(refs), {'t0_r7_c1', 'rows_0_18', 'rows_0_18.c1'})
            self.assertTrue(locations['rows_0_18.c1'])

    def test_ast_resolves_reused_loop_variables_and_conditional_branches(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'loops.docx'
            document = Document()
            for text in ('{% for item in first %}', '{{ item.valid }}', '{% endfor %}',
                         '{% for item in second %}', '{% if enabled %}',
                         '{{ item.typo }}', '{% endif %}', '{% endfor %}'):
                document.add_paragraph(text)
            document.sections[0].header.paragraphs[0].text = '{{ header_value }}'
            document.save(path)
            refs, locations = audit.template_contract(path)
            self.assertEqual(set(refs), {'first', 'first.valid', 'second', 'second.typo', 'enabled', 'header_value'})
            self.assertTrue(any(p.startswith('word/header') for p in refs['header_value']))
            self.assertEqual(len(locations['first.valid']), 1)
            self.assertEqual(len(locations['second.typo']), 1)
            self.assertNotEqual(locations['first.valid'], locations['second.typo'])

    def test_optional_reference_to_nonexistent_column_is_an_error(self):
        schemas = {'resources': {'columns': [{'name': 'name'}]}}
        with self.assertRaisesRegex(ValueError, 'Несуществующая колонка'):
            audit.source_columns('item.nonexistent', schemas, 'resources')
        self.assertEqual(audit.source_columns('item.name', schemas, 'resources')[0], ['resources.name'])

    def test_unprinted_fields_require_an_explicit_exception(self):
        with self.assertRaisesRegex(ValueError, 'не используется'):
            audit.unprinted_reason('СП_70_А', 'rows_9_2.c3', {'label': 'Дата подписания акта'})
        with self.assertRaises(ValueError):
            audit.unprinted_reason('TEST', 'missing', {'label': 'Наименование'})
        self.assertIn('Рукописная', audit.unprinted_reason('TEST', 'rows.c3', {'label': 'Подпись'}))
        self.assertIn('реестра', audit.unprinted_reason('РЕЕСТР_ИТД', 'registry.date', {}))
