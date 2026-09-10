-- ============================================================
--  小屋 · 数据库初始化
--  用法：Supabase 后台 → 左侧 SQL Editor → New query → 粘贴全部 → Run
--  可重复执行，不会出错
-- ============================================================

-- ---------- 1. 记录表 ----------
create table if not exists public.entries (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null default auth.uid() references auth.users(id) on delete cascade,
  kind          text not null default 'text',        -- text | voice
  text          text default '',                     -- 文字内容（语音的转写文字也存这里，前端不显示）
  mood          text not null default 'roar',        -- roar|joy|calm|think|luck
  tags          text[] default '{}',
  audio_url     text,                                -- 语音文件地址（二期）
  duration_text text,                                -- 语音时长 '0:32'
  duration_sec  int,                                 -- 语音时长秒数
  created_at    timestamptz not null default now()
);

comment on table  public.entries is '小屋 · 记录（不可修改、不可删除）';
comment on column public.entries.text is '文字内容；语音条目的转写文字也存这里，前端不展示';

-- 常用索引
create index if not exists entries_user_created_idx on public.entries (user_id, created_at desc);

-- ---------- 2. 开启 RLS ----------
alter table public.entries enable row level security;

-- ---------- 3. 安全策略：只能操作自己的数据 ----------
drop policy if exists "entries_select_own" on public.entries;
create policy "entries_select_own" on public.entries
  for select using (auth.uid() = user_id);

drop policy if exists "entries_insert_own" on public.entries;
create policy "entries_insert_own" on public.entries
  for insert with check (auth.uid() = user_id);

-- ⚠️ 刻意不创建 UPDATE / DELETE 策略：
--    RLS 默认拒绝，因此「不可修改、不可删除」由数据库强制执行，
--    即使有人篡改前端代码也改不动、删不掉。

-- ---------- 4. 收回匿名角色的直接权限（双保险） ----------
revoke all on public.entries from anon;

-- ============================================================
--  完成 ✅
--  验证：Table Editor 里应该能看到 entries 表；
--        随便插一条数据，用另一个账号登录应该完全看不到。
-- ============================================================
