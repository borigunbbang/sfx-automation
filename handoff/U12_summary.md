# U12 요약 — 보안·운영 체크리스트 최종 점검 (+ 실제 배포)

> 원래 범위는 TECH_SPEC.md 10번 체크리스트 6~8번 점검(문서 작업)이었지만, 진행하면서
> "혼자 쓰더라도 실제로 배포까지 해보자"는 결정이 나와서 Render/Vercel 실배포와 그 과정에서
> 드러난 아키텍처 문제(효과음 라이브러리 로컬 의존)까지 이번 Unit에서 함께 처리했다.

## 1. 완료한 것

### 배포
- **프론트엔드**: Vercel — `https://sfx-automation.vercel.app` (Root Directory `frontend`, Vite 자동 인식)
- **백엔드 API**: Render — `https://autosfx-backend.onrender.com` (Free 웹서비스, [render.yaml](../render.yaml) Blueprint로 배포)
- **워커(worker.py)**: 배포하지 않고 이 컴퓨터에서 계속 실행 — 이유는 아래 "효과음 라이브러리" 참고. 실사용 시 이 컴퓨터가 켜져 있고 워커가 돌고 있어야 업로드된 영상이 처리된다.
- CORS(`CORS_ALLOW_ORIGINS`)와 Supabase Auth의 Site URL/Redirect URLs를 실제 Vercel 주소로 맞춤

### 효과음 라이브러리를 비공개 Supabase Storage로 이전 (배포를 위해 반드시 필요했던 작업)
- 배포 전 백엔드(`main.py`)의 `/events/{id}/sfx-audio`, 효과음 교체(PATCH) 검증 로직이 `eff sample/` **로컬 폴더**를 직접 읽고 있어서, Render처럼 이 컴퓨터가 아닌 곳에 배포하면 미리듣기/효과음 교체 기능이 깨지는 걸 발견함(U09~U11부터 남아있던 미해결 이슈)
- **사용자 확인: 이 앱은 혼자만 쓸 예정**이라 제3자 노출 문제는 없지만, 기능 자체가 깨지는 건 고쳐야 해서 아래처럼 처리:
  - [backend/scripts/sync_sfx_library.py](../backend/scripts/sync_sfx_library.py): `eff sample/`을 **비공개**(`public: false`) Storage 버킷 `sfx-library`로 동기화하는 스크립트. Storage 키가 공백/한글을 허용하지 않아서(`InvalidKey`) ASCII 슬러그(`iam-01.wav` 등)로 업로드하고, 원본 파일명 매핑은 같은 버킷의 `_manifest.json`에 저장
  - [app/supabase_rest.py](../backend/app/supabase_rest.py): `list_sfx_filenames()`/`fetch_sfx_object()` 추가 — `service_role` 키로만 접근(사용자별 데이터가 아니라 앱 공유 자산이라 RLS 대상이 아님)
  - [app/main.py](../backend/app/main.py): `_resolve_sfx_filename()`과 `/events/{id}/sfx-audio`가 로컬 디스크 대신 위 함수를 사용하도록 변경. 응답에 `Cache-Control: no-store` 추가(교체 직후 미리듣기가 브라우저 캐시 때문에 이전 파일을 재생하던 버그를 로컬 테스트 중 발견해서 같이 고침)
  - `worker.py`: `matched_sfx_path`에 이 컴퓨터에서만 의미 있는 로컬 절대경로 대신 **원본 파일명만** 저장
  - **macOS 유니코드 버그**: macOS(APFS)의 `os.listdir()`이 한글 파일명을 NFD(자모 분리)로 돌려주는데 브라우저/JS는 NFC(완성형)를 쓴다 — 그대로 두면 효과음 교체 시 "파일을 찾을 수 없음"으로 실패함. 매니페스트 생성/조회/저장 세 곳 모두 `unicodedata.normalize("NFC", ...)`로 통일해서 해결 (로컬 테스트 중 직접 재현하고 확인함)
