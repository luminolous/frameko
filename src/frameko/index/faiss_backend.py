from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..errors import DependencyMissingError
from .base import VectorBackend


class FaissBackend(VectorBackend):
    """FAISS backend using IndexIDMap2(IndexFlatIP).

    Notes:
      - If vectors are L2-normalized, IP corresponds to cosine similarity.
      - This backend stores only vectors+ids. Payloads are expected to live in SQLite.
    """

    def __init__(self, index_path: Path, dim: Optional[int] = None) -> None:
        self.index_path = Path(index_path)
        self._dim = dim
        self._index = None

        try:
            import faiss
        except Exception as e:
            raise DependencyMissingError("FAISS requires extras: pip install -e '.[faiss]'") from e
        self.faiss = faiss

        if self.index_path.exists():
            self._index = faiss.read_index(str(self.index_path))
            self._dim = self._index.d

    @property
    def dim(self) -> int:
        if self._dim is None:
            raise ValueError("FAISS dim is not set yet. Upsert at least once.")
        return int(self._dim)

    def _ensure_index(self, dim: int) -> None:
        if self._index is not None:
            return
        self._dim = int(dim)
        base = self.faiss.IndexFlatIP(self._dim)
        self._index = self.faiss.IndexIDMap2(base)

    def upsert(self, ids: np.ndarray, vectors: np.ndarray, payloads: List[Dict[str, Any]]) -> None:
        vectors = np.asarray(vectors, dtype=np.float32)
        ids = np.asarray(ids, dtype=np.int64)
        if vectors.ndim != 2:
            raise ValueError("vectors must be 2D")
        self._ensure_index(vectors.shape[1])

        # Remove existing IDs if present (best-effort)
        try:
            self._index.remove_ids(ids)
        except Exception:
            pass

        self._index.add_with_ids(vectors, ids)

    def search(
        self, query_vec: np.ndarray, topk: int = 20, where: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        if self._index is None:
            return np.array([], dtype=np.int64), np.array([], dtype=np.float32)

        q = np.asarray(query_vec, dtype=np.float32)
        if q.ndim == 1:
            q = q[None, :]

        scores, ids = self._index.search(q, int(topk))
        ids = ids[0]
        scores = scores[0]

        # FAISS doesn't do metadata filtering here.
        # If user passes `where`, caller can post-filter; for MVP we ignore.
        mask = ids != -1
        return ids[mask].astype(np.int64), scores[mask].astype(np.float32)

    def save(self) -> None:
        if self._index is None:
            return
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.faiss.write_index(self._index, str(self.index_path))

    def close(self) -> None:
        # Nothing special
        return
