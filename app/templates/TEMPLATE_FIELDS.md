# Свойства всех DOCX-шаблонов

Все имена ниже доступны непосредственно в Word через `{{ ... }}`. Общие типы, собственные поля и циклы описаны в [инструкции](README.md).
Технический ключ нужен только для совместимости сохранённых карточек; автор шаблона использует путь свойства. При регистрации новой формы он задаётся через `template_path` в JSON.

## И_1_13_07_01

Ведомость технической документации

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.readiness_date` | Дата акта технической готовности | `readiness_date` |
| `representatives.installer.position` | Представительмонтажной организации (должность) | `t1_r0_c2` |
| `representatives.installer.fio` | Представительмонтажной организации (расшифровка подписи) | `t1_r0_c6` |
| `form.section_1_2` | Номера документов, раздел 1 | `section_1_2` |
| `form.section_1_3` | Количество листов, раздел 1 | `section_1_3` |
| `form.section_1_4` | Примечание, раздел 1 | `section_1_4` |
| `form.section_2_2` | Номера документов, раздел 2 | `section_2_2` |
| `form.section_2_3` | Количество листов, раздел 2 | `section_2_3` |
| `form.section_2_4` | Примечание, раздел 2 | `section_2_4` |
| `form.section_3_2` | Номера документов, раздел 3 | `section_3_2` |
| `form.section_3_3` | Количество листов, раздел 3 | `section_3_3` |
| `form.section_3_4` | Примечание, раздел 3 | `section_3_4` |

## И_1_13_07_02

Акт технической готовности электромонтажных работ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `representatives.customer.details` | (должность, фамилия, имя, отчество) | `t1_r1_c0` |
| `representatives.general_contractor.details` | (должность, фамилия, имя, отчество) | `t1_r4_c0` |
| `representatives.installer.details` | (должность, фамилия, имя, отчество) | `t1_r7_c0` |
| `form.volume_work` | Выполненные работы, характеристики и физические объёмы | `t2_r0_c0` |
| `project.documentation.designer_name` | Проектная организация | `t3_r0_c0` |
| `form.test_fibre` | Индивидуальные испытания: проведены / не проведены | `t4_r0_c1` |

## И_1_13_07_03

Ведомость изменений и отступлений от проекта

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.readiness_date` | Дата акта технической готовности | `readiness_date` |
| `form.design_changes` | № п.п. / Состав изменений и отступлений / Причина изменений / Кем, когда согласовано, номер документа | `rows_1` |
| `form.design_changes[].number` | № п.п. | `rows_1.c1` |
| `form.design_changes[].deviations` | Состав изменений и отступлений | `rows_1.c2` |
| `form.design_changes[].value` | Причина изменений | `rows_1.c3` |
| `form.design_changes[].deviations_number_fibre` | Кем, когда согласовано, номер документа | `rows_1.c4` |
| `representatives.foreman.position` | Производитель работ (должность) | `t2_r0_c1` |
| `representatives.foreman.fio` | Производитель работ (расшифровка подписи) | `t2_r0_c5` |

## И_1_13_07_04

Ведомость электромонтажных недоделок

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.readiness_date` | Дата акта технической готовности | `readiness_date` |
| `form.defects` | № п.п. / Недоделки / Срок устранения / Кто устраняет | `rows_1` |
| `form.defects[].number` | № п.п. | `rows_1.c1` |
| `form.defects[].defects` | Недоделки | `rows_1.c2` |
| `form.defects[].date` | Срок устранения | `rows_1.c3` |
| `form.defects[].value` | Кто устраняет | `rows_1.c4` |
| `representatives.installer.position` | (должность) | `t2_r0_c0` |
| `representatives.installer.fio` | (расшифровка подписи) | `t2_r0_c4` |
| `representatives.general_contractor.position` | (должность) | `t3_r0_c0` |
| `representatives.general_contractor.fio` | (расшифровка подписи) | `t3_r0_c4` |
| `representatives.customer.position` | (должность) | `t4_r0_c0` |
| `representatives.customer.fio` | (расшифровка подписи) | `t4_r0_c4` |

## И_1_13_07_05

Ведомость смонтированного электрооборудования

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.readiness_date` | Дата акта технической готовности | `readiness_date` |
| `form.equipment` | № п.п. / Наименование электрооборудования, комплекта / Тип, марка / Заводской номер или маркировка / Кол-во / Примечание | `rows_1` |
| `form.equipment[].number` | № п.п. | `rows_1.c1` |
| `form.equipment[].equipment_completeness_fibre` | Наименование электрооборудования, комплекта | `rows_1.c2` |
| `form.equipment[].type` | Тип, марка | `rows_1.c3` |
| `form.equipment[].number_organisation_fibre` | Заводской номер или маркировка | `rows_1.c4` |
| `form.equipment[].quantity` | Кол-во | `rows_1.c5` |
| `form.equipment[].notes` | Примечание | `rows_1.c6` |
| `representatives.installer.position` | (должность) | `t2_r0_c0` |
| `representatives.installer.fio` | (расшифровка подписи) | `t2_r0_c4` |
| `representatives.customer.position` | (должность) | `t3_r0_c0` |
| `representatives.customer.fio` | (расшифровка подписи) | `t3_r0_c4` |
| `representatives.general_contractor.position` | (должность) | `t4_r0_c0` |
| `representatives.general_contractor.fio` | (расшифровка подписи) | `t4_r0_c4` |

## И_1_13_07_06

Акт готовности строительной части помещений (сооружений) к производству электромонтажных работ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.ready_date` | Дата готовности помещений | `ready_date` |
| `form.defects` | № п.п. / Помещение (сооружение) / Недоделки / Сроки устранения / Кто устраняет | `rows_7` |
| `form.defects[].number` | № п.п. | `rows_7.c1` |
| `form.defects[].location` | Помещение (сооружение) | `rows_7.c2` |
| `form.defects[].defects` | Недоделки | `rows_7.c3` |
| `form.defects[].date` | Сроки устранения | `rows_7.c4` |
| `form.defects[].value` | Кто устраняет | `rows_7.c5` |
| `representatives.builder.details` | (должность, фамилия, и., о.) | `t1_r0_c0` |
| `representatives.customer.details` | (должность, фамилия, и., о.) | `t2_r0_c0` |
| `representatives.installer.details` | (должность, фамилия, и., о.) | `t3_r0_c0` |
| `form.location_fibre` | (наименование помещений, сооружений) | `t4_r0_c0` |
| `form.number_design_documentation` | (указать проект, № чертежа) | `t5_r0_c0` |
| `form.number_design_documentation_organisation` | (наименование проектной организации, № чертежей строительных зданий) | `t6_r0_c0` |

## И_1_13_07_06а

Справка о ликвидации недоделок

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.defects_date` | Дата ведомости недоделок | `defects_date` |
| `representatives.customer.details` | (должность, фамилия, и., о.) | `t1_r0_c0` |
| `representatives.installer.details` | (должность, фамилия, и., о.) | `t2_r0_c0` |
| `form.defects_voltage_fibre` | Ликвидированные недоделки | `t3_r0_c0` |

## И_1_13_07_06б

Акт передачи смонтированного оборудования для производства пусконаладочных работ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `representatives.commissioner.details` | (должность, фамилия, и., о.) | `t1_r0_c0` |
| `representatives.installer.details` | (должность, фамилия, и., о.) | `t2_r0_c0` |
| `form.volume_work` | Выполненные работы, характеристики и физические объёмы | `t3_r0_c0` |
| `project.documentation.designer_name` | Проектная организация | `t4_r0_c0` |
| `representatives.installer.fio` | Сдали / ФИО | `t5_r0_c3` |
| `representatives.commissioner.fio` | Сдали / Приняли / ФИО | `t5_r0_c8` |

## И_1_13_07_07

Акт о приёмке и монтаже силового трансформатора

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.date_t7_r4` | Дата акта приёмки строительной части | `date_t7_r4` |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.power` | Мощность | `t1_r0_c1` |
| `form.voltage_power` | Мощность кВА, ВН | `t1_r0_c3` |
| `form.voltage` | СН | `t1_r1_c1` |
| `form.voltage_2` | СН кВ, НН | `t1_r1_c3` |
| `form.organisation_fibre` | Завод-изготовитель | `t2_r0_c1` |
| `form.organisation_type_fibre` | Завод-изготовитель , тип | `t2_r0_c3` |
| `form.number_organisation` | заводской номер | `t2_r1_c1` |
| `form.date_number_organisation` | заводской номер , дата выпуска | `t2_r1_c3` |
| `form.date_location` | дата прибытия на площадку | `t2_r2_c1` |
| `representatives.customer.details` | от предприятия заказчика (должность, фамилия, и.о.) | `t3_r0_c1` |
| `representatives.installer.details` | от электромонтажной организации (должность, фамилия, и.о.) | `t3_r2_c1` |
| `form.requirements` | трансформатор по перечню ГОСТ Р 52719-2007 (п. 6.8.2) (есть, нет) | `t4_r1_c1` |
| `form.fibre` | Отсутствуют документы (наименование документов) | `t4_r3_c1` |
| `form.completeness_fibre` | б) трансформатор (укомплектован, не полностью укомплектован | `t4_r5_c2` |
| `form.completeness` | 1. Комплектность | `t4_r7_c0` |
| `form.completeness_2` | 1. Комплектность | `t4_r9_c0` |
| `form.system` | К трансформатору не поставлены: | `t4_r11_c1` |
| `form.test` | Результаты внешнего осмотра трансформатора | `t5_r0_c0` |
| `form.oil_fibre` | (отсутствие течи масла из бака трансформатора и узлов, заполненных маслом) | `t6_r0_c0` |
| `form.number_design_documentation` | пути и др.) выполнена согласно проекта № | `t7_r1_c1` |
| `form.test_2` | (приняты, не приняты) | `t7_r2_c0` |
| `form.number_organisation_2` | монтажной организацией по акту № | `t7_r4_c1` |
| `form.description_defects_date` | Не закончено строительством (перечислить неоконченные работы) | `t8_r0_c1` |
| `form.fibre_2` | Акт о приёмке и монтаже силового трансформатора | `t8_r2_c0` |
| `form.requirements_voltage_fibre` | (наименование стандарта, ТУ, пробивное напряжение) | `t9_r0_c0` |
| `form.oil_flow_rate` | всего требуется масла (с учётом расхода на технологические нужды) | `t9_r2_c1` |
| `form.voltage_3` | имеется в трансформаторе | `t10_r0_c1` |
| `form.missing_oil_quantity_oil_quantity` | недостающее количество масла | `t10_r1_c1` |
| `form.customer_date_system` | будет поставлено заказчиком (дата) | `t10_r2_c1` |
| `form.organisations_customer_full_name` | будет поставлено заказчиком | `t10_r2_c2` |
| `form.conclusion` | Заключение о пригодности к монтажу | `t11_r0_c0` |
| `representatives.material_custodian.details` | Трансформатор принят на хранениематериально ответственным лицом (фамилия, и., о., подпись) | `t12_r4_c1` |

## И_1_13_07_09

Протокол осмотра и проверки технической готовности ЭМР по АБ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.capacity_duration` | 1. Аккумуляторная батарея | `t1_r0_c2` |
| `form.capacity` | 1. Аккумуляторная батарея ёмкость | `t1_r0_c4` |
| `form.voltage` | напряжение | `t1_r1_c1` |
| `form.voltage_structure_quantity` | напряжение В, количество элементов | `t1_r1_c3` |
| `form.design_documentation` | с проектом | `t1_r2_c1` |
| `form.design_documentation_organisation_fibre` | с проектом (наименование проектной организации, | `t1_r2_c2` |
| `form.work` | ЭЛЕКТРОМОНТАЖНЫХ РАБОТ ПО АККУМУЛЯТОРНОЙ БАТАРЕЕ | `t1_r4_c0` |
| `representatives.inspector.fio` | Осмотр и проверку произвел / (ФИО) | `t2_r0_c3` |
| `representatives.foreman.fio` | Производитель работ (мастер) / (ФИО) | `t2_r2_c3` |

## И_1_13_07_10

Ведомость замеров при контрольном разряде аккумуляторной батареи

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.battery_measurements` | Номер элемента / Напряжение, В заряжен / Плотность, г/см³ заряжен / Напряжение, В разряжен / Плотность, г/см³ Разряжен / Напряжение В / Плотность, г/см³ | `rows_2` |
| `form.battery_measurements[].structure_number` | Номер элемента | `rows_2.c1` |
| `form.battery_measurements[].voltage` | Напряжение, В заряжен | `rows_2.c2` |
| `form.battery_measurements[].density` | Плотность, г/см³ заряжен | `rows_2.c3` |
| `form.battery_measurements[].voltage_2` | Напряжение, В разряжен | `rows_2.c4` |
| `form.battery_measurements[].density_2` | Плотность, г/см³ Разряжен | `rows_2.c5` |
| `form.battery_measurements[].voltage_3` | Напряжение В | `rows_2.c6` |
| `form.battery_measurements[].density_3` | Плотность, г/см³ | `rows_2.c7` |
| `form.type` | (тип аккумулятора) | `t1_r0_c0` |
| `form.capacity` | , ёмкость | `t1_r0_c2` |
| `form.voltage_capacity_duration` | , ёмкость А.ч, напряжение | `t1_r0_c4` |
| `form.structure_quantity_fibre` | количество элементов | `t1_r2_c1` |
| `form.resistance_insulation_method` | Сопротивление изоляции аккумуляторов, замеренное по методике ПУЭ-7 п.1.8.38-1, | `t1_r3_c1` |
| `form.temperature_location` | Температура помещения | `t1_r4_c1` |
| `form.electrolyte_temperature_location` | Температура помещения °С, температура электролита | `t1_r4_c3` |
| `form.qualification` | Разряд производится | `t3_r0_c1` |
| `form.capacity_qualification_system` | Ёмкость аккумуляторной батареи (по разряду) составляет | `t4_r0_c1` |
| `form.structure_fibre` | отстающих элементов | `t4_r1_c1` |
| `form.structure_quantity_number` | отстающих элементов шт., номера отстающих элементов | `t4_r1_c3` |
| `representatives.inspector.fio` | Замеры выполнил | `measured_by` |
| `representatives.foreman.fio` | Производитель работ | `foreman` |

## И_1_13_07_11

Акт осмотра канализации из труб перед закрытием

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `representatives.installer.details` | (должность, фамилия, и.о.) | `t1_r0_c0` |
| `representatives.customer.details` | (должность, фамилия, и.о.) | `t2_r0_c0` |
| `form.materials_test` | произвела осмотр (материал) | `t2_r2_c1` |
| `form.location` | (место укладки) | `t2_r4_c0` |
| `form.pipe_number_design_documentation` | 1. Прокладка труб произведена по чертежам № | `t3_r0_c2` |
| `project.documentation.designer_name` | (наименование проектной организации) | `t3_r1_c0` |
| `form.deviations_date_number` | (при наличии отклонения указывается кем согласованы, № чертежа и дата согласования) | `t4_r0_c0` |
| `form.connection_pipe` | 3. Соединения труб выполнены | `t4_r2_c2` |
| `form.pipe` | металлических труб обеспечен (чем) | `t4_r3_c1` |

## И_1_13_07_12

Протокол испытаний давлением

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.pressure_tests` | Место установки или участок / Класс взрыво-опасной зоны / Фактическое давление, кПа / Падение давления при испытаниях, кПа / Продолжительность испытания, мин / Примечание | `rows_3` |
| `form.pressure_tests[].equipment_location_fibre` | Место установки или участок | `rows_3.c1` |
| `form.pressure_tests[].class` | Класс взрыво-опасной зоны | `rows_3.c2` |
| `form.pressure_tests[].pressure_system` | Фактическое давление, кПа | `rows_3.c3` |
| `form.pressure_tests[].pressure_drop_pressure_test` | Падение давления при испытаниях, кПа | `rows_3.c4` |
| `form.pressure_tests[].duration_test` | Продолжительность испытания, мин | `rows_3.c5` |
| `form.pressure_tests[].notes` | Примечание | `rows_3.c6` |
| `representatives.installer.details` | (должность, фамилия, и., о.) | `t1_r0_c0` |
| `representatives.customer.details` | (должность, фамилия, и., о.) | `t2_r0_c0` |
| `form.instrument_pressure_number` | Испытательное давление измерено манометром, заводской номер | `t4_r0_c1` |
| `form.accuracy_class_class` | класс точности (не более четвёртого) | `t4_r1_c1` |
| `form.class` | класса | `t4_r4_c2` |

## И_1_13_07_14а

Акт приёмки траншей, каналов, туннелей и блоков под монтаж кабелей

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `representatives.installer.details` | (должность, фамилия, и., о.) | `t1_r0_c0` |
| `representatives.customer.details` | (должность, фамилия, и., о.) | `t2_r0_c0` |
| `representatives.general_contractor.details` | (должность, фамилия, и., о.) | `t3_r0_c0` |
| `organisations.general_contractor.full_name` | выполненных (наименование генподрядной организации) | `t4_r0_c1` |
| `form.cable` | (траншеи, каналы, туннели, блоки кабельной канализации) | `t5_r0_c0` |
| `form.number_design_documentation_organisation` | (наименование организации, № чертежей рабочей документации) | `t6_r0_c0` |
| `form.description` | (перечислить) | `t7_r0_c0` |
| `form.deviations_design_documentation_organisation` | согласованы (наименование проектной организации) | `t7_r2_c1` |
| `form.fibre` | 4. Разбивка трассы траншеи (каналов, туннелей) (выполнена, не выполнена) | `t7_r4_c1` |
| `form.voltage_thickness_cross_section` | выполнена из | `t7_r7_c1` |
| `form.thickness_coating` | выполнена из толщиной слоя | `t7_r7_c3` |
| `form.pipe_materials` | трубах (материал) | `t7_r8_c1` |
| `form.depth` | глубине | `t7_r10_c1` |
| `form.depth_connection_pipe` | глубине мм, соединение и окраска труб (способ выполнения) | `t7_r10_c3` |
| `form.cable_fibre` | Обрамление и перекрытия кабельных каналов | `t8_r0_c0` |
| `form.notes` | 9. Особые замечания | `t9_r0_c1` |
| `form.design_documentation` | 8. Дренаж выполнен по проекту. | `t9_r1_c0` |

## И_1_13_07_15

Протокол осмотра и проверки сопротивления изоляции кабелей на барабане перед прокладкой

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.cable_installation` | Номер барабана / Марка кабеля, сечение, мм², напряжение, кВ / Длина кабеля, м / Завод-изготовитель / Дата выпуска / Состояние / барабана и обшивки / Состояние / наружных витков / Состояние / герметизиру-ющих заделок / Сопротивление изоляции, МОм / Заключение | `rows_1` |
| `form.cable_installation[].drum_number` | Номер барабана | `rows_1.c1` |
| `form.cable_installation[].voltage_cross_section_cable` | Марка кабеля, сечение, мм², напряжение, кВ | `rows_1.c2` |
| `form.cable_installation[].length_cable` | Длина кабеля, м | `rows_1.c3` |
| `form.cable_installation[].organisation_fibre` | Завод-изготовитель | `rows_1.c4` |
| `form.cable_installation[].date` | Дата выпуска | `rows_1.c5` |
| `form.cable_installation[].drum_condition` | Состояние / барабана и обшивки | `rows_1.c6` |
| `form.cable_installation[].condition_fibre` | Состояние / наружных витков | `rows_1.c7` |
| `form.cable_installation[].condition` | Состояние / герметизиру-ющих заделок | `rows_1.c8` |
| `form.cable_installation[].resistance_insulation_system` | Сопротивление изоляции, МОм | `rows_1.c9` |
| `form.cable_installation[].conclusion` | Заключение | `rows_1.c10` |
| `form.instrument_voltage_resistance` | Сопротивление изоляции замерено мегаомметром на напряжение 2500 В типа | `t2_r0_c1` |
| `form.number_organisation` | заводской № | `t2_r1_c1` |
| `representatives.inspector.fio` | произвел / (ФИО) | `t3_r1_c3` |
| `representatives.foreman.fio` | произвел / / (мастер) / (ФИО) | `t3_r1_c9` |
| `representatives.customer.fio` | Представитель заказчика / (ФИО) | `t4_r0_c3` |

## И_1_13_07_16

Протокол прогрева кабелей на барабане перед прокладкой при низких температурах

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.cable_joints` | Номер барабана / Марка кабеля, сечение, мм², напряжение, кВ / Длина кабеля, м / Прогрев кабелей внутри обогреваемых помещений / температура в помещении, °С / Прогрев кабелей внутри обогреваемых помещений / продолжительность прогрева, ч / Прогрев кабелей электрическим током, А / температура внешних витков кабеля при температуре наружного воздуха / -10°С / Прогрев кабелей электрическим током, А / температура внешних витков кабеля при температуре наружного воздуха / ниже -10°С | `rows_1` |
| `form.cable_joints[].drum_number` | Номер барабана | `rows_1.c1` |
| `form.cable_joints[].voltage_cross_section_cable` | Марка кабеля, сечение, мм², напряжение, кВ | `rows_1.c2` |
| `form.cable_joints[].length_cable` | Длина кабеля, м | `rows_1.c3` |
| `form.cable_joints[].temperature_voltage_cable` | Прогрев кабелей внутри обогреваемых помещений / температура в помещении, °С | `rows_1.c4` |
| `form.cable_joints[].cable_heating_duration` | Прогрев кабелей внутри обогреваемых помещений / продолжительность прогрева, ч | `rows_1.c5` |
| `form.cable_joints[].temperature_cable_heating` | Прогрев кабелей электрическим током, А / температура внешних витков кабеля при температуре наружного воздуха / -10°С | `rows_1.c6` |
| `form.cable_joints[].temperature_cable_heating_2` | Прогрев кабелей электрическим током, А / температура внешних витков кабеля при температуре наружного воздуха / ниже -10°С | `rows_1.c7` |
| `representatives.worker.fio` | Прогрев произвёл | `heated_by` |
| `representatives.foreman.fio` | Производитель работ | `foreman` |

## И_1_13_07_17

Акт осмотра кабельной канализации в траншеях и каналах перед закрытием

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `representatives.installer.details` | (должность, фамилия, и., о.) | `t1_r0_c0` |
| `representatives.customer.details` | (должность, фамилия, и., о.) | `t2_r0_c0` |
| `representatives.general_contractor.details` | (должность, фамилия, и., о.) | `t3_r0_c0` |
| `form.voltage_cable_test` | произвела осмотр кабельной канализации в (траншее, канале) | `t3_r2_c1` |
| `form.cable_number_design_documentation` | (наименование проектной организации, № чертежей и кабельных журналов) | `t4_r0_c0` |
| `form.deviations_number_design_documentation` | 2. Отступления от проекта согласованы и нанесены на чертежи № | `t4_r2_c1` |
| `form.cable_quantity_fibre` | 4. На кабелях смонтировано (количество) | `t5_r0_c1` |
| `form.cable_materials_coating` | 5. Произведена подсыпка кабельных линий слоем (материал подсыпки) | `t5_r3_c1` |
| `form.notes_cable` | (указать дополнительные места защиты кабелей при наличии) | `t5_r6_c0` |
| `form.voltage_cross_section_cable` | защищены (указать, чем защищены) | `t5_r9_c1` |
| `form.features` | Другие особенности, отмеченные комиссией | `t6_r0_c0` |

## И_1_13_07_18

Журнал прокладки кабелей

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.foundations` | Дата прокладки / Наименование и номер кабеля по кабельному журналу или исполнительной схеме / Марка кабеля, напряжение, кВ, сечение, мм² / Общая длина линии, м / Номер барабана и длина кабеля на каждом, м / Коли- чество соеди- нительных муфт на линии / Температура окружаю- щего воздуха при прокладке, °С / Способ подогрева кабеля и продолжи- тельность прокладки, ч / Фамилия и подпись ответст- венного за прокладку | `rows_1` |
| `form.foundations[].date` | Дата прокладки | `rows_1.c1` |
| `form.foundations[].cable_number_fibre` | Наименование и номер кабеля по кабельному журналу или исполнительной схеме | `rows_1.c2` |
| `form.foundations[].voltage_cross_section_cable` | Марка кабеля, напряжение, кВ, сечение, мм² | `rows_1.c3` |
| `form.foundations[].length` | Общая длина линии, м | `rows_1.c4` |
| `form.foundations[].length_drum_cable` | Номер барабана и длина кабеля на каждом, м | `rows_1.c5` |
| `form.foundations[].joint` | Коли- чество соеди- нительных муфт на линии | `rows_1.c6` |
| `form.foundations[].temperature` | Температура окружаю- щего воздуха при прокладке, °С | `rows_1.c7` |
| `form.foundations[].cable_heating_duration` | Способ подогрева кабеля и продолжи- тельность прокладки, ч | `rows_1.c8` |
| `form.foundations[].representative` | Фамилия и подпись ответст- венного за прокладку | `rows_1.c9` |
| `representatives.foreman.fio` | Производитель работ / (ФИО) | `t2_r0_c3` |

## И_1_13_07_19

Журнал монтажа кабельных муфт напряжением выше 1000 В

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.connections` | Кабель / Номер по кабельному журналу / Кабель / Марка, сечение, мм², напряжение, кВ / Муфта / Номер / Муфта / Тип, размер / Муфта / Дата монтажа / Фамилия и подпись исполнителя | `rows_1` |
| `form.connections[].cable_number` | Кабель / Номер по кабельному журналу | `rows_1.c1` |
| `form.connections[].voltage_cross_section_cable` | Кабель / Марка, сечение, мм², напряжение, кВ | `rows_1.c2` |
| `form.connections[].joint_number` | Муфта / Номер | `rows_1.c3` |
| `form.connections[].dimensions_joint_type` | Муфта / Тип, размер | `rows_1.c4` |
| `form.connections[].joint_date` | Муфта / Дата монтажа | `rows_1.c5` |
| `form.connections[].representative` | Фамилия и подпись исполнителя | `rows_1.c6` |
| `representatives.foreman.fio` | Производитель работ (мастер) / (ФИО) | `t2_r0_c3` |

## И_1_13_07_20

Акт готовности монолитного бетонного фундамента под опору ВЛ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.support_system` | ПОД ОПОРУ ВЛ | `t1_r0_c1` |
| `form.support_number` | Опора № | `t2_r0_c1` |
| `form.support_number_fibre` | Опора № , наименование опоры | `t2_r0_c3` |
| `form.support_number_type` | Опора № , наименование опоры , тип | `t2_r0_c5` |
| `representatives.customer.details` | (должность, фамилия, и., о.) | `t3_r0_c0` |
| `representatives.builder.details` | (должность, фамилия, и., о.) | `t4_r0_c0` |
| `representatives.installer.details` | (должность, фамилия, и., о.) | `t5_r0_c0` |
| `form.foundation_design_documentation` | 1. Фундамент выполнен согласно проекту по чертежам | `t6_r0_c2` |
| `form.concrete_type_system` | 2. Согласно предъявленным протоколам марка бетона составляет | `t6_r2_c2` |
| `form.materials_coating_quantity` | (материал покрытия, число слоев) | `t7_r0_c0` |
| `form.bolts_number_design_documentation` | 3. Анкерные болты (закладные части) установлены по чертежам № | `t7_r2_c2` |
| `form.deviations_design_documentation` | 5. Отступления от проекта (существо отступления) | `t8_r0_c2` |
| `form.representatives_customer_details` | согласованы с заказчиком в лице (должность, фамилия, и., о.) | `t8_r2_c1` |
| `representatives.designer.details` | и проектной организацией в лице (должность, фамилия, и., о.) | `t8_r4_c1` |
| `form.number_design_documentation` | (номера чертежей) | `t9_r0_c0` |

## И_1_13_07_21

