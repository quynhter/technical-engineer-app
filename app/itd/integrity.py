"""Fail closed when a protected source is absent, replaced or corrupted."""
import hashlib
from pathlib import Path


def verify_files(root, entries):
    root = Path(root).resolve()
    for name, expected in entries.items():
        path = root / name
        if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file():
            raise ValueError(f'Отсутствует или недопустим файл знаний: {name}')
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            header = handle.read(128)
            if header.startswith(b'version https://git-lfs.github.com/spec/v1'):
                raise ValueError(f'Не загружен объект LFS: {name}')
            digest.update(header)
            for block in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError(f'Нарушена целостность файла знаний: {name}')


def manifest_entries(path):
    return {line[66:]: line[:64] for line in Path(path).read_text(encoding='utf-8').splitlines()}
