# U04 요약 — 프론트엔드 로그인/회원가입 화면

## 1. 완료한 것

- `frontend/` React + Vite 프로젝트 생성 (`npm create vite@latest frontend -- --template react`), `@supabase/supabase-js` 설치
- [`frontend/src/supabaseClient.js`](../frontend/src/supabaseClient.js) — Supabase JS 클라이언트 초기화 (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`)
- [`frontend/src/AuthForm.jsx`](../frontend/src/AuthForm.jsx) — 가입/로그인 폼 (모드 토글). U02 비밀번호 정책(8자 이상 + 대/소문자+숫자) 안내 문구 포함
- [`frontend/src/MePanel.jsx`](../frontend/src/MePanel.jsx) — 로그인 성공 후 U03의 `GET /me`를 호출해서 응답을 화면에 표시, 로그아웃 버튼
- [`frontend/src/api.js`](../frontend/src/api.js) — 백엔드 호출 헬퍼 (`VITE_API_BASE_URL`)
- [`frontend/src/App.jsx`](../frontend/src/App.jsx) — `supabase.auth.getSession()` / `onAuthStateChange`로 세션 관리, 세션 유무에 따라 `AuthForm` ↔ `MePanel` 전환
- `frontend/.env` / `.env.example` — `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`
- `frontend/.gitignore`에 `.env`/`.env.*` 추가 (Vite 기본 템플릿에는 빠져있었음)
- **백엔드 수정 (U03 코드)**: [`backend/app/main.py`](../backend/app/main.py)에 `CORSMiddleware` 추가 — 브라우저 fetch가 `Failed to fetch`로 막히던 문제 해결. 허용 origin은 `CORS_ALLOW_ORIGINS` 환경변수(기본값 `http://localhost:5173`)

## 2. 완료 기준 테스트 결과

브라우저(자동화)로 실제 흐름을 끝까지 확인:

1. `http://localhost:5173`에서 "회원가입" 모드로 전환 → `dpfla0130@gmail.com` / 비밀번호로 가입 제출 → "가입 요청 완료. 확인 이메일 링크를 클릭한 뒤 로그인해주세요" 메시지 확인
2. 실제 수신한 Supabase 확인 이메일의 링크를 클릭 (사용자가 직접 확인)
3. 로그인 폼에서 로그인 제출 → 처음엔 CORS 미설정으로 `/me` 호출이 `Failed to fetch`로 실패 → CORS 미들웨어 추가 후 재시도
4. 로그인 성공 + `/me` 응답이 화면에 정상 표시됨:
   ```json
   {
     "id": "a59df9c8-f6c9-4c24-a2a0-332d9cd78abc",
     "email": "dpfla0130@gmail.com",
     "role": "authenticated"
   }
   ```
   → **U04 완료 기준 통과.**

## 3. 다음 Unit(U05~)이 알아야 할 것

- 프론트 프로젝트 경로: `frontend/` (실행: `npm run dev`, 기본 포트 `5173`)
- 환경변수(`.env`, gitignore됨): `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL=http://127.0.0.1:8000`
- 백엔드(U03)도 함께 실행해야 `/me` 확인 가능: `cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000`
- **백엔드에 `CORS_ALLOW_ORIGINS` 환경변수 추가됨** — 배포 시 실제 프론트 도메인을 이 값에 추가해야 함 (현재 기본값은 로컬 개발용 `http://localhost:5173`만 허용)
- 로그인 세션은 Supabase JS SDK가 브라우저 `localStorage`에 자동 저장/갱신 (별도 구현 불필요)
- 실제 가입 테스트로 생성된 계정: `dpfla0130@gmail.com` (사용자 본인 이메일 — 이후 필요 없으면 Supabase 대시보드에서 삭제 가능)

## 4. 미해결/보류 이슈

- 회원가입 폼에 클라이언트 측 비밀번호 정책 실시간 검증(정규식 체크)은 아직 없음 — `minLength=8`만 걸려있고, 실제 정책 위반은 Supabase 서버 응답 메시지에 의존
- CAPTCHA(hCaptcha/Turnstile) 미연동 — U02에서 U04 시점에 연동하기로 했으나 이번 세션에서는 보류 (필요 시 별도 Unit 또는 U12에서 처리)
- 배포 환경 CORS origin 아직 미설정 (로컬만 확인됨)
