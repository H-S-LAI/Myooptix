"""
Thin wrapper around the MyoOptix Collab REST API.
All methods are synchronous (called from Qt main thread or worker thread).
"""

import json
import urllib.request
import urllib.error
from typing import Optional

API_BASE          = "https://pleasant-miracle-production-95c3.up.railway.app"
TIMEOUT           = 10   # seconds (default)
TIMEOUT_REGISTER  = 30   # seconds (email sending can be slow)


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def _request(method: str, path: str, body: Optional[dict] = None,
             token: Optional[str] = None, timeout: int = TIMEOUT) -> dict:
    url  = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("detail", str(e))
        except Exception:
            detail = str(e)
        raise APIError(detail, e.code)
    except urllib.error.URLError as e:
        raise APIError(f"Cannot reach server — check your internet connection.\n({e.reason})")
    except Exception as e:
        raise APIError(str(e))


def register(email: str, password: str, full_name: str, institution: str) -> dict:
    return _request("POST", "/auth/register", {
        "email": email, "password": password,
        "full_name": full_name, "institution": institution,
    }, timeout=TIMEOUT_REGISTER)


def login(email: str, password: str) -> dict:
    """Returns {"token": str, "expires_in": int}"""
    return _request("POST", "/auth/login", {"email": email, "password": password})


def verify(token: str) -> dict:
    """Returns {"valid": True, "email": str, "full_name": str, "institution": str}"""
    return _request("GET", "/auth/verify", token=token)


def log_analysis(token: str, filename: str,
                 file_size_mb: float = 0.0, duration_sec: float = 0.0) -> dict:
    return _request("POST", "/log/analysis", {
        "filename": filename,
        "file_size_mb": round(file_size_mb, 2),
        "duration_sec": round(duration_sec, 1),
    }, token=token)
