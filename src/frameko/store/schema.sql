PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS videos (
  video_id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  duration REAL,
  fps REAL,
  width INTEGER,
  height INTEGER,
  codec TEXT,
  format TEXT,
  size INTEGER,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS frames (
  frame_id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL,
  t_sec REAL NOT NULL,
  scene_idx INTEGER,
  frame_path TEXT NOT NULL,
  dhash INTEGER,
  blur_var REAL,
  created_at REAL NOT NULL,
  FOREIGN KEY(video_id) REFERENCES videos(video_id)
);

CREATE INDEX IF NOT EXISTS idx_frames_video ON frames(video_id);
CREATE INDEX IF NOT EXISTS idx_frames_time ON frames(video_id, t_sec);
