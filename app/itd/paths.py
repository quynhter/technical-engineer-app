"""Расположение инструментов, локальных данных и дерева ИТД."""
from contextvars import ContextVar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
itd_root = ContextVar('itd_root', default=None)
previous_itd_roots = ContextVar('previous_itd_roots', default=())


def database_workspace(database):
    parent = Path(database).resolve().parent
    return parent.parent if parent.name in ('db', 'data') else parent


def data_directory(database):
    return Path(database).resolve().parent


def default_database():
    return ROOT / 'db' / 'itd.db'


def default_templates():
    return Path(__file__).resolve().parent.parent / 'templates'


def document_root(workspace):
    return itd_root.get() or workspace / 'ИТД'


def relative_or_absolute(workspace, path):
    return str(path.relative_to(workspace)) if path.is_relative_to(workspace) else str(path)