Акт готовности сборных железобетонных фундаментов под установку опор ВЛ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.date_t10_r1` | Дата повторного предъявления фундаментов | `date_t10_r1` |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.wire_measurements` | Номер опоры / Наимено-вание и тип опоры / Тип фундам-мента / Завод-изгото-витель сборного ЖБ, паспорт, марка / № чертежа фунда-мента / Наличие гидро-изоляция, материал / Дата устрой-ства фунда-мента / Установка на опоры разре-шается, подпись произво-дителя работ / Приме-чание | `rows_11` |
| `form.wire_measurements[].support_number` | Номер опоры | `rows_11.c1` |
| `form.wire_measurements[].support_type` | Наимено-вание и тип опоры | `rows_11.c2` |
| `form.wire_measurements[].type` | Тип фундам-мента | `rows_11.c3` |
| `form.wire_measurements[].passport_organisation_type` | Завод-изгото-витель сборного ЖБ, паспорт, марка | `rows_11.c4` |
| `form.wire_measurements[].number_design_documentation` | № чертежа фунда-мента | `rows_11.c5` |
| `form.wire_measurements[].insulation_materials` | Наличие гидро-изоляция, материал | `rows_11.c6` |
| `form.wire_measurements[].date` | Дата устрой-ства фунда-мента | `rows_11.c7` |
| `form.wire_measurements[].support_equipment_representative` | Установка на опоры разре-шается, подпись произво-дителя работ | `rows_11.c8` |
| `form.wire_measurements[].value` | Приме-чание | `rows_11.c9` |
| `form.foundation_support_equipment` | ФУНДАМЕНТОВ ПОД УСТАНОВКУ ОПОР ВЛ | `t1_r0_c1` |
| `representatives.customer.details` | (должность, фамилия, и., о.) | `t2_r0_c0` |
| `representatives.builder.details` | (должность, фамилия, и., о.) | `t3_r0_c0` |
| `representatives.installer.details` | (должность, фамилия, и., о.) | `t4_r0_c0` |
| `form.foundation_concrete_system` | рассмотрела техническую документацию на сборные железобетонные фундаменты ВЛ | `t5_r0_c0` |
| `form.support_equipment_quantity` | 1. Предъявлено под установку опор ВЛ законченные устройством (число) | `t6_r0_c2` |
| `form.support_quantity` | Из них под опоры: промежуточные (число) | `t7_r0_c1` |
| `form.bolts_support_quantity` | Из них под опоры: промежуточные , анкерные (число) | `t7_r0_c3` |
| `form.quantity_fibre` | угловые (число) | `t7_r2_c1` |
| `form.quantity_fibre_2` | угловые , другие (число) | `t7_r2_c3` |
| `project.documentation.designer_name` | (наименование проектной организации) | `t8_r0_c0` |
| `form.number_design_documentation_fibre` | по чертежам (наименование и номера чертежей) | `t8_r2_c1` |
| `form.deviations_design_documentation` | 4. Отступления от проекта (существо отступления) | `t9_r0_c2` |
| `form.representatives_customer_details` | согласованы с заказчиком в лице (должность, фамилия, и., о.) | `t9_r2_c1` |
| `representatives.designer.details` | и проектной организацией в лице (должность, фамилия, и., о.) | `t9_r4_c1` |
| `form.foundation_concrete_support` | 5. Сборные железобетонные фундаменты для опор (номера опор) | `t9_r6_c2` |
| `form.test` | комиссией не приняты по причине (указать причину) | `t9_r8_c1` |
| `form.foundation_date_system` | Срок переделки (доработки) отбракованных фундаментов и повторного их предъявления | `t10_r0_c0` |

## И_1_13_07_22

