"""
Logic tests for MyoOptix Collab API.
Run: pytest tests/test_api.py -v

Uses FastAPI TestClient with mocked psycopg2 and resend — no real DB needed.
"""
import os
os.environ.setdefault("JWT_SECRET",     "testsecret-long-enough-32chars!!")
os.environ.setdefault("ADMIN_KEY",      "testadmin")
os.environ.setdefault("DATABASE_URL",   "unused-mocked")
os.environ.setdefault("RESEND_API_KEY", "unused")
os.environ.setdefault("NOTIFY_EMAIL",   "admin@test.com")
os.environ.setdefault("FROM_EMAIL",     "noreply@test.com")
os.environ.setdefault("API_BASE_URL",   "http://testserver")

import pytest
from unittest.mock import patch, MagicMock, call
from fastapi.testclient import TestClient
from jose import jwt
from datetime import datetime, timedelta, timezone


def _make_cursor(fetchone=None, fetchall=None):
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.return_value = fetchone
    cur.fetchall.return_value = fetchall or []
    cur.fetchone.side_effect = None
    return cur


def _make_conn(cursor):
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor
    conn.commit = MagicMock()
    return conn


# Import app with no-op patches so module-level code doesn't fail
with patch("psycopg2.connect", return_value=_make_conn(_make_cursor())), \
     patch("resend.Emails.send", return_value=None):
    from main import app, create_token, decode_token, _hash_pw

client = TestClient(app, raise_server_exceptions=True)


def _token(user_id="uid-1", email="test@example.com", hours=2):
    exp = datetime.now(timezone.utc) + timedelta(hours=hours)
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": exp},
        "testsecret-long-enough-32chars!!",
        algorithm="HS256",
    )


# ── JWT helpers ───────────────────────────────────────────────────────────────
def test_create_and_decode_token():
    tok = create_token("abc", "a@b.com")
    p = decode_token(tok)
    assert p["sub"] == "abc"
    assert p["email"] == "a@b.com"


