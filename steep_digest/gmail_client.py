from __future__ import annotations

import base64
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_credentials(credentials_path: Path, token_path: Path) -> Credentials:
    creds: Credentials | None = None
    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def list_message_ids(service, q: str, max_results: int = 500) -> list[dict[str, str]]:
    ids: list[dict[str, str]] = []
    page_token: str | None = None
    while True:
        req: dict[str, Any] = {
            "userId": "me",
            "q": q,
            "maxResults": min(100, max_results - len(ids)),
        }
        if page_token:
            req["pageToken"] = page_token
        res = service.users().messages().list(**req).execute()
        for m in res.get("messages", []) or []:
            ids.append({"id": m["id"]})
            if len(ids) >= max_results:
                return ids
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return ids


def get_message_meta(service, msg_id: str) -> tuple[int, list[dict[str, str]]]:
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="metadata", metadataHeaders=["From", "Subject"])
        .execute()
    )
    internal_date = int(msg.get("internalDate", "0"))
    headers = []
    for h in msg.get("payload", {}).get("headers", []) or []:
        if h.get("name") and h.get("value"):
            headers.append({"name": h["name"], "value": h["value"]})
    return internal_date, headers


def get_message_full(service, msg_id: str) -> dict[str, Any]:
    return (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="full")
        .execute()
    )


def _decode_part_body(data_b64: str) -> str:
    raw = base64.urlsafe_b64decode(data_b64 + "===")
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return raw.decode("latin-1", errors="replace")


def extract_body_text(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (text_plain, text_html) best effort."""

    plain: str | None = None
    html: str | None = None

    def walk(part: dict[str, Any]) -> None:
        nonlocal plain, html
        mime = part.get("mimeType", "")
        body = part.get("body") or {}
        data = body.get("data")
        if data and mime == "text/plain" and plain is None:
            plain = _decode_part_body(data)
        elif data and mime == "text/html" and html is None:
            html = _decode_part_body(data)
        for child in part.get("parts") or []:
            walk(child)

    walk(payload)
    return plain, html


def message_to_source(
    msg_full: dict[str, Any],
) -> tuple[str, str, str, str]:
    """msg_id, from_hdr, subject, body_for_llm"""
    msg_id = msg_full["id"]
    internal = msg_full.get("payload") or {}
    headers_list = internal.get("headers") or []
    headers = {h["name"].lower(): h["value"] for h in headers_list if h.get("name")}
    subject = headers.get("subject", "")
    from_hdr = headers.get("from", "")
    plain, html = extract_body_text(internal)
    body = (plain or "").strip()
    if not body and html:
        body = _strip_html_minimal(html)
    snippet = (msg_full.get("snippet") or "").strip()
    if not body:
        body = snippet
    text = f"Subject: {subject}\nFrom: {from_hdr}\n\n{body}"
    return msg_id, from_hdr, subject, text


def _strip_html_minimal(html: str) -> str:
    import re

    s = re.sub(r"(?is)<script.*?>.*?</script>", "", html)
    s = re.sub(r"(?is)<style.*?>.*?</style>", "", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def send_rfc822(
    service,
    *,
    to_addr: str,
    subject: str,
    text_plain: str,
    text_html: str,
) -> None:
    root = MIMEMultipart("alternative")
    root["To"] = to_addr
    root["Subject"] = subject
    root.attach(MIMEText(text_plain, "plain", "utf-8"))
    root.attach(MIMEText(text_html, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(root.as_bytes()).decode("ascii")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
