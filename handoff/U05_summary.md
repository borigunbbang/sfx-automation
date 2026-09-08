# U05 요약 — 영상 업로드 API

## 1. 완료한 것

- [`backend/app/main.py`](../backend/app/main.py) — `POST /projects/upload` 엔드포인트 추가
  - `multipart/form-data`로 영상 파일(`file`)을 받음 (인증 필요, `Depends(get_current_user)`)
  - Supabase Storage `{bucket}/{user_id}/{project_id}_{원본파일명}`에 업로드
  - `projects` 테이블에 `status: pending` 행 insert, 생성된 행을 그대로 응답으로 반환
- [`backend/app/auth.py`](../backend/app/auth.py) 리팩터링: `get_current_user`가 이제 `AuthedUser`(원본 JWT 문자열 + claim)를 반환하도록 변경 — U05부터 사용자의 원본 토큰을 Supabase REST/Storage 호출에 그대로 forward해야 하기 때문
- [`backend/app/supabase_rest.py`](../backend/app/supabase_rest.py) — Supabase REST(PostgREST)/Storage를 **사용자 본인의 JWT로** 호출하는 `httpx` 기반 헬퍼 (`upload_object`, `insert_row`). **`service_role` 키를 전혀 쓰지 않음** — U01의 DB RLS, 이번에 만든 Storage RLS가 백엔드를 거쳐도 그대로 적용됨
- `backend/requirements.txt`에 `httpx`, `python-multipart` 추가
- `backend/.env`(.example)에 `SUPABASE_ANON_KEY`, `SUPABASE_VIDEOS_BUCKET=video` 추가
- **Supabase Storage 버킷 `video`** (대시보드에서 수동 생성, public=OFF) + RLS 정책 6개 (INSERT / SELECT+UPDATE / SELECT+DELETE 조합, 대시보드 Storage Policies UI에서 생성)
  - 조건식: `bucket_id = 'video' and (storage.foldername(name))[1] = auth.uid()::text` — 자기 user_id 폴더만 접근 가능
  - ⚠️ **SQL 편집기로는 `storage.objects`에 정책을 만들 수 없음** (`42501: must be owner of table objects`) — 반드시 대시보드 Storage → Policies UI 사용. [`supabase/migrations/0002_storage_videos_bucket.sql`](../supabase/migrations/0002_storage_videos_bucket.sql)에 참고용으로 기록해둠 (실행용 아님)
  - ⚠️ **버킷 이름은 `videos`가 아니라 `video`(단수)** — 처음 생성할 때 그렇게 만들어져서 그대로 유지하기로 함. 이후 Unit에서 버킷 이름 참조 시 `video` 사용할 것

## 2. 완료 기준 테스트 결과

1. 토큰 없이 업로드 → `401 {"detail":"Authorization: Bearer <token> 헤더가 필요합니다."}`
2. 로그인 후(`dpfla0130@gmail.com`) 샘플 mp4 파일(`ffmpeg`로 생성한 1초짜리 더미 영상)을 업로드:
   ```
   POST /projects/upload → 200
   {
     "id": "39be2b91-affe-4f55-9183-598bebd581d1",
     "user_id": "a59df9c8-f6c9-4c24-a2a0-332d9cd78abc",
     "video_path": "video/a59df9c8-f6c9-4c24-a2a0-332d9cd78abc/39be2b91-affe-4f55-9183-598bebd581d1_sample.mp4",
     "status": "pending", ...
   }
   ```
3. Supabase REST/Storage API로 실제 생성 여부 직접 확인:
   - `GET /rest/v1/projects?id=eq.<id>` → 위와 동일한 행이 실제 DB에 존재함을 확인
   - `POST /storage/v1/object/list/video` (prefix=해당 user_id) → 업로드한 파일(`..._sample.mp4`, 12331 bytes)이 Storage에 실제로 존재함을 확인
   → **U05 완료 기준 통과.**

## 3. 다음 Unit(U06)이 알아야 할 것

- 엔드포인트: `POST /projects/upload` (multipart, 필드명 `file`), 응답은 생성된 `projects` 행 그대로 (`id`, `user_id`, `video_path`, `roi`, `status`, `created_at`, `updated_at`)
- Storage 경로 규칙: `video/{user_id}/{project_id}_{원본파일명}` (버킷명 `video`, 단수 주의)
- `video_path` 컬럼에는 버킷명까지 포함한 전체 경로(`video/...`)가 저장됨 — U06 워커가 다운로드할 때 이 값을 그대로 Storage object 경로로 쓰면 됨
- 백엔드는 `service_role` 키 없이 사용자의 JWT를 그대로 forward하는 방식(`app/supabase_rest.py`)을 씀 — U06(백그라운드 워커)은 사용자 세션이 없는 별도 프로세스이므로 이 방식이 그대로는 안 통함. U06에서는 `service_role` 키(또는 워커 전용 인증)가 필요할 가능성이 높음 — 그때 다시 검토 필요
- 분석 파이프라ine(이벤트 감지 등)은 아직 연결 안 됨 (U06에서 처리)

## 4. 미해결/보류 이슈

- 업로드 파일 크기/형식 검증 없음 (실제 서비스 전 U12 등에서 제한 추가 필요)
- 테스트로 생성된 project 행 1건, Storage 파일 1건이 실제 DB/Storage에 남아있음 (정리 필수는 아님)
- U06(백그라운드 워커)은 사용자 로그인 세션이 없는 상태로 동작해야 하므로, 이번에 채택한 "사용자 JWT forward" 인증 방식을 그대로 못 씀 — service_role 키 도입 여부를 U06에서 다시 판단해야 함