Паспорт воздушной линии электропередачи

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.tensioning` | Номер опор и пролетов, на которых смонтированы соединения / Тип соединительного напряженного зажима / Способ монтажа соединения / Исполнитель / Фамилия, И.О. / Исполнитель / Подпись | `rows_3` |
| `form.tensioning[].support_connection_number` | Номер опор и пролетов, на которых смонтированы соединения | `rows_3.c1` |
| `form.tensioning[].type` | Тип соединительного напряженного зажима | `rows_3.c2` |
| `form.tensioning[].connection_method` | Способ монтажа соединения | `rows_3.c3` |
| `form.tensioning[].representative` | Исполнитель / Фамилия, И.О. | `rows_3.c4` |
| `form.tensioning[].representative_2` | Исполнитель / Подпись | `rows_3.c5` |
| `form.support` | 1. Монтаж опор воздушной линии электропередачи | `t1_r3_c0` |
| `form.quantity_system_fibre` | Промежуточные / Установлено на ВЛ, шт. | `t1_r4_c1` |
| `form.support_number_design_documentation` | Промежуточные / Тип опоры (номер чертежа для нетиповых) | `t1_r4_c2` |
| `form.support_materials` | Промежуточные / Материал опоры | `t1_r4_c3` |
| `form.notes_support_coating` | Промежуточные / Защитное покрытие дополнительно к заводскому (окраска, антисептик), к-во опор | `t1_r4_c4` |
| `form.bolts_quantity_system` | Анкерные / Установлено на ВЛ, шт. | `t1_r5_c1` |
| `form.bolts_support_number` | Анкерные / Тип опоры (номер чертежа для нетиповых) | `t1_r5_c2` |
| `form.bolts_support_materials` | Анкерные / Материал опоры | `t1_r5_c3` |
| `form.notes_bolts_support` | Анкерные / Защитное покрытие дополнительно к заводскому (окраска, антисептик), к-во опор | `t1_r5_c4` |
| `form.quantity_system_fibre_2` | Угловые / Установлено на ВЛ, шт. | `t1_r6_c1` |
| `form.support_number_design_documentation_2` | Угловые / Тип опоры (номер чертежа для нетиповых) | `t1_r6_c2` |
| `form.support_materials_fibre` | Угловые / Материал опоры | `t1_r6_c3` |
| `form.notes_support_coating_2` | Угловые / Защитное покрытие дополнительно к заводскому (окраска, антисептик), к-во опор | `t1_r6_c4` |
| `form.quantity_system_fibre_3` | Другие / Установлено на ВЛ, шт. | `t1_r7_c1` |
| `form.support_number_design_documentation_3` | Другие / Тип опоры (номер чертежа для нетиповых) | `t1_r7_c2` |
| `form.support_materials_2` | Другие / Материал опоры | `t1_r7_c3` |
| `form.notes_support_coating_3` | Другие / Защитное покрытие дополнительно к заводскому (окраска, антисептик), к-во опор | `t1_r7_c4` |
| `form.quantity_system_fibre_4` | Всего: / Установлено на ВЛ, шт. | `t1_r8_c1` |
| `form.support_number_design_documentation_4` | Всего: / Тип опоры (номер чертежа для нетиповых) | `t1_r8_c2` |
| `form.support_materials_3` | Всего: / Материал опоры | `t1_r8_c3` |
| `form.notes_support_coating_4` | Всего: / Защитное покрытие дополнительно к заводскому (окраска, антисептик), к-во опор | `t1_r8_c4` |
| `form.system` | На ВЛ | `t2_r0_c1` |
| `form.voltage_cable_system` | На ВЛ кВ смонтирован провод марки | `t2_r0_c3` |
| `form.cross_section` | сечением | `t2_r1_c1` |
| `form.voltage_cross_section_quantity` | сечением мм², в общем количестве | `t2_r1_c3` |
| `form.length` | марки | `t2_r2_c1` |
| `form.length_2` | марки протяжённостью | `t2_r2_c3` |
| `form.system_2` | На ВЛ | `t4_r0_c1` |
| `form.pipe_qualification_type` | а) трубчатые разрядники типа | `t4_r1_c2` |
| `form.description_support_number` | на опорах (перечислить номера опор) | `t4_r2_c1` |
| `form.type` | б) разъединители типа | `t5_r0_c2` |
| `form.support_number` | на опорах (номера опор) | `t5_r1_c1` |
| `form.earthing_support_system` | Монтаж заземляющих устройств опор ВЛ | `t6_r0_c1` |
| `form.conclusion` | Заключение | `t7_r0_c0` |
| `representatives.foreman.fio` | Производитель работ / (ФИО) | `t8_r0_c3` |

## И_1_13_07_23

Акт замеров в натуре габаритов от проводов ВЛ до пересекаемого объекта

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.cross_section_representative_test` | Мы, нижеподписавшиеся, произвели осмотр и измерения пересечения ВЛ | `t1_r0_c1` |
| `form.system_fibre` | (наименование ВЛ) | `t1_r1_c0` |
| `form.location_fibre` | с объектом (наименование объекта) | `t1_r3_c1` |
| `form.cross_section_design_documentation` | 1. Пересечение выполнено согласно чертежу | `t2_r0_c2` |
| `form.quantity_system_fibre` | 2. На пересекающей ВЛ смонтированы (число) | `t2_r1_c2` |
| `form.cable_system_fibre` | 2. На пересекающей ВЛ смонтированы проводов марки | `t2_r1_c4` |
| `form.cross_section_support_number` | 3. Ограничивающие объект пересечения опоры ВЛ № | `t2_r3_c2` |
| `form.location_system_fibre` | установлены на пикетах. | `t2_r4_c1` |
| `form.system` | составляет | `t3_r1_c1` |
| `form.cable_system_fibre_2` | 5. Расстояние от ближайшего провода ВЛ (до пересекаемого | `t3_r2_c2` |
| `form.voltage_cable_location` | Акт замеров в натуре габаритов от проводов ВЛ до пересекаемого объекта | `t3_r4_c0` |
| `form.system_2` | составляет | `t3_r6_c1` |
| `form.temperature_medium` | 6. Измерения выполнялись при температуре окружающей среды | `t3_r7_c2` |
| `representatives.crossing_owner.details` | Представитель объекта пересечения (наименование организации, должность, фамилия, и, о, подпись) | `t4_r0_c1` |
| `representatives.customer.details` | Представитель заказчика (должность фамилия, и, о, подпись) | `t5_r0_c1` |
| `representatives.installer.details` | Представитель монтажной организации (должность фамилия, и, о, подпись) | `t6_r0_c1` |

## И_1_13_07_24

Паспорт заземляющего устройства

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `form.division` | Подразделение | `division` |
| `object.name` | Объект | `object_name` |
| `form.site` | Участок | `site` |
| `document.date.day` | Дата подписания | `day` |
| `document.date.month` | Дата подписания | `month` |
| `document.date.year` | Дата подписания | `year` |
| `form.earthing` | № п.п. / Элемент заземляющих устройств / Параметры элементов заземляющего устройства / материал / Параметры элементов заземляющего устройства / профиль / Параметры элементов заземляющего устройства / размеры, мм / Параметры элементов заземляющего устройства / кол-во, шт. / Параметры элементов заземляющего устройства / глубина заложения, м / Примечание | `rows_3` |
| `form.earthing[].number` | № п.п. | `rows_3.c1` |
| `form.earthing[].earthing_structure` | Элемент заземляющих устройств | `rows_3.c2` |
| `form.earthing[].earthing_materials_structure` | Параметры элементов заземляющего устройства / материал | `rows_3.c3` |
| `form.earthing[].earthing_structure_fibre` | Параметры элементов заземляющего устройства / профиль | `rows_3.c4` |
| `form.earthing[].dimensions_earthing_structure` | Параметры элементов заземляющего устройства / размеры, мм | `rows_3.c5` |
| `form.earthing[].earthing_structure_quantity` | Параметры элементов заземляющего устройства / кол-во, шт. | `rows_3.c6` |
| `form.earthing[].earthing_depth_structure` | Параметры элементов заземляющего устройства / глубина заложения, м | `rows_3.c7` |
| `form.earthing[].notes` | Примечание | `rows_3.c8` |
| `representatives.installer.details` | (должность, фамилия, и., о.) | `t1_r1_c0` |
| `representatives.customer.details` | (должность, фамилия, и., о.) | `t1_r4_c0` |
| `form.description` | (название) | `t2_r0_c0` |
| `form.design_documentation_organisation_work` | разработанным (проектная организация) | `t2_r2_c1` |
| `form.number_design_documentation` | по чертежам (номер) | `t2_r4_c1` |
| `form.deviations_design_documentation` | 2. Отступления от проекта | `t2_r6_c1` |
| `form.earthing_voltage_design_documentation` | 1. Заземляющее устройство выполнено в соответствии с проектом | `t2_r7_c0` |
| `form.representative_deviations_date` | согласованы с (организация, должность, фамилия, и, о, дата) | `t2_r8_c1` |
| `form.voltage_number_design_documentation` | и внесены в чертежи (номер) | `t2_r10_c1` |
| `form.earthing_connection_structure` | Характер соединений элементов заземления | `t4_r0_c0` |
| `form.defects` | 5. Выделены дефекты | `t5_r0_c1` |
| `form.earthing_passport` | Паспорт заземляющего устройства | `t5_r1_c0` |

## И_1_13_07_25

Обложка к комплекту технической документации по сдаче-приёмке электромонтажных работ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `organisations.installer.full_name` | Электромонтажная организация | `installer_org` |
| `form.division` | (Подразделение) | `t0_r2_c0` |
| `object.name` | Объект | `object_name` |
| `organisations.customer.full_name` | Заказчик | `customer_org` |
| `project.city` | Город | `city` |
| `form.year` | Год комплекта | `year` |

## МИНСТРОЙ_344_АОГРО

Акт освидетельствования геодезической разбивочной основы

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `object.name` | Наименование объекта | `object_name` |
| `object.address` | Почтовый или строительный адрес объекта | `object_address` |
| `organisations.customer.full_name` | customer: наименование | `customer_name` |
| `organisations.customer.ogrn` | customer: ОГРН | `customer_ogrn` |
| `organisations.customer.inn` | customer: ИНН | `customer_inn` |
| `organisations.customer.address` | customer: адрес | `customer_address` |
| `organisations.customer.phone` | customer: телефон | `customer_phone` |
| `organisations.customer.sro_info` | customer: сведения СРО | `customer_sro` |
| `form.customer_individual` | Индивидуальные реквизиты физического лица/ИП при необходимости | `customer_individual` |
| `organisations.builder.full_name` | builder_org: наименование | `builder_org_name` |
| `organisations.builder.ogrn` | builder_org: ОГРН | `builder_org_ogrn` |
| `organisations.builder.inn` | builder_org: ИНН | `builder_org_inn` |
| `organisations.builder.address` | builder_org: адрес | `builder_org_address` |
| `organisations.builder.phone` | builder_org: телефон | `builder_org_phone` |
| `organisations.builder.sro_info` | builder_org: сведения СРО | `builder_org_sro` |
| `organisations.designer.full_name` | designer_org: наименование | `designer_org_name` |
| `organisations.designer.ogrn` | designer_org: ОГРН | `designer_org_ogrn` |
| `organisations.designer.inn` | designer_org: ИНН | `designer_org_inn` |
| `organisations.designer.address` | designer_org: адрес | `designer_org_address` |
| `organisations.designer.phone` | designer_org: телефон | `designer_org_phone` |
| `organisations.designer.sro_info` | designer_org: сведения СРО | `designer_org_sro` |
| `document.number` | Номер акта | `act_num` |
| `document.date.day` | День подписания | `signed_day` |
| `document.date.month` | Месяц подписания | `signed_month` |
| `document.date.year` | Год подписания | `signed_year` |
| `representatives.customer_control.details` | Строительный контроль застройщика/заказчика | `customer_control_details` |
| `representatives.customer_control.nrs_id` | Строительный контроль застройщика/заказчика: номер НРС | `customer_control_nrs` |
| `representatives.customer_control.organisation.full_name` | control_org: наименование | `control_org_name` |
| `representatives.customer_control.organisation.ogrn` | control_org: ОГРН | `control_org_ogrn` |
| `representatives.customer_control.organisation.inn` | control_org: ИНН | `control_org_inn` |
| `representatives.customer_control.organisation.address` | control_org: адрес | `control_org_address` |
| `representatives.customer_control.organisation.phone` | control_org: телефон | `control_org_phone` |
| `representatives.builder.details` | Лицо, осуществляющее строительство | `builder_details` |
| `representatives.builder_control.details` | Строительный контроль лица, осуществляющего строительство | `builder_control_details` |
| `representatives.builder_control.nrs_id` | Строительный контроль лица, осуществляющего строительство: номер НРС | `builder_control_nrs` |
| `representatives.designer.details` | Представитель проектировщика | `designer_details` |
| `representatives.designer.organisation.full_name` | designer_employer: наименование | `designer_employer_name` |
| `representatives.designer.organisation.ogrn` | designer_employer: ОГРН | `designer_employer_ogrn` |
| `representatives.designer.organisation.inn` | designer_employer: ИНН | `designer_employer_inn` |
| `representatives.designer.organisation.address` | designer_employer: адрес | `designer_employer_address` |
| `representatives.designer.organisation.phone` | designer_employer: телефон | `designer_employer_phone` |
| `representatives.work_performer.details` | Представитель фактического исполнителя работ | `work_performer_details` |
| `representatives.work_performer.organisation.full_name` | work_performer_employer: наименование | `work_performer_employer_name` |
| `representatives.work_performer.organisation.ogrn` | work_performer_employer: ОГРН | `work_performer_employer_ogrn` |
| `representatives.work_performer.organisation.inn` | work_performer_employer: ИНН | `work_performer_employer_inn` |
| `representatives.work_performer.organisation.address` | work_performer_employer: адрес | `work_performer_employer_address` |
| `representatives.work_performer.organisation.phone` | work_performer_employer: телефон | `work_performer_employer_phone` |
| `form.object_name` | Наименование объекта | `examined_object` |
| `form.design_compliance` | Чертежи, проектировщик, регламенты и нормативные акты | `design_compliance` |
| `form.additional_info` | Дополнительные сведения | `additional_info` |
| `form.copies_count` | Количество экземпляров | `copies_count` |
| `form.attachments` | Приложения: чертежи, схемы, ведомости | `attachments` |
| `representatives.customer_control.fio_short` | Строительный контроль застройщика/заказчика: подпись/ФИО | `customer_control_signature` |
| `representatives.builder.fio_short` | Лицо, осуществляющее строительство: подпись/ФИО | `builder_signature` |
| `representatives.builder_control.fio_short` | Строительный контроль лица, осуществляющего строительство: подпись/ФИО | `builder_control_signature` |
| `representatives.designer.fio_short` | Представитель проектировщика: подпись/ФИО | `designer_signature` |
| `representatives.work_performer.fio_short` | Представитель фактического исполнителя работ: подпись/ФИО | `work_performer_signature` |

## МИНСТРОЙ_344_АООК

Акт освидетельствования ответственных конструкций

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `object.name` | Наименование объекта | `object_name` |
| `object.address` | Почтовый или строительный адрес объекта | `object_address` |
| `organisations.customer.full_name` | customer: наименование | `customer_name` |
| `organisations.customer.ogrn` | customer: ОГРН | `customer_ogrn` |
| `organisations.customer.inn` | customer: ИНН | `customer_inn` |
| `organisations.customer.address` | customer: адрес | `customer_address` |
| `organisations.customer.phone` | customer: телефон | `customer_phone` |
| `organisations.customer.sro_info` | customer: сведения СРО | `customer_sro` |
| `form.customer_individual` | Индивидуальные реквизиты физического лица/ИП при необходимости | `customer_individual` |
| `organisations.builder.full_name` | builder_org: наименование | `builder_org_name` |
| `organisations.builder.ogrn` | builder_org: ОГРН | `builder_org_ogrn` |
| `organisations.builder.inn` | builder_org: ИНН | `builder_org_inn` |
| `organisations.builder.address` | builder_org: адрес | `builder_org_address` |
| `organisations.builder.phone` | builder_org: телефон | `builder_org_phone` |
| `organisations.builder.sro_info` | builder_org: сведения СРО | `builder_org_sro` |
| `organisations.designer.full_name` | designer_org: наименование | `designer_org_name` |
| `organisations.designer.ogrn` | designer_org: ОГРН | `designer_org_ogrn` |
| `organisations.designer.inn` | designer_org: ИНН | `designer_org_inn` |
| `organisations.designer.address` | designer_org: адрес | `designer_org_address` |
| `organisations.designer.phone` | designer_org: телефон | `designer_org_phone` |
| `organisations.designer.sro_info` | designer_org: сведения СРО | `designer_org_sro` |
| `document.number` | Номер акта | `act_num` |
| `document.date.day` | День подписания | `signed_day` |
| `document.date.month` | Месяц подписания | `signed_month` |
| `document.date.year` | Год подписания | `signed_year` |
| `representatives.customer_control.details` | Строительный контроль застройщика/заказчика | `customer_control_details` |
| `representatives.customer_control.nrs_id` | Строительный контроль застройщика/заказчика: номер НРС | `customer_control_nrs` |
| `representatives.customer_control.organisation.full_name` | control_org: наименование | `control_org_name` |
| `representatives.customer_control.organisation.ogrn` | control_org: ОГРН | `control_org_ogrn` |
| `representatives.customer_control.organisation.inn` | control_org: ИНН | `control_org_inn` |
| `representatives.customer_control.organisation.address` | control_org: адрес | `control_org_address` |
| `representatives.customer_control.organisation.phone` | control_org: телефон | `control_org_phone` |
| `representatives.builder.details` | Лицо, осуществляющее строительство | `builder_details` |
| `representatives.builder_control.details` | Строительный контроль лица, осуществляющего строительство | `builder_control_details` |
| `representatives.builder_control.nrs_id` | Строительный контроль лица, осуществляющего строительство: номер НРС | `builder_control_nrs` |
| `representatives.designer.details` | Представитель проектировщика | `designer_details` |
| `representatives.designer.organisation.full_name` | designer_employer: наименование | `designer_employer_name` |
| `representatives.designer.organisation.ogrn` | designer_employer: ОГРН | `designer_employer_ogrn` |
| `representatives.designer.organisation.inn` | designer_employer: ИНН | `designer_employer_inn` |
| `representatives.designer.organisation.address` | designer_employer: адрес | `designer_employer_address` |
| `representatives.designer.organisation.phone` | designer_employer: телефон | `designer_employer_phone` |
| `representatives.work_performer.details` | Представитель фактического исполнителя работ | `work_performer_details` |
| `representatives.work_performer.organisation.full_name` | work_performer_employer: наименование | `work_performer_employer_name` |
| `representatives.work_performer.organisation.ogrn` | work_performer_employer: ОГРН | `work_performer_employer_ogrn` |
| `representatives.work_performer.organisation.inn` | work_performer_employer: ИНН | `work_performer_employer_inn` |
| `representatives.work_performer.organisation.address` | work_performer_employer: адрес | `work_performer_employer_address` |
| `representatives.work_performer.organisation.phone` | work_performer_employer: телефон | `work_performer_employer_phone` |
| `organisations.work_performer.full_name` | Фактический исполнитель работ/конструкций | `actual_performer` |
| `form.construction_description` | Перечень и характеристика конструкций | `construction_description` |
| `project.documentation.description` | Чертежи, проектная/рабочая документация, проектировщик | `design_documents` |
| `form.hidden_works_acts` | Скрытые работы, даты и номера актов | `hidden_works_acts` |
| `form.materials_quality` | Применённые материалы и документы качества | `materials_quality` |
| `form.structure` | Исполнительные геодезические схемы | `geodetic_schemes` |
| `form.control_results` | Экспертизы, обследования и испытания | `control_results` |
| `form.test_reports` | Документы проведённых испытаний и опробований | `test_reports` |
| `form.compliance_basis` | Технические регламенты и разделы документации | `compliance_basis` |
| `form.decision` | Решение по пункту 9: выбранные подпункты, нагрузка, условия и последующие работы | `decision` |
| `form.additional_info` | Дополнительные сведения | `additional_info` |
| `form.copies_count` | Количество экземпляров | `copies_count` |
| `form.attachments` | Приложения | `attachments` |
| `form.work_start` | Индивидуальная дата начала работ | `work_start` |
| `form.work_end` | Индивидуальная дата окончания работ | `work_end` |
| `representatives.customer_control.fio_short` | Строительный контроль застройщика/заказчика: подпись/ФИО | `customer_control_signature` |
| `representatives.builder.fio_short` | Лицо, осуществляющее строительство: подпись/ФИО | `builder_signature` |
| `representatives.builder_control.fio_short` | Строительный контроль лица, осуществляющего строительство: подпись/ФИО | `builder_control_signature` |
| `representatives.designer.fio_short` | Представитель проектировщика: подпись/ФИО | `designer_signature` |
| `representatives.work_performer.fio_short` | Представитель фактического исполнителя работ: подпись/ФИО | `work_performer_signature` |

## МИНСТРОЙ_344_АОСР

Акт освидетельствования скрытых работ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `object.name` | Наименование объекта | `object_name` |
| `object.address` | Почтовый или строительный адрес объекта | `object_address` |
| `organisations.customer.full_name` | customer: наименование | `customer_name` |
| `organisations.customer.ogrn` | customer: ОГРН | `customer_ogrn` |
| `organisations.customer.inn` | customer: ИНН | `customer_inn` |
| `organisations.customer.address` | customer: адрес | `customer_address` |
| `organisations.customer.phone` | customer: телефон | `customer_phone` |
| `organisations.customer.sro_info` | customer: сведения СРО | `customer_sro` |
| `form.customer_individual` | Индивидуальные реквизиты физического лица/ИП при необходимости | `customer_individual` |
| `organisations.builder.full_name` | builder_org: наименование | `builder_org_name` |
| `organisations.builder.ogrn` | builder_org: ОГРН | `builder_org_ogrn` |
| `organisations.builder.inn` | builder_org: ИНН | `builder_org_inn` |
| `organisations.builder.address` | builder_org: адрес | `builder_org_address` |
| `organisations.builder.phone` | builder_org: телефон | `builder_org_phone` |
| `organisations.builder.sro_info` | builder_org: сведения СРО | `builder_org_sro` |
| `organisations.designer.full_name` | designer_org: наименование | `designer_org_name` |
| `organisations.designer.ogrn` | designer_org: ОГРН | `designer_org_ogrn` |
| `organisations.designer.inn` | designer_org: ИНН | `designer_org_inn` |
| `organisations.designer.address` | designer_org: адрес | `designer_org_address` |
| `organisations.designer.phone` | designer_org: телефон | `designer_org_phone` |
| `organisations.designer.sro_info` | designer_org: сведения СРО | `designer_org_sro` |
| `document.number` | Номер акта | `act_num` |
| `document.date.day` | День подписания | `signed_day` |
| `document.date.month` | Месяц подписания | `signed_month` |
| `document.date.year` | Год подписания | `signed_year` |
| `representatives.customer_control.details` | Строительный контроль застройщика/заказчика | `customer_control_details` |
| `representatives.customer_control.nrs_id` | Строительный контроль застройщика/заказчика: номер НРС | `customer_control_nrs` |
| `representatives.customer_control.organisation.full_name` | control_org: наименование | `control_org_name` |
| `representatives.customer_control.organisation.ogrn` | control_org: ОГРН | `control_org_ogrn` |
| `representatives.customer_control.organisation.inn` | control_org: ИНН | `control_org_inn` |
| `representatives.customer_control.organisation.address` | control_org: адрес | `control_org_address` |
| `representatives.customer_control.organisation.phone` | control_org: телефон | `control_org_phone` |
| `representatives.builder.details` | Лицо, осуществляющее строительство | `builder_details` |
| `representatives.builder_control.details` | Строительный контроль лица, осуществляющего строительство | `builder_control_details` |
| `representatives.builder_control.nrs_id` | Строительный контроль лица, осуществляющего строительство: номер НРС | `builder_control_nrs` |
| `representatives.designer.details` | Представитель проектировщика | `designer_details` |
| `representatives.designer.organisation.full_name` | designer_employer: наименование | `designer_employer_name` |
| `representatives.designer.organisation.ogrn` | designer_employer: ОГРН | `designer_employer_ogrn` |
| `representatives.designer.organisation.inn` | designer_employer: ИНН | `designer_employer_inn` |
| `representatives.designer.organisation.address` | designer_employer: адрес | `designer_employer_address` |
| `representatives.designer.organisation.phone` | designer_employer: телефон | `designer_employer_phone` |
| `representatives.work_performer.details` | Представитель фактического исполнителя работ | `work_performer_details` |
| `representatives.work_performer.organisation.full_name` | work_performer_employer: наименование | `work_performer_employer_name` |
| `representatives.work_performer.organisation.ogrn` | work_performer_employer: ОГРН | `work_performer_employer_ogrn` |
| `representatives.work_performer.organisation.inn` | work_performer_employer: ИНН | `work_performer_employer_inn` |
| `representatives.work_performer.organisation.address` | work_performer_employer: адрес | `work_performer_employer_address` |
| `representatives.work_performer.organisation.phone` | work_performer_employer: телефон | `work_performer_employer_phone` |
| `organisations.work_performer.full_name` | Фактический исполнитель работ/конструкций | `actual_performer` |
| `form.work_description` | Наименование скрытых работ | `work_description` |
| `project.documentation.description` | Чертежи, проектная/рабочая документация, проектировщик | `design_documents` |
| `form.materials_quality` | Применённые материалы и документы качества | `materials_quality` |
| `form.compliance_documents` | Исполнительные схемы, экспертизы, обследования, испытания | `compliance_documents` |
| `form.compliance_basis` | Технические регламенты, нормативные акты и разделы документации | `compliance_basis` |
| `form.subsequent_works` | Разрешённые последующие работы | `subsequent_works` |
| `form.additional_info` | Дополнительные сведения | `additional_info` |
| `form.copies_count` | Количество экземпляров | `copies_count` |
| `form.attachments` | Приложения | `attachments` |
| `form.work_start` | Индивидуальная дата начала работ | `work_start` |
| `form.work_end` | Индивидуальная дата окончания работ | `work_end` |
| `representatives.customer_control.fio_short` | Строительный контроль застройщика/заказчика: подпись/ФИО | `customer_control_signature` |
| `representatives.builder.fio_short` | Лицо, осуществляющее строительство: подпись/ФИО | `builder_signature` |
| `representatives.builder_control.fio_short` | Строительный контроль лица, осуществляющего строительство: подпись/ФИО | `builder_control_signature` |
| `representatives.designer.fio_short` | Представитель проектировщика: подпись/ФИО | `designer_signature` |
| `representatives.work_performer.fio_short` | Представитель фактического исполнителя работ: подпись/ФИО | `work_performer_signature` |

## МИНСТРОЙ_344_АОУСИТО

Акт освидетельствования участков сетей инженерно-технического обеспечения

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `object.name` | Наименование объекта | `object_name` |
| `object.address` | Почтовый или строительный адрес объекта | `object_address` |
| `organisations.customer.full_name` | customer: наименование | `customer_name` |
| `organisations.customer.ogrn` | customer: ОГРН | `customer_ogrn` |
| `organisations.customer.inn` | customer: ИНН | `customer_inn` |
| `organisations.customer.address` | customer: адрес | `customer_address` |
| `organisations.customer.phone` | customer: телефон | `customer_phone` |
| `organisations.customer.sro_info` | customer: сведения СРО | `customer_sro` |
| `form.customer_individual` | Индивидуальные реквизиты физического лица/ИП при необходимости | `customer_individual` |
| `organisations.builder.full_name` | builder_org: наименование | `builder_org_name` |
| `organisations.builder.ogrn` | builder_org: ОГРН | `builder_org_ogrn` |
| `organisations.builder.inn` | builder_org: ИНН | `builder_org_inn` |
| `organisations.builder.address` | builder_org: адрес | `builder_org_address` |
| `organisations.builder.phone` | builder_org: телефон | `builder_org_phone` |
| `organisations.builder.sro_info` | builder_org: сведения СРО | `builder_org_sro` |
| `organisations.designer.full_name` | designer_org: наименование | `designer_org_name` |
| `organisations.designer.ogrn` | designer_org: ОГРН | `designer_org_ogrn` |
| `organisations.designer.inn` | designer_org: ИНН | `designer_org_inn` |
| `organisations.designer.address` | designer_org: адрес | `designer_org_address` |
| `organisations.designer.phone` | designer_org: телефон | `designer_org_phone` |
| `organisations.designer.sro_info` | designer_org: сведения СРО | `designer_org_sro` |
| `document.number` | Номер акта | `act_num` |
| `document.date.day` | День подписания | `signed_day` |
| `document.date.month` | Месяц подписания | `signed_month` |
| `document.date.year` | Год подписания | `signed_year` |
| `representatives.customer_control.details` | Строительный контроль застройщика/заказчика | `customer_control_details` |
| `representatives.customer_control.nrs_id` | Строительный контроль застройщика/заказчика: номер НРС | `customer_control_nrs` |
| `representatives.customer_control.organisation.full_name` | control_org: наименование | `control_org_name` |
| `representatives.customer_control.organisation.ogrn` | control_org: ОГРН | `control_org_ogrn` |
| `representatives.customer_control.organisation.inn` | control_org: ИНН | `control_org_inn` |
| `representatives.customer_control.organisation.address` | control_org: адрес | `control_org_address` |
| `representatives.customer_control.organisation.phone` | control_org: телефон | `control_org_phone` |
| `representatives.builder.details` | Лицо, осуществляющее строительство | `builder_details` |
| `representatives.builder_control.details` | Строительный контроль лица, осуществляющего строительство | `builder_control_details` |
| `representatives.builder_control.nrs_id` | Строительный контроль лица, осуществляющего строительство: номер НРС | `builder_control_nrs` |
| `representatives.designer.details` | Представитель проектировщика | `designer_details` |
| `representatives.designer.organisation.full_name` | designer_employer: наименование | `designer_employer_name` |
| `representatives.designer.organisation.ogrn` | designer_employer: ОГРН | `designer_employer_ogrn` |
| `representatives.designer.organisation.inn` | designer_employer: ИНН | `designer_employer_inn` |
| `representatives.designer.organisation.address` | designer_employer: адрес | `designer_employer_address` |
| `representatives.designer.organisation.phone` | designer_employer: телефон | `designer_employer_phone` |
| `representatives.work_performer.details` | Представитель фактического исполнителя работ | `work_performer_details` |
| `representatives.work_performer.organisation.full_name` | work_performer_employer: наименование | `work_performer_employer_name` |
| `representatives.work_performer.organisation.ogrn` | work_performer_employer: ОГРН | `work_performer_employer_ogrn` |
| `representatives.work_performer.organisation.inn` | work_performer_employer: ИНН | `work_performer_employer_inn` |
| `representatives.work_performer.organisation.address` | work_performer_employer: адрес | `work_performer_employer_address` |
| `representatives.work_performer.organisation.phone` | work_performer_employer: телефон | `work_performer_employer_phone` |
| `representatives.network_operator.details` | Представитель эксплуатирующей организации | `network_operator_details` |
| `representatives.network_operator.organisation.full_name` | network_operator_employer: наименование | `network_operator_employer_name` |
| `representatives.network_operator.organisation.ogrn` | network_operator_employer: ОГРН | `network_operator_employer_ogrn` |
| `representatives.network_operator.organisation.inn` | network_operator_employer: ИНН | `network_operator_employer_inn` |
| `representatives.network_operator.organisation.address` | network_operator_employer: адрес | `network_operator_employer_address` |
| `representatives.network_operator.organisation.phone` | network_operator_employer: телефон | `network_operator_employer_phone` |
| `form.network_sections` | Перечень и характеристика участков сетей | `network_sections` |
| `project.documentation.description` | Чертежи, проектная/рабочая документация, проектировщик | `design_documents` |
| `form.connection_conditions` | Технические условия подключения: номер, дата, кем выданы, срок действия | `connection_conditions` |
| `form.hidden_works_acts` | Скрытые работы, даты и номера актов | `hidden_works_acts` |
| `form.materials_quality` | Применённые материалы и документы качества | `materials_quality` |
| `form.voltage_date_number` | Исполнительные геодезические схемы | `geodetic_schemes` |
| `form.control_results` | Экспертизы, обследования и испытания | `control_results` |
| `form.technical_conditions` | Реквизиты предъявленных технических условий | `technical_conditions` |
| `form.test_reports` | Документы проведённых испытаний и опробований | `test_reports` |
| `form.compliance_basis` | Технические условия, регламенты, нормативные акты и разделы документации | `compliance_basis` |
| `form.additional_info` | Дополнительные сведения | `additional_info` |
| `form.copies_count` | Количество экземпляров | `copies_count` |
| `form.attachments` | Приложения | `attachments` |
| `form.work_start` | Индивидуальная дата начала работ | `work_start` |
| `form.work_end` | Индивидуальная дата окончания работ | `work_end` |
| `representatives.customer_control.fio_short` | Строительный контроль застройщика/заказчика: подпись/ФИО | `customer_control_signature` |
| `representatives.builder.fio_short` | Лицо, осуществляющее строительство: подпись/ФИО | `builder_signature` |
| `representatives.builder_control.fio_short` | Строительный контроль лица, осуществляющего строительство: подпись/ФИО | `builder_control_signature` |
| `representatives.designer.fio_short` | Представитель проектировщика: подпись/ФИО | `designer_signature` |
| `representatives.work_performer.fio_short` | Представитель фактического исполнителя работ: подпись/ФИО | `work_performer_signature` |
| `representatives.network_operator.fio_short` | Представитель эксплуатирующей организации: подпись/ФИО | `network_operator_signature` |

## МИНСТРОЙ_344_АРООКС

Акт разбивки осей объекта капитального строительства на местности

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `object.name` | Наименование объекта | `object_name` |
| `object.address` | Почтовый или строительный адрес объекта | `object_address` |
| `organisations.customer.full_name` | customer: наименование | `customer_name` |
| `organisations.customer.ogrn` | customer: ОГРН | `customer_ogrn` |
| `organisations.customer.inn` | customer: ИНН | `customer_inn` |
| `organisations.customer.address` | customer: адрес | `customer_address` |
| `organisations.customer.phone` | customer: телефон | `customer_phone` |
| `organisations.customer.sro_info` | customer: сведения СРО | `customer_sro` |
| `form.customer_individual` | Индивидуальные реквизиты физического лица/ИП при необходимости | `customer_individual` |
| `organisations.builder.full_name` | builder_org: наименование | `builder_org_name` |
| `organisations.builder.ogrn` | builder_org: ОГРН | `builder_org_ogrn` |
| `organisations.builder.inn` | builder_org: ИНН | `builder_org_inn` |
| `organisations.builder.address` | builder_org: адрес | `builder_org_address` |
| `organisations.builder.phone` | builder_org: телефон | `builder_org_phone` |
| `organisations.builder.sro_info` | builder_org: сведения СРО | `builder_org_sro` |
| `organisations.designer.full_name` | designer_org: наименование | `designer_org_name` |
| `organisations.designer.ogrn` | designer_org: ОГРН | `designer_org_ogrn` |
| `organisations.designer.inn` | designer_org: ИНН | `designer_org_inn` |
| `organisations.designer.address` | designer_org: адрес | `designer_org_address` |
| `organisations.designer.phone` | designer_org: телефон | `designer_org_phone` |
| `organisations.designer.sro_info` | designer_org: сведения СРО | `designer_org_sro` |
| `document.number` | Номер акта | `act_num` |
| `document.date.day` | День подписания | `signed_day` |
| `document.date.month` | Месяц подписания | `signed_month` |
| `document.date.year` | Год подписания | `signed_year` |
| `representatives.customer_control.details` | Строительный контроль застройщика/заказчика | `customer_control_details` |
| `representatives.customer_control.nrs_id` | Строительный контроль застройщика/заказчика: номер НРС | `customer_control_nrs` |
| `representatives.customer_control.organisation.full_name` | control_org: наименование | `control_org_name` |
| `representatives.customer_control.organisation.ogrn` | control_org: ОГРН | `control_org_ogrn` |
| `representatives.customer_control.organisation.inn` | control_org: ИНН | `control_org_inn` |
| `representatives.customer_control.organisation.address` | control_org: адрес | `control_org_address` |
| `representatives.customer_control.organisation.phone` | control_org: телефон | `control_org_phone` |
| `representatives.builder.details` | Лицо, осуществляющее строительство | `builder_details` |
| `representatives.builder_control.details` | Строительный контроль лица, осуществляющего строительство | `builder_control_details` |
| `representatives.builder_control.nrs_id` | Строительный контроль лица, осуществляющего строительство: номер НРС | `builder_control_nrs` |
| `representatives.designer.details` | Представитель проектировщика | `designer_details` |
| `representatives.designer.organisation.full_name` | designer_employer: наименование | `designer_employer_name` |
| `representatives.designer.organisation.ogrn` | designer_employer: ОГРН | `designer_employer_ogrn` |
| `representatives.designer.organisation.inn` | designer_employer: ИНН | `designer_employer_inn` |
| `representatives.designer.organisation.address` | designer_employer: адрес | `designer_employer_address` |
| `representatives.designer.organisation.phone` | designer_employer: телефон | `designer_employer_phone` |
| `representatives.work_performer.details` | Представитель фактического исполнителя работ | `work_performer_details` |
| `representatives.work_performer.organisation.full_name` | work_performer_employer: наименование | `work_performer_employer_name` |
| `representatives.work_performer.organisation.ogrn` | work_performer_employer: ОГРН | `work_performer_employer_ogrn` |
| `representatives.work_performer.organisation.inn` | work_performer_employer: ИНН | `work_performer_employer_inn` |
| `representatives.work_performer.organisation.address` | work_performer_employer: адрес | `work_performer_employer_address` |
| `representatives.work_performer.organisation.phone` | work_performer_employer: телефон | `work_performer_employer_phone` |
| `form.axes` | Оси, по которым произведена разбивка | `axes` |
| `form.object_name` | Наименование объекта | `examined_object` |
| `form.setting_out_basis` | Данные и чертежи, по которым выполнена разбивка | `setting_out_basis` |
| `form.axes_fixing` | Способ закрепления осей | `axes_fixing` |
| `form.design_compliance` | Чертежи, проектная документация, регламенты и нормативные акты | `design_compliance` |
| `form.additional_info` | Дополнительные сведения | `additional_info` |
| `form.copies_count` | Количество экземпляров | `copies_count` |
| `form.attachments` | Приложения: чертежи, схемы, ведомости | `attachments` |
| `representatives.customer_control.fio_short` | Строительный контроль застройщика/заказчика: подпись/ФИО | `customer_control_signature` |
| `representatives.builder.fio_short` | Лицо, осуществляющее строительство: подпись/ФИО | `builder_signature` |
| `representatives.builder_control.fio_short` | Строительный контроль лица, осуществляющего строительство: подпись/ФИО | `builder_control_signature` |
| `representatives.designer.fio_short` | Представитель проектировщика: подпись/ФИО | `designer_signature` |
| `representatives.work_performer.fio_short` | Представитель фактического исполнителя работ: подпись/ФИО | `work_performer_signature` |

## ТИТУЛЬНЫЙ_ЛИСТ

Титульный лист исполнительной документации и наклейки

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `object.name` | object | `object` |
| `project.name` | project | `project` |
| `project.code` | cifr | `cifr` |
| `project.city` | city | `city` |
| `organisations.customer.full_name` | client | `client` |
| `organisations.technical_customer.full_name` | tech_client | `tech_client` |
| `organisations.general_contractor.full_name` | gen_contractor | `gen_contractor` |
| `organisations.builder.full_name` | sub_contractor | `sub_contractor` |
| `form.year` | year | `year` |
| `form.copies` | copies | `copies` |
| `form.volumes` | volumes | `volumes` |
| `form.font` | font | `font` |
| `form.labels` | labels | `labels` |

## СП_40_102_2000_Е

Акт о проведении входного контроля партии труб

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.organisation_fibre` | наименование организации получателя | `t0_r0_c1` |
| `form.cable_fibre` | водопровод, канализация и др. | `t1_r0_c1` |
| `form.pressure_system` | давлением | `t1_r2_c1` |
| `representatives.customer.details` | организация заказчика, должность, Ф.И.О. | `t2_r0_c1` |
| `form.representatives_customer_details` | организация подрядчика, должность, Ф.И.О. | `t2_r2_c0` |
| `representatives.network_operator.details` | эксплуатирующая организация, должность, Ф.И.О. | `t2_r4_c0` |
| `form.pipe_number_test` | провели входной контроль партии труб (соединительных деталей) № | `t3_r0_c1` |
| `form.diameter` | диаметром | `t3_r1_c1` |
| `form.date_fibre` | наименование фирмы, дата | `t3_r2_c1` |
| `form.type` | из полимера типа | `t3_r4_c1` |
| `form.drum_quantity_fibre` | шт., бухт или барабанов (ящиков соединительных деталей) | `t4_r0_c1` |
| `form.requirements` | российский или зарубежный стандарт | `t4_r2_c1` |
| `form.pipe_quantity` | Количество труб Ду | `t5_r0_c1` |
| `form.length` | мм, длиной | `t5_r0_c3` |
| `form.requirements_fibre` | (маркировка по стандарту) | `t5_r0_c5` |
| `form.quantity` | Количество деталей Ду | `t5_r2_c1` |
| `form.length_mm` | мм | `t5_r2_c3` |
| `form.requirements_fibre_2` | (маркировка по стандарту) | `t5_r2_c5` |
| `form.quality_documents_cable_fibre` | Данные о сопроводительном сертификате | `t6_r0_c1` |
| `form.date` | Дата | `t7_r0_c1` |

## СП_42_101_2003_П

Акт приёмки газопроводов для комплексного опробования

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.gas_pipeline_commissioning_equipment` | 2. Предъявленное к приемке газооборудование считать принятым с "…"… 20… г. для проведения комплексного опробования (пусконаладочных работ). | `p120_1` |
| `form.gas_pipeline_commissioning_equipment_2` | 2. Предъявленное к приемке газооборудование считать принятым с "…"… 20… г. для проведения комплексного опробования (пусконаладочных работ). | `p120_2` |
| `form.gas_pipeline_commissioning_equipment_3` | 2. Предъявленное к приемке газооборудование считать принятым с "…"… 20… г. для проведения комплексного опробования (пусконаладочных работ). | `p120_3` |
| `project.documentation.object_description` | (наименование и адрес объекта) | `t0_r0_c0` |
| `project.city` | г. | `t1_r0_c1` |
| `form.test_date.day` | « | `t1_r0_c4` |
| `form.test_date.month` | » | `t1_r0_c6` |
| `form.test_date.year` | 20 | `t1_r0_c8` |
| `representatives.commission_chair.details` | (фамилия, имя, отчество, должность) | `t2_r1_c0` |
| `representatives.general_contractor.details` | (фамилия, имя, отчество, должность) | `t2_r4_c1` |
| `representatives.network_operator.details` | (фамилия, имя, отчество, должность) | `t2_r6_c1` |
| `representatives.customer_control.details` | (фамилия, имя, отчество, должность) | `t2_r8_c1` |
| `organisations.general_contractor.full_name` | (наименование организации) | `t3_r0_c1` |
| `form.quantity_type` | (тип, количество, техническая характеристика) | `t3_r3_c0` |
| `form.equipment_fibre` | , | `t3_r5_c1` |
| `form.type` | (тип автоматики) | `t3_r6_c0` |
| `object.name` | (наименование объекта) | `t3_r9_c0` |
| `form.number_design_documentation` | 2. Проект N | `t4_r0_c1` |
| `form.organisation_fibre` | (наименование организации) | `t4_r0_c3` |
| `form.date` | (месяц, год) | `t5_r1_c1` |
| `form.date_2` | (месяц, год) | `t5_r1_c3` |
| `organisations.commissioner.full_name` | (наименование пусконаладочной организации) | `t6_r1_c0` |
| `form.number_fibre` | от « | `t7_r0_c3` |
| `form.number_fibre_2` | » | `t7_r0_c5` |
| `form.number_fibre_3` | 20 | `t7_r0_c7` |
| `form.date_work` | « | `t7_r2_c2` |
| `form.date_work_2` | » | `t7_r2_c4` |
| `form.date_work_3` | 20 | `t7_r2_c6` |
| `form.test` | (виды испытаний) | `t8_r0_c0` |

## СП_42_101_2003_Т

Строительный паспорт ГРП

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.accuracy_class_instrument_gas_pipeline` | «…» … 20… г. произведено испытание газопровода и оборудования ГРП на герметичность давлением … МПа в течение 12 ч при помощи манометра класса точности …. | `p53_1` |
| `form.accuracy_class_instrument_gas_pipeline_2` | «…» … 20… г. произведено испытание газопровода и оборудования ГРП на герметичность давлением … МПа в течение 12 ч при помощи манометра класса точности …. | `p53_2` |
| `form.accuracy_class_instrument_gas_pipeline_3` | «…» … 20… г. произведено испытание газопровода и оборудования ГРП на герметичность давлением … МПа в течение 12 ч при помощи манометра класса точности …. | `p53_3` |
| `form.accuracy_class_instrument_gas_pipeline_4` | «…» … 20… г. произведено испытание газопровода и оборудования ГРП на герметичность давлением … МПа в течение 12 ч при помощи манометра класса точности …. | `p53_4` |
| `form.accuracy_class_instrument_gas_pipeline_5` | «…» … 20… г. произведено испытание газопровода и оборудования ГРП на герметичность давлением … МПа в течение 12 ч при помощи манометра класса точности …. | `p53_5` |
| `form.pressure_drop_pressure_system` | Падение давления … МПа при допускаемом падении давления … МПа. | `p54_6` |
| `form.pressure_drop_pressure_system_2` | Падение давления … МПа при допускаемом падении давления … МПа. | `p54_7` |
| `form.number_design_documentation_organisation` | (наименование строительно-монтажной организации, номер проекта) | `t0_r0_c1` |
| `form.location` | по адресу: | `t0_r2_c1` |
| `form.dimensions_pressure_equipment` | Указываются давление газа (на входе и на выходе), тип и размеры установленного оборудования, число и площадь помещений, система отопления и вентиляции, данные об освещении, связи, телеуправлении | `t1_r0_c0` |
| `form.passport_attachments_quality_documents` | 2. Перечень прилагаемых сертификатов, технических паспортов (или их копий) и других документов, удостоверяющих качество материалов и оборудования | `t2_r0_c0` |
| `form.gas_pipeline_connection_cable` | 3*. Данные о сварке стыков газопровода | `rows_3_2` |
| `form.gas_pipeline_connection_cable[].welding_representative` | Фамилия, имя, отчество сварщика (паяльщика) | `rows_3_2.c1` |
| `form.gas_pipeline_connection_cable[].welding_number` | Номер (клеймо) сварщика (паяльщика) | `rows_3_2.c2` |
| `form.gas_pipeline_connection_cable[].diameter_connection_pipe` | Сварено стыков / Диаметр труб, мм | `rows_3_2.c3` |
| `form.gas_pipeline_connection_cable[].welding_date_quantity` | Дата проведения сварочных работ / Число, шт. | `rows_3_2.c4` |
| `form.gas_pipeline_connection_cable[].value` | Графа 5 | `rows_3_2.c5` |
| `representatives.foreman.details` | (должность, подпись, инициалы, фамилия производителя работ) | `t4_r0_c0` |
| `form.representatives_foreman_details` | (должность, подпись, инициалы, фамилия) | `t5_r0_c1` |
| `representatives.network_operator.details` | (должность, подпись, инициалы, фамилия) | `t5_r2_c1` |
| `form.date_design_documentation_organisation` | (наименование проектной организации, дата выпуска проекта) | `t6_r1_c0` |
| `form.deviations_voltage_number` | с учетом согласованных изменений, внесенных в рабочие чертежи № | `t6_r3_c1` |
| `form.date` | « | `t7_r0_c2` |
| `form.date_2` | » | `t7_r0_c4` |
| `form.date_3` | 20 | `t7_r0_c6` |
| `form.ready_date.day` | « | `t7_r2_c2` |
| `form.ready_date.month` | » | `t7_r2_c4` |
| `form.ready_date.year` | 20 | `t7_r2_c6` |
| `representatives.chief_engineer.details` | (подпись, инициалы, фамилия) | `t8_r0_c1` |
| `form.representatives_network_operator_details` | (должность, подпись, инициалы, фамилия) | `t8_r2_c1` |

## СП_42_101_2003_С

Строительный паспорт газоиспользующего оборудования

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.accuracy_class_instrument_gas_pipeline` | «…»…20… г. газопровод испытан на герметичность давлением … МПа в течение … ч, с подключенным газоиспользующим оборудованием. Фактическое падение давления … МПа установлено при помощи манометра класса точности …. | `p56_1` |
| `form.accuracy_class_instrument_gas_pipeline_2` | «…»…20… г. газопровод испытан на герметичность давлением … МПа в течение … ч, с подключенным газоиспользующим оборудованием. Фактическое падение давления … МПа установлено при помощи манометра класса точности …. | `p56_2` |
| `form.accuracy_class_instrument_gas_pipeline_3` | «…»…20… г. газопровод испытан на герметичность давлением … МПа в течение … ч, с подключенным газоиспользующим оборудованием. Фактическое падение давления … МПа установлено при помощи манометра класса точности …. | `p56_3` |
| `form.accuracy_class_instrument_gas_pipeline_4` | «…»…20… г. газопровод испытан на герметичность давлением … МПа в течение … ч, с подключенным газоиспользующим оборудованием. Фактическое падение давления … МПа установлено при помощи манометра класса точности …. | `p56_4` |
| `form.accuracy_class_instrument_gas_pipeline_5` | «…»…20… г. газопровод испытан на герметичность давлением … МПа в течение … ч, с подключенным газоиспользующим оборудованием. Фактическое падение давления … МПа установлено при помощи манометра класса точности …. | `p56_5` |
| `form.accuracy_class_instrument_gas_pipeline_6` | «…»…20… г. газопровод испытан на герметичность давлением … МПа в течение … ч, с подключенным газоиспользующим оборудованием. Фактическое падение давления … МПа установлено при помощи манометра класса точности …. | `p56_6` |
| `form.accuracy_class_instrument_gas_pipeline_7` | «…»…20… г. газопровод испытан на герметичность давлением … МПа в течение … ч, с подключенным газоиспользующим оборудованием. Фактическое падение давления … МПа установлено при помощи манометра класса точности …. | `p56_7` |
| `form.number_design_documentation_organisation` | (наименование строительно-монтажной организации и номер проекта) | `t0_r0_c1` |
| `form.location_fibre` | (город, улица, привязки начального и конечного пикетов) | `t0_r2_c1` |
| `form.gas_pipeline_pressure_length` | ность газопровода и число запорных устройств на них; для внутрицехового оборудования — общая протяженность газопровода, тип и число установленного газоиспользующего оборудования, рабочее давление газа | `t1_r0_c0` |
| `form.passport_attachments_quality_documents` | 2. Перечень прилагаемых сертификатов, технических паспортов (или их копий) и других документов, удостоверяющих качество материалов и оборудования | `t2_r0_c0` |
| `form.gas_pipeline_connection_cable` | 3. Данные о сварке стыков газопровода | `rows_3_2` |
| `form.gas_pipeline_connection_cable[].welding_representative` | Фамилия, имя, отчество сварщика (паяльщика) | `rows_3_2.c1` |
| `form.gas_pipeline_connection_cable[].welding_number` | Номер (клеймо) сварщика (паяльщика) | `rows_3_2.c2` |
| `form.gas_pipeline_connection_cable[].diameter_connection_pipe` | Сварено стыков / Диаметр труб, мм | `rows_3_2.c3` |
| `form.gas_pipeline_connection_cable[].welding_date_quantity` | Дата проведения сварочных работ / Число, шт. | `rows_3_2.c4` |
| `form.gas_pipeline_connection_cable[].value` | Графа 5 | `rows_3_2.c5` |
| `representatives.foreman.details` | (должность, подпись, инициалы, фамилия производителя работ) | `t4_r0_c0` |
| `form.representatives_foreman_details` | (должность, подпись, инициалы, фамилия) | `t5_r0_c1` |
| `representatives.network_operator.details` | (должность, подпись, инициалы, фамилия) | `t5_r2_c1` |
| `form.date_design_documentation_organisation` | (наименование проектной организации, дата выпуска проекта) | `t6_r1_c0` |
| `form.deviations_voltage_number` | с учетом согласованных изменений, внесенных в рабочие чертежи № | `t6_r3_c1` |
| `form.date` | « | `t7_r0_c2` |
| `form.date_2` | » | `t7_r0_c4` |
| `form.date_3` | 20 | `t7_r0_c6` |
| `form.ready_date.day` | « | `t7_r2_c2` |
| `form.ready_date.month` | » | `t7_r2_c4` |
| `form.ready_date.year` | 20 | `t7_r2_c6` |
| `representatives.chief_engineer.details` | (подпись, инициалы, фамилия) | `t8_r0_c1` |
| `form.representatives_network_operator_details` | (должность, подпись, инициалы, фамилия) | `t8_r2_c1` |

## СП_42_101_2003_Р

Строительный паспорт газопровода

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.defects_requirements_thickness` | на отсутствие механических повреждений и трещин — внешним осмотром; толщина — замером по ГОСТ 9.602 … мм; адгезия к стали — по ГОСТ 9.602; сплошность — дефектоскопом. | `p112_1` |
| `form.pipe_test_fibre` | 3. Проверка на отсутствие электрического контакта между металлом трубы и грунтом произведена после полной засыпки траншеи «…» … 20 … г. | `p114_2` |
| `form.pipe_test_fibre_2` | 3. Проверка на отсутствие электрического контакта между металлом трубы и грунтом произведена после полной засыпки траншеи «…» … 20 … г. | `p114_3` |
| `form.pipe_test_fibre_3` | 3. Проверка на отсутствие электрического контакта между металлом трубы и грунтом произведена после полной засыпки траншеи «…» … 20 … г. | `p114_4` |
| `form.gas_pipeline_tightness_cable` | 1. «…» … 20… г. перед испытанием на герметичность произведена продувка газопровода воздухом. | `p127_5` |
| `form.gas_pipeline_tightness_cable_2` | 1. «…» … 20… г. перед испытанием на герметичность произведена продувка газопровода воздухом. | `p127_6` |
| `form.gas_pipeline_tightness_cable_3` | 1. «…» … 20… г. перед испытанием на герметичность произведена продувка газопровода воздухом. | `p127_7` |
| `form.gas_pipeline_tightness_voltage` | 2. «…» … 20… г. засыпанный до проектных отметок газопровод с установленной на нем арматурой и ответвлениями к объектам до отключающих запорных устройств (или подземная часть газового ввода) испытан на герметичность в течение … ч. | `p128_8` |
| `form.gas_pipeline_tightness_voltage_2` | 2. «…» … 20… г. засыпанный до проектных отметок газопровод с установленной на нем арматурой и ответвлениями к объектам до отключающих запорных устройств (или подземная часть газового ввода) испытан на герметичность в течение … ч. | `p128_9` |
| `form.gas_pipeline_tightness_voltage_3` | 2. «…» … 20… г. засыпанный до проектных отметок газопровод с установленной на нем арматурой и ответвлениями к объектам до отключающих запорных устройств (или подземная часть газового ввода) испытан на герметичность в течение … ч. | `p128_10` |
| `form.gas_pipeline_tightness_voltage_4` | 2. «…» … 20… г. засыпанный до проектных отметок газопровод с установленной на нем арматурой и ответвлениями к объектам до отключающих запорных устройств (или подземная часть газового ввода) испытан на герметичность в течение … ч. | `p128_11` |
| `form.gas_pipeline_pressure_temperature` | До начала испытания подземный (наземный) газопровод находился под давлением воздуха в течение … ч для выравнивания температуры воздуха в газопроводе с температурой грунта. | `p129_12` |
| `form.requirements_instrument_pressure` | Замеры давления производились манометром (дифманометром) по ГОСТ …, класс …. | `p130_13` |
| `form.requirements_instrument_pressure_2` | Замеры давления производились манометром (дифманометром) по ГОСТ …, класс …. | `p130_14` |
| `form.defects_gas_pipeline_tightness` | «…» … 20… г. произведено испытание надземного газопровода (надземной части газового ввода) на герметичность давлением … МПа с выдержкой в течение … ч, последующим внешним осмотром и проверкой всех сварных, резьбовых и фланцевых соединений. Утечки и дефекты не обнаружены. Надземный газопровод (надземная часть газового ввода) испытание на герметичность выдержал. | `p163_15` |
| `form.defects_gas_pipeline_tightness_2` | «…» … 20… г. произведено испытание надземного газопровода (надземной части газового ввода) на герметичность давлением … МПа с выдержкой в течение … ч, последующим внешним осмотром и проверкой всех сварных, резьбовых и фланцевых соединений. Утечки и дефекты не обнаружены. Надземный газопровод (надземная часть газового ввода) испытание на герметичность выдержал. | `p163_16` |
| `form.defects_gas_pipeline_tightness_3` | «…» … 20… г. произведено испытание надземного газопровода (надземной части газового ввода) на герметичность давлением … МПа с выдержкой в течение … ч, последующим внешним осмотром и проверкой всех сварных, резьбовых и фланцевых соединений. Утечки и дефекты не обнаружены. Надземный газопровод (надземная часть газового ввода) испытание на герметичность выдержал. | `p163_17` |
| `form.defects_gas_pipeline_tightness_4` | «…» … 20… г. произведено испытание надземного газопровода (надземной части газового ввода) на герметичность давлением … МПа с выдержкой в течение … ч, последующим внешним осмотром и проверкой всех сварных, резьбовых и фланцевых соединений. Утечки и дефекты не обнаружены. Надземный газопровод (надземная часть газового ввода) испытание на герметичность выдержал. | `p163_18` |
| `form.defects_gas_pipeline_tightness_5` | «…» … 20… г. произведено испытание надземного газопровода (надземной части газового ввода) на герметичность давлением … МПа с выдержкой в течение … ч, последующим внешним осмотром и проверкой всех сварных, резьбовых и фланцевых соединений. Утечки и дефекты не обнаружены. Надземный газопровод (надземная часть газового ввода) испытание на герметичность выдержал. | `p163_19` |
| `organisations.installer.full_name` | (наименование строительно-монтажной организации | `t0_r0_c1` |
| `form.number_design_documentation` | и номер проекта) | `t0_r2_c0` |
| `form.location_fibre` | (город, улица, привязки начального и конечного пикетов) | `t0_r4_c1` |
| `form.gas_pipeline_insulation_connection` | зопровода, материал труб, тип изоляционного покрытия линейной части и сварных стыков (для стальных подземных газопроводов и газовых вводов), число установленных запорных устройств и других сооружений. | `t1_r0_c0` |
| `form.passport_attachments_quality_documents` | 2. Перечень прилагаемых сертификатов, технических паспортов (или их копий) и других документов, удостоверяющих качество материалов и оборудования | `t2_r0_c0` |
| `form.gas_pipeline_connection_cable` | 3. Данные о сварке стыков газопровода | `rows_3_2` |
| `form.gas_pipeline_connection_cable[].welding_representative` | Фамилия, имя, отчество сварщика | `rows_3_2.c1` |
| `form.gas_pipeline_connection_cable[].welding` | Вид сварки | `rows_3_2.c2` |
| `form.gas_pipeline_connection_cable[].welding_number` | Номер (клеймо) сварщика | `rows_3_2.c3` |
| `form.gas_pipeline_connection_cable[].diameter_connection_pipe` | Сварено стыков / Диаметр труб, мм | `rows_3_2.c4` |
| `form.gas_pipeline_connection_cable[].welding_date_quantity` | Дата проведения сварочных работ / Число, шт. | `rows_3_2.c5` |
| `form.gas_pipeline_connection_cable[].value` | Графа 6 | `rows_3_2.c6` |
| `representatives.foreman.details` | (должность, подпись, инициалы, фамилия производителя работ) | `t4_r0_c0` |
| `form.representatives_foreman_details` | (должность, подпись, инициалы, фамилия) | `t6_r0_c1` |
| `representatives.network_operator.details` | (должность, подпись, инициалы, фамилия) | `t6_r2_c1` |
| `representatives.laboratory_head.details` | (подпись, инициалы, фамилия) | `t7_r0_c1` |
| `form.representatives_network_operator_details` | (должность, подпись, инициалы, фамилия) | `t7_r2_c1` |
| `form.gas_pipeline_pressure_cable` | Данные замеров давления при испытании подземного (наземного) газопровода | `rows_8_3` |
| `form.gas_pipeline_pressure_cable[].date_test` | Дата испытания / Месяц | `rows_8_3.c1` |
| `form.gas_pipeline_pressure_cable[].pressure_quantity_system` | Замеры давления, кПа (мм рт. ст.) / Число | `rows_8_3.c2` |
| `form.gas_pipeline_pressure_cable[].pressure_drop_pressure_system` | Падение давления, кПа (мм рт. ст.) / Часы | `rows_8_3.c3` |
| `form.gas_pipeline_pressure_cable[].instrument` | манометрическое / P1 | `rows_8_3.c4` |
| `form.gas_pipeline_pressure_cable[].value` | барометрическое / P2 | `rows_8_3.c5` |
| `form.gas_pipeline_pressure_cable[].value_2` | допускаемое / B1 | `rows_8_3.c6` |
| `form.gas_pipeline_pressure_cable[].value_3` | фактическое / B2 | `rows_8_3.c7` |
| `form.gas_pipeline_pressure_cable[].value_4` | Графа 8 | `rows_8_3.c8` |
| `form.gas_pipeline_pressure_cable[].value_5` | Графа 9 | `rows_8_3.c9` |
| `form.representatives_foreman_details_2` | (должность, подпись, инициалы, фамилия) | `t9_r0_c1` |
| `form.representatives_network_operator_details_2` | (должность, подпись, инициалы, фамилия) | `t9_r2_c1` |
| `form.date_design_documentation_organisation` | (наименование проектной организации, дата выпуска проекта) | `t10_r1_c0` |
| `form.deviations_voltage_number` | с учетом согласованных изменений, внесенных в рабочие чертежи № | `t10_r3_c1` |
| `form.date` | « | `t11_r0_c2` |
| `form.date_2` | » | `t11_r0_c4` |
| `form.date_3` | 20 | `t11_r0_c6` |
| `form.ready_date.day` | « | `t11_r2_c2` |
| `form.ready_date.month` | » | `t11_r2_c4` |
| `form.ready_date.year` | 20 | `t11_r2_c6` |
| `representatives.chief_engineer.details` | (подпись, инициалы, фамилия) | `t12_r0_c1` |
| `form.representatives_network_operator_details_3` | (должность, подпись, инициалы, фамилия) | `t12_r2_c1` |

## СП_45_Ш

Акт приёмки захватки стены в грунте (баретты)

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.certificate_voltage_number` | освидетельствования и приемки захватки стены в грунте (баретты) №… | `p9_1` |
| `organisations.builder.full_name` | Наименование строительной организации | `t0_r0_c1` |
| `object.name` | Наименование строительного объекта | `t0_r1_c1` |
| `representatives.customer_control.details` | (представитель застройщика (технического заказчика, эксплуатирующей организации или регионального оператора) по вопросам строительного контроля) | `t1_r0_c0` |
| `representatives.builder_control.details` | (представитель лица, осуществляющего строительство, по вопросам строительного контроля (специалист по организации строительства)) | `t1_r2_c0` |
| `representatives.work_performer.details` | (представитель лица, выполнившего работы, подлежащие освидетельствованию) | `t1_r4_c0` |
| `form.number_fibre` | установили, что захватка № (баретта №) | `t2_r0_c1` |
| `form.voltage_elevation_work` | Работы по захватке стены в грунте (баретты) выполнены с отметки | `t3_r0_c2` |
| `form.depth_work` | Траншея разработана на глубину, м | `t3_r1_c2` |
| `form.voltage_fibre` | Грунт в основании траншеи | `t3_r2_c2` |
| `form.concrete_class` | Траншея заполнена бетоном класса | `t3_r3_c2` |
| `form.dimensions` | Размеры захватки (баретты), м | `t3_r4_c2` |
| `form.certificate_number_fibre` | Акт освидетельствования и приемки траншеи захватки № (баретты №) | `t4_r0_c2` |
| `form.certificate_number_fibre_2` | Акт освидетельствования арматурного каркаса захватки № (баретты №) | `t4_r1_c2` |
| `form.representatives_builder_control_details` | Представитель лица, осуществляющего строительство, по вопросам строительного контроля (специалист по организации строительства) | `t5_r1_c0` |
| `form.representatives_work_performer_details` | Представитель лица, выполнившего работы, подлежащие освидетельствованию | `t5_r3_c0` |
| `form.certificate_quality_documents_concrete` | 4_r0_c2 }}2.Акт освидетельствования арматурного каркаса захватки № (баретты №){{ t4_r1_c2 }}3.Сертификат на бентонит (полимерный порошок).4.Сертификат на арматуру.5.Ведомость контроля качества бетона. | `t5_r5_c0` |

