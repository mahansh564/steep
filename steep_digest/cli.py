from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from steep_digest.allowlist import gmail_query_or_clause, load_senders
from steep_digest.gmail_client import (
    build_service,
    get_credentials,
    get_message_full,
    get_message_meta,
    list_message_ids,
    message_to_source,
    send_rfc822,
)
from steep_digest.llm import classify_newsletters
from steep_digest.render import digest_plain_for_telegram, render_digest
from steep_digest.settings import Settings
from steep_digest.state import DigestState
from steep_digest.telegram import send_telegram_chunks, split_message

log = logging.getLogger("steep_digest")

DEFAULT_USER_BLURB = (
    "No USER.md / STEEP_USER_MD_PATH configured. "
    "Treat interesting_for_me as broadly professional or technical curiosity."
)


def _load_user_blurb(settings: Settings) -> str:
    if settings.user_md_path:
        p = Path(settings.user_md_path)
        if p.is_file():
            return p.read_text(encoding="utf-8").strip()
    cwd_user = Path.cwd() / "USER.md"
    if cwd_user.is_file():
        return cwd_user.read_text(encoding="utf-8").strip()
    repo_user = Path(__file__).resolve().parent.parent / "USER.md"
    if repo_user.is_file():
        return repo_user.read_text(encoding="utf-8").strip()
    return DEFAULT_USER_BLURB


def _max_process() -> int:
    return max(1, int(os.environ.get("STEEP_MAX_MESSAGES", "50")))


def _list_cap() -> int:
    return max(_max_process(), int(os.environ.get("STEEP_LIST_CAP", "500")))


def run_digest(settings: Settings) -> int:
    try:
        return _run_digest_impl(settings)
    except FileNotFoundError as e:
        log.error("Missing path or credentials: %s", e)
        return 2
    except Exception as e:
        log.exception("Digest failed: %s", e)
        return 1


def _run_digest_impl(settings: Settings) -> int:
    allow_path = Path(settings.allowlist_path)
    senders = load_senders(allow_path)
    q = gmail_query_or_clause(senders)
    state_path = Path(settings.state_path)
    state = DigestState.load(state_path)

    creds = get_credentials(
        Path(settings.gmail_credentials_path),
        Path(settings.gmail_token_path),
    )
    service = build_service(creds)

    list_cap = _list_cap()
    ids = list_message_ids(service, q, max_results=list_cap)
    candidates: list[tuple[int, str]] = []
    for mid in ids:
        msg_id = mid["id"]
        internal, _ = get_message_meta(service, msg_id)
        if internal > state.last_internal_date_ms:
            candidates.append((internal, msg_id))

    candidates.sort(key=lambda t: t[0], reverse=True)
    max_proc = _max_process()
    candidates = candidates[:max_proc]
    max_internal = state.last_internal_date_ms

    messages_for_llm: list[dict[str, str]] = []
    ordered_ids: list[str] = []

    for internal, msg_id in sorted(candidates, key=lambda t: t[0]):
        full = get_message_full(service, msg_id)
        m_id, from_hdr, subject, body = message_to_source(full)
        ordered_ids.append(m_id)
        messages_for_llm.append(
            {
                "id": m_id,
                "from": from_hdr,
                "subject": subject,
                "body": body[:120_000],
            }
        )
        max_internal = max(max_internal, internal)

    user_blurb = _load_user_blurb(settings)

    if not messages_for_llm:
        log.info("No new allowlisted messages after cursor %s", state.last_internal_date_ms)
        return 0

    if not settings.openai_api_key:
        log.error("OPENAI_API_KEY is required when there are messages to classify.")
        return 2

    items = classify_newsletters(
        settings,
        user_interests_blurb=user_blurb,
        messages=messages_for_llm,
    )
    items = _reorder_items(items, ordered_ids)

    subject, text_plain, text_html = render_digest(
        items,
        subject_prefix=settings.subject_prefix,
        run_at=datetime.now(timezone.utc),
    )

    if settings.dry_run:
        print(subject)
        print("-" * 60)
        print(text_plain)
        log.info("Dry run: skipping Gmail send, Telegram, and state update.")
        return 0

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        log.error("Telegram credentials missing for non-dry-run.")
        return 2

    tg_body = digest_plain_for_telegram(subject, text_plain)
    chunks = split_message(tg_body)
    try:
        send_telegram_chunks(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            chunks,
        )
    except Exception as e:
        log.exception("Telegram send failed: %s", e)
        return 3

    try:
        send_rfc822(
            service,
            to_addr=settings.digest_to_email,
            subject=subject,
            text_plain=text_plain,
            text_html=text_html,
        )
    except Exception as e:
        log.exception("Gmail send failed: %s", e)
        return 4

    new_state = DigestState(
        version=state.version,
        last_internal_date_ms=max_internal,
    )
    new_state.save(state_path)
    log.info(
        "Digest sent for %d messages; cursor -> %s",
        len(ordered_ids),
        max_internal,
    )
    return 0


def _reorder_items(
    items: list[dict],
    ordered_ids: list[str],
) -> list[dict]:
    by_ref = {str(i.get("message_id_ref", "")): i for i in items}
    out: list[dict] = []
    for mid in ordered_ids:
        if mid in by_ref:
            out.append(by_ref[mid])
    for k, v in by_ref.items():
        if k not in ordered_ids:
            out.append(v)
    return out


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Steep newsletter digest runner")
    p.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run"],
        help="run (default): fetch, classify, deliver",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify and print digest; no send; no state update",
    )
    p.add_argument("--verbose", action="store_true", help="Debug logging")
    args = p.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # `python -m steep_digest` with no explicit env: friendly error for required vars
    required = [
        "GMAIL_CREDENTIALS_PATH",
        "GMAIL_TOKEN_PATH",
        "ALLOWLIST_PATH",
        "STATE_PATH",
        "DIGEST_TO_EMAIL",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        log.error("Missing required environment variables: %s", ", ".join(missing))
        sys.exit(2)

    base = Settings.from_environ()
    settings = replace(base, dry_run=base.dry_run or args.dry_run, verbose=base.verbose or args.verbose)

    if args.command == "run":
        rc = run_digest(settings)
        sys.exit(rc)


if __name__ == "__main__":
    main()
