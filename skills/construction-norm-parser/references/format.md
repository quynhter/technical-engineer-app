# Формат локальной базы

Команды выполняются как `app/.venv/bin/python -m app.itd <команда>`
(Windows: `app/.venv/Scripts/python.exe`). Каноническая документация:
`app/knowledge/README.md`. Структура: `<root>/<corpus>/*.md`, `rules.jsonl`.
README.md не индексируется. Во входе только UTF-8; символическая ссылка
вместо файла не допускается. Файл в корне без подпапки набора не принимается.

Поддерживается ограниченный YAML: `key: value`, строки и массивы в синтаксисе
JSON в одну строку. Вложенные YAML-объекты, теги, anchors, многострочные значения
не поддерживаются. Произвольные дополнительные поля сохраняются в metadata.

Markdown (пример структуры, не нормативное утверждение):

```markdown
---
doc_id: "ШИФР ИЗ ОРИГИНАЛА"
doc_title: "Название из оригинала"
edition: "Редакция из оригинала"
section: "Раздел"
clause: "4.2"
mandatory_level: "не проверено"
work_types: ["вид работ"]
itd_forms: []
control_type: "измерительный"
keywords: ["поисковый термин"]
source_original: "путь к оригиналу или архивный ID"
source_sha256: "SHA-256 оригинала"
source_page: null
source_sheet: null
source_locator: "пункт 4.2, таблица 2, примечание 1"
verification_status: "unverified"
---
### ШИФР — пункт 4.2

Дословный текст, таблица и относящиеся к ним примечания.

Контекст ссылки (пояснение): полная ссылка с шифром и пунктом.
```

JSONL: один JSON-объект на строку. Обязательны непустые строки doc_id, clause,
work_category, subject, parameter, operator, raw_text. required_itd — массив
строк; min_value/max_value — конечные числа или null. Для понятных числовых
правил используй gte/lte/eq/range; сложные текстовые условия сохраняй текстом.
Числовое правило не исполняется индексом. Пример с вымышленными данными:

```json
{"doc_id":"ТЕСТ","clause":"4.2","section":"Испытания","work_category":"испытания","subject":"образец","parameter":"температура","operator":"gte","min_value":5,"max_value":null,"unit":"°C","condition":"только при условиях пункта 4.2; пример, не норматив","control_method":"измерительный","required_itd":[],"raw_text":"Учебная выдержка, заменить оригиналом.","source_original":null,"source_sha256":null,"source_page":null,"source_locator":"4.2","edition":null,"verification_status":"unverified"}
```

`knowledge-export --output db/work/knowledge-export.jsonl` выдаёт единый
JSONL с id, корпусом, видом записи, текстом и исходными metadata для дальнейшей
загрузки. Команда не перезаписывает существующий файл. ID без явного бизнес-ID
привязан к пути и порядковому номеру чанка/строки, при перестановке меняется.
Не используй его как постоянную деловую ссылку: сохраняй также пункт и хеш.
