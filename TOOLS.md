# Tools — steep-digest

| Capability | Implementation |
|------------|----------------|
| Read allowlisted mail | `googleapiclient` Gmail API v1, OAuth2 user creds |
| Classify + summarize | OpenAI-compatible Chat Completions + JSON schema |
| Send digest email | Gmail API `users.messages.send` (RFC 822 raw) |
| Send Telegram | HTTPS `POST https://api.telegram.org/bot<token>/sendMessage` |
| CLI entrypoint | `steep-digest run` or `python -m steep_digest run` |

## CLI flags

- `--dry-run` — classify and print digest to stdout; no Gmail send, no Telegram; state file unchanged.
- `--verbose` — debug logging.

Environment variables are documented in [`config/example.env`](config/example.env).
