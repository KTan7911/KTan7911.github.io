-- ============================================================
--  小屋 · 权限修复
--  用法：Supabase 后台 → SQL Editor → New query → 粘贴 → Run
--
--  背景：之前用 revoke all 把表权限收得太干净了。
--        RLS 负责「行级过滤」，但表级权限必须单独授予。
-- ============================================================

-- ---------- 1. 授予登录用户表级权限 ----------
-- entries：只能查 + 增（刻意不给 update/delete，保证不可改不可删）
grant select, insert on public.entries  to authenticated;

-- profiles：可以查 + 增 + 改（资料可以改）
grant select, insert, update on public.profiles to authenticated;

-- ---------- 2. 未来新建的表也自动带上权限 ----------
alter default privileges in schema public
  grant select, insert on tables to authenticated;

-- ---------- 3. 确认 RLS 是开着的 ----------
alter table public.entries  enable row level security;
alter table public.profiles enable row level security;

-- ---------- 4. 重新声明策略（幂等，确保存在） ----------
-- entries：只能看自己的、只能插自己的
drop policy if exists "entries_select_own" on public.entries;
create policy "entries_select_own" on public.entries
  for select to authenticated using (auth.uid() = user_id);

drop policy if exists "entries_insert_own" on public.entries;
create policy "entries_insert_own" on public.entries
  for insert to authenticated with check (auth.uid() = user_id);

-- profiles：只能看/插/改自己的
drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles
  for select to authenticated using (auth.uid() = user_id);

drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own" on public.profiles
  for insert to authenticated with check (auth.uid() = user_id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles
  for update to authenticated using (auth.uid() = user_id)
                            with check (auth.uid() = user_id);

-- ---------- 5. 匿名用户彻底没权限（双保险） ----------
revoke all on public.entries  from anon;
revoke all on public.profiles from anon;

-- ============================================================
--  完成 ✅
--
--  验证：
--  1) 小屋页面能正常发送、能保存资料
--  2) 记录依然改不了、删不掉（没有 update/delete 权限）
-- ============================================================
