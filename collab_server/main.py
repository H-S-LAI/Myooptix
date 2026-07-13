from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta, timezone
import bcrypt
from jose import JWTError, jwt
from pathlib import Path
import asyncpg
import os
import json
import urllib.request
import logging
import asyncio
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

load_dotenv()

# ── config ────────────────────────────────────────────────────────────────────
SECRET_KEY   = os.environ["JWT_SECRET"]
ADMIN_KEY    = os.environ["ADMIN_KEY"]
DB_URL       = os.environ["DATABASE_URL"]
NOTIFY_EMAIL  = os.environ["NOTIFY_EMAIL"]
FROM_EMAIL    = os.environ.get("FROM_EMAIL", "MyoOptix <b101110099@tmu.edu.tw>")
BREVO_API_KEY = os.environ["BREVO_API_KEY"]
API_BASE_URL  = os.environ["API_BASE_URL"]

TOKEN_EXPIRE_HOURS = 2

bearer = HTTPBearer()

def _hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _verify_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ── DB pool ───────────────────────────────────────────────────────────────────
_pool: asyncpg.Pool = None

SCHEMA_SQL = """
create extension if not exists "pgcrypto";

create table if not exists public.users (
  id            uuid primary key default gen_random_uuid(),
  email         text unique not null,
  password_hash text not null,
  full_name     text not null,
  institution   text not null,
  status        text not null default 'active'
                  check (status in ('active', 'suspended')),
  created_at    timestamptz not null default now()
);

create table if not exists public.pending_requests (
  id            uuid primary key default gen_random_uuid(),
  email         text unique not null,
  password_hash text not null,
  full_name     text not null,
  institution   text not null,
  status        text not null default 'pending'
                  check (status in ('pending', 'approved', 'rejected')),
  created_at    timestamptz not null default now()
);

create table if not exists public.login_logs (
  id         bigserial primary key,
  user_id    uuid references public.users(id) on delete set null,
  email      text not null,
  ip_address text,
  success    boolean not null,
  created_at timestamptz not null default now()
);

create table if not exists public.analysis_logs (
  id            bigserial primary key,
  user_id       uuid references public.users(id) on delete set null,
  email         text not null,
  filename      text not null,
  file_size_mb  numeric(8,2),
  duration_sec  numeric(8,1),
  ip_address    text,
  created_at    timestamptz not null default now()
);
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    # Railway internal Postgres uses no SSL; Supabase pooler needs ssl=require
    ssl = "require" if "supabase" in DB_URL else None
    _pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=5, ssl=ssl)
    async with _pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    logging.info("DB schema ready")
    yield
    await _pool.close()

app = FastAPI(title="MyoOptix Collab API", lifespan=lifespan, debug=True)

_static = Path(__file__).parent / "static"
if _static.exists():
    app.mount("/web", StaticFiles(directory=str(_static), html=True), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── JWT ───────────────────────────────────────────────────────────────────────
def create_token(user_id: str, email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": user_id, "email": email, "exp": exp}, SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    return decode_token(creds.credentials)

def require_admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if creds.credentials != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Admin access required")

# ── schemas ───────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    institution: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AnalysisLogRequest(BaseModel):
    filename: str
    file_size_mb: float = 0.0
    duration_sec: float = 0.0

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    institution: str

# ── helpers ───────────────────────────────────────────────────────────────────
def _get_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")

async def _send_email(to: str, subject: str, html: str):
    def _brevo_send():
        sender_email = FROM_EMAIL.split("<")[-1].rstrip(">").strip() if "<" in FROM_EMAIL else FROM_EMAIL
        payload = json.dumps({
            "sender":   {"name": "MyoOptix", "email": sender_email},
            "to":       [{"email": to}],
            "subject":  subject,
            "htmlContent": html,
        }).encode()
        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=payload,
            headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read()
    try:
        await asyncio.to_thread(_brevo_send)
    except Exception as e:
        logging.error(f"Brevo email error: {e}")

async def _send_admin_notify(req_id: str, full_name: str, email: str, institution: str):
    approve_url = f"{API_BASE_URL}/admin/approve/{req_id}?key={ADMIN_KEY}"
    reject_url  = f"{API_BASE_URL}/admin/reject/{req_id}?key={ADMIN_KEY}"
    await _send_email(
        to=NOTIFY_EMAIL,
        subject=f"[MyoOptix] New registration: {full_name}",
        html=f"""
        <h2>New MyoOptix Collab registration</h2>
        <table>
          <tr><td><b>Name</b></td><td>{full_name}</td></tr>
          <tr><td><b>Email</b></td><td>{email}</td></tr>
          <tr><td><b>Institution</b></td><td>{institution}</td></tr>
        </table><br>
        <a href="{approve_url}" style="background:#7c9c6e;color:#fff;padding:10px 24px;border-radius:6px;text-decoration:none;font-weight:bold;">Approve</a>
        &nbsp;&nbsp;
        <a href="{reject_url}" style="background:#c0392b;color:#fff;padding:10px 24px;border-radius:6px;text-decoration:none;font-weight:bold;">Reject</a>
        """,
    )

async def _send_approval_email(email: str, full_name: str):
    await _send_email(
        to=email,
        subject="[MyoOptix] Your account has been approved",
        html=f"<h2>Welcome to MyoOptix Collab, {full_name}!</h2><p>Your account is now active. Log in with your registered email and password.</p>",
    )

async def _send_rejection_email(email: str, full_name: str):
    await _send_email(
        to=email,
        subject="[MyoOptix] Registration update",
        html=f"<h2>Hi {full_name},</h2><p>Your registration was not approved. Contact {NOTIFY_EMAIL} for more information.</p>",
    )

async def _send_registration_received_email(email: str, full_name: str):
    await _send_email(
        to=email,
        subject="[MyoOptix] Registration received — pending review",
        html=f"""
        <h2>Hi {full_name},</h2>
        <p>We've received your registration request for <b>MyoOptix Collab</b>.</p>
        <p>Our team will review your application and notify you once it's approved.</p>
        <p style="color:#8a8070;font-size:13px;">If you have any questions, contact us at {NOTIFY_EMAIL}.</p>
        """,
    )

# ── auth ──────────────────────────────────────────────────────────────────────
@app.post("/auth/register")
async def register(body: RegisterRequest, request: Request):
    async with _pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id, status FROM public.pending_requests WHERE email=$1", body.email)
        if existing:
            if existing["status"] == "pending":
                raise HTTPException(400, "A registration request for this email is already pending.")
            # rejected: allow re-application by deleting old record
            await conn.execute("DELETE FROM public.pending_requests WHERE email=$1", body.email)
        if await conn.fetchrow("SELECT id FROM public.users WHERE email=$1", body.email):
            raise HTTPException(400, "An account with this email already exists.")
        h = _hash_pw(body.password)
        row = await conn.fetchrow(
            "INSERT INTO public.pending_requests (email, password_hash, full_name, institution) VALUES ($1,$2,$3,$4) RETURNING id",
            body.email, h, body.full_name, body.institution
        )
    await _send_admin_notify(str(row["id"]), body.full_name, body.email, body.institution)
    await _send_registration_received_email(body.email, body.full_name)
    return {"message": "Registration submitted. You will receive an email when approved."}


@app.post("/auth/login")
async def login(body: LoginRequest, request: Request):
    ip = _get_ip(request)
    async with _pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id, password_hash, status FROM public.users WHERE email=$1", body.email)
        success = (user is not None
                   and _verify_pw(body.password, user["password_hash"])
                   and user["status"] == "active")
        await conn.execute(
            "INSERT INTO public.login_logs (user_id, email, ip_address, success) VALUES ($1,$2,$3,$4)",
            str(user["id"]) if user else None, body.email, ip, success
        )
    if not success:
        if user and user["status"] == "suspended":
            raise HTTPException(403, "Account suspended. Please contact the administrator.")
        raise HTTPException(401, "Invalid email or password.")
    return {"token": create_token(str(user["id"]), body.email), "expires_in": TOKEN_EXPIRE_HOURS * 3600}


@app.get("/auth/verify")
async def verify(user: dict = Depends(current_user)):
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("SELECT status, full_name, institution FROM public.users WHERE id=$1", user["sub"])
    if not row or row["status"] != "active":
        raise HTTPException(403, "Account suspended or not found.")
    return {"valid": True, "email": user["email"], "full_name": row["full_name"], "institution": row["institution"]}


@app.post("/log/analysis")
async def log_analysis(body: AnalysisLogRequest, request: Request, user: dict = Depends(current_user)):
    async with _pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO public.analysis_logs (user_id, email, filename, file_size_mb, duration_sec, ip_address) VALUES ($1,$2,$3,$4,$5,$6)",
            user["sub"], user["email"], body.filename, body.file_size_mb, body.duration_sec, _get_ip(request)
        )
    return {"logged": True}


# ── admin ─────────────────────────────────────────────────────────────────────
@app.get("/admin/requests")
async def admin_list_requests(_=Depends(require_admin)):
    async with _pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, email, full_name, institution, status, created_at FROM public.pending_requests ORDER BY created_at DESC")
    return [dict(r) for r in rows]


@app.get("/admin/approve/{req_id}")
async def admin_approve(req_id: str, key: str = ""):
    if key != ADMIN_KEY:
        raise HTTPException(403, "Forbidden")
    async with _pool.acquire() as conn:
        req = await conn.fetchrow("SELECT * FROM public.pending_requests WHERE id=$1 AND status='pending'", req_id)
        if not req:
            return {"message": "Request not found or already processed."}
        await conn.execute(
            "INSERT INTO public.users (email, password_hash, full_name, institution) VALUES ($1,$2,$3,$4) ON CONFLICT (email) DO NOTHING",
            req["email"], req["password_hash"], req["full_name"], req["institution"]
        )
        await conn.execute("UPDATE public.pending_requests SET status='approved' WHERE id=$1", req_id)
    await _send_approval_email(req["email"], req["full_name"])
    return {"message": f"Approved and email sent to {req['email']}."}


@app.get("/admin/reject/{req_id}")
async def admin_reject(req_id: str, key: str = ""):
    if key != ADMIN_KEY:
        raise HTTPException(403, "Forbidden")
    async with _pool.acquire() as conn:
        req = await conn.fetchrow("SELECT * FROM public.pending_requests WHERE id=$1 AND status='pending'", req_id)
        if not req:
            return {"message": "Request not found or already processed."}
        await conn.execute("UPDATE public.pending_requests SET status='rejected' WHERE id=$1", req_id)
    await _send_rejection_email(req["email"], req["full_name"])
    return {"message": f"Rejected and email sent to {req['email']}."}


@app.get("/admin/users")
async def admin_list_users(_=Depends(require_admin)):
    async with _pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, email, full_name, institution, status, created_at FROM public.users ORDER BY created_at DESC")
    return [dict(r) for r in rows]


@app.post("/admin/users/{user_id}/suspend")
async def admin_suspend(user_id: str, _=Depends(require_admin)):
    async with _pool.acquire() as conn:
        await conn.execute("UPDATE public.users SET status='suspended' WHERE id=$1", user_id)
    return {"message": "User suspended."}


@app.post("/admin/users/{user_id}/activate")
async def admin_activate(user_id: str, _=Depends(require_admin)):
    async with _pool.acquire() as conn:
        await conn.execute("UPDATE public.users SET status='active' WHERE id=$1", user_id)
    return {"message": "User activated."}


@app.post("/admin/users")
async def admin_create_user(body: CreateUserRequest, _=Depends(require_admin)):
    async with _pool.acquire() as conn:
        exists = await conn.fetchrow("SELECT id FROM public.users WHERE email=$1", body.email)
        if exists:
            raise HTTPException(400, "User with this email already exists.")
        await conn.execute(
            "INSERT INTO public.users (email, password_hash, full_name, institution) VALUES ($1,$2,$3,$4)",
            body.email, _hash_pw(body.password), body.full_name, body.institution,
        )
    return {"message": f"User {body.email} created."}


@app.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, _=Depends(require_admin)):
    async with _pool.acquire() as conn:
        user = await conn.fetchrow("SELECT email FROM public.users WHERE id=$1", user_id)
        if not user:
            raise HTTPException(404, "User not found.")
        await conn.execute("DELETE FROM public.analysis_logs WHERE user_id=$1", user_id)
        await conn.execute("DELETE FROM public.login_logs WHERE user_id=$1", user_id)
        await conn.execute("DELETE FROM public.pending_requests WHERE email=$1", user["email"])
        await conn.execute("DELETE FROM public.users WHERE id=$1", user_id)
    return {"message": f"User {user['email']} and all associated logs deleted."}


@app.delete("/admin/requests/rejected")
async def admin_clear_rejected(_=Depends(require_admin)):
    async with _pool.acquire() as conn:
        result = await conn.execute("DELETE FROM public.pending_requests WHERE status='rejected'")
    count = int(result.split()[-1])
    return {"message": f"Deleted {count} rejected request(s)."}


@app.get("/admin/logs/login")
async def admin_login_logs(_=Depends(require_admin)):
    async with _pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM public.login_logs ORDER BY created_at DESC LIMIT 500")
    return [dict(r) for r in rows]


@app.get("/admin/logs/analysis")
async def admin_analysis_logs(_=Depends(require_admin)):
    async with _pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM public.analysis_logs ORDER BY created_at DESC LIMIT 500")
    return [dict(r) for r in rows]


@app.get("/")
def root():
    return {"service": "MyoOptix Collab API", "status": "ok"}
