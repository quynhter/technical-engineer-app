"""Связи шаблонов с ролями и карточками, без правок рабочих данных."""
import json
import unittest
from copy import deepcopy
from pathlib import Path
from test_web_workspace import WorkspaceFixture
from itd.db import connect
from itd.acts import add_act,build_context,register_form
from itd.form_catalog import catalog,catalog_fields,ensure_act_form
from itd.form_defaults import apply_form_defaults,field_bindings
from itd.fields import validate_fields
from itd.participants import add_organization,add_signatory,assign
from itd.changes import update_record
from itd import document_versions as versions
from itd.act_participants import organization_candidates,set_organizations


class FormBindingTests(WorkspaceFixture,unittest.TestCase):
    def setUp(self):
        super().setUp();s=self.create();self.pid=s['projects'][0]['id'];self.oid=s['object']['id']
        self.ids={}
        with connect(self.path) as c:
            for role,name in [('general_contractor','Генподрядчик'),('installer','Монтажник'),('customer_control','Контроль')]:
                org=add_organization(c,full_name=name+' тестовый')
                assign(c,entity='organization',entity_id=org,object_id=self.oid,role_key=role)
                person=add_signatory(c,org_id=org,fio=name+' Представитель',position='Инженер')
                assign(c,entity='signatory',entity_id=person,object_id=self.oid,role_key=role,multiple=True)
                self.ids[role]=(org,person)

    def test_all_catalogue_fields_validate_and_every_map_key_exists(self):
        items=catalog();self.assertEqual(len(items),91)
        for item in items:
            with self.subTest(code=item['code']):
                raw=catalog_fields(item);before=deepcopy(raw)
                validate_fields(apply_form_defaults(item['code'],raw))
                self.assertEqual(raw,before)
                self.assertFalse(set(field_bindings().get(item['code'],{}))-{f['key'] for f in raw})

    def test_a2_representatives_and_repeated_signatures_follow_distinct_roles(self):
        with connect(self.path) as c:
            ensure_act_form(c,self.pid,'СП_77_А_2')
            aid=add_act(c,project_id=self.pid,act_type='СП_77_А_2')
            value=build_context(c,aid)['context']
            self.assertEqual(value['t2_r0_c1'],'Генподрядчик тестовый')
            self.assertEqual(value['t2_r4_c1'],'Монтажник тестовый')
            self.assertEqual(value['t2_r2_c1'],'Инженер Генподрядчик Представитель')
            self.assertEqual(value['t2_r6_c1'],'Инженер Монтажник Представитель')
            self.assertEqual(value['t2_r9_c0'],'Инженер Контроль Представитель')
            self.assertEqual(value['t5_r0_c1'],'Генподрядчик Представитель')
            self.assertEqual(value['t7_r0_c1'],'Контроль Представитель')
            self.assertEqual(value['t2_r15_c0'],'Сигнализация, РД-01-СПС')
            self.assertEqual(set(versions.required_roles(c,aid)),{'general_contractor','installer','customer_control'})
            # No rewriting of previously registered definitions.
            stored=json.loads(c.execute('SELECT fields FROM document_types WHERE code=?',('СП_77_А_2',)).fetchone()[0])
            self.assertEqual(next(f for f in stored if f['key']=='t2_r0_c1')['kind'],'literal')

    def test_preserve_nonempty_user_text_custom_references_and_hidden_fields(self):
        fields=[{'key':'t2_r0_c1','kind':'literal','value':'Согласованное вручную название'},
                {'key':'t2_r4_c1','kind':'reference','source':'organizations.builder.full_name'},
                {'key':'t2_r2_c1','kind':'literal','state':'hidden','value':None}]
        self.assertEqual(apply_form_defaults('СП_77_А_2',fields),fields)

    def test_alternative_role_stays_unselected_until_explicit_choice(self):
        with connect(self.path) as c:
            ensure_act_form(c,self.pid,'СП_77_А_1');aid=add_act(c,project_id=self.pid,act_type='СП_77_А_1')
            initial=build_context(c,aid)
            self.assertIn('t1_r2_c1',initial['missing'])
            fields=apply_form_defaults('СП_77_А_1',json.loads(c.execute('SELECT fields FROM document_types WHERE code=?',('СП_77_А_1',)).fetchone()[0]))
            for f in fields:
                if f.get('role_slot')=='construction_party':
                    if f['kind']=='signatory':f['role']='general_contractor'
                    else:f['source']=f['source'].replace('.construction_party.','.general_contractor.')
            update_record(c,entity='acts',record_id=aid,changes={'fields':fields})
            self.assertEqual(build_context(c,aid)['context']['t1_r2_c1'],'Инженер Генподрядчик Представитель')

    def test_organization_choice_is_role_scoped_and_rejects_other_company(self):
        with connect(self.path) as c:
            register_form(c,code='ORG_TEST',name='Акт',fields=[{'key':'org','kind':'reference','source':'organizations.general_contractor.full_name'}])
            aid=add_act(c,project_id=self.pid,act_type='ORG_TEST')
            self.assertEqual([o['id'] for o in organization_candidates(c,self.pid)['general_contractor']],[self.ids['general_contractor'][0]])
            with self.assertRaises(ValueError):set_organizations(c,self.pid,aid,{'general_contractor':self.ids['installer'][0]})
            set_organizations(c,self.pid,aid,{'general_contractor':self.ids['general_contractor'][0]})
            self.assertEqual(build_context(c,aid)['context']['org'],'Генподрядчик тестовый')

    def test_alias_fields_repeat_resolved_values_without_new_manual_input(self):
        from itd.fields import resolve_fields
        context,missing=resolve_fields([{'key':'name','kind':'reference','source':'object.name','required':True},
            {'key':'repeat','kind':'reference','source':'field_values.name','required':True}],{'object':{'name':'Название'}})
        self.assertEqual(context,{'name':'Название','repeat':'Название'});self.assertFalse(missing)

    def test_statement_signatory_uses_participant_role(self):
        with connect(self.path) as c:
            from itd.form_catalog import connect_form
            connect_form(c,'И_1_13_07_01');aid=add_act(c,project_id=self.pid,act_type='И_1_13_07_01')
            context=build_context(c,aid)['context']
            self.assertEqual(context['t1_r0_c2'],'Инженер')
            self.assertEqual(context['t1_r0_c6'],'Монтажник Представитель')

    def test_multiple_representatives_require_explicit_selection(self):
        with connect(self.path) as c:
            org,person=self.ids['general_contractor']
            other=add_signatory(c,org_id=org,fio='Другой представитель',position='Прораб')
            assign(c,entity='signatory',entity_id=other,object_id=self.oid,role_key='general_contractor',multiple=True)
            ensure_act_form(c,self.pid,'СП_77_А_2');aid=add_act(c,project_id=self.pid,act_type='СП_77_А_2')
            self.assertIn('t2_r2_c1',build_context(c,aid)['missing'])
            from itd.ojr import set_act_people
            set_act_people(c,self.pid,aid,{'general_contractor':other})
            self.assertEqual(build_context(c,aid)['context']['t2_r2_c1'],'Прораб Другой представитель')

    def test_version_cannot_mix_signer_and_organization_of_other_role(self):
        with connect(self.path) as c:
            register_form(c,code='ROLE_PAIR',name='Акт',fields=[{'key':'person','kind':'signatory','role':'installer'}])
            aid=add_act(c,project_id=self.pid,act_type='ROLE_PAIR');v=versions.ensure(c,self.pid,aid)[-1]
            payload={'act_id':aid,'id':v['id'],'revision':v['revision'],'card':{**v['card'],'organizations':{'installer':self.ids['general_contractor'][0]}},'signers':[{'role':'installer','person_id':self.ids['installer'][1],'signed':False}]}
            with self.assertRaises(ValueError):versions.save(c,self.pid,payload)
            self.assertEqual(versions.versions(c,self.pid,aid)[-1],v)

    def test_shared_act_service_rejects_signer_from_different_selected_company(self):
        with connect(self.path) as c:
            from itd.ojr import set_act_people
            register_form(c,code='PAIR_CHECK',name='Акт',fields=[])
            aid=add_act(c,project_id=self.pid,act_type='PAIR_CHECK')
            org,person=self.ids['installer']
            # Directly seeded inconsistent legacy state must not bypass the common service.
            c.execute('INSERT INTO act_organizations VALUES(?,?,?)',(aid,'installer',self.ids['general_contractor'][0]))
            with self.assertRaises(ValueError):set_act_people(c,self.pid,aid,{'installer':person})
            self.assertFalse(c.execute('SELECT 1 FROM act_signatories WHERE act_id=?',(aid,)).fetchone())
