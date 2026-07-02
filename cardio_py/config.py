"""
Persistent config — saved to config.json in the project folder.
Avoids re-entering paths on every page refresh.
"""

import json
import os
from pathlib import Path

_CONFIG_FILE = Path(__file__).parent.parent / "config.json"


def load() -> dict:
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def save(data: dict) -> None:
    existing = load()
    existing.update(data)
    _CONFIG_FILE.write_text(json.dumps(existing, indent=2))
