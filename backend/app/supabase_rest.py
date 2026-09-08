"""
Supabase REST(PostgREST) / Storage API를 사용자 자신의 JWT로 호출하는 얇은 래퍼.

service_role 키를 쓰지 않고 사용자의 access token을 그대로 forward하기 때문에,
U01에서 설정한 DB RLS 정책과 U05에서 설정하는 Storage RLS 정책이
백엔드를 거치더라도 그대로(즉, "본인 데이터만") 적용된다.
"""

import os
from typing import Any, Dict, List, Optional

import httpx

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]


def _headers(user_token: str, *, content_type: Optional[str] = None) -> dict:
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {user_token}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


async def upload_object(*, bucket: str, path: str, content: bytes, content_type: str, user_token: str) -> None:
    """Supabase Storage에 파일을 업로드한다 (해당 사용자 권한으로)."""
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            content=content,
            headers=_headers(user_token, content_type=content_type),
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"Storage 업로드 실패 ({resp.status_code}): {resp.text}")


async def insert_row(*, table: str, data: dict, user_token: str) -> dict:
    """PostgREST를 통해 한 행을 insert하고, 생성된 행을 반환한다 (해당 사용자 권한으로)."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = _headers(user_token, content_type="application/json")
    headers["Prefer"] = "return=representation"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=data, headers=headers)

    if resp.status_code >= 400:
        raise RuntimeError(f"{table} insert 실패 ({resp.status_code}): {resp.text}")

    rows = resp.json()
    return rows[0]


async def fetch_rows(*, table: str, params: Dict[str, Any], user_token: str) -> List[dict]:
    """PostgREST GET 요청 (해당 사용자 권한으로) — RLS로 본인 소유 행만 반환된다."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params, headers=_headers(user_token))

    if resp.status_code >= 400:
        raise RuntimeError(f"{table} 조회 실패 ({resp.status_code}): {resp.text}")

    return resp.json()
