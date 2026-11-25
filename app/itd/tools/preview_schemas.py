"""Write-preview payloads matching the editable РД forms."""
from dataclasses import dataclass
from functools import reduce
from operator import or_
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator

from ..assistant_files import MAX_BYTES


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


Id = Annotated[int, Field(gt=0, le=2**63-1)]
Revision = Annotated[int, Field(ge=0, le=2**63-1)]
Amount = Annotated[float, Field(ge=0)]
Text = Annotated[str, Field(min_length=1, max_length=20000)]
Note = Annotated[str, Field(max_length=20000)]
Role = Annotated[str, Field(pattern=r'^[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё_0-9]*$', max_length=100)]
Key = Annotated[str, Field(pattern=r'^[A-Za-z_][A-Za-z_0-9]*$', max_length=160)]
IdList = Annotated[list[Id], Field(max_length=500)]
Scalar = str | int | float | bool | None
Category = Literal[
    'Шкафы, пульты, клеммные и распределительные коробки',
    'Приборы и средства автоматизации',
    'Материалы для монтажа приборов и средств автоматизации',
    'Кабельная продукция',
]


class File(Input):
    name: Annotated[str, Field(min_length=1, max_length=255, pattern=r'^[^/\\\x00-\x1f]+$')]
    content: Annotated[str, Field(min_length=1, max_length=4 * ((MAX_BYTES + 2) // 3))]


class ChatAttachment(Input):
    attachment_id: Annotated[str, Field(pattern=r'^[0-9a-f]{32}$')]


Attachment = File | ChatAttachment


class DocumentField(Input):
    key: Key
    kind: Literal['literal', 'reference', 'table', 'signatory']
    label: Note | None = None
    required: bool = False
    state: Literal['hidden', 'not_applicable'] | None = None
    reason: Note | None = None
    format: Note | None = None
    value_type: Literal['text', 'date', 'number'] | None = None
    value: Scalar | list[dict[Key, Scalar]] = Field(
        default=None,
        description=('В загруженном шаблоне используйте {{ $db.organizations.full_name }}. '
                     'В карточке документа найдите запись в binding_sources результата project-records '
                     'и укажите её идентификатор во всех связанных подстановках, например '
                     '{{ $db.organizations.r12.full_name }} и {{ $db.organizations.r12.inn }}. '
                     'Сохраните остальные свойства поля и текст вокруг подстановок.'),
    )
    source: Note | None = None
    template_path: Note | None = None
    template: Note | None = None
    presentation: Note | None = None
    role: Role | None = None
    expression: Note | bool | None = None
    binding_explicit: bool | None = None
    binding_role: Role | None = None
    role_slot: Role | None = None
    role_options: list[Role] | None = None
    mask: Note | None = None
    marker_path: Note | None = None
    db_table: Note | None = None
    type: Note | None = None
    view: Note | None = None
    fields: Annotated[list['DocumentField'], Field(max_length=200)] | None = None
    block: Note | None = None
    placeholder: Note | None = None

    @model_validator(mode='after')
    def table_columns(self):
        if isinstance(self.value, list):
            if self.kind != 'table' or self.fields is None or len(self.value) > 500:
                raise ValueError('Некорректные строки ручной таблицы')
            columns = {field.key for field in self.fields}
            if any(set(row) - columns for row in self.value):
                raise ValueError('Колонка отсутствует в определении ручной таблицы')
        return self


DocumentFields = Annotated[list[DocumentField], Field(max_length=200)]


class SchemeFields(Input):
    num: Text | None = None
    name: Text | None = None
    ref_code: Note | None = None
    sheets_count: Id | None = None
    note: Note | None = None


class SchemeNew(SchemeFields):
    num: Text
    name: Text
    file: Attachment | None = None


class SchemeEdit(Input):
    id: Id
    changes: SchemeFields
    file: Attachment | None = None


class ResourceFields(Input):
    name: Text | None = None
    unit: Text | None = None
    category: Category | None = None
    spec_num: Note | None = None
    short_name: Note | None = None
    type_mark: Note | None = None
    manufacturer: Note | None = None
    supplier: Note | None = None
    qty_proj: Amount | None = None
    qty_fact: Amount | None = None
    unit_weight: Amount | None = None
    note: Note | None = None


class ResourceNew(ResourceFields):
    name: Text
    unit: Text
    category: Category
    serial_numbers: list[Text] | None = None


class ResourcePatch(ResourceFields):
    serial_num: Note | None = None


class ResourceEdit(Input):
    id: Id
    changes: ResourcePatch


class SourceFile(Input):
    file: Attachment
    doc_type: Literal['order', 'certificate', 'passport', 'rd', 'scheme', 'other', 'contract', 'quality'] = 'rd'
    title: Text | None = None


class AttachmentFields(Input):
    title: Text | None = None
    doc_num: Note | None = None
    doc_date: Note | None = None
    sheets_count: Id | None = None
    note: Note | None = None


class AttachmentEdit(Input):
    id: Id
    changes: AttachmentFields


class Material(Input):
    resource_id: Id
    quantity: Amount | None = None


class Entry(Input):
    id: Id | None = None
    revision: Id | None = None
    title: Text
    entry_date: Note | None = None
    details: Note | None = None
    act_id: Id | None = None
    attachment_id: Id | None = None
    resource_id: Id | None = None
    responsible: Note | None = None
    change_reason: Note | None = None


class WorkValues(Input):
    location: Note | None = None
    method: Note | None = None
    tests: Note | None = None
    line_number: Note | None = None
    mark: Note | None = None
    drum: Note | None = None
    couplings: Note | None = None
    temperature: Note | float | None = None
    heating: Note | None = None


class Work(Entry):
    conditions: Note | None = None
    responsible_id: Id | None = None
    work_type: Note | None = None
    quantity: Amount | None = None
    unit: Note | None = None
    materials: Annotated[list[Material], Field(max_length=200)] | None = None
    work_fields: WorkValues | None = None


class CableWork(Work):
    work_type: Literal['cable'] = 'cable'


class PersonnelFields(Input):
    person_id: Id
    org_id: Id | None = None
    organization: Note | None = None
    person: Note | None = None
    scope: Note | None = None
    authority: Note | None = None
    start_date: Note | None = None
    end_date: Note | None = None


class Personnel(Entry):
    work_fields: PersonnelFields


class JournalIssueFields(Input):
    issued_date: Note | None = None
    keeper: Note | None = None
    transfer_date: Note | None = None
    recipient: Note | None = None


class JournalIssue(Entry):
    work_fields: JournalIssueFields


class ControlFields(Input):
    defects: Note | None = None
    deadline: Note | None = None
    resolved_date: Note | None = None
    resolved_by: Note | None = None


class Control(Entry):
    work_fields: ControlFields


class SpecialJournal(Input):
    id: Id | None = None
    revision: Id | None = None
    name: Text
    org_id: Id | None = None
    keeper_id: Id | None = None
    recipient_id: Id | None = None
    issued_date: Note | None = None
    transfer_date: Note | None = None
    note: Note | None = None


class LinkedJournal(Input):
    act_type: Text
    entry_kind: Literal['work', 'incoming', 'journal']
    work_type: Note | None = None
    table_key: Key
    mapping: dict[Key, Text]
    date_signed: Note | None = None


class IncomingReview(Input):
    status: Literal['matches', 'mismatch', 'uncertain']
    checked_by: Text
    note: Text


class IncomingItem(Input):
    id: Id | None = None
    revision: Id | None = None
    resource_id: Id
    result: Literal['pending', 'accepted', 'rejected']
    quantity: Amount | None = None
    document_type: Note | None = None
    details: Note | None = None
    file: Attachment | None = None
    review: IncomingReview | None = None


class IncomingDay(Input):
    date: Text
    resources: Annotated[list[IncomingItem], Field(min_length=1, max_length=200)]


class SupplyValues(Input):
    batch_num: Note | None = None
    supply_date: Note | None = None
    quantity: Amount | None = None
    unit: Text | None = None
    supplier: Note | None = None
    source: Text
    attachment_id: Id | None = None
    status: Literal['accepted', 'rejected', 'pending', 'void']
    note: Note | None = None


class SupplyNew(SupplyValues):
    resource_id: Id
    source_key: Text
    status: Literal['accepted', 'rejected', 'pending']


class SupplyEdit(Input):
    id: Id
    resource_id: Id
    revision: Id
    reason: Text
    values: SupplyValues


class SupplyStatus(Input):
    id: Id
    status: Literal['accepted', 'rejected', 'void']
    note: Text
    revision: Id


class FactValues(Input):
    location: Text
    work_description: Text
    source: Text
    reported_by: Text
    status: Literal['pending', 'confirmed', 'void']
    quantity: Amount | None = None
    unit: Text | None = None
    start_date: Note | None = None
    end_date: Note | None = None
    attachment_id: Id | None = None


class FactNew(FactValues):
    resource_id: Id
    source_key: Text
    status: Literal['pending', 'confirmed']
    work_entry_id: Id | None = None


class FactFromWork(Input):
    work_entry_id: Id
    resource_id: Id
    source_key: Text
    status: Literal['pending', 'confirmed']
    quantity: Amount | None = None


class FactEdit(Input):
    id: Id
    resource_id: Id
    reason: Text
    source_key: Text
    values: FactValues


class FactStatus(Input):
    id: Id
    status: Literal['confirmed', 'void']
    reason: Text


class QualityCheck(Input):
    resource_id: Id
    attachment_id: Id
    status: Literal['matches', 'mismatch', 'uncertain']
    checked_by: Text
    checked_date: Text
    source: Text
    note: Text


class ActFields(Input):
    date_signed: Note | None = None
    filename_title: Note | None = None
    registry_note: Note | None = None
    sheets_count: Id | None = None
    fields: DocumentFields | None = None


class ActPatch(ActFields):
    is_active: bool | Literal[0, 1] | None = None


class ActEdit(Input):
    id: Id
    changes: ActPatch


class Removal(Input):
    id: Id
    revision: Id
    resource_ids: IdList


class ActNew(Input):
    act_type: Text
    date_signed: Note | None = None
    fields: DocumentFields = Field(default_factory=list)
    entry_ids: IdList = Field(default_factory=list)
    resource_ids: IdList = Field(default_factory=list)
    scheme_ids: IdList = Field(default_factory=list)
    fact_ids: IdList = Field(default_factory=list)
    resource_removals: list[Removal] = Field(default_factory=list, max_length=200)
    organizations: dict[Role, Id] = Field(default_factory=dict)
    signatories: dict[Role, Id] = Field(default_factory=dict)
    work_only: bool = False
    attachment_id: Id | None = None


class ActComposition(Input):
    act_id: Id
    resources: IdList
    schemes: IdList


class ActWorks(Input):
    act_id: Id
    entry_ids: IdList


class ActSigners(Input):
    act_id: Id
    signatories: dict[Role, Id]


class ActState(Input):
    act_id: Id
    state: Literal['draft', 'signed']
    basis: Text
    signed_date: Note | None = None
    work_description: Note | None = None
    expected_revision: Revision
    signatories: dict[Role, Id] | None = None


class ActSourceReview(Input):
    act_id: Id
    reason: Text


class FinalReview(Input):
    act_id: Id
    note: Text


class Allocation(Input):
    act_id: Id
    supply_id: Id
    quantity: Amount


class VersionNew(Input):
    act_id: Id
    id: Id | None = None
    revision: Id | None = None


class VersionEnsure(Input):
    act_id: Id


class VersionSigner(Input):
    role: Role
    person_id: Id
    signed: bool = False
    signed_date: Note | None = None


class VersionFields(ActFields):
    organizations: dict[Role, Id] | None = None
    work_description: Note | None = None


class VersionEdit(Input):
    act_id: Id
    id: Id
    revision: Id
    card: VersionFields
    signers: Annotated[list[VersionSigner], Field(max_length=100)]
    work_description: Note | None = None
    signed_attachment_id: Id | None = None


class VersionDelete(Input):
    act_id: Id
    id: Id
    revision: Id


class RequirementFields(Input):
    title: Text | None = None
    work_scope: Text | None = None
    basis: Text | None = None
    kind: Literal['act', 'attachment', 'scheme', 'xlsx'] | None = None
    state: Literal['required', 'not_applicable'] | None = None
    reason: Note | None = None
    act_type: Note | None = None
    attachment_type: Note | None = None
    act_id: Id | None = None
    attachment_id: Id | None = None
    scheme_id: Id | None = None
    release_id: Id | None = None


class RequirementNew(RequirementFields):
    title: Text
    work_scope: Text
    basis: Text
    kind: Literal['act', 'attachment', 'scheme', 'xlsx']


class RequirementEdit(Input):
    id: Id
    changes: RequirementFields


class DeliveryEvent(Input):
    event_date: Text
    source: Text
    note: Text


class DeliveryNew(DeliveryEvent):
    release_id: Id
    recipient: Text


class DeliveryEdit(DeliveryEvent):
    id: Id
    revision: Id
    status: Literal['remarks', 'corrected', 'sent', 'accepted']
    release_id: Id | None = None


class RemarkNew(Input):
    delivery_id: Id
    description: Text
    source: Text


class RemarkResolve(Input):
    id: Id
    resolution: Text
    resolution_source: Text
    resolution_date: Text
    resolution_release_id: Id


class JournalTitle(Input):
    signatories: dict[Role, Id | None]
    organizations: dict[Role, Id | None]


class Assignment(Input):
    entity: Literal['organization', 'signatory']
    entity_id: Id
    role: Role
    scope: Literal['object', 'project']
    mode: Literal['add', 'replace', 'remove']


class ParticipantPeriod(Input):
    org_id: Id
    active_from: Note | None = None
    active_to: Note | None = None
    basis: Text


class ObjectUnit(Input):
    name: Text
    code: Note | None = None
    genplan_num: Note | None = None


class Designer(Input):
    name: Text


class ProjectFields(Input):
    code: Text | None = None
    name: Text | None = None
    city: Note | None = None
    gip: Note | None = None
    inv_num: Note | None = None
    contract_num: Note | None = None
    contract_date: Note | None = None
    form_set: Note | None = None
    unit_id: Id | None = None
    designer_org_id: Id | None = None
    smr_start: Note | None = None
    smr_end: Note | None = None
    pnr_start: Note | None = None
    pnr_end: Note | None = None


class ProjectEdit(Input):
    changes: ProjectFields


class FormConnect(Input):
    code: Text


class TemplateNew(Input):
    name: Text
    form_set: Text
    file: Attachment
    fields: DocumentFields | None = None


TemplateCode = Annotated[str, Field(pattern=r'^TPL_[0-9a-f]{32}$')]


class TemplateEdit(Input):
    code: TemplateCode
    revision: Id
    name: Text | None = None
    form_set: Text | None = None
    file: Attachment | None = None
    fields: DocumentFields | None = None


class TemplateRemove(Input):
    code: TemplateCode
    revision: Id


class Remove(Input):
    id: Id


class SpecificationLine(Input):
    position: Note | None = None
    name: Note | None = None
    unit: Note | None = None
    quantity: Amount | Note | None = None
    reference: Note | None = None
    category: Category | None = None
    page: Id | None = None
    sheet: Note | None = None
    locator: Note | None = None


class Specification(Input):
    project_id: Id
    attachment: Attachment
    category: Category | None = None
    rows: Annotated[list[SpecificationLine], Field(max_length=500)] | None = None


@dataclass(frozen=True)
class Definition:
    name: str
    label: str
    model: type[Input]


def table(name, label, **operations):
    variants = [
        create_model(f'{model.__name__}{verb.title()}Row', __base__=model,
                     operation=(Literal[verb], ...))
        for verb, model in operations.items()
    ]
    rows = Annotated[reduce(or_, variants), Field(discriminator='operation')] if len(variants) > 1 else variants[0]
    model = create_model('Preview' + ''.join(part.title() for part in name.split('-')),
                         __base__=Input, project_id=(Id, ...),
                         rows=(Annotated[list[rows], Field(min_length=1, max_length=200)], ...))
    return Definition('preview-' + name, label, model)


DEFINITIONS = (
    table('resources', 'Ведомость ресурсов', add=ResourceNew, edit=ResourceEdit, remove=Remove),
    table('schemes', 'Исполнительные схемы', add=SchemeNew, edit=SchemeEdit, remove=Remove),
    table('source-files', 'Исходные файлы', add=SourceFile, edit=AttachmentEdit, remove=Remove),
    Definition('preview-specification', 'Импорт спецификации ресурсов', Specification),
    table('works', 'ОЖР. Работы', save=Work, remove=Remove),
    table('cable-works', 'ЖПК. Прокладка кабелей', save=CableWork, remove=Remove),
    table('ojr-personnel', 'ОЖР. Инженерно-технический персонал', save=Personnel, remove=Remove),
    table('ojr-journals', 'ОЖР. Записи о выдаче журналов', save=JournalIssue, remove=Remove),
    table('ojr-control', 'ОЖР. Строительный контроль', save=Control, remove=Remove),
    table('ojr-supervision', 'ОЖР. Государственный строительный надзор', save=Control, remove=Remove),
    table('ojr-title', 'ОЖР. Титульный лист', save=JournalTitle),
    table('special-journals', 'Реестр специальных журналов', save=SpecialJournal, remove=Remove),
    table('linked-journals', 'Связи форм журналов с записями', add=LinkedJournal),
    table('incoming-control', 'ЖВК. Входной контроль', save=IncomingDay, remove=Remove),
    table('supplies', 'Поставки и партии', add=SupplyNew, edit=SupplyEdit, status=SupplyStatus, remove=Remove),
    table('installation-facts', 'Факты монтажа', add=FactNew, from_work=FactFromWork,
          edit=FactEdit, status=FactStatus, remove=Remove),
    table('quality-reviews', 'Проверки документов качества', add=QualityCheck, remove=Remove),
    table('documents', 'Основные документы', add=ActNew, edit=ActEdit, remove=Remove),
    table('document-versions', 'Карточки версий документов', ensure=VersionEnsure,
          add=VersionNew, edit=VersionEdit, remove=VersionDelete),
    table('document-composition', 'Ресурсы и схемы акта', save=ActComposition),
    table('document-works', 'Связи работ с актом', save=ActWorks),
    table('document-signatories', 'Подписанты актов', save=ActSigners),
    table('document-status', 'ОЖР. Статусы основных документов', save=ActState),
    table('document-sources', 'Сверка источников актов', review=ActSourceReview),
    table('document-reviews', 'Проверка готовности документов', review=FinalReview),
    table('document-allocations', 'Списание поставок в акт', save=Allocation),
    table('package-requirements', 'Требования к комплекту', add=RequirementNew, edit=RequirementEdit, remove=Remove),
    table('deliveries', 'Сдача и события передачи', add=DeliveryNew, status=DeliveryEdit, remove=Remove),
    table('delivery-remarks', 'Замечания при сдаче', add=RemarkNew, resolve=RemarkResolve, remove=Remove),
    table('participant-assignments', 'Назначения участников в документах', save=Assignment),
    table('participant-periods', 'Периоды участия организаций', save=ParticipantPeriod, remove=Remove),
    table('object-units', 'Корпуса и части объекта', add=ObjectUnit, remove=Remove),
    table('project-designer', 'Разработчик раздела', add=Designer),
    table('project-details', 'Реквизиты и связи раздела', edit=ProjectEdit),
    table('document-forms', 'Подключение форм документов из каталога', add=FormConnect),
    table('document-templates', 'Загруженные шаблоны DOCX', add=TemplateNew, edit=TemplateEdit, remove=TemplateRemove),
)
