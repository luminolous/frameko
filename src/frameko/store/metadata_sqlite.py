from __future__ import annotations

import ctypes
import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

def _to_i64(x):
    if x is None:
        return None
    return ctypes.c_int64(int(x)).value

def _stable_video_id(path: str, info: Dict[str, Any]) -> str:
    # Simple stable-ish id: hash of absolute path + size + duration
    p = str(Path(path).resolve())
    size = str(info.get("size", ""))
    dur = str(round(float(info.get("duration", 0.0)), 3))
    s = (p + "|" + size + "|" + dur).encode("utf-8")
    return hashlib.sha1(s).hexdigest()[:16]


class MetadataStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        sql = schema_path.read_text(encoding="utf-8")
        self.conn.executescript(sql)
        self.conn.commit()

    def upsert_video(self, video_path: str, info: Dict[str, Any]) -> str:
        vid = _stable_video_id(video_path, info)
        now = time.time()
        self.conn.execute(
            """
            INSERT INTO videos(video_id, path, duration, fps, width, height, codec, format, size, created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(video_id) DO UPDATE SET
              path=excluded.path,
              duration=excluded.duration,
              fps=excluded.fps,
              width=excluded.width,
              height=excluded.height,
              codec=excluded.codec,
              format=excluded.format,
              size=excluded.size
            """,
            (
                vid,
                video_path,
                float(info.get("duration") or 0.0),
                float(info.get("fps") or 0.0) if info.get("fps") is not None else None,
                info.get("width"),
                info.get("height"),
                info.get("codec"),
                info.get("format"),
                int(info.get("size") or 0),
                now,
            ),
        )
        self.conn.commit()
        return vid

    def insert_frame(
        self,
        video_id: str,
        t_sec: float,
        scene_idx: Optional[int],
        frame_path: str,
        dhash: Optional[int],
        blur_var: Optional[float],
    ) -> int:
        now = time.time()
        dhash = _to_i64(dhash)
        
        cur = self.conn.execute(
            """
            INSERT INTO frames(video_id, t_sec, scene_idx, frame_path, dhash, blur_var, created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (video_id, float(t_sec), scene_idx, frame_path, dhash, blur_var, now),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_frame(self, frame_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM frames WHERE frame_id=?", (int(frame_id),))
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_frame_path(self, frame_id: int) -> Optional[str]:
        cur = self.conn.execute("SELECT frame_path FROM frames WHERE frame_id=?", (int(frame_id),))
        row = cur.fetchone()
        return str(row[0]) if row else None

    def get_frame_t_sec(self, frame_id: int) -> Optional[float]:
        cur = self.conn.execute("SELECT t_sec FROM frames WHERE frame_id=?", (int(frame_id),))
        row = cur.fetchone()
        return float(row[0]) if row else None

    def get_frame_scene_idx(self, frame_id: int) -> Optional[int]:
        cur = self.conn.execute("SELECT scene_idx FROM frames WHERE frame_id=?", (int(frame_id),))
        row = cur.fetchone()
        if row is None:
            return None
        return int(row[0]) if row[0] is not None else None

    def close(self) -> None:
        self.conn.close()
