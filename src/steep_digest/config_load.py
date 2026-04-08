from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from steep_digest.paths import config_dir


def load_digest_config(root: Path) -> dict[str, Any]:
    path = config_dir(root) / "digest.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("digest.yaml must be a mapping")
    return data


def resolve_cursor_path(root: Path, cfg: dict[str, Any]) -> Path:
    raw = cfg.get("cursor_path") or "state/digest-cursor.json"
    p = Path(raw)
    return p if p.is_absolute() else (root / p)


def resolve_reader_path(root: Path, cfg: dict[str, Any]) -> Path:
    env_p = (os.environ.get("STEEP_READER_CLAUDE_MD") or "").strip()
    raw = env_p or cfg.get("reader_claude_md")
    if not raw:
        raise ValueError(
            "Set reader_claude_md in config/digest.yaml or STEEP_READER_CLAUDE_MD to your CLAUDE.md path"
        )
    p = Path(raw)
    return p if p.is_absolute() else (root / p)


def resolve_digest_to_email(cfg: dict[str, Any]) -> str:
    env_e = os.environ.get("STEEP_DIGEST_TO_EMAIL", "").strip()
    if env_e:
        return env_e
    v = cfg.get("digest_to_email")
    if not v:
        raise ValueError(
            "Set digest_to_email in config/digest.yaml or STEEP_DIGEST_TO_EMAIL in the environment"
        )
    return str(v).strip()


def bootstrap_days(cfg: dict[str, Any]) -> int:
    v = cfg.get("bootstrap_days", 7)
    return int(v) if v is not None else 7


def subject_template(cfg: dict[str, Any]) -> str:
    t = cfg.get("subject_template")
    if t:
        return str(t)
    return "Steep digest — {date} ({run_id})"
