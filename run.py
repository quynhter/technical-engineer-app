#!/usr/bin/env python3
"""Запуск веб-приложения ИТД: python run.py --help."""
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


def main():
    # Plain python3 uses the application's environment when it is available.
    # An explicitly activated environment and container Python retain precedence.
    python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if sys.prefix == sys.base_prefix and python.is_file():
        os.execv(str(python), [str(python), str(ROOT / 'run.py'), *sys.argv[1:]])
    try:
        from app.itd.web import main as start_server
    except ImportError:
        print('Не удалось загрузить зависимости приложения. Создайте отдельное окружение '
              'и установите зависимости из корня проекта:\n\n'
              '  python3 -m venv .venv\n'
              '  .venv/bin/python -m pip install -r app/requirements.txt\n'
              '  .venv/bin/python run.py --public --port 8080 --no-browser\n\n'
              'Если окружение уже создано, повторите установку с --force-reinstall. '
              'Пакеты из ~/.local для запуска не требуются.', file=sys.stderr)
        return 1
    start_server()
    return 0


if __name__ == '__main__':
    sys.exit(main())
