-- ============================================================
--  小屋 · 第二步：个人资料表
--  用法：Supabase 后台 → SQL Editor → New query → 粘贴 → Run
--  可重复执行，不会出错
-- ============================================================

-- ---------- 1. 个人资料表 ----------
create table if not exists public.profiles (
  user_id     uuid primary key references auth.users(id) on delete cascade,
  nickname    text default '',                 -- 昵称
  avatar_kind text default 'sprout',           -- 卡通形象：sprout|bear|cat|bunny|cloud|pig
  avatar_url  text,                            -- 自定义头像（上传的照片），优先显示
  birthday    date,                            -- 生日
  gender      text default '',                 -- 性别（可选）
  hobbies     text[] default '{}',             -- 爱好标签
  bio         text default '',                 -- 个性签名
  updated_at  timestamptz not null default now()
);

comment on table public.profiles is '小屋 · 个人资料（仅本人可见）';

-- ---------- 2. 开启 RLS ----------
alter table public.profiles enable row level security;

-- ---------- 3. 策略：只能读写自己的资料 ----------
drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles
  for select using (auth.uid() = user_id);

drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own" on public.profiles
  for insert with check (auth.uid() = user_id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles
  for update using (auth.uid() = user_id)
             with check (auth.uid() = user_id);

-- 注：资料可以改（这是允许的），但记录（entries）依旧不可改不可删

-- ---------- 4. 收回匿名权限 ----------
revoke all on public.profiles from anon;

-- ============================================================
--  完成 ✅
--  验证：Table Editor 里会多出 profiles 表
-- ============================================================
