# U11 요약 — 보정 저장 API + 최종 CSV 재생성

## 1. 완료한 것

### 백엔드
- [`backend/app/supabase_rest.py`](../backend/app/supabase_rest.py)에 `update_rows`(PostgREST PATCH)와 `delete_rows`(PostgREST DELETE) 추가 — 기존 `fetch_rows`/`insert_row`와 동일하게 사용자 JWT를 그대로 forward해서 RLS가 적용된다. `events` 테이블의 update/delete RLS 정책(U01에서 이미 만들어둠, project 소유자 확인)이 이번에 처음 실사용됨.
- [`backend/app/main.py`](../backend/app/main.py)에 엔드포인트 3개 추가:
  - `POST /projects/{id}/events` — 이벤트 수동 추가 저장 (U10의 "로컬 임시 이벤트"를 즉시 서버에 만드는 방식으로 설계 변경, 아래 3번 참고)
  - `PATCH /projects/{id}/events/{event_id}` — 부분 갱신. body는 `effect_type`/`start_ms`/`end_ms`/`sfx_filename` 중 있는 필드만 반영(`EventUpdate` 모델, 없는 필드는 None → 미변경)
  - `DELETE /projects/{id}/events/{event_id}` — 삭제
  - 셋 다 먼저 `_get_owned_project`로 project 소유 확인(404 통일) 후, PATCH/DELETE는 응답이 빈 리스트면(=RLS가 조용히 걸러낸 경우) 404로 변환
  - `sfx_filename`은 파일명만 받고(`iam 컷인 07.wav`), 서버가 `_resolve_sfx_filename()`으로 `eff sample/` 라이브러리 안의 실제 절대 경로로 바꿔 `matched_sfx_path`에 저장 — 파일이 없으면 404. 빈 문자열이면 매칭 해제(`null`)
  - `_SFX_LIBRARY_DIR` 상수를 파일 상단으로 옮겨서(U09에서는 하단에 있었음) 새 헬퍼 함수와 기존 `/events/{id}/sfx-audio`가 공유

### 프론트엔드
- [`frontend/src/api.js`](../frontend/src/api.js)에 `updateProjectEvent`/`createProjectEvent`/`deleteProjectEvent` 추가
- [`frontend/src/ResultView.jsx`](../frontend/src/ResultView.jsx): U10에서 mock(로컬 state)만 호출하던 4개 핸들러를 전부 실제 API 호출로 교체
  - **설계 변경**: U10의 "로컬에서 `local-*` id로 임시 이벤트를 만들고 나중에 서버 id로 교체" 방식 대신, **이벤트 추가 시 바로 `POST`해서 서버가 만든 실제 id를 받아오는 방식**으로 단순화함 (더 이상 `local-` 접두사 구분이 필요 없어짐)
  - 각 핸들러는 API 성공 시 서버가 돌려준 최신 행으로 `events` state를 갱신, 실패 시 화면은 그대로 두고 에러 메시지만 표시 (낙관적 업데이트 아님 — 저장 실패가 화면에 반영되는 걸 막기 위함)
  - `savingAction` state 추가 — API 호출 중 보정 버튼들을 비활성화(중복 클릭 방지)
  - `handlePreview`: U10에서 붙였던 `filename` 쿼리 파라미터 제거 — 이제 `matched_sfx_path`가 실제로 DB에 저장되므로 파라미터 없이 호출해도 최신 교체 결과가 그대로 재생됨
- [`frontend/src/CorrectionPanel.jsx`](../frontend/src/CorrectionPanel.jsx): `saving` prop을 받아 변경/교체/삭제 버튼을 저장 중에 비활성화

### 기타
- **CSV 재생성 로직은 별도로 구현하지 않음** — U07의 `GET /projects/{id}/export.csv`가 애초에 매 요청마다 `events` 테이블을 다시 조회해서 CSV를 만드는 구조라서, 보정 내용이 DB에 저장되기만 하면 자동으로 최신 CSV가 나온다 (TECH_SPEC 4.6 "출력 생성" 요구사항이 기존 엔드포인트만으로 이미 충족됨)

## 2. 완료 기준 테스트 결과

로컬에서 백엔드(`uvicorn`)/워커(`worker.py`)/프론트(`vite`)를 모두 띄우고, 참고 이미지 원본 영상(`references.yaml`의 `source_video`)에서 `caption_style_01` 이벤트가 포함된 40초 클립을 잘라(ffmpeg, imageio-ffmpeg 번들 바이너리 사용) 실제 업로드 → 처리 완료 → 브라우저(dpfla0130@gmail.com 세션)에서 확인:

