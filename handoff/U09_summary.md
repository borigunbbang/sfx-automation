# U09 요약 — 결과 확인 화면

## 1. 완료한 것

- [`frontend/src/ResultView.jsx`](../frontend/src/ResultView.jsx) — project가 `done`이 되면 표시되는 결과 화면:
  - `supabase.storage.from(bucket).createSignedUrl(...)`로 U05가 저장한 영상의 signed URL을 발급받아 `<video>` 태그로 재생 (백엔드 새 엔드포인트 없이, 프론트가 이미 가진 사용자 세션의 RLS 권한으로 직접 서명 — Storage `select` 정책이 이미 있어서 별도 작업 불필요)
  - `GET /projects/{id}/events`(U07)로 받은 이벤트를 영상 길이 대비 비율로 타임라인에 마커로 표시
  - 마커 클릭 → 해당 시점으로 영상 탐색(seek) + 상세 정보 패널(시작/끝 시각, 효과 타입, 매칭된 효과음 파일명) 표시
  - CSV 다운로드 버튼 — U07의 `/export.csv`는 인증 헤더가 필요해서 `<a href>` 직링크 대신 `fetch` → Blob → 임시 `<a>` 클릭으로 구현
- [`frontend/src/UploadPage.jsx`](../frontend/src/UploadPage.jsx) — `project.status === 'done'`이면 `ResultView` 렌더링하도록 연결 (U08과 자연스럽게 이어짐)
- **오디오 미리듣기는 이번 Unit에서 의도적으로 생략** (사용자 결정) — `matched_sfx_path`가 아직 로컬 파일 경로라 브라우저가 접근 불가 (U06 이슈). "미리듣기 (준비 중)" 버튼을 비활성 상태로 배치해둠. SFX를 Storage로 옮기는 작업은 별도 Unit에서 진행 예정
- `frontend/.env`(.example)에 `VITE_SUPABASE_VIDEOS_BUCKET=video` 추가 (signed URL 발급 시 버킷/경로 파싱에 필요)

## 2. 완료 기준 테스트 결과

U06/U08과 동일한 방식(`DataTransfer`로 실제 mp4 주입)으로 캡션 클립을 다시 업로드해서 전체 플로우 확인:

1. 업로드 → 워커 처리 → `status: done` → `ResultView` 자동 표시
2. `<video>` 엘리먼트가 signed URL로 실제 로드됨 확인: `readyState: 4`(재생 가능), `duration: 35.03`(업로드한 클립 길이와 일치)
3. 타임라인에 이벤트 4개가 마커로 정확히 표시됨 (`20.99s`, `26.86s`, `29.09s`, `31.83s`)
4. 첫 번째 마커(`caption_style_01`) 클릭 → `video.currentTime`이 정확히 `20.987`로 이동, 상세 패널에 "매칭된 효과음: iam 컷인 01.wav" 표시
   → **U09 완료 기준 통과** (오디오 미리듣기 제외, 사용자와 합의된 범위)

## 3. 다음 Unit(U10)이 알아야 할 것

- `ResultView`는 `project`, `session` props만 받음 — U10(보정 UI)에서 이 컴포넌트를 확장하거나 옆에 보정 패널을 추가하면 됨
- 이벤트 선택 상태(`selectedEvent`)가 이미 있어서, U10의 "타입 변경/효과음 교체/삭제" UI를 이 선택된 이벤트 기준으로 붙이기 좋음
- **오디오 미리듣기 미구현 상태 유지** — U10에서 SFX를 Storage로 옮기는 작업을 먼저 하거나, 최소한 이 문제를 다시 검토해야 함
- signed URL은 1시간(3600초) 유효 — 화면을 오래 열어두면 만료될 수 있음 (재발급 로직 없음, 필요시 새로고침으로 해결)

## 4. 미해결/보류 이슈

- 오디오 미리듣기 없음 (위 참고)
- signed URL 자동 갱신 없음 (만료 시 새로고침 필요)
- 타임라인이 단순 막대 마커라 겹치는 이벤트가 구분 안 될 수 있음 (이벤트가 조밀한 영상에서는 UX 개선 필요)
- 여러 project 이력 목록/전환 기능 없음 (U08 이슈와 동일 — 한 번에 하나의 project만 추적)
