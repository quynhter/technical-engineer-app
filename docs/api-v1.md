# HTTP API v1 — этап 2

Один FastAPI/Uvicorn-сервер для команды, один выбранный сервером контекст БД.
Ни имя инструмента, ни тело обычного запроса не выбирают другую БД. Глобальное
переключение остаётся отдельным действием администратора.

Новый префикс `/api/v1/`; старые пути сохранены на время переноса разделов.
Оба набора вызывают одни сервисы и проверяют роли на сервере. Новые разделы
используют только v1; прежние адреса удаляются после проверки и согласования.
Статические файлы сохраняют прежние пути. CLI web и его флаги не изменены.

## Ошибки и вход

Заголовок X-ITD-Token содержит токен сеанса. Он не передаётся в URL и не логируется.
Код входа передаётся только в JSON POST login; код и токены в хранилище — SHA-256.
Сеансы находятся в `<стартовая БД>.accounts.sqlite3`, переживают перезапуск,
имеют абсолютный срок 8 часов и простой 30 минут, максимум 10 сеансов на человека.
При смене роли, удалении, ротации кода и переключении БД выполняется отзыв.
Самостоятельная история схемы аккаунтов — account_schema_migrations, версия 1.
Обычный GET не мигрирует и не меняет режим деловой БД. WAL включается initialize
или подготовкой сервера; перед переходом DELETE→WAL предусмотрен SQLite backup.

У v1 ошибка имеет вид `{"error":{"code":"invalid_input","message":"…"}}`.
Дополнительно могут возвращаться fields, journal_dates, session_expired.
Основные коды: forbidden, session_expired, invalid_input, body_too_large,
not_found, internal_error. Старый API сохраняет строковый error для совместимости.
JSON должен быть объектом; ограничение тела 48 МБ, превышение — 413.
Host сверяется с адресом принявшего соединение; чужой Origin отклоняется.
Ответы no-store, CSP, nosniff и no-referrer, загрузки с UTF-8 filename*.

## Соответствие маршрутов

Н — наблюдатель, Р — редактор/администратор, А — администратор.
Все не публичные операции требуют действующего сеанса.

| Метод | Прежний путь | Путь v1 | Минимальная роль |
|---|---|---|---|
| GET | `/api/account` | `/api/v1/account` | Н (свой профиль) |
| GET | `/api/admin` | `/api/v1/admin` | А |
| GET | `/api/bootstrap` | `/api/v1/bootstrap` | Н |
| GET | `/api/configuration` | `/api/v1/configuration` | Р |
| GET | `/api/context` | `/api/v1/context` | Н |
| GET | `/api/download` | `/api/v1/download` | Р |
| GET | `/api/knowledge` | `/api/v1/knowledge` | Н |
| GET | `/api/original` | `/api/v1/original` | Р |
| GET | `/api/package` | `/api/v1/package` | Р |
| GET | `/api/project` | `/api/v1/project` | Н |
| GET | `/api/status` | `/api/v1/status` | Н |
| GET | `/api/workspace` | `/api/v1/workspace` | Н |
| POST | `/api/account/profile` | `/api/v1/account/profile` | Н (свой профиль) |
| POST | `/api/account/rotate` | `/api/v1/account/rotate` | Н (свой профиль) |
| POST | `/api/act` | `/api/v1/act` | Р |
| POST | `/api/action` | `/api/v1/action` | Н только context; прочие действия Р |
| POST | `/api/activate` | `/api/v1/activate` | Р |
| POST | `/api/admin/create` | `/api/v1/admin/create` | А |
| POST | `/api/admin/delete` | `/api/v1/admin/delete` | А |
| POST | `/api/admin/role` | `/api/v1/admin/role` | А |
| POST | `/api/admin/rotate` | `/api/v1/admin/rotate` | А |
| POST | `/api/admin/settings` | `/api/v1/admin/settings` | А |
| POST | `/api/configuration/preview` | `/api/v1/configuration/preview` | Р |
| POST | `/api/entry` | `/api/v1/entry` | Р |
| POST | `/api/fact` | `/api/v1/fact` | Р |
| POST | `/api/fact-status` | `/api/v1/fact-status` | Р |
| POST | `/api/files/apply` | `/api/v1/files/apply` | Р |
| POST | `/api/files/plan` | `/api/v1/files/plan` | Р |
| POST | `/api/files/recover` | `/api/v1/files/recover` | Р |
| POST | `/api/generate` | `/api/v1/generate` | Р |
| POST | `/api/incoming-day` | `/api/v1/incoming-day` | Р |
| POST | `/api/login` | `/api/v1/login` | Публичный вход |
| POST | `/api/logout` | `/api/v1/logout` | Н (свой профиль) |
| POST | `/api/ojr-title` | `/api/v1/ojr-title` | Р |
| POST | `/api/quality` | `/api/v1/quality` | Р |
| POST | `/api/registry/export` | `/api/v1/registry/export` | Р |
| POST | `/api/resource-import/commit` | `/api/v1/resource-import/commit` | Р |
| POST | `/api/resource-import/preview` | `/api/v1/resource-import/preview` | Р |
| POST | `/api/resource-import/stage` | `/api/v1/resource-import/stage` | Р |
| POST | `/api/review` | `/api/v1/review` | Р |
| POST | `/api/save` | `/api/v1/save` | Р |
| POST | `/api/statement` | `/api/v1/statement` | Р |
| POST | `/api/upload` | `/api/v1/upload` | Р |
| POST | `/api/versions/create` | `/api/v1/versions/create` | Р |
| POST | `/api/versions/delete` | `/api/v1/versions/delete` | Р |
| POST | `/api/versions/ensure` | `/api/v1/versions/ensure` | Р |
| POST | `/api/versions/list` | `/api/v1/versions/list` | Р |
| POST | `/api/versions/regenerate` | `/api/v1/versions/regenerate` | Р |
| POST | `/api/versions/save` | `/api/v1/versions/save` | Р |
| POST | `/api/work-fact` | `/api/v1/work-fact` | Р |

Новые маршруты: GET `/api/v1/events` — авторизованный SSE; GET
`/api/v1/openapi.json` — авторизованная спецификация. SSE отправляет workspace
с ревизией и workspace_id, комментарии heartbeat; после отзыва сеанса —
session-expired и завершение. Ожидание клиента не держит транзакцию или lock БД.
Токен нужен в заголовке: EventSource без авторизационного заголовка не подходит,
используйте потоковый fetch с AbortController. Это поток состояния, не LLM-чат.

## Экспорт

POST registry/export — явная запись/выпуск DOCX. GET download выдаёт проверенный
зарегистрированный файл; GET package собирает выбранные выпуски и связанные
приложения без повторной генерации. Имена выпущенных файлов в ZIP совпадают
с именами на диске. GET не меняет деловую БД и audit_events. Обязательный аудит
ZIP записывается в отдельный read_events; при ошибке аудита ZIP не выдаётся.
После таймаута POST результат неизвестен: сначала прочитайте состояние,
не повторяйте выпуск автоматически. Новый frontend-клиент этого не делает.

Проверки: app/tests/test_http_api.py (ASGI), test_read_boundaries.py и
старые тесты запуска (реальные локальные сокеты). Все fixtures временные.
