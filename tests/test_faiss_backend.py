import numpy as np
import pytest

from frameko.index.faiss_backend import FaissBackend


def test_faiss_add_and_search(tmp_path):
    faiss = pytest.importorskip("faiss")

    idx_path = tmp_path / "faiss.index"
    b = FaissBackend(idx_path)

    rng = np.random.default_rng(0)
    vecs = rng.normal(size=(100, 32)).astype(np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12

    ids = np.arange(100, dtype=np.int64)
    b.upsert(ids, vecs, payloads=[{} for _ in range(100)])

    q = vecs[0]
    out_ids, scores = b.search(q, topk=5)

    assert out_ids[0] == 0
    assert scores.shape[0] <= 5

    b.save()
    assert idx_path.exists()
