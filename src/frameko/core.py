from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import json
import time
import hashlib

import numpy as np

from .config import FramekoConfig
from .video.ffmpeg import ensure_ffmpeg, ensure_ffprobe, probe_video
from .scenes.scenedetect_adapter import detect_scenes
from .pipelines.sampling import sample_timestamps
from .video.extract import extract_frame
from .pipelines.dedup import dhash_uint64, hamming_distance
from .pipelines.quality import variance_of_laplacian


@dataclass(frozen=True)
class ExtractedFrame:
    frame_uid: int
    t_sec: float
    scene_idx: int
    frame_path: str
    dhash: int
    blur_var: Optional[float]


class Frameko:
    def __init__(
        self,
        index_dir: Union[str, Path],
        backend: str = "faiss",
        preset: str = "default",
        config: Optional[FramekoConfig] = None,
        backend_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.frames_dir = self.index_dir / "frames"
        self.frames_dir.mkdir(parents=True, exist_ok=True)

        self.cfg = config or FramekoConfig.load_preset(preset)
        self.cfg_path = self.index_dir / "config.json"
        self.cfg.save_json(self.cfg_path)

        # Metadata output
        self.videos_jsonl = self.index_dir / "videos.jsonl"
        self.frames_jsonl = self.index_dir / "frames.jsonl"

        # External tools for ingest
        ensure_ffmpeg()
        ensure_ffprobe()

        # Embedding / backend (optional)
        self._embedder = None
        # NOTE: assuming elsewhere in your code you set:
        #   self.backend = ...
        # If you don't use backend anymore, you can set self.backend = None.

    # helpers
    def _make_video_id(self, video_path: Path) -> str:
        h = hashlib.blake2b(str(video_path.resolve()).encode("utf-8"), digest_size=6).hexdigest()
        return f"v_{int(time.time())}_{h}"

    def _frame_uid64(self, video_id: str, frame_idx: int) -> int:
        b = f"{video_id}:{frame_idx}".encode("utf-8")
        digest = hashlib.blake2b(b, digest_size=8).digest()
        return int.from_bytes(digest, byteorder="big", signed=False)

    def _append_jsonl(self, path: Path, obj: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # main
    def ingest(
        self,
        video_path: Union[str, Path],
        *,
        frames_per_scene: Optional[int] = None,
        detector: Optional[str] = None,
        threshold: Optional[float] = None,
        min_scene_len_frames: Optional[int] = None,
        limit_scenes: Optional[int] = None,
    ) -> str:
        video_path = Path(video_path)
        info = probe_video(video_path)
        video_id = self._make_video_id(video_path)

        # save "video table" record
        self._append_jsonl(
            self.videos_jsonl,
            {
                "video_id": video_id,
                "video_path": str(video_path),
                "info": info,
                "created_at": time.time(),
            },
        )

        # Detect scenes
        det = detector or self.cfg.scene_detector
        if det == "none":
            scenes = [(0.0, float(info.get("duration", 0.0)))]
        else:
            scenes = detect_scenes(
                video_path,
                detector=det,
                threshold=threshold if threshold is not None else self.cfg.scene_threshold,
                min_scene_len_frames=min_scene_len_frames
                if min_scene_len_frames is not None
                else self.cfg.min_scene_len_frames,
                limit_scenes=limit_scenes,
            )
            if not scenes:
                scenes = [(0.0, float(info.get("duration", 0.0)))]

        fpp = frames_per_scene if frames_per_scene is not None else self.cfg.frames_per_scene

        # Sample timestamps
        ts = sample_timestamps(
            scenes,
            frames_per_scene=fpp,
            edge_eps=self.cfg.scene_edge_epsilon_sec,
        )

        extracted: List[ExtractedFrame] = []
        seen_hashes: List[int] = []

        for i, (t_sec, scene_idx) in enumerate(ts):
            out_path = self.frames_dir / f"{video_id}_{i:06d}.{self.cfg.image_format}"

            extract_frame(
                video_path=video_path,
                t_sec=float(t_sec),
                out_path=out_path,
                jpeg_quality=self.cfg.jpeg_quality,
            )

            # Compute dhash + dedup
            dh = int(dhash_uint64(out_path, hash_size=self.cfg.dhash_size))
            if self.cfg.enable_dedup:
                is_dup = False
                for prev in seen_hashes[-500:]:
                    if hamming_distance(dh, prev) <= self.cfg.max_hamming:
                        is_dup = True
                        break
                if is_dup:
                    try:
                        out_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    continue
                seen_hashes.append(dh)

            # Blur filter
            blur_v: Optional[float]
            if self.cfg.enable_blur_filter:
                v = float(variance_of_laplacian(out_path))
                if v < self.cfg.blur_var_threshold:
                    try:
                        out_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    continue
                blur_v = v
            else:
                blur_v = None

            frame_uid = self._frame_uid64(video_id, i)
            rec = ExtractedFrame(
                frame_uid=frame_uid,
                t_sec=float(t_sec),
                scene_idx=int(scene_idx),
                frame_path=str(out_path),
                dhash=dh,
                blur_var=blur_v,
            )
            extracted.append(rec)

            # write frame metadata immediately (replaces store.insert_frame)
            self._append_jsonl(
                self.frames_jsonl,
                {
                    "video_id": video_id,
                    "frame_uid": frame_uid,
                    "t_sec": rec.t_sec,
                    "scene_idx": rec.scene_idx,
                    "frame_path": rec.frame_path,
                    "dhash": rec.dhash,
                    "blur_var": rec.blur_var,
                    "created_at": time.time(),
                },
            )

        if not extracted:
            return video_id

        # OPTIONAL: embed + upsert into backend
        if getattr(self, "backend", None) is not None:
            embedder = self._get_embedder()
            paths = [r.frame_path for r in extracted]
            vectors = embedder.encode_images(paths)

            ids = np.array([r.frame_uid for r in extracted], dtype=np.int64)
            payloads = [
                {
                    "video_id": video_id,
                    "t_sec": r.t_sec,
                    "frame_path": r.frame_path,
                    "scene_idx": r.scene_idx,
                }
                for r in extracted
            ]

            self.backend.upsert(ids=ids, vectors=vectors, payloads=payloads)
            self.backend.save()

        return video_id

    def close(self) -> None:
        if getattr(self, "backend", None) is not None:
            self.backend.close()
