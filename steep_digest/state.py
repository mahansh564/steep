from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class DigestState:
    version: int = 1
    last_internal_date_ms: int = 0

    @classmethod
    def load(cls, path: Path) -> DigestState:
        if not path.is_file():
            return cls()
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            version=int(data.get("version", 1)),
            last_internal_date_ms=int(data.get("last_internal_date_ms", 0)),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