## СП_45_Я

Акт приёмки сваи

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.certificate_number_fibre` | освидетельствования и приёмки сваи №… | `p9_1` |
| `organisations.builder.full_name` | Наименование строительной организации | `t0_r0_c1` |
| `object.name` | Наименование строительного объекта | `t0_r1_c1` |
| `representatives.customer_control.details` | (представитель застройщика (технического заказчика, эксплуатирующей организации или регионального оператора) по вопросам строительного контроля) | `t1_r0_c0` |
| `representatives.builder_control.details` | (представитель лица, осуществляющего строительство, по вопросам строительного контроля (специалист по организации строительства)) | `t1_r2_c0` |
| `representatives.work_performer.details` | (представитель лица, выполнившего работы, подлежащие освидетельствованию) | `t1_r4_c0` |
| `form.number_fibre` | установили, что свая № | `t2_r0_c1` |
| `form.elevation_work` | Работы по свае выполнены с отметки | `t3_r0_c2` |
| `form.voltage_depth` | Скважина пробурена на глубину, м | `t3_r1_c2` |
| `form.voltage_welding_fibre` | Грунт в основании подошвы сваи | `t3_r2_c2` |
| `form.voltage_concrete_class` | Скважина заполнена бетоном класса | `t3_r3_c2` |
| `form.dimensions_diameter_length` | Размеры сваи (диаметр, длина), м | `t3_r4_c2` |
| `form.certificate_voltage_number` | Акт освидетельствования и приемки скважины сваи № | `t4_r0_c2` |
| `form.certificate_number_fibre_2` | Акт освидетельствования арматурного каркаса сваи № | `t4_r1_c2` |
| `form.representatives_builder_control_details` | Представитель лица, осуществляющего строительство, по вопросам строительного контроля (специалист по организации строительства) | `t5_r1_c0` |
| `form.representatives_work_performer_details` | Представитель лица, выполнившего работы, подлежащие освидетельствованию | `t5_r3_c0` |
| `form.certificate_quality_documents_concrete` | r0_c2 }}2.Акт освидетельствования арматурного каркаса сваи №{{ t4_r1_c2 }}3.Документ о качестве на бентонит (полимерный порошок).4.Документ о качестве на арматуру.5.Ведомость контроля качества бетона. | `t5_r5_c0` |

## СП_45_Ю

Акт приёмки скважины

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.certificate_voltage_number` | освидетельствования и приёмки скважины сваи №… | `p9_1` |
| `organisations.builder.full_name` | Наименование строительной организации | `t0_r0_c1` |
| `object.name` | Наименование строительного объекта | `t0_r1_c1` |
| `representatives.customer_control.details` | (представитель застройщика (технического заказчика, эксплуатирующей организации или регионального оператора) по вопросам строительного контроля) | `t1_r0_c0` |
| `representatives.builder_control.details` | (представитель лица, осуществляющего строительство, по вопросам строительного контроля (специалист по организации строительства)) | `t1_r2_c0` |
| `representatives.work_performer.details` | (представитель лица, выполнившего работы, подлежащие освидетельствованию) | `t1_r4_c0` |
| `form.voltage_elevation` | Отметка низа скважины, м | `t3_r0_c2` |
| `form.voltage_elevation_2` | Отметка устья скважины, м | `t3_r1_c2` |
| `form.elevation_system_fibre` | Абсолютная отметка кровли | `t3_r2_c2` |
| `form.power_coating` | и мощности слоя грунта, | `t3_r3_c2` |
| `form.voltage_diameter_depth` | Диаметр и глубина скважины, м | `t3_r4_c2` |
| `form.deviations_voltage` | Отклонения скважины | `t3_r5_c2` |
| `form.voltage_duration_method` | Буровой шлам удален из скважины с применением (способ и время) | `t3_r7_c1` |
| `form.location_fibre` | на строительной площадке и установили: | `t3_r9_c1` |
| `form.structure_work_fibre` | (наименование работ и конструкций) | `t4_r1_c1` |
| `form.concrete_date_fibre` | Начать бетонирование не позднее | `t4_r3_c2` |
| `form.duration` | ч. « | `t4_r3_c4` |
| `form.concrete_date_duration` | » | `t4_r3_c6` |
| `form.concrete_date_duration_2` | 20 | `t4_r3_c8` |
| `form.representatives_builder_control_details` | Представитель лица, осуществляющего строительство, по вопросам строительного контроля (специалист по организации строительства) | `t5_r1_c0` |
| `form.representatives_work_performer_details` | Представитель лица, выполнившего работы, подлежащие освидетельствованию | `t5_r3_c0` |
| `form.concrete_structure_date` | производство последующих работ по устройству (монтажу){{ t4_r1_c1 }}(наименование работ и конструкций)2.Начать бетонирование не позднее{{ t4_r3_c2 }}ч. «{{ t4_r3_c4 }}»{{ t4_r3_c6 }}20{{ t4_r3_c8 }}г. | `t5_r5_c0` |

## СП_45_Щ

Акт приёмки траншеи

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `organisations.builder.full_name` | Наименование строительной организации | `t0_r0_c1` |
| `object.name` | Наименование строительного объекта | `t0_r1_c1` |
| `representatives.customer_control.details` | (представитель застройщика (технического заказчика, эксплуатирующей организации или регионального оператора) по вопросам строительного контроля) | `t1_r0_c0` |
| `representatives.builder_control.details` | (представитель лица, осуществляющего строительство, по вопросам строительного контроля (специалист по организации строительства)) | `t1_r2_c0` |
| `representatives.work_performer.details` | (представитель лица, выполнившего работы, подлежащие освидетельствованию) | `t1_r4_c0` |
| `form.elevation` | Отметка низа траншеи, м | `t3_r0_c2` |
| `form.elevation_2` | Отметка устья траншеи, м | `t3_r1_c2` |
| `form.elevation_system_fibre` | Абсолютная отметка кровли | `t3_r2_c2` |
| `form.power_coating` | и мощности слоя грунта, | `t3_r3_c2` |
| `form.dimensions_depth` | Размеры (глубина) траншеи, м | `t3_r4_c2` |
| `form.deviations` | Отклонения траншеи | `t3_r5_c2` |
| `form.duration_method_fibre` | Буровой шлам удален из траншеи с применением (способ и время) | `t3_r7_c1` |
| `form.location_fibre` | на строительной площадке и установили: | `t3_r9_c1` |
| `form.structure_work_fibre` | (наименование работ и конструкций) | `t4_r1_c1` |
| `form.concrete_date_fibre` | Начать бетонирование не позднее | `t4_r3_c2` |
| `form.duration` | ч. « | `t4_r3_c4` |
| `form.concrete_date_duration` | » | `t4_r3_c6` |
| `form.concrete_date_duration_2` | 20 | `t4_r3_c8` |
| `form.representatives_builder_control_details` | Представитель лица, осуществляющего строительство, по вопросам строительного контроля (специалист по организации строительства) | `t5_r1_c0` |
| `form.representatives_work_performer_details` | Представитель лица, выполнившего работы, подлежащие освидетельствованию | `t5_r3_c0` |
| `form.concrete_structure_date` | производство последующих работ по устройству (монтажу){{ t4_r1_c1 }}(наименование работ и конструкций)2.Начать бетонирование не позднее{{ t4_r3_c2 }}ч. «{{ t4_r3_c4 }}»{{ t4_r3_c6 }}20{{ t4_r3_c8 }}г. | `t5_r5_c0` |

## СП_45_1

Журнал контроля качества глинистого раствора

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `object.name` | Наименование объекта | `t0_r0_c1` |
| `object.address` | Адрес объекта | `t0_r2_c1` |
| `form.organisation_fibre` | Наименование строительной организации | `t0_r4_c1` |
| `form.date` | Начат « | `t1_r0_c1` |
| `form.date_2` | » | `t1_r0_c3` |
| `form.date_3` | 20 | `t1_r0_c5` |
| `form.date_4` | Окончен « | `t1_r2_c1` |
| `form.date_5` | » | `t1_r2_c3` |
| `form.date_6` | 20 | `t1_r2_c5` |
| `form.date_7` | Начат «{{ t1_r0_c1 }}»{{ t1_r0_c3 }}20{{ t1_r0_c5 }}г.Окончен «{{ t1_r2_c1 }}»{{ t1_r2_c3 }}20{{ t1_r2_c5 }}г. | `rows_2_3` |
| `form.date_7[].number` | № п/п | `rows_2_3.c1` |
| `form.date_7[].date_duration` | Время проб отбора / Дата | `rows_2_3.c2` |
| `form.date_7[].location` | Место отбора пробы / Часы | `rows_2_3.c3` |
| `form.date_7[].work` | Вид работы при отборе пробы | `rows_2_3.c4` |
| `form.date_7[].depth` | Глубина отбора пробы | `rows_2_3.c5` |
| `form.date_7[].value` | Параметры раствора | `rows_2_3.c6` |
| `form.date_7[].notes` | Примечания / Вязкость, с | `rows_2_3.c7` |
| `form.date_7[].value_2` | Водоотделение, % | `rows_2_3.c8` |
| `form.date_7[].value_3` | Стабильность, г/см³ | `rows_2_3.c9` |
| `form.date_7[].value_4` | Содержание песка, % | `rows_2_3.c10` |
| `form.date_7[].duration` | Водоотдача, см³ за 30 мин | `rows_2_3.c11` |
| `form.date_7[].density` | Плотность, г/см³ | `rows_2_3.c12` |
| `form.date_7[].value_5` | Графа 13 | `rows_2_3.c13` |

## СП_48_И

Журнал входного контроля

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `object.name` | Наименование объекта | `t0_r0_c1` |
| `object.address` | Адрес объекта | `t0_r2_c1` |
| `form.organisation_fibre` | Наименование строительной организации | `t0_r4_c1` |
| `form.date` | Начат « | `t1_r0_c1` |
| `form.date_2` | » | `t1_r0_c3` |
| `form.date_3` | 20 | `t1_r0_c5` |
| `form.date_4` | Окончен « | `t1_r2_c1` |
| `form.date_5` | » | `t1_r2_c3` |
| `form.date_6` | 20 | `t1_r2_c5` |
| `form.date_7` | Начат «{{ t1_r0_c1 }}»{{ t1_r0_c3 }}20{{ t1_r0_c5 }}г.Окончен «{{ t1_r2_c1 }}»{{ t1_r2_c3 }}20{{ t1_r2_c5 }}г. | `rows_2_2` |
| `form.date_7[].number` | № п/п | `rows_2_2.c1` |
| `form.date_7[].date` | Дата доставки | `rows_2_2.c2` |
| `form.date_7[].equipment_materials_structure` | Наименование деталей, материалов, изделий, конструкций, оборудования | `rows_2_2.c3` |
| `form.date_7[].quantity` | Кол-во | `rows_2_2.c4` |
| `form.date_7[].value` | Поставщик | `rows_2_2.c5` |
| `form.date_7[].number_organisation_fibre` | Наименование и номер документа изготовителя | `rows_2_2.c6` |
| `form.date_7[].requirements_cable_design_documentation` | Результат проверки сопроводительных документов производителя и визуального осмотра на соответствие требованиям утвержденной проектной документации и соответствующим документам по стандартизации | `rows_2_2.c7` |
| `form.date_7[].conclusion_test_fibre` | Решение о необходимости проведения лабораторного контроля | `rows_2_2.c8` |
| `form.date_7[].test` | Результат лабораторного контроля | `rows_2_2.c9` |
| `form.date_7[].representative_test_system` | Подпись лица, осуществляющего контроль | `rows_2_2.c10` |

## СП_68_М

Акт приёмки оборудования после индивидуального испытания

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_0_2` |
| `document.date.month` | Месяц подписания | `date_0_4` |
| `document.date.year` | Год подписания | `date_0_6` |
| `project.city` | (место составления) | `t0_r0_c0` |
| `representatives.customer.details` | (инициалы, фамилия, должность) | `t1_r0_c1` |
| `organisations.customer.full_name` | [наименование организации - застройщика (технического заказчика)] | `t1_r2_c0` |
| `representatives.general_contractor.details` | (инициалы, фамилия, должность) | `t2_r0_c1` |
| `organisations.general_contractor.full_name` | (наименование организации) | `t2_r2_c0` |
| `representatives.installer.details` | (инициалы, фамилия, должность) | `t2_r4_c1` |
| `organisations.installer.full_name` | (наименование организации) | `t2_r6_c0` |
| `representatives.network_operator.details` | (инициалы, фамилия, должность) | `t2_r8_c1` |
| `organisations.network_operator.full_name` | (наименование организации) | `t2_r10_c0` |
| `representatives.designer.details` | (инициалы, фамилия, должность) | `t2_r12_c1` |
| `organisations.designer.full_name` | (наименование организации) | `t2_r14_c0` |
| `representatives.gsn.details` | (инициалы, фамилия, должность) | `t2_r17_c0` |
| `representatives.supervisory.details` | (инициалы, фамилия, должность) | `t2_r20_c0` |
| `form.equipment_system_fibre` | 1. Предъявлено к приёмке следующее оборудование: | `t2_r22_c1` |
| `form.attachments_voltage_equipment` | [перечень оборудования и его краткая техническая характеристика (при необходимости перечень указывается в приложении)] | `t2_r23_c0` |
| `form.location_fibre` | (наименование здания, сооружения, цеха) | `t2_r25_c1` |
| `form.organisation_fibre` | (наименование предприятия, его очереди, пускового комплекса) | `t2_r27_c1` |
| `form.work` | 2. Монтажные работы выполнены | `t2_r29_c1` |
| `form.organisations_installer_full_name` | (наименование монтажных организаций, их ведомственная подчинённость) | `t2_r30_c0` |
| `form.design_documentation_work_documentation` | 3. Проектная документация разработана | `t2_r32_c1` |
| `form.number_design_documentation_organisation` | (наименования проектных организаций, номера чертежей и даты их составления) | `t2_r33_c0` |
| `form.date` | (месяц и год) | `t2_r35_c1` |
| `form.date_2` | (месяц и год) | `t2_r37_c1` |
| `form.test_fibre` | (наименование испытаний) | `t2_r40_c0` |
| `form.work_start.day` | « | `t3_r0_c2` |
| `form.work_start.month` | » | `t3_r0_c4` |
| `form.work_start.year` | 20 | `t3_r0_c6` |
| `form.commissioning_fibre` | с«{{ t3_r0_c2 }}»{{ t3_r0_c4 }}20{{ t3_r0_c6 }}г.для комплексного опробования. | `t4_r1_c0` |
| `form.commissioning_fibre_2` | с«{{ t3_r0_c2 }}»{{ t3_r0_c4 }}20{{ t3_r0_c6 }}г.для комплексного опробования. | `t4_r2_c0` |
| `form.repeated_commissioning_fibre_2` | {{ t4_r2_c0 }} | `t4_r2_c2` |

## СП_68_Н

Акт приёмки оборудования после комплексного опробования

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.attachments_commissioning_voltage` | указываются в приложении … к акту), выявленные в процессе комплексного опробования, | `p343_1` |
| `form.attachments_voltage` | в приложении … к акту. | `p346_2` |
| `document.date.day` | День подписания | `date_6_2` |
| `document.date.month` | Месяц подписания | `date_6_4` |
| `document.date.year` | Год подписания | `date_6_6` |
| `project.city` | (место составления) | `t0_r6_c0` |
| `representatives.customer.details` | Представитель застройщика (технического заказчика) | `t0_r9_c1` |
| `organisations.customer.full_name` | наименование организации - застройщика (технического заказчика) | `t0_r11_c0` |
| `form.representative` | генерального подрядчика | `t0_r14_c1` |
| `organisations.general_contractor.full_name` | (наименование организации) | `t0_r16_c0` |
| `organisations.installer.full_name` | субподрядных (монтажных) организаций | `t0_r18_c1` |
| `form.organisations_installer_full_name` | (наименование организации) | `t0_r20_c0` |
| `organisations.network_operator.full_name` | эксплуатационной организаций | `t0_r22_c1` |
| `form.organisations_network_operator_full_name` | (наименование организации) | `t0_r24_c0` |
| `form.design_documentation_fibre` | генерального проектировщика | `t0_r26_c1` |
| `organisations.designer.full_name` | (наименование организации) | `t0_r28_c0` |
| `representatives.gsn.details` | (инициалы, фамилия, должность) | `t0_r31_c0` |
| `representatives.supervisory.details` | (инициалы, фамилия, должность) | `t0_r34_c0` |
| `form.equipment_fibre` | 1. Оборудование: | `t0_r36_c1` |
| `form.attachments_voltage_2` | (при необходимости указывается в приложении к акту)] | `t0_r38_c0` |
| `form.voltage_fibre` | смонтированное в | `t0_r40_c1` |
| `form.voltage` | входящего в состав | `t0_r42_c1` |
| `form.work_start.day` | " | `t0_r46_c2` |
| `form.work_start.month` | " | `t0_r46_c4` |
| `form.work_start.year` | 20 | `t0_r46_c6` |
| `form.work_start_2.day` | " | `t0_r46_c10` |
| `form.work_start_2.month` | " | `t0_r46_c12` |
| `form.work_start_2.year` | 20 | `t0_r46_c14` |
| `form.voltage_duration` | в течение | `t0_r48_c1` |
| `form.commissioning_cable_fibre` | и по | `t0_r50_c1` |
| `organisations.commissioner.full_name` | (наименование организации-заказчика, пусконаладочной организации) | `t0_r53_c0` |
| `form.test_date_3.day` | " | `t0_r63_c1` |
| `form.test_date_3.month` | " | `t0_r63_c3` |
| `form.test_date_3.year` | 20 | `t0_r63_c5` |
| `form.additional_statement` | таблица 0, строка 68, ячейка 1 | `t0_r68_c1` |
| `form.additional_statement_continuation` | таблица 0, строка 69, ячейка 1 | `t0_r69_c1` |
| `form.repeated_additional_statement_continuation` | {{ t0_r69_c1 }} | `t0_r69_c9` |

