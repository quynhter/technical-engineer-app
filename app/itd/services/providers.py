"""Administrator-managed server credentials; secrets never leave this service."""
import json
import os
from pathlib import Path
import re
import tempfile
from threading import RLock
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from .. import llm
from .permissions import require

_LOCK = RLock()


class ProviderInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(min_length=1, max_length=100)
    protocol: str
    base_url: str = Field(min_length=1, max_length=2000)
    api_key: str = Field(default='', max_length=8192)
    allow_anonymous: bool = False


def config_path(accounts):
    return accounts.path.with_name(accounts.path.name + '.llm-providers.json')


def settings(actor, path):
    require(actor, 'admin')
    configured = llm.profiles(path)
    return [dict(name=name, protocol=p['protocol'], base_url=p['base_url'],
                 key_configured=bool(p.get('api_key')), allow_anonymous=p.get('allow_anonymous', False))
            for name, p in configured.items()]


def save(actor, path, data):
    require(actor, 'admin')
    value = ProviderInput.model_validate(data)
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', value.name) or value.protocol not in ('chat', 'anthropic', 'gemini'):
        raise ValueError('Проверьте название и протокол подключения')
    url = urlsplit(value.base_url)
    if (url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password
            or url.query or url.fragment or any(c.isspace() for c in value.base_url)
            or any(ord(c) < 32 or ord(c) == 127 for c in value.api_key)):
        raise ValueError('Проверьте адрес и ключ подключения')
    path = Path(path)
    with _LOCK:
        stored = json.loads(path.read_text()) if path.exists() else {}
        previous = stored.get(value.name) or llm.profiles(path).get(value.name, {})
        preset = llm.PRESETS.get(value.name)
        env = previous.get('api_key_env', preset[2] if preset else '')
        key = value.api_key or previous.get('api_key', '')
        if not key and not os.environ.get(env, '') and not value.allow_anonymous:
            raise ValueError('Введите ключ API или разрешите подключение без ключа')
        stored[value.name] = dict(protocol=value.protocol, base_url=value.base_url.rstrip('/'),
                                  api_key=key, api_key_env=env, allow_anonymous=value.allow_anonymous)
        # Same-directory atomic replace preserves the old working configuration on failure.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.llm-', delete=False) as handle:
                temporary = Path(handle.name)
                os.chmod(temporary, 0o600)
                json.dump(stored, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return {'name': value.name, 'saved': True}
