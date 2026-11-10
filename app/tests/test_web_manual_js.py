"""Проверка маршрутизации реального обработчика формы при DOM name-clobbering."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest


class WebManualJsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Нужен Node')
    def test_representative_caption_and_empty_role_choices(self):
        assets=Path(__file__).parents[1]/'itd/web_assets'
        ui=(assets/'ui.js').read_text()
        roles=(assets/'ojr-ui.js').read_text()
        functions=ui[ui.index('function representativeLabel('):ui.index('function cleanFieldLabel(')]
        functions+=roles[roles.index('function actRoleCandidates('):]
        script=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
const p={id:1,org_id:2,position:'Инженер',fio:'Иванов И.И.',last_name:'Иванов',first_name:'Иван',middle_name:'Иванович',status:'Действует'};
const org={id:2,short_name:'ООО Тест',full_name:'Полное название'};
const ctx={pdata:{journals:{directory:{organizations:[org],people:[p,{id:3,status:'Отозван'}]}},participant_choices:{people:{builder:[p]}}}};
vm.runInNewContext(SOURCE,ctx);
assert.equal(ctx.representativeLabel(p),'Инженер ООО Тест Иванов Иван Иванович');
assert.deepEqual(Array.from(ctx.actRoleCandidates('inspector'),p=>p.id),[1]);
assert.deepEqual(Array.from(ctx.actRoleCandidates('builder'),p=>p.id),[1]);
assert.equal(ctx.representativeLabel({position:'Мастер',fio:'Петров Пётр',organization:{full_name:'Организация'}}),'Мастер Организация Петров Пётр');
""".replace('SOURCE',json.dumps(functions))
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Нужен Node')
    def test_findings_resolve_resource_names_and_link_exact_card(self):
        source=(Path(__file__).parents[1]/'itd/web_assets/app.js').read_text()
        functions=source[source.index('function resourceLabel('):source.index('function findingDestination(')]
        script=r"""
const assert=require('node:assert/strict');
const pdata={resources:[{id:7,spec_num:'12',name:'Кабель <А>',type_mark:'КПС'}],acts:[],attachments:[],releases:[],workspace_entries:[],quality_reviews:[],manual:{supplies:[]},workflow:{fact_records:[{id:21,resource_id:7,work_description:'Прокладка',location:'Этаж 2'}],matrix:{requirements:[]},deliveries:[],remarks:[]}};
const esc=v=>String(v).replaceAll('<','&lt;').replaceAll('>','&gt;'),actName=()=>'';
FUNCTIONS
const details=findingDetails({code:'qty_fact_unknown',resource_id:7,fact_id:21});
assert.match(details,/Поз\. 12\. Кабель <А>\. КПС/);assert.match(details,/Этаж 2/);
assert.doesNotMatch(details,/Ресурс №|Факт №/);
const link=findingSubjectLink({fact_id:21});
assert.match(link,/data-resource-card="7"/);assert.match(link,/Кабель &lt;А&gt;/);
assert.match(resourceLabel(999),/недоступен/);
""".replace('FUNCTIONS',functions)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Нужен Node')
    def test_middle_text_split_preserves_full_unicode_value(self):
        source=(Path(__file__).parents[1]/'itd/web_assets/ui.js').read_text()
        function=source[source.index('function fitMiddleText('):source.index('let middleCanvas;')]
        script=function+r"""
const assert=require('node:assert/strict');
const measure=text=>Array.from(text).length;
for(const text of ['', 'РД', 'Имя🙂'])assert.equal(fitMiddleText(text,30,measure),text);
const original='Очень длинное наименование рабочей документации — корпус 2, редакция 17.pdf';
const shortened=fitMiddleText(original,45,measure);
assert.match(shortened,/\.\.\./);assert.ok(shortened.endsWith('редакция 17.pdf'));
assert.ok(Array.from(shortened).length<=45);assert.ok(original.startsWith(shortened.split('...')[0]));
const unicode=fitMiddleText('🙂'.repeat(60),20,measure);assert.equal(Array.from(unicode).length,20);
assert.ok(!/[\uD800-\uDBFF]$/.test(unicode.split('...')[0]));

"""
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Нужен Node для проверки даты выпуска')
    def test_release_timestamp_uses_browser_timezone_and_padded_format(self):
        import os
        source=(Path(__file__).parents[1]/'itd/web_assets/app.js').read_text()
        formatter=source[source.index('function formatDateTime('):source.index('const iconPaths')]
        script=formatter+"""
const assert=require('node:assert/strict');
assert.equal(formatDateTime('2026-10-31T10:19:27.896Z'),'31.10.2026 13:19');
assert.equal(formatDateTime('2026-12-31T23:05:00Z'),'01.01.2027 02:05');
assert.equal(formatDateTime(null),'Дата не указана');
assert.equal(formatDateTime('invalid'),'Дата не распознана');
"""
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,
                              env={**os.environ,'TZ':'Europe/Moscow'})
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Нужен Node для проверки браузерного обработчика')
    def test_named_id_control_does_not_hide_manual_form_identity(self):
        source=(Path(__file__).parents[1]/'itd/web_assets/app.js').read_text()
        handler=next(line for line in source.splitlines() if line.startswith("document.addEventListener('submit',"))
        script=r'''
const vm=require('node:vm');
let handler, routed=false, pending;
const ctx={
 document:{addEventListener:(kind,fn)=>{handler=fn;}},
 currentUser:{role:'editor'},
 FormData:class {},
 validateInputs:()=>true,
 action:fn=>{pending=fn();},
 submitManual:async form=>{routed=true;}
};
vm.runInNewContext(SOURCE,ctx);
// HTMLFormElement.id может возвращать контрол с name="id" вместо строки.
handler({preventDefault(){},target:{id:{name:'id'},closest:()=>null,getAttribute:key=>key==='id'?'manual-form':null}});
Promise.resolve(pending).then(()=>{if(!routed)throw Error('Ручная форма не направлена в общий сервис');});
'''.replace('SOURCE',json.dumps(handler))
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Нужен Node для проверки подсказки')
    def test_agent_help_closes_outside_even_when_option_stops_bubbling(self):
        source=(Path(__file__).parents[1]/'itd/web_assets/ui.js').read_text()
        script=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const listeners={},help={open:true};
