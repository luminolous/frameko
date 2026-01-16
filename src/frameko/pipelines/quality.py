from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image


def variance_of_laplacian(image_path: Union[str, Path]) -> float:
    """Simple blur detector: variance of Laplacian (no OpenCV required).

    Higher variance => sharper.
    """
    image_path = Path(image_path)
    with Image.open(image_path) as im:
        gray = im.convert("L")
        arr = np.asarray(gray, dtype=np.float32)

    # Laplacian kernel
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)

    # Convolution (valid padding via manual padding)
    padded = np.pad(arr, ((1, 1), (1, 1)), mode="edge")
    out = (
        k[0, 0] * padded[:-2, :-2]
        + k[0, 1] * padded[:-2, 1:-1]
        + k[0, 2] * padded[:-2, 2:]
        + k[1, 0] * padded[1:-1, :-2]
        + k[1, 1] * padded[1:-1, 1:-1]
        + k[1, 2] * padded[1:-1, 2:]
        + k[2, 0] * padded[2:, :-2]
        + k[2, 1] * padded[2:, 1:-1]
        + k[2, 2] * padded[2:, 2:]
    )

    return float(out.var())
