from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from ..errors import DependencyMissingError


Scene = Tuple[float, float]  # (start_sec, end_sec)


def detect_scenes(
    video_path: Path,
    detector: str = "adaptive",
    threshold: float = 27.0,
    min_scene_len_frames: int = 15,
    limit_scenes: Optional[int] = None,
) -> List[Scene]:
    """Detect scenes using PySceneDetect if installed.

    Returns list of (start_sec, end_sec). If scenedetect is missing, returns empty list.
    """
    try:
        from scenedetect import open_video
        from scenedetect.scene_manager import SceneManager
        from scenedetect.detectors import ContentDetector, AdaptiveDetector
    except Exception:
        # Soft-fail: return empty list (caller will fallback)
        return []

    video_path = Path(video_path)

    video = open_video(str(video_path))
    sm = SceneManager()

    det = detector.lower().strip()
    if det == "content":
        sm.add_detector(ContentDetector(threshold=threshold, min_scene_len=min_scene_len_frames))
    else:
        # default adaptive
        sm.add_detector(AdaptiveDetector(threshold=threshold, min_scene_len=min_scene_len_frames))

    sm.detect_scenes(video)
    scene_list = sm.get_scene_list()

    scenes: List[Scene] = []
    for (start, end) in scene_list:
        scenes.append((start.get_seconds(), end.get_seconds()))
        if limit_scenes is not None and len(scenes) >= limit_scenes:
            break

    return scenes
