# U07 요약 — 결과 조회 API

## 1. 완료한 것

- [`backend/app/supabase_rest.py`](../backend/app/supabase_rest.py)에 `fetch_rows()` 추가 — 사용자 JWT로 PostgREST GET 요청(RLS 적용)
- [`backend/app/main.py`](../backend/app/main.py)에 3개 엔드포인트 추가 (모두 로그인 필요, U03/U05와 동일하게 `service_role` 없이 사용자 JWT forward):
  - `GET /projects/{id}` — project 1건 조회
  - `GET /projects/{id}/events` — 해당 project의 이벤트 목록 (`start_ms` 오름차순)
  - `GET /projects/{id}/export.csv` — 이벤트를 CSV로 내보내기
- 소유권 확인 로직(`_get_owned_project`): RLS가 본인 소유가 아닌 행은 그냥 빈 목록으로 돌려주는 것을 이용해, "존재하지 않음"과 "남의 데이터라 안 보임"을 구분하지 않고 **둘 다 404로 통일** (다른 사용자 데이터의 존재 여부 자체를 노출하지 않기 위함)
- CSV 컬럼: `timestamp_sec, end_sec, effect_type, sfx_filename` (TECH_SPEC.md 4.6 기준). ⚠️ REAPER 마커/리전 임포트와의 정확한 컬럼 포맷 호환은 이번 Unit에서는 다루지 않음 — M9(향후 확장)에서 실제 REAPER 임포트 테스트하며 다시 다듬을 예정

## 2. 완료 기준 테스트 결과 (U06에서 만든 실제 데이터로 확인)

프로젝트 `02718277-0966-4efb-be0c-8973718bf700` (U06에서 처리 완료된 캡션 클립) 기준:

1. 토큰 없이 `GET /projects/{id}` → `401`
2. `GET /projects/{id}` → `200` + project 전체 필드(`status: done` 등) 정확히 반환
3. `GET /projects/{id}/events` → `200` + U06이 저장한 이벤트 4건 그대로 반환 (JSON 예시는 아래)
4. 존재하지 않는 id로 `GET /projects/{다른id}` → `404 {"detail":"프로젝트를 찾을 수 없습니다."}`
5. `GET /projects/{id}/export.csv` → `200`, `Content-Disposition: attachment`, 내용:
   ```csv
   timestamp_sec,end_sec,effect_type,sfx_filename
   20.99,21.15,caption_style_01,iam 컷인 01.wav
   26.86,26.99,unknown,
   29.09,29.3,unknown,
   31.83,31.93,unknown,
   ```
   → **U07 완료 기준 통과.**

## 3. API 응답 스키마 예시

`GET /projects/{id}`:
```json
{
  "id": "02718277-0966-4efb-be0c-8973718bf700",
  "user_id": "a59df9c8-f6c9-4c24-a2a0-332d9cd78abc",
  "video_path": "video/<user_id>/<project_id>_clip_with_caption.mp4",
  "roi": null,
  "status": "done",
  "created_at": "2026-09-08T08:26:43.562559+00:00",
  "updated_at": "2026-09-08T08:28:16.827251+00:00"
}
```

`GET /projects/{id}/events` (배열, `start_ms` 오름차순):
```json
[
  {
    "id": "d0b24494-e518-4fe5-925b-c172d13f06e8",
    "project_id": "02718277-0966-4efb-be0c-8973718bf700",
    "start_ms": 20987,
    "end_ms": 21154,
    "representative_frame_path": null,
    "effect_type": "caption_style_01",
    "match_score": 16,
    "matched_sfx_path": "/Users/mac/Documents/afeel/sfx-automation/eff sample/iam 컷인 01.wav",
    "created_at": "2026-09-08T08:28:14.455393+00:00"
  }
]
```

## 4. 다음 Unit(U08)이 알아야 할 것

- 프론트엔드 업로드 화면(U08)에서 이 3개 엔드포인트로 상태 폴링(`GET /projects/{id}`의 `status` 필드) 및 결과 표시(`GET /projects/{id}/events`) 가능
- `events[].matched_sfx_path`가 여전히 **로컬 파일 경로**임 (U06 이슈 그대로 유지) — 프론트에서 오디오 미리듣기를 하려면 별도 서빙 방법이 필요함 (예: 이 경로를 브라우저가 접근 가능한 형태로 바꾸는 엔드포인트 추가, 혹은 향후 SFX를 Storage로 옮기는 작업)
- CSV 다운로드는 인증된 `fetch` 필요 (`<a href>` 직링크 불가, `Authorization` 헤더 필요) — 프론트에서 구현 시 blob으로 받아서 다운로드 트리거하는 방식 고려

## 5. 미해결/보류 이슈

- REAPER 마커/리전 임포트 CSV의 정확한 컬럼 포맷 미검증 (M9에서 다룸)
- `/projects` (내 프로젝트 목록 전체 조회) 엔드포인트는 아직 없음 — 지금은 프론트가 업로드 응답의 `id`를 기억해둬야 함 (U08에서 필요해지면 추가)
