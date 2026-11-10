"""Запуск из любой папки: python /путь/к/app/scripts/start_web.py."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from app.itd.web import main

if __name__ == '__main__':
    main()
