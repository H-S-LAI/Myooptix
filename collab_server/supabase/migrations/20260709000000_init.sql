-- MyoOptix Collab: users, pending requests, login logs

create extension if not exists "pgcrypto";

-- ── users ──────────────────────────────────────────────────────────────────
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

-- ── pending_requests ───────────────────────────────────────────────────────
create table if not exists public.pending_requests (
  id          uuid primary key default gen_random_uuid(),
  email       text unique not null,
  password_hash text not null,
  full_name   text not null,
  institution text not null,
  status      text not null default 'pending'
                check (status in ('pending', 'approved', 'rejected')),
  created_at  timestamptz not null default now()
);

-- ── login_logs ─────────────────────────────────────────────────────────────
create table if not exists public.login_logs (
  id         bigserial primary key,
  user_id    uuid references public.users(id) on delete set null,
  email      text not null,
  ip_address text,
  success    boolean not null,
  created_at timestamptz not null default now()
);

-- ── RLS: disable public access, server uses service_role ──────────────────
alter table public.users            enable row level security;
alter table public.pending_requests enable row level security;
alter table public.login_logs       enable row level security;

-- No anon/authenticated policies — only service_role (bypasses RLS) can touch these tables.
