# Frameko

**Frameko** is a lightweight Python toolkit for turning videos into **clean, representative frame datasets**. It runs a simple pipeline: **scene detection → timestamp sampling → FFmpeg frame extraction**, with optional **near-duplicate removal (dHash)** and **blur filtering (variance of Laplacian)**.

It’s especially handy when you want a compact set of frames from long videos (anime clips, movies, lectures, gameplay) without extracting *every single frame*.

---

## Highlights

- **Scene detection** using PySceneDetect (`content`, `adaptive`, or `none`).
- **Sampling**: extract `1` (mid) or `3` (start/mid/end) frames per detected scene.
- **Fast extraction** via **ffmpeg** (`ffmpeg -ss ... -frames:v 1`).
- **Optional dedup** using perceptual **dHash** + Hamming distance.
- **Optional blur filter** using **variance of Laplacian** (no OpenCV required for the metric).
- **Automatic metadata** output (`videos.jsonl`, `frames.jsonl`) + config snapshot (`config.json`).

---

## Installation

### Requirements

- Python **>= 3.9**
- **ffmpeg** + **ffprobe** available in your PATH

### How to use

```bash
git clone https://github.com/luminolous/frameko.git
cd frameko
pip install -e .
```

```bash
apt-get update -y
apt-get install -y ffmpeg
pip install -e .
```

```python
from frameko import Frameko, FramekoConfig

cfg = FramekoConfig.load_preset("default")
fk = Frameko(index_dir="/content/frameko_storage", config=cfg)

video_id = fk.ingest(
    "/content/How Alya fall in love with Kuze  Alya Sometimes Hides Her Feelings in Russian.mp4",
    detector="content",
    threshold=20.0,
    min_scene_len_frames=10,
    limit_scenes=None,   # set None if you want to collect all frame in video
    frames_per_scene=1
)

print("video_id:", video_id)
```

**Note:** `limit_scenes=None` means **no cap on the number of detected scenes** (i.e., process the whole video). Frameko still extracts **`frames_per_scene` frames per scene**, not *every frame in the video*.

### Outputs

Everything is written under your `index_dir`:

```
frameko_storage/
  frames/
    <video_id>_000000.jpg
    <video_id>_000001.jpg
    ...
  videos.jsonl
  frames.jsonl
  config.json
```

- `frames/`: extracted images
- `videos.jsonl`: one JSON line per ingested video (path + ffprobe info)
- `frames.jsonl`: one JSON line per extracted frame (timestamp, scene index, file path, dhash, blur score, ...)
- `config.json`: the config snapshot used for this run

---

## `ingest(...)` Parameters

```python
Frameko.ingest(
  video_path,
  frames_per_scene=None,
  detector=None,
  threshold=None,
  min_scene_len_frames=None,
  limit_scenes=None,
)
```

- **`video_path`**: path to the input video.
- **`frames_per_scene`**: `1` or `3`
  - `1` → one frame at the scene midpoint
  - `3` → start/mid/end (with a small epsilon offset from scene edges)
- **`detector`**:
  - `"content"` → cut detection based on content change between frames
  - `"adaptive"` → more adaptive version for dynamic content
  - `"none"` → skip detection (treat the whole video as one scene)
- **`threshold`**: detector sensitivity (lower can produce more cuts; higher can produce fewer cuts).
- **`min_scene_len_frames`**: minimum gap (in frames) between detected cuts.
- **`limit_scenes`**:
  - `None` → process all detected scenes
  - `int` → stop after N scenes (useful for quick testing)

---

## Configuration

Frameko uses a small config dataclass (`FramekoConfig`) and YAML presets in `src/frameko/presets/`:

- `default.yaml`
- `anime.yaml`
- `lecture.yaml`

Load a preset:

```python
cfg = FramekoConfig.load_preset("anime")
```

Some useful config fields:

- Scene detection:
  - `scene_detector`, `scene_threshold`, `min_scene_len_frames`
- Sampling:
  - `frames_per_scene`, `scene_edge_epsilon_sec`
- Dedup:
  - `enable_dedup`, `dhash_size`, `max_hamming`
- Blur filter:
  - `enable_blur_filter`, `blur_var_threshold`
- Extraction:
  - `image_format`, `jpeg_quality` (ffmpeg `-q:v`, lower is higher quality)

Example overrides:

```python
cfg = FramekoConfig.load_preset("default")
cfg.enable_dedup = False
cfg.enable_blur_filter = True
cfg.blur_var_threshold = 90.0
```

---

## Tuning Tips

- Too many scene cuts? Increase `threshold` or increase `min_scene_len_frames`.
- Too few scene cuts? Decrease `threshold`.
- Still getting very similar frames? Enable dedup and lower `max_hamming`.
- Want sharper frames only? Enable blur filter and raise `blur_var_threshold`.