'use strict';
let journalSection='0',journalRefreshBusy=false;
const journalFields={
 '1':{organization:'Организация',person:'Фамилия, инициалы и должность работника',start_date:'Начало работ на объекте',end_date:'Окончание работ на объекте',scope:'Вид работ',authority:'Основание полномочий'},
 '2':{issued_date:'Дата выдачи журнала',keeper:'Организация и представитель, ведущие журнал',transfer_date:'Дата передачи заказчику',recipient:'Представитель, принявший журнал'},
 '4':{defects:'Выявленные недостатки',deadline:'Срок устранения',resolved_date:'Дата устранения',resolved_by:'Представитель, подтвердивший устранение'},
 '6':{defects:'Выявленные нарушения',deadline:'Срок устранения',resolved_date:'Фактическая дата устранения',resolved_by:'Должностное лицо, подтвердившее устранение'}
};
function journalTable(headers,rows,{ids=null,entity=null,records=null}={}){
 const selectable=Array.isArray(ids),columns=headers.length+(selectable?1:0);
 const head=(selectable?'<th class="row-check"><input type="checkbox" data-select-visible aria-label="Выбрать все видимые строки"></th>':'')+headers.map(h=>`<th>${esc(h)}</th>`).join('');
 const body=rows.map((cells,i)=>{
  const id=selectable?esc(ids[i]):'';
  const record=records?.[i]||(entity&&ids?{entity,id:ids[i]}:null);
  const recordAttrs=record?` data-record-entity="${esc(record.entity)}" data-record-id="${esc(record.id)}"`:'';
  return `<tr${recordAttrs}${selectable?` data-row-id="${id}"`:''}>${selectable?`<td class="row-check"><input type="checkbox" data-row-select="${id}" aria-label="Выбрать строку ${i+1}"></td>`:''}${cells.map(c=>`<td>${c}</td>`).join('')}<td class="table-fill" data-table-fill aria-hidden="true"></td></tr>`;
 }).join('');
 return `<div class="table-scroll"><table${selectable?' data-selectable':''}><thead><tr>${head}<th class="table-fill" data-table-fill aria-hidden="true"></th></tr></thead><tbody>${rows.length?body:`<tr><td colspan="${columns+1}" class="empty">Сведения пока не внесены.</td></tr>`}</tbody></table></div>`;
}
function journalValue(value){return esc(value==null?'Не указано':typeof value==='number'?formatTableNumber(value):displayTableDate(value));}
function journalEntryAction(e){return `<small>${esc(e.section_code)} · Запись № ${e.id}</small>`;}
function journalEntryName(e,text=e.title){return `<button type="button" class="cell-open" data-journal-edit="${e.id}">${esc(text)}</button>`;}
const journalHelp={
 '1':'Укажите работника, вид работ и известные сроки его участия.',
 '2':'Запишите выдачу или передачу специального журнала.',
 '3':'Записывайте выполненные работы. Эти же записи доступны для подготовки актов.',
 '4':'Опишите проведённый контроль. Недостатки и их устранение укажите, если эти сведения известны.',
 '5':'Здесь автоматически появляются зарегистрированные документы всех разделов объекта.',
 '6':'Внесите сведения о состоявшемся мероприятии госстройнадзора.'
};
function generalJournalPage(){
 const j=pdata.journals;
 let html='';
 if(journalHelp[journalSection])html+=`<p class="journal-purpose">${esc(journalHelp[journalSection])}</p>`;
 if(journalSection==='0'){
  const o=j.object;
  html+=card('Сведения об объекте','<p class="hint">Сроки автоматически рассчитываются по датам СМР и ПНР всех разделов объекта: самое раннее начало и самое позднее окончание. При отсутствии дат разделов показаны сроки из карточки объекта.</p><div class="toolbar"><button class="secondary" data-view="object">Открыть карточку объекта</button></div>'+journalTable(['Сведения','Текущее значение'],[['Наименование',o.name],['Адрес',o.address],['Вид строительства',o.construction_type],['Начало строительства объекта',j.construction_dates.start],['Окончание строительства объекта',j.construction_dates.end],['Разрешение: номер, дата, орган',[o.permit_num,displayTableDate(o.permit_date),o.permit_authority].filter(Boolean).join(' · ')||null],['Экспертиза: номер, дата, орган',[o.expertise_num,displayTableDate(o.expertise_date),o.expertise_authority].filter(Boolean).join(' · ')||null],['Дело ГСН',o.gsn_case]].map(row=>row.map(journalValue))),'building');
  html+=titleAssignmentsEditor();
  html+=card('Участники объекта','<div class="toolbar"><button class="secondary" data-view="participants">Открыть участников</button></div>'+journalTable(['Организация','Роли','Представители и основания'],j.participants.map(o=>[esc(o.full_name),esc(o.roles.map(r=>meta.roles[r]||r).join(', ')),o.representatives.map(r=>esc([[r.position,r.fio].filter(Boolean).join(' '),r.order_doc,r.status].filter(Boolean).join(' · '))).join('<br>')]),{records:j.participants.map(o=>({entity:'organizations',id:o.id}))})+'<p class="hint">Указаны участники объекта. Назначения документов в отдельных разделах могут отличаться. Полномочия и подписи проверяются отдельно.</p>','user');
 }else if(journalSection==='3'){
  html+=workPage();
 }else if(journalSection==='5'){
  html+=card('5. Исполнительная документация',`<button class="secondary" data-view="documents">Открыть документы раздела</button><p class="hint">Здесь показаны акты со статусом «Подписан». Реквизиты и состав подписантов зафиксированы при подтверждении статуса.</p>`+journalTable(['Раздел','Документ','Работы и место','Дата подписания','Подписанты'],j.sections['5'].map(a=>[esc(a.section_code),esc(a.act_num+' «'+a.form_name+'»'),esc(a.work_description),journalValue(a.date_signed),esc(a.signed_by.map(p=>[[p.position,p.fio].filter(Boolean).join(' '),p.organization?.full_name].filter(Boolean).join(' · ')).join('; '))]),{records:j.sections['5'].map(a=>({entity:'acts',id:a.id}))}),'file');
 }else{
  const legacy=journalSection==='legacy',entries=legacy?j.legacy:j.sections[journalSection],fields=journalFields[journalSection]||{};
  html+=card(legacy?'Прежние записи без раздела':journalSection+'. '+j.section_names[journalSection],(legacy?'<p class="hint">Существующие записи сохранены. При редактировании можно явно выбрать раздел ОЖР.</p>':`<button data-journal-new="${journalSection}">${{'1':'Добавить работника','2':'Добавить журнал','4':'Внести проверку','6':'Добавить мероприятие'}[journalSection]}</button>`)+journalTable(['Дата','Содержание',...Object.values(fields),'Ответственный','Источник'],entries.map(e=>[journalValue(e.entry_date),journalEntryName(e,[e.title,e.details].filter(Boolean).join(' · ')),...Object.keys(fields).map(k=>journalValue(e.resolved_fields[k])),journalValue(e.responsible_person?[e.responsible_person.position,e.responsible_person.fio].filter(Boolean).join(' '):e.responsible),journalEntryAction(e)])),'list');
  if(journalSection==='2')html+=card('Подключённые формы журналов',journalTable(['Раздел','Форма','Источник'],j.connected.map(j=>[esc(j.section_code),esc(j.act_num+' «'+j.name+'»'),esc({work:'Работы',incoming:'Входной контроль',journal:'Записи журналов'}[j.entry_kind])]))+'<p class="hint">Подключение формы не означает выдачу или передачу специального журнала. Эти события внесите отдельной записью выше.</p>','file');
 }
 return html;
}
const incomingResultNames={pending:'Проверка не завершена',accepted:'Входной контроль пройден',rejected:'Не принято'};
const documentReviewNames={matches:'Соответствует',mismatch:'Выявлено несоответствие',uncertain:'Применимость не подтверждена'};
function incomingJournalBody(){
 return filteredEntries('incoming').map(e=>{
  const w=e.work_fields,s=e.supply,outcome=w.incoming_result||'pending';
  return `<tr><td>${journalValue(e.entry_date)}</td><td><button type="button" class="cell-open" data-edit-entry="${e.id}">${esc(e.resource?.name||e.title)}</button></td><td>${journalValue(e.quantity??s?.quantity)} ${esc(e.unit||s?.unit||e.resource?.unit)}</td><td>${esc(incomingResultNames[outcome])}</td><td>${esc(e.details)}</td></tr>`;
 }).join('')||'<tr><td colspan="5" class="empty">За выбранный период записей нет.</td></tr>';
}
function incomingJournalTable(){
 const f=tableFilters.incoming;
 return `<div class="toolbar"><button data-editor="incoming">Добавить запись</button><input data-filter="search" data-kind="incoming" aria-label="Поиск записей" placeholder="Найти ресурс…" value="${esc(f.search)}"></div><div class="table-filters"><fieldset class="table-date-range"><legend>Дата</legend><label class="field"><span>С</span><input type="date" aria-label="Дата с" data-filter="from" data-kind="incoming" value="${esc(f.from)}"></label><label class="field"><span>По</span><input type="date" aria-label="Дата по" data-filter="to" data-kind="incoming" value="${esc(f.to)}"></label></fieldset><button type="button" class="secondary" data-reset-filters="incoming">Сбросить фильтр</button></div><div class="table-count" id="table-count" hidden data-total="${pdata.journals.incoming.length}">Показано ${filteredEntries('incoming').length} из ${pdata.journals.incoming.length}</div><div class="table-scroll"><table><thead><tr><th>Дата</th><th>Ресурс</th><th>Кол-во</th><th>Результат</th><th>Примечание</th></tr></thead><tbody id="entry-rows">${incomingJournalBody()}</tbody></table></div>`;
}
function entryResourceSelect(e){return `<label class="field wide"><span>Материал или оборудование</span><select name="resource_id"><option value="">Укажу вручную</option>${pdata.resources.map(r=>option(r.id,r.name,e.resource_id)).join('')}</select></label>`;}
let incomingBlockNumber=0;
function incomingBlock(entry={}){
 const key=++incomingBlockNumber;
 const w=typeof entry.work_fields==='string'?JSON.parse(entry.work_fields):entry.work_fields||{};
 const file=pdata.attachments.find(a=>a.id===entry.attachment_id);
 const review=pdata.quality_reviews.find(r=>r.id===w.quality_review_id&&r.attachment_id===file?.id);
 const canReview=file&&sourceType(file)==='quality';
 return `<fieldset class="preview-section incoming-resource" data-incoming-resource data-id="${entry.id||''}" data-revision="${entry.revision||''}" data-original-resource="${entry.resource_id||''}" data-original-quality="${Boolean(canReview)}"><legend>Ресурс</legend><div class="grid">
 <label class="field wide"><span>Ресурс *</span><select name="resource_id" required><option value="">Выберите ресурс…</option>${pdata.resources.map(r=>option(r.id,resourceLabel(r.id),entry.resource_id)).join('')}</select></label>
 ${input('quantity','Кол-во',entry.quantity,'number')}
 <label class="field"><span>Результат</span><select name="result">${Object.entries(incomingResultNames).map(([value,label])=>option(value,label,w.incoming_result||'pending')).join('')}</select></label>
 ${input('details','Примечание',entry.details,'text',true)}
 <label class="field wide"><span>Тип документа</span><select name="document_type"><option value="">Выберите тип…</option>${Object.entries(pdata.journals.incoming_document_types||{}).map(([value,label])=>option(value,label,w.incoming_document_type)).join('')}</select></label></div>
 ${uploadZone('incoming-file-'+key,'Выбрать файл')}
 <p class="hint" aria-live="polite" data-incoming-filename data-original-name="${esc(file?.original_name||'')}">${esc(file?.original_name||'')}</p>
 <details class="ux-disclosure" data-document-review ${canReview?'':'hidden'}>
 <summary>Сверка документа</summary>
 ${review?`<p class="hint" data-document-review-history>Последняя сверка: ${esc(documentReviewNames[review.status])} · ${esc(displayTableDate(review.checked_date))} · ${esc(review.checked_by)}</p>`:''}
 <div class="grid"><label class="field wide"><span>Результат новой сверки</span><select name="review_status"><option value="">Оставить без новой сверки</option>${Object.entries(documentReviewNames).map(([value,label])=>option(value,label)).join('')}</select></label>
 ${input('review_by','Кто сверил')}${input('review_note','Что сверили','', 'text',true)}</div></details>
 ${entry.id?'':'<button type="button" class="secondary" data-incoming-remove>Убрать ресурс</button>'}</fieldset>`;
}
function incomingEntryEditor(entry){
 const sameDay=entry.id&&entry.entry_date?pdata.journals.incoming.filter(row=>row.entry_date===entry.entry_date):[];
 const unique=new Set(sameDay.map(row=>row.resource_id));
 const entries=sameDay.length&&unique.size===sameDay.length&&!unique.has(null)?sameDay:entry.id?[entry]:[];
 return `<form id="incoming-day-form"><div class="grid">${input('date','Дата контроля *',entry.entry_date,'date')}</div>
 <div data-incoming-blocks>${entries.map(incomingBlock).join('')}</div>
 <div class="toolbar"><button type="button" class="secondary" data-incoming-add>Добавить ресурс</button></div>
 <div class="ux-form-actions"><button type="submit">Сохранить запись</button><button type="button" class="secondary" data-action="cancel-entry">Отменить</button></div></form>`;
}
function syncIncomingChoices(form){
 const selects=[...form.querySelectorAll('select[name="resource_id"]')];
 const selected=new Set(selects.map(select=>select.value).filter(Boolean));
 const date=form.elements.namedItem('date').value;
 const editing=new Set([...form.querySelectorAll('[data-incoming-resource]')].map(block=>Number(block.dataset.id)));
 for(const row of pdata.journals.incoming){
  if(row.entry_date===date&&!editing.has(row.id))selected.add(String(row.resource_id));
 }
 for(const select of selects){
  const value=select.value;
  select.innerHTML='<option value="">Выберите ресурс…</option>'+pdata.resources
   .filter(r=>String(r.id)===value||!selected.has(String(r.id)))
   .map(r=>option(r.id,resourceLabel(r.id),value)).join('');
  enhanceSelect(select);
 }
}
async function submitIncomingDay(form){
 const blocks=[...form.querySelectorAll('[data-incoming-resource]')];
 if(!blocks.length)throw Error('Добавьте хотя бы один ресурс');
 const files=blocks.map(block=>block.querySelector('input[type="file"]').files[0]);
 if(files.reduce((total,file)=>total+(file?.size||0),0)>32*1024*1024)throw Error('Общий размер файлов одной записи — до 32 МБ');
 const resources=await Promise.all(blocks.map(async(block,index)=>{
  const read=name=>block.querySelector(`[name="${name}"]`).value;
  const file=files[index],quantity=read('quantity');
  const status=block.querySelector('[data-document-review]').hidden?'':read('review_status');
  return {id:Number(block.dataset.id)||null,revision:Number(block.dataset.revision)||null,resource_id:Number(read('resource_id')),
   quantity:quantity===''?null:Number(quantity),result:read('result'),details:read('details'),document_type:read('document_type'),
   ...(status?{review:{status,checked_by:read('review_by'),note:read('review_note')}}:{}),
   ...(file?{file:{name:file.name,content:await readUploadContent(file)}}:{})};
 }));
 if(!await saveDatedJournal('/api/incoming-day',{project_id:projectId,day:{date:form.elements.namedItem('date').value,resources}},'day'))return;
 closeEditor(true);
 await reloadJournalWorkspace();
 await loadProject(projectId);
 render();
 toast('Запись сохранена');
}
document.addEventListener('click',event=>{
 const button=event.target.closest('[data-incoming-add],[data-incoming-remove]');
 const form=button?.closest('#incoming-day-form');
 if(!form)return;
 if(button.hasAttribute('data-incoming-add')){
  const date=form.elements.namedItem('date');
  if(!date.value){notice('Сначала выберите дату контроля');date.focus();return;}
  if(form.querySelectorAll('[data-incoming-resource]').length>=pdata.resources.length){notice('Все доступные ресурсы уже добавлены');return;}
  form.querySelector('[data-incoming-blocks]').insertAdjacentHTML('beforeend',incomingBlock());
  decorateSelects();
  syncIncomingChoices(form);
  form.querySelector('[data-incoming-resource]:last-child .smart-input')?.focus();
 }else{
  button.closest('[data-incoming-resource]').remove();
  syncIncomingChoices(form);
  form.querySelector('[data-incoming-add]').focus();
 }
 formDirty=true;
});
document.addEventListener('change',event=>{
 const field=event.target,form=field.closest('#incoming-day-form');
 if(!form)return;
 if(field.name==='resource_id'||field.name==='date')syncIncomingChoices(form);
 const block=field.closest('[data-incoming-resource]');
 if(!block)return;
 const file=block.querySelector('input[type="file"]').files[0];
 const name=block.querySelector('[data-incoming-filename]');
 const type=block.querySelector('[name="document_type"]');
 const sameResource=block.querySelector('[name="resource_id"]').value===block.dataset.originalResource;
 name.textContent=file?.name||(sameResource?name.dataset.originalName:'');
 type.required=Boolean(file);
 const review=block.querySelector('[data-document-review]');
 review.hidden=file?!type.value||type.value==='other':!sameResource||block.dataset.originalQuality!=='true';
 const history=review.querySelector('[data-document-review-history]');
 if(history)history.hidden=Boolean(file)||!sameResource;
 const status=block.querySelector('[name="review_status"]');
 if(field.type==='file'||field.name==='resource_id'){
  status.value='';
  enhanceSelect(status);
  for(const key of ['review_by','review_note'])block.querySelector(`[name="${key}"]`).value='';
 }
 const required=!review.hidden&&Boolean(status.value);
 for(const key of ['review_by','review_note'])block.querySelector(`[name="${key}"]`).required=required;
});
function specializedEntryEditor(kind,e){
 if(kind==='incoming')return incomingEntryEditor(e);
 const w=typeof e.work_fields==='string'?JSON.parse(e.work_fields):e.work_fields||{};
 const allFields=Object.assign({},...Object.values(journalFields));
 const fieldInput=(k,l)=>input('work_'+k,journalFields[w.journal_section]?.[k]||l,w[k],k.endsWith('_date')||k==='deadline'?'date':'text',true).replace('<label ',`<label data-journal-field="${k}" ${journalFields[w.journal_section]?.[k]?'':'hidden'} `);
 const section=`<label class="field"><span>Раздел ОЖР</span><select name="work_journal_section"><option value="">Без раздела</option>${['1','2','4','6'].map(s=>option(s,s+'. '+pdata.journals.section_names[s],w.journal_section)).join('')}</select></label>`;
 const people=`<div class="grid wide" data-journal-person ${w.journal_section==='1'?'':'hidden'}><label class="field"><span>Выбрать организацию</span><select name="work_org_id"><option value="">Введу вручную</option>${pdata.journals.directory.organizations.map(o=>option(o.id,o.full_name,w.org_id)).join('')}</select></label><label class="field"><span>Выбрать работника</span><select name="work_person_id"><option value="">Введу вручную</option>${pdata.journals.directory.people.filter(r=>r.status==='Действует'||r.id===w.person_id).map(r=>option(r.id,representativeLabel(r),w.person_id)).join('')}</select></label></div>`;
 const titleLabel={'1':'Краткое описание *','2':'Название журнала *','4':'Что проверяли *','6':'Контрольное мероприятие *'}[w.journal_section]||'Содержание записи *';
 return `<form id="entry-form" data-kind="journal"><p class="ux-form-intro">${esc(journalHelp[w.journal_section]||'Выберите раздел для этой записи.')} Обязательное поле отмечено *.</p>${w.journal_section?`<details class="ux-disclosure"><summary>Раздел ОЖР: ${esc(pdata.journals.section_names[w.journal_section])}</summary>${section}</details>`:section}<div class="grid">${input('title',titleLabel,e.title,'text',true)}${input('entry_date','Дата записи',e.entry_date,'date')}${input('responsible','Ответственный: должность, ФИО',e.responsible)}${people}${Object.entries(allFields).filter(([k])=>!['resolved_date','resolved_by','organization','person','authority'].includes(k)).map(([k,l])=>fieldInput(k,l)).join('')}</div><details class="ux-disclosure" data-journal-resolution ${['4','6'].includes(w.journal_section)?'':'hidden'} ${w.resolved_date||w.resolved_by?'open':''}><summary>Сведения об устранении</summary><div class="grid">${['resolved_date','resolved_by'].map(k=>fieldInput(k,allFields[k])).join('')}</div></details><details class="ux-disclosure" ${e.details||e.resource_id||e.attachment_id?'open':''}><summary>Место, примечание и документ-основание</summary><div class="grid">${input('details','Место и дополнительные сведения',e.details,'text',true)}${entryResourceSelect(e)}${attachmentSelectForEntry(e)}</div></details><div class="ux-form-actions"><button type="submit">Сохранить запись</button><button type="button" class="secondary" data-action="cancel-entry">Отменить</button></div></form>`;
}
function attachmentSelectForEntry(e){return `<label class="field wide"><span>Документ-основание</span><select name="attachment_id"><option value="">Не выбран</option>${pdata.attachments.filter(a=>pdata.project_attachment_ids.includes(a.id)).map(a=>option(a.id,a.title,e.attachment_id)).join('')}</select></label>`;}
async function refreshJournals(){
 if(typeof sessionSuspended!=='undefined'&&sessionSuspended)return;
 if(journalRefreshBusy||busy||dirty||formDirty||!projectId||!['journal','incoming','work','resources','ojr','facts','cable'].includes(workspaceView)||$('#editor-dialog').open||document.hidden||document.activeElement?.matches?.('input,textarea,select,[role=combobox]'))return;
 journalRefreshBusy=true;
 const pid=projectId,view=workspaceView;
 try{const revision=pdata?._revision;const next=await api('/api/project?project_id='+pid+'&poll=1'+(revision&&Date.now()-(pdata._checkedAt||0)<60000?'&revision='+encodeURIComponent(revision):''));if(pid!==projectId||view!==workspaceView||dirty||formDirty||busy||$('#editor-dialog').open)return;
 if(next.unchanged)return;
 if(JSON.stringify({...next,_checkedAt:0})!==JSON.stringify({...pdata,_checkedAt:0})){if(next._revision)next._checkedAt=Date.now();pdata=next;selectedEntries=new Set([...selectedEntries].filter(id=>pdata.workspace_entries.some(e=>e.id===id&&!e.act_id)));const positions=[...(document.querySelectorAll?.('#content .table-scroll')||[])].map(el=>[el.scrollLeft,el.scrollTop]);render();[...(document.querySelectorAll?.('#content .table-scroll')||[])].forEach((el,i)=>{if(positions[i])[el.scrollLeft,el.scrollTop]=positions[i];});}
 if(pdata?._revision)pdata._checkedAt=Date.now();
 }catch(_){/* Статус соединения отображается отдельно; введённые данные сохраняются. */}finally{journalRefreshBusy=false;}
}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b||formDirty)return;
 if(b.dataset.journalSection){journalSection=b.dataset.journalSection;render();}
 if(b.dataset.journalNew)openEditor('journal',{kind:'journal',work_fields:{journal_section:b.dataset.journalNew}});
 if(b.dataset.journalEdit)action(async()=>{const j=pdata.journals;const entry=[...Object.values(j.sections).flat(),...j.legacy].find(x=>x.id===Number(b.dataset.journalEdit)&&x.kind);if(!entry)return;if(entry.project_id!==projectId)await loadProject(entry.project_id,true);openEditor(entry.kind,entry);});
});
setInterval(refreshJournals,5000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshJournals();});

document.addEventListener('change',e=>{if(e.target.name!=='work_journal_section')return;const fields=journalFields[e.target.value]||{};document.querySelectorAll('[data-journal-field]').forEach(el=>{el.hidden=!fields[el.dataset.journalField];if(!el.hidden)el.querySelector('span').textContent=fields[el.dataset.journalField];});document.querySelector('[data-journal-person]').hidden=e.target.value!=='1';document.querySelector('[data-journal-resolution]').hidden=!['4','6'].includes(e.target.value);if(e.target.value!=='1')for(const name of ['work_org_id','work_person_id'])e.target.form.elements.namedItem(name).value='';});

document.addEventListener('change',e=>{if(e.target.name!=='work_type')return;const panel=e.target.closest('form')?.querySelector('[data-cable-fields]');if(panel){panel.hidden=e.target.value!=='cable';panel.open=!panel.hidden;}});
