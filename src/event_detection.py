"""
M1: 자막 이벤트 감지 (프레임 차분 기반)

영상을 프레임 단위로 훑으면서, 지정한 ROI(관심 영역) 안에서
"큰 변화가 생겼다가 다시 안정된" 구간을 자막 이벤트 후보로 찾아낸다.

이 모듈은 아직 "효과 타입 분류"는 하지 않는다 (TECH_SPEC.md M1 범위).
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from PIL import Image
import imageio


@dataclass
class Event:
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    peak_diff: float
    representative_frame_idx: int | None = None  # "움직임 멈춘 첫 프레임" (안정화 프레임)


def _to_gray_small(frame: np.ndarray, roi: tuple[int, int, int, int] | None, size=(320, 180)) -> np.ndarray:
    """프레임을 ROI로 자르고, 그레이스케일 + 축소해서 비교 연산량을 줄인다."""
    img = Image.fromarray(frame)
    if roi is not None:
        x0, y0, x1, y1 = roi
        img = img.crop((x0, y0, x1, y1))
    img = img.convert("L").resize(size)
    return np.asarray(img, dtype=np.float32)


def compute_diff_signal(video_path: str, roi: tuple[int, int, int, int] | None = None,
                         sample_every: int = 1, max_frames: int | None = None):
    """영상 전체를 훑으며 인접 프레임(ROI) 간 평균 절대 차이를 계산한다.

    Returns: (fps, diffs: list[float], frame_indices: list[int])
    frame_indices[i]는 diffs[i]가 "frame_indices[i-1] -> frame_indices[i]" 변화량임을 의미.
    """
    reader = imageio.get_reader(video_path, "ffmpeg")
    meta = reader.get_meta_data()
    fps = meta["fps"]

    diffs = []
    frame_indices = []
    prev_gray = None
    for idx, frame in enumerate(reader):
        if max_frames is not None and idx >= max_frames:
            break
        if idx % sample_every != 0:
            continue
        gray = _to_gray_small(frame, roi)
        if prev_gray is not None:
            diff = float(np.abs(gray - prev_gray).mean())
            diffs.append(diff)
            frame_indices.append(idx)
        prev_gray = gray
    reader.close()
    return fps, diffs, frame_indices


def find_events(fps: float, diffs: list[float], frame_indices: list[int],
                 threshold: float, min_gap_frames: int = 5) -> list[Event]:
    """diff 신호에서 임계값을 넘는 구간을 찾아 이벤트로 그룹핑한다."""
    events: list[Event] = []
    in_event = False
    cur_start_i = None
    cur_peak = 0.0

    def close_event(end_i):
        nonlocal in_event, cur_start_i, cur_peak
        start_frame = frame_indices[cur_start_i]
        end_frame = frame_indices[end_i]
        events.append(Event(
            start_frame=start_frame,
            end_frame=end_frame,
            start_time=start_frame / fps,
            end_time=end_frame / fps,
            peak_diff=cur_peak,
        ))
        in_event = False
        cur_start_i = None
        cur_peak = 0.0

    for i, d in enumerate(diffs):
        if d >= threshold:
            if not in_event:
                in_event = True
                cur_start_i = i
                cur_peak = d
            else:
                cur_peak = max(cur_peak, d)
        else:
            if in_event:
                close_event(i - 1)
    if in_event:
        close_event(len(diffs) - 1)

    # 너무 가까운 이벤트는 하나로 병합 (디바운스)
    merged: list[Event] = []
    for ev in events:
        if merged and (ev.start_frame - merged[-1].end_frame) <= min_gap_frames:
            prev = merged[-1]
            merged[-1] = Event(
                start_frame=prev.start_frame,
                end_frame=ev.end_frame,
                start_time=prev.start_time,
                end_time=ev.end_time,
                peak_diff=max(prev.peak_diff, ev.peak_diff),
            )
        else:
            merged.append(ev)
    return merged


def attach_stable_frames(fps: float, diffs: list[float], frame_indices: list[int],
                          events: list[Event], stable_threshold: float,
                          search_window_frames: int = 30) -> None:
    """각 이벤트 종료 시점 이후, diff가 다시 stable_threshold 밑으로 떨어지는
    첫 프레임을 '대표(정지) 프레임'으로 지정한다 (TECH_SPEC 3.2)."""
    idx_lookup = {f: i for i, f in enumerate(frame_indices)}
    for ev in events:
        end_i = idx_lookup.get(ev.end_frame)
        if end_i is None:
            continue
        rep_i = None
        for i in range(end_i, min(end_i + search_window_frames, len(diffs))):
            if diffs[i] < stable_threshold:
                rep_i = i
                break
        ev.representative_frame_idx = frame_indices[rep_i] if rep_i is not None else ev.end_frame