## СП_70_И

Акт испытания конструкций здания и сооружения

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_0_4` |
| `document.date.month` | Месяц подписания | `date_0_6` |
| `document.date.year` | Год подписания | `date_0_8` |
| `project.city` | г. | `t0_r0_c1` |
| `organisations.customer.full_name` | (наименование организации-заказчика, назначившей комиссию) | `t1_r0_c0` |
| `form.test_date.day` | « | `t2_r0_c2` |
| `form.test_date.month` | » | `t2_r0_c4` |
| `form.test_date.year` | 20 | `t2_r0_c6` |
| `form.number` | № | `t2_r0_c9` |
| `representatives.commission_chair.details` | (фамилия, инициалы, должность) | `t3_r0_c0` |
| `representatives.general_contractor.details` | (фамилия, инициалы, должность) | `t4_r0_c0` |
| `representatives.installer.details` | (фамилия, инициалы, должность) | `t5_r0_c0` |
| `form.organisation_fibre` | (наименование организации и ее ведомственная подчиненность) | `t6_r0_c0` |
| `object.name` | (наименование здания, сооружения) | `t7_r0_c0` |
| `form.object_name` | (наименование объекта) | `t8_r0_c0` |
| `project.code` | (шифр проекта) | `t9_r0_c0` |
| `form.design_documentation_organisation_fibre` | (наименование проектной организации и ее ведомственная подчиненность) | `t9_r2_c0` |
| `form.work` | (виды работ) | `t10_r0_c0` |
| `form.organisation_work_fibre` | (наименование организации и перечень видов работ) | `t11_r0_c0` |
| `form.date` | (месяц, год) | `t12_r0_c1` |
| `form.date_2` | (месяц, год) | `t12_r0_c4` |
| `form.number_design_documentation_organisation` | (шифр проекта, наименование организации, ведомственная подчиненность) | `t13_r0_c0` |
| `form.date_test` | (дата начала и окончания испытания) | `t13_r2_c1` |
| `form.test` | (указать результаты испытаний) | `t14_r0_c0` |
| `form.object_name_2` | (наименование здания, сооружения) | `t15_r0_c0` |
| `form.attachments.document_1` | 1 | `t16_r0_c1` |
| `form.attachments.document_2` | 2 | `t17_r0_c1` |
| `form.representative` | Члены комиссии | `t19_r0_c1` |

## СП_70_В

Журнал АКЗ сварных соединений

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.connection_welding_number` | Журнал антикоррозионной защиты сварных соединений №… | `p18_1` |
| `form.organisation_work_fibre` | Наименование организации, выполняющей работы | `t0_r0_c0` |
| `object.name` | Наименование объекта строительства | `t1_r0_c0` |
| `representatives.work_performer.details` | Должность, фамилия, инициалы и подпись лица, ответственного за выполнение работ по антикоррозионной защите сварных соединений и ведение журнала | `t2_r0_c0` |
| `project.documentation.designer_name` | Организация, разработавшая проектную документацию; чертежи КЖ | `t3_r0_c1` |
| `project.code` | Шифр проекта | `t3_r1_c1` |
| `organisations.ppr_designer.full_name` | Организация, разработавшая проект производства работ по антикоррозионной защите сварных соединений | `t3_r2_c1` |
| `form.project_code` | Шифр проекта | `t3_r3_c1` |
| `form.structure_organisation_fibre` | Предприятие, изготовившее конструкции | `t3_r4_c1` |
| `form.number` | Шифр заказа | `t3_r5_c1` |
| `representatives.customer_control.details` | Заказчик (организация), должность, фамилия, инициалы и подпись руководителя (представителя) технического надзора | `t4_r0_c0` |
| `form.work_start.day` | " | `t5_r0_c2` |
| `form.work_start.month` | " | `t5_r0_c4` |
| `form.work_start.year` | 20 | `t5_r0_c6` |
| `form.work_end_2.day` | " | `t6_r0_c2` |
| `form.work_end_2.month` | " | `t6_r0_c4` |
| `form.work_end_2.year` | 20 | `t6_r0_c6` |
| `form.date` | Журнал окончен "{{ t6_r0_c2 }}"{{ t6_r0_c4 }}20{{ t6_r0_c6 }}г. | `rows_7_2` |
| `form.date[].date_work` | Дата выполнения работ | `rows_7_2.c1` |
| `form.date[].materials_structure_coating` | Наименование соединяемых элементов и материал антикоррозионного покрытия закладных изделий, нанесённого на заводе | `rows_7_2.c2` |
| `form.date[].connection_structure_number` | Место или номер (по чертежу или схеме) стыкуемого элемента | `rows_7_2.c3` |
| `form.date[].elevation_representative_position` | Отметка о сдаче и приёмке узла под антикоррозионную защиту (должность, подпись) | `rows_7_2.c4` |
| `form.date[].connection_welding_materials` | Материал покрытия сварных соединений и способ его нанесения | `rows_7_2.c5` |
| `form.date[].temperature_connection_welding` | Атмосферные условия при производстве антикоррозионной защиты сварных соединений (температура воздуха, осадки) | `rows_7_2.c6` |
| `form.date[].representative` | Фамилия и инициалы исполнителя | `rows_7_2.c7` |
| `form.date[].representative_work` | Фамилия и инициалы ответственного за ведение работ по антикоррозионной защите (мастера, производителя работ) | `rows_7_2.c8` |
| `form.date[].thickness_coating_test` | Результаты осмотра качества покрытия. Толщина покрытия | `rows_7_2.c9` |
| `form.date[].representative_2` | Подпись исполнителя | `rows_7_2.c10` |
| `form.date[].representative_work_2` | Подписи о приёмке антикоррозионной защиты (мастера, производителя работ) | `rows_7_2.c11` |
| `form.date[].customer_author_supervision_notes` | Замечания по контрольной проверке (производителя работ, авторского надзора, технического надзора, заказчика) | `rows_7_2.c12` |

## СП_70_Ф

Журнал бетонных работ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.organisation` | Организация | `t0_r0_c0` |
| `object.name` | Наименование объекта | `t1_r0_c0` |
| `form.location` | Адрес | `t2_r0_c0` |
| `form.strength_concrete_structure` | 1. Класс бетона по прочности на сжатие конструктивных элементов | `t3_r0_c0` |
| `form.concrete_volume` | 2. Объём бетона общий | `t4_r0_c1` |
| `form.concrete_volume_fibre` | Объём бетона неармированного | `t5_r0_c1` |
| `form.concrete_volume_fibre_2` | Объём бетона армированного | `t6_r0_c1` |
| `form.representative_work` | Производитель работ | `t7_r0_c1` |
| `form.date` | Начало | `t8_r0_c1` |
| `form.date_2` | Окончание | `t9_r0_c1` |
| `form.date_3` | Окончание{{ t9_r0_c1 }} | `rows_10_3` |
| `form.date_3[].concrete_date_duration` | Дата и время укладки бетона | `rows_10_3.c1` |
| `form.date_3[].elevation_concrete_structure` | Наименование бетонируемой конструкции и ее расположение (оси, отметка) | `rows_10_3.c2` |
| `form.date_3[].concrete_organisation_fibre` | Изготовитель (поставщик) бетонной смеси | `rows_10_3.c3` |
| `form.date_3[].quality_documents_requirements_concrete` | Условное обозначение бетонной смеси и номер документа о качестве по ГОСТ 7473 | `rows_10_3.c4` |
| `form.date_3[].voltage_concrete_structure` | Объем партии бетонной смеси, уложенной в конструкцию, м3 | `rows_10_3.c5` |
| `form.date_3[].temperature` | Температура наружного воздуха, °С | `rows_10_3.c6` |
| `form.date_3[].concrete_method` | Способ и режим твердения бетона | `rows_10_3.c7` |
| `form.date_3[].strength_voltage_concrete` | Проектный класс прочности бетона В / Нормируемый (В норм) | `rows_10_3.c8` |
| `form.date_3[].requirements_strength_voltage` | Прочность бетона в промежуточном возрасте при распалубке или нагружении конструкций (% Внорм) / Фактический (Вф) в проектном возрасте в контролируемой партии конструкций по результатам сплошного неразрушающего контроля прочности по ГОСТ 18105 | `rows_10_3.c9` |
| `form.date_3[].requirements_strength_concrete` | Средняя прочность серий контрольных образцов бетона (МПа) по результатам входного контроля прочности бетонной смеси по пунктам 6.2 и 7.2.4 ГОСТ 18105-2018 или по пункту 8.2.4 ГОСТ 18105-2018 / Нормируемая | `rows_10_3.c10` |
| `form.date_3[].requirements_strength_voltage_2` | Подписи ответственных исполнителей работ по бетонированию и контролю качества / Фактическая в контролируемой партии конструкций по результатам сплошного неразрушающего контроля прочности по ГОСТ 18105 | `rows_10_3.c11` |
| `form.date_3[].voltage` | В промежуточном возрасте | `rows_10_3.c12` |
| `form.date_3[].voltage_design_documentation` | В проектном возрасте | `rows_10_3.c13` |
| `form.date_3[].value` | Графа 14 | `rows_10_3.c14` |

## СП_70_Д

Журнал выполнения монтажных соединений на болтах с контролируемым натяжением

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.bolts_number_test` | на болтах с контролируемым натяжением №… | `p12_1` |
| `form.organisation_work_fibre` | Наименование организации, выполняющей работы | `t0_r0_c1` |
| `object.name` | Наименование объекта строительства | `t1_r0_c0` |
| `representatives.work_performer.details` | Должность, фамилия, инициалы и подпись лица, ответственного за выполнение работ и ведение журнала | `t2_r0_c0` |
| `project.documentation.designer_name` | Организация, разработавшая проектную документацию, чертежи КМ | `t3_r0_c1` |
| `project.code` | Шифр проекта | `t3_r1_c1` |
| `form.strength_diameter_bolts` | Диаметры и классы прочности болтов | `t3_r1_c3` |
| `organisations.ppr_designer.full_name` | Организация, разработавшая проект производства работ | `t3_r2_c1` |
| `form.project_code` | Шифр проекта | `t3_r3_c1` |
| `form.structure_design_documentation_organisation` | Предприятие, разработавшее чертежи КМД и изготовившее конструкции | `t3_r4_c1` |
| `form.number` | Шифр заказа | `t3_r5_c1` |
| `form.strength_diameter_bolts_2` | Диаметры и классы прочности болтов | `t3_r5_c3` |
| `representatives.customer_control.details` | Заказчик (организация), должность, фамилия, инициалы и подпись руководителя (представителя) технического надзора | `t4_r0_c0` |
| `form.work_start.day` | " | `t5_r0_c2` |
| `form.work_start.month` | " | `t5_r0_c4` |
| `form.work_start.year` | 20 | `t5_r0_c6` |
| `form.work_end_2.day` | " | `t6_r0_c2` |
| `form.work_end_2.month` | " | `t6_r0_c4` |
| `form.work_end_2.year` | 20 | `t6_r0_c6` |
| `form.representative_work` | и лиц, ответственных за выполнение работ и ведение журнала | `rows_7_2` |
| `form.representative_work[].representative` | Фамилия, имя, отчество | `rows_7_2.c1` |
| `form.representative_work[].qualification` | Присвоенный разряд | `rows_7_2.c2` |
| `form.representative_work[].welding_number` | Присвоенный номер или знак (клеймо) | `rows_7_2.c3` |
| `form.representative_work[].voltage_date_fibre` | Квалификационное удостоверение / Дата выдачи | `rows_7_2.c4` |
| `form.representative_work[].notes` | Примечание / Кем выдано | `rows_7_2.c5` |
| `form.representative_work[].value` | Графа 6 | `rows_7_2.c6` |
| `form.notes_voltage_welding` | р или знак (клеймо)Квалификационное удостоверениеПримечаниеДата выдачиКем выдано{%tr for item in rows_7_2 %}{{ item.c1 }}{{ item.c2 }}{{ item.c3 }}{{ item.c4 }}{{ item.c5 }}{{ item.c6 }}{%tr endfor %} | `rows_8_3` |
| `form.notes_voltage_welding[].date` | Дата | `rows_8_3.c1` |
| `form.notes_voltage_welding[].voltage_elevation_connection` | Номер чертежа КМД и наименование узла (стыка) в соединении, ряд, ось, отметка | `rows_8_3.c2` |
| `form.notes_voltage_welding[].voltage_bolts_quantity` | Постановка болтов / Число постав-ленных болтов в соеди-нении, шт. | `rows_8_3.c3` |
| `form.notes_voltage_welding[].bolts_number_test` | Результаты контроля / Номер серти-фиката на болты | `rows_8_3.c4` |
| `form.notes_voltage_welding[].method_work_fibre` | Способ обработки контактных поверхностей | `rows_8_3.c5` |
| `form.notes_voltage_welding[].fibre` | Расчётный момент закручивания, кгс*м, угол поворота, град. | `rows_8_3.c6` |
| `form.notes_voltage_welding[].work_fibre` | Качество обработки контактных поверхно-стей | `rows_8_3.c7` |
| `form.notes_voltage_welding[].bolts_quantity_fibre` | Число прове-ренных болтов, шт | `rows_8_3.c8` |
| `form.notes_voltage_welding[].test_fibre` | Результаты проверки момента закручивания, кгс*м, угла поворота, град. | `rows_8_3.c9` |
| `form.notes_voltage_welding[].welding_number_representative` | Номер клейма, подпись бригадира | `rows_8_3.c10` |
| `form.notes_voltage_welding[].bolts_representative_fibre` | Подпись лица, ответственного за постановку болтов | `rows_8_3.c11` |
| `form.notes_voltage_welding[].representative_customer` | Подпись представителя заказчика | `rows_8_3.c12` |

## СП_70_Г

Журнал замоноличивания монтажных стыков и узлов

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.connection_number_fibre` | Журнал замоноличивания монтажных стыков и узлов №… | `p16_1` |
| `form.organisation_work_fibre` | Наименование организации, выполняющей работы | `t0_r0_c1` |
| `object.name` | Наименование объекта строительства | `t1_r0_c0` |
| `representatives.work_performer.details` | Должность, фамилия, инициалы и подпись лица, ответственного за выполнение работы по замоноличиванию и ведение журнала | `t2_r0_c0` |
| `project.documentation.designer_name` | Организация, разработавшая проектную документацию, чертежи КЖ, | `t3_r0_c1` |
| `project.code` | Шифр проекта | `t3_r1_c1` |
| `organisations.ppr_designer.full_name` | Организация, разработавшая проект производства работ по замоноличиванию монтажных стыков и узлов | `t3_r2_c1` |
| `form.project_code` | Шифр проекта | `t3_r3_c1` |
| `form.structure_organisation_fibre` | Предприятие, изготовившее конструкции | `t3_r4_c1` |
| `form.number` | Шифр заказа | `t3_r5_c1` |
| `representatives.customer_control.details` | Заказчик (организация), должность, фамилия, инициалы и подпись руководителя (представителя) технического надзора | `t4_r0_c0` |
| `form.work_start.day` | " | `t5_r0_c2` |
| `form.work_start.month` | " | `t5_r0_c4` |
| `form.work_start.year` | 20 | `t5_r0_c6` |
| `form.work_end_2.day` | " | `t6_r0_c2` |
| `form.work_end_2.month` | " | `t6_r0_c4` |
| `form.work_end_2.year` | 20 | `t6_r0_c6` |
| `form.date` | Журнал окончен "{{ t6_r0_c2 }}"{{ t6_r0_c4 }}20{{ t6_r0_c6 }}г. | `rows_7_2` |
| `form.date[].date` | Дата замоноличивания | `rows_7_2.c1` |
| `form.date[].connection_number_design_documentation` | Наименование стыков и узлов, место или номер по чертежу или схеме | `rows_7_2.c2` |
| `form.date[].concrete` | Заданные марки бетона (раствора) и рабочий состав бетонной (растворной) смеси | `rows_7_2.c3` |
| `form.date[].temperature` | Температура наружного воздуха, °С | `rows_7_2.c4` |
| `form.date[].temperature_voltage_structure` | Температура предварительного обогрева элементов в узлах, °С | `rows_7_2.c5` |
| `form.date[].temperature_voltage_concrete` | Температура бетона в момент укладки, °С | `rows_7_2.c6` |
| `form.date[].test_fibre` | Результата испытаний контрольных образцов | `rows_7_2.c7` |
| `form.date[].date_2` | Дата распалубки | `rows_7_2.c8` |
| `form.date[].representative` | Фамилия и инициалы исполнителя (бригадира), подпись | `rows_7_2.c9` |
| `form.date[].customer_author_supervision_notes` | Замечания производителя работ, авторского надзора, технического надзора заказчика | `rows_7_2.c10` |

## СП_70_Е

Журнал контрольной тарировки динамометрических ключей

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.organisation_fibre` | (наименование строительной организации) | `t0_r0_c0` |
| `object.name` | (наименование объекта строительства) | `t0_r2_c0` |
| `form.location` | (месторасположение объекта) | `t0_r4_c0` |
| `form.test_fibre` | контрольной тарировки динамометрических ключей | `rows_1_2` |
| `form.test_fibre[].date` | Дата | `rows_1_2.c1` |
| `form.test_fibre[].type` | Ключ / тип | `rows_1_2.c2` |
| `form.test_fibre[].number_weight` | Вес груза*, Н (кгс) / номер | `rows_1_2.c3` |
| `form.test_fibre[].test` | Момент от контрольного груза, Нм (кгс*м) | `rows_1_2.c4` |
| `form.test_fibre[].equipment` | Показания на приборе**, деление | `rows_1_2.c5` |
| `form.test_fibre[].representative` | Подпись бригадира | `rows_1_2.c6` |
| `form.test_fibre[].value` | Графа 7 | `rows_1_2.c7` |

## СП_70_А

Журнал работ по монтажу строительных конструкций

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.structure_number_work` | Журнал работ по монтажу строительных конструкций №… | `p16_1` |
| `form.organisation_work_fibre` | Наименование организации, выполняющей работы | `t0_r0_c1` |
| `object.name` | Наименование объекта строительства | `t1_r0_c0` |
| `representatives.work_performer.details` | Должность, фамилия, инициалы и подпись лица, ответственного за монтажные работы и ведение журнала | `t2_r0_c0` |
| `project.documentation.designer_name` | Организация, разработавшая проектную документацию; чертежи КЖ, КМ, КД | `t3_r0_c1` |
| `project.code` | Шифр проекта | `t3_r1_c1` |
| `organisations.ppr_designer.full_name` | Организация, разработавшая проект производства работ | `t3_r2_c1` |
| `form.project_code` | Шифр проекта | `t3_r3_c1` |
| `form.structure_organisation_fibre` | Предприятие, изготовившее конструкции | `t3_r4_c1` |
| `form.number` | Шифр заказа | `t3_r5_c1` |
| `representatives.customer_control.details` | Заказчик (организация), должность, фамилия, инициалы и подпись руководителя (представителя) технического надзора | `t4_r0_c0` |
| `form.structure_volume_work` | Объем работ: стальных конструкций, т | `t5_r0_c1` |
| `form.concrete_structure` | сборных железобетонных конструкций, м³ | `t5_r1_c1` |
| `form.structure` | деревянных конструкций, м³ | `t5_r2_c1` |
| `form.work_start.day` | " | `t6_r0_c2` |
| `form.work_start.month` | " | `t6_r0_c4` |
| `form.work_start.year` | 20 | `t6_r0_c6` |
| `form.work_end_2.day` | " | `t7_r0_c2` |
| `form.work_end_2.month` | " | `t7_r0_c4` |
| `form.work_end_2.year` | 20 | `t7_r0_c6` |
| `form.location` | инженерно-технического персонала, занятого на монтаже здания (сооружения) | `rows_8_1` |
| `form.location[].representative` | Фамилия, имя, отчество | `rows_8_1.c1` |
| `form.location[].qualification_fibre` | Специальность и образование | `rows_8_1.c2` |
| `form.location[].position` | Занимаемая должность | `rows_8_1.c3` |
| `form.location[].date_location_work` | Дата начала работы на объекте | `rows_8_1.c4` |
| `form.location[].elevation_date` | Отметка о прохождении аттестации и дата аттестации | `rows_8_1.c5` |
| `form.location[].date_location_work_2` | Дата окончания работы на объекте | `rows_8_1.c6` |
| `form.certificate_structure_representative` | актов освидетельствования скрытых работ и актов промежуточной приемки ответственных конструкций | `rows_9_2` |
| `form.certificate_structure_representative[].number` | № п/п | `rows_9_2.c1` |
| `form.certificate_structure_representative[].fibre` | Наименование актов | `rows_9_2.c2` |
| `form.certificate_structure_representative[].date_representative` | Дата подписания акта | `rows_9_2.c3` |
| `form.number_2` | {{ item.c1 }} | `t9_r1_c0` |
| `form.number_3` | {{ item.c2 }} | `t9_r1_c1` |
| `form.repeated_number_3` | {{ t9_r1_c1 }} | `t9_r1_c2` |
| `form.number_4` | № п/пНаименование актов Дата подписания акта {{ t9_r1_c0 }}{{ t9_r1_c1 }}{{ t9_r1_c2 }}{%tr for item in rows_9_2 %}{{ item.c1 }}{{ item.c2 }}{%tr endfor %} | `rows_10_2` |
| `form.number_4[].date_work` | Дата выполнения работ, смена | `rows_10_2.c1` |
| `form.number_4[].structure_test_type` | Описание производимых работ, наименование устанавливаемых конструкций, их марка, результаты осмотра конструкций | `rows_10_2.c2` |
| `form.number_4[].equipment_number_location` | Место установки и номера монтажных схем | `rows_10_2.c3` |
| `form.number_4[].passport_structure_number` | Номера технических паспортов на конструкции | `rows_10_2.c4` |
| `form.number_4[].temperature_fibre` | Атмосферные условия (температура окружающего воздуха, осадки, скорость ветра) | `rows_10_2.c5` |
| `form.number_4[].representative` | Фамилия, инициалы исполнителя (бригадира) | `rows_10_2.c6` |
| `form.number_4[].representative_2` | Подпись исполнителя (бригадира) | `rows_10_2.c7` |
| `form.number_4[].customer_author_supervision_notes` | Замечания и предложения по монтажу конструкций руководителей монтажной организации, авторского надзора, технического надзора заказчика | `rows_10_2.c8` |
| `form.number_4[].author_supervision_representative_system` | Подпись мастера (производителя работ), разрешившего производство работ и принявшего работу. Подпись лиц, осуществляющих авторский надзор | `rows_10_2.c9` |

## СП_70_Б

Журнал сварочных работ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.welding_number_work` | Журнал сварочных работ №… | `p16_1` |
| `form.organisation_work_fibre` | Наименование организации, выполняющей работы: | `t0_r0_c1` |
| `object.name` | Наименование объекта строительства: | `t1_r0_c0` |
| `representatives.work_performer.details` | Должность, фамилия, инициалы и подпись лица, ответственного за сварочные работы и ведение журнала | `t2_r0_c0` |
| `project.documentation.designer_name` | Организация, разработавшая проектную документацию; чертежи КМ, КЖ, КМД, КЖД | `t3_r0_c1` |
| `project.code` | Шифр проекта | `t3_r1_c1` |
| `organisations.ppr_designer.full_name` | Организация, разработавшая проект производства сварочных работ | `t3_r2_c1` |
| `form.project_code` | Шифр проекта | `t3_r3_c1` |
| `form.materials_structure_organisation` | Предприятие, изготовившее стальные конструкции, арматурные и закладные изделия | `t3_r4_c1` |
| `form.quality_documents_number` | Шифр документа о качестве | `t3_r5_c1` |
| `representatives.customer_control.details` | Заказчик (организация), должность, фамилия, инициалы и подпись руководителя (представителя) технического надзора | `t4_r0_c0` |
| `form.work_start.day` | " | `t5_r0_c2` |
| `form.work_start.month` | " | `t5_r0_c4` |
| `form.work_start.year` | 20 | `t5_r0_c6` |
| `form.work_end_2.day` | " | `t6_r0_c2` |
| `form.work_end_2.month` | " | `t6_r0_c4` |
| `form.work_end_2.year` | 20 | `t6_r0_c6` |
| `form.welding_work` | инженерно-технического персонала, занятого выполнением сварочных работ | `rows_7_1` |
| `form.welding_work[].representative` | Фамилия, имя, отчество | `rows_7_1.c1` |
| `form.welding_work[].qualification_fibre` | Специальность и образование | `rows_7_1.c2` |
| `form.welding_work[].position` | Занимаемая должность | `rows_7_1.c3` |
| `form.welding_work[].date_location_work` | Дата начала работы на объекте | `rows_7_1.c4` |
| `form.welding_work[].elevation_date` | Отметка о прохождении аттестации и дата | `rows_7_1.c5` |
| `form.welding_work[].date_location_work_2` | Дата окончания работы на объекте | `rows_7_1.c6` |
| `form.welding_location_work` | выполнявших сварочные работы на объекте | `rows_8_2` |
| `form.welding_location_work[].representative` | Фамилия, имя, отчество | `rows_8_2.c1` |
| `form.welding_location_work[].voltage_qualification` | Разряд квалифи-кационный | `rows_8_2.c2` |
| `form.welding_location_work[].welding_number` | Номер личного клейма | `rows_8_2.c3` |
| `form.welding_location_work[].welding_number_work` | Диплом, удостоверение на право производства сварочных работ / номер | `rows_8_2.c4` |
| `form.welding_location_work[].elevation_welding_date` | Отметка о сварке пробных и контрольных образцов / срок действия | `rows_8_2.c5` |
| `form.welding_location_work[].voltage_welding_fibre` | допущен к сварке (швов в пространственном положении) | `rows_8_2.c6` |
| `form.welding_location_work[].value` | Графа 7 | `rows_8_2.c7` |
| `form.voltage_welding_date` | ерсрок действиядопущен к сварке (швов в пространственном положении){%tr for item in rows_8_2 %}{{ item.c1 }}{{ item.c2 }}{{ item.c3 }}{{ item.c4 }}{{ item.c5 }}{{ item.c6 }}{{ item.c7 }}{%tr endfor %} | `rows_9_2` |
| `form.voltage_welding_date[].date_work` | Дата выполнения работ, смена | `rows_9_2.c1` |
| `form.voltage_welding_date[].structure_type_fibre` | Наименование соединяемых элементов; марка стали | `rows_9_2.c2` |
| `form.voltage_welding_date[].welding_structure_number` | Место или номер (по чертежу или схеме) свариваемого элемента | `rows_9_2.c3` |
| `form.voltage_welding_date[].elevation_welding_representative` | Отметка о сдаче и приёмке узла под сварку (должность, фамилия, инициалы, подпись) | `rows_9_2.c4` |
| `form.voltage_welding_date[].welding_materials_number` | Марка применяемых сварочных материалов (проволока, флюс, электроды), номер партии | `rows_9_2.c5` |
| `form.voltage_welding_date[].temperature_fibre` | Атмосферные условия (температура воздуха, осадки, скорость ветра) | `rows_9_2.c6` |
| `form.voltage_welding_date[].welding_number_representative` | Фамилия, инициалы сварщика, номер удостоверения | `rows_9_2.c7` |
| `form.voltage_welding_date[].welding` | Клеймо | `rows_9_2.c8` |
| `form.voltage_welding_date[].connection_welding_representative` | Подписи сварщиков, сваривших соединения | `rows_9_2.c9` |
| `form.voltage_welding_date[].representative_work` | Фамилия, инициалы ответственного за производство работ (мастера, производителя работ) | `rows_9_2.c10` |
| `form.voltage_welding_date[].welding_representative_work` | Подпись руководителя сварочных работ | `rows_9_2.c11` |
| `form.voltage_welding_date[].representative_elevation_connection` | Отметка о приёмке сварного соединения представителя ИЛ | `rows_9_2.c12` |
| `form.voltage_welding_date[].notes_representative_test` | Замечания по контрольной проверке (производителя работ и др.) | `rows_9_2.c13` |

