from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from steep_digest.allowlist import gmail_from_query_fragment, load_allowlist
from steep_digest.compose_render import email_html, plain_digest, telegram_html
from steep_digest.config_load import (
    bootstrap_days,
    load_digest_config,
    resolve_cursor_path,
    resolve_digest_to_email,
    resolve_reader_path,
    subject_template,
)
from steep_digest.cursor import load_cursor, save_cursor
from steep_digest.deliver import send_gmail_email, send_telegram_html
from steep_digest.gmail_ingest import fetch_and_filter_messages, list_candidate_message_ids
from steep_digest.gmail_service import get_credentials, gmail_service
from steep_digest.llm_digest import build_digest_items
from steep_digest.paths import config_dir, repo_root


def _run_id() -> str:
    return uuid.uuid4().hex[:8]


def _after_date_for_query(cursor_ms: int | None, bootstrap_d: int) -> str:
    if cursor_ms is None:
        start = datetime.now(timezone.utc) - timedelta(days=bootstrap_d)
    else:
        start = datetime.fromtimestamp(max(0, cursor_ms - 86_400_000) / 1000.0, tz=timezone.utc)
    return start.strftime("%Y/%m/%d")


def cmd_gmail_auth(root: Path) -> int:
    """Refresh or create token.json using credentials.json."""
    get_credentials(root)
    print(f"OK — token stored at {root / 'token.json'}")
    return 0


def cmd_run(root: Path) -> int:
    load_dotenv(root / ".env")
    root = root.resolve()
    allow_path = config_dir(root) / "newsletter-allowlist.yaml"
    allow = load_allowlist(allow_path)
    dcfg = load_digest_config(root)
    cursor_path = resolve_cursor_path(root, dcfg)
    reader_path = resolve_reader_path(root, dcfg)
    to_email = resolve_digest_to_email(dcfg)
    subj_tpl = subject_template(dcfg)
    bootstrap_d = bootstrap_days(dcfg)

    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not tok or not chat:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID", file=sys.stderr)
        return 2

    state = load_cursor(cursor_path)
    cursor_raw = state.get("last_successful_internal_ms")
    cursor_ms: int | None = int(cursor_raw) if cursor_raw is not None else None

    reader_md = reader_path.read_text(encoding="utf-8")

    service = gmail_service(root)
    from_q = gmail_from_query_fragment(allow)
    after = _after_date_for_query(cursor_ms, bootstrap_d)
    q = f"{from_q} after:{after}"

    ids = list_candidate_message_ids(service, q)
    messages = fetch_and_filter_messages(service, ids, allow, cursor_ms)

    rid = _run_id()
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")
    subject = subj_tpl.format(date=run_date, run_id=rid)

    items = build_digest_items(reader_md, messages)

    text_body = plain_digest(items, run_id=rid, run_date=run_date)
    html_body = email_html(items, run_id=rid, run_date=run_date)
    tg_body = telegram_html(items, run_id=rid, run_date=run_date)

    send_gmail_email(service, to_addr=to_email, subject=subject, text_body=text_body, html_body=html_body)
    send_telegram_html(token=tok, chat_id=chat, html=tg_body)

    if messages:
        new_cursor = max(m.internal_date_ms for m in messages)
    else:
        new_cursor = max(cursor_ms or 0, int(datetime.now(timezone.utc).timestamp() * 1000))

    save_cursor(
        cursor_path,
        {
            "last_successful_internal_ms": new_cursor,
            "last_run_id": rid,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    print(f"OK — digest sent to {to_email} and Telegram; cursor -> {new_cursor}")
    return 0


def main() -> None:
    root = repo_root()
    p = argparse.ArgumentParser(prog="steep-digest")
    sub = p.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Build digest from Gmail and deliver")
    run_p.set_defaults(fn=lambda: cmd_run(root))

    auth_p = sub.add_parser("gmail-auth", help="OAuth browser flow; writes token.json")
    auth_p.set_defaults(fn=lambda: cmd_gmail_auth(root))

    args = p.parse_args()
    fn = getattr(args, "fn", None)
    if fn is None:
        p.print_help()
        raise SystemExit(2)
    raise SystemExit(fn())


if __name__ == "__main__":
    main()
