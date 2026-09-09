"""
U06: 백그라운드 워커 — status=pending인 project를 찾아
기존 src/의 M1(이벤트 감지) → M2(참고 이미지 매칭) → M3(SFX 선택) 로직을 그대로 실행하고,
결과를 events 테이블에 저장한 뒤 project.status를 done으로 바꾼다.

이 워커는 특정 로그인 사용자 세션 없이 모든 사용자의 pending project를 찾아야 하므로,
U03/U05와 달리 사용자 JWT를 forward하는 방식을 쓸 수 없다 — 대신 Supabase의
service_role 키로 REST/Storage를 호출한다 (RLS를 우회하는 대신, 쿼리에서
직접 project_id/user_id로 범위를 좁혀서 안전하게 사용한다).

Mock 전략 (TASK_BREAKDOWN.md U06 참고):
  참고 이미지/효과음 라이브러리는 아직 사용자별 Storage 등록 시스템이 없어서,
  오늘 로컬 프로토타입에서 쓰던 것과 동일한 로컬 설정(references/references.yaml,
  eff sample/ 폴더)을 그대로 재사용한다. 사용자별 등록은 이후 Unit에서 다룬다.

실행:
    .venv/bin/python worker.py            # 무한 폴링
    WORKER_RUN_ONCE=1 .venv/bin/python worker.py   # pending 1건만 처리하고 종료 (테스트용)
"""

import os
import sys
import tempfile
import time
import unicodedata

import httpx
import numpy as np
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# backend/ 의 부모 디렉터리(sfx-automation/)를 sys.path에 추가해서
# 기존 M1~M3 프로토타입 코드(src/)를 그대로 import해서 재사용한다.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from src.event_detection import attach_stable_frames, compute_diff_signal, find_events  # noqa: E402
from src.reference_matching import DEFAULT_ROI, classify_frame, load_references  # noqa: E402
from src.sfx_matching import SfxPicker  # noqa: E402
import imageio  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
REST_URL = f"{SUPABASE_URL}/rest/v1"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"

REFERENCES_YAML = os.path.join(ROOT_DIR, "references", "references.yaml")
MIN_DURATION_FRAMES = 3
POLL_INTERVAL_SEC = int(os.environ.get("WORKER_POLL_INTERVAL_SEC", "10"))

_HEADERS = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
}


def fetch_next_pending_project(client: httpx.Client):
    resp = client.get(
        f"{REST_URL}/projects",
        params={"status": "eq.pending", "order": "created_at.asc", "limit": "1"},
        headers=_HEADERS,
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def set_status(client: httpx.Client, project_id: str, status: str):
    resp = client.patch(
        f"{REST_URL}/projects",
        params={"id": f"eq.{project_id}"},
        json={"status": status},
        headers={**_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"},
    )
    resp.raise_for_status()


def download_video(client: httpx.Client, video_path: str) -> str:
    """video_path는 `{bucket}/{path}` 형태 (U05가 저장한 그대로). 임시 파일로 받아 경로를 반환."""
    resp = client.get(f"{STORAGE_URL}/object/{video_path}", headers=_HEADERS)
    resp.raise_for_status()

    fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
    with os.fdopen(fd, "wb") as f:
        f.write(resp.content)
    return tmp_path


def insert_event(client: httpx.Client, data: dict):
    resp = client.post(
        f"{REST_URL}/events",
        json=data,
        headers={**_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"},
    )
    resp.raise_for_status()


def roi_from_project(project: dict):
    roi = project.get("roi")
    if not roi:
        # 아직 ROI 지정 UI가 없어서(U08/U09), 오늘 로컬 프로토타입과 동일한 기본값으로 대체.
        return DEFAULT_ROI
    return (roi["x"], roi["y"], roi["x"] + roi["width"], roi["y"] + roi["height"])


def process_project(client: httpx.Client, project: dict):
    project_id = project["id"]
    print(f"[worker] 처리 시작: project={project_id}")
    set_status(client, project_id, "processing")

    local_video = None
    try:
        local_video = download_video(client, project["video_path"])
        roi = roi_from_project(project)

        fps, diffs, frame_indices = compute_diff_signal(local_video, roi=roi, sample_every=1)
        events = []
        if diffs:
            diffs_arr = np.array(diffs)
            threshold = float(np.percentile(diffs_arr, 97))
            stable_threshold = float(np.percentile(diffs_arr, 50))
            events = find_events(fps, diffs, frame_indices, threshold=threshold, min_gap_frames=int(fps * 0.2))
            events = [e for e in events if (e.end_frame - e.start_frame) >= MIN_DURATION_FRAMES]
            attach_stable_frames(fps, diffs, frame_indices, events, stable_threshold=stable_threshold)

        print(f"[worker] 이벤트 후보 {len(events)}개 감지")

        references = load_references(REFERENCES_YAML)
        picker = SfxPicker()
        reader = imageio.get_reader(local_video, "ffmpeg")
        for ev in events:
            rep_idx = ev.representative_frame_idx or ev.end_frame
            frame = reader.get_data(rep_idx)
            img = Image.fromarray(frame)
            effect_type, dist, matched_ref = classify_frame(img, references)
            sfx_path = picker.pick(matched_ref.sfx_folder) if matched_ref else None
            # U12: matched_sfx_path에는 이 워커가 도는 컴퓨터에서만 의미 있는 로컬 절대
            # 경로 대신 원본 파일명만 저장한다 — 백엔드(Render)는 이 파일명으로 효과음
            # 라이브러리 Storage 버킷(backend/scripts/sync_sfx_library.py가 채움)을 찾는다.
            # NFC 정규화: macOS os.listdir()은 한글 파일명을 NFD로 돌려주는데, Storage
            # 매니페스트/프론트는 NFC를 기준으로 삼는다(sync_sfx_library.py 참고).
            sfx_filename = unicodedata.normalize("NFC", os.path.basename(sfx_path)) if sfx_path else None

            insert_event(client, {
                "project_id": project_id,
                "start_ms": int(ev.start_time * 1000),
                "end_ms": int(ev.end_time * 1000),
                "effect_type": effect_type,
                "match_score": float(dist) if dist is not None else None,
                "matched_sfx_path": sfx_filename,
            })
        reader.close()

        set_status(client, project_id, "done")
        print(f"[worker] 완료: project={project_id}, 이벤트 {len(events)}건 저장")
    except Exception:
        set_status(client, project_id, "failed")
        raise
    finally:
        if local_video and os.path.exists(local_video):
            os.remove(local_video)


def main():
    run_once = os.environ.get("WORKER_RUN_ONCE") == "1"
    print(f"[worker] 시작 (poll interval={POLL_INTERVAL_SEC}s, run_once={run_once})")
    with httpx.Client(timeout=120) as client:
        while True:
            project = fetch_next_pending_project(client)
            if project:
                try:
                    process_project(client, project)
                except Exception as exc:
                    # U12: 프로젝트 하나가 깨진 영상 등으로 실패해도(status는 이미 "failed"로
                    # 기록됨) 워커 전체가 죽어서 이후 pending 프로젝트를 영영 못 받는 일이
                    # 없도록, 여기서 잡고 계속 폴링한다. run_once(테스트용)는 기존처럼 종료.
                    print(f"[worker] 처리 실패(계속 진행): project={project['id']} ({exc})")
                if run_once:
                    return
            else:
                if run_once:
                    print("[worker] pending project 없음")
                    return
                time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
