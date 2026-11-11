"""Общий объектный контракт, совместимость карточек и самостоятельные шаблоны."""
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from docx import Document
from jinja2 import UndefinedError

from itd.docx_render import render_docx
from itd.fields import resolve_fields, validate_fields
from itd.form_catalog import catalog, catalog_fields
from itd.template_objects import (CONTEXT_KEY, build_template_context, contracts,
                                  date_object, render_context, template_schema)

ROOT = Path(__file__).resolve().parents[2]


class TemplateObjectTests(unittest.TestCase):
    def roots(self):
        org = {'full_name': 'ООО <Заказчик> & Партнёры', 'short_name': 'ООО Заказчик', 'inn': '12345'}
        person = {'position': 'Инженер', 'last_name': 'Иванов', 'first_name': 'Иван',
                  'middle_name': 'Иванович', 'fio': 'Иванов Иван Иванович',
                  'fio_short': 'Иванов И. И.', 'organization': org}
        return {'object': {'name': 'Проверочный объект', 'city': 'Москва'},
                'project': {'name': 'Автоматизация', 'code': 'ТЕСТ-АТХ'},
                'act': {'act_num': '01/АТХ', 'date_signed': '2026-11-11'},
                'organizations': {'customer': org}, 'signatories': {'recipient': person}}

    def test_recipient_has_properties_and_nested_organisation(self):
        fields = [{'key': 'recipient', 'kind': 'signatory', 'role': 'recipient',
                   'presentation': 'position_org_fio', 'required': True,
                   'template_path': 'recipient.text'}]
        roots = self.roots()
        values, missing = resolve_fields(fields, roots, draft=False)
        model = build_template_context('CUSTOM', values, roots=roots, fields=fields)
        self.assertFalse(missing)
        self.assertEqual(model['recipient']['position'], 'Инженер')
        self.assertEqual(model['recipient']['last_name'], 'Иванов')
        self.assertEqual(model['recipient']['organisation']['inn'], '12345')
        self.assertEqual(model['organisations']['customer']['role'], 'Заказчик')
        self.assertEqual(model['companies'][0]['role_key'], 'customer')
        self.assertEqual(model['document']['date']['month'], 'ноября')
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / 'author.docx'
            output = Path(directory) / 'out.docx'
            doc = Document()
            doc.add_paragraph('{{ recipient.position }} {{ recipient.organisation }} {{ recipient.last_name }}')
            doc.add_paragraph('{{ recipient.organisation.full_name }}')
            doc.add_paragraph('{%p for company in companies %}')
            doc.add_paragraph('{{ company.role }}: {{ company.name }}')
            doc.add_paragraph('{%p endfor %}')
            doc.save(template)
            render_docx(template, {**values, CONTEXT_KEY: model}, output)
            printed = '\n'.join(p.text for p in Document(output).paragraphs)
            self.assertIn('Инженер ООО Заказчик Иванов', printed)
            self.assertIn('ООО <Заказчик> & Партнёры', printed)
            self.assertIn('Заказчик: ООО Заказчик', printed)
            self.assertNotIn("{'", printed)

    def test_manual_values_are_not_replaced_by_current_database_values(self):
        values = {'object_name': 'Имя из карточки', 'recipient': 'Ручной представитель'}
        model = build_template_context('СП_77_А_21', values, roots=self.roots())
        self.assertEqual(model['object']['name'], 'Имя из карточки')
        self.assertEqual(model['recipient']['text'], 'Ручной представитель')

    def test_database_switch_does_not_reuse_person_or_company(self):
        first = build_template_context('СП_77_А_21', {}, roots=self.roots())
        other = self.roots()
        other['signatories']['recipient']['last_name'] = 'Петров'
        other['organizations']['customer']['short_name'] = 'Другой заказчик'
        second = build_template_context('СП_77_А_21', {}, roots=other)
        self.assertEqual(first['recipient']['last_name'], 'Иванов')
        self.assertEqual(second['recipient']['last_name'], 'Петров')
        self.assertEqual(first['companies'][0]['name'], 'ООО Заказчик')
        self.assertEqual(second['companies'][0]['name'], 'Другой заказчик')

    def test_custom_fields_have_explicit_paths_and_zero_is_preserved(self):
        fields = [{'key': 'pressure', 'kind': 'literal', 'value': 0,
                   'required': True, 'template_path': 'form.test.pressure'}]
        values, _ = resolve_fields(fields, {}, draft=False)
        model = build_template_context('CUSTOM', values, fields=fields)
        self.assertEqual(model['form']['test']['pressure'], 0)
        with self.assertRaises(ValueError):
            validate_fields([{**fields[0], 'template_path': 'Испытание.давление'}])

    def test_new_form_can_use_common_objects_without_declaring_every_property(self):
        model = build_template_context('NEW_CUSTOM_FORM', {}, roots=self.roots())
        self.assertEqual(model['object']['name'], 'Проверочный объект')
        self.assertEqual(model['recipient']['last_name'], 'Иванов')

    def test_registered_metadata_alias_does_not_break_shipped_contract(self):
        values = {'rows_0_18': [{'c1': 7}]}
        fields = [{'key': 'rows_0_18', 'kind': 'table', 'template_path': 'form.old_readings',
                   'fields': [{'key': 'c1', 'template_path': 'old_number'}]}]
        model = build_template_context('СП_77_А_19_УЧАСТОК', values, fields=fields)
        self.assertEqual(model['form']['fibre_measurements'][0]['fibre_number'], 7)
        self.assertEqual(model['form']['old_readings'][0]['old_number'], 7)

    def test_existing_table_records_get_named_properties_without_registration(self):
        values = {'rows_0_18': [{'c1': 1, 'c2': 0, 'c7': '11.11.2026'}]}
        model = build_template_context('СП_77_А_19_УЧАСТОК', values)
        row = model['form']['fibre_measurements'][0]
        self.assertEqual(row['fibre_number'], 1)
        self.assertEqual(row['power_ab_input'], 0)
        self.assertEqual(row['measured_on'], '11.11.2026')

    def test_91_contracts_match_definitions_and_templates_use_english_properties(self):
        items = catalog()
        self.assertEqual(len(contracts()), len(items))
        for item in items:
            with self.subTest(code=item['code']):
                for field in catalog_fields(item):
                    self.assertEqual(field['template_path'], contracts()[item['code']][field['key']]['path'])
                path = ROOT / item.get('template', 'app/templates/' + item['code'] + '.docx')
                with ZipFile(path) as z:
                    for part in z.namelist():
                        if part.startswith('word/') and part.endswith('.xml'):
                            import re
                            xml = z.read(part).decode()
                            for marker in re.findall(r'{{.*?}}|{%.*?%}', xml):
                                self.assertNotRegex(marker, r'[А-Яа-яЁё]')
                                self.assertNotIn(' set ', marker)
                                self.assertNotRegex(marker, r'\b(?:t\d+_r\d+_c\d+|p\d+_\d+|rows_\d+)')

    def test_date_and_public_schema(self):
        self.assertEqual(date_object('2026-11-11')['text'], '11.11.2026')
        self.assertEqual(date_object(None)['year'], '')
        self.assertIn('last_name', template_schema()['types']['Representative'])
        self.assertIn('materials', template_schema('СП_77_А_21')['fields'])

    def test_legacy_year_binding_does_not_repeat_month(self):
        from itd.form_defaults import apply_form_defaults
        legacy = [{'key': 't1_r0_c7', 'kind': 'reference',
                   'source': 'field_values.t1_r0_c5', 'required': True}]
        fields = apply_form_defaults('СП_72_Д', legacy)
        values, _ = resolve_fields(fields, {'act': {'date_signed': '2026-11-11'}}, draft=False)
        self.assertEqual(values['t1_r0_c7'], '2026')

    def test_unknown_property_still_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / 'custom.docx'
            output = Path(directory) / 'out.docx'
            doc = Document(); doc.add_paragraph('{{ recipient.positon }}'); doc.save(template)
            model = build_template_context('СП_77_А_21', {}, roots=self.roots())
            with self.assertRaises(UndefinedError):
                render_docx(template, {CONTEXT_KEY: model}, output)
            self.assertFalse(output.exists())

    def test_object_property_wins_over_dictionary_method(self):
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / 'custom.docx'
            output = Path(directory) / 'out.docx'
            doc = Document(); doc.add_paragraph('{{ form.items }}'); doc.save(template)
            render_docx(template, {'form': {'items': 'Проверенное значение'}}, output)
            self.assertEqual(Document(output).paragraphs[0].text, 'Проверенное значение')
