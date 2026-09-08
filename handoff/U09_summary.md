# U09 요약 — 결과 확인 화면

## 1. 완료한 것

- [`frontend/src/ResultView.jsx`](../frontend/src/ResultView.jsx) — project가 `done`이 되면 표시되는 결과 화면:
  - `supabase.storage.from(bucket).createSignedUrl(...)`로 U05가 저장한 영상의 signed URL을 발급받아 `<video>` 태그로 재생 (백엔드 새 엔드포인트 없이, 프론트가 이미 가진 사용자 세션의 RLS 권한으로 직접 서명 — Storage `select` 정책이 이미 있어서 별도 작업 불필요)
  - `GET /projects/{id}/events`(U07)로 받은 이벤트를 영상 길이 대비 비율로 타임라인에 마커로 표시
  - 마커 클릭 → 해당 시점으로 영상 탐색(seek) + 상세 정보 패널(시작/끝 시각, 효과 타입, 매칭된 효과음 파일명) 표시
  - CSV 다운로드 버튼 — U07의 `/export.csv`는 인증 헤더가 필요해서 `<a href>` 직링크 대신 `fetch` → Blob → 임시 `<a>` 클릭으로 구현
- [`frontend/src/UploadPage.jsx`](../frontend/src/UploadPage.jsx) — `project.status === 'done'`이면 `ResultView` 렌더링하도록 연결 (U08과 자연스럽게 이어짐)
- `frontend/.env`(.example)에 `VITE_SUPABASE_VIDEOS_BUCKET=video` 추가 (signed URL 발급 시 버킷/경로 파싱에 필요)
- **오디오 미리듣기 (최초엔 생략했다가 사용자 요청으로 재추가)**:
  - [`backend/app/main.py`](../backend/app/main.py)에 `GET /events/{id}/sfx-audio` 간이 서빙 엔드포인트 추가 — `matched_sfx_path`(로컬 파일 경로, U06 이슈)를 인증된 사용자에게 스트리밍
  - 안전장치: 서빙 가능한 경로를 `sfx-automation/` 루트 하위로만 제한 (`os.path.realpath` + prefix 체크) — 임의 파일 읽기 방지
  - `events`는 `user_id`가 없고 `project`를 통해서만 소유자 확인이 되므로, 사용자 JWT로 조회해서 본인 프로젝트 소속이 아니면 자연히 404
  - 확장자별 media type 매핑(`.wav/.mp3/.m4a/.aiff`) — 로컬 SFX 라이브러리(`eff sample/`)와 동일
  - 프론트: `frontend/src/api.js`의 `fetchEventSfxAudioUrl()`이 인증된 `fetch` → Blob → object URL로 변환 (`<audio src>`는 커스텀 헤더를 못 보내서 직링크 불가)
  - `ResultView.jsx`: 선택된 이벤트에 `matched_sfx_path`가 있으면 "미리듣기" 버튼 활성화, 클릭 시 숨겨진 `<audio>` 엘리먼트에 로드해서 재생
  - **여전히 임시방편**: SFX 라이브러리 자체를 Storage로 옮기는 근본적인 작업은 아직 안 함 (아래 "미해결 이슈" 참고)

## 2. 완료 기준 테스트 결과

U06/U08과 동일한 방식(`DataTransfer`로 실제 mp4 주입)으로 캡션 클립을 다시 업로드해서 전체 플로우 확인:

1. 업로드 → 워커 처리 → `status: done` → `ResultView` 자동 표시
2. `<video>` 엘리먼트가 signed URL로 실제 로드됨 확인: `readyState: 4`(재생 가능), `duration: 35.03`(업로드한 클립 길이와 일치)
3. 타임라인에 이벤트 4개가 마커로 정확히 표시됨 (`20.99s`, `26.86s`, `29.09s`, `31.83s`)
4. 첫 번째 마커(`caption_style_01`) 클릭 → `video.currentTime`이 정확히 `20.987`로 이동, 상세 패널에 "매칭된 효과음: iam 컷인 01.wav" 표시
5. `GET /events/{id}/sfx-audio`: 토큰 없이 401, 인증된 요청 시 실제 WAV 파일(`content-type: audio/wav`, 1.37MB) 스트리밍 확인 (curl)
6. 화면에서 "미리듣기" 버튼 클릭 → `<audio>`가 blob URL로 실제 로드되고 끝까지 재생됨 확인 (`currentTime === duration === 4.77s`)
   → **U09 완료 기준 통과** (오디오 미리듣기 포함)

## 3. 다음 Unit(U10)이 알아야 할 것

- `ResultView`는 `project`, `session` props만 받음 — U10(보정 UI)에서 이 컴포넌트를 확장하거나 옆에 보정 패널을 추가하면 됨
- 이벤트 선택 상태(`selectedEvent`)가 이미 있어서, U10의 "타입 변경/효과음 교체/삭제" UI를 이 선택된 이벤트 기준으로 붙이기 좋음
- 오디오 미리듣기는 `GET /events/{id}/sfx-audio`(백엔드가 로컬 파일을 직접 스트리밍)로 동작 — **아직 워커/백엔드가 같은 서버(로컬 파일시스템 공유)에 있다는 전제**에 의존함. 나중에 백엔드/워커를 분리 배포하면 이 방식은 깨짐 → 그때는 SFX를 Storage로 옮기는 게 사실상 필수
- signed URL은 1시간(3600초) 유효 — 화면을 오래 열어두면 만료될 수 있음 (재발급 로직 없음, 필요시 새로고침으로 해결)

## 4. 미해결/보류 이슈

- **SFX 라이브러리가 여전히 로컬 파일 기반** — `/events/{id}/sfx-audio`는 배포 환경(백엔드/워커가 분리된 서버)에서는 동작 안 함. 실제 서비스 전에는 반드시 Storage 기반으로 전환 필요 (U06 이슈와 동일, 임시로 봉합만 함)
- signed URL 자동 갱신 없음 (만료 시 새로고침 필요)
- 타임라인이 단순 막대 마커라 겹치는 이벤트가 구분 안 될 수 있음 (이벤트가 조밀한 영상에서는 UX 개선 필요)
- 여러 project 이력 목록/전환 기능 없음 (U08 이슈와 동일 — 한 번에 하나의 project만 추적)
- 미리듣기 중 다른 마커를 눌러 새로 미리듣기하면 이전 재생은 멈추지 않고 겹쳐 재생될 수 있음 (같은 `<audio>` 엘리먼트라 src 교체 시 자동 정지되긴 하나, 명시적 pause 처리는 안 함)
