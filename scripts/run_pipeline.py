"""
M1 -> M2 -> M3 전체 파이프라인 실행 스크립트.

영상 -> 자막 이벤트 감지 -> (단순) 참고 이미지 매칭 -> 효과음 선택 -> CSV 출력

사용법:
    python scripts/run_pipeline.py
"""
import sys, os, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import imageio
from PIL import Image

from src.event_detection import compute_diff_signal, find_events, attach_stable_frames
from src.reference_matching import load_references, classify_frame
from src.sfx_matching import SfxPicker

VIDEO_PATH = "/Users/mac/Downloads/효과 사이트 구축용 샘플 영상.mp4"
REFERENCES_YAML = os.path.join(os.path.dirname(__file__), "..", "references", "references.yaml")
OUT_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "output.csv")
ROI = (0, 650, 1920, 1080)
MIN_DURATION_FRAMES = 3


def main():
    print("=== M1: 자막 이벤트 감지 ===")
    fps, diffs, frame_indices = compute_diff_signal(VIDEO_PATH, roi=ROI, sample_every=1)
    diffs_arr = np.array(diffs)
    threshold = float(np.percentile(diffs_arr, 97))
    stable_threshold = float(np.percentile(diffs_arr, 50))

    events = find_events(fps, diffs, frame_indices, threshold=threshold, min_gap_frames=int(fps * 0.2))
    events = [e for e in events if (e.end_frame - e.start_frame) >= MIN_DURATION_FRAMES]
    attach_stable_frames(fps, diffs, frame_indices, events, stable_threshold=stable_threshold)
    print(f"이벤트 후보 {len(events)}개 감지")

    print("\n=== M2: 참고 이미지 매칭 ===")
    references = load_references(REFERENCES_YAML)
    print(f"등록된 참고 이미지 {len(references)}개: {[r.effect_type for r in references]}")

    print("\n=== M3: 효과음 매칭 + CSV 출력 ===")
    picker = SfxPicker()
    reader = imageio.get_reader(VIDEO_PATH, "ffmpeg")

    rows = []
    for ev in events:
        rep_idx = ev.representative_frame_idx or ev.end_frame
        frame = reader.get_data(rep_idx)
        img = Image.fromarray(frame)
        effect_type, dist, matched_ref = classify_frame(img, references)

        sfx_path = None
        if matched_ref is not None:
            sfx_path = picker.pick(matched_ref.sfx_folder)

        rows.append({
            "timestamp_sec": round(ev.start_time, 2),
            "end_sec": round(ev.end_time, 2),
            "effect_type": effect_type,
            "match_distance": dist,
            "sfx_filename": os.path.basename(sfx_path) if sfx_path else "",
        })
    reader.close()

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp_sec", "end_sec", "effect_type", "match_distance", "sfx_filename"])
        writer.writeheader()
        writer.writerows(rows)

    matched = sum(1 for r in rows if r["effect_type"] != "unknown")
    print(f"\n총 {len(rows)}개 이벤트 중 {matched}개 매칭, {len(rows)-matched}개 미분류")
    print(f"결과 CSV: {OUT_CSV}")

    print("\n미리보기 (상위 20개):")
    for r in rows[:20]:
        print(f"  {r['timestamp_sec']:7.2f}s  type={r['effect_type']:16s} dist={r['match_distance']:>4}  sfx={r['sfx_filename']}")


if __name__ == "__main__":
    main()
