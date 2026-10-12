"""Content-Disposition for downloads (B17 review L12)."""

from __future__ import annotations

from urllib.parse import quote


def disposition(name: str, kind: str = "attachment") -> str:
    """A header any file name fits in: an ASCII-safe filename=, and filename*= with the real name (RFC 6266)."""
    plain = "".join(c if 32 <= ord(c) < 127 and c not in '"\\;' else "_" for c in name) or "export"
    return f"{kind}; filename=\"{plain}\"; filename*=UTF-8''{quote(name, safe='')}"
