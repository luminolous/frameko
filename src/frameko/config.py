from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import json
import yaml

from .errors import ConfigError


@dataclass
class FramekoConfig:
    # Scene detection
    scene_detector: str = "adaptive"  # "adaptive" | "content" | "none"
    scene_threshold: float = 27.0
    min_scene_len_frames: int = 15

    # Sampling
    frames_per_scene: int = 1  # 1 or 3
    scene_edge_epsilon_sec: float = 0.15

    # Dedup
    enable_dedup: bool = True
    dhash_size: int = 8
    max_hamming: int = 6

    # Blur filter
    enable_blur_filter: bool = False
    blur_var_threshold: float = 80.0

    # Extraction
    image_format: str = "jpg"
    jpeg_quality: int = 2  # ffmpeg -q:v (lower is better)

    extra: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def presets_dir() -> Path:
        return Path(__file__).parent / "presets"

    @classmethod
    def load_preset(cls, name: str) -> "FramekoConfig":
        p = cls.presets_dir() / f"{name}.yaml"
        if not p.exists():
            raise ConfigError(f"Preset not found: {name} ({p})")
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ConfigError("Preset YAML must be a mapping")
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FramekoConfig":
        # Allow unknown keys in extra
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        base = {k: v for k, v in d.items() if k in known}
        extra = {k: v for k, v in d.items() if k not in known}
        cfg = cls(**base)  # type: ignore[arg-type]
        cfg.extra.update(extra)
        return cfg

    def to_dict(self) -> Dict[str, Any]:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__.keys()}  # type: ignore[attr-defined]
        return d

    def save_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
