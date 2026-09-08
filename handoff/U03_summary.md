# U03 요약 — FastAPI 스캐폴딩 + JWT 인증 미들웨어

## 1. 완료한 것

- `backend/` FastAPI 프로젝트 생성
  - [`backend/app/main.py`](../backend/app/main.py) — 앱 엔트리포인트. `GET /`(헬스체크, 인증 불필요), `GET /me`(인증 필요)
  - [`backend/app/auth.py`](../backend/app/auth.py) — JWT 검증 dependency (`get_current_user`)
  - `backend/requirements.txt` — `fastapi`, `uvicorn[standard]`, `PyJWT[crypto]`, `python-dotenv`
  - `backend/.env.example` — 필요한 환경변수 목록 (실제 `.env`는 gitignore 처리됨, 최상위 `.gitignore`의 `.env`/`.env.*` 규칙이 하위 폴더에도 적용됨을 확인)
  - `backend/.venv` — Python 3.9 가상환경 (시스템에 3.9만 설치되어 있음)
- **인증 방식 — 중요한 변경점**: 이 Supabase 프로젝트는 JWKS(`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`)를 확인해보니 **비대칭(ES256) 서명 키**를 사용 중이었다. 따라서 U01 인계 파일에서 "U03에서 `service_role` 키를 `.env`에 저장 예정"이라고 했던 계획은 불필요해졌다 — `service_role` 키 없이 Supabase의 공개 JWKS만으로 토큰 서명 검증이 가능하다 (`PyJWT`의 `PyJWKClient` 사용).
  - 검증 조건: `algorithms=["ES256","RS256"]`, `audience="authenticated"`, `issuer="{SUPABASE_URL}/auth/v1"`
  - `/me`는 DB 조회 없이 토큰 claim(`sub`, `email`, `role`)만 그대로 반환하는 더미 엔드포인트

## 2. 완료 기준 테스트 결과

서버 실행: `cd backend && .venv/bin/uvicorn app.main:app --port 8000`

1. 토큰 없이 호출:
   ```
   GET /me → 401
   {"detail":"Authorization: Bearer <token> 헤더가 필요합니다."}
   ```
2. 잘못된(형식이 아닌) 토큰:
   ```
   GET /me (Authorization: Bearer not-a-real-token) → 401
   {"detail":"유효하지 않은 토큰입니다: Not enough segments"}
   ```
3. 유효한 Supabase 토큰으로 호출:
   - Supabase Auth 대시보드에서 **U03 인증 테스트 전용 계정**을 새로 생성 (`u03-test@gmail.com`, Auto Confirm) — 기존 test1/test2는 비밀번호를 알 수 없어 로그인 실패, 새 계정으로 대체
   - `POST {SUPABASE_URL}/auth/v1/token?grant_type=password`로 로그인해서 `access_token` 발급받음
   - ```
     GET /me (Authorization: Bearer <access_token>) → 200
     {"id":"76d2ace1-14f4-4842-85ab-303b296a7969","email":"u03-test@gmail.com","role":"authenticated"}
     ```
   → **U03 완료 기준(401/200) 모두 통과.**

## 3. 다음 Unit(U04, U05)이 알아야 할 것

- FastAPI 프로젝트 경로: `backend/` (venv: `backend/.venv`, 실행: `.venv/bin/uvicorn app.main:app --reload --port 8000`)
- 환경변수(`.env`, gitignore됨): `SUPABASE_URL`, `SUPABASE_JWT_AUD`(기본값 `authenticated`) — 둘 다 비밀 아님, `service_role` 키는 이 방식에서는 필요 없음
- 인증 필요한 엔드포인트는 `Depends(get_current_user)`를 붙이면 됨 (`app/auth.py`에서 import). 반환값은 Supabase JWT claim dict (`sub`=user id, `email`, `role` 등)
- 프론트엔드(U04)는 Supabase Auth JS SDK로 로그인 후 받은 `session.access_token`을 `Authorization: Bearer <token>` 헤더로 그대로 백엔드에 보내면 됨
- **U03 테스트 전용 계정**: `u03-test@gmail.com` (비밀번호는 이 문서에 기록하지 않음 — U01/U02와 동일한 방침, 필요시 대시보드에서 재설정)
- 기존 `test1@example.com`/`test2@example.com`의 비밀번호는 분실된 상태로 보임 — 필요 시 대시보드에서 재설정 필요

## 4. 미해결/보류 이슈

- `test1@example.com`/`test2@example.com` 비밀번호 분실 (재설정 안 함, U03 테스트는 새 계정으로 대체 진행)
- CORS 설정 아직 없음 — U04(프론트엔드 연결) 시점에 프론트 origin 허용 설정 필요
- 배포(Render/Fly.io) 설정 아직 없음 — 로컬 실행만 확인됨
