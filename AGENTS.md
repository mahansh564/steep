# Agent workflow — daily newsletter digest

## Goal

Once per day (UTC, scheduled on Hetzner), produce **one email digest** and the **same content** on **Telegram** (split into multiple messages if needed).

## Pipeline

1. **Load state** — read `STATE_PATH`. If missing, treat cursor as `0` (process all matching mail once; use with care on first run).
2. **Build Gmail query** — OR of `from:` clauses from `ALLOWLIST_PATH` YAML (see `steep_digest/allowlist.py`).
3. **List + fetch** — Gmail API `users.messages.list` with that query; for each candidate, fetch full message if `internalDate > last_internal_date_ms`.
4. **Normalize** — extract best-effort plain text per message for the model (strip tracking noise where obvious; never drop the subject line).
5. **Classify** — call the configured LLM with strict JSON schema: each source message → bucket + title + summary + optional primary URL + rationale.
6. **Render** — HTML + plain text with four anchored sections.
7. **Deliver** — Telegram `sendMessage` first (chunks ≤ 4096 chars); then Gmail `users.messages.send` to `DIGEST_TO_EMAIL`.
8. **Commit state** — only after **both** sends succeed. Set `last_internal_date_ms` to the max `internalDate` among processed messages. If there were zero messages, the runner exits without changing state.

## Failure behavior

- If Gmail list/get, LLM, or render throws: **do not** advance the cursor. Log stderr; optionally notify Telegram with a one-line error if env vars permit.
- If **only** Telegram fails: do **not** advance cursor (user choice: keep email+telegram atomic).
- `--dry-run`: no send; print preview to stdout; do **not** advance cursor.

## OpenClaw alignment

Copy `SOUL.md`, `USER.md`, `AGENTS.md`, `TOOLS.md` into your OpenClaw workspace on the VM if you drive the same policy from an interactive agent; the **scheduled** path is `steep-digest run`.
