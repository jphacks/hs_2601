-- 公開バケットは policy 無しで /object/public/ が読めるので、
-- 一覧 API まで anon に開けていた select policy は外す（下書きの画像も列挙できてしまうため）。
drop policy if exists "public read plans bucket" on storage.objects;

-- 上書き保存で updated_at が進むようにする。
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists route_plans_set_updated_at on public.route_plans;
create trigger route_plans_set_updated_at
  before update on public.route_plans
  for each row execute function public.set_updated_at();