## СП_71_Г

Акт приёмки выполненных работ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.text` | (дата составления документа) | `t0_r0_c0` |
| `object.name` | (наименование здания, сооружения) | `t1_r0_c1` |
| `form.voltage_location` | в осях: | `t1_r2_c1` |
| `form.elevation` | на отм.: | `t1_r2_c4` |
| `object.address` | (район застройки, квартал, улица, N дома и корпуса) | `t2_r0_c1` |
| `form.author_supervision` | - авторского надзора | `t3_r0_c0` |
| `organisations.customer_control.full_name` | - технического надзора заказчика | `t4_r0_c0` |
| `organisations.general_contractor.full_name` | - генеральной подрядной организации | `t5_r0_c0` |
| `representatives.subcontractor.details` | - субподрядной организации | `t6_r0_c0` |
| `organisations.installer.full_name` | (наименование строительно-монтажной организации) | `t7_r0_c1` |
| `form.work_fibre` | (наименование работ) | `t8_r0_c0` |
| `form.requirements_date_number` | (стандарт, проект серии, наименование проектной организации, номера чертежей и дата их составления) | `t9_r0_c0` |
| `form.voltage_work` | 3 Работы выполнены в период с | `t9_r2_c1` |
| `form.voltage_work_2` | по | `t9_r2_c3` |
| `representatives.author_supervision.details` | (Ф.И.О.) | `t11_r0_c3` |
| `representatives.customer_control.details` | (Ф.И.О.) | `t11_r2_c3` |
| `representatives.general_contractor.details` | (Ф.И.О.) | `t11_r4_c3` |
| `form.representatives_subcontractor_details` | (Ф.И.О.) | `t11_r6_c3` |

## СП_71_В

Предписание контроля качества строительно-монтажных работ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.text` | (дата составления документа) | `t0_r0_c0` |
| `object.name` | (наименование здания, сооружения) | `t1_r0_c1` |
| `object.address` | (район застройки, квартал, улица, N дома и корпуса) | `t1_r2_c1` |
| `representatives.inspection_party.details` | (нужное подчеркнуть) (должность, наименование организации, Ф.И.О.) | `t2_r1_c0` |
| `representatives.builder.details` | (должность, наименование организации, Ф.И.О.) | `t3_r0_c0` |
| `organisations.installer.full_name` | (наименование строительно-монтажной организации) | `t3_r2_c1` |
| `form.test_fibre` | На основании проведённого осмотра предложены к выполнению следующие мероприятия: | `rows_4_2` |
| `form.test_fibre[].number` | N п/п | `rows_4_2.c1` |
| `form.test_fibre[].fibre` | Наименование мероприятий | `rows_4_2.c2` |
| `form.test_fibre[].date` | Срок исполнения | `rows_4_2.c3` |
| `form.test_fibre[].elevation` | Отметки о выполнении | `rows_4_2.c4` |
| `representatives.author_supervision.details` | (Ф.И.О.) | `t5_r0_c3` |
| `representatives.customer_control.details` | (Ф.И.О.) | `t5_r2_c3` |
| `representatives.general_contractor.details` | (Ф.И.О.) | `t5_r4_c3` |

## СП_72_Д

Акт приёмки защитного покрытия

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.number` | АКТ № | `t0_r0_c1` |
| `project.city` | г. | `t1_r0_c1` |
| `form.signed_date.day` | " | `t1_r0_c3` |
| `form.signed_date.month` | " | `t1_r0_c5` |
| `form.signed_date.year` | {{ t1_r0_c5 }} | `t1_r0_c7` |
| `form.fibre` | (наименование) | `t2_r0_c0` |
| `representatives.installer.details` | (наименование организации, должность, инициалы, фамилия) | `t3_r0_c0` |
| `representatives.customer.details` | (наименование организации, должность, инициалы, фамилия) | `t4_r0_c0` |
| `representatives.general_contractor.details` | (наименование организации, должность, инициалы, фамилия) | `t5_r0_c0` |
| `form.structure_location_fibre` | 1. | `t6_r0_c1` |
| `form.coating` | 2. | `t7_r0_c1` |
| `form.volume_work` | Объём выполненных работ | `t8_r0_c2` |
| `form.date_work` | Дата начала работ | `t9_r0_c2` |
| `form.date_work_2` | Дата окончания работ | `t10_r0_c2` |
| `form.requirements_voltage_design_documentation` | Работы выполнены в соответствии с проектно-сметной документацией, стандартами, строительными нормами и правилами и отвечают требованиям их приёмки. | `t11_r0_c0` |
| `form.work` | Качество выполненных работ: | `t12_r0_c1` |

## СП_72_Г

Журнал производства антикоррозионных работ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.number` | № | `t0_r0_c1` |
| `object.name` | Наименование объекта | `t1_r0_c0` |
| `form.work_fibre` | Основание для выполнения работ | `t2_r0_c1` |
| `form.representative_work` | Производитель работ | `t3_r0_c1` |
| `form.date_work` | Начало работ | `t4_r0_c1` |
| `form.date_work_2` | Окончание работ | `t4_r0_c3` |
| `form.voltage_fibre` | В журнале пронумеровано | `t5_r0_c1` |
| `form.organisation_representative` | Подпись администрации организации, выдавшей журнал | `rows_7_4` |
| `form.organisation_representative[].date_quantity` | Дата (число, месяц, год), смена | `rows_7_4.c1` |
| `form.organisation_representative[].materials_work_fibre` | Наименование работ и применяемых материалов (пооперационно) | `rows_7_4.c2` |
| `form.organisation_representative[].volume` | Объём | `rows_7_4.c3` |
| `form.organisation_representative[].temperature_materials_duration` | Температура во время выполнения работ, С / на поверхности материала | `rows_7_4.c4` |
| `form.organisation_representative[].materials_fibre` | Применяемые материалы / окружающего воздуха на расстоянии не более 1 м от поверхности | `rows_7_4.c5` |
| `form.organisation_representative[].requirements_thickness_coating` | Число нанесенных слоев и их толщина, мкм / Наименование, ГОСТ, ТУ | `rows_7_4.c6` |
| `form.organisation_representative[].passport_quality_documents_temperature` | Температура С, и продолжительность сушки отдельных слоев покрытия, ч / номер / паспорта качества | `rows_7_4.c7` |
| `form.organisation_representative[].coating_representative_test` | Фамилия и инициалы бригадира (специалиста), выполнявшего защитное покрытие / протокола входного контроля | `rows_7_4.c8` |
| `form.organisation_representative[].certificate_date_number` | Дата и номер акта освидетельствования выполненных работ | `rows_7_4.c9` |
| `form.organisation_representative[].notes` | Примечание | `rows_7_4.c10` |
| `form.organisation_representative[].value` | Графа 11 | `rows_7_4.c11` |
| `form.organisation_representative[].value_2` | Графа 12 | `rows_7_4.c12` |
| `form.organisation_representative[].value_3` | Графа 13 | `rows_7_4.c13` |

## СП_73_В

Акт о проведении гидростатического или манометрического испытания на герметичность

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.system_fibre` | (наименование системы) | `t0_r0_c0` |
| `object.name` | (наименование объекта, здания, цеха) | `t1_r0_c1` |
| `project.city` | Город | `t1_r2_c1` |
| `form.test_date.day` | " | `t1_r2_c3` |
| `form.test_date.month` | " | `t1_r2_c5` |
| `form.test_date.year` | 20 | `t1_r2_c7` |
| `representatives.customer.details` | (наименование организации, должность, инициалы, фамилия) | `t2_r0_c0` |
| `representatives.builder.details` | (наименование организации, должность, инициалы, фамилия) | `t3_r0_c0` |
| `representatives.installer.details` | (наименование организации, должность, инициалы, фамилия) | `t4_r0_c0` |
| `form.number_design_documentation_organisation` | (наименование проектной организации и номера чертежей) | `t5_r0_c1` |
| `form.instrument_method` | (гидростатическим или манометрическим методом) | `t5_r2_c1` |
| `form.pressure_system` | давлением | `t5_r4_c1` |
| `form.pressure_system_2` | ( | `t5_r4_c4` |
| `form.voltage_duration` | в течение | `t5_r5_c1` |
| `form.pressure_drop_pressure_system` | 3. Падение давления составило | `t5_r6_c1` |
| `form.pressure_drop_pressure_system_2` | ( | `t5_r6_c4` |

## СП_73_Д

Акт о проведении индивидуального испытания оборудования

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `object.name` | (наименование объекта строительства, здания, цеха) | `t0_r0_c1` |
| `project.city` | Город | `t1_r0_c1` |
| `form.test_date.day` | " | `t1_r0_c3` |
| `form.test_date.month` | " | `t1_r0_c5` |
| `form.test_date.year` | 20 | `t1_r0_c7` |
| `representatives.customer.details` | (наименование организации, должность, инициалы, фамилия) | `t2_r0_c0` |
| `representatives.builder.details` | (наименование организации, должность, инициалы, фамилия) | `t3_r0_c0` |
| `representatives.installer.details` | (наименование организации, должность, инициалы, фамилия) | `t4_r0_c0` |
| `form.joint_number_system` | (вентиляторы, насосы, муфты, самоочищающиеся фильтры с электроприводом, регулирующие клапаны систем вентиляции (кондиционирования воздуха), теплоутилизаторы, увлажнители, секции нагрева и охлаждения, воздушно-тепловые завесы (указываются номера систем)) | `t5_r0_c0` |
| `form.voltage_duration_test` | прошли испытание в течение | `t5_r2_c1` |

## СП_73_Г

Акт о проведении испытания систем канализации и водостоков

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.system_fibre` | (наименование системы) | `t0_r0_c0` |
| `object.name` | (наименование объекта, здания, цеха) | `t1_r0_c1` |
| `project.city` | Город | `t1_r2_c1` |
| `form.test_date.day` | " | `t1_r2_c3` |
| `form.test_date.month` | " | `t1_r2_c5` |
| `form.test_date.year` | 20 | `t1_r2_c7` |
| `representatives.customer.details` | (наименование организации, должность, инициалы, фамилия) | `t2_r0_c0` |
| `representatives.builder.details` | (наименование организации, должность, инициалы, фамилия) | `t3_r0_c0` |
| `representatives.installer.details` | (наименование организации, должность, инициалы, фамилия) | `t4_r0_c0` |
| `form.number_design_documentation_organisation` | (наименование проектной организации и номера чертежей) | `t5_r0_c1` |
| `form.duration_fibre` | проливом воды путем одновременного открытия | `t6_r0_c2` |
| `form.voltage_equipment_duration` | санитарных приборов, подключенных к проверяемому участку в течение | `t6_r2_c1` |

## СП_73_Е

Паспорт системы вентиляции (кондиционирования воздуха)

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.equipment_system_fibre` | Наименование системы, установки | `t0_r0_c1` |
| `object.name` | Объект | `t0_r1_c1` |
| `form.location` | Адрес | `t0_r2_c1` |
| `form.location_2` | Зона, цех, помещения | `t0_r3_c1` |
| `form.system` | 1. Назначение системы | `t1_r0_c1` |
| `form.equipment_location_system` | 2. Местонахождение оборудования системы | `t1_r1_c1` |
| `form.design_documentation` | По проекту | `t2_r4_c1` |
| `form.repeated_design_documentation` | {{ t2_r4_c1 }} | `t2_r4_c2` |
| `form.repeated_repeated_design_documentation` | {{ t2_r4_c2 }} | `t2_r4_c3` |
| `form.repeated_repeated_repeated_design_documentation` | {{ t2_r4_c3 }} | `t2_r4_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation` | {{ t2_r4_c4 }} | `t2_r4_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation` | {{ t2_r4_c5 }} | `t2_r4_c6` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_design_documentation` | {{ t2_r4_c6 }} | `t2_r4_c7` |
| `form.design_documentation_2` | Фактически | `t2_r5_c1` |
| `form.repeated_design_documentation_2` | {{ t2_r5_c1 }} | `t2_r5_c2` |
| `form.repeated_repeated_design_documentation_2` | {{ t2_r5_c2 }} | `t2_r5_c3` |
| `form.repeated_repeated_repeated_design_documentation_2` | {{ t2_r5_c3 }} | `t2_r5_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_2` | {{ t2_r5_c4 }} | `t2_r5_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_2` | {{ t2_r5_c5 }} | `t2_r5_c6` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_2` | {{ t2_r5_c6 }} | `t2_r5_c7` |
| `form.notes` | Примечание - | `t3_r0_c1` |
| `form.design_documentation_3` | По проекту | `t4_r3_c1` |
| `form.repeated_design_documentation_3` | {{ t4_r3_c1 }} | `t4_r3_c2` |
| `form.repeated_repeated_design_documentation_3` | {{ t4_r3_c2 }} | `t4_r3_c3` |
| `form.repeated_repeated_repeated_design_documentation_3` | {{ t4_r3_c3 }} | `t4_r3_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_3` | {{ t4_r3_c4 }} | `t4_r3_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_3` | {{ t4_r3_c5 }} | `t4_r3_c6` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_3` | {{ t4_r3_c6 }} | `t4_r3_c7` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_3` | {{ t4_r3_c7 }} | `t4_r3_c8` |
| `form.design_documentation_4` | Фактически | `t4_r4_c1` |
| `form.repeated_design_documentation_4` | {{ t4_r4_c1 }} | `t4_r4_c2` |
| `form.repeated_repeated_design_documentation_4` | {{ t4_r4_c2 }} | `t4_r4_c3` |
| `form.repeated_repeated_repeated_design_documentation_4` | {{ t4_r4_c3 }} | `t4_r4_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_4` | {{ t4_r4_c4 }} | `t4_r4_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_4` | {{ t4_r4_c5 }} | `t4_r4_c6` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_4` | {{ t4_r4_c6 }} | `t4_r4_c7` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_4` | {{ t4_r4_c7 }} | `t4_r4_c8` |
| `form.notes_2` | Примечание - | `t5_r0_c1` |
| `form.design_documentation_5` | По проекту | `t6_r2_c1` |
| `form.repeated_design_documentation_5` | {{ t6_r2_c1 }} | `t6_r2_c2` |
| `form.repeated_repeated_design_documentation_5` | {{ t6_r2_c2 }} | `t6_r2_c3` |
| `form.repeated_repeated_repeated_design_documentation_5` | {{ t6_r2_c3 }} | `t6_r2_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_5` | {{ t6_r2_c4 }} | `t6_r2_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_5` | {{ t6_r2_c5 }} | `t6_r2_c6` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_5` | {{ t6_r2_c6 }} | `t6_r2_c7` |
| `form.design_documentation_6` | Фактически | `t6_r3_c1` |
| `form.repeated_design_documentation_6` | {{ t6_r3_c1 }} | `t6_r3_c2` |
| `form.repeated_repeated_design_documentation_6` | {{ t6_r3_c2 }} | `t6_r3_c3` |
| `form.repeated_repeated_repeated_design_documentation_6` | {{ t6_r3_c3 }} | `t6_r3_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_6` | {{ t6_r3_c4 }} | `t6_r3_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_6` | {{ t6_r3_c5 }} | `t6_r3_c6` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_6` | {{ t6_r3_c6 }} | `t6_r3_c7` |
| `form.notes_3` | Примечание - | `t7_r0_c1` |
| `form.design_documentation_7` | По проекту | `t8_r2_c1` |
| `form.repeated_design_documentation_7` | {{ t8_r2_c1 }} | `t8_r2_c2` |
| `form.repeated_repeated_design_documentation_7` | {{ t8_r2_c2 }} | `t8_r2_c3` |
| `form.repeated_repeated_repeated_design_documentation_7` | {{ t8_r2_c3 }} | `t8_r2_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_7` | {{ t8_r2_c4 }} | `t8_r2_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_7` | {{ t8_r2_c5 }} | `t8_r2_c6` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_7` | {{ t8_r2_c6 }} | `t8_r2_c7` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_7` | {{ t8_r2_c7 }} | `t8_r2_c8` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_7` | {{ t8_r2_c8 }} | `t8_r2_c9` |
| `form.design_documentation_8` | Фактически | `t8_r3_c1` |
| `form.repeated_design_documentation_8` | {{ t8_r3_c1 }} | `t8_r3_c2` |
| `form.repeated_repeated_design_documentation_8` | {{ t8_r3_c2 }} | `t8_r3_c3` |
| `form.repeated_repeated_repeated_design_documentation_8` | {{ t8_r3_c3 }} | `t8_r3_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_8` | {{ t8_r3_c4 }} | `t8_r3_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_8` | {{ t8_r3_c5 }} | `t8_r3_c6` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_8` | {{ t8_r3_c6 }} | `t8_r3_c7` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_8` | {{ t8_r3_c7 }} | `t8_r3_c8` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_8` | {{ t8_r3_c8 }} | `t8_r3_c9` |
| `form.notes_4` | Примечание - | `t9_r0_c1` |
| `form.design_documentation_9` | По проекту | `t10_r4_c1` |
| `form.repeated_design_documentation_9` | {{ t10_r4_c1 }} | `t10_r4_c2` |
| `form.repeated_repeated_design_documentation_9` | {{ t10_r4_c2 }} | `t10_r4_c3` |
| `form.repeated_repeated_repeated_design_documentation_9` | {{ t10_r4_c3 }} | `t10_r4_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_9` | {{ t10_r4_c4 }} | `t10_r4_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_9` | {{ t10_r4_c5 }} | `t10_r4_c6` |
| `form.design_documentation_10` | Фактически | `t10_r5_c1` |
| `form.repeated_design_documentation_10` | {{ t10_r5_c1 }} | `t10_r5_c2` |
| `form.repeated_repeated_design_documentation_10` | {{ t10_r5_c2 }} | `t10_r5_c3` |
| `form.repeated_repeated_repeated_design_documentation_10` | {{ t10_r5_c3 }} | `t10_r5_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_10` | {{ t10_r5_c4 }} | `t10_r5_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_10` | {{ t10_r5_c5 }} | `t10_r5_c6` |
| `form.notes_5` | Примечание - | `t11_r0_c1` |
| `form.design_documentation_11` | По проекту | `t12_r4_c1` |
| `form.repeated_design_documentation_11` | {{ t12_r4_c1 }} | `t12_r4_c2` |
| `form.repeated_repeated_design_documentation_11` | {{ t12_r4_c2 }} | `t12_r4_c3` |
| `form.repeated_repeated_repeated_design_documentation_11` | {{ t12_r4_c3 }} | `t12_r4_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_11` | {{ t12_r4_c4 }} | `t12_r4_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_11` | {{ t12_r4_c5 }} | `t12_r4_c6` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_11` | {{ t12_r4_c6 }} | `t12_r4_c7` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_11` | {{ t12_r4_c7 }} | `t12_r4_c8` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_11` | {{ t12_r4_c8 }} | `t12_r4_c9` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_11` | {{ t12_r4_c9 }} | `t12_r4_c10` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_11` | {{ t12_r4_c10 }} | `t12_r4_c11` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_11` | {{ t12_r4_c11 }} | `t12_r4_c12` |
| `form.design_documentation_12` | Фактически | `t12_r5_c1` |
| `form.repeated_design_documentation_12` | {{ t12_r5_c1 }} | `t12_r5_c2` |
| `form.repeated_repeated_design_documentation_12` | {{ t12_r5_c2 }} | `t12_r5_c3` |
| `form.repeated_repeated_repeated_design_documentation_12` | {{ t12_r5_c3 }} | `t12_r5_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_12` | {{ t12_r5_c4 }} | `t12_r5_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_12` | {{ t12_r5_c5 }} | `t12_r5_c6` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_12` | {{ t12_r5_c6 }} | `t12_r5_c7` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_12` | {{ t12_r5_c7 }} | `t12_r5_c8` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_12` | {{ t12_r5_c8 }} | `t12_r5_c9` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_12` | {{ t12_r5_c9 }} | `t12_r5_c10` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_12` | {{ t12_r5_c10 }} | `t12_r5_c11` |
| `form.repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_repeated_design_documentation_12` | {{ t12_r5_c11 }} | `t12_r5_c12` |
| `form.notes_6` | Примечание - | `t13_r0_c1` |
| `form.design_documentation_13` | По проекту | `t14_r2_c1` |
| `form.repeated_design_documentation_13` | {{ t14_r2_c1 }} | `t14_r2_c2` |
| `form.repeated_repeated_design_documentation_13` | {{ t14_r2_c2 }} | `t14_r2_c3` |
| `form.repeated_repeated_repeated_design_documentation_13` | {{ t14_r2_c3 }} | `t14_r2_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_13` | {{ t14_r2_c4 }} | `t14_r2_c5` |
| `form.design_documentation_14` | Фактически | `t14_r3_c1` |
| `form.repeated_design_documentation_14` | {{ t14_r3_c1 }} | `t14_r3_c2` |
| `form.repeated_repeated_design_documentation_14` | {{ t14_r3_c2 }} | `t14_r3_c3` |
| `form.repeated_repeated_repeated_design_documentation_14` | {{ t14_r3_c3 }} | `t14_r3_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_14` | {{ t14_r3_c4 }} | `t14_r3_c5` |
| `form.notes_7` | Примечание - | `t15_r0_c1` |
| `form.design_documentation_15` | По проекту | `t16_r2_c1` |
| `form.repeated_design_documentation_15` | {{ t16_r2_c1 }} | `t16_r2_c2` |
| `form.repeated_repeated_design_documentation_15` | {{ t16_r2_c2 }} | `t16_r2_c3` |
| `form.repeated_repeated_repeated_design_documentation_15` | {{ t16_r2_c3 }} | `t16_r2_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_15` | {{ t16_r2_c4 }} | `t16_r2_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_15` | {{ t16_r2_c5 }} | `t16_r2_c6` |
| `form.design_documentation_16` | Фактически | `t16_r3_c1` |
| `form.repeated_design_documentation_16` | {{ t16_r3_c1 }} | `t16_r3_c2` |
| `form.repeated_repeated_design_documentation_16` | {{ t16_r3_c2 }} | `t16_r3_c3` |
| `form.repeated_repeated_repeated_design_documentation_16` | {{ t16_r3_c3 }} | `t16_r3_c4` |
| `form.repeated_repeated_repeated_repeated_design_documentation_16` | {{ t16_r3_c4 }} | `t16_r3_c5` |
| `form.repeated_repeated_repeated_repeated_repeated_design_documentation_16` | {{ t16_r3_c5 }} | `t16_r3_c6` |
| `form.notes_8` | Примечание - | `t17_r0_c1` |
| `form.flow_rate_location` | Таблица Е.2 - Расход воздуха по помещениям | `rows_18_3` |
| `form.flow_rate_location[].cross_section_number` | Номер мерного сечения | `rows_18_3.c1` |
| `form.flow_rate_location[].location_fibre` | Наименование помещений | `rows_18_3.c2` |
| `form.flow_rate_location[].flow_rate_duration` | Расход воздуха, м³/ч / Фактически | `rows_18_3.c3` |
| `form.flow_rate_location[].deviations_design_documentation` | Невязка, % отклонения от показателей / По проекту | `rows_18_3.c4` |
| `form.flow_rate_location[].value` | Графа 5 | `rows_18_3.c5` |
| `representatives.acceptance_party.details` | (подпись, инициалы, фамилия) | `t19_r0_c0` |
| `representatives.designer.details` | (подпись, инициалы, фамилия) | `t20_r0_c0` |
| `representatives.installer.details` | (подпись, инициалы, фамилия) | `t21_r0_c0` |

## СП_73_Ж

Паспорт системы охлаждения (сплит, VRF, VRV)

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `object.address` | Адрес объекта | `t0_r0_c1` |
| `organisations.installer.full_name` | (наименование организации, | `t0_r1_c1` |
| `representatives.installer.details` | должность, инициалы, фамилия) | `t0_r3_c0` |
| `form.system_fibre` | Наименование системы | `t0_r5_c1` |
| `form.type` | (тип, модель, производитель) | `t0_r6_c1` |
| `form.voltage_percentage` | (230 В±10%) | `t1_r0_c1` |
| `form.temperature` | (не менее 12ºС) | `t1_r4_c1` |
| `form.deviations_percentage_organisation` | (отклонение от заводских параметров не более ±5%) | `t1_r6_c1` |
| `form.refrigerant` | Используемый хладон | `t2_r0_c1` |
| `form.quantity_system` | Количество дозаправленного хладагента, кг | `t3_r0_c1` |
| `form.condensate` | Пролив конденсата | `t4_r0_c1` |
| `form.notes_equipment_fibre` | Наличие дополнительных агрегатов и опций | `t5_r0_c1` |
| `form.completeness` | (дренажная помпа, козырек, защитная сетка, комплект зимнего старта, прочее) | `t5_r1_c0` |
| `form.conclusion` | Заключение | `t6_r0_c1` |
| `representatives.customer.details` | (подпись, инициалы, фамилия) | `t7_r0_c1` |
| `form.representatives_installer_details` | (подпись, инициалы, фамилия) | `t8_r0_c1` |

## СП_74_Б