- 새 환경변수: `SUPABASE_SFX_BUCKET`(기본값 `sfx-library`), `SUPABASE_SERVICE_ROLE_KEY`를 FastAPI 앱도 사용하게 됨(이전엔 워커 전용이었음) — `backend/.env.example`, `render.yaml`에 반영

### 워커 안정성 수정
- 실제 배포 테스트 중 발견: project 하나가 처리 실패하면(예: 손상된 영상) `status`는 `failed`로 잘 기록되지만 **워커 프로세스 전체가 죽어서** 이후 다른 pending project를 영영 못 받는 문제가 있었음
- `worker.py`의 메인 루프에서 프로젝트 단위 예외를 잡아서 로그만 남기고 폴링을 계속하도록 수정

### TECH_SPEC.md 10번 체크리스트 6~8번 점검 결과

| # | 항목 | 결과 |
|---|---|---|
| 6 | 도메인·HTTPS | Vercel/Render 기본 제공 서브도메인 사용(커스텀 도메인 구매는 안 함 — 혼자 쓰는 용도라 불필요 판단). 둘 다 HTTPS 기본 강제됨. Supabase Auth Site URL/Redirect URLs를 실제 배포 주소로 맞춤. **완료** |
| 7 | 운영 기본기 | - 로그: Render 대시보드(Logs 탭)와 Vercel 대시보드에서 확인 가능, 별도 외부 모니터링 툴은 연결 안 함(혼자 쓰는 규모엔 과함)<br>- 백업: **Supabase 무료 플랜은 자동 백업이 전혀 없음**(Pro부터 지원). 지금은 감수하고 진행 — 데이터가 중요해지면 Pro 전환 또는 수동 `pg_dump` 필요<br>- 개인정보 삭제: 실사용자가 본인 1명뿐이라 별도 회원탈퇴 기능은 만들지 않음. 필요 시 Supabase 대시보드에서 계정/Storage 파일을 수동 삭제하는 것으로 결정 |
| 8 | 무료 티어 한계 | 아래 "무료 티어 한계 정리" 참고. **특히 Supabase Storage 파일당 50MB 제한을 실제로 부딪혀서 확인함** (아래 참고) |

#### 무료 티어 한계 정리 (실제 조사 + 실측)
- **Supabase Free**: DB 500MB, Storage 1GB, **파일 하나당 업로드 최대 50MB(하드캡, 대시보드에서도 못 올림 — Pro부터 가능)**, 7일 미사용 시 프로젝트 일시정지(재개 ~30초)
- **Render Free**: 15분 무요청 시 슬립, 재요청 시 콜드스타트 30~60초, 워크스페이스당 월 750 인스턴스 시간
- **Vercel Free(Hobby)**: 월 100GB 대역폭(초과 시 다음 주기까지 정지), 비상업적 용도로만 허용

## 2. 완료 기준 테스트 결과

