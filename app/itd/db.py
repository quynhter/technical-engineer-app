"""Подключение, миграции и операции с согласованной частью модели.

Даты передаются в ISO YYYY-MM-DD и проверяются календарём Python.
Остальные сущности добавляются следующими миграциями после уточнения требований.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path


MIGRATIONS = Path(__file__).parent / "migrations"
DATE_FIELDS = ("smr_start", "smr_end", "pnr_start", "pnr_end")


@contextmanager
def connect(path: str | Path, *, transaction=True):
    """Транзакция с внешними ключами и закрытием соединения."""
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            if transaction:
                connection.execute("BEGIN")
            yield connection
    finally:
        connection.close()


def initialize(path: str | Path) -> None:
    """Применить новые миграции; старую схему без истории не преобразовывать молча."""
    with connect(path, transaction=False) as connection:
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if tables and "schema_migrations" not in tables:
            raise ValueError(
                "В БД обнаружена прежняя схема без истории миграций. "
                "Для неё потребуется отдельный перенос данных."
            )
        # Каждая миграция и её отметка применяются одной транзакцией.
        for migration in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations "
                    "(version INTEGER PRIMARY KEY, name TEXT NOT NULL)"
                )
                version = int(migration.name.split("_", 1)[0])
                exists = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = ?", (version,)
                ).fetchone()
                if not exists:
                    # Завершённые SQL-операторы выполняются без executescript,
                    # чтобы не создавать неявный COMMIT перед миграцией.
                    statement = ""
                    for line in migration.read_text(encoding="utf-8").splitlines(True):
                        statement += line
                        if sqlite3.complete_statement(statement):
                            connection.execute(statement)
                            statement = ""
                    if statement.strip():
                        raise ValueError(f"Незавершённый SQL в {migration.name}")
                    connection.execute(
                        "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                        (version, migration.name),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise


def required_text(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label}: требуется текст")
    value = value.strip()
    if not value:
        raise ValueError(f"Не заполнено поле: {label}")
    return value


def calendar_date(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Дата должна быть строкой ГГГГ-ММ-ДД или null")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"Некорректная дата: {value}; требуется ГГГГ-ММ-ДД") from error
    if parsed.isoformat() != value:
        raise ValueError(f"Требуется дата ГГГГ-ММ-ДД: {value}")
    return value


def add_object(connection: sqlite3.Connection, name: str) -> int:
    cursor = connection.execute(
        "INSERT INTO objects (name) VALUES (?)", (required_text(name, "объект"),)
    )
    return cursor.lastrowid


def add_project(
    connection: sqlite3.Connection, *, object_id: int, section_code: str,
    code: str, name: str, city: str | None = None,
    smr_start: str | None = None, smr_end: str | None = None,
    pnr_start: str | None = None, pnr_end: str | None = None,
) -> int:
    section_code = required_text(section_code, "раздел").upper()
    dates = tuple(calendar_date(value) for value in (smr_start, smr_end, pnr_start, pnr_end))
    for label, start, end in (("СМР", dates[0], dates[1]), ("ПНР", dates[2], dates[3])):
        if start is not None and end is not None and start > end:
            raise ValueError(f"{label}: начало позже окончания")
    cursor = connection.execute(
        "INSERT INTO projects "
        "(object_id, section_code, code, name, city, smr_start, smr_end, pnr_start, pnr_end) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (object_id, section_code, required_text(code, "шифр РД"),
         required_text(name, "наименование раздела"), city, *dates),
    )
    return cursor.lastrowid


def atomic_operation(function):
    """Откат одной операции даже при перехвате ошибки вызывающим кодом."""
    from functools import wraps
    @wraps(function)
    def run(connection, *args, **kwargs):
        name='itd_'+function.__name__
        connection.execute('SAVEPOINT '+name)
        try:
            result=function(connection,*args,**kwargs)
            connection.execute('RELEASE '+name)
            return result
        except Exception:
            connection.execute('ROLLBACK TO '+name)
            connection.execute('RELEASE '+name)
            raise
    return run
