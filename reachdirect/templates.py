"""Message personalisation: ``{{first_name}}`` placeholders with optional fallbacks ``{{first_name|there}}``."""

from __future__ import annotations

import re

_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\|\s*([^}]*?)\s*)?\}\}")


def placeholders(template: str) -> list[str]:
    return list(dict.fromkeys(m.group(1) for m in _PLACEHOLDER.finditer(template)))


def render(template: str, values: dict[str, str]) -> tuple[str, list[str]]:
    """Fills placeholders. Returns (text, missing) where missing lists placeholders with no value and no fallback."""
    missing: list[str] = []

    def sub(m: re.Match) -> str:
        key, fallback = m.group(1), m.group(2)
        value = values.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
        if fallback is not None:
            return fallback
        missing.append(key)
        return m.group(0)

    return _PLACEHOLDER.sub(sub, template), list(dict.fromkeys(missing))


def first_name(full_name: str) -> str:
    parts = full_name.strip().split()
    return parts[0] if parts else ""
