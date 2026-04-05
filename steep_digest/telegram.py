from __future__ import annotations

import httpx

TG_MAX = 4096
# Leave room for "(part xx/yy)\n\n" when splitting into multiple messages
_PACK_TARGET = 3900


def split_message(text: str, limit: int = TG_MAX) -> list[str]:
    """Split on paragraph boundaries, then hard-split; never exceed `limit`."""
    text = text.rstrip()
    if len(text) <= limit:
        return [text]

    blocks = text.split("\n\n")
    packed: list[str] = []
    buf: list[str] = []
    cur = 0
    target = min(_PACK_TARGET, limit)

    def flush() -> None:
        nonlocal buf, cur
        if buf:
            packed.append("\n\n".join(buf))
            buf = []
            cur = 0

    for block in blocks:
        if len(block) > target:
            flush()
            packed.extend(_hard_split(block, target))
            continue
        extra = len(block) + (2 if buf else 0)
        if cur + extra > target:
            flush()
        buf.append(block)
        cur += extra

    flush()

    trimmed: list[str] = []
    for p in packed:
        if len(p) <= limit:
            trimmed.append(p)
        else:
            trimmed.extend(_hard_split(p, target))

    if len(trimmed) <= 1:
        return trimmed

    n = len(trimmed)
    out: list[str] = []
    for i, chunk in enumerate(trimmed):
        hdr = f"(part {i + 1}/{n})\n\n"
        body = chunk
        if len(hdr) + len(body) > limit:
            body_parts = _hard_split(body, limit - len(hdr))
            for j, bp in enumerate(body_parts):
                sub = f"(part {i + 1}/{n})" + (f" §{j + 1}" if len(body_parts) > 1 else "")
                out.append(sub + "\n\n" + bp)
        else:
            out.append(hdr + body)
    return out


def _hard_split(s: str, limit: int) -> list[str]:
    if len(s) <= limit:
        return [s]
    chunks: list[str] = []
    start = 0
    while start < len(s):
        end = min(start + limit, len(s))
        chunks.append(s[start:end])
        start = end
    return chunks


def send_telegram_chunks(
    bot_token: str,
    chat_id: str,
    chunks: list[str],
    *,
    disable_web_page_preview: bool = True,
) -> None:
    base = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    with httpx.Client(timeout=60.0) as client:
        for text in chunks:
            if len(text) > TG_MAX:
                raise ValueError(f"Telegram chunk length {len(text)} > {TG_MAX}")
            r = client.post(
                base,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "disable_web_page_preview": disable_web_page_preview,
                },
            )
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(f"Telegram API error: {data}")
