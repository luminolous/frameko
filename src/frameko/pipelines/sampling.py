from __future__ import annotations

from typing import List, Sequence, Tuple


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
