-- 作る人の一覧（GET /api/routes?creator_id=...）用に、作成者 ID を持たせる。
-- creator_id は作る人のブラウザ（localStorage）のランダム ID。CLI で作った既存の行は null のまま。
alter table public.route_plans add column if not exists creator_id text;

-- 一覧は「作成者で絞って新しい順」なので、その順の複合インデックスにする。
create index if not exists route_plans_creator_created_idx
  on public.route_plans (creator_id, created_at desc);
