from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np


class VectorBackend(ABC):
    @abstractmethod
    def upsert(self, ids: np.ndarray, vectors: np.ndarray, payloads: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self, query_vec: np.ndarray, topk: int = 20, where: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError

    @abstractmethod
    def save(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
