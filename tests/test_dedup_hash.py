from pathlib import Path

import numpy as np
from PIL import Image

from frameko.pipelines.dedup import dhash_uint64, hamming_distance


def test_dhash_and_hamming(tmp_path: Path):
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"

    Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8)).save(a)
    img = np.zeros((32, 32, 3), dtype=np.uint8)
    img[:, 16:] = 255
    Image.fromarray(img).save(b)

    ha = dhash_uint64(a)
    hb = dhash_uint64(b)
    assert isinstance(ha, int)
    assert isinstance(hb, int)
    assert hamming_distance(ha, hb) >= 1
