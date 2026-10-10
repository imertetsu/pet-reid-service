"""Demo gallery: the enrolled dogs of the test split, with fictitious
aliases, owners and collars.

Usage: python -m app.gallery   (writes artifacts/gallery.json + gallery.npz)

Raw ResNet50 features are stored, so the same gallery serves all methods.
"""

from __future__ import annotations

import json
import random

import numpy as np

from app import settings
from app.features import FEATURES_PATH, load_manifest

GALLERY_JSON = settings.ARTIFACTS_DIR / "gallery.json"
GALLERY_NPZ = settings.ARTIFACTS_DIR / "gallery.npz"

DOG_NAMES = [
    "Luna", "Toby", "Rocky", "Max", "Kira", "Nala", "Bruno", "Lola", "Simba", "Coco",
    "Thor", "Maya", "Zeus", "Canela", "Rufo", "Frida", "Oso", "Mia", "Chispa", "Lucas",
    "Bella", "Duke", "Pelusa", "Tango", "Sasha", "Bobby", "Nina", "Rex", "Kiara", "Pancho",
    "Lia", "Milo", "Dana", "Fito", "Greta", "Hugo", "Iris", "Jack", "Kaiser", "Lupe",
]
OWNER_NAMES = [
    "Ana R.", "Carlos M.", "Lucía P.", "Jorge V.", "María T.", "Diego S.", "Valeria Q.",
    "Andrés L.", "Paola G.", "Fernando C.", "Camila A.", "Rodrigo F.", "Daniela H.",
]


def device_id_for(number: int, alias: str) -> str:
    """Same format as the thesis seed data, e.g. GPS-001-LUNA."""
    return f"GPS-{number:03d}-{alias.upper()}"


def build() -> None:
    records = load_manifest()
    gallery = [r for r in records if r["role"] == "gallery" and r["split"] == "test"]
    paths = [r["path"] for r in gallery]

    if FEATURES_PATH.exists():
        with np.load(FEATURES_PATH) as cache:
            index = {p: i for i, p in enumerate(cache["paths"])}
            features = cache["features"][[index[p] for p in paths]]
    else:
        from app.images import load_path
        from app.model import build_backbone, extract_features

        images = np.stack([load_path(settings.DATA_DIR / p) for p in paths])
        features = extract_features(build_backbone(), images)

    rng = random.Random(settings.SEED)
    pets, seen = [], {}
    for record in gallery:
        identity = record["identity"]
        if identity not in seen:
            number = len(seen) + 1
            alias = f"{rng.choice(DOG_NAMES)}"
            seen[identity] = {
                "id": identity,
                "alias": alias,
                "owner": rng.choice(OWNER_NAMES),
                "device_id": device_id_for(number, alias),
                "source": "DogFaceNet",
                "photos": [],
            }
            pets.append(seen[identity])
        seen[identity]["photos"].append(record["path"])

    GALLERY_JSON.write_text(json.dumps({"pets": pets}, indent=1, ensure_ascii=False), encoding="utf-8")
    np.savez_compressed(
        GALLERY_NPZ,
        paths=np.array(paths),
        identities=np.array([r["identity"] for r in gallery]),
        features=features.astype(np.float32),
    )
    print(f"Galería: {len(pets)} mascotas, {len(paths)} fotos -> {GALLERY_JSON.name}")


if __name__ == "__main__":
    build()
