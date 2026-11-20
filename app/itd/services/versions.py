"""Content identity shared by CLI, web, MCP and future assistants."""
import hashlib

from ..paths import ROOT


def skills_version():
    digest = hashlib.sha256()
    for path in sorted((ROOT / 'ai/skills').rglob('*')):
        if path.is_file() and path.suffix in ('.md', '.yaml', '.yml'):
            digest.update(str(path.relative_to(ROOT)).encode() + b'\0')
            digest.update(path.read_bytes() + b'\0')
    return digest.hexdigest()