def test_expired_token_raises():
    from fastapi import HTTPException
    exp = datetime.now(timezone.utc) - timedelta(hours=1)
    tok = jwt.encode({"sub": "x", "email": "x@x.com", "exp": exp},
                     "testsecret-long-enough-32chars!!", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        decode_token(tok)
    assert exc.value.status_code == 401


# ── root ──────────────────────────────────────────────────────────────────────
def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── register ──────────────────────────────────────────────────────────────────
def test_register_success():
    cur = _make_cursor(fetchone=None)
    cur.fetchone.side_effect = [None, None, {"id": "req-1"}]  # no pending, no user, then insert returning
    with patch("psycopg2.connect", return_value=_make_conn(cur)), \
         patch("resend.Emails.send", return_value=None):
        r = client.post("/auth/register", json={
            "email": "new@example.com",
            "password": "StrongPass123!",
            "full_name": "Test User",
            "institution": "TMU",
        })
    assert r.status_code == 200
    assert "submitted" in r.json()["message"].lower()


def test_register_duplicate_pending():
    cur = _make_cursor(fetchone={"id": "existing"})
    with patch("psycopg2.connect", return_value=_make_conn(cur)), \
         patch("resend.Emails.send", return_value=None):
        r = client.post("/auth/register", json={
            "email": "dup@example.com", "password": "p",
            "full_name": "X", "institution": "Y",
        })
    assert r.status_code == 400


# ── login ─────────────────────────────────────────────────────────────────────
def test_login_success():
    hashed = _hash_pw("correctpassword")
    cur = _make_cursor(fetchone={"id": "uid-1", "password_hash": hashed, "status": "active"})
    with patch("psycopg2.connect", return_value=_make_conn(cur)):
        r = client.post("/auth/login", json={"email": "a@b.com", "password": "correctpassword"})
    assert r.status_code == 200
    assert "token" in r.json()
    assert r.json()["expires_in"] == 7200


def test_login_wrong_password():
    hashed = _hash_pw("correctpassword")
    cur = _make_cursor(fetchone={"id": "uid-1", "password_hash": hashed, "status": "active"})
    with patch("psycopg2.connect", return_value=_make_conn(cur)):
        r = client.post("/auth/login", json={"email": "a@b.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_login_suspended():
    hashed = _hash_pw("correctpassword")
    cur = _make_cursor(fetchone={"id": "uid-1", "password_hash": hashed, "status": "suspended"})
    with patch("psycopg2.connect", return_value=_make_conn(cur)):
        r = client.post("/auth/login", json={"email": "a@b.com", "password": "correctpassword"})
    assert r.status_code == 403


def test_login_no_user():
    cur = _make_cursor(fetchone=None)
    with patch("psycopg2.connect", return_value=_make_conn(cur)):
        r = client.post("/auth/login", json={"email": "nobody@b.com", "password": "p"})
    assert r.status_code == 401


# ── verify ────────────────────────────────────────────────────────────────────
def test_verify_valid():
    cur = _make_cursor(fetchone={"status": "active", "full_name": "Test", "institution": "TMU"})
    with patch("psycopg2.connect", return_value=_make_conn(cur)):
        r = client.get("/auth/verify", headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_verify_suspended():
    cur = _make_cursor(fetchone={"status": "suspended", "full_name": "X", "institution": "Y"})
    with patch("psycopg2.connect", return_value=_make_conn(cur)):
        r = client.get("/auth/verify", headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 403


def test_verify_no_token():
    r = client.get("/auth/verify")
    assert r.status_code in (401, 403)  # HTTPBearer returns 403; no-header returns 403


# ── analysis log ──────────────────────────────────────────────────────────────
def test_log_analysis():
    cur = _make_cursor()
    with patch("psycopg2.connect", return_value=_make_conn(cur)):
        r = client.post("/log/analysis",
            json={"filename": "sample.mov", "file_size_mb": 45.2, "duration_sec": 12.3},
            headers={"Authorization": f"Bearer {_token()}"},
        )
    assert r.status_code == 200
    assert r.json()["logged"] is True


# ── admin ─────────────────────────────────────────────────────────────────────
def test_admin_wrong_key():
    r = client.get("/admin/users", headers={"Authorization": "Bearer wrongkey"})
    assert r.status_code == 403


def test_admin_correct_key():
    cur = _make_cursor(fetchall=[])
    with patch("psycopg2.connect", return_value=_make_conn(cur)):
        r = client.get("/admin/users", headers={"Authorization": "Bearer testadmin"})
    assert r.status_code == 200
    assert r.json() == []


def test_admin_list_requests():
    rows = [{"id": "r1", "email": "a@b.com", "full_name": "A", "institution": "B",
             "status": "pending", "created_at": "2026-07-09T00:00:00"}]
    cur = _make_cursor(fetchall=rows)
    with patch("psycopg2.connect", return_value=_make_conn(cur)):
        r = client.get("/admin/requests", headers={"Authorization": "Bearer testadmin"})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_admin_approve_not_found():
    cur = _make_cursor(fetchone=None)
    with patch("psycopg2.connect", return_value=_make_conn(cur)), \
         patch("resend.Emails.send", return_value=None):
        r = client.get("/admin/approve/nonexistent?key=testadmin")
    assert r.status_code == 200
    assert "not found" in r.json()["message"].lower()


def test_admin_approve_success():
    req = {"id": "r1", "email": "u@x.com", "full_name": "U", "institution": "X",
           "password_hash": _hash_pw("pass"), "status": "pending"}
    cur = _make_cursor(fetchone=req)
    with patch("psycopg2.connect", return_value=_make_conn(cur)), \
         patch("resend.Emails.send", return_value=None):
        r = client.get("/admin/approve/r1?key=testadmin")
    assert r.status_code == 200
    assert "approved" in r.json()["message"].lower()


def test_admin_reject_wrong_key():
    r = client.get("/admin/reject/some-id?key=badkey")
    assert r.status_code == 403


def test_admin_suspend():
    cur = _make_cursor()
    with patch("psycopg2.connect", return_value=_make_conn(cur)):
        r = client.post("/admin/users/uid-1/suspend",
                        headers={"Authorization": "Bearer testadmin"})
    assert r.status_code == 200


def test_admin_activate():
    cur = _make_cursor()
    with patch("psycopg2.connect", return_value=_make_conn(cur)):
        r = client.post("/admin/users/uid-1/activate",
                        headers={"Authorization": "Bearer testadmin"})
    assert r.status_code == 200
