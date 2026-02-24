from __future__ import annotations
from typing import List, Sequence, Tuple, Optional


def sample_timestamps(
    scenes: Sequence[Tuple[float, float]],
    frames_per_scene: int = 1,
    edge_eps: float = 0.15,
) -> List[Tuple[float, int]]:
    """Return list of (t_sec, scene_idx).

    frames_per_scene:
      - 1: mid
      - 3: start/mid/end with epsilon offset
    """
    out: List[Tuple[float, int]] = []
    for idx, (s, e) in enumerate(scenes):
        if e <= s:
            continue
        dur = e - s
        if frames_per_scene == 1:
            out.append((s + dur / 2.0, idx))
        elif frames_per_scene == 3:
            out.append((min(e, s + edge_eps), idx))
            out.append((s + dur / 2.0, idx))
            out.append((max(s, e - edge_eps), idx))
        else:
            out.append((s + dur / 2.0, idx))
    return out

def sample_every_seconds(
    *,
    duration: float,
    every_sec: float = 1.0,
    scenes: Optional[Sequence[Tuple[float, float]]] = None,
    start_sec: float = 0.0,
    end_sec: Optional[float] = None,
) -> List[Tuple[float, int]]:
    """Return list of (t_sec, scene_idx) sampled every N seconds.
    If scenes is provided, scene_idx is assigned based on which scene contains t_sec.
    """
    if every_sec <= 0:
        raise ValueError("every_sec must be > 0")

    end = duration if end_sec is None else min(float(end_sec), float(duration))
    t = max(0.0, float(start_sec))

    # generate global timestamps
    ts: List[float] = []
    while t < end:
        ts.append(t)
        t += float(every_sec)

    if not scenes:
        return [(x, 0) for x in ts]

    # map each timestamp to scene index (scenes assumed sorted)
    out: List[Tuple[float, int]] = []
    j = 0
    n = len(scenes)
    for x in ts:
        while j < n and x >= scenes[j][1]:
            j += 1
        if j >= n:
            break
        # if there is a gap (rare), skip until we enter a scene
        if x < scenes[j][0]:
            continue
        out.append((x, j))
    return out
