"""
U03: FastAPI 스캐폴딩 + JWT 인증 미들웨어.
U05: 영상 업로드 API.

실행:
    uvicorn app.main:app --reload --port 8000

확인용 엔드포인트:
    GET  /                  - 헬스체크 (인증 불필요)
    GET  /me                - 로그인(유효한 Supabase JWT) 필요. 토큰 없으면 401,
                              유효하면 200 + 사용자 정보 반환.
    POST /projects/upload   - 로그인 필요. 영상 파일을 Supabase Storage에 저장하고
                              projects 테이블에 status=pending 행 생성.
"""

from dotenv import load_dotenv

load_dotenv()  # SUPABASE_URL 등 .env를 app.auth/app.supabase_rest가 import될 때 읽을 수 있도록 먼저 로드

import os
import uuid

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.auth import AuthedUser, get_current_user
from app.supabase_rest import insert_row, upload_object

app = FastAPI(title="AutoSFX API")

VIDEOS_BUCKET = os.environ.get("SUPABASE_VIDEOS_BUCKET", "videos")

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
