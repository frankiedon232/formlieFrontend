"""Stored files, always under a workspace path (CLAUDE.md rule 13): tenants/{tenant_id}/orgs/{organisation_id}/{module}/{uuid}.

Development keeps them in a folder (STORAGE_DIR, git-ignored). Object storage replaces this before going live,
behind the same three calls, so callers only ever handle keys, never paths.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import get_settings


def key_for(tenant_id: uuid.UUID, organisation_id: uuid.UUID, module: str, file_id: uuid.UUID) -> str:
    return f"tenants/{tenant_id}/orgs/{organisation_id}/{module}/{file_id}"


def _path(key: str) -> Path:
    root = Path(get_settings().storage_dir).resolve()
    path = (root / key).resolve()
    if root not in path.parents:  # a key can never point outside the store
        raise ValueError("storage key outside the store")
    return path


def put(key: str, content: bytes) -> int:
    path = _path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_bytes(content)
    tmp.replace(path)  # readers never see half a file
    return len(content)


def get(key: str) -> bytes | None:
    path = _path(key)
    return path.read_bytes() if path.is_file() else None
