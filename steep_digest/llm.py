from __future__ import annotations

import json
from typing import Any

import httpx

from steep_digest.settings import Settings

BUCKET_ALIASES = {
    "need_to_know": "need_to_know",
    "good_to_know": "good_to_know",
    "interesting": "interesting",
    "interesting_for_me": "interesting",
    "fluff": "fluff",
}

JSON_SCHEMA: dict[str, Any] = {
    "name": "newsletter_digest",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "message_id_ref",
                        "bucket",
                        "title",
                        "summary",
                        "primary_url",
                        "sender",
                        "rationale_short",
                    ],
                    "properties": {
                        "message_id_ref": {"type": "string"},
                        "bucket": {
                            "type": "string",
                            "enum": [
                                "need_to_know",
                                "good_to_know",
                                "interesting",
                                "fluff",
                            ],
                        },
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "primary_url": {"type": ["string", "null"]},
                        "sender": {"type": "string"},
                        "rationale_short": {"type": "string"},
                    },
                },
            }
        },
    },
    "strict": True,
}


def classify_newsletters(
    settings: Settings,
    *,
    user_interests_blurb: str,
    messages: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """messages: {id, from, subject, body}"""
    if not messages:
        return []
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required unless using dry-run with no messages")

    system = (
        "You classify and summarize newsletter emails into exactly one bucket per message. "
        "Buckets: need_to_know, good_to_know, interesting, fluff. "
        "need_to_know = time-sensitive, risk, security, money/legal, hard deadlines. "
        "good_to_know = useful context without urgent action. "
        "interesting = matches the user's interests blurb. "
        "fluff = promos, repetitive marketing, low-signal filler. "
        "Return strict JSON matching the schema. "
        "message_id_ref must equal the provided message id for each item. "
        "One output item per input message, same order as input."
    )
    user_payload = {
        "user_interests": user_interests_blurb,
        "messages": messages,
    }
    user = json.dumps(user_payload, ensure_ascii=False)

    url = f"{settings.openai_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.openai_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": JSON_SCHEMA,
        },
    }

    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()

    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    items = parsed.get("items") or []
    out: list[dict[str, Any]] = []
    for it in items:
        b = str(it.get("bucket", "")).lower()
        b = BUCKET_ALIASES.get(b, b)
        it2 = dict(it)
        it2["bucket"] = b
        out.append(it2)
    return out


def fake_classify_for_empty() -> list[dict[str, Any]]:
    return []
