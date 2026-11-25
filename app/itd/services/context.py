"""Explicit workspace and authenticated principal, never taken from tool payloads."""
from contextlib import contextmanager
from contextvars import ContextVar
import os
import getpass
import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..paths import default_templates, itd_root, previous_itd_roots
from .permissions import WORKSPACE_ACTIONS


class Actor(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    user_id: int | str
    role: Literal['viewer', 'editor', 'admin']
    source: Literal['web', 'cli', 'cli-agent', 'mcp', 'assistant', 'background']
    on_behalf_of: int | str | None = None

    @model_validator(mode='after')
    def delegation(self):
        if self.source in ('cli-agent', 'mcp', 'assistant') and self.on_behalf_of is None:
            raise ValueError('Для агента требуется пользователь-поручитель')
        return self


class ServiceContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    database: Path
    root: Path | None = None
    templates: Path = Field(default_factory=default_templates)
    accounts_namespace: str = ''
    previous_roots: tuple[Path, ...] = ()
    settings: dict[str, Any] = Field(default_factory=dict)


def accounts_namespace(path):
    path = Path(path).resolve()
    stat = path.stat()
    return hashlib.sha256(os.fsencode(path) + f'\n{stat.st_dev}:{stat.st_ino}'.encode()).hexdigest()


class OperationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    operation: str
    data: dict[str, Any] = Field(default_factory=dict)


class WorkspaceActionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    project_id: int
    action: str = Field(json_schema_extra={'enum': WORKSPACE_ACTIONS})
    data: dict[str, Any] = Field(default_factory=dict)


current_actor = ContextVar('service_actor', default=None)


def local_actor(agent=False):
    # Existing CLI authority is the OS account with direct access to the DB files.
    local_id = str(os.getuid()) if hasattr(os, 'getuid') else hashlib.sha256(getpass.getuser().encode()).hexdigest()[:16]
    principal = 'os:' + local_id
    return Actor(user_id=principal, role='admin', source='cli-agent' if agent else 'cli',
                 on_behalf_of=principal if agent else None)


@contextmanager
def scope(ctx, actor):
    token = current_actor.set(actor)
    root_token = itd_root.set(ctx.root)
    roots_token = previous_itd_roots.set(ctx.previous_roots)
    try:
        yield
    finally:
        previous_itd_roots.reset(roots_token)
        itd_root.reset(root_token)
        current_actor.reset(token)
