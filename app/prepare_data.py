"""Build the dataset: verify, deduplicate, select and split DogFaceNet by identity.

Usage:
    python -m app.prepare_data --archive path/to/DogFaceNet_224resized.zip
    python -m app.prepare_data --download

Output:
    data/images/<split>/<identity>/<file>   selected images (original bytes)
    data/manifest.json                      one record per image (split and role)
    data/dataset_info.json                  source, license and selection statistics

Roles: ``train`` images build training pairs. In ``val``/``test`` an
enrolled identity puts its first photos in the ``gallery`` and the rest are
``query``; a non-enrolled identity only has ``query`` photos, which the system
should reject.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import shutil
import ssl
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

from app import settings

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")
POPCOUNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def md5_of(path: Path) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_archive(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Descargando {settings.DOGFACENET_URL} ...")
    # Use the OS trust store so HTTPS inspection by local antivirus does not break it
    context = ssl.create_default_context()
    with urllib.request.urlopen(settings.DOGFACENET_URL, context=context) as response:
        with open(target, "wb") as handle:
            shutil.copyfileobj(response, handle)


def dhash(data: bytes) -> int:
    """64-bit difference hash, robust to re-encoding and small resizes."""
    with Image.open(io.BytesIO(data)) as image:
        small = np.asarray(image.convert("L").resize((9, 8), Image.Resampling.BILINEAR))
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pairwise Hamming distances between two uint64 hash vectors."""
    xor = np.bitwise_xor(a[:, None], b[None, :])
    return POPCOUNT[xor.view(np.uint8)].reshape(*xor.shape, 8).sum(axis=-1)


def read_archive(path: Path) -> dict[str, list[tuple[str, bytes]]]:
    """Group archive images by identity folder (the parent directory name)."""
    groups: dict[str, list[tuple[str, bytes]]] = defaultdict(list)
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith(IMAGE_SUFFIXES):
                continue
            parts = name.split("/")
            groups[parts[-2]].append((name, archive.read(name)))
    return groups


def find_conflicting_identities(groups, near_bits: int = 2) -> set[str]:
    """Identities sharing an (almost) identical photo with another identity."""
    owners, hashes = [], []
    for identity, files in groups.items():
        for _, data in files:
            owners.append(identity)
            hashes.append(dhash(data))
    owners_arr = np.array(owners)
    hashes_arr = np.array(hashes, dtype=np.uint64)
    conflicts: set[str] = set()
    chunk = 512
    for start in range(0, len(hashes_arr), chunk):
        dist = hamming_matrix(hashes_arr[start : start + chunk], hashes_arr)
        rows, cols = np.nonzero(dist <= near_bits)
        for r, c in zip(rows + start, cols):
            if owners_arr[r] != owners_arr[c]:
                conflicts.update((owners_arr[r], owners_arr[c]))
    return conflicts


