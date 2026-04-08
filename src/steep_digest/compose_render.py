from __future__ import annotations

import html
import re
from typing import Any

from steep_digest.digest_schema import DigestItem, normalize_digest_payload


def _section_title(key: str) -> str:
    return {
        "must_know": "MUST KNOW",
        "interesting": "INTERESTING FOR ME",
        "fluff": "FLUFF",
    }.get(key, key.upper())


def _group(items: list[DigestItem]) -> dict[str, list[DigestItem]]:
    by: dict[str, list[DigestItem]] = {"must_know": [], "interesting": [], "fluff": []}
    for it in items:
        if it.section in by:
            by[it.section].append(it)
    return by


def plain_digest(
    items: list[DigestItem],
    *,
    run_id: str,
    run_date: str,
) -> str:
    lines: list[str] = [
        f"Steep digest — {run_date} ({run_id})",
        "",
    ]
    by = _group(items)
    for key in ("must_know", "interesting", "fluff"):
        sec_items = by[key]
        lines.append(_section_title(key))
        lines.append("")
        if not sec_items:
            lines.append("— (nothing this run)")
            lines.append("")
            continue
        for it in sec_items:
            lines.append(f"• {it.title}")
            lines.append(f"  {it.rationale}")
            for s in it.sources:
                if s.url:
                    lines.append(f"  - {s.label}: {s.url}")
                elif s.gmail_message_id:
                    lines.append(f"  - {s.label} (gmail id: {s.gmail_message_id})")
            lines.append("")
    lines.append("—")
    lines.append("Steep · personal newsletter digest")
    return "\n".join(lines).strip() + "\n"


_LINK_OK = re.compile(r"^https?://[^\s<>]+$")


def telegram_html(
    items: list[DigestItem],
    *,
    run_id: str,
    run_date: str,
) -> str:
    parts: list[str] = [html.escape(f"Steep digest — {run_date} ({run_id})"), ""]
    by = _group(items)
    for key in ("must_know", "interesting", "fluff"):
        sec_items = by[key]
        parts.append(f"<b>{html.escape(_section_title(key))}</b>")
        parts.append("")
        if not sec_items:
            parts.append(html.escape("— (nothing this run)"))
            parts.append("")
            continue
        for it in sec_items:
            parts.append(f"• {html.escape(it.title)}")
            parts.append(html.escape(it.rationale))
            for s in it.sources:
                label = html.escape(s.label)
                if s.url and _LINK_OK.match(s.url):
                    parts.append(f'  - <a href="{html.escape(s.url)}">{label}</a>')
                elif s.gmail_message_id:
                    parts.append(f"  - {label} ({html.escape(s.gmail_message_id)})")
            parts.append("")
    parts.append(html.escape("Steep · personal newsletter digest"))
    return "\n".join(parts).strip()


def email_html(
    items: list[DigestItem],
    *,
    run_id: str,
    run_date: str,
) -> str:
    style = """
body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
       color: #111; background: #fafafa; margin: 0; padding: 24px; }
.card { max-width: 720px; margin: 0 auto; background: #fff; border-radius: 12px;
        padding: 28px 32px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
h1 { font-size: 1.35rem; margin: 0 0 8px; }
.meta { color: #555; font-size: 0.9rem; margin-bottom: 28px; }
h2 { font-size: 1.05rem; margin: 28px 0 12px; padding-bottom: 6px;
     border-bottom: 1px solid #eee; }
ul { margin: 0; padding-left: 1.1rem; }
li { margin: 12px 0; }
.title { font-weight: 600; }
.rationale { color: #444; font-size: 0.92rem; margin: 4px 0 6px; }
.sources { font-size: 0.88rem; color: #555; margin-left: 0; list-style: none; padding: 0; }
.sources li { margin: 2px 0; }
.footer { margin-top: 32px; font-size: 0.82rem; color: #777; }
"""
    chunks: list[str] = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<style>{style}</style></head><body><div class='card'>",
        "<h1>Steep digest</h1>",
        f"<div class='meta'>{html.escape(run_date)} · <code>{html.escape(run_id)}</code></div>",
    ]
    by = _group(items)
    for key in ("must_know", "interesting", "fluff"):
        sec_items = by[key]
        chunks.append(f"<h2>{html.escape(_section_title(key))}</h2>")
        if not sec_items:
            chunks.append("<p>— (nothing this run)</p>")
            continue
        chunks.append("<ul>")
        for it in sec_items:
            chunks.append("<li>")
            chunks.append(f"<div class='title'>{html.escape(it.title)}</div>")
            chunks.append(f"<div class='rationale'>{html.escape(it.rationale)}</div>")
            chunks.append("<ul class='sources'>")
            for s in it.sources:
                if s.url and _LINK_OK.match(s.url):
                    chunks.append(
                        f"<li><a href='{html.escape(s.url)}'>{html.escape(s.label)}</a></li>"
                    )
                elif s.gmail_message_id:
                    chunks.append(
                        f"<li>{html.escape(s.label)} "
                        f"<small>(gmail: {html.escape(s.gmail_message_id)})</small></li>"
                    )
                else:
                    chunks.append(f"<li>{html.escape(s.label)}</li>")
            chunks.append("</ul></li>")
        chunks.append("</ul>")
    chunks.append("<div class='footer'>Steep · personal newsletter digest</div>")
    chunks.append("</div></body></html>")
    return "".join(chunks)


def from_llm_payload(payload: dict[str, Any]) -> list[DigestItem]:
    return normalize_digest_payload(payload)
