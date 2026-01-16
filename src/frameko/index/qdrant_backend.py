from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..errors import DependencyMissingError
from .base import VectorBackend


class QdrantBackend(VectorBackend):
    """Qdrant backend (optional).

    This is a minimal implementation for local or remote Qdrant.
    Payloads are stored in Qdrant to enable filtering.
    """

    def __init__(
        self,
        collection: str = "frameko",
        url: Optional[str] = None,
        host: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        dim: Optional[int] = None,
        distance: str = "Cosine",
    ) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models as rest
        except Exception as e:
            raise DependencyMissingError("Qdrant requires extras: pip install -e '.[qdrant]'") from e

        self.rest = rest
        self.collection = collection
        self._dim = dim
        self.client = QdrantClient(url=url, host=host, port=port, api_key=api_key)

        # Create collection lazily when dim known
        if dim is not None:
            self._ensure_collection(dim=dim, distance=distance)

    def _ensure_collection(self, dim: int, distance: str = "Cosine") -> None:
        self._dim = int(dim)
        try:
            self.client.get_collection(self.collection)
            return
        except Exception:
            pass

        dist = getattr(self.rest.Distance, distance)
        self.client.recreate_collection(
            collection_name=self.collection,
            vectors_config=self.rest.VectorParams(size=self._dim, distance=dist),
        )

    def upsert(self, ids: np.ndarray, vectors: np.ndarray, payloads: List[Dict[str, Any]]) -> None:
        vectors = np.asarray(vectors, dtype=np.float32)
        ids = np.asarray(ids, dtype=np.int64)
        if self._dim is None:
            self._ensure_collection(dim=vectors.shape[1])

        points = []
        for i, pid in enumerate(ids.tolist()):
            points.append(self.rest.PointStruct(id=int(pid), vector=vectors[i].tolist(), payload=payloads[i]))

        self.client.upsert(collection_name=self.collection, points=points)

    def search(
        self, query_vec: np.ndarray, topk: int = 20, where: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        q = np.asarray(query_vec, dtype=np.float32).tolist()

        qfilter = None
        if where:
            must = []
            for k, v in where.items():
                must.append(self.rest.FieldCondition(key=k, match=self.rest.MatchValue(value=v)))
            qfilter = self.rest.Filter(must=must)

        hits = self.client.search(
            collection_name=self.collection,
            query_vector=q,
            limit=int(topk),
            query_filter=qfilter,
        )

        ids = np.array([h.id for h in hits], dtype=np.int64)
        scores = np.array([h.score for h in hits], dtype=np.float32)
        return ids, scores

    def save(self) -> None:
        # Qdrant persists itself
        return

    def close(self) -> None:
        return
