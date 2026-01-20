from __future__ import annotations

import subprocess
from pathlib import Path

from .ffmpeg import run


def extract_frame(
    video_path: Path,
    t_sec: float,
    out_path: Path,
    jpeg_quality: int = 2,
) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{t_sec:.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
    ]

    if out_path.suffix.lower() in {".jpg", ".jpeg"}:
        cmd += ["-q:v", str(int(jpeg_quality))]

    cmd += ["-y", str(out_path)]

    p = run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg extract failed: {p.stderr[:500]}")
