import copy
import json
import unittest
from test_web_workspace import WorkspaceFixture
from itd.db import connect
from itd.acts import register_form,add_act
from itd import document_versions as versions
from itd.configuration import export_configuration,prepare_import
from itd.workspace import snapshot,save_workspace
from itd.participants import add_signatory,assign


class DocumentVersionTests(WorkspaceFixture,unittest.TestCase):
    def test_generation_syncs_optional_people_selected_outside_version_card(self):
        from itd.ojr import set_act_people
        with connect(self.path) as c:
            versions.save(c,self.pid,self.draft(c))
            set_act_people(c,self.pid,self.aid,{'customer_control':self.person,'other_1':self.person})
            versions.prepare_generation(c,self.aid)
            current=versions.versions(c,self.pid,self.aid)[-1]
            self.assertEqual({s['role'] for s in current['signers']},{'customer_control','other_1'})
            self.assertTrue(all(not s['signed'] for s in current['signers']))

    def setUp(self):
        super().setUp();state=self.create();self.oid=state['object']['id'];self.pid=state['projects'][0]['id']
        self.person=state['participants'][0]['representatives'][0]['id'];self.org=state['participants'][0]['id']
        with connect(self.path) as c:
            register_form(c,code='VERSION_TEST',name='Акт',fields=[{'key':'works','kind':'literal','value':'Монтаж','required':True},{'key':'person','kind':'signatory','role':'customer_control','required':True}])
            self.aid=add_act(c,project_id=self.pid,act_type='VERSION_TEST')

    def payload(self):
        return super().payload()

    def draft(self,c):
        v=versions.ensure(c,self.pid,self.aid)[-1]
        return dict(act_id=self.aid,id=v['id'],revision=v['revision'],card=v['card'],work_description='Монтаж на этаже 2',signers=[dict(role='customer_control',person_id=self.person,signed=False)])

    def test_empty_role_allows_object_people_and_saves_version(self):
        from itd.participants import add_organization
        from itd.act_participants import organization_candidates
        with connect(self.path) as c:
            c.execute("DELETE FROM signatory_assignments WHERE role_key='customer_control'")
            org=add_organization(c,full_name='Другой участник',short_name='ДУ')
            c.execute("INSERT INTO object_participants(object_id,org_id,role_key) VALUES (?,?,'builder')",(self.oid,org))
            person=add_signatory(c,org_id=org,fio='Петров Пётр Петрович',position='Инженер')
            revoked=add_signatory(c,org_id=org,fio='Отозванный',position='Инженер')
            c.execute("UPDATE signatories SET status='Отозван' WHERE id=?",(revoked,))
            foreign_org=add_organization(c,full_name='Вне объекта')
            foreign=add_signatory(c,org_id=foreign_org,fio='Чужой',position='Инженер')
            choices={p['id'] for p in versions.candidates(c,self.pid)['customer_control']}
            self.assertIn(self.person,choices);self.assertIn(person,choices)
            self.assertNotIn(revoked,choices);self.assertNotIn(foreign,choices)
            self.assertIn(org,{o['id'] for o in organization_candidates(c,self.pid)['customer_control']})
            data=self.draft(c)
            data['card']['organizations']={'customer_control':org}
            data['signers'][0]['person_id']=person
            saved=versions.save(c,self.pid,data)[0]
            self.assertEqual(saved['signers'][0]['person_id'],person)
            self.assertEqual([r[0] for r in c.execute("SELECT signatory_id FROM signatory_assignments WHERE object_id=? AND role_key='customer_control'",(self.oid,))],[person])
            rep=next(r for o in snapshot(c,self.oid)['participants'] for r in o['representatives'] if r['id']==person)
            self.assertIn('customer_control',rep['document_roles'])

    def test_empty_role_assignment_is_rolled_back_on_invalid_version(self):
        with connect(self.path) as c:
            c.execute("DELETE FROM signatory_assignments WHERE role_key='customer_control'")
            data=self.draft(c)
            data['signers'][0].update(role='inspector',signed=True,signed_date='2026-11-03')
            with self.assertRaises(ValueError):versions.save(c,self.pid,data)
            self.assertFalse(c.execute("SELECT 1 FROM signatory_assignments WHERE role_key='inspector'").fetchone())

    def test_shared_act_service_remembers_empty_role(self):
        from itd.ojr import set_act_people
        with connect(self.path) as c:
            set_act_people(c,self.pid,self.aid,{'inspector':self.person})
            rep=next(r for o in snapshot(c,self.oid)['participants'] for r in o['representatives'] if r['id']==self.person)
            self.assertIn('inspector',rep['document_roles'])
            self.assertIn('customer_control',rep['document_roles'])

    def test_existing_role_does_not_expand_to_unassigned_people(self):
        with connect(self.path) as c:
            other=add_signatory(c,org_id=self.org,fio='Без назначения',position='Инженер')
            self.assertNotIn(other,{p['id'] for p in versions.candidates(c,self.pid)['customer_control']})
            with self.assertRaises(ValueError):versions.validate_signer(c,self.pid,other,'customer_control')

    def test_participant_role_works_without_roster_and_each_signature_has_date(self):
        with connect(self.path) as c:
            self.assertEqual(versions.candidates(c,self.pid)['customer_control'][0]['id'],self.person)
            data=self.draft(c);data['signers'][0].update(signed=True,signed_date=None)
            with self.assertRaises(ValueError):versions.save(c,self.pid,data)
            data['signers'][0]['signed_date']='2026-11-03'
            saved=versions.save(c,self.pid,data)[0]
            self.assertTrue(saved['signers'][0]['signed'])
            self.assertEqual(c.execute('SELECT state FROM act_execution_status').fetchone()[0],'signed')

    def test_version_two_keeps_version_one_signers_and_rejects_historical_edits(self):
        with connect(self.path) as c:
            saved=versions.save(c,self.pid,self.draft(c))[0]
            old=copy.deepcopy(saved)
            created=versions.create(c,self.pid,self.aid,{'id':saved['id'],'revision':saved['revision']})
            data=self.draft(c);data['signers']=[];versions.save(c,self.pid,data)
            result=versions.versions(c,self.pid,self.aid)
            self.assertEqual(result[0],old);self.assertEqual(result[1]['signers'],[])
            with self.assertRaises(ValueError):versions.save(c,self.pid,dict(act_id=self.aid,id=old['id'],revision=old['revision'],card=old['card']))

    def test_different_counts_and_multiple_people_of_one_role(self):
        with connect(self.path) as c:
            other=add_signatory(c,org_id=self.org,fio='Петров Пётр Петрович',position='Инженер')
            assign(c,entity='signatory',entity_id=other,object_id=self.oid,role_key='customer_control',multiple=True)
            data=self.draft(c);data['signers'].append(dict(role='customer_control',person_id=other,signed=False))
            result=versions.save(c,self.pid,data)[-1]
            self.assertEqual(len(result['signers']),2)
            self.assertEqual({s['person_id'] for s in result['signers']},{other,self.person})

    def test_missing_required_role_cannot_mark_whole_version_signed(self):
        with connect(self.path) as c:
            data=self.draft(c);data['signers'][0].update(role='builder',signed=True,signed_date='2026-11-03')
            with self.assertRaises(ValueError):versions.save(c,self.pid,data)
            self.assertIsNone(c.execute('SELECT * FROM act_execution_status').fetchone())

    def test_contractor_can_sign_as_general_contractor_without_optional_signature(self):
        from itd.act_participants import organization_candidates
        from itd.acts import build_context

        with connect(self.path) as c:
            c.execute("INSERT INTO object_participants(object_id,org_id,role_key) VALUES (?,?,'builder')",
                      (self.oid, self.org))
            assign(c, entity='signatory', entity_id=self.person, object_id=self.oid, role_key='builder')
            register_form(c, code='VERSION_TEST', name='Акт испытаний', fields=[
                {'key': 'company', 'kind': 'reference', 'source': 'organizations.general_contractor.full_name'},
                {'key': 'contractor', 'kind': 'signatory', 'role': 'general_contractor', 'required': True},
                {'key': 'control', 'kind': 'signatory', 'role': 'customer_control'},
            ])
            self.assertEqual(organization_candidates(c, self.pid)['general_contractor'][0]['id'], self.org)
            self.assertEqual(versions.candidates(c, self.pid)['general_contractor'][0]['id'], self.person)
            data = self.draft(c)
            data['work_description'] = None
            data['signers'].append(dict(role='general_contractor', person_id=self.person, signed=True,
                                        signed_date='2026-11-03'))
            versions.save(c, self.pid, data)
            status = c.execute('SELECT state, signers_json FROM act_execution_status').fetchone()
            self.assertEqual(status['state'], 'signed')
            self.assertEqual(set(json.loads(status['signers_json'])), {'general_contractor'})
            self.assertEqual(build_context(c, self.aid)['context']['company'], 'Застройщик')

    def test_stale_revision_and_other_project_cannot_update_version(self):
        with connect(self.path) as c:
            data=self.draft(c);versions.save(c,self.pid,data)
            with self.assertRaises(ValueError):versions.save(c,self.pid,data)
            with self.assertRaises(ValueError):versions.versions(c,999,self.aid)

    def test_roundtrip_scopes_do_not_include_other_blocks_and_preview_never_writes(self):
        with connect(self.path) as c:
            before=snapshot(c,self.oid)
            for scope in ('object','rd','participants','permits'):
                exported=export_configuration(c,self.oid,scope)
                self.assertEqual(prepare_import(c,self.oid,scope,exported)['changes'],[])
            exported=export_configuration(c,self.oid,'rd')
            self.assertEqual(set(exported['data']),{'projects'})
            exported['data']['projects'][0]['name']='Изменённый раздел'
            preview=prepare_import(c,self.oid,'rd',exported)
            self.assertEqual(len(preview['changes']),1)
            self.assertEqual(snapshot(c,self.oid),before)
            saved=save_workspace(c,preview['state'])
            self.assertEqual(saved['participants'],before['participants'])
            self.assertEqual(saved['object'],before['object'])
            self.assertEqual(saved['projects'][0]['name'],'Изменённый раздел')

    def test_object_configuration_includes_permits_and_accepts_legacy_files(self):
        with connect(self.path) as c:
            original=snapshot(c,self.oid)
            exported=export_configuration(c,self.oid,'object')
            self.assertIn('permit_num',exported['data']['object'])
            self.assertIn('expertise_date',exported['data']['object'])
            legacy=export_configuration(c,self.oid,'permits')
            legacy['data']['object'].update(permit_num='РС-123',expertise_date='2026-11-01')
            preview=prepare_import(c,self.oid,'object',legacy)
            self.assertEqual(preview['state']['object']['permit_num'],'РС-123')
            self.assertEqual(preview['state']['object']['name'],original['object']['name'])
            self.assertEqual(snapshot(c,self.oid),original)
            # Прежний экспорт объекта без разрешений оставляет их без изменений.
            old_object=export_configuration(c,self.oid,'object')
            for key in legacy['data']['object']:old_object['data']['object'].pop(key)
            self.assertEqual(prepare_import(c,self.oid,'object',old_object)['changes'],[])
            legacy['data']['object']['name']='Недопустимое поле старой вкладки'
            with self.assertRaises(ValueError):prepare_import(c,self.oid,'object',legacy)

    def test_import_rejects_foreign_scope_object_and_unexpected_fields(self):
        with connect(self.path) as c:
            exported=export_configuration(c,self.oid,'rd')
            with self.assertRaises(ValueError):prepare_import(c,self.oid,'object',exported)
            exported['object_id']=999
            with self.assertRaises(ValueError):prepare_import(c,self.oid,'rd',exported)
            exported['object_id']=self.oid;exported['data']['projects'][0]['agent_context']='{}'
            with self.assertRaises(ValueError):prepare_import(c,self.oid,'rd',exported)

    def test_generated_file_and_card_versions_remain_independent(self):
        from docx import Document
        from itd.acts import generate
        with connect(self.path) as c:
            template=self.path.parent/'templates';template.mkdir()
            doc=Document();doc.add_paragraph('{{ works }}');doc.save(template/'VERSION_TEST.docx')
            first=generate(c,act_id=self.aid,templates_dir=template,output=self.path.parent/'first.docx')
            first_version=versions.versions(c,self.pid,self.aid)[-1]
            second=generate(c,act_id=self.aid,templates_dir=template,output=self.path.parent/'second.docx')
            result=versions.versions(c,self.pid,self.aid)
            self.assertEqual(len(result),2)
            self.assertEqual(result[0],first_version)
            self.assertEqual(result[0]['release_id'],first['release_id'])
            self.assertEqual(result[1]['release_id'],second['release_id'])

    def test_upload_registers_original_and_links_it_to_act_and_version(self):
        import base64
        from types import SimpleNamespace
        from itd.web import Handler,project_data
        from itd.archive import archived_path,digest
        handler=object.__new__(Handler);handler.server=SimpleNamespace(database=self.path)
        original=b'%PDF-1.4\nUI test original'
        with connect(self.path) as c:
            uploaded=handler.mutate(c,'/api/upload',dict(project_id=self.pid,name='Подписанный акт.pdf',content=base64.b64encode(original).decode(),doc_type='other'))
            result=handler.mutate(c,'/api/act',dict(project_id=self.pid,act_type='VERSION_TEST',attachment_id=uploaded['id'],fields=[]))
            value=versions.versions(c,self.pid,result['act_id'])[0]
            self.assertEqual(value['attachment_id'],uploaded['id'])
            self.assertEqual(project_data(c,self.pid)['act_originals'][0]['original_name'],'Подписанный акт.pdf')
            self.assertEqual(c.execute('SELECT count(*) FROM act_attachments WHERE act_id=?',(result['act_id'],)).fetchone()[0],1)
            # The uploaded file does not assert that anyone signed it.
            self.assertEqual(value['signers'],[])

    def test_existing_release_history_uses_its_recorded_context(self):
        from docx import Document
        from itd.acts import generate
        with connect(self.path) as c:
            template=self.path.parent/'templates';template.mkdir()
            doc=Document();doc.add_paragraph('{{ works }}');doc.save(template/'VERSION_TEST.docx')
            first=generate(c,act_id=self.aid,templates_dir=template,output=self.path.parent/'first.docx')
            second=generate(c,act_id=self.aid,templates_dir=template,output=self.path.parent/'second.docx')
            c.execute('DELETE FROM document_versions WHERE act_id=?',(self.aid,))
            result=versions.ensure(c,self.pid,self.aid)
            self.assertEqual([v['release_id'] for v in result],[first['release_id'],second['release_id'],None])
            self.assertEqual(result[0]['snapshot']['works'],'Монтаж')
            self.assertEqual(result[0]['signers'],[])
