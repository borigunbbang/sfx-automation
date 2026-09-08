-- U01: 초기 스키마 + RLS (TECH_SPEC.md 5. 데이터 모델 기준)
-- Supabase SQL Editor에서 전체를 한 번에 실행한다.
-- auth.users는 Supabase Auth가 이미 관리하므로 별도 users 테이블은 만들지 않는다.

create extension if not exists pgcrypto; -- gen_random_uuid() 용 (Supabase는 보통 기본 활성화되어 있음)

-- ─────────────────────────────────────────────
-- 1. projects
-- ─────────────────────────────────────────────
create table if not exists public.projects (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references auth.users(id) on delete cascade,
  video_path        text,
  roi               jsonb,               -- {x, y, width, height}
  status            text not null default 'pending'
                      check (status in ('pending', 'processing', 'done', 'failed')),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index if not exists projects_user_id_idx on public.projects(user_id);

-- ─────────────────────────────────────────────
-- 2. reference_images (사용자별 참고 이미지 라이브러리)
-- ─────────────────────────────────────────────
create table if not exists public.reference_images (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references auth.users(id) on delete cascade,
  image_path        text not null,       -- Supabase Storage 경로
  effect_type       text not null,
  sfx_folder        text not null,       -- Supabase Storage 경로
  created_at        timestamptz not null default now()
);

create index if not exists reference_images_user_id_idx on public.reference_images(user_id);

-- ─────────────────────────────────────────────
-- 3. events (project에 종속, user_id는 없고 project를 통해 소유자 확인)
-- ─────────────────────────────────────────────
create table if not exists public.events (
  id                          uuid primary key default gen_random_uuid(),
  project_id                  uuid not null references public.projects(id) on delete cascade,
  start_ms                    integer not null,
  end_ms                      integer not null,
  representative_frame_path   text,
  effect_type                 text not null default 'unknown',
  match_score                 real,
  matched_sfx_path            text,
  created_at                  timestamptz not null default now()
);

create index if not exists events_project_id_idx on public.events(project_id);

-- ─────────────────────────────────────────────
-- updated_at 자동 갱신 (projects)
-- ─────────────────────────────────────────────
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists projects_set_updated_at on public.projects;
create trigger projects_set_updated_at
  before update on public.projects
  for each row execute function public.set_updated_at();

-- ─────────────────────────────────────────────
-- RLS 활성화
-- ─────────────────────────────────────────────
alter table public.projects enable row level security;
alter table public.reference_images enable row level security;
alter table public.events enable row level security;

-- ─────────────────────────────────────────────
-- RLS 정책: projects (본인 user_id 행만 CRUD)
-- ─────────────────────────────────────────────
drop policy if exists "projects_select_own" on public.projects;
create policy "projects_select_own" on public.projects
  for select using (auth.uid() = user_id);

drop policy if exists "projects_insert_own" on public.projects;
create policy "projects_insert_own" on public.projects
  for insert with check (auth.uid() = user_id);

drop policy if exists "projects_update_own" on public.projects;
create policy "projects_update_own" on public.projects
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "projects_delete_own" on public.projects;
create policy "projects_delete_own" on public.projects
  for delete using (auth.uid() = user_id);

-- ─────────────────────────────────────────────
-- RLS 정책: reference_images (본인 user_id 행만 CRUD)
-- ─────────────────────────────────────────────
drop policy if exists "reference_images_select_own" on public.reference_images;
create policy "reference_images_select_own" on public.reference_images
  for select using (auth.uid() = user_id);

drop policy if exists "reference_images_insert_own" on public.reference_images;
create policy "reference_images_insert_own" on public.reference_images
  for insert with check (auth.uid() = user_id);

drop policy if exists "reference_images_update_own" on public.reference_images;
create policy "reference_images_update_own" on public.reference_images
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "reference_images_delete_own" on public.reference_images;
create policy "reference_images_delete_own" on public.reference_images
  for delete using (auth.uid() = user_id);

-- ─────────────────────────────────────────────
-- RLS 정책: events (user_id가 없으므로 project_id를 통해 소유자 확인)
-- ─────────────────────────────────────────────
drop policy if exists "events_select_own" on public.events;
create policy "events_select_own" on public.events
  for select using (
    exists (
      select 1 from public.projects p
      where p.id = events.project_id and p.user_id = auth.uid()
    )
  );

drop policy if exists "events_insert_own" on public.events;
create policy "events_insert_own" on public.events
  for insert with check (
    exists (
      select 1 from public.projects p
      where p.id = events.project_id and p.user_id = auth.uid()
    )
  );

drop policy if exists "events_update_own" on public.events;
create policy "events_update_own" on public.events
  for update using (
    exists (
      select 1 from public.projects p
      where p.id = events.project_id and p.user_id = auth.uid()
    )
  ) with check (
    exists (
      select 1 from public.projects p
      where p.id = events.project_id and p.user_id = auth.uid()
    )
  );

drop policy if exists "events_delete_own" on public.events;
create policy "events_delete_own" on public.events
  for delete using (
    exists (
      select 1 from public.projects p
      where p.id = events.project_id and p.user_id = auth.uid()
    )
  );
