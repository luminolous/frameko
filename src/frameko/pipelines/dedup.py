from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image


def dhash_uint64(image_path: Union[str, Path], hash_size: int = 8) -> int:
    """Compute difference-hash (dHash) as uint64 integer.

    Steps:
      1) Convert to grayscale
      2) Resize to (hash_size+1, hash_size)
      3) Compare adjacent pixels

    Returns an integer bitset.
    """
    image_path = Path(image_path)
    with Image.open(image_path) as im:
        im = im.convert("L").resize((hash_size + 1, hash_size))
        arr = np.asarray(im, dtype=np.int16)

    diff = arr[:, 1:] > arr[:, :-1]
    bits = diff.flatten()

    # Pack into integer (little-endian bit order)
    h = 0
    for i, b in enumerate(bits.tolist()):
        if b:
            h |= 1 << i
    return int(h)


def hamming_distance(a: int, b: int) -> int:
    return int((a ^ b).bit_count())
