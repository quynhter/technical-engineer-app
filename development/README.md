# Разработка

`frontend/` — браузерные тесты; исходники React, зависимости и сборка находятся в `../app/frontend/`.
`tests/` — Python-тесты и воспроизводимые fixtures. `scripts/` — запуск проверок,
аудит связей и подготовка шаблонов. `docs/` — исследования и материалы разработки шаблонов.
`work/` — локальные отчёты, снимки и тестовые файлы; `repository-backups/` — локальный архив репозитория.
Окружение Python находится в `.venv/`. Рабочие данные, архивы документов и выпуски остаются рядом с БД.

Из корня проекта:

```bash
PYTHONPATH=app development/.venv/bin/python -m unittest discover -s development/tests -v
development/.venv/bin/python development/scripts/run_tests.py
PYTHONPATH=app development/.venv/bin/python development/scripts/audit_relationships.py --write-map
```

Сборка интерфейса: `npm ci` и `npm run build` из `app/frontend`. Тесты: `npm test` из `development/frontend` (используют зависимости `app/frontend/node_modules`); `npm test` из `app/frontend` запускает те же тесты.
Настройки проверок: `ruff check --config development/ruff.toml app development`,
`eslint --config development/eslint.config.mjs app/itd/web_assets app/frontend development/frontend`.

[Рабочая документация и знания](../ai/README.md).
