"""
U12: `eff sample/`(효과음 라이브러리)을 Supabase Storage의 비공개 버킷으로 동기화한다.

Render에 배포된 백엔드는 이 컴퓨터의 로컬 파일에 접근할 수 없으므로, 미리듣기(U09)/
효과음 교체(U11) 기능이 실제 배포 환경에서 동작하려면 라이브러리 자체를 Storage에
올려둬야 한다. 이 버킷은 사용자별 데이터가 아니라 앱 전체가 공유하는 고정 자산이라
public으로 만들지 않고, service_role 키로만 접근하도록 비공개로 유지한다.

Storage 객체 키는 공백/한글 등을 허용하지 않아서(Supabase InvalidKey), 실제 원본
파일명(예: "iam 컷인 01.wav")은 ASCII 슬러그(예: "iam-01.wav")로 변환해 업로드하고,
원본 파일명 <-> 슬러그 매핑을 같은 버킷의 `_manifest.json`에 저장한다.
DB(`matched_sfx_path`)와 프론트엔드는 항상 원본 파일명을 그대로 쓰고, 백엔드가
`_manifest.json`을 통해 슬러그로 변환해서 Storage에서 읽는다
(app/supabase_rest.py의 list_sfx_filenames/fetch_sfx_object 참고).

실행 (라이브러리 파일이 추가/변경될 때마다 재실행하면 됨 — 이미 있는 파일은 덮어씀):
    backend/.venv/bin/python backend/scripts/sync_sfx_library.py
"""

import json
import os
import re
import unicodedata

import httpx
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
BUCKET = os.environ.get("SUPABASE_SFX_BUCKET", "sfx-library")
LIBRARY_DIR = os.path.join(ROOT_DIR, "eff sample")
MANIFEST_KEY = "_manifest.json"

_HEADERS = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
}

_MEDIA_TYPES = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aiff": "audio/aiff"}


def slugify_filename(name: str) -> str:
    """원본 파일명을 Storage 키로 쓸 수 있는 ASCII 슬러그로 바꾼다 (확장자는 유지)."""
    base, ext = os.path.splitext(name)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return f"{slug or 'sfx'}{ext.lower()}"


def ensure_bucket(client: httpx.Client):
    resp = client.get(f"{SUPABASE_URL}/storage/v1/bucket/{BUCKET}", headers=_HEADERS)
    if resp.status_code == 200:
        print(f"[sync] 버킷 '{BUCKET}' 이미 존재함")
        return
    resp = client.post(
        f"{SUPABASE_URL}/storage/v1/bucket",
        json={"name": BUCKET, "public": False},
        headers=_HEADERS,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"버킷 생성 실패 ({resp.status_code}): {resp.text}")
    print(f"[sync] 버킷 '{BUCKET}' 생성 완료 (비공개)")


def build_manifest(disk_names: list) -> tuple:
    """{슬러그: 원본파일명(NFC)}과 {슬러그: 디스크상 실제 파일명} 두 개를 만든다.

    macOS(APFS)는 os.listdir()이 한글 파일명을 NFD(자모 분리)로 돌려주는데, 브라우저/JS는
    보통 NFC(완성형)를 쓴다. 그대로 두면 프론트에서 보낸 파일명과 여기서 만든 매니페스트가
    유니코드 정규화 형태만 달라서 문자열 비교가 실패한다 — 그래서 매니페스트/DB/프론트가
    보는 "원본 파일명"은 항상 NFC로 통일하고, 실제 디스크 파일을 열 때만 원래 이름을 쓴다.
    슬러그 충돌이 나면 숫자를 붙여 구분한다.
    """
    manifest: dict = {}
    disk_name_by_slug: dict = {}
    used_slugs: dict = {}
    for disk_name in disk_names:
        nfc_name = unicodedata.normalize("NFC", disk_name)
        slug = slugify_filename(nfc_name)
        if slug in used_slugs:
            used_slugs[slug] += 1
            base, ext = os.path.splitext(slug)
            slug = f"{base}-{used_slugs[slug]}{ext}"
        else:
            used_slugs[slug] = 0
        manifest[slug] = nfc_name
        disk_name_by_slug[slug] = disk_name
    return manifest, disk_name_by_slug


def upload_all(client: httpx.Client, manifest: dict, disk_name_by_slug: dict):
    for slug, name in manifest.items():
        path = os.path.join(LIBRARY_DIR, disk_name_by_slug[slug])
        ext = os.path.splitext(name)[1].lower()
        with open(path, "rb") as f:
            content = f.read()
        resp = client.post(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{slug}",
            content=content,
            headers={**_HEADERS, "Content-Type": _MEDIA_TYPES[ext], "x-upsert": "true"},
        )
        if resp.status_code >= 400:
            print(f"[sync] 실패: {name} -> {slug} ({resp.status_code}) {resp.text}")
        else:
            print(f"[sync] 업로드: {name} -> {slug} ({len(content):,} bytes)")


def upload_manifest(client: httpx.Client, manifest: dict):
    content = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    resp = client.post(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{MANIFEST_KEY}",
        content=content,
        headers={**_HEADERS, "Content-Type": "application/json", "x-upsert": "true"},
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"매니페스트 업로드 실패 ({resp.status_code}): {resp.text}")
    print(f"[sync] 매니페스트 업로드 완료 ({len(manifest)}건)")


def main():
    if not os.path.isdir(LIBRARY_DIR):
        raise SystemExit(f"라이브러리 폴더를 찾을 수 없습니다: {LIBRARY_DIR}")

    files = sorted(
        f for f in os.listdir(LIBRARY_DIR)
        if os.path.splitext(f)[1].lower() in _MEDIA_TYPES
    )
    if not files:
        raise SystemExit(f"업로드할 효과음 파일이 없습니다: {LIBRARY_DIR}")

    manifest, disk_name_by_slug = build_manifest(files)

    with httpx.Client(timeout=60) as client:
        ensure_bucket(client)
        upload_all(client, manifest, disk_name_by_slug)
        upload_manifest(client, manifest)


if __name__ == "__main__":
    main()
