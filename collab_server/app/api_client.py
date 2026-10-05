"""
Thin wrapper around the MyoOptix Collab REST API.
All methods are synchronous (called from Qt main thread or worker thread).
"""

import json
import ssl
import urllib.request
import urllib.error
from typing import Optional

API_BASE          = "https://pleasant-miracle-production-95c3.up.railway.app"
TIMEOUT           = 10   # seconds (default)
TIMEOUT_REGISTER  = 30   # seconds (email sending can be slow)


_system_ctx = ssl.create_default_context()   # uses the OS trust store
_bundled_ctx = None                          # built on demand from certifi


def _bundled_context() -> ssl.SSLContext:
    """CA bundle shipped with the app, used only as a fallback."""
    global _bundled_ctx
    if _bundled_ctx is None:
        import certifi
        _bundled_ctx = ssl.create_default_context(cafile=certifi.where())
    return _bundled_ctx


def _urlopen(req, timeout):
    """Open `req`, retrying with the bundled CA bundle on a verification error.

    The OS trust store is tried first so that networks with a TLS-inspecting
    proxy keep working. Windows machines that never received the self-signed
    ISRG Root X2 validate our chain through the X1 cross-sign instead, which
    expired 2025-09-16; certifi carries the self-signed root, so the retry
    succeeds there. Only verification errors are retried — the request never
    reached the server, so re-sending it is safe.
    """
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=_system_ctx)
    except urllib.error.URLError as e:
        if not isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError):
            raise
        return urllib.request.urlopen(req, timeout=timeout, context=_bundled_context())


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
        with _urlopen(req, timeout) as resp:
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
