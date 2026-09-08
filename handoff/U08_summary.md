# U08 요약 — 업로드 화면

## 1. 완료한 것

- [`frontend/src/UploadPage.jsx`](../frontend/src/UploadPage.jsx) — 로그인 후 메인 화면. 파일 선택 + 업로드 버튼, 업로드 성공 후 3초 간격으로 `GET /projects/{id}`(U07)를 폴링해서 상태(`대기중/처리중/완료/실패`)를 화면에 반영. `status`가 `pending`/`processing`이 아니게 되면 폴링 자동 중단
- [`frontend/src/api.js`](../frontend/src/api.js) — `uploadProjectVideo()`(U05 호출), `fetchProject()`(U07 호출) 추가
- [`frontend/src/App.jsx`](../frontend/src/App.jsx) — 로그인 후 화면을 `MePanel`(U04, 디버그용) 대신 `UploadPage`로 교체
- `MePanel.jsx` 삭제 (U08의 UploadPage가 역할을 흡수, 더 이상 안 씀)
- **Mock 사용 안 함**: U05/U06/U07이 이미 완료돼 있어서, 처음부터 실제 API로 바로 구현 (TASK_BREAKDOWN에 적힌 "U05/U06이 아직이면 mock" 조건에 해당하지 않음)

## 2. 완료 기준 테스트 결과

브라우저 자동화로 실제 흐름 확인 (⚠️ 파일 `<input type=file>`은 보안상 스크립트로 값을 못 넣어서, `DataTransfer` API로 실제 mp4 파일을 프로그래밍적으로 주입해서 테스트함 — 실제 사용자가 파일 선택 다이얼로그로 고르는 것과 동일한 `change` 이벤트가 발생하므로 컴포넌트 로직 검증에는 동일):

1. U06에서 쓴 실제 자막 클립(`clip_with_caption.mp4`)을 업로드 → 화면에 즉시 "상태: 대기중" 표시
2. 백그라운드 워커(U06) 실행 중 상태로 대기 → 워커가 처리 완료하자 **화면이 자동으로 "상태: 완료"로 갱신됨** (수동 새로고침 없이, 폴링으로)
3. 화면에 표시된 JSON이 실제 `GET /projects/{id}` 응답(`status: "done"`, `updated_at` 갱신됨)과 일치
   → **U08 완료 기준 통과** (mock 없이 실제 U05~U07까지 전부 연결된 상태로 바로 확인됨)

## 3. 다음 Unit(U09)이 알아야 할 것

- 폴링 간격: 3초 (`UploadPage.jsx`의 `POLL_INTERVAL_MS`)
- `project.status`가 `done`이 된 이후 화면은 현재 project의 원본 JSON만 보여줌 — **이벤트 목록/타임라인/오디오 미리듣기는 아직 없음** (U09에서 구현)
- U09에서 결과 화면을 만들 때 `GET /projects/{id}/events`(U07)를 그대로 쓰면 됨
- 업로드는 한 번에 하나만 추적함 (여러 개 업로드 이력 목록은 없음 — 필요해지면 `/projects` 목록 API 추가 필요, U07 인계 파일에도 메모됨)

## 4. 미해결/보류 이슈

- 업로드 진행률(progress bar) 없음 — 지금은 업로드 요청이 끝날 때까지 "업로드 중..." 텍스트만 표시
- 실패(`status: failed`) 시 사용자에게 원인을 알려줄 방법 없음 (DB에 에러 메시지 컬럼이 없어서 — U06 이슈와 동일)
- 업로드 완료 후 "결과 보기" 같은 명시적 다음 액션 버튼 없음 (U09에서 결과 화면과 자연스럽게 연결할 때 추가하면 됨)