1. **타입 변경**: `caption_style_01` → `slide`로 변경 → `PATCH .../events/{id}` 200 OK, 마커 툴팁 즉시 반영
2. **효과음 교체**: `iam 컷인 01.wav` → `iam 컷인 07.wav`로 교체 → `PATCH` 200 OK. **미리듣기**를 filename 파라미터 없이 호출 → 실제로 07번 파일(길이 4.0s, 01번은 4.77s)이 재생됨 → DB에 실제로 저장됐다는 뜻
3. **이벤트 추가**: 2.00s~3.00s 이벤트 추가 → `POST .../events` 200 OK, 서버가 만든 실제 id로 즉시 화면에 반영
4. **이벤트 삭제**: 방금 추가한 이벤트 삭제 → `DELETE .../events/{id}` 200 OK, 화면에서 사라짐
5. **영속성 확인(재부팅급 검증)**: 페이지를 새로고침한 뒤(= 컴포넌트 state 완전히 날아간 상태) 브라우저 콘솔에서 저장된 Supabase 세션 토큰으로 직접 `GET /projects/{id}/events` 호출 → `slide`/`iam 컷인 07.wav`가 그대로 남아있고, 추가했다 삭제한 이벤트는 없음(원래 5건) 확인
6. **CSV 재생성 확인**: `GET /projects/{id}/export.csv` 응답에 `10.98,11.14,slide,iam 컷인 07.wav` 행이 정확히 포함됨 확인
7. **보안**: 토큰 없이 `PATCH .../events/{id}` 호출 시 401 확인

→ **U11 완료 기준 통과** (보정 내용이 실제로 저장되고, CSV에 반영됨을 직접 확인)

## 3. 다음 Unit(U12)이 알아야 할 것

- U11로 Phase A~D(TECH_SPEC M4~M7)가 전부 끝남. **U12는 TECH_SPEC.md 10번 체크리스트 6~8번(도메인/HTTPS, 백업·모니터링, 무료 티어 한계)만 점검하면 되는 "출시 가능" 게이트** — 코드 작업보다는 설정/운영 점검 위주
- 로컬 테스트에 쓴 launch 설정: `/Users/mac/Documents/afeel/.claude/launch.json`(Browser 프리뷰용, `npm --prefix` 방식은 이 환경 샌드박스에서 `EPERM: process.cwd` 오류가 나서 실패 — 대신 프론트를 Bash로 직접 띄운 뒤 `url: "http://localhost:5173"`로 "이미 떠 있는 서버에 attach" 방식을 씀). 백엔드는 `backend/.venv/bin/uvicorn app.main:app --port 8000`, 워커는 `backend/.venv/bin/python worker.py`로 각각 Bash 백그라운드 실행
- 테스트용 클립은 `eff sample`/`references.yaml`이 참조하는 원본 영상(`/Users/mac/Downloads/효과 사이트 구축용 샘플 영상.mp4`)에서 205~245초 구간을 잘라 만듦 (`caption_style_01` 이벤트가 216초 부근에 있어서 이 구간에 포함됨) — 원본 영상이 1.3GB라 매번 통째로 올리기엔 느려서, 필요하면 이 방식(ffmpeg로 짧은 구간만 추출)을 재사용하면 됨. ffmpeg CLI가 시스템에 없어서 `backend/.venv/lib/python3.9/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-x86_64-v7.1` 번들 바이너리를 직접 실행함
- 테스트에 쓴 project(`b8c87cfc-228d-4cf4-835e-10dd2739de26`)는 Supabase에 실제로 남아있음 — 정리가 필요하면 대시보드에서 삭제(또는 그대로 둬도 RLS로 본인 계정에서만 보임)

## 4. 미해결/보류 이슈

- `EventUpdate.start_ms`/`end_ms` 갱신 API는 만들어뒀지만 프론트 UI에서 시간 자체를 보정하는 입력은 아직 없음(현재 UI는 타입/효과음/삭제/수동추가만 노출) — 필요하면 이후에 UI만 추가하면 됨(백엔드는 이미 지원)
- U09/U10부터 이어진 이슈 그대로 유지: SFX 라이브러리가 여전히 로컬 파일 기반(백엔드/워커 분리 배포 시 깨짐), signed URL 자동 갱신 없음, project 이력 목록 없음(새로고침하면 진행 중이던 project를 잃음 — 이번 U11 테스트에서도 이 때문에 재조회를 API 직접 호출로 우회함)
- 동시에 여러 이벤트를 보정할 수 없음(한 번에 하나씩)은 여전함
