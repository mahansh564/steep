from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Root of the steep checkout (directory containing config/)."""
    env = os.environ.get("STEEP_REPO_ROOT")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def config_dir(root: Path | None = None) -> Path:
    r = root or repo_root()
    return r / "config"
