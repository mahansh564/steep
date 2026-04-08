from __future__ import annotations

import base64
import re
from typing import Any

import html2text

_h2t = html2text.HTML2Text()
_h2t.ignore_links = False
_h2t.ignore_images = True
_h2t.body_width = 0


def html_to_text(html: str) -> str:
    if not html:
        return ""
    text = _h2t.handle(html)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _decode_part(data: str | None) -> str:
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    except Exception:
        return ""


def body_text_from_message_payload(payload: dict[str, Any]) -> str:
    """Best-effort plain text from Gmail API message payload."""
    body = payload.get("body") or {}
    data = body.get("data")
    mime = (payload.get("mimeType") or "").lower()

    parts = payload.get("parts")
    if parts:
        plain_chunks: list[str] = []
        html_chunks: list[str] = []
        for p in parts:
            pm = (p.get("mimeType") or "").lower()
            if pm.startswith("multipart/"):
                nested = body_text_from_message_payload(p)
                if nested:
                    plain_chunks.append(nested)
                continue
            b = p.get("body") or {}
            d = b.get("data")
            if pm == "text/plain" and d:
                plain_chunks.append(_decode_part(d))
            elif pm == "text/html" and d:
                html_chunks.append(_decode_part(d))
        if plain_chunks:
            return "\n\n".join(c.strip() for c in plain_chunks if c.strip()).strip()
        if html_chunks:
            return html_to_text("\n".join(html_chunks))

    if mime == "text/plain" and data:
        return _decode_part(data).strip()
    if mime == "text/html" and data:
        return html_to_text(_decode_part(data))
    if data:
        return html_to_text(_decode_part(data))
    return ""