- **배포된 두 서비스 모두 HTTPS로 정상 응답**: `curl https://autosfx-backend.onrender.com/` → 200, `https://sfx-automation.vercel.app` 접속 시 로그인 화면 정상 렌더링
- **CORS**: `OPTIONS /me`, `OPTIONS /projects/upload`에 대한 preflight가 Vercel 주소를 `Access-Control-Allow-Origin`으로 정확히 반환
- **인증**: 실제 배포 사이트에서 로그인 성공, 토큰 없이 `/events/{id}/sfx-audio` 호출 시 401
- **효과음 라이브러리 Storage 이전 검증**: 직접 API 호출로 효과음 교체(PATCH) → 미리듣기(GET sfx-audio) → 정확히 바뀐 파일(바이트 수 일치)이 반환됨을 확인. 한글 파일명 정상 인식 확인
- **실사용 시나리오 풀 테스트 (가장 중요)**: 원본 샘플 영상에서 40초짜리 클립(30MB)을 잘라 **실제 배포된 Vercel/Render 조합**에 업로드 → 로컬 워커가 프로덕션 Supabase를 폴링해서 처리(`status: pending → done`) → 이벤트 5건 감지, `caption_style_01` 1건이 `iam 컷인 01.wav`에 정상 매칭 → CSV export에 한글 파일명 정확히 반영 → 미리듣기 스트리밍 정상(1,373,190 bytes, 원본과 일치) 확인. 테스트에 쓴 project/영상은 종료 후 삭제해서 정리함
- **300MB 영상 업로드 실패 재현 및 원인 규명**: 실제 원본 영상(299MB) 업로드 시도 → 브라우저에서 "Failed to fetch". 150MB 더미로 재현하니 Supabase가 `413 Payload too large`로 명확히 응답 → Storage 무료 플랜 50MB 상한이 원인임을 확정
- **워커 안정성 수정 확인**: 의도적으로 깨진 더미 "영상"을 업로드해서 워커가 실패 처리(`status: failed`) 후에도 죽지 않고 이후 정상 프로젝트를 이어서 처리하는지 확인(코드 수정 전 실제로 죽는 것도 먼저 재현함)

## 3. 다음 세션이 알아야 할 것

- **실사용 절차**: 영상을 처리하려면 (1) 이 컴퓨터에서 `backend/.venv/bin/python worker.py`가 돌고 있어야 하고, (2) 업로드할 영상은 **50MB 이하로 미리 잘라서** 올려야 한다(예: `imageio_ffmpeg` 번들 바이너리로 구간 추출, U11/U12에서 쓴 방식 재사용 가능)
- 효과음 라이브러리(`eff sample/`)에 파일을 추가/변경하면 `backend/.venv/bin/python backend/scripts/sync_sfx_library.py`를 다시 실행해서 Storage에 동기화해야 한다
- Render 무료 웹서비스는 15분 미사용 시 슬립 상태가 된다 — 오랜만에 접속하면 첫 요청이 30~60초 걸릴 수 있음(정상 동작이니 당황하지 않아도 됨)
- Render 서비스 환경변수: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_AUD`, `SUPABASE_VIDEOS_BUCKET`, `SUPABASE_SFX_BUCKET`, `CORS_ALLOW_ORIGINS`가 Render 대시보드에 설정되어 있음
- Vercel 프로젝트 환경변수(`VITE_API_BASE_URL` 등)는 Config 타입으로 저장됨 — Secret 타입으로 저장하면 나중에 Config로 못 바꾸니(Vercel 제약) 이후 `VITE_` 접두사 변수는 처음부터 Config로 추가할 것
- 로그인 비밀번호를 잊어버렸을 때: 이 프로젝트엔 아직 "비밀번호 찾기" UI가 없음. `SUPABASE_SERVICE_ROLE_KEY`로 Admin API(`PUT /auth/v1/admin/users/{id}`)를 이용해 재설정 가능(이번 세션에서 실제로 이렇게 처리함)

## 4. 미해결/보류 이슈

- **Supabase 무료 플랜 자동 백업 없음** — 데이터가 중요해지면 Pro 플랜 전환 또는 수동 백업 스크립트 필요
- **영상 50MB 제한이 여전히 남아있음** — 사용자가 "일단 클립을 잘라서 올리는 방식 유지"를 선택함(옵션 2). 나중에 불편하면: (a) Supabase Pro 결제, 또는 (b) 혼자 쓰는 도구인 점을 살려 브라우저 업로드 단계 자체를 없애고 로컬 파일 경로를 직접 처리하는 구조로 되돌리는 방안을 재검토
- U09~U11부터 이어진 이슈: signed URL 자동 갱신 없음, project 이력 목록 없음(새로고침하면 진행 중이던 project를 잃음), 동시에 여러 이벤트 보정 불가 — 전부 그대로 유지
- `EventUpdate.start_ms`/`end_ms` 프론트 UI 없음(U11부터 유지) — 백엔드는 지원하지만 화면에 시간 보정 입력이 없음
