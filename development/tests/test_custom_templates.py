import base64
import io
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from docx import Document

from itd.acts import add_act
from itd.db import initialize, connect, add_object, add_project
from itd.resources import add_resource
from itd.services.context import ServiceContext
from itd.services.documents import mutate
from itd.releases import build_project_zip


class TemplateWorkflowTests(unittest.TestCase):
    def test_select_records_when_preparing_a_document(self):
        from itd.acts import build_context
        from itd.custom_templates import list_templates
        from itd.participants import add_organization, add_signatory

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            database = root / 'test.db'
            initialize(database)
            ctx = ServiceContext(database=database, templates=root)
            document = Document()
            document.add_paragraph('{{ company }}')
            table = document.add_table(rows=1, cols=2)
            table.cell(0, 0).text = '{{ serial_number }}'
            table.cell(0, 1).text = '{{ contacts.representative }}'
            buffer = io.BytesIO()
            document.save(buffer)
            content = base64.b64encode(buffer.getvalue()).decode()

            with connect(database) as c:
                oid = add_object(c, 'Тестовый объект')
                pid = add_project(c, object_id=oid, name='Раздел', section_code='1', code='РД')

                def call(op, **data):
                    return mutate(c, '/api/' + op, {'project_id': pid, **data}, ctx)

                inspected = call('templates/inspect', content=content)
                self.assertIn({'key': 'short_fio', 'label': 'Инициалы', 'type': 'text'},
                              inspected['schema']['signatories']['columns'])
                company, contacts = inspected['fields']
                company['value'] = '{{ $db.organizations.full_name }}, ИНН: {{ $db.organizations.inn }}'
                contacts.pop('source')
                contacts['value'] = [{'representative': '{{ $db.signatories.short_fio }}'}]
                code = call('templates/save', content=content, original_name='Акт.docx', name='Акт',
                            form_set='СП', fields=[company, contacts])['code']
                org = add_organization(c, full_name='Строймонтаж', inn='7700000001')
                foreign = add_organization(c, full_name='Другой объект')
                c.execute('INSERT INTO object_participants(object_id,org_id,role_key) VALUES (?,?,?)',
                          (oid, org, 'contractor'))
                rep = add_signatory(c, org_id=org, fio='Иванов Иван Иванович', position='Инженер')
                aid = call('act', act_type=code)['act_id']
                pending = build_context(c, aid)
                self.assertEqual(pending['missing'], ['company', 'contacts[1].representative'])
                self.assertEqual(pending['context']['company'], '[УТОЧНИТЬ], ИНН: [УТОЧНИТЬ]')
                self.assertEqual(pending['field_diagnostics'][0]['record_tables'], ['organizations'])
                with self.assertRaisesRegex(ValueError, r'contacts\[1\]\.representative'):
                    build_context(c, aid, draft=False)

                version = call('versions/ensure', act_id=aid)['versions'][-1]
                company_value = company['value'].replace('organizations.', f'organizations.r{org}.')
                contacts_value = [{'representative': f'{{{{ $db.signatories.r{rep}.short_fio }}}}'}]
                version['card']['fields'] = [
                    {**company, 'value': company_value.replace(f'r{org}.', f'r{foreign}.')},
                    {**contacts, 'value': contacts_value},
                ]
                version = call('versions/save', act_id=aid, id=version['id'],
                               revision=version['revision'], card=version['card'])['versions'][-1]
                self.assertEqual(build_context(c, aid)['missing'], ['company'])

                version['card']['fields'][0]['value'] = company_value
                call('versions/save', act_id=aid, id=version['id'], revision=version['revision'],
                     card=version['card'])
                self.assertEqual(build_context(c, aid, draft=False)['missing'], [])
                out = Document(call('generate', act_id=aid)['output'])
                self.assertEqual(out.paragraphs[0].text, 'Строймонтаж, ИНН: 7700000001')
                self.assertEqual(out.tables[0].cell(0, 1).text, 'Иванов И. И.')
                self.assertEqual(list_templates(c)[0]['fields'], [company, contacts])

    def test_template_storage_and_project_zip(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            database = root/'test.db'
            initialize(database)
            ctx = ServiceContext(database=database,templates=root)
            document = Document()
            document.add_paragraph('{{ object.name }}')
            document.add_paragraph('Комментарий: {{ comment }}')
            table = document.add_table(rows=1,cols=2)
            table.cell(0,0).text = '{{ serial_number }}'
            table.cell(0,1).text = '{{ resources.qty_proj }}'
            buffer = io.BytesIO()
            document.save(buffer)
            content = base64.b64encode(buffer.getvalue()).decode()
            with connect(database) as c:
                oid = add_object(c,'Капремонт')
                pid = add_project(c,object_id=oid,name='Раздел',section_code='1',code='РД')
                def call(op, **data):
                    return mutate(c,'/api/'+op,{'project_id':pid,**data},ctx)
                for qty in (0,1.5):
                    add_resource(c,project_id=pid,name='Кабель',category='Кабельная продукция',unit='м',qty_proj=qty)
                fields = call('templates/inspect',content=content)['fields']
                fields[0]['value'] = '{{ $db.objects.name }} (объект)'
                fields[2]['db_table'] = 'resources'
                fields[2]['fields'][1]['mask'] = '0.00'
                code = call('templates/save',content=content,original_name='Акт.docx',name='Акт',fields=fields,form_set='СП')['code']
                aid = add_act(c,project_id=pid,act_type=code)
                result = call('generate',act_id=aid)
                out = Document(result['output'])
                self.assertEqual(out.paragraphs[0].text,'Капремонт (объект)')
                self.assertEqual(out.paragraphs[1].text,'Комментарий: ')
                self.assertEqual([[c.text for c in r.cells] for r in out.tables[0].rows],[['1','0.00'],['2','1.50']])
                row = c.execute('SELECT * FROM files WHERE act_id=?',(aid,)).fetchone()
                self.assertEqual(Path(result['output']),root/'storage'/row['id'])
                self.assertEqual(row['name'],'Акт.docx')
                sid = call('scheme-save',action='scheme-add',data={'num':'1','name':'Схема'},
                           file={'name':'ИС.dwg','content':base64.b64encode(b'drawing').decode()})['id']
                call('scheme-save',action='update',data={'entity':'schemes','id':sid,'expected':{'num':'1'},'changes':{'num':'2'}})
                build_project_zip(c,pid,root/'files.zip')
                with ZipFile(root/'files.zip') as archive:
                    self.assertEqual(archive.read('Капремонт/Схемы/ИС.dwg'),b'drawing')
                    self.assertEqual(archive.read('Капремонт/Акт.docx'),Path(result['output']).read_bytes())

    def test_plain_row_split_serial_and_selected_record(self):
        from itd.custom_templates import inspect_doc
        from itd.fields import resolve_fields
        from itd.docx_render import render_docx
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            doc = Document()
            doc.add_paragraph('{{serial_number}}')
            row = doc.add_table(rows=1,cols=2).rows[0]
            p = row.cells[0].paragraphs[0]
            p.add_run('{{serial_')
            p.add_run('number}}')
            row.cells[1].text = '{{amount}}'
            doc.add_paragraph('{{chosen}}')
            custom = doc.add_table(rows=1,cols=2)
            custom.cell(0,1).text = '{{measurements.unit}}'
            single = doc.add_table(rows=1,cols=1)
            single.cell(0,0).text = '{{note}} / {{note}}'
            custom.cell(0,0).text = '{{measurements.length}}'
            src = root/'TPL_sample.docx'
            doc.save(src)
            fields = inspect_doc(src.read_bytes())
            self.assertEqual([f['key'] for f in fields], ['table_1', 'chosen', 'measurements', 'note'])
            table, chosen, measurements, note = fields
            self.assertEqual(note['kind'],'literal')
            note['value']='Текст'
            measurements.pop('source')
            measurements['value'] = [{'length':4},{'length':7}]
            table.pop('source')
            table['value'] = [{'amount':'5,2'},{'amount':'0'}]
            table['fields'][1].update(value_type='number', mask='0.00')
            chosen.update(value='{{ $db.resources.r22.quantity }}',mask='0.000')
            records = {'resources': {'r9':{'quantity':2}, 'r22':{'quantity':3.5}}}
            context, _ = resolve_fields(fields, {'records':records})
            result = Document(render_docx(src, context, root/'result.docx'))
            self.assertEqual(result.tables[2].cell(0,0).text,'Текст / Текст')
            self.assertEqual([r.cells[0].text for r in result.tables[1].rows], ['4','7'])
            self.assertEqual([p.text for p in result.paragraphs], ['1','3.500'])
            self.assertEqual([[c.text for c in r.cells] for r in result.tables[0].rows],
                             [['1','5.20'],['2','0.00']])

    def test_single_dotted_cell_and_previous_table_definition(self):
        from itd.custom_templates import inspect_doc
        from itd.docx_render import render_docx
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            doc = Document()
            doc.add_table(rows=1, cols=1).cell(0,0).text = '{{measurements.length}}'
            src = root/'TPL_single.docx'
            doc.save(src)
            field, = inspect_doc(src.read_bytes())
            self.assertEqual((field['kind'], field['marker_path']), ('literal', 'measurements.length'))
            for label, value, expected in [('scalar', {'length':5}, ['5']),
                                           ('legacy', [{'length':4},{'length':7}], ['4','7'])]:
                output = render_docx(src, {'measurements':value}, root/(label+'.docx'))
                self.assertEqual([row.cells[0].text for row in Document(output).tables[0].rows], expected)

    def test_one_marker_column_is_layout_even_with_several_fields(self):
        from itd.custom_templates import inspect_doc
        doc = Document()
        layout = doc.add_table(rows=2, cols=2)
        layout.cell(0,0).text = 'Объект'
        layout.cell(0,1).text = '{{info.name}} {{info.address}}'
        layout.cell(1,1).text = '{{info.city}}'
        single = doc.add_table(rows=2, cols=1)
        single.cell(0,0).text = '{{ object }}'
        single.cell(1,0).text = '{{ location }}'
        buf = io.BytesIO()
        doc.save(buf)
        fields = inspect_doc(buf.getvalue())
        self.assertEqual([f.get('marker_path', f['key']) for f in fields],
                         ['info.name','info.address','info.city','object','location'])
        self.assertTrue(all(f['kind']=='literal' for f in fields))

    def test_edit_download_delete_and_rollback(self):
        from itd.custom_templates import list_templates, template_operation
        from itd.fields import resolve_fields
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db = root/'test.db'
            initialize(db)
            doc = Document()
            doc.add_paragraph('{{ value }}')
            buf = io.BytesIO()
            doc.save(buf)
            payload = {'name':'Форма','original_name':'Форма.docx','form_set':'СП',
                       'content':base64.b64encode(buf.getvalue()).decode(),
                       'fields':[{'key':'value','kind':'literal','mask':'«dd» mmmm yyyy',
                                  'value':'{{ $db.objects.name }}, {{ $db.objects.work_start }}'}]}
            with connect(db) as c:
                code = template_operation(c,'save',payload,root)['code']
                text,_ = resolve_fields(payload['fields'],{'object':{'name':'Корпус','work_start':'2026-11-08'}})
                self.assertEqual(text['value'],'Корпус, «08» ноября 2026')
            with connect(db) as c:
                item = list_templates(c)[0]
                template_operation(c,'save',{**item,'name':'Изменённое название'},root)
                with self.assertRaisesRegex(ValueError,'уже изменён'):
                    template_operation(c,'delete',item,root)
                item = list_templates(c)[0]
                download = template_operation(c,'download',item,root)
                self.assertEqual(download['content'],payload['content'])
            with self.assertRaisesRegex(RuntimeError,'откат'), connect(db) as c:
                template_operation(c,'delete',item,root)
                raise RuntimeError('откат')
            self.assertEqual((root/(code+'.docx')).read_bytes(),buf.getvalue())
            with connect(db) as c:
                template_operation(c,'delete',item,root)
                self.assertEqual(list_templates(c),[])
            self.assertFalse((root/(code+'.docx')).exists())

    def test_journal_exports_use_current_records(self):
        from itd.journal_export import export
        from itd.paths import default_templates
        from itd.workspace import save_entry
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db = root/'journal.db'
            initialize(db)
            with connect(db) as c:
                oid = add_object(c, 'Проверочный объект')
                pid = add_project(c, object_id=oid, section_code='ЭОМ', code='РД', name='Проект')
                save_entry(c, pid, {'kind':'work','work_type':'cable','entry_date':'2026-11-08',
                                    'title':'Прокладка','work_fields':{'line_number':'КЛ-01'}})
                save_entry(c, pid, {'kind':'incoming','entry_date':'2026-11-10','title':'Партия',
                                    'work_fields':{'incoming_result':'accepted'}})
            with connect(db) as c:
                c.execute('PRAGMA query_only=ON')
                for kind, expected in [('ojr','Проверочный объект'),('incoming','Партия'),('cable','КЛ-01')]:
                    output = root/(kind+'.docx')
                    export(c,pid,kind,default_templates(),output)
                    with ZipFile(output) as package:
                        self.assertIn(expected,package.read('word/document.xml').decode())
