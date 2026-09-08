# U06 요약 — 백그라운드 워커 (분석 파이프라인 연결)

## 1. 완료한 것

- [`backend/worker.py`](../backend/worker.py) — `status: pending`인 project를 폴링해서 기존 `src/`의 M1~M3 로직을 그대로 실행:
  1. Supabase Storage에서 영상을 임시 파일로 다운로드
  2. `src.event_detection.compute_diff_signal` / `find_events` / `attach_stable_frames`로 이벤트 감지 (ROI는 `project.roi`가 있으면 사용, 없으면 로컬 프로토타입과 동일한 기본값 `(0,650,1920,1080)`로 폴백)
  3. `src.reference_matching.load_references` / `classify_frame`으로 효과 타입 분류
  4. `src.sfx_matching.SfxPicker`로 효과음 선택
  5. `events` 테이블에 insert, 끝나면 project `status: done` (실패 시 `failed`)
- **인증 방식**: 워커는 특정 로그인 사용자 세션이 없는 별도 프로세스라 U03/U05의 "사용자 JWT forward" 방식을 쓸 수 없음 → **U01에서 예약해뒀던 `service_role` 키를 여기서 처음 사용**. FastAPI 앱(`main.py`)은 여전히 이 키를 안 쓰고, `worker.py`만 사용
  - `service_role` 키는 사용자가 직접 `.env`에 입력(채팅에 값 노출 없이 진행) — [backend/.env.example](../backend/.env.example)에 자리만 마련해둠
- `backend/requirements.txt`에 `numpy`/`pillow`/`ImageHash`/`ImageIO`/`imageio-ffmpeg`/`PyYAML` 추가 (루트 `requirements.txt`와 동일 버전) — `src/` 코드를 백엔드 venv에서 그대로 import해서 재사용
- **Mock 전략 그대로 적용**: 참고 이미지/효과음 라이브러리는 아직 사용자별 Storage 등록 시스템이 없어서, 오늘 로컬 프로토타입과 동일한 `references/references.yaml` + `eff sample/` 폴더를 그대로 재사용 (워커가 로컬 파일시스템에서 직접 읽음)

## 2. 완료 기준 테스트 결과

1. U01 테스트 때 남아있던 가짜 project 행 4개(`videos/user1_sample.mp4` 등, 실제 Storage 파일 없음) 정리
2. 실제 자막이 있는 원본 샘플 영상(`/Users/mac/Downloads/효과 사이트 구축용 샘플 영상.mp4`, 로컬 프로토타입에서 쓰던 것)에서 195~230초 구간(실제 자막 이벤트가 있는 216초 부근 포함)을 잘라 `POST /projects/upload`로 업로드
3. `WORKER_RUN_ONCE=1 .venv/bin/python worker.py` 실행 → `status: pending` → `processing` → `done` 전환 확인
4. `events` 테이블에 실제 이벤트 4건 생성 확인, 그중 하나가:
   ```json
   {
     "start_ms": 20987, "end_ms": 21154,
     "effect_type": "caption_style_01",
     "match_score": 16,
     "matched_sfx_path": ".../eff sample/iam 컷인 01.wav"
   }
   ```
   → 클립 offset 20.99초 = 원본 영상 기준 215.99초 — **오늘 로컬 프로토타입 결과(`data/output.csv`의 `215.98,216.15,caption_style_01,18,iam 컷인 01.wav`)와 거의 정확히 일치**. 나머지 3건은 `unknown`(원본 결과와 마찬가지로 미분류가 대다수인 경향도 일치).
   → **U06 완료 기준 통과.**
5. 추가로 U05의 1초짜리 더미(단색) 테스트 영상도 처리해서, 이벤트가 거의 없는 영상에서도 워커가 정상 동작(`unknown` 이벤트 1건, `status: done`)함을 확인

## 3. 다음 Unit(U07)이 알아야 할 것

- 워커 실행: `cd backend && .venv/bin/python worker.py` (무한 폴링) 또는 `WORKER_RUN_ONCE=1 ...` (1건만 처리하고 종료, 테스트용)
- `events` 테이블 컬럼: `project_id, start_ms, end_ms, representative_frame_path(현재 항상 null), effect_type, match_score, matched_sfx_path`
- `matched_sfx_path`는 **로컬 파일시스템 절대 경로**임 (Supabase Storage 경로 아님) — U01 스키마 주석엔 "Storage 경로"라고 되어 있었지만, 아직 사용자별 SFX 라이브러리를 Storage에 등록하는 기능이 없어서 임시로 로컬 경로를 그대로 저장 중. **U07(결과 조회 API)이나 이후 Unit에서 이 경로로 실제 파일을 서빙할 방법이 필요함** (지금 이대로는 브라우저가 접근 불가)
- `representative_frame_path`는 항상 null (대표 프레임 이미지를 Storage에 업로드하는 로직 없음 — 필요시 추가 Unit)
- `project.roi`가 비어있으면 워커가 로컬 프로토타입 기본값 `(0,650,1920,1080)`을 씀 — 실제 서비스에서는 사용자가 지정한 ROI를 써야 함(U08/U09에서 ROI 지정 UI 필요)
- `SUPABASE_SERVICE_ROLE_KEY`는 `backend/.env`에만 있고 커밋되지 않음 — 새 환경에서 워커를 돌리려면 이 값을 다시 채워야 함

## 4. 미해결/보류 이슈

- 참고 이미지/SFX 라이브러리가 여전히 로컬 파일 기반(`references/`, `eff sample/`) — 사용자별로 Storage에 등록하는 기능은 아직 없음. 실제 여러 사용자가 쓰려면 이 부분을 반드시 나중에 DB(`reference_images` 테이블)/Storage 기반으로 바꿔야 함
- `matched_sfx_path`가 로컬 경로라 프론트엔드에서 오디오 미리듣기 불가 (U07/U09에서 해결 필요)
- 워커가 단일 프로세스 순차 폴링이라 동시에 여러 project를 처리 못 함 (트래픽 늘면 TECH_SPEC에 적힌 대로 큐 기반으로 교체 예정)
- 에러 처리 시 project.status만 `failed`로 바뀌고 에러 상세 내용은 로그에만 남음(DB에 에러 메시지 컬럼 없음)
