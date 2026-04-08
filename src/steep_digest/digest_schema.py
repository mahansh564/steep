from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceRef:
    label: str
    gmail_message_id: str | None = None
    url: str | None = None


@dataclass
class DigestItem:
    section: str  # must_know | interesting | fluff
    title: str
    rationale: str
    sources: list[SourceRef] = field(default_factory=list)


def normalize_digest_payload(data: dict[str, Any]) -> list[DigestItem]:
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("LLM output must contain 'items' array")
    out: list[DigestItem] = []
    for i, row in enumerate(raw_items):
        if not isinstance(row, dict):
            continue
        sec = str(row.get("section") or "").strip().lower().replace(" ", "_")
        if sec in ("must know", "must-know"):
            sec = "must_know"
        elif sec in ("interesting_for_me", "interesting-for-me", "interestingforme"):
            sec = "interesting"
        elif sec.startswith("interesting") and sec != "interesting":
            sec = "interesting"
        if sec not in ("must_know", "interesting", "fluff"):
            raise ValueError(f"items[{i}].section must be must_know|interesting|fluff, got {sec!r}")
        title = str(row.get("title") or "").strip()
        rationale = str(row.get("rationale") or "").strip()
        if not title:
            continue
        sources: list[SourceRef] = []
        for s in row.get("sources") or []:
            if not isinstance(s, dict):
                continue
            sources.append(
                SourceRef(
                    label=str(s.get("label") or "source"),
                    gmail_message_id=(
                        str(s["gmail_message_id"]).strip() if s.get("gmail_message_id") else None
                    ),
                    url=str(s["url"]).strip() if s.get("url") else None,
                )
            )
        out.append(DigestItem(section=sec, title=title, rationale=rationale, sources=sources))
    return out