const ctx={ResizeObserver:class{observe(){} unobserve(){}},MutationObserver:class{observe(){} disconnect(){}},document:{
 getElementById:()=>null,
 addEventListener:(type,fn,capture)=>{(listeners[type]??=[]).push({fn,capture});},
 querySelectorAll:()=>[help].filter(x=>x.open)
}};
vm.runInNewContext(SOURCE,ctx);
const click=listeners.click.find(x=>x.capture===true);
assert.ok(click,'Обработчик должен видеть клик до stopPropagation пункта списка');
click.fn({target:{closest:()=>help}});assert.equal(help.open,true);
click.fn({target:{closest:()=>null}});assert.equal(help.open,false);
help.open=true;
listeners.change.find(x=>x.capture===true).fn({target:{matches:()=>true}});
assert.equal(help.open,false);
help.open=true;
listeners.keydown.forEach(x=>x.fn({key:'Escape'}));assert.equal(help.open,false);
'''.replace('SOURCE',json.dumps(source))
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


class JournalJsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Нужен Node')
    def test_live_refresh_preserves_input_and_rejects_stale_responses(self):
        source=(Path(__file__).parents[1]/'itd/web_assets/journals.js').read_text()
        start=source.index('async function refreshJournals()')
        refresh=source[start:source.index("document.addEventListener('click'", start)]
        script=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
let requests=0,renders=0,resolve;
const ctx={journalRefreshBusy:false,busy:false,dirty:false,formDirty:false,projectId:1,
 workspaceView:'journal',document:{hidden:false},$:()=>({open:false}),pdata:{version:1},selectedEntries:new Set(),
 api:async()=>{requests++;return {version:2,workspace_entries:[]};},render:()=>renders++};
vm.runInNewContext(SOURCE,ctx);
(async()=>{
 ctx.formDirty=true;await ctx.refreshJournals();assert.equal(requests,0);
 ctx.formDirty=false;ctx.dirty=true;await ctx.refreshJournals();assert.equal(requests,0);
 ctx.workspaceView='cable';
 ctx.dirty=false;await ctx.refreshJournals();assert.equal(renders,1);assert.equal(ctx.pdata.version,2);
 await ctx.refreshJournals();assert.equal(renders,1,'Не перерисовывать неизменённые данные');
 ctx.api=()=>new Promise(r=>resolve=r);
 const pending=ctx.refreshJournals();ctx.formDirty=true;resolve({version:3});await pending;
 assert.equal(ctx.pdata.version,2,'Ввод, начатый во время запроса, сохраняется');
 ctx.formDirty=false;const switched=ctx.refreshJournals();ctx.projectId=2;resolve({version:4});await switched;
 assert.equal(ctx.pdata.version,2,'Ответ прежнего раздела не заменяет текущий');
})().catch(e=>{console.error(e);process.exitCode=1;});
'''.replace('SOURCE',json.dumps(refresh))
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Нужен Node')
    def test_incoming_table_has_date_column_without_legacy_export(self):
        source=(Path(__file__).parents[1]/'itd/web_assets/journals.js').read_text()
        table=source[source.index('const incomingResultNames='):source.index('function entryResourceSelect(')]
        script=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
const entries=[
 {id:1,entry_date:'2026-11-05',title:'Кабель',work_fields:{incoming_result:'accepted'}},
 {id:2,entry_date:'2026-11-05',title:'Манометр',work_fields:{incoming_result:'pending'}}
];
const ctx={filteredEntries:()=>entries,esc:x=>x??'',journalValue:x=>x??'—',
 tableFilters:{incoming:{}},pdata:{journals:{incoming:entries}}};
vm.runInNewContext(SOURCE,ctx);
const html=ctx.incomingJournalTable();
assert.match(html,/<th>Дата<\/th><th>Ресурс<\/th><th>Кол-во<\/th><th>Результат<\/th><th>Примечание<\/th>/);
assert.equal((html.match(/<td>2026-11-05<\/td>/g)||[]).length,2);
assert.doesNotMatch(html,/Выгрузить записи|Поставка/);
""".replace('SOURCE',json.dumps(table))
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Нужен Node')
    def test_inline_title_save_clears_dirty_state_even_without_open_dialog(self):
        source=(Path(__file__).parents[1]/'itd/web_assets/ojr-ui.js').read_text()
        handler=source[source.index('async function submitArchitectureForm('):source.index("document.addEventListener('click'")]
        script=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
const ctx={formDirty:true,projectId:1,titleRoles:{builder:'Подрядчик'},pdata:{journals:{title_signatories:[]}},
 FormData:class {get(){return '';}},api:async()=>({saved:true}),
 closeEditor:()=>false,loadProject:async()=>{},render:()=>{},toast:()=>{}};
vm.runInNewContext(SOURCE,ctx);
ctx.submitArchitectureForm({getAttribute:()=> 'ojr-title-form'}).then(()=>assert.equal(ctx.formDirty,false)).catch(e=>{console.error(e);process.exitCode=1;});
""".replace('SOURCE',json.dumps(handler))
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
