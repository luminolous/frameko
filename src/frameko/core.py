from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import json
import time

import numpy as np

from .config import FramekoConfig
from .errors import DependencyMissingError
from .video.ffmpeg import ensure_ffmpeg, ensure_ffprobe, probe_video
from .scenes.scenedetect_adapter import detect_scenes
from .pipelines.sampling import sample_timestamps
from .video.extract import extract_frame
from .pipelines.dedup import dhash_uint64, hamming_distance
from .pipelines.quality import variance_of_laplacian


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

        # External tools for ingest
        ensure_ffmpeg()
        ensure_ffprobe()

        # Embedding
        self._embedder = None

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
        """Ingest a video and add frames to the index.

        Returns: video_id
        """
        video_path = Path(video_path)
        info = probe_video(video_path)
        video_id = self.store.upsert_video(video_path=str(video_path), info=info)

        # Detect scenes (optional)
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

        fps = float(info.get("fps", 0.0)) if info.get("fps") else 0.0
        fpp = frames_per_scene if frames_per_scene is not None else self.cfg.frames_per_scene

        # Sample timestamps
        ts = sample_timestamps(
            scenes,
            frames_per_scene=fpp,
            edge_eps=self.cfg.scene_edge_epsilon_sec,
        )

        # Extract, filter, embed in batches
        extracted: List[Tuple[int, str]] = []  # (frame_id, path)
        seen_hashes: List[int] = []

        for i, (t_sec, scene_idx) in enumerate(ts):
            out_path = self.frames_dir / f"{video_id}_{i:06d}.{self.cfg.image_format}"
            extract_frame(
                video_path=video_path,
                t_sec=t_sec,
                out_path=out_path,
                jpeg_quality=self.cfg.jpeg_quality,
            )

            # Compute dhash + dedup
            dh = dhash_uint64(out_path, hash_size=self.cfg.dhash_size)
            if self.cfg.enable_dedup:
                is_dup = False
                for prev in seen_hashes[-500:]:  # small rolling window to keep it fast
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

            # Blur filter (optional)
            if self.cfg.enable_blur_filter:
                v = variance_of_laplacian(out_path)
                if v < self.cfg.blur_var_threshold:
                    try:
                        out_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    continue
            else:
                v = None

            frame_id = self.store.insert_frame(
                video_id=video_id,
                t_sec=float(t_sec),
                scene_idx=scene_idx,
                frame_path=str(out_path),
                dhash=int(dh),
                blur_var=float(v) if v is not None else None,
            )
            extracted.append((frame_id, str(out_path)))

        if not extracted:
            return video_id

        embedder = self._get_embedder()
        paths = [p for _, p in extracted]
        vectors = embedder.encode_images(paths)

        # Upsert into backend
        ids = np.array([fid for fid, _ in extracted], dtype=np.int64)
        payloads = [
            {
                "video_id": video_id,
                "t_sec": self.store.get_frame_t_sec(fid),
                "frame_path": self.store.get_frame_path(fid),
                "scene_idx": self.store.get_frame_scene_idx(fid),
            }
            for fid, _ in extracted
        ]
        self.backend.upsert(ids=ids, vectors=vectors, payloads=payloads)
        self.backend.save()

        return video_id

    def close(self) -> None:
        try:
            self.store.close()
        finally:
            self.backend.close()
