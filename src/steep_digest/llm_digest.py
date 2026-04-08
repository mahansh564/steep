from __future__ import annotations

import json
import os
import re
from typing import Any

from anthropic import Anthropic

from steep_digest.compose_render import from_llm_payload
from steep_digest.digest_schema import DigestItem
from steep_digest.gmail_ingest import IngestedMessage

DEFAULT_MODEL = "claude-sonnet-4-20250514"

SYSTEM = """You are an editorial assistant producing ONE digest for a single reader.
The reader's priorities and taste are defined in READER_CONTEXT (their CLAUDE.md).
You MUST classify every distinct story or item into exactly one section:
- must_know: time-sensitive, decision-relevant, or safety/security relevant for this reader
- interesting: worth reading but not urgent
- fluff: low signal for this reader (still summarize briefly if it appeared in input)

Output ONLY valid JSON matching this shape (no markdown fences):
{
  "items": [
    {
      "section": "must_know" | "interesting" | "fluff",
      "title": "short headline",
      "rationale": "one line tied to READER_CONTEXT",
      "sources": [
        { "label": "string", "gmail_message_id": "optional", "url": "optional https" }
      ]
    }
  ]
}

Rules:
- Every item MUST cite at least one gmail_message_id from the provided messages when applicable.
- Prefer accurate titles; do not invent facts for must_know.
- If input has no substantive items, return {"items": []}.
"""


def _pack_messages_for_prompt(messages: list[IngestedMessage]) -> str:
    blocks: list[str] = []
    for m in messages:
        blocks.append(
            "\n".join(
                [
                    f"MESSAGE_ID: {m.message_id}",
                    f"Subject: {m.subject}",
                    f"From: {m.from_header}",
                    f"Snippet: {m.snippet}",
                    "Body:",
                    m.body_text,
                    "----",
                ]
            )
        )
    return "\n".join(blocks)


_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def _parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    text = _JSON_FENCE.sub("", text).strip()
    return json.loads(text)


def build_digest_items(reader_md: str, messages: list[IngestedMessage]) -> list[DigestItem]:
    if not messages:
        return []
    client = Anthropic()
    model = os.environ.get("STEEP_ANTHROPIC_MODEL", DEFAULT_MODEL)
    user_content = (
        "READER_CONTEXT:\n"
        f"{reader_md.strip()}\n\n"
        "RAW_NEWSLETTERS:\n"
        f"{_pack_messages_for_prompt(messages)}\n"
    )
    msg = client.messages.create(
        model=model,
        max_tokens=8192,
        temperature=0.2,
        system=SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )
    text = ""
    for block in msg.content:
        if block.type == "text":
            text += block.text
    payload = _parse_json_object(text)
    return from_llm_payload(payload)