Акт на приёмку электрозащитной установки в эксплуатацию

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_0_3` |
| `document.date.month` | Месяц подписания | `date_0_5` |
| `document.date.year` | Год подписания | `date_0_7` |
| `project.city` | г. | `t0_r0_c1` |
| `organisations.installer.full_name` | строительно-монтажной организации | `t1_r0_c1` |
| `form.system` | ОЭТС | `t1_r1_c1` |
| `representatives.customer.details` | Заказчика | `t1_r2_c1` |
| `form.foundation_support` | (стене, опоре, фундаменте) | `t2_r0_c0` |
| `form.location` | по адресу | `t3_r0_c1` |
| `form.design_documentation` | (дренажная, катодная и др.) | `t4_r0_c1` |
| `form.length` | Общая протяжённость защищаемых сетей | `t4_r2_c2` |
| `form.quantity_type` | (тип, количество) | `t5_r0_c1` |
| `form.length_type` | (марка, длина) | `t5_r2_c1` |
| `form.resistance_system` | (характеристика, значение сопротивления растеканию) | `t5_r4_c1` |
| `form.quantity_location` | (количество и на каких сооружениях) | `t5_r6_c1` |
| `form.bonding` | Перемычки между | `t5_r8_c1` |

## СП_74_Г

Акт о проведении испытаний трубопроводов на прочность и герметичность

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_0_3` |
| `document.date.month` | Месяц подписания | `date_0_5` |
| `document.date.year` | Год подписания | `date_0_7` |
| `project.city` | г. | `t0_r0_c1` |
| `representatives.installer.details` | (фамилия, имя, отчество, должность) | `t1_r0_c0` |
| `representatives.customer_control.details` | (фамилия, имя, отчество, должность) | `t2_r0_c0` |
| `representatives.network_operator.details` | (фамилия, имя, отчество, должность) | `t3_r0_c1` |
| `organisations.installer.full_name` | (наименование строительно-монтажной организации) | `t4_r0_c0` |
| `form.system` | (гидравлические или пневматические) | `t5_r0_c1` |
| `form.location_number` | (пикета, шахты) № | `t6_r0_c1` |
| `form.location_number_2` | до камеры (пикета, шахты) № | `t6_r0_c3` |
| `form.cable_pipe_fibre` | (наименование трубопровода) | `t6_r1_c1` |
| `form.length` | протяженностью | `t6_r1_c3` |
| `form.length_location_cable` | (пикета, шахты) №{{ t6_r0_c1 }}до камеры (пикета, шахты) №{{ t6_r0_c3 }}трассы{{ t6_r1_c1 }}протяженностью{{ t6_r1_c3 }}м.(наименование трубопровода) | `rows_7_4` |
| `form.length_location_cable[].cable_pipe_fibre` | Трубопровод | `rows_7_4.c1` |
| `form.length_location_cable[].pressure_system` | Испытательное давление, МПа (кгс/см²) | `rows_7_4.c2` |
| `form.length_location_cable[].pressure_duration_system` | Продолжительность, выдержки под испытательным давлением, мин | `rows_7_4.c3` |
| `form.length_location_cable[].pressure_test_system` | Наружный осмотр при давлении, МПа (кгс/см²) | `rows_7_4.c4` |
| `form.date_number_design_documentation` | (наименование проектной организации, номера чертежей и дата их составления) | `t8_r1_c0` |

## СП_74_Д

Акт о проведении промывки (продувки) трубопроводов

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_0_3` |
| `document.date.month` | Месяц подписания | `date_0_5` |
| `document.date.year` | Год подписания | `date_0_7` |
| `project.city` | г. | `t0_r0_c1` |
| `representatives.installer.details` | (фамилия, имя, отчество, должность) | `t1_r0_c0` |
| `representatives.customer_control.details` | (фамилия, имя, отчество, должность) | `t2_r0_c0` |
| `representatives.network_operator.details` | (фамилия, имя, отчество, должность) | `t3_r0_c1` |
| `organisations.installer.full_name` | (наименование строительно-монтажной организации) | `t4_r0_c0` |
| `form.location_number` | участке от камеры (пикета, шахты) № | `t5_r1_c1` |
| `form.location_number_2` | до камеры (пикета, шахты) № | `t5_r1_c3` |
| `form.cable_pipe_fibre` | (наименование трубопровода) | `t5_r2_c0` |
| `form.length` | протяженностью | `t5_r4_c1` |
| `form.pressure_flow_rate_system` | (наименование среды, давление, расход) | `t5_r5_c1` |
| `form.date_number_design_documentation` | (наименование проектной организации, номера чертежей и дата их составления) | `t5_r8_c0` |

## СП_74_А

Акт о растяжке компенсаторов

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_0_3` |
| `document.date.month` | Месяц подписания | `date_0_5` |
| `document.date.year` | Год подписания | `date_0_7` |
| `project.city` | г. | `t0_r0_c1` |
| `object.name` | Объект | `t1_r0_c0` |
| `representatives.customer.details` | (наименование организации, должность, фамилия, инициалы) | `t2_r0_c0` |
| `representatives.builder.details` | (наименование организации, должность, фамилия, инициалы) | `t3_r0_c0` |
| `representatives.network_operator.details` | (наименование организации, должность, фамилия, инициалы) | `t4_r0_c0` |
| `form.location_number_fibre` | составили настоящий акт о том, что на участке тепловых сетей от камеры (пикета) № | `t4_r2_c1` |
| `form.location_number` | таблице, на участке до камеры (пикета, шахты) № | `t5_r1_c1` |
| `form.certificate_voltage_location` | 1.К освидетельствованию и приемке предъявлена растяжка компенсаторов, перечисленных в таблице, на участке до камеры (пикета, шахты) №{{ t5_r1_c1 }}проведена растяжка компенсаторов: | `rows_6_4` |
| `form.certificate_voltage_location[].joint_number_design_documentation` | Номер компенсатора по проектной схеме | `rows_6_4.c1` |
| `form.certificate_voltage_location[].number_design_documentation` | Номер чертежа | `rows_6_4.c2` |
| `form.certificate_voltage_location[].joint_type` | Тип компенсатора | `rows_6_4.c3` |
| `form.certificate_voltage_location[].design_documentation` | Величина растяжки, мм / проектная | `rows_6_4.c4` |
| `form.certificate_voltage_location[].value` | фактическая | `rows_6_4.c5` |
| `form.temperature_joint_fibre` | Растяжка компенсаторов проведена при температуре окружающего воздуха | `t7_r0_c1` |

## СП_76_Б

Акт сдачи-приёмки пусконаладочных работ

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | (город, населённый пункт) | `t0_r0_c0` |
| `organisations.customer.full_name` | (заказчик) | `t0_r2_c0` |
| `object.name` | (объект) | `t0_r4_c0` |
| `representatives.customer.details` | (Ф.И.О., должность) | `t1_r0_c0` |
| `organisations.commissioner.full_name` | от | `t1_r2_c1` |
| `representatives.commissioner.details` | (Ф.И.О., должность) | `t1_r3_c0` |
| `form.voltage_number_fibre` | 1. В соответствии с договором № | `t2_r0_c1` |
| `form.test_date.day` | " | `t2_r0_c4` |
| `form.test_date.month` | " | `t2_r0_c6` |
| `form.test_date.year` | 20 | `t2_r0_c8` |
| `form.voltage_number_fibre_2` | заключённым между | `t2_r1_c1` |
| `form.commissioning_work_fibre` | и | `t2_r2_c1` |
| `form.object_name` | (наименование объекта, электроустановки) | `t2_r4_c0` |
| `form.fibre` | установила следующее: | `t2_r6_c0` |
| `form.equipment_work_fibre` | 2. Работы выполнены на следующих электроустановках | `t3_r0_c0` |
| `form.work_start_2.day` | " | `t4_r0_c3` |
| `form.work_start_2.month` | " | `t4_r0_c5` |
| `form.work_start_2.year` | 20 | `t4_r0_c7` |
| `form.work_end_3.day` | " | `t5_r0_c2` |
| `form.work_end_3.month` | " | `t5_r0_c4` |
| `form.work_end_3.year` | 20 | `t5_r0_c6` |
| `form.commissioning_voltage_system` | 4. Результаты пусконаладочных работ приведены в представленной технической документации в составе: | `t6_r0_c0` |
| `form.notes` | 6. Дополнительные замечания: | `t7_r0_c0` |
| `form.representatives_commissioner_details` | (Ф.И.О.) | `t8_r1_c2` |
| `form.representatives_customer_details` | (Ф.И.О.) | `t8_r1_c6` |

## СП_77_А_2

Акт готовности объекта к производству работ по монтажу систем автоматизации

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_0_3` |
| `document.date.month` | Месяц подписания | `date_0_5` |
| `document.date.year` | Год подписания | `date_0_7` |
| `project.city` | Город | `t0_r0_c1` |
| `object.name` | Объект | `t1_r0_c1` |
| `organisations.general_contractor.full_name` | (наименование генподрядчика) | `t2_r0_c1` |
| `representatives.general_contractor.details` | (должность, Ф.И.О.) | `t2_r2_c1` |
| `organisations.installer.full_name` | (наименование монтирующей организации) | `t2_r4_c1` |
| `representatives.installer.details` | (должность, Ф.И.О.) | `t2_r6_c1` |
| `representatives.customer_control.details` | (должность, Ф.И.О.) | `t2_r9_c0` |
| `form.object_name` | (наименование объекта, стройки) | `t2_r12_c0` |
| `project.documentation.section_description` | (наименование вида монтажных работ и номер проекта) | `t2_r15_c0` |
| `form.notes` | Особые замечания | `t3_r0_c0` |
| `form.attachments` | Приложение | `t4_r0_c0` |
| `form.representatives_general_contractor_details` | Представитель генподрядчика | `t5_r0_c1` |
| `form.representatives_installer_details` | Представитель монтажной организации | `t6_r0_c1` |
| `form.representatives_customer_control_details` | Представитель заказчика | `t7_r0_c1` |

## СП_77_А_8

Акт испытания трубных проводок на герметичность

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.test_date.day` | "…" … 20… г. | `p36_1` |
| `form.test_date.month` | "…" … 20… г. | `p36_2` |
| `form.test_date.year` | "…" … 20… г. | `p36_3` |
| `form.temperature_voltage_test` | в начале испытания … °C | `p83_4` |
| `form.temperature_voltage_test_2` | в конце испытания … °C | `p84_5` |
| `form.plugs_voltage_cable` | Установлено … заглушек. Снято после испытаний … заглушек.Согласно приведенным результатам испытаний и осмотру монтаж трубных проводок выполнен в соответствии с рабочей документацией и СП 77.13330 | `p151_6` |
| `form.plugs_voltage_cable_2` | Установлено … заглушек. Снято после испытаний … заглушек.Согласно приведенным результатам испытаний и осмотру монтаж трубных проводок выполнен в соответствии с рабочей документацией и СП 77.13330 | `p151_7` |
| `project.code` | Проект N | `x_0_16` |
| `form.instruments` | Таблица 1 | `rows_0_21` |
| `form.instruments[].number` | Проект N {{ x_0_16 }} / Данные контрольных приборов / N п/п | `rows_0_21.c1` |
| `form.instruments[].name` | Наименование приборов | `rows_0_21.c2` |
| `form.instruments[].type` | Тип | `rows_0_21.c3` |
| `form.instruments[].serial_number` | N прибора | `rows_0_21.c4` |
| `form.instruments[].scale` | Шкала | `rows_0_21.c5` |
| `form.instruments[].accuracy_class` | Класс | `rows_0_21.c6` |
| `form.instruments[].notes` | Примечание | `rows_0_21.c7` |
| `form.tightness_tests` | Таблица 1 | `rows_0_32` |
| `form.tightness_tests[].number` | Графа 1 | `rows_0_32.c1` |
| `form.tightness_tests[].value` | Графа 2 | `rows_0_32.c2` |
| `form.tightness_tests[].value_2` | Графа 3 | `rows_0_32.c3` |
| `form.tightness_tests[].value_3` | Графа 4 | `rows_0_32.c4` |
| `form.tightness_tests[].value_4` | Графа 5 | `rows_0_32.c5` |
| `form.tightness_tests[].value_5` | Графа 6 | `rows_0_32.c6` |
| `form.tightness_tests[].value_6` | Графа 7 | `rows_0_32.c7` |
| `form.tightness_tests[].value_7` | Графа 8 | `rows_0_32.c8` |
| `form.tightness_tests[].value_8` | Графа 9 | `rows_0_32.c9` |
| `project.city` | Город | `t0_r6_c1` |
| `form.fibre` | (наименование) | `t0_r7_c1` |
| `organisations.customer.full_name` | Представитель организации-заказчика | `t0_r9_c1` |
| `representatives.customer.details` | (наименование организации, должность, Ф.И.О.) | `t0_r10_c0` |
| `organisations.installer.full_name` | Представитель монтирующей организации | `t0_r12_c1` |
| `representatives.installer.details` | (наименование организации, должность, Ф.И.О.) | `t0_r13_c0` |
| `project.documentation.designer_name` | Наименование проектной организации | `t0_r15_c1` |
| `form.repeated_project_documentation_designer_name` | {{ t0_r15_c1 }} | `t0_r15_c2` |
| `form.medium` | Испытательная среда | `t0_r24_c1` |
| `form.representatives_customer_details` | (подпись, Ф.И.О.) | `t0_r37_c1` |
| `form.representatives_installer_details` | (подпись, Ф.И.О.) | `t0_r39_c1` |

## СП_77_А_7

Акт испытания трубных проводок на прочность и плотность

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.test_date.day` | "…" … 20… г. | `p35_1` |
| `form.test_date.month` | "…" … 20… г. | `p35_2` |
| `form.test_date.year` | "…" … 20… г. | `p35_3` |
| `form.plugs_system_fibre` | Установлено … заглушек. | `p93_4` |
| `form.plugs_test` | Снято после испытания … заглушек. | `p94_5` |
| `form.pressure_tests` | Таблица 1 | `rows_0_21` |
| `form.pressure_tests[].number` | N трубной проводки | `rows_0_21.c1` |
| `form.pressure_tests[].name` | Наименование трубной проводки | `rows_0_21.c2` |
| `form.pressure_tests[].inner_diameter_mm` | Внутренний диаметр трубопровода, мм | `rows_0_21.c3` |
| `form.pressure_tests[].length_mm` | Длина трубной проводки, мм | `rows_0_21.c4` |
| `form.pressure_tests[].strength_pressure_mpa` | Испытательное давление на прочность, МПа, (кгс/см²) | `rows_0_21.c5` |
| `form.pressure_tests[].tightness_pressure_mpa` | Испытательное давление на плотность, МПа, (кгс/см²) | `rows_0_21.c6` |
| `form.pressure_tests[].notes` | Примечание | `rows_0_21.c7` |
| `project.city` | Город | `t0_r5_c1` |
| `organisations.customer.full_name` | Предприятие (завод-заказчик) | `t0_r6_c1` |
| `form.fibre` | (наименование) | `t0_r7_c0` |
| `form.organisations_customer_full_name` | Представитель организации-заказчика | `t0_r9_c1` |
| `representatives.customer.details` | (наименование организации, должность, Ф.И.О.) | `t0_r10_c0` |
| `organisations.installer.full_name` | Представитель монтирующей организации | `t0_r12_c1` |
| `representatives.installer.details` | (наименование организации, должность, фамилия, имя, отчество) | `t0_r13_c0` |
| `form.representatives_customer_details` | (подпись, Ф.И.О.) | `t0_r26_c1` |
| `form.representatives_installer_details` | (подпись, Ф.И.О.) | `t0_r28_c1` |

## СП_77_А_9

Акт на обезжиривание труб, арматуры и соединений

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_5_3` |
| `document.date.month` | Месяц подписания | `date_5_5` |
| `document.date.year` | Год подписания | `date_5_7` |
| `project.city` | Город | `t0_r5_c1` |
| `organisations.customer.full_name` | Предприятие (завод-заказчик) | `t0_r7_c1` |
| `object.name` | Цех (объект) | `t0_r8_c1` |
| `organisations.installer.full_name` | Монтирующая организация | `t0_r9_c1` |
| `representatives.customer.details` | От заказчика | `t0_r12_c1` |
| `representatives.installer.details` | От монтажной организации | `t0_r14_c1` |
| `form.materials_fibre` | (наименование изделий) | `t0_r17_c0` |
| `form.method` | (метод обезжиривания) | `t0_r20_c0` |
| `form.representatives_customer_details` | заказчика | `t0_r26_c1` |
| `form.representatives_installer_details` | монтирующей организации | `t0_r28_c1` |

## СП_77_А_5

Акт окончания работ по монтажу систем автоматизации

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_0_3` |
| `document.date.month` | Месяц подписания | `date_0_5` |
| `document.date.year` | Год подписания | `date_0_7` |
| `project.city` | Город | `t0_r0_c1` |
| `organisations.construction_party.full_name` | Генподрядчик (заказчик) | `t1_r0_c1` |
| `representatives.construction_party.details` | (Ф.И.О. должность) | `t2_r3_c0` |
| `organisations.installer.full_name` | от монтажной организации | `t2_r5_c1` |
| `representatives.installer.details` | (Ф.И.О. должность) | `t2_r6_c0` |
| `project.documentation.object_and_project` | (наименование объекта, обозначение рабочей документации) | `t3_r0_c0` |
| `form.work_start.day` | " | `t4_r0_c2` |
| `form.work_start.month` | " | `t4_r0_c4` |
| `form.work_start.year` | 20 | `t4_r0_c6` |
| `form.work_end_2.day` | " | `t5_r0_c2` |
| `form.work_end_2.month` | " | `t5_r0_c4` |
| `form.work_end_2.year` | 20 | `t5_r0_c6` |
| `form.attachments_documentation` | Перечень прилагаемой к акту документации | `t6_r0_c1` |
| `form.attachments_voltage_equipment` | кументацией. Смонтированные приборы, средства автоматизации и вспомогательная аппаратура перечислены в ведомости смонтированных технических средств систем автоматизации, прилагаемой к настоящему акту. | `t6_r1_c0` |

## СП_77_А_1

Акт передачи рабочей документации для производства работ по монтажу систем автоматизации

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_0_3` |
| `document.date.month` | Месяц подписания | `date_0_5` |
| `document.date.year` | Год подписания | `date_0_7` |
| `project.city` | Город | `t0_r0_c1` |
| `organisations.construction_party.full_name` | (наименование генподрядчика, заказчика) | `t1_r0_c1` |
| `representatives.construction_party.details` | (должность, Ф.И.О.) | `t1_r2_c1` |
| `organisations.installer.full_name` | (наименование монтажной организации) | `t1_r4_c1` |
| `representatives.installer.details` | (должность, Ф.И.О.) | `t1_r6_c1` |
| `object.name` | (наименование объекта, стройки) | `t2_r0_c0` |
| `project.documentation.designer_name` | Проектная организация | `t3_r0_c1` |
| `project.code` | Проект № | `t4_r0_c1` |
| `form.drawings` | Переданы в производство работ | `rows_5_2` |
| `form.drawings[].number` | № п/п | `rows_5_2.c1` |
| `form.drawings[].number_design_documentation_fibre` | Наименование и номер чертежа | `rows_5_2.c2` |
| `form.drawings[].quantity` | Количество экз. | `rows_5_2.c3` |
| `form.drawings[].notes` | Примечание | `rows_5_2.c4` |
| `form.representatives_construction_party_details` | Рабочую документацию сдал: | `t6_r0_c1` |
| `form.representatives_installer_details` | Рабочую документацию принял: | `t7_r0_c1` |

## СП_77_А_3

Акт передачи технических средств автоматизации в монтаж

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_0_3` |
| `document.date.month` | Месяц подписания | `date_0_5` |
| `document.date.year` | Год подписания | `date_0_7` |
| `project.city` | Город | `t0_r0_c1` |
| `organisations.customer.full_name` | Заказчик | `t1_r0_c1` |
| `representatives.customer.details` | (должность, Ф.И.О.) | `t2_r0_c1` |
| `organisations.installer.full_name` | (наименование организации) | `t2_r2_c1` |
| `representatives.installer.details` | (должность, Ф.И.О.) | `t2_r4_c1` |
| `project.name` | (наименование вида монтажных работ) | `t3_r0_c0` |
| `form.location_fibre` | (наименование конкретного объекта монтажа) | `t3_r2_c0` |
| `form.materials` | следующие технические средства и материалы: | `rows_4_4` |
| `form.materials[].number` | № п/п | `rows_4_4.c1` |
| `form.materials[].number_design_documentation_fibre` | Наименование и номер чертежа | `rows_4_4.c2` |
| `form.materials[].organisation_type_documentation` | Тип, марка и заводская документация | `rows_4_4.c3` |
| `form.materials[].value` | Единица измерения | `rows_4_4.c4` |
| `form.materials[].quantity` | Количество | `rows_4_4.c5` |
| `form.specification_reference` | (обозначение с "СО1") | `t5_r0_c0` |
| `form.representatives_customer_details` | Представитель заказчика | `t6_r0_c1` |
| `form.representatives_installer_details` | Представитель монтажной организации | `t7_r0_c1` |

## СП_77_А_22

Акт приёмки в эксплуатацию отдельных систем автоматизации

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.form_reference` | Приложение А.22 | `t0_r1_c0` |
| `form.form_reference_2` | Приложение А.22 | `t0_r2_c0` |
| `form.test_date.day` | " | `t1_r0_c1` |
| `form.test_date.month` | " | `t1_r0_c3` |
| `form.test_date.year` | 20 | `t1_r0_c5` |
| `project.city` | Город | `t2_r0_c1` |
| `form.test_date_2.day` | " | `t2_r0_c3` |
| `form.test_date_2.month` | " | `t2_r0_c5` |
| `form.test_date_2.year` | 20 | `t2_r0_c7` |
| `organisations.commissioner.full_name` | (наименование пусконаладочной организации) | `t3_r0_c0` |
| `representatives.customer.details` | (представитель заказчика, Ф.И.О., должность) | `t4_r0_c0` |
| `representatives.commissioner.details` | (представители пусконаладочной организации, Ф.И.О., должность) | `t4_r2_c0` |
| `form.system_fibre` | (наименование систем автоматизации) | `t5_r0_c0` |
| `form.duration` | (времени) | `t6_r0_c1` |
| `form.requirements_design_documentation_fibre` | (наименование нормативного документа, проекта) | `t7_r0_c0` |
| `form.commissioning_work` | Пусконаладочные работы выполнены с оценкой | `t8_r1_c2` |
| `form.attachments.document_1` | 1. | `t9_r0_c1` |
| `form.attachments.document_2` | 2. | `t9_r1_c1` |
| `form.attachments.document_3` | 3. | `t9_r2_c1` |

## СП_77_А_23

Акт приёмки систем автоматизации в эксплуатацию

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.voltage_test_system` | Перечисленные системы автоматизации, прошедшие комплексную наладку, считать принятыми в эксплуатацию с «…» … 20 … г. | `p86_1` |
| `form.voltage_test_system_2` | Перечисленные системы автоматизации, прошедшие комплексную наладку, считать принятыми в эксплуатацию с «…» … 20 … г. | `p86_2` |
| `form.voltage_test_system_3` | Перечисленные системы автоматизации, прошедшие комплексную наладку, считать принятыми в эксплуатацию с «…» … 20 … г. | `p86_3` |
| `form.form_reference` | Приложение А.23 | `t0_r1_c0` |
| `form.form_reference_2` | Приложение А.23 | `t0_r2_c0` |
| `form.test_date.day` | " | `t1_r0_c1` |
| `form.test_date.month` | " | `t1_r0_c3` |
| `form.test_date.year` | 20 | `t1_r0_c5` |
| `project.city` | Город | `t2_r0_c1` |
| `form.test_date_2.day` | " | `t2_r0_c3` |
| `form.test_date_2.month` | " | `t2_r0_c5` |
| `form.test_date_2.year` | 20 | `t2_r0_c7` |
| `organisations.customer.full_name` | (наименование предприятия заказчика) | `t3_r0_c1` |
| `form.commission_order.date.day` | приказом от « | `t4_r0_c1` |
| `form.commission_order.date.month` | » | `t4_r0_c3` |
| `form.commission_order.date.year` | 20 | `t4_r0_c5` |
| `form.commission_order.number` | г. № | `t4_r0_c7` |
| `representatives.commission_chair.details` | (должность, Ф.И.О.) | `t5_r0_c0` |
| `representatives.commissioner.details` | (должность, Ф.И.О.) | `t6_r0_c1` |
| `representatives.supervisory.details` | (должность, Ф.И.О.) | `t6_r2_c1` |
| `form.system_fibre` | (наименование систем или технических средств) | `t7_r0_c0` |
| `form.date_design_documentation_work` | (обозначение проекта, дата разработки) | `t7_r2_c1` |
| `project.documentation.designer_name` | (наименование организации) | `t7_r4_c1` |
| `organisations.commissioner.full_name` | (наименование организации) | `t7_r6_c1` |
| `form.work_start.day` | с « | `t8_r0_c1` |
| `form.work_start.month` | » | `t8_r0_c3` |
| `form.work_start.year` | 20 | `t8_r0_c5` |
| `form.work_end.day` | г. по « | `t8_r0_c7` |
| `form.work_end.month` | » | `t8_r0_c9` |
| `form.work_end.year` | 20 | `t8_r0_c11` |
| `form.attachments_documentation` | Перечень прилагаемой к акту документации: | `t9_r0_c0` |

## СП_77_А_13

Журнал по сварке трубопроводов

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.test_date.day` | "…" … 20… г. | `p260_1` |
| `form.test_date.month` | "…" … 20… г. | `p260_2` |
| `form.test_date.year` | "…" … 20… г. | `p260_3` |
| `form.test_date_2.day` | "…" … 20… г. | `p261_4` |
| `form.test_date_2.month` | "…" … 20… г. | `p261_5` |
| `form.test_date_2.year` | "…" … 20… г. | `p261_6` |
| `form.welding` | Таблица 1 | `rows_0_8` |
| `form.welding[].number` | (N чертежей расположения трубопроводов, буквенно-цифровое обозначение участков) / № п/п | `rows_0_8.c1` |
| `form.welding[].connection_welding_number` | (наименование и месторасположение объекта) / Номер сварного соединения по чертежам (исполнительным чертежам) | `rows_0_8.c2` |
| `form.welding[].cable_pipe_number` | Номер трубной проводки | `rows_0_8.c3` |
| `form.welding[].welding_representative` | Ф.И.О. сварщика, личное клеймо | `rows_0_8.c4` |
| `form.welding[].quality_documents_number_type` | Марка стали (композиция марок сталей), НД, № сертификата | `rows_0_8.c5` |
| `form.welding[].thickness_diameter_cable` | Наружный диаметр элемента трубопровода и толщина стенки DнхS, мм | `rows_0_8.c6` |
| `form.welding[].temperature_voltage_welding` | Дата сварки, температурные условия в рабочей зоне, °С | `rows_0_8.c7` |
| `form.welding[].welding_method` | Способ сварки | `rows_0_8.c8` |
| `form.welding[].quality_documents_welding_materials` | Сварочные материалы (марка электрода, сварочной проволоки, защитный газ, флюс), НД, № сертификата | `rows_0_8.c9` |
| `form.welding[].heating` | Режим предварительного и сопутствующего подогрева | `rows_0_8.c10` |
| `form.welding[].elevation_welding_test` | Отметка о контроле корня шва | `rows_0_8.c11` |
| `form.welding[].conclusion_welding_date` | Стилоскопирование металла шва, № заключения, дата | `rows_0_8.c12` |
| `form.welding[].welding_representative_2` | Ф.И.О. оператора-термиста, личное клеймо | `rows_0_8.c13` |
| `form.welding[].connection_welding_heating` | № диаграммы по журналу термообработки сварных соединений | `rows_0_8.c14` |
| `form.welding[].welding_date_number` | Замер твердости металла шва, N включения, дата | `rows_0_8.c15` |
| `form.welding[].conclusion_elevation_connection` | Отметка о годности сварного соединения по внешнему осмотру и измерениям | `rows_0_8.c16` |
| `form.welding[].conclusion_connection_welding` | Способ и результаты неразрушающего контроля сварного соединения, N заключения, дата | `rows_0_8.c17` |
| `form.welding[].conclusion_voltage_welding` | Результаты замера ферритной фазы в металле шва, N заключения, дата | `rows_0_8.c18` |
| `project.documentation.object_description` | (наименование и месторасположение объекта) | `t0_r2_c1` |
| `form.voltage_cable_pipe` | (N чертежей расположения трубопроводов, буквенно-цифровое обозначение участков) | `t0_r4_c0` |
| `organisations.installer.full_name` | (наименование монтажной организации) | `t0_r16_c10` |
| `representatives.site_manager.details` | (подпись, Ф.И.О.) | `t0_r18_c11` |
| `representatives.welding_supervisor.details` | (подпись, Ф.И.О.) | `t0_r18_c13` |
| `form.installation_manager_date` | "{{ p260_1 }}" {{ p260_2 }} 20{{ p260_3 }} г. | `t0_r19_c10` |
| `form.representatives_welding_supervisor_details` | (подпись, Ф.И.О.) | `t0_r19_c12` |

