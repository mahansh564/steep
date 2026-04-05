from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any

HEADINGS = {
    "need_to_know": "NEED TO KNOW",
    "good_to_know": "GOOD TO KNOW",
    "interesting": "INTERESTING FOR ME",
    "fluff": "FLUFF",
}

ORDER = ["need_to_know", "good_to_know", "interesting", "fluff"]


def render_digest(
    items: list[dict[str, Any]],
    *,
    subject_prefix: str,
    run_at: datetime | None = None,
) -> tuple[str, str, str]:
    """Return (subject, text_plain, text_html)."""
    now = run_at or datetime.now(timezone.utc)
    date_s = now.strftime("%Y-%m-%d")
    subject = f"{subject_prefix} — {date_s}"

    grouped: dict[str, list[dict[str, Any]]] = {k: [] for k in ORDER}
    for it in items:
        b = str(it.get("bucket", "good_to_know")).lower()
        if b not in grouped:
            b = "good_to_know"
        grouped[b].append(it)

    lines_plain: list[str] = [
        f"{subject_prefix} — {date_s} (UTC)",
        "",
    ]
    blocks_html: list[str] = [
        f"<h1>{escape(subject_prefix)} — {escape(date_s)} <span style='color:#666'>(UTC)</span></h1>"
    ]

    for key in ORDER:
        title = HEADINGS[key]
        lines_plain.append(f"=== {title} ===")
        lines_plain.append("")
        anchor = key.replace("_", "-")
        blocks_html.append(f"<h2 id='{anchor}'>{escape(title)}</h2>")
        if not grouped[key]:
            lines_plain.append("(nothing in this section today)")
            lines_plain.append("")
            blocks_html.append("<p><em>Nothing in this section today.</em></p>")
            continue
        ul: list[str] = []
        for it in grouped[key]:
            t = escape(str(it.get("title", "")))
            s = escape(str(it.get("summary", "")))
            sender = escape(str(it.get("sender", "")))
            url = it.get("primary_url")
            lines_plain.append(f"• {it.get('title','')}")
            lines_plain.append(f"  From: {it.get('sender','')}")
            lines_plain.append(f"  {it.get('summary','')}")
            if url:
                lines_plain.append(f"  Link: {url}")
            lines_plain.append("")

            link_html = ""
            if isinstance(url, str) and url.strip():
                safe = escape(url.strip(), quote=True)
                link_html = f"<p><a href='{safe}'>{safe}</a></p>"
            ul.append(
                "<li>"
                f"<strong>{t}</strong> "
                f"<span style='color:#555'>— {sender}</span>"
                f"<p>{s}</p>{link_html}"
                "</li>"
            )
        blocks_html.append("<ul>" + "".join(ul) + "</ul>")

    text_plain = "\n".join(lines_plain).rstrip() + "\n"
    text_html = (
        "<!DOCTYPE html><html><body style='font-family:system-ui,sans-serif;max-width:720px'>"
        + "\n".join(blocks_html)
        + "</body></html>"
    )
    return subject, text_plain, text_html


def digest_plain_for_telegram(subject: str, text_plain: str) -> str:
    return f"{subject}\n\n{text_plain.split('(UTC)', 1)[-1].lstrip() if '(UTC)' in text_plain else text_plain}"
