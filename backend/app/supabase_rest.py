"""
Supabase REST(PostgREST) / Storage API를 사용자 자신의 JWT로 호출하는 얇은 래퍼.

service_role 키를 쓰지 않고 사용자의 access token을 그대로 forward하기 때문에,
U01에서 설정한 DB RLS 정책과 U05에서 설정하는 Storage RLS 정책이
백엔드를 거치더라도 그대로(즉, "본인 데이터만") 적용된다.
"""

import json
import os
import unicodedata
from typing import Any, Dict, List, Optional

import httpx

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# U12: 효과음 라이브러리는 사용자별 데이터가 아니라 앱 전체가 공유하는 고정 자산이라,
# 다른 함수들과 달리 사용자 JWT가 아니라 service_role 키로만 접근하는 비공개 버킷을 쓴다
# (backend/scripts/sync_sfx_library.py가 이 버킷을 채운다).
SFX_LIBRARY_BUCKET = os.environ.get("SUPABASE_SFX_BUCKET", "sfx-library")
_SFX_MANIFEST_KEY = "_manifest.json"


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


async def update_rows(
    *, table: str, params: Dict[str, Any], data: dict, user_token: str
) -> List[dict]:
    """PostgREST PATCH 요청 (해당 사용자 권한으로). RLS로 본인 소유가 아닌 행은 조용히
    0건 갱신되므로(에러가 아님), 반환된 리스트가 비어 있으면 호출부에서 404로 처리해야 한다."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = _headers(user_token, content_type="application/json")
    headers["Prefer"] = "return=representation"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(url, params=params, json=data, headers=headers)

    if resp.status_code >= 400:
        raise RuntimeError(f"{table} 수정 실패 ({resp.status_code}): {resp.text}")

    return resp.json()


async def delete_rows(*, table: str, params: Dict[str, Any], user_token: str) -> List[dict]:
    """PostgREST DELETE 요청 (해당 사용자 권한으로). 반환 리스트가 비어 있으면 삭제된 행이
    없다는 뜻 (존재하지 않거나 본인 소유가 아님 — RLS가 조용히 걸러냄)."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = _headers(user_token, content_type="application/json")
    headers["Prefer"] = "return=representation"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.delete(url, params=params, headers=headers)

    if resp.status_code >= 400:
        raise RuntimeError(f"{table} 삭제 실패 ({resp.status_code}): {resp.text}")

    return resp.json()


def _service_headers(*, content_type: Optional[str] = None) -> dict:
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY가 설정되지 않았습니다 (효과음 라이브러리 접근에 필요).")
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


async def _fetch_sfx_manifest() -> Dict[str, str]:
    """{슬러그: 원본파일명} 매니페스트를 읽는다 (backend/scripts/sync_sfx_library.py가 올려둠)."""
    url = f"{SUPABASE_URL}/storage/v1/object/{SFX_LIBRARY_BUCKET}/{_SFX_MANIFEST_KEY}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_service_headers())
    if resp.status_code >= 400:
        raise RuntimeError(f"효과음 라이브러리 매니페스트 조회 실패 ({resp.status_code}): {resp.text}")
    return json.loads(resp.content)


async def list_sfx_filenames() -> List[str]:
    """효과음 라이브러리에 실제로 있는 원본 파일명 목록 (DB/프론트가 쓰는 이름 기준)."""
    manifest = await _fetch_sfx_manifest()
    return list(manifest.values())


async def fetch_sfx_object(filename: str) -> bytes:
    """원본 파일명으로 효과음 원본 바이트를 가져온다 (미리듣기 스트리밍용).
    Storage 키는 공백/한글을 허용하지 않아서 매니페스트로 슬러그를 역조회한 뒤 요청한다.
    매니페스트는 NFC로 정규화해서 저장돼 있으므로(sync_sfx_library.py), 입력값도 NFC로
    맞춰서 비교한다 — 브라우저(NFC)와 macOS 파일시스템(NFD)의 한글 정규화 형태가 다르다."""
    filename = unicodedata.normalize("NFC", filename)
    manifest = await _fetch_sfx_manifest()
    slug = next((s for s, original in manifest.items() if original == filename), None)
    if slug is None:
        raise FileNotFoundError(filename)

    url = f"{SUPABASE_URL}/storage/v1/object/{SFX_LIBRARY_BUCKET}/{slug}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_service_headers())
    if resp.status_code == 404:
        raise FileNotFoundError(filename)
    if resp.status_code >= 400:
        raise RuntimeError(f"효과음 파일 조회 실패 ({resp.status_code}): {resp.text}")
    return resp.content
