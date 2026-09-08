# U01 요약 — Supabase 프로젝트 생성 + DB 스키마/RLS

## 1. 완료한 것

- Supabase 프로젝트: `borigunbbang's Project` (Org: `borigunbbang's Org`, Region: AWS ap-northeast-2, Free plan)
  - Project URL: `https://imeujftiiqhbfzqvebnr.supabase.co`
  - anon(publishable) key: `sb_publishable_NG-kKbdUWgwoG0Lj8n5SIw_5FlCbpKo` (공개 노출 가능한 키, 프론트엔드용)
  - ⚠️ `service_role` 키는 아직 어디에도 기록/공유하지 않음 — U03에서 FastAPI `.env`에만 최초 저장 예정
- 스키마 SQL: [`supabase/migrations/0001_init_schema.sql`](../supabase/migrations/0001_init_schema.sql)
  - `public.projects` (`id, user_id, video_path, roi jsonb, status, created_at, updated_at`)
  - `public.reference_images` (`id, user_id, image_path, effect_type, sfx_folder, created_at`)
  - `public.events` (`id, project_id, start_ms, end_ms, representative_frame_path, effect_type, match_score, matched_sfx_path, created_at`) — `user_id` 없음, `project_id` → `projects.user_id`로 소유자 확인
  - 세 테이블 모두 RLS 활성화 + "본인 `user_id`(또는 `project_id` 경유) 행만 select/insert/update/delete" 정책 적용
- RLS 테스트 스크립트: [`supabase/rls_test.sql`](../supabase/rls_test.sql)
- `.gitignore`에 `.env`, `.env.*` 추가 (TECH_SPEC 체크리스트 1번 선반영)
- 대시보드에 테스트 계정 2개 생성 (Auto Confirm):
  - `test1@example.com` — UUID `1383948d-145f-49db-9c08-1c5c9a6451d0`
  - `test2@example.com` — UUID `be3ebb0b-8b5c-4434-9de2-6f1f65426fec`

## 2. 완료 기준 테스트 결과

1. `pg_class.relrowsecurity` 조회 → `projects`, `reference_images`, `events` 모두 `true` (RLS 켜짐) 확인
2. 각 테스트 유저 소유로 `projects` 행 생성 후, SQL Editor에서 `set_config('request.jwt.claims', ...)`로 유저를 가장(impersonate)해 조회
   - user1(`1383948d...`)로 조회 → user1 소유 행만 반환 (user2 행 안 보임)
   - user2(`be3ebb0b...`)로 조회 → user2 소유 행만 반환 (user1 행 안 보임)
   - → **서로의 데이터가 RLS로 정확히 차단됨을 확인. U01 완료 기준 통과.**

(테스트용 project 행 2~3건이 DB에 남아있음 — 다음 Unit에서 실제 데이터로 덮어써지거나, 필요시 수동 정리 가능. 삭제 필수는 아님.)

## 3. 다음 Unit(U02, U03)이 알아야 할 것

- Supabase Project URL: `https://imeujftiiqhbfzqvebnr.supabase.co`
- anon(publishable) key: `sb_publishable_NG-kKbdUWgwoG0Lj8n5SIw_5FlCbpKo`
- `service_role` 키: 아직 미보관 — U03 진행 시 대시보드 **Project Settings → API**에서 직접 발급받아 FastAPI `.env`에만 저장 (절대 커밋 금지, `.gitignore`에 이미 반영됨)
- 테이블/컬럼명은 위 1번 참고. `events`는 `user_id`가 없고 `project_id`를 통해서만 소유자 확인 가능 (백엔드 쿼리 작성 시 유의)
- 테스트 계정: `test1@example.com` / `test2@example.com` (비밀번호는 별도 안전한 채널로 전달 필요 — 이 문서에는 기록하지 않음)

## 4. 미해결/보류 이슈

- U02(Auth 보안 옵션: 이메일 확인, SMTP, 비밀번호 정책, CAPTCHA)는 아직 미착수
- 도메인/HTTPS(체크리스트 6번), 백업/모니터링(7번), 무료 티어 한계(8번)는 U12(출시 전 최종 점검)에서 다룰 예정
