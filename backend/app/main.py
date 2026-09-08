"""
U03: FastAPI 스캐폴딩 + JWT 인증 미들웨어.

실행:
    uvicorn app.main:app --reload --port 8000

확인용 엔드포인트:
    GET /            - 헬스체크 (인증 불필요)
    GET /me          - 로그인(유효한 Supabase JWT) 필요. 토큰 없으면 401,
                       유효하면 200 + 사용자 정보 반환.
"""

from dotenv import load_dotenv

load_dotenv()  # SUPABASE_URL 등 .env를 app.auth가 import될 때 읽을 수 있도록 먼저 로드

from fastapi import Depends, FastAPI

from app.auth import get_current_user

app = FastAPI(title="AutoSFX API")


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {
        "id": user.get("sub"),
        "email": user.get("email"),
        "role": user.get("role"),
    }
