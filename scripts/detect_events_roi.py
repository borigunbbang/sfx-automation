"""
ROI(하단 자막 영역)로 제한해서 이벤트를 다시 찾는 버전.
카메라 컷/화면 전환(화이트 플래시)과 자막 팝업을 구분하기 위해
"지속시간이 있는(순간적이지 않은)" 이벤트만 후보로 남긴다.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import imageio
from PIL import Image

from src.event_detection import compute_diff_signal, find_events, attach_stable_frames

VIDEO_PATH = "/Users/mac/Downloads/효과 사이트 구축용 샘플 영상.mp4"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "events_roi")
ROI = (0, 650, 1920, 1080)  # 하단 넓게
MIN_DURATION_FRAMES = 3  # 0.1s 이상 지속된 것만 "자막 팝업" 후보로


def main():
    print(f"영상 분석 시작 (ROI={ROI})")
    fps, diffs, frame_indices = compute_diff_signal(VIDEO_PATH, roi=ROI, sample_every=1)
    diffs_arr = np.array(diffs)
    print(f"총 프레임 비교 수: {len(diffs)}, fps={fps:.2f}")
    for p in [50, 80, 90, 95, 97, 99]:
        print(f"  percentile {p}: {np.percentile(diffs_arr, p):.3f}")

    threshold = float(np.percentile(diffs_arr, 97))
    stable_threshold = float(np.percentile(diffs_arr, 50))
    print(f"threshold={threshold:.3f} stable_threshold={stable_threshold:.3f}")

    events = find_events(fps, diffs, frame_indices, threshold=threshold, min_gap_frames=int(fps * 0.2))
    print(f"전체 이벤트 후보: {len(events)}")

    # 지속시간 필터: 순간적인 컷/플래시 제외
    long_events = [e for e in events if (e.end_frame - e.start_frame) >= MIN_DURATION_FRAMES]
    print(f"지속시간 {MIN_DURATION_FRAMES}프레임 이상인 후보: {len(long_events)}")

    attach_stable_frames(fps, diffs, frame_indices, long_events, stable_threshold=stable_threshold)

    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        os.remove(os.path.join(OUT_DIR, f))

    reader = imageio.get_reader(VIDEO_PATH, "ffmpeg")
    for i, ev in enumerate(long_events):
        rep_idx = ev.representative_frame_idx or ev.end_frame
        try:
            frame = reader.get_data(rep_idx)
        except Exception as e:
            print(f"프레임 {rep_idx} 읽기 실패: {e}")
            continue
        img = Image.fromarray(frame).resize((960, 540))
        dur = (ev.end_frame - ev.start_frame) / fps
        fname = f"ev{i:03d}_t{ev.start_time:.2f}-{ev.end_time:.2f}s_dur{dur:.2f}_peak{ev.peak_diff:.1f}.jpg"
        img.save(os.path.join(OUT_DIR, fname), quality=85)
    reader.close()
    print(f"{len(long_events)}장 저장 완료: {OUT_DIR}")

    for i, ev in enumerate(long_events):
        dur = (ev.end_frame - ev.start_frame) / fps
        print(f"  [{i:03d}] {ev.start_time:7.2f}s ~ {ev.end_time:7.2f}s (dur={dur:.2f}s, peak={ev.peak_diff:.1f})")


if __name__ == "__main__":
    main()
