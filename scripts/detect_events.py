"""
M1 프로토타입 실행 스크립트.

사용법:
    python scripts/detect_events.py

영상 전체를 훑어서 diff 신호를 계산하고, 분포(percentile)를 출력한 뒤
임계값을 기준으로 이벤트를 찾아 대표 프레임 썸네일을 data/events/ 에 저장한다.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import imageio
from PIL import Image

from src.event_detection import compute_diff_signal, find_events, attach_stable_frames

VIDEO_PATH = "/Users/mac/Downloads/효과 사이트 구축용 샘플 영상.mp4"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "events")


def main():
    print(f"영상 분석 시작: {VIDEO_PATH}")
    fps, diffs, frame_indices = compute_diff_signal(VIDEO_PATH, roi=None, sample_every=1)
    diffs_arr = np.array(diffs)
    print(f"총 프레임 비교 수: {len(diffs)}, fps={fps:.2f}")
    for p in [50, 80, 90, 95, 97, 99, 99.5, 99.9]:
        print(f"  percentile {p}: {np.percentile(diffs_arr, p):.3f}")
    print(f"  max: {diffs_arr.max():.3f}")

    # 상위 1% 정도를 "큰 변화"로 보고 임계값을 잡아본다 (튜닝 포인트)
    threshold = float(np.percentile(diffs_arr, 99))
    stable_threshold = float(np.percentile(diffs_arr, 50))
    print(f"\n사용할 threshold(이벤트 시작 기준)={threshold:.3f}, stable_threshold(안정화 기준)={stable_threshold:.3f}")

    events = find_events(fps, diffs, frame_indices, threshold=threshold, min_gap_frames=int(fps * 0.3))
    print(f"\n감지된 이벤트 후보 수: {len(events)}")

    attach_stable_frames(fps, diffs, frame_indices, events, stable_threshold=stable_threshold)

    os.makedirs(OUT_DIR, exist_ok=True)
    # 오래된 결과 정리
    for f in os.listdir(OUT_DIR):
        os.remove(os.path.join(OUT_DIR, f))

    reader = imageio.get_reader(VIDEO_PATH, "ffmpeg")
    saved = 0
    max_save = 40
    for i, ev in enumerate(events):
        if saved >= max_save:
            break
        rep_idx = ev.representative_frame_idx or ev.end_frame
        try:
            frame = reader.get_data(rep_idx)
        except Exception as e:
            print(f"  프레임 {rep_idx} 읽기 실패: {e}")
            continue
        img = Image.fromarray(frame).resize((960, 540))
        fname = f"ev{i:03d}_t{ev.start_time:.1f}-{ev.end_time:.1f}s_peak{ev.peak_diff:.1f}.jpg"
        img.save(os.path.join(OUT_DIR, fname), quality=85)
        saved += 1
    reader.close()
    print(f"\n대표 프레임 {saved}장을 {OUT_DIR} 에 저장했습니다.")

    print("\n이벤트 목록 (시작-끝, 시간):")
    for i, ev in enumerate(events[:max_save]):
        print(f"  [{i:03d}] {ev.start_time:7.2f}s ~ {ev.end_time:7.2f}s  (peak={ev.peak_diff:.2f})")


if __name__ == "__main__":
    main()
