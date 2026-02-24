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

    if (not out_path.exists()) or out_path.stat().st_size == 0:
        cmd2 = [
            "ffmpeg","-hide_banner","-loglevel","error",
            "-i", str(video_path),
            "-ss", f"{t_sec:.3f}",
            "-frames:v","1",
        ]
        if out_path.suffix.lower() in {".jpg",".jpeg"}:
            cmd2 += ["-q:v", str(int(jpeg_quality))]
        cmd2 += ["-y", str(out_path)]
        p2 = run(cmd2)
        if p2.returncode != 0 or (not out_path.exists()) or out_path.stat().st_size == 0:
            raise RuntimeError(f"ffmpeg produced empty output at t={t_sec:.3f}. stderr: {(p2.stderr or p.stderr)[:500]}")