## СП_77_А_14

Заключение о проверке качества сварных швов, произведённой методом капиллярной дефектоскопии

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.welding` | …сварочная лаборатория | `p11_1` |
| `form.conclusion_number` | ЗАКЛЮЧЕНИЕ N … | `p15_2` |
| `form.weld_inspections` | Таблица 1 | `rows_0_16` |
| `form.weld_inspections[].defects_number_test` | Дефектоскопист / Удостоверение / Результаты контроля / N блока | `rows_0_16.c1` |
| `form.weld_inspections[].position_number` | Поз. КИП | `rows_0_16.c2` |
| `form.weld_inspections[].thickness_diameter_pipe` | Место контроля (наименование участка, диаметр и толщина стенки трубы) | `rows_0_16.c3` |
| `form.weld_inspections[].date_test` | Дата контроля | `rows_0_16.c4` |
| `form.weld_inspections[].connection_number` | Номер стыка | `rows_0_16.c5` |
| `form.weld_inspections[].welding_representative` | Ф.И.О. сварщика | `rows_0_16.c6` |
| `form.weld_inspections[].welding` | Клеймо сварщика | `rows_0_16.c7` |
| `form.weld_inspections[].defects` | Обнаружены дефекты | `rows_0_16.c8` |
| `form.weld_inspections[].conclusion_test` | Заключение по контролю | `rows_0_16.c9` |
| `form.welding_2` | {{ p11_1 }}сварочная лаборатория | `t0_r3_c1` |
| `object.name` | Объект | `t0_r6_c1` |
| `form.repeated_object_name` | {{ t0_r6_c1 }} | `t0_r6_c2` |
| `project.code` | Проект | `t0_r7_c1` |
| `form.repeated_project_code` | {{ t0_r7_c1 }} | `t0_r7_c2` |
| `form.defects_test_completeness` | Контроль производился дефектоскопическим комплектом | `t0_r9_c1` |
| `form.test_class` | Класс чувствительности контроля | `t0_r10_c1` |
| `form.defects` | Дефектоскопист | `t0_r11_c1` |
| `form.fibre` | Удостоверение | `t0_r12_c1` |
| `representatives.flaw_detector.details` | (Ф.И.О.) | `t0_r33_c2` |
| `representatives.laboratory_head.details` | (Ф.И.О.) | `t0_r35_c2` |

## СП_77_А_10

Опись технической документации

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `organisations.installer.full_name` | Монтажная организация | `t0_r5_c1` |
| `organisations.customer.full_name` | Предприятие (заказчик) | `t0_r6_c1` |
| `object.name` | Цех (объект) | `t0_r7_c1` |
| `form.documentation` | Вид документации | `t0_r8_c1` |
| `form.certificate` | Свидетельство о монтаже | `t0_r12_c2` |
| `form.repeated_certificate` | {{ t0_r12_c2 }} | `t0_r12_c3` |
| `form.connection_cable_pipe` | Акт на обезжиривание труб, арматуры и соединений (для кислородопроводов) | `t0_r13_c2` |
| `form.repeated_connection_cable_pipe` | {{ t0_r13_c2 }} | `t0_r13_c3` |
| `form.welding_fibre` | Схема расположения сварных швов | `t0_r14_c2` |
| `form.repeated_welding_fibre` | {{ t0_r14_c2 }} | `t0_r14_c3` |
| `form.cable_pipe_welding` | Журнал по сварке трубопроводов | `t0_r15_c2` |
| `form.repeated_cable_pipe_welding` | {{ t0_r15_c2 }} | `t0_r15_c3` |
| `form.conclusion` | Заключение ВИК | `t0_r16_c2` |
| `form.repeated_conclusion` | {{ t0_r16_c2 }} | `t0_r16_c3` |
| `form.defects_conclusion` | Заключение цветной дефектоскопии | `t0_r17_c2` |
| `form.repeated_defects_conclusion` | {{ t0_r17_c2 }} | `t0_r17_c3` |
| `form.defects_conclusion_method` | Заключение дефектоскопии ультразвуковым или радиографическим методом | `t0_r18_c2` |
| `form.repeated_defects_conclusion_method` | {{ t0_r18_c2 }} | `t0_r18_c3` |
| `form.defects_connection_welding` | Список сварщиков, дефектоскопистов и сборщиков резьбовых соединений | `t0_r19_c2` |
| `form.repeated_defects_connection_welding` | {{ t0_r19_c2 }} | `t0_r19_c3` |
| `form.welding_fibre_2` | Копии удостоверений сварщиков | `t0_r20_c2` |
| `form.repeated_welding_fibre_2` | {{ t0_r20_c2 }} | `t0_r20_c3` |
| `form.defects_connection_fibre` | Копии удостоверений дефектоскопистов, сборщиков резьбовых соединений | `t0_r21_c2` |
| `form.repeated_defects_connection_fibre` | {{ t0_r21_c2 }} | `t0_r21_c3` |
| `form.quality_documents_cable_pipe` | Документация входного контроля на изделия и материалы для трубных проводок. Сертификаты | `t0_r22_c2` |
| `form.repeated_quality_documents_cable_pipe` | {{ t0_r22_c2 }} | `t0_r22_c3` |
| `form.strength_density_cable` | Акт испытания трубных проводок на прочность и плотность | `t0_r23_c2` |
| `form.repeated_strength_density_cable` | {{ t0_r23_c2 }} | `t0_r23_c3` |
| `form.tightness_pressure_drop_pressure` | Акт испытания трубных проводок на герметичность с определением падения давления за время испытания | `t0_r24_c2` |
| `form.repeated_tightness_pressure_drop_pressure` | {{ t0_r24_c2 }} | `t0_r24_c3` |
| `representatives.documentation_sender.details` | Документацию сдал: | `t0_r26_c1` |
| `representatives.documentation_recipient.details` | Документацию принял: | `t0_r28_c1` |

## СП_77_А_19_МУФТА

Паспорт на смонтированную соединительную муфту

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.test_date.day` | "…" … 20… г. | `p58_1` |
| `form.test_date.month` | "…" … 20… г. | `p58_2` |
| `form.test_date.year` | "…" … 20… г. | `p58_3` |
| `project.city` | Город | `t0_r6_c1` |
| `object.name` | Объект | `t0_r7_c1` |
| `organisations.installer.full_name` | Монтажная организация | `t0_r8_c1` |
| `project.code` | Проект | `t0_r9_c1` |
| `form.joint_number` | Муфта N | `t0_r10_c1` |
| `form.optical_lines` | Оптические линии связи | `t0_r11_c1` |
| `form.location` | Регенерационный участок | `t0_r12_c1` |
| `form.cable_type` | Марка оптического кабеля | `t0_r13_c1` |
| `representatives.worker.details` | Монтаж производил | `t0_r14_c1` |
| `representatives.installer.details` | (наименование монтажной организации, Ф.И.О. исполнителей, дата) | `t0_r15_c0` |
| `form.repair` | Сведения о ремонте | `t0_r17_c1` |
| `form.instrument_equipment` | Измерительные приборы | `t0_r18_c1` |
| `form.number_fibre` | НомерОВ | `t0_r19_c0` |
| `form.fibres.fibre_1.attenuation_ab_db` | 1 | `t0_r22_c1` |
| `form.fibres.fibre_1.attenuation_ba_db` | {{ t0_r22_c1 }} | `t0_r22_c2` |
| `form.fibres.fibre_2.attenuation_ab_db` | 2 | `t0_r23_c1` |
| `form.fibres.fibre_2.attenuation_ba_db` | {{ t0_r23_c1 }} | `t0_r23_c2` |
| `form.fibres.fibre_3.attenuation_ab_db` | 3 | `t0_r24_c1` |
| `form.fibres.fibre_3.attenuation_ba_db` | {{ t0_r24_c1 }} | `t0_r24_c2` |
| `form.fibres.fibre_4.attenuation_ab_db` | 4 | `t0_r25_c1` |
| `form.fibres.fibre_4.attenuation_ba_db` | {{ t0_r25_c1 }} | `t0_r25_c2` |
| `form.fibres.fibre_5.attenuation_ab_db` | 5 | `t0_r26_c1` |
| `form.fibres.fibre_5.attenuation_ba_db` | {{ t0_r26_c1 }} | `t0_r26_c2` |
| `form.fibres.fibre_6.attenuation_ab_db` | 6 | `t0_r27_c1` |
| `form.fibres.fibre_6.attenuation_ba_db` | {{ t0_r27_c1 }} | `t0_r27_c2` |
| `form.fibres.fibre_7.attenuation_ab_db` | 7 | `t0_r28_c1` |
| `form.fibres.fibre_7.attenuation_ba_db` | {{ t0_r28_c1 }} | `t0_r28_c2` |
| `form.fibres.fibre_8.attenuation_ab_db` | 8 | `t0_r29_c1` |
| `form.fibres.fibre_8.attenuation_ba_db` | {{ t0_r29_c1 }} | `t0_r29_c2` |
| `representatives.inspector.details` | (должность, Ф.И.О.) | `t0_r30_c2` |

## СП_77_А_19_УЧАСТОК

Паспорт регенерационного участка

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.test_date.day` | "…" … 20… г. | `p58_1` |
| `form.test_date.month` | "…" … 20… г. | `p58_2` |
| `form.test_date.year` | "…" … 20… г. | `p58_3` |
| `form.fibre_measurements` | Таблица 1 | `rows_0_18` |
| `form.fibre_measurements[].fibre_number` | Графа 1 | `rows_0_18.c1` |
| `form.fibre_measurements[].power_ab_input` | НаправлениеА-Б / Pвх | `rows_0_18.c2` |
| `form.fibre_measurements[].power_ab_output` | Направление Б-А / Pвых | `rows_0_18.c3` |
| `form.fibre_measurements[].power_ba_input` | Затухание А, дБ / Pвх | `rows_0_18.c4` |
| `form.fibre_measurements[].power_ba_output` | Pвых | `rows_0_18.c5` |
| `form.fibre_measurements[].attenuation_db` | Графа 6 | `rows_0_18.c6` |
| `form.fibre_measurements[].measured_on` | Графа 7 | `rows_0_18.c7` |
| `project.city` | Город | `t0_r6_c1` |
| `object.name` | Объект | `t0_r7_c1` |
| `organisations.installer.full_name` | Монтажная организация | `t0_r8_c1` |
| `project.code` | Проект | `t0_r9_c1` |
| `form.location` | Регенерационный участок | `t0_r10_c1` |
| `form.number_fibre` | НомерОВ | `t0_r11_c0` |
| `representatives.inspector.details` | (должность, Ф.И.О.) | `t0_r23_c2` |

## СП_77_А_4

Протокол входного контроля оптического кабеля

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.drum_number` | № бухты барабана | `t0_r0_c1` |
| `form.cable_type` | Марка кабеля | `t1_r0_c1` |
| `form.quantity_fibre` | Количество оптических волокон | `t2_r0_c1` |
| `form.type` | тип | `t3_r0_c2` |
| `form.number_organisation` | заводской № | `t3_r1_c2` |
| `form.date` | год выпуска | `t3_r2_c2` |
| `form.fibre_measurements` | Прибор:тип{{ t3_r0_c2 }}заводской №{{ t3_r1_c2 }}год выпуска{{ t3_r2_c2 }} | `rows_4_5` |
| `form.fibre_measurements[].length` | Длина ОК, М L | `rows_4_5.c1` |
| `form.fibre_measurements[].number_fibre` | Номер ОВ | `rows_4_5.c2` |
| `form.fibre_measurements[].passport_attenuation_fibre` | Паспортные данные (затухание ОВ, А, ДБ) | `rows_4_5.c3` |
| `form.fibre_measurements[].power` | Мощность излучения по индикатору, ДБ / Авх | `rows_4_5.c4` |
| `form.fibre_measurements[].attenuation` | Результаты расчёта / Затухания А, ДБ / Авых | `rows_4_5.c5` |
| `form.fibre_measurements[].attenuation_date_test` | Дата проверки / Коэффициент затухания α, ДБ/км | `rows_4_5.c6` |
| `form.fibre_measurements[].value` | Графа 7 | `rows_4_5.c7` |
| `form.fibre_measurements[].value_2` | Графа 8 | `rows_4_5.c8` |
| `representatives.inspector.details` | (подпись, Ф.И.О. исполнителя) | `t5_r0_c1` |

## СП_77_А_19_ИЗМЕРЕНИЯ

Протокол измерения параметров смонтированного оптического кабеля

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_6_3` |
| `document.date.month` | Месяц подписания | `date_6_5` |
| `document.date.year` | Год подписания | `date_6_7` |
| `project.city` | Город | `t0_r6_c1` |
| `object.name` | Объект | `t0_r8_c1` |
| `project.code` | Проект | `t0_r10_c1` |
| `representatives.installer.details` | (должность, Ф.И.О.) | `t0_r12_c1` |
| `representatives.customer.details` | (должность, Ф.И.О.) | `t0_r15_c1` |
| `form.design_documentation` | рабочие чертежи | `t0_r19_c1` |
| `form.deviations_design_documentation` | отступление от рабочих чертежей | `t0_r20_c1` |
| `form.conclusion` | 4. Заключение о сдаче-приемке ВОЛС | `t0_r24_c0` |
| `form.acceptance_conclusion` | таблица 0, строка 26, ячейка 0 | `t0_r26_c0` |
| `form.representatives_installer_details` | Представители монтажной организации | `t0_r28_c1` |
| `form.repeated_representatives_installer_details` | {{ t0_r28_c1 }} | `t0_r28_c3` |
| `organisations.customer.full_name` | Заказчик | `t0_r32_c1` |
| `form.repeated_organisations_customer_full_name` | {{ t0_r32_c1 }} | `t0_r32_c3` |

## СП_77_А_16

Протокол измерения сопротивления изоляции

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_6_3` |
| `document.date.month` | Месяц подписания | `date_6_5` |
| `document.date.year` | Год подписания | `date_6_7` |
| `form.instruments` | Таблица 1 | `rows_0_22` |
| `form.instruments[].number` | № п/п | `rows_0_22.c1` |
| `form.instruments[].name` | Наименование прибора | `rows_0_22.c2` |
| `form.instruments[].type` | Тип | `rows_0_22.c3` |
| `form.instruments[].serial_number` | № прибора | `rows_0_22.c4` |
| `form.instruments[].scale` | Шкала | `rows_0_22.c5` |
| `form.instruments[].accuracy_class` | Класс | `rows_0_22.c6` |
| `form.instruments[].notes` | Примечание | `rows_0_22.c7` |
| `form.insulation_measurements` | Таблица 1 | `rows_0_33` |
| `form.insulation_measurements[].number` | Графа 1 | `rows_0_33.c1` |
| `form.insulation_measurements[].drawing_mark` | Графа 2 | `rows_0_33.c2` |
| `form.insulation_measurements[].cable_type` | Графа 3 | `rows_0_33.c3` |
| `form.insulation_measurements[].cores_and_cross_section` | Графа 4 | `rows_0_33.c4` |
| `form.insulation_measurements[].between_cores_mohm` | между проводами (жилами) | `rows_0_33.c5` |
| `form.insulation_measurements[].to_ground_mohm` | относи-тельно земли | `rows_0_33.c6` |
| `form.insulation_measurements[].notes` | Графа 7 | `rows_0_33.c7` |
| `project.city` | Город | `t0_r6_c1` |
| `object.name` | Объект | `t0_r8_c1` |
| `organisations.customer.full_name` | Заказчик | `t0_r10_c1` |
| `organisations.installer.full_name` | Монтажная организация | `t0_r12_c1` |
| `project.code` | Проект № | `t0_r14_c1` |
| `representatives.customer.details` | Заказчика | `t0_r39_c1` |
| `representatives.installer.details` | Монтирующей организации | `t0_r41_c1` |

## СП_77_А_18

Протокол испытаний давлением

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.pressure_tests` | Таблица 1 | `rows_0_29` |
| `form.pressure_tests[].equipment_location_fibre` | Место установки или участок | `rows_0_29.c1` |
| `form.pressure_tests[].class` | Класс взрывоопасной зоны | `rows_0_29.c2` |
| `form.pressure_tests[].pressure_system` | Фактическое давление, кПа | `rows_0_29.c3` |
| `form.pressure_tests[].pressure_drop_pressure_test` | Падение давления при испытании, кПа | `rows_0_29.c4` |
| `form.pressure_tests[].duration_test` | Продолжительность испытания, мин | `rows_0_29.c5` |
| `form.pressure_tests[].notes` | Примечание | `rows_0_29.c6` |
| `object.name` | (объект) | `t0_r6_c0` |
| `project.city` | (город) | `t0_r6_c3` |
| `organisations.installer.full_name` | (монтажная организация) | `t0_r8_c0` |
| `organisations.customer.full_name` | (заказчик) | `t0_r8_c3` |
| `form.division` | (подразделение) | `t0_r10_c0` |
| `form.object_name` | (объект) | `t0_r10_c3` |
| `form.location` | (участок) | `t0_r12_c0` |
| `form.test_date.day` | " | `t0_r12_c2` |
| `form.test_date.month` | " | `t0_r12_c4` |
| `form.test_date.year` | 20 | `t0_r12_c6` |
| `representatives.installer.details` | (должность, Ф.И.О.) | `t0_r17_c0` |
| `representatives.customer.details` | (должность, Ф.И.О.) | `t0_r20_c0` |
| `form.instrument_pressure_number` | Испытательное давление измерено манометром, заводской номер | `t0_r33_c1` |
| `form.accuracy_class` | точности | `t0_r34_c1` |
| `form.explosion_zone` | таблица 0, строка 37, ячейка 0 | `t0_r37_c0` |
| `form.class` | класса | `t0_r37_c2` |

## СП_77_А_17

Протокол прогрева кабелей на барабанах

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_6_3` |
| `document.date.month` | Месяц подписания | `date_6_5` |
| `document.date.year` | Год подписания | `date_6_7` |
| `form.cable_heating` | Таблица 1 | `rows_0_16` |
| `form.cable_heating[].drum_number` | Номер барабана | `rows_0_16.c1` |
| `form.cable_heating[].voltage_cross_section_cable` | Марка кабеля, напряжение, кВ, сечение, мм2 | `rows_0_16.c2` |
| `form.cable_heating[].length_cable` | Длина кабеля, м | `rows_0_16.c3` |
| `form.cable_heating[].temperature_voltage_cable` | Прогрев кабелей внутри обогреваемых помещений / температура в помещении, °С | `rows_0_16.c4` |
| `form.cable_heating[].temperature_cable_heating` | Прогрев кабелей электрическим током, А / температура внешних витков кабеля при температуре наружного воздуха / продолжительность прогрева, ч | `rows_0_16.c5` |
| `form.cable_heating[].temperature` | -10°С | `rows_0_16.c6` |
| `form.cable_heating[].temperature_2` | ниже-10°С | `rows_0_16.c7` |
| `project.city` | Город | `t0_r6_c1` |
| `object.name` | Объект | `t0_r8_c1` |
| `organisations.installer.full_name` | Монтажная организация | `t0_r10_c1` |
| `representatives.worker.details` | Прогрев произвёл | `t0_r19_c1` |
| `form.repeated_representatives_worker_details` | {{ t0_r19_c1 }} | `t0_r19_c3` |
| `representatives.installer.details` | монтирующей организации | `t0_r23_c1` |
| `form.repeated_representatives_installer_details` | {{ t0_r23_c1 }} | `t0_r23_c3` |

## СП_77_А_11

Свидетельство о монтаже трубных проводок

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.certificate_number` | Свидетельство № | `t0_r3_c1` |
| `project.documentation.object_description` | (наименование и месторасположение объекта, отделение, корпус) | `t0_r5_c0` |
| `form.cable_pipe_class` | (назначение и категория трубопровода) | `t0_r7_c0` |
| `form.voltage_number_fibre` | (буквенно-цифровое обозначение) | `t0_r9_c0` |
| `form.pressure_temperature_system` | (рабочая среда, рабочее давление, рабочая температура) | `t0_r11_c0` |
| `organisations.installer.full_name` | (наименование монтажной организации) | `t0_r14_c1` |
| `form.voltage_work_documentation` | в полном соответствии с рабочей документацией, разработанной | `t0_r16_c1` |
| `project.documentation.designer_name` | (наименование проектной организации) | `t0_r17_c0` |
| `form.cable_pipe_equipment` | (номера чертежей расположения оборудования трубопроводов) | `t0_r19_c1` |
| `form.cable_pipe_welding` | Вид сварки, применявшейся при монтаже трубных проводок | `t0_r22_c1` |
| `form.connection_welding_volume` | Методы и объем контроля качества сварных соединений | `t0_r23_c1` |
| `form.notes_voltage_work` | Примечание - Пункты 3 и 4 заполняются при наличии указаний в рабочей документации или НТД о необходимости выполнения указанных работ | `t0_r30_c0` |
| `representatives.installer.details` | (Ф.И.О.) | `t0_r36_c2` |
| `representatives.chief_engineer.details` | (Ф.И.О.) | `t0_r38_c2` |

## СП_77_А_15

Список сварщиков, дефектоскопистов и сборщиков резьбовых соединений

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `form.specialists` | Таблица 1 | `rows_0_11` |
| `form.specialists[].number` | (месторасположение объекта, отделение, корпус) / (наименование монтажной организации) / N п/п | `rows_0_11.c1` |
| `form.specialists[].representative` | Ф.И.О. | `rows_0_11.c2` |
| `form.specialists[].qualification` | Специальность, вид операции | `rows_0_11.c3` |
| `form.specialists[].qualification_2` | Разряд | `rows_0_11.c4` |
| `form.specialists[].welding` | Личное клеймо | `rows_0_11.c5` |
| `form.specialists[].number_2` | Номер | `rows_0_11.c6` |
| `form.specialists[].connection_number_test` | N журнала учета и проверки качества контрольных соединений | `rows_0_11.c7` |
| `form.specialists[].representative_2` | Образец подписи | `rows_0_11.c8` |
| `project.documentation.object_description` | (месторасположение объекта, отделение, корпус) | `t0_r5_c0` |
| `organisations.installer.full_name` | (наименование монтажной организации) | `t0_r7_c0` |
| `form.column_notes.number` | {{ item.c1 }} | `t0_r10_c0` |
| `form.column_notes.full_name` | {{ item.c2 }} | `t0_r10_c1` |
| `form.column_notes.speciality` | {{ item.c3 }} | `t0_r10_c2` |
| `form.column_notes.qualification` | {{ item.c4 }} | `t0_r10_c3` |
| `form.column_notes.stamp` | {{ item.c5 }} | `t0_r10_c4` |
| `form.column_notes.certificate` | {{ item.c6 }} | `t0_r10_c5` |
| `form.column_notes.test_log` | {{ item.c7 }} | `t0_r10_c6` |
| `form.column_notes.signature` | {{ t0_r10_c6 }} | `t0_r10_c7` |
| `representatives.welding_supervisor.details` | (Ф.И.О.) | `t0_r27_c2` |
| `representatives.installer.details` | (Ф.И.О.) | `t0_r29_c2` |

## СП_77_А_24

Акт приостановки (консервации) монтажных работ по системам автоматизации

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `p32_1` |
| `document.date.month` | Месяц подписания | `p32_2` |
| `document.date.year` | Год подписания | `p32_3` |
| `form.accepted_work` | Выполненные работы и технические средства, переданные заказчику | `rows_0_17` |
| `form.accepted_work[].number` | № п/п | `rows_0_17.c1` |
| `form.accepted_work[].customer_test_work` | Выполненные и принятые заказчиком работы | `rows_0_17.c2` |
| `form.accepted_work[].customer_system` | Технические средства систем автоматизации, переданные заказчику | `rows_0_17.c3` |
| `form.accepted_work[].notes` | Примечание | `rows_0_17.c4` |
| `project.city` | Город | `t0_r5_c1` |
| `organisations.customer.full_name` | (наименование объекта, заказчик) | `t0_r6_c1` |
| `form.number_design_documentation_organisation` | (наименование и номер проекта, проектная организация) | `t0_r8_c1` |
| `representatives.construction_party.details` | Представитель генподрядчика (заказчика): должность и Ф.И.О. | `t0_r10_c1` |
| `representatives.installer.details` | Представитель монтажной организации: должность и Ф.И.О. | `t0_r12_c1` |
| `form.representatives_installer_details` | Представитель монтажной организации: должность и Ф.И.О.; подпись от руки | `t0_r19_c1` |
| `form.representatives_construction_party_details` | Представитель генподрядчика (заказчика): должность и Ф.И.О.; подпись от руки | `t0_r21_c1` |

## СП_77_А_20

Разрешение на монтаж технических средств автоматизации

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `document.date.day` | День подписания | `date_0_3` |
| `document.date.month` | Месяц подписания | `date_0_5` |
| `document.date.year` | Год подписания | `date_0_7` |
| `project.city` | Город | `t0_r0_c1` |
| `object.name` | Объект | `t1_r0_c1` |
| `project.code` | Проект | `t1_r1_c1` |
| `organisations.customer.full_name` | (наименование заказчика) | `t1_r2_c1` |
| `form.defects` | Недоделки, подлежащие устранению: строка 1 | `t2_r0_c0` |
| `form.defects_2` | Недоделки, подлежащие устранению: строка 2 | `t2_r1_c0` |
| `form.defects_3` | Недоделки, подлежащие устранению: строка 3 | `t2_r2_c0` |
| `representatives.customer.details` | Представитель заказчика: должность и Ф.И.О. | `t3_r0_c1` |

## СП_77_А_21

Ведомость смонтированных технических средств автоматизации

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `project.city` | Город | `city` |
| `document.date.day` | day | `day` |
| `document.date.month` | month | `month` |
| `document.date.year` | year | `year` |
| `object.name` | object_name | `object_name` |
| `project.name` | project_name | `project_name` |
| `companies` | companies | `companies` |
| `companies[].role` | role | `companies.role` |
| `companies[].name` | name | `companies.name` |
| `form.materials` | materials | `materials` |
| `form.materials[].no` | no | `materials.no` |
| `form.materials[].spec_no` | spec_no | `materials.spec_no` |
| `form.materials[].item_name` | item_name | `materials.item_name` |
| `form.materials[].item_type` | item_type | `materials.item_type` |
| `form.materials[].serial_no` | serial_no | `materials.serial_no` |
| `form.materials[].notes` | notes | `materials.notes` |
| `recipient.text` | Принял | `recipient` |
| `consignor.text` | Сдал | `consignor` |

## РЕЕСТР_ИТД

Реестр исполнительной документации

| Свойство DOCX | Подпись поля | Ключ карточки |
| --- | --- | --- |
| `object.name` | object_name | `object_name` |
| `project.code` | project_code | `project_code` |
| `project.name` | project_name | `project_name` |
| `form.registry` | registry | `registry` |
| `form.registry[].no` | no | `registry.no` |
| `form.registry[].name` | name | `registry.name` |
| `form.registry[].number` | number | `registry.number` |
| `form.registry[].date` | date | `registry.date` |
| `form.registry[].sheets_count` | sheets_count | `registry.sheets_count` |
| `form.registry[].note` | note | `registry.note` |
| `form.registry[].number_date` | number_date | `registry.number_date` |
| `form.registry[].organization` | organization | `registry.organization` |
| `form.registry[].pages` | pages | `registry.pages` |
