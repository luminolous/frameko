from frameko import Frameko

fk = Frameko(index_dir="store", backend="faiss", preset="default")
video_id = fk.ingest("./your_video.mp4")
print("video_id:", video_id)

hits = hits = fk.search_image("store/frames/some_frame.jpg", topk=8)
for h in hits:
    print(h.score, h.t_sec, h.frame_path)

fk.close()
