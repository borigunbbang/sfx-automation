# U01 — Supabase 프로젝트 생성 + DB 스키마 / RLS

참고: [TASK_BREAKDOWN.md](../TASK_BREAKDOWN.md) U01, [TECH_SPEC.md](../TECH_SPEC.md) 3.2 / 5 / 10(1, 5번)

## 1. Supabase 프로젝트 생성 (수동, 대시보드에서)

계정 생성/로그인은 본인이 직접 진행해야 합니다.

1. https://supabase.com 접속 → 로그인 (또는 가입)
2. "New Project" 클릭
   - Name: `sfx-automation` (또는 원하는 이름)
   - Database Password: 강력한 비밀번호 생성 후 **안전한 곳에 별도 보관** (이 저장소에 절대 커밋하지 않음)
   - Region: 사용자와 가까운 리전 (예: Northeast Asia - Seoul/Tokyo)
   - Plan: Free tier로 시작
3. 프로젝트 생성 완료까지 1~2분 대기
4. **Project Settings → API**에서 아래 두 값을 확인 (U03/U04에서 필요)
   - `Project URL`
   - `anon public` key (공개 키 — 프론트엔드에 노출되어도 됨)
   - ⚠️ `service_role` key는 **절대 프론트엔드나 이 저장소에 넣지 않는다** (TECH_SPEC 체크리스트 1번). FastAPI 서버 환경변수로만 사용 (U03에서 진행).

## 2. 스키마 + RLS 적용

1. Supabase 대시보드 → **SQL Editor** → New query
2. [`migrations/0001_init_schema.sql`](./migrations/0001_init_schema.sql) 전체 내용을 붙여넣고 Run
3. 왼쪽 **Table Editor**에서 `projects`, `reference_images`, `events` 3개 테이블이 생성됐고, 각 테이블에 RLS(자물쇠 아이콘)가 켜져 있는지 확인

생성되는 테이블 (TECH_SPEC.md 5번 데이터 모델과 대응):

| 테이블 | 소유자 컬럼 | 비고 |
|---|---|---|
| `projects` | `user_id` | `auth.users`가 이미 User 역할 (별도 users 테이블 없음) |
| `reference_images` | `user_id` | 참고 이미지 라이브러리 |
| `events` | (없음, `project_id`로 소유자 확인) | `projects`에 종속 |

## 3. RLS 동작 확인 (완료 기준)

1. 대시보드 → **Authentication → Users → Add user**로 테스트 계정 2개 생성
   - `test1@example.com` / 임시 비밀번호
   - `test2@example.com` / 임시 비밀번호
   - 각 유저의 UUID를 복사해둔다
2. [`rls_test.sql`](./rls_test.sql)의 `<USER1_UUID>`, `<USER2_UUID>`를 실제 UUID로 치환
3. SQL Editor에서 실행 → user1로 조회 시 user1의 project 1건만, user2로 조회 시 user2의 project 1건만 보이는지 확인
4. 통과하면 U01 완료. 테스트용 계정/행은 그대로 둬도 되고(다음 Unit에서 재사용 가능), 정리하고 싶으면 파일 하단 주석 참고

## 4. 다음 Unit(U02, U03)이 알아야 할 것

- 테이블명: `public.projects`, `public.reference_images`, `public.events`
- 소유자 판별: `projects.user_id` / `reference_images.user_id` = `auth.uid()`, `events`는 `project_id` → `projects.user_id` 경유
- `service_role` 키는 아직 어디에도 저장하지 않음 — U03에서 FastAPI `.env`에 최초 저장 예정 (`.env`는 이미 `.gitignore`에 있는지 U03에서 재확인)
- Project URL / anon key는 `handoff/U01_summary.md`에 기록 (anon key는 공개돼도 되는 키라 문제 없음)
