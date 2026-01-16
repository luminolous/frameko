from pathlib import Path
import shutil
import subprocess

import pytest

from frameko.video.extract import extract_frame
from frameko.video.ffmpeg import ensure_ffmpeg


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_extract_frame(tmp_path: Path):
    ensure_ffmpeg()

    # Create a tiny synthetic video (2 seconds) with color source
    video = tmp_path / "test.mp4"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=red:s=320x240:d=2",
        "-y",
        str(video),
    ]
    subprocess.run(cmd, check=True)

    out = tmp_path / "frame.jpg"
    extract_frame(video, t_sec=0.5, out_path=out)
    assert out.exists()
    assert out.stat().st_size > 0
