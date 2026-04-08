# NanoClaw runbook — Steep digest

> **Monorepo:** NanoClaw lives in `nanoclaw/` (submodule). Full wiring: **[integrations/nanoclaw/README.md](../integrations/nanoclaw/README.md)**.

## What runs where

- **NanoClaw** triggers a **scheduled task** (recommended: daily **09:00** — set NanoClaw **`TZ`**).
- The task **`script`** runs **`steep-digest`** in the container and ends with **`{"wakeAgent": false}`** so no extra Claude turn runs for that tick.

## Prerequisites on the host

1. **steep** checkout available at a stable path (bind mount, sync, or clone).
2. **Python 3.11+** venv with `pip install -e ".[dev]"` (or production install without dev extras).
3. **Files in repo root (gitignored):** `credentials.json`, `token.json`
4. **Environment variables** (shell, NanoClaw secret store, or `.env` next to `steep-digest`):
   - `ANTHROPIC_API_KEY`
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - Optional: `STEEP_ANTHROPIC_MODEL`, `STEEP_REPO_ROOT`, `STEEP_READER_CLAUDE_MD`, `STEEP_DIGEST_TO_EMAIL`

## Scheduled task command

Use the **group** that already has your reader **`CLAUDE.md`**. Point `config/digest.yaml` → `reader_claude_md` at that file, or set `STEEP_READER_CLAUDE_MD`.

Example:

```bash
cd /path/to/steep && /path/to/steep/.venv/bin/steep-digest run
```

## Cursor and idempotency

- **Cursor** advances **only after** both **Gmail send** and **Telegram** succeed.
- State file path: `config/digest.yaml` → `cursor_path` (default `state/digest-cursor.json`).
- First sync uses **`bootstrap_days`** to cap history.

## Operational checks

- **`steep-digest gmail-auth`**: (re)establish OAuth token.
- Dry observation: temporarily inspect Gmail `q` by adding logging in a dev branch (not required for normal use).

## Failure modes

| Symptom | Check |
|--------|--------|
| No mail ingested | Allowlist entries, `after:` window, cursor file |
| Auth errors | `token.json` refresh; `credentials.json` client type |
| Telegram 400 | HTML parse errors; message length (auto-chunk should help) |
| Wrong buckets | Edit group **`CLAUDE.md`**; keep it explicit about priorities |
