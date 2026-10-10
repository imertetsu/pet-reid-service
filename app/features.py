"""Compute ResNet50 features once for every image in the manifest and cache them.

Usage: python -m app.features

ResNet50 is frozen, so its features do not change during training. Caching them
makes training the head take seconds on CPU. Training images are also cached
horizontally flipped, which is the only augmentation used.
"""

from __future__ import annotations

import json
import time

import numpy as np

from app import settings
from app.images import load_path
from app.model import build_backbone, extract_features

FEATURES_PATH = settings.ARTIFACTS_DIR / "features_resnet50.npz"


def load_manifest() -> list[dict]:
    return json.loads(settings.MANIFEST_PATH.read_text(encoding="utf-8"))["images"]


def load_features() -> dict[str, np.ndarray]:
    """Return {"paths", "features", "flipped"}; ``flipped`` rows are NaN outside train."""
    if not FEATURES_PATH.exists():
        raise SystemExit("Faltan las características. Ejecute: python -m app.features")
    with np.load(FEATURES_PATH) as cache:
        return {key: cache[key] for key in cache.files}


def main() -> None:
    records = load_manifest()
    backbone = build_backbone()
    paths = [r["path"] for r in records]
    features = np.zeros((len(records), 2048), dtype=np.float32)
    flipped = np.full((len(records), 2048), np.nan, dtype=np.float32)
    start = time.time()
    batch = 64
    for begin in range(0, len(records), batch):
        chunk = records[begin : begin + batch]
        images = np.stack([load_path(settings.DATA_DIR / r["path"]) for r in chunk])
        features[begin : begin + len(chunk)] = extract_features(backbone, images)
        is_train = np.array([r["split"] == "train" for r in chunk])
        if is_train.any():
            mirrored = images[is_train][:, :, ::-1, :]
            flipped[begin : begin + len(chunk)][is_train] = extract_features(backbone, mirrored)
        print(f"{begin + len(chunk)}/{len(records)} imágenes ({time.time() - start:.0f} s)")
    settings.ARTIFACTS_DIR.mkdir(exist_ok=True)
    np.savez_compressed(FEATURES_PATH, paths=np.array(paths), features=features, flipped=flipped)
    print(f"Guardado {FEATURES_PATH}")


if __name__ == "__main__":
    main()
