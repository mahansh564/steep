from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from steep_digest.allowlist import email_allowed
from steep_digest.extract import body_text_from_message_payload


@dataclass
class IngestedMessage:
    message_id: str
    thread_id: str
    internal_date_ms: int
    subject: str
    from_header: str
    snippet: str
    body_text: str


def _header(headers: list[dict[str, str]], name: str) -> str:
    for h in headers:
        if (h.get("name") or "").lower() == name.lower():
            return h.get("value") or ""
    return ""


def _parse_internal_date(msg: dict[str, Any]) -> int:
    raw = msg.get("internalDate")
    if raw is None:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def list_candidate_message_ids(service, query: str, max_pages: int = 50) -> list[str]:
    ids: list[str] = []
    page_token: str | None = None
    for _ in range(max_pages):
        req: dict[str, Any] = {"userId": "me", "q": query}
        if page_token:
            req["pageToken"] = page_token
        resp = service.users().messages().list(**req).execute()
        for m in resp.get("messages") or []:
            mid = m.get("id")
            if mid:
                ids.append(mid)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def fetch_and_filter_messages(
    service,
    message_ids: list[str],
    allowlist: list[str],
    cursor_ms: int | None,
    *,
    body_max_chars: int = 12000,
) -> list[IngestedMessage]:
    out: list[IngestedMessage] = []
    seen: set[str] = set()
    for mid in message_ids:
        if mid in seen:
            continue
        seen.add(mid)
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=mid, format="full")
            .execute()
        )
        internal = _parse_internal_date(msg)
        if cursor_ms is not None and internal <= cursor_ms:
            continue
        payload = msg.get("payload") or {}
        headers = payload.get("headers") or []
        from_h = _header(headers, "From")
        if not email_allowed(from_h, allowlist):
            continue
        subj = _header(headers, "Subject")
        body = body_text_from_message_payload(payload)
        if len(body) > body_max_chars:
            body = body[:body_max_chars] + "\n\n[truncated]"
        out.append(
            IngestedMessage(
                message_id=mid,
                thread_id=str(msg.get("threadId") or ""),
                internal_date_ms=internal,
                subject=subj,
                from_header=from_h,
                snippet=str(msg.get("snippet") or ""),
                body_text=body,
            )
        )
    out.sort(key=lambda m: m.internal_date_ms)
    return out
