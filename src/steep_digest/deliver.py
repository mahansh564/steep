from __future__ import annotations

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx


def send_gmail_email(
    service,
    *,
    to_addr: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    msg = MIMEMultipart("alternative")
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def send_telegram_html(
    *,
    token: str,
    chat_id: str,
    html: str,
    max_len: int = 3900,
) -> None:
    """Send possibly long HTML as one or more Telegram messages."""
    chunks = _chunk_telegram(html, max_len=max_len)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    with httpx.Client(timeout=60) as client:
        for c in chunks:
            r = client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": c,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(f"Telegram error: {data}")


def _chunk_telegram(text: str, *, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts: list[str] = []
    rest = text
    while rest:
        if len(rest) <= max_len:
            parts.append(rest)
            break
        cut = rest.rfind("\n\n", 0, max_len)
        if cut < max_len // 2:
            cut = rest.rfind(" ", 0, max_len)
        if cut < max_len // 2:
            cut = max_len
        parts.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    return [p for p in parts if p]
