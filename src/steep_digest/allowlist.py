from __future__ import annotations

from email.utils import parseaddr
from pathlib import Path

import yaml


def load_allowlist(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = data.get("allowlist")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("newsletter-allowlist.yaml: allowlist must be a list")
    out: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        else:
            raise ValueError("newsletter-allowlist.yaml: each allowlist entry must be a string")
    return out


def gmail_from_query_fragment(entries: list[str]) -> str:
    """Build parenthesized `(from:x OR from:y)` fragment for Gmail `q` parameter."""
    if not entries:
        raise ValueError("allowlist is empty; add senders to config/newsletter-allowlist.yaml")
    parts: list[str] = []
    for e in entries:
        if e.startswith("@"):
            dom = e[1:].strip().lstrip("@")
            if not dom:
                continue
            parts.append(f"from:{dom}")
        elif "@" in e:
            parts.append(f"from:{e.strip()}")
        else:
            parts.append(f"from:{e.strip()}")
    inner = " OR ".join(parts)
    return f"({inner})"


def sender_email_from_header(from_header: str) -> str:
    _, addr = parseaddr(from_header)
    return (addr or "").strip().lower()


def email_allowed(sender: str, entries: list[str]) -> bool:
    """True if `sender` (raw From header or email) matches allowlist rules."""
    email = sender if "@" in sender and "<" not in sender else sender_email_from_header(sender)
    email = email.lower()
    if not email or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[-1].lower()
    for rule in entries:
        r = rule.strip()
        if not r:
            continue
        if r.startswith("@"):
            dom = r[1:].strip().lstrip("@").lower()
            if domain == dom or email.endswith(f"@{dom}"):
                return True
        elif "@" in r:
            if email == r.strip().lower():
                return True
        else:
            dom = r.strip().lower()
            if domain == dom or email.endswith(f"@{dom}"):
                return True
    return False
