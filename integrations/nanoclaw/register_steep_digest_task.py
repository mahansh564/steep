#!/usr/bin/env python3
"""Insert or replace the Steep digest scheduled task in NanoClaw's SQLite store.

Usage (from steep repo root, after NanoClaw has registered main):
  python3 integrations/nanoclaw/register_steep_digest_task.py \\
    --db nanoclaw/store/messages.db \\
    --cron '0 9 * * *' \\
    --next-run 2026-04-09T09:00:00

Requires: main group row in registered_groups; use TZ in NanoClaw .env for cron alignment.
"""

from __future__ import annotations

import argparse
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--db",
        type=Path,
        default=Path("nanoclaw/store/messages.db"),
        help="Path to NanoClaw messages.db",
    )
    ap.add_argument(
        "--task-id",
        default="steep-digest-daily",
        help="Stable task id (re-running updates the same row)",
    )
    ap.add_argument(
        "--cron",
        default="0 9 * * *",
        help="Cron expression (NanoClaw TIMEZONE / TZ applies)",
    )
    ap.add_argument(
        "--next-run",
        help="ISO8601 next run time (UTC recommended). Default: now + 3 minutes",
    )
    ap.add_argument(
        "--script-file",
        type=Path,
        default=Path("integrations/nanoclaw/steep-digest-task-script.sh"),
        help="Bash script stored in scheduled_tasks.script",
    )
    args = ap.parse_args()

    script = args.script_file.read_text(encoding="utf-8")
    prompt = (
        "Steep digest: the task script runs `steep-digest` and sets wakeAgent=false "
        "so this turn does not invoke Claude."
    )

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT jid, folder FROM registered_groups WHERE is_main = 1 OR folder = 'main' LIMIT 1"
    ).fetchone()
    if not row:
        raise SystemExit(
            "No main group in registered_groups. Complete NanoClaw /setup first."
        )
    jid, folder = row["jid"], row["folder"]

    if args.next_run:
        next_run = args.next_run
    else:
        next_run = (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat()

    created = datetime.now(timezone.utc).isoformat()

    conn.execute("DELETE FROM task_run_logs WHERE task_id = ?", (args.task_id,))
    conn.execute("DELETE FROM scheduled_tasks WHERE id = ?", (args.task_id,))
    conn.execute(
        """
        INSERT INTO scheduled_tasks
        (id, group_folder, chat_jid, prompt, script, schedule_type, schedule_value,
         context_mode, next_run, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            args.task_id,
            folder,
            jid,
            prompt,
            script,
            "cron",
            args.cron,
            "group",
            next_run,
            "active",
            created,
        ),
    )
    conn.commit()
    conn.close()
    print(f"OK — task {args.task_id!r} for group {folder!r} jid {jid!r} next_run={next_run}")


if __name__ == "__main__":
    main()
