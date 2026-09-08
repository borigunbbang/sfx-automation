"""
U03: FastAPI 스캐폴딩 + JWT 인증 미들웨어.
U05: 영상 업로드 API.
U07: 결과 조회 API.

실행:
    uvicorn app.main:app --reload --port 8000

확인용 엔드포인트:
    GET  /                          - 헬스체크 (인증 불필요)
    GET  /me                        - 로그인(유효한 Supabase JWT) 필요. 토큰 없으면 401,
                                       유효하면 200 + 사용자 정보 반환.
    POST /projects/upload           - 로그인 필요. 영상 파일을 Supabase Storage에 저장하고
                                       projects 테이블에 status=pending 행 생성.
    GET  /projects/{id}             - 로그인 필요. project 상태 조회 (본인 소유만, 없으면 404).
    GET  /projects/{id}/events      - 로그인 필요. 해당 project의 이벤트 목록.
    GET  /projects/{id}/export.csv  - 로그인 필요. 이벤트를 CSV로 내보내기.
    GET  /events/{id}/sfx-audio     - 로그인 필요. 매칭된 효과음 파일 스트리밍 (U09 미리듣기용).
"""

from dotenv import load_dotenv

load_dotenv()  # SUPABASE_URL 등 .env를 app.auth/app.supabase_rest가 import될 때 읽을 수 있도록 먼저 로드

import csv
import io
import os
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from app.auth import AuthedUser, get_current_user
from app.supabase_rest import fetch_rows, insert_row, upload_object

app = FastAPI(title="AutoSFX API")

VIDEOS_BUCKET = os.environ.get("SUPABASE_VIDEOS_BUCKET", "videos")

# U09: 매칭된 효과음(matched_sfx_path)이 아직 Storage가 아니라 로컬 파일 경로라서(U06 이슈),
# 이 루트 밖의 경로는 절대 서빙하지 않도록 제한한다 (임의 파일 읽기 방지용 안전장치).
# 워커(worker.py)와 동일하게 backend/의 부모 디렉터리(sfx-automation/)를 루트로 잡는다.
_ROOT_DIR = os.path.realpath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_SFX_MEDIA_TYPES = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aiff": "audio/aiff"}

# 프론트엔드(U04, Vite 개발 서버)에서 브라우저 fetch로 호출할 수 있도록 CORS 허용.
# 콤마로 여러 origin을 지정할 수 있게 하고, 기본값은 로컬 Vite 개발 서버.
_allowed_origins = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/me")
def me(user: AuthedUser = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.claims.get("role"),
    }


