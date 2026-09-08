"""
Supabase가 발급한 JWT를 검증하는 인증 미들웨어(FastAPI dependency).

이 프로젝트는 Supabase의 비대칭(ES256) JWT 서명 키를 사용하므로,
service_role 같은 비밀 값 없이 Supabase의 공개 JWKS 엔드포인트만으로
토큰 서명을 검증할 수 있다.
  JWKS: {SUPABASE_URL}/auth/v1/.well-known/jwks.json

토큰이 없거나 유효하지 않으면 401을 반환한다.

U05부터: 검증된 사용자의 원본 토큰(raw JWT)도 함께 보관해서,
Supabase REST/Storage 호출 시 그대로 forward한다 — 이렇게 하면
DB/Storage의 RLS 정책이 그 사용자 기준으로 그대로 적용되어,
백엔드가 service_role 같은 강한 권한 없이도 "본인 데이터만" 안전하게 다룰 수 있다.
"""

import os
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_JWT_AUD = os.environ.get("SUPABASE_JWT_AUD", "authenticated")
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
ISSUER = f"{SUPABASE_URL}/auth/v1"

# PyJWKClient가 kid 기준으로 알맞은 공개키를 찾아주고 내부적으로 캐싱한다.
_jwks_client = jwt.PyJWKClient(JWKS_URL)

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthedUser:
    token: str  # 원본 JWT 문자열 (Supabase REST/Storage 호출에 그대로 forward)
    claims: dict  # 검증된 JWT payload

    @property
    def id(self) -> str:
        return self.claims["sub"]

    @property
    def email(self) -> Optional[str]:
        return self.claims.get("email")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> AuthedUser:
    """유효한 Supabase JWT를 검증해 AuthedUser로 반환. 실패 시 401."""
    if credentials is None:
        raise _unauthorized("Authorization: Bearer <token> 헤더가 필요합니다.")

    token = credentials.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience=SUPABASE_JWT_AUD,
            issuer=ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise _unauthorized(f"유효하지 않은 토큰입니다: {exc}") from exc

    return AuthedUser(token=token, claims=payload)
