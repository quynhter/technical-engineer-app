# Интерфейс Astryx

Сборка включена в `app/itd/web_assets/design.js` и `design.css`. Для запуска Python-приложения Node.js и доступ к CDN не нужны. Это локальный bundle Astryx с зависимостями, а не независимая реализация библиотеки. Версии зафиксированы в package-lock.json; лицензии поставляются в design-LICENSE.txt. Open Sans берётся из локальных файлов приложения.

Для изменения интерфейса: `npm ci`, затем `npm run build` из этой папки. Короткая проверка: `npm test`. В git включаются исходники, lockfile и готовые assets, без node_modules.

`design.jsx` использует один Theme/InternationalizationProvider и React-порталы: удаление страницы не сбрасывает глобальную тему. `adapters.jsx` связывает Date Input, Collapsible, Clickable Card, Banner и Dialog с исходными DOM-формами. Диалоги сохраняют createWorkspaceDialog и проверки beforeClose. Поля сохраняют исходные узлы и слушатели, получают полную рамку TextInput/TextArea.

`design.jsx` монтирует оболочку и компоненты вокруг существующих DOM-форм, сохраняя их значения и обработчики. `astryx-tables.jsx` подключает настоящий Table и плагины Astryx к модели общих таблиц: resizing, column settings, filtering, sorting, selection и pagination. Специальные редактируемые таблицы документов сохраняют структуру бланка. Предпочтения таблиц хранятся в localStorage под ключом itd.astryx.tables.v1, без деловых данных.

Обновление Astryx выполняется явно с пересборкой и проверкой API. Шесть официальных тем доступны в шапке; шрифт во всех темах принудительно Open Sans.
