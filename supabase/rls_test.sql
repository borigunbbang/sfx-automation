-- U01 완료 기준 테스트: RLS가 실제로 서로의 행을 막는지 SQL Editor에서 직접 확인.
-- 전제: 0001_init_schema.sql을 먼저 실행했고, Authentication > Users에서
--       테스트 계정 두 개(test1@example.com, test2@example.com)를 만들어 두었다.
--
-- 사용법:
--   1) Authentication > Users에서 두 계정의 UUID를 복사해 아래 <USER1_UUID>, <USER2_UUID>를 치환
--   2) 이 파일 전체를 SQL Editor에 붙여넣고 한 번에 실행
--   3) 각 SELECT 결과가 "본인 행만" 보이면 성공

-- ── 0. service_role(관리자 권한)로 각 유저 소유 project 1개씩 미리 생성 ──
-- SQL Editor는 기본적으로 postgres 권한이라 RLS를 우회하므로, 여기서는 그냥 insert 가능.
insert into public.projects (user_id, video_path, status)
values ('<USER1_UUID>', 'videos/user1_sample.mp4', 'pending')
returning id, user_id;

insert into public.projects (user_id, video_path, status)
values ('<USER2_UUID>', 'videos/user2_sample.mp4', 'pending')
returning id, user_id;

-- ── 1. user1로 "가장" 해서 조회 ──
-- Supabase SQL Editor에서 RLS 정책이 적용된 상태로 특정 유저를 흉내내는 표준 트릭:
set local role authenticated;
select set_config('request.jwt.claim.sub', '<USER1_UUID>', true);
select set_config('request.jwt.claims', json_build_object('sub', '<USER1_UUID>')::text, true);

-- 기대 결과: user1의 project 1건만 보여야 한다 (user2 행은 보이면 안 됨)
select id, user_id, video_path from public.projects;

reset role;

-- ── 2. user2로 "가장" 해서 조회 ──
set local role authenticated;
select set_config('request.jwt.claim.sub', '<USER2_UUID>', true);
select set_config('request.jwt.claims', json_build_object('sub', '<USER2_UUID>')::text, true);

-- 기대 결과: user2의 project 1건만 보여야 한다 (user1 행은 보이면 안 됨)
select id, user_id, video_path from public.projects;

reset role;

-- ── 3. (선택) 정리 — 테스트 행 삭제하고 싶으면 postgres 권한으로 실행 ──
-- delete from public.projects where video_path in ('videos/user1_sample.mp4', 'videos/user2_sample.mp4');

-- ── 참고: 더 실제와 가까운 테스트 ──
-- 위 SQL Editor 트릭 대신, 브라우저 시크릿창 2개를 열어 각각 test1/test2로 로그인한 뒤
-- Supabase JS 클라이언트(또는 REST API: `apikey: <anon key>`, `Authorization: Bearer <해당 유저의 access_token>`)로
--   GET {project_url}/rest/v1/projects?select=*
-- 를 호출해도 동일하게 검증 가능하다 (U03~U04에서 실제 프론트/백엔드가 이 방식을 쓰게 됨).
