# U10 요약 — 보정 UI

## 1. 완료한 것

- [`frontend/src/CorrectionPanel.jsx`](../frontend/src/CorrectionPanel.jsx) — 선택된 이벤트 하나에 대한 보정 UI: 효과 타입 변경, 효과음 파일명 교체, 미리듣기, 이벤트 삭제
- [`frontend/src/ResultView.jsx`](../frontend/src/ResultView.jsx)에 보정 동작 4가지를 mock(로컬 state)으로 구현:
  - **타입 변경**: `events` 배열에서 해당 행의 `effect_type`만 갱신 → 타임라인 마커 색/툴팁에 즉시 반영
  - **효과음 교체**: `matched_sfx_path`를 `eff sample/{입력한 파일명}` 형태로 갱신 (표시용 mock 값)
  - **이벤트 삭제**: `events` 배열에서 필터링 제거, 선택 해제
  - **이벤트 수동 추가**: 시작/종료(초) 입력 폼 → `id: local-{uuid}`인 임시 이벤트를 생성해 배열에 삽입(시간순 정렬), 자동 선택
  - `selectedEvent`는 매번 `events` 배열에서 id로 다시 찾도록 리팩터링(이전엔 클릭 시점의 복사본을 들고 있어서 보정이 화면에 즉시 반영 안 되는 버그가 있었음)
- **모든 보정은 서버에 저장되지 않음** (TASK_BREAKDOWN의 mock 전략 그대로) — 새로고침하면 사라짐. 실제 저장은 U11에서 `PATCH /projects/{id}/events/{event_id}`로 구현 예정
- **부가 개선 (교체 → 미리듣기 연동)**: 효과음을 mock으로 교체한 뒤 "미리듣기"를 눌러도 실제로는 서버 DB에 저장된 원래 파일이 재생되는 문제를 발견 → `GET /events/{id}/sfx-audio`에 `filename` 쿼리 파라미터를 추가해서, 로컬 SFX 라이브러리(`eff sample/`)에서 그 파일명을 직접 찾아 재생하도록 확장 (event 소유권 확인은 그대로 유지). 프론트는 항상 `matched_sfx_path`의 파일명을 이 파라미터로 넘기도록 통일

## 2. 완료 기준 테스트 결과

U06/U08/U09와 동일한 방식으로 실제 업로드 → 처리 완료 후, 브라우저에서 4가지 조작을 순서대로 확인:

1. **타입 변경**: `caption_style_01` → `slide`로 변경 → 마커 툴팁이 즉시 `"20.99s - slide"`로 바뀜
2. **효과음 교체 + 미리듣기**: `iam 컷인 01.wav` → `iam 컷인 07.wav`로 교체 후 미리듣기 클릭 → 네트워크 요청이 `?filename=iam 컷인 07.wav`로 나가고, 실제로 다른 파일(재생 길이 4.0s, 원래 파일은 4.77s)이 재생됨을 확인
3. **이벤트 추가**: 시작 5초/종료 6초 입력 후 추가 → 마커 목록에 `"5.00s - unknown"`이 시간순으로 정확히 삽입되고 자동 선택됨
4. **이벤트 삭제**: 방금 추가한 이벤트 삭제 → 마커 목록에서 사라짐, 원래 4개만 남음
   → **U10 완료 기준 통과** (mock 데이터 기준, 4가지 조작 모두 화면에 정상 반영)

## 3. 다음 Unit(U11)이 알아야 할 것

- U11(보정 저장 API)이 구현해야 할 프론트 쪽 훅 포인트: `ResultView.jsx`의 `handleChangeType`/`handleReplaceSfx`/`handleDeleteEvent`/`handleAddEvent` — 지금은 전부 `setEvents`(로컬)만 호출하므로, 각 핸들러 안에 `PATCH /projects/{id}/events/{event_id}`(또는 삭제/생성용 엔드포인트) 호출을 추가하면 됨
- 로컬로 추가된 이벤트는 `id`가 `local-` 접두사를 가진 임시 UUID임 — U11에서 저장 API를 만들 때 이 접두사로 "아직 서버에 없는 새 이벤트"를 구분해서 POST(생성)로 보내고, 그 외는 PATCH(수정)로 보내면 됨
- `GET /events/{id}/sfx-audio`의 `filename` 파라미터는 U10에서 미리듣기 임시방편으로 추가한 것 — U11에서 실제로 `matched_sfx_path`를 서버에 저장하게 되면, 저장된 값을 그대로 신뢰해도 되므로 이 파라미터는 (호환을 위해 유지하되) 필수는 아니게 됨

## 4. 미해결/보류 이슈

- 효과음 교체 시 입력한 파일명이 실제 `eff sample/` 폴더에 존재하는지 프론트에서 검증하지 않음 — 존재하지 않는 파일명을 입력하고 미리듣기하면 404 (자연스러운 실패, 크래시는 아님)
- 미분류(`unknown`) 이벤트의 "대표 프레임을 새 참고 이미지로 등록" 기능(TECH_SPEC 4.5)은 이번 Unit에서 구현하지 않음 — 참고 이미지 등록 시스템 자체가 아직 없음(U06 이슈)
- 여러 이벤트를 동시에 보정할 수 없음 (한 번에 하나씩만 선택/수정)
