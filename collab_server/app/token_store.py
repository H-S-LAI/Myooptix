"""
Persist JWT token to a local file (~/.myooptix_collab/token.json).
Falls back gracefully if read/write fails.
"""

import json
import os
from pathlib import Path

_DIR  = Path.home() / ".myooptix_collab"
_FILE = _DIR / "token.json"


def save(token: str, email: str):
    try:
        _DIR.mkdir(exist_ok=True)
        _FILE.write_text(json.dumps({"token": token, "email": email}))
    except Exception:
        pass


def load() -> tuple[str, str]:
    """Returns (token, email) or ("", "")"""
    try:
        data = json.loads(_FILE.read_text())
        return data.get("token", ""), data.get("email", "")
    except Exception:
        return "", ""


def clear():
    try:
        _FILE.unlink(missing_ok=True)
    except Exception:
        pass
