"""Локальный воспроизводимый индекс нормативных материалов, отдельно от деловых данных.

Исходные MD/JSONL не изменяются. Содержимое нормативов никогда не исполняется.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = '1'
NOTICE = ('Материалы подготовлены ИИ; редакция, применимость и точность требуют проверки '
          'по оригиналу. mandatory_level и required_itd — данные источника, '
          'а не согласованные требования объекта. Автоматический нормоконтроль не выполняется.')


def default_root():
    return ROOT / 'app' / 'knowledge'


def default_index(database):
    return Path(database).resolve().parent / 'knowledge.db'


def _json(text):
    def reject(value):
        raise ValueError(f'Недопустимое число JSON: {value}')
    return json.loads(text, parse_constant=reject)


def _text(data, key):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'Поле {key}: требуется непустой текст')
    return value


def _strings(data, key):
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f'Поле {key}: требуется массив строк')
    return value


def _frontmatter(lines):
    """Ограниченный YAML: скаляры и однострочные массивы в синтаксисе JSON.

    Без тегов, alias, многострочных значений и исполняемых конструкторов.
    """
    data = {}
    for line in lines:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = re.fullmatch(r'([a-z][a-z0-9_]*):\s*(.*)', line)
        if not match:
            raise ValueError('YAML: ожидается key: value; массивы задавайте как JSON в одной строке')
        key, value = match.groups()
        if key in data:
            raise ValueError(f'YAML: повтор поля {key}')
        if value.startswith(('"', '[')) or value in ('null', 'true', 'false'):
            data[key] = _json(value)
        elif value.startswith("'") and value.endswith("'"):
            data[key] = value[1:-1].replace("''", "'")
        elif value and not value.startswith(('!', '&', '*', '{', '|', '>')):
            data[key] = value
        else:
            raise ValueError(f'YAML: неподдерживаемое значение {key}; используйте JSON-строку')
    return data


def _entry(corpus, relative, sha, line, kind, metadata, body, ordinal):
    _text(metadata, 'doc_id')
    _text(metadata, 'clause')
    work = _strings(metadata, 'work_types') if kind == 'chunk' else [_text(metadata, 'work_category')]
    forms = _strings(metadata, 'itd_forms' if kind == 'chunk' else 'required_itd')
    if kind == 'chunk':
        _strings(metadata, 'keywords')
    else:
        for key in ('parameter', 'subject', 'operator', 'raw_text'):
            _text(metadata, key)
        for key in ('min_value', 'max_value'):
            value = metadata.get(key)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError(f'{key}: требуется конечное число или null')
    if not body.strip():
        raise ValueError('Пустой текст')
    locator = f'{relative}:{line}'
    return {'id': f'{relative}#{kind}-{ordinal}', 'corpus': corpus, 'kind': kind,
            'doc_id': metadata['doc_id'], 'clause': metadata['clause'],
            'source_file': relative, 'source_line': line, 'source_sha256': sha,
            'locator': locator, 'metadata': metadata, 'text': body,
            'work_types': work, 'itd_forms': forms,
            'provenance_status': 'unverified', 'notice': NOTICE}


def load_sources(root):
    """Валидировать весь набор до публикации индекса. Ошибка не оставляет полубазу."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f'Папка знаний не найдена: {root}')
    entries, files = [], {}
    for path in sorted(root.rglob('*')):
        if path.suffix.lower() not in ('.md', '.jsonl') or path.name.lower() == 'readme.md':
            continue
        if path.is_symlink() or root not in path.resolve().parents:
            raise ValueError(f'Ссылка за пределы набора не допускается: {path}')
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if len(Path(relative).parts) < 2:
            raise ValueError(f'{relative}: разместите документ в подпапке набора')
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        files[relative] = sha
        try:
            content = raw.decode('utf-8-sig')
            corpus = Path(relative).parts[0]
            if path.suffix.lower() == '.jsonl':
                for line, text in enumerate(content.splitlines(), 1):
                    if not text.strip():
                        continue
                    data = _json(text)
                    if not isinstance(data, dict):
                        raise ValueError(f'Строка {line}: требуется JSON-объект')
                    entries.append(_entry(corpus, relative, sha, line, 'rule', data, data.get('raw_text', ''), line))
            else:
                lines = content.splitlines()
                if not lines or lines[0] != '---':
                    raise ValueError('Markdown должен начинаться с YAML-шапки ---')
                starts = [i for i, value in enumerate(lines) if value == '---']
                # Каждый чанк имеет собственную пару разделителей.
                if len(starts) % 2:
                    raise ValueError('Незакрытая YAML-шапка')
                for ordinal, offset in enumerate(range(0, len(starts), 2), 1):
                    start, end = starts[offset:offset + 2]
                    stop = starts[offset + 2] if offset + 2 < len(starts) else len(lines)
                    metadata = _frontmatter(lines[start + 1:end])
                    entries.append(_entry(corpus, relative, sha, start + 1, 'chunk', metadata,
                                          '\n'.join(lines[end + 1:stop]), ordinal))
        except (ValueError, UnicodeError, TypeError) as error:
            raise ValueError(f'{relative}: {error}') from error
    if not entries:
        raise ValueError('Набор знаний пуст: нужны Markdown с YAML-шапкой или JSONL')
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return entries, {'root': str(root), 'files': files, 'fingerprint': digest, 'format_version': FORMAT_VERSION}


def _summary(entries):
    corpora = {}
    for row in entries:
        item = corpora.setdefault(row['corpus'], {'chunks': 0, 'rules': 0, 'documents': set()})
        item['chunks' if row['kind'] == 'chunk' else 'rules'] += 1
        item['documents'].add(row['doc_id'])
    for item in corpora.values():
        item['documents'] = sorted(item['documents'])
    return corpora


