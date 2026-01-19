from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Sequence, Union

import numpy as np

from ..errors import DependencyMissingError


class OpenCLIPEmbedder:
    def __init__(
        self,
        model_name: str = "ViT-B-32",
        pretrained: str = "laion2b_s34b_b79k",
        device: str = "cpu",
        normalize: bool = True,
        batch_size: int = 32,
    ) -> None:
        try:
            import torch
            import open_clip
            from PIL import Image
        except Exception as e:
            raise DependencyMissingError(
                "OpenCLIP embedding requires extras: pip install -e '.[clip]'"
            ) from e

        self.torch = torch
        self.open_clip = open_clip
        self.Image = Image

        self.device = device
        self.normalize = normalize
        self.batch_size = int(batch_size)

        model, _, preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained
        )

        self.model = model.to(device)
        self.model.eval()
        self.preprocess = preprocess

    def _l2norm(self, x: np.ndarray) -> np.ndarray:
        eps = 1e-12
        n = np.linalg.norm(x, axis=-1, keepdims=True)
        return x / (n + eps)

    def encode_images(self, images: Sequence[Union[str, Path]]) -> np.ndarray:
        torch = self.torch
        out: List[np.ndarray] = []

        for i in range(0, len(images), self.batch_size):
            batch = images[i : i + self.batch_size]
            tensors = []
            for p in batch:
                with self.Image.open(str(p)) as im:
                    im = im.convert("RGB")
                    tensors.append(self.preprocess(im))
            x = torch.stack(tensors).to(self.device)
            with torch.no_grad():
                feats = self.model.encode_image(x)
            feats = feats.detach().cpu().numpy().astype(np.float32)
            if self.normalize:
                feats = self._l2norm(feats)
            out.append(feats)

        return np.concatenate(out, axis=0)