@app.post("/projects/upload")
async def upload_project_video(
    file: UploadFile,
    user: AuthedUser = Depends(get_current_user),
):
    """
    영상 파일을 업로드받아:
      1. Supabase Storage `{VIDEOS_BUCKET}/{user_id}/{project_id}_{원본파일명}`에 저장
      2. `projects` 테이블에 status=pending 행 생성
    분석 파이프라인 연결은 U06에서 처리 (여기서는 저장/기록까지만).
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")

    project_id = str(uuid.uuid4())
    safe_filename = file.filename or "upload.mp4"
    storage_path = f"{user.id}/{project_id}_{safe_filename}"

    try:
        await upload_object(
            bucket=VIDEOS_BUCKET,
            path=storage_path,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            user_token=user.token,
        )

        project = await insert_row(
            table="projects",
            data={
                "id": project_id,
                "user_id": user.id,
                "video_path": f"{VIDEOS_BUCKET}/{storage_path}",
                "status": "pending",
            },
            user_token=user.token,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return project


async def _get_owned_project(project_id: str, user: AuthedUser) -> dict:
    """본인 소유 project 1건을 가져온다. RLS 덕분에 다른 사람 project는 그냥 빈 목록으로 와서
    존재 여부를 굳이 구분하지 않고 404로 통일할 수 있다 (다른 사용자 데이터 존재 유무를 노출하지 않음)."""
    try:
        rows = await fetch_rows(
            table="projects",
            params={"id": f"eq.{project_id}"},
            user_token=user.token,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not rows:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    return rows[0]


@app.get("/projects/{project_id}")
async def get_project(project_id: str, user: AuthedUser = Depends(get_current_user)):
    return await _get_owned_project(project_id, user)


@app.get("/projects/{project_id}/events")
async def get_project_events(project_id: str, user: AuthedUser = Depends(get_current_user)):
    await _get_owned_project(project_id, user)  # 존재/소유 확인 (없으면 404)

    try:
        events = await fetch_rows(
            table="events",
            params={"project_id": f"eq.{project_id}", "order": "start_ms.asc"},
            user_token=user.token,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return events


@app.get("/projects/{project_id}/export.csv")
async def export_project_csv(project_id: str, user: AuthedUser = Depends(get_current_user)):
    """
    이벤트를 CSV로 내보낸다 (TECH_SPEC.md 4.6).
    컬럼: timestamp_sec, end_sec, effect_type, sfx_filename
    (REAPER 마커/리전 임포트과의 정확한 컬럼 호환은 M9 확장 단계에서 다시 다룰 예정 —
     지금은 "타임코드 + 효과 타입 + 파일명" 정보를 담는 표 형태만 우선 제공)
    """
    await _get_owned_project(project_id, user)

    try:
        events = await fetch_rows(
            table="events",
            params={"project_id": f"eq.{project_id}", "order": "start_ms.asc"},
            user_token=user.token,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["timestamp_sec", "end_sec", "effect_type", "sfx_filename"])
    for ev in events:
        sfx_path = ev.get("matched_sfx_path")
        writer.writerow([
            round(ev["start_ms"] / 1000, 2),
            round(ev["end_ms"] / 1000, 2),
            ev["effect_type"],
            os.path.basename(sfx_path) if sfx_path else "",
        ])
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="project_{project_id}_events.csv"'},
    )


_SFX_LIBRARY_DIR = os.path.realpath(os.path.join(_ROOT_DIR, "eff sample"))


@app.get("/events/{event_id}/sfx-audio")
async def get_event_sfx_audio(
    event_id: str,
    filename: Optional[str] = None,
    user: AuthedUser = Depends(get_current_user),
):
    """
    U09 오디오 미리듣기용 간이 서빙 엔드포인트.

    matched_sfx_path는 아직 Storage가 아니라 워커가 도는 서버의 로컬 파일 경로다
    (U06/U09 인계 파일 참고 — SFX 라이브러리를 Storage로 옮기는 건 이후 Unit 과제).
    events는 user_id가 없고 project를 통해서만 소유자가 확인되므로, RLS가 걸린
    사용자 JWT로 조회해서 본인 프로젝트의 이벤트가 아니면 자연히 빈 목록(→404)이 된다.

    U10부터: `filename` 쿼리 파라미터를 주면 DB에 저장된 matched_sfx_path 대신
    로컬 SFX 라이브러리(`eff sample/`)에서 그 파일명을 바로 찾아 재생한다.
    보정 UI(U10)에서 "효과음 교체"는 화면(mock)에만 반영되고 서버에는 저장되지
    않으므로(U11 예정), 교체 직후 미리듣기도 이 파일명 기준으로 동작해야
    실제로 바뀐 소리를 들을 수 있다. event_id 소유권 확인은 그대로 거친다.
    """
    try:
        rows = await fetch_rows(
            table="events",
            params={"id": f"eq.{event_id}"},
            user_token=user.token,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not rows:
        raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")

    if filename:
        safe_name = os.path.basename(filename)  # 경로 조작 방지 (../ 등 제거)
        sfx_path = os.path.join(_SFX_LIBRARY_DIR, safe_name)
    else:
        sfx_path = rows[0].get("matched_sfx_path")

    if not sfx_path:
        raise HTTPException(status_code=404, detail="매칭된 효과음이 없습니다.")

    real_path = os.path.realpath(sfx_path)
    if not (real_path == _ROOT_DIR or real_path.startswith(_ROOT_DIR + os.sep)):
        raise HTTPException(status_code=403, detail="허용되지 않은 경로입니다.")
    if not os.path.isfile(real_path):
        raise HTTPException(status_code=404, detail="효과음 파일을 찾을 수 없습니다.")

    ext = os.path.splitext(real_path)[1].lower()
    media_type = _SFX_MEDIA_TYPES.get(ext, "application/octet-stream")
    return FileResponse(real_path, media_type=media_type)
