# Steep

Personal newsletter digest: pull allowlisted mail from **Gmail**, classify into **MUST KNOW / INTERESTING FOR ME / FLUFF** with **Claude** using your **CLAUDE.md** as the reader profile, then **send** the combined digest via **Gmail** and **Telegram**.

**NanoClaw** is included as a **git submodule** at [`nanoclaw/`](nanoclaw/). Monorepo wiring (mount allowlist, Docker layer with Python, scheduled task registration) lives in [`integrations/nanoclaw/README.md`](integrations/nanoclaw/README.md).

Designed to run on a **NanoClaw** scheduled task (recommended) or standalone / cron.

## Clone (with NanoClaw submodule)

```bash
git clone --recurse-submodules https://github.com/YOU/steep.git
# or after a normal clone:
git submodule update --init
```

## Quick start

1. **Python 3.11+**

   ```bash
   cd /path/to/steep
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

2. **Google Cloud / Gmail API**
   - Create an OAuth **Desktop app** client; download JSON as **`credentials.json`** in the repo root (see `.gitignore`; never commit).
   - First auth:

     ```bash
     steep-digest gmail-auth
     ```

   This writes **`token.json`** (gitignored).

3. **Anthropic**
   - Export `ANTHROPIC_API_KEY` (or put it in `.env`).

4. **Telegram**
   - Create a bot with [@BotFather](https://t.me/BotFather), set `TELEGRAM_BOT_TOKEN`.
   - Your user chat id → `TELEGRAM_CHAT_ID` (e.g. message [@userinfobot](https://t.me/userinfobot)).

5. **Config**
   - Edit **`config/newsletter-allowlist.yaml`** with senders/domains.
   - Edit **`config/digest.yaml`**:
     - `reader_claude_md`: absolute path to your NanoClaw group **`CLAUDE.md`**
     - `digest_to_email`: where to send the digest mail  
     Or set `STEEP_READER_CLAUDE_MD` / `STEEP_DIGEST_TO_EMAIL` in the environment.

6. **Run**

   ```bash
   export STEEP_REPO_ROOT=/path/to/steep  # optional if not cwd
   steep-digest run
   ```

   Cursor state defaults to **`state/digest-cursor.json`** (gitignored via `state/`).

## Allowlist syntax

See comments in **`config/newsletter-allowlist.yaml`**. Examples:

- Full address: `newsletter@example.com`
- Domain (anyone at host): `@substack.com`
- Bare domain: `beehiiv.com`

## NanoClaw

Mount or clone this repo where your scheduled task runs, ensure Python venv + env vars, then schedule **one task** (e.g. 09:00 local) with a command like:

```bash
cd /path/to/steep && .venv/bin/steep-digest run
```

Details: **`docs/nanoclaw-runbook.md`**.

## Design spec

**`docs/superpowers/specs/2026-04-08-steep-newsletter-digest-design.md`**

## License

See repository root (add if needed).
