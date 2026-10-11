"""settingsChanges(): field-level before / after for the audit trail (nested objects by their own fields)."""

from __future__ import annotations

from typing import Any


def _show(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, list):
        return ", ".join(_show_item(v) for v in value)
    return _show_item(value)


def _show_item(value: Any) -> str:
    """String(value) in JavaScript (an array's items are joined the same way; null and undefined are '')."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, dict):
        return "[object Object]"
    if isinstance(value, list):
        return ",".join(_show_item(v) for v in value)
    return str(value)


def settings_changes(before: dict[str, Any] | None, after: dict[str, Any], prefix: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    before = before or {}
    for key, b in after.items():
        a = before.get(key)
        if isinstance(b, dict) and b:
            out += settings_changes(a if isinstance(a, dict) else {}, b, f"{prefix}{key}.")
            continue
        if _show(a) != _show(b):
            out.append({"field": f"{prefix}{key}", "before": _show(a), "after": _show(b)})
    return out
