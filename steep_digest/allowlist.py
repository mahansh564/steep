from __future__ import annotations

from pathlib import Path

import yaml


def _from_clause(entry: str) -> str:
    s = entry.strip()
    if not s:
        return ""
    if s.startswith("@"):
        domain = s[1:]
        return f"from:*@{domain}"
    if "@" in s:
        return f"from:{s}"
    return f"from:*@{s}"


def load_senders(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = data.get("senders") or []
    if not isinstance(raw, list):
        raise ValueError("allowlist YAML must contain a list 'senders'")
    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            out.append(item)
        else:
            raise ValueError("each senders entry must be a string")
    return out


def gmail_query_or_clause(senders: list[str]) -> str:
    parts = []
    for e in senders:
        c = _from_clause(e)
        if c:
            parts.append(f"({c})")
    if not parts:
        raise ValueError("allowlist is empty")
    return "(" + " OR ".join(parts) + ")"
