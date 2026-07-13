-- Add analysis_logs table for per-file usage tracking

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

alter table public.analysis_logs enable row level security;
