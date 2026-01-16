"""frameko: video → frames → embeddings → vector search (notebook-first)."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .core import Frameko

try:
    __version__ = version("frameko")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["Frameko", "__version__"]