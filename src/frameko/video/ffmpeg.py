from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..errors import ExternalToolMissingError


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise ExternalToolMissingError(
            "ffmpeg not found in PATH. Install ffmpeg and ensure it's available."
        )


def ensure_ffprobe() -> None:
    if shutil.which("ffprobe") is None:
        raise ExternalToolMissingError(
            "ffprobe not found in PATH. Install ffmpeg (includes ffprobe)."
        )


def run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)


def probe_video(video_path: Path) -> Dict[str, Any]:
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(str(video_path))

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(video_path),
    ]
    p = run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {p.stderr[:500]}")

    data = json.loads(p.stdout)
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    vstream = None
    for s in streams:
        if s.get("codec_type") == "video":
            vstream = s
            break

    duration = float(fmt.get("duration", 0.0) or 0.0)

    fps = None
    if vstream:
        # r_frame_rate like "24000/1001"
        r = vstream.get("r_frame_rate") or vstream.get("avg_frame_rate")
        if r and isinstance(r, str) and "/" in r:
            num, den = r.split("/", 1)
            try:
                fps = float(num) / float(den)
            except Exception:
                fps = None

    info: Dict[str, Any] = {
        "duration": duration,
        "fps": fps,
        "width": vstream.get("width") if vstream else None,
        "height": vstream.get("height") if vstream else None,
        "codec": vstream.get("codec_name") if vstream else None,
        "format": fmt.get("format_name"),
        "size": int(fmt.get("size", 0) or 0),
    }
    return info
