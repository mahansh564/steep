from __future__ import annotations

import os
from dataclasses import dataclass


def _truthy(key: str, default: bool = False) -> bool:
    v = os.environ.get(key)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    gmail_credentials_path: str
    gmail_token_path: str
    allowlist_path: str
    state_path: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    telegram_bot_token: str
    telegram_chat_id: str
    digest_to_email: str
    user_md_path: str | None
    subject_prefix: str
    dry_run: bool
    verbose: bool

    @staticmethod
    def from_environ() -> Settings:
        return Settings(
            gmail_credentials_path=os.environ["GMAIL_CREDENTIALS_PATH"],
            gmail_token_path=os.environ["GMAIL_TOKEN_PATH"],
            allowlist_path=os.environ["ALLOWLIST_PATH"],
            state_path=os.environ["STATE_PATH"],
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            openai_base_url=os.environ.get(
                "OPENAI_BASE_URL", "https://api.openai.com/v1"
            ).rstrip("/"),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
            digest_to_email=os.environ["DIGEST_TO_EMAIL"],
            user_md_path=os.environ.get("STEEP_USER_MD_PATH") or None,
            subject_prefix=os.environ.get("DIGEST_SUBJECT_PREFIX", "Newsletter digest"),
            dry_run=_truthy("STEEP_DRY_RUN", False),
            verbose=_truthy("STEEP_VERBOSE", False),
        )