def status(root=None, index=None):
    entries, manifest = load_sources(root or default_root())
    result = {'root': manifest['root'], 'corpora': _summary(entries), 'entries': len(entries),
              'fingerprint': manifest['fingerprint'], 'index_status': 'missing', 'notice': NOTICE}
    if index and Path(index).is_file():
        try:
            with sqlite3.connect(Path(index).resolve().as_uri() + '?mode=ro', uri=True) as conn:
                stored = json.loads(conn.execute('SELECT manifest FROM knowledge_meta').fetchone()[0])
            result['index_status'] = 'ready' if stored == manifest else 'stale'
        except (sqlite3.Error, ValueError, TypeError):
            result['index_status'] = 'invalid'
    result['warnings'] = ['У подготовленных фрагментов не подтверждены оригинал, редакция и применимость.',
                          'Номер строки Markdown/JSONL не является страницей оригинала.',
                          'Некоторые Markdown-фрагменты объединяют несколько пунктов; это видно в clause.']
    return result


def build_index(root, index):
    entries, manifest = load_sources(root)
    index = Path(index).resolve()
    source_root = Path(root).resolve()
    if index == source_root or source_root in index.parents:
        raise ValueError('Индекс должен находиться вне папки исходных знаний')
    index.parent.mkdir(parents=True, exist_ok=True)
    if index.exists():
        try:
            with sqlite3.connect(index.as_uri() + '?mode=ro', uri=True) as existing:
                existing.execute('SELECT manifest FROM knowledge_meta').fetchone()
        except sqlite3.Error as error:
            raise ValueError('Назначение не является индексом знаний; перезапись запрещена') from error
    fd, name = tempfile.mkstemp(prefix='.knowledge-', suffix='.db', dir=index.parent)
    os.close(fd)
    try:
        with sqlite3.connect(name) as conn:
            conn.execute('CREATE TABLE knowledge_meta (manifest TEXT NOT NULL)')
            conn.execute('INSERT INTO knowledge_meta VALUES (?)', (json.dumps(manifest),))
            conn.execute('CREATE TABLE knowledge_entries (id TEXT PRIMARY KEY, corpus TEXT, kind TEXT, doc_id TEXT, clause TEXT, work TEXT, forms TEXT, payload TEXT)')
            conn.execute("CREATE VIRTUAL TABLE knowledge_fts USING fts5(id UNINDEXED, content, tokenize='unicode61')")
            for row in entries:
                conn.execute('INSERT INTO knowledge_entries VALUES (?,?,?,?,?,?,?,?)',
                             (row['id'], row['corpus'], row['kind'], row['doc_id'], row['clause'],
                              '\n'.join(row['work_types']).casefold(), '\n'.join(row['itd_forms']).casefold(),
                              json.dumps(row, ensure_ascii=False)))
                searchable = (json.dumps(row['metadata'], ensure_ascii=False) + '\n' + row['text']).casefold().replace('ё', 'е')
                conn.execute('INSERT INTO knowledge_fts VALUES (?,?)', (row['id'], searchable))
        os.replace(name, index)
    finally:
        Path(name).unlink(missing_ok=True)
    return {'index': str(index), 'entries': len(entries), 'corpora': _summary(entries), 'notice': NOTICE}


def ensure_index(root, index):
    state = status(root, index)
    if state['index_status'] != 'ready':
        build_index(root, index)


def search(root, index, query='', *, corpus=None, kind=None, clause=None, work=None, form=None, limit=10):
    if not 1 <= limit <= 100:
        raise ValueError('limit: допустимо от 1 до 100')
    if len(query) > 500:
        raise ValueError('Запрос длиннее 500 символов')
    if kind not in (None, 'chunk', 'rule'):
        raise ValueError('kind: chunk или rule')
    ensure_index(root, index)
    tokens = re.findall(r'[^\W_]+', query.casefold().replace('ё', 'е'), re.UNICODE)
    if query.strip() and not tokens:
        raise ValueError('Введите слова или номер пункта')
    where, parameters = [], []
    for column, value in (('corpus', corpus), ('kind', kind), ('clause', clause)):
        if value:
            where.append(f'e.{column}=?')
            parameters.append(value)
    for column, value in (('work', work), ('forms', form)):
        if value:
            where.append(f'instr(e.{column},?)>0')
            parameters.append(value.casefold())
    join, order = '', 'e.id'
    if tokens:
        join = ' JOIN knowledge_fts f ON f.id=e.id'
        where.append('knowledge_fts MATCH ?')
        parameters.append(' AND '.join('"' + token + '"*' for token in tokens))
        order = 'bm25(knowledge_fts), e.id'
    sql = 'SELECT e.payload FROM knowledge_entries e' + join
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY ' + order + ' LIMIT ?'
    with sqlite3.connect(Path(index).resolve().as_uri() + '?mode=ro', uri=True) as conn:
        hits = [json.loads(row[0]) for row in conn.execute(sql, (*parameters, limit))]
    for hit in hits:
        hit['excerpt'] = hit['text'][:800]
        del hit['text']
    return {'query': query, 'hits': hits, 'count': len(hits), 'notice': NOTICE}


def show(root, index, entry_id):
    ensure_index(root, index)
    with sqlite3.connect(Path(index).resolve().as_uri() + '?mode=ro', uri=True) as conn:
        row = conn.execute('SELECT payload FROM knowledge_entries WHERE id=?', (entry_id,)).fetchone()
    if row is None:
        raise ValueError('Фрагмент не найден; возьмите id из knowledge-search')
    return json.loads(row[0])


def export_entries(root, output):
    entries, _ = load_sources(root)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + '\n')
    return {'output': str(output.resolve()), 'entries': len(entries)}