def deduplicate(files: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    """Drop exact and near-duplicate photos inside one identity (keeps the first)."""
    kept, seen_sha, kept_hashes = [], set(), []
    for name, data in sorted(files):
        sha = hashlib.sha256(data).hexdigest()
        if sha in seen_sha:
            continue
        h = dhash(data)
        if kept_hashes:
            dist = hamming_matrix(np.array([h], np.uint64), np.array(kept_hashes, np.uint64))
            if dist.min() <= settings.NEAR_DUPLICATE_MAX_BITS:
                continue
        seen_sha.add(sha)
        kept_hashes.append(h)
        kept.append((name, data))
    return kept


def split_identities(identities: list[str], rng: random.Random) -> dict[str, list[str]]:
    shuffled = sorted(identities)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = round(n * settings.SPLIT_FRACTIONS["train"])
    n_val = round(n * settings.SPLIT_FRACTIONS["val"])
    return {
        "train": shuffled[:n_train],
        "val": shuffled[n_train : n_train + n_val],
        "test": shuffled[n_train + n_val :],
    }


def assign_roles(split: str, identities: list[str], rng: random.Random) -> dict[str, bool]:
    """Return identity -> enrolled flag. Train identities are not part of any gallery."""
    if split == "train":
        return {identity: False for identity in identities}
    order = sorted(identities)
    rng.shuffle(order)
    n_enrolled = round(len(order) * settings.REGISTERED_FRACTION)
    return {identity: i < n_enrolled for i, identity in enumerate(order)}


def image_role(split: str, enrolled: bool, index: int) -> str:
    if split == "train":
        return "train"
    if enrolled and index < settings.GALLERY_PHOTOS_PER_IDENTITY:
        return "gallery"
    return "query"


def write_split(split, selected, rng, records, source: str):
    enrolled_map = assign_roles(split, list(selected), rng)
    for identity in sorted(selected):
        enrolled = enrolled_map[identity]
        for index, (original_name, data) in enumerate(selected[identity]):
            suffix = Path(original_name).suffix.lower()
            relative = Path("images") / split / identity / f"{index:02d}{suffix}"
            target = settings.DATA_DIR / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            records.append(
                {
                    "path": relative.as_posix(),
                    "identity": identity,
                    "split": split,
                    "role": image_role(split, enrolled, index),
                    "enrolled": enrolled,
                    "source": source,
                    "original_file": original_name,
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--archive", type=Path, default=settings.DOGFACENET_ARCHIVE)
    parser.add_argument("--download", action="store_true", help="descargar desde Zenodo")
    args = parser.parse_args()

    if not args.archive.exists():
        if not args.download:
            raise SystemExit(f"No existe {args.archive}. Use --download o --archive.")
        download_archive(args.archive)
    checksum = md5_of(args.archive)
    if checksum != settings.DOGFACENET_MD5:
        raise SystemExit(f"Checksum MD5 inesperado: {checksum}")
    print("Checksum MD5 verificado.")

    rng = random.Random(settings.SEED)
    groups = read_archive(args.archive)
    n_images_raw = sum(len(v) for v in groups.values())
    print(f"Archivo: {len(groups)} identidades, {n_images_raw} imágenes.")

    conflicts = find_conflicting_identities(groups)
    deduped = {k: deduplicate(v) for k, v in groups.items() if k not in conflicts}
    n_removed_dups = sum(len(groups[k]) - len(v) for k, v in deduped.items())
    eligible = {
        k: v for k, v in deduped.items() if len(v) >= settings.MIN_PHOTOS_PER_IDENTITY
    }
    print(
        f"Conflictos entre identidades: {len(conflicts)} | duplicados internos: "
        f"{n_removed_dups} | identidades con >= {settings.MIN_PHOTOS_PER_IDENTITY} fotos: "
        f"{len(eligible)}"
    )

    splits = split_identities(list(eligible), rng)
    for folder in ("train", "val", "test"):
        shutil.rmtree(settings.IMAGES_DIR / folder, ignore_errors=True)

    records: list[dict] = []
    for split, identities in splits.items():
        selected = {}
        for identity in identities:
            files = list(eligible[identity])
            rng.shuffle(files)
            selected[f"dfn_{int(identity):04d}"] = files[: settings.MAX_PHOTOS_PER_IDENTITY]
        write_split(split, selected, rng, records, source="DogFaceNet_224resized")

    summary = defaultdict(lambda: defaultdict(int))
    identities_per_split = defaultdict(set)
    enrolled_per_split = defaultdict(set)
    for record in records:
        summary[record["split"]][record["role"]] += 1
        identities_per_split[record["split"]].add(record["identity"])
        if record["enrolled"]:
            enrolled_per_split[record["split"]].add(record["identity"])

    info = {
        "source": {
            "name": "DogFaceNet_224resized",
            "authors": "Mougeot, G., Li, D. & Jia, S. (2019)",
            "doi": "10.5281/zenodo.12578449",
            "license": "CC BY 4.0",
            "md5": checksum,
        },
        "seed": settings.SEED,
        "raw": {"identities": len(groups), "images": n_images_raw},
        "filtering": {
            "conflicting_identities_removed": len(conflicts),
            "duplicate_images_removed": n_removed_dups,
            "min_photos_per_identity": settings.MIN_PHOTOS_PER_IDENTITY,
            "max_photos_per_identity": settings.MAX_PHOTOS_PER_IDENTITY,
            "eligible_identities": len(eligible),
        },
        "splits": {
            split: {
                "identities": len(identities_per_split[split]),
                "enrolled_identities": len(enrolled_per_split[split]),
                "images": sum(roles.values()),
                "roles": dict(roles),
            }
            for split, roles in summary.items()
        },
    }
    settings.MANIFEST_PATH.write_text(
        json.dumps({"seed": settings.SEED, "images": records}, indent=1), encoding="utf-8"
    )
    settings.DATASET_INFO_PATH.write_text(
        json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(info["splits"], indent=2))


if __name__ == "__main__":
    main()
