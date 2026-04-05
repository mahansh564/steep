# steep — Newsletter digest (OpenClaw + Gmail + Telegram)

Daily job (designed for a **Hetzner** VM) that:

1. Reads **allowlisted** Gmail senders
2. Classifies and summarizes with a **cloud LLM** into four buckets: NEED TO KNOW, GOOD TO KNOW, INTERESTING FOR ME, FLUFF
3. Sends **one HTML email** to yourself via **Gmail**
4. Mirrors the **full digest** to **Telegram** (split across messages when needed)

OpenClaw-oriented policy lives in [`SOUL.md`](SOUL.md), [`USER.md`](USER.md), [`AGENTS.md`](AGENTS.md), and [`TOOLS.md`](TOOLS.md). The scheduled runner is the Python CLI [`steep_digest`](steep_digest/).

## Quick start (local)

```bash
cd /path/to/steep
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Export the variables from [`config/example.env`](config/example.env) (see below), then:

```bash
steep-digest run --dry-run
```

`--dry-run` prints the digest and **does not** send email/Telegram or update the cursor.

## Google Cloud / Gmail OAuth

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **Gmail API**.
3. **OAuth consent screen** (External is fine for personal use).
4. Create **OAuth client ID** → Application type **Desktop app**.
5. Download JSON as `credentials.json`.

### First token (recommended: your laptop)

Run once with `GMAIL_CREDENTIALS_PATH` pointing at `credentials.json`. The CLI opens a browser and writes `GMAIL_TOKEN_PATH` (e.g. `token.json`). Copy `token.json` to the server (secure permissions `600`, dedicated Unix user).

On a headless server without a one-time local run, use a desktop machine to produce `token.json`, then deploy it.

Required OAuth scopes (configured in code): `gmail.readonly`, `gmail.send`.

## Telegram

1. Create a bot with [@BotFather](https://t.me/BotFather), copy the token.
2. Get your chat id (e.g. message [@userinfobot](https://t.me/userinfobot) or use `getUpdates` after DMing your bot).

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `digest.env`.

## Allowlist

Copy [`config/example.allowlist.yaml`](config/example.allowlist.yaml) to the server and set `ALLOWLIST_PATH`. Entries can be full addresses or domains (`@substack.com`, `newsletter.com`).

Gmail search uses `from:` clauses joined with `OR`. Very large allowlists may exceed Gmail query limits; prefer labeling in Gmail and narrowing senders if that happens.

## Environment variables

See [`config/example.env`](config/example.env). Minimum:

| Variable | Purpose |
|----------|---------|
| `GMAIL_CREDENTIALS_PATH` | OAuth client JSON |
| `GMAIL_TOKEN_PATH` | Writable path for refreshed user token |
| `ALLOWLIST_PATH` | YAML allowlist |
| `STATE_PATH` | JSON cursor (`last_internal_date_ms`) |
| `DIGEST_TO_EMAIL` | Where to send the digest |
| `OPENAI_API_KEY` | LLM key (OpenAI-compatible by default) |
| `OPENAI_BASE_URL` | Optional (default `https://api.openai.com/v1`) |
| `OPENAI_MODEL` | e.g. `gpt-4o-mini` |
| `TELEGRAM_BOT_TOKEN` | Bot token |
| `TELEGRAM_CHAT_ID` | Your chat id |

Optional: `STEEP_USER_MD_PATH`, `STEEP_MAX_MESSAGES`, `STEEP_LIST_CAP`, `DIGEST_SUBJECT_PREFIX`, `STEEP_DRY_RUN`, `STEEP_VERBOSE`.

Edit **`USER.md`** (or `STEEP_USER_MD_PATH`) so the model can score **INTERESTING FOR ME** against your real interests.

## Hetzner deployment

Example layout (paths are suggestions):

| Path | Content |
|------|---------|
| `/opt/steep` | Git clone + virtualenv `.venv` |
| `/etc/steep/digest.env` | Environment (mode `640`, root:steep) |
| `/etc/steep/credentials.json` | OAuth client (`640`) |
| `/etc/steep/allowlist.yaml` | Allowlist (`640`) |
| `/var/lib/steep/token.json` | User OAuth token (`600`, owner `steep`) |
| `/var/lib/steep/state.json` | Cursor (`600`) |

```bash
sudo useradd --system --home /opt/steep --shell /usr/sbin/nologin steep || true
sudo mkdir -p /opt/steep /etc/steep /var/lib/steep
sudo chown -R steep:steep /opt/steep /var/lib/steep
# deploy code + venv as steep; install with pip install -e .
sudo cp deploy/steep-digest.service /etc/systemd/system/
sudo cp deploy/steep-digest.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now steep-digest.timer
sudo systemctl start steep-digest.service   # manual test
journalctl -u steep-digest.service -e
```

Change `06:30:00` in [`deploy/steep-digest.timer`](deploy/steep-digest.timer) to your preferred **UTC** time.

## Behavior notes

- **Cursor**: After **successful** Telegram **and** Gmail sends, the runner sets `last_internal_date_ms` to the maximum `internalDate` of processed messages. Failures do **not** advance the cursor (the next run may duplicate if one channel succeeded).
- **Order**: Telegram is sent first, then Gmail.
- **Limits**: `STEEP_MAX_MESSAGES` (default `50`) caps how many new messages are summarized per run after the cursor filter.

## License

Specify in-repo as needed.
