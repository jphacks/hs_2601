-- 写真列（道案内）の保存先。1 行 = 1 つの道案内。
-- id は命名（name）の SHA-256 先頭 12 桁。同じ名前で保存し直すと上書きされる。
create table if not exists public.route_plans (
  id          text primary key,
  name        text not null unique,
  status      text not null default 'published' check (status in ('draft', 'published')),
  origin      text not null,
  destination text not null,
  plan_json   jsonb not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- 参加者（anon キー）は公開済みの行だけ読める。書き込みはサーバー（service_role）のみ。
alter table public.route_plans enable row level security;

drop policy if exists "public read published route_plans" on public.route_plans;
create policy "public read published route_plans"
  on public.route_plans for select
  to anon, authenticated
  using (status = 'published');

-- 画像置き場。公開バケットなので URL を知っていれば誰でも見られる。
insert into storage.buckets (id, name, public)
  values ('plans', 'plans', true)
  on conflict (id) do nothing;

drop policy if exists "public read plans bucket" on storage.objects;
create policy "public read plans bucket"
  on storage.objects for select
  to anon, authenticated
  using (bucket_id = 'plans');
