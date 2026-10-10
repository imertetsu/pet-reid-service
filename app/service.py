"""Inference service: loads the real model and answers identify / register requests."""

from __future__ import annotations

import json
import threading
import time
import uuid

import numpy as np

from app import metrics, settings
from app.gallery import GALLERY_JSON, GALLERY_NPZ
from app.images import ImageValidationError, load_image, to_array
from app.evaluate import load_trained
from app.model import build_backbone, embed, extract_features
from app.telemetry import Telemetry
from app.train import CALIBRATION_PATH, HEAD_WEIGHTS_PATH, METHODS, PROJECTION_PATH

METHOD_LABELS = {
    "baseline": "ResNet50 base (línea base, sin entrenar)",
    "siamese": "ResNet50 + cabeza siamesa (contrastiva)",
    "pca_lda": "ResNet50 + PCA + LDA",
}
TOP_K = 3
RUNTIME_PETS = settings.RUNTIME_DIR / "pets.json"
RUNTIME_PHOTOS = settings.RUNTIME_DIR / "photos"
RUNTIME_FEATURES = settings.RUNTIME_DIR / "features"


class ReidService:
    def __init__(self):
        for path in (CALIBRATION_PATH, HEAD_WEIGHTS_PATH, PROJECTION_PATH, GALLERY_JSON, GALLERY_NPZ):
            if not path.exists():
                raise RuntimeError(f"Falta el artefacto {path.name}. Revise el README.")
        self.calibration = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
        self.trained = load_trained(self.calibration)
        self.backbone = build_backbone()
        self.telemetry = Telemetry(seed=settings.SEED)
        self._lock = threading.Lock()

        self.pets: dict[str, dict] = {}
        self._photo_paths: list[str] = []  # one entry per gallery photo
        self._photo_owner: list[str] = []
        self._features = np.zeros((0, 2048), dtype=np.float32)
        self._embeddings: dict[str, np.ndarray] = {}

        dataset = json.loads(GALLERY_JSON.read_text(encoding="utf-8"))["pets"]
        with np.load(GALLERY_NPZ) as cache:
            feature_by_path = dict(zip(cache["paths"], cache["features"]))
        for pet in dataset:
            photos = [f"/media/data/{p}" for p in pet["photos"]]
            feats = np.stack([feature_by_path[p] for p in pet["photos"]])
            self._add_pet({**pet, "photos": photos, "registered_in_demo": False}, feats)
        self._load_runtime_pets()
        self._warm_up()

    def _warm_up(self) -> None:
        """Run the model once at startup so the first real request is not slow."""
        blank = np.zeros((1, settings.IMAGE_SIZE, settings.IMAGE_SIZE, 3), dtype=np.float32)
        features = extract_features(self.backbone, blank)
        for method in METHODS:
            embed(method, features, self.trained)
            self._gallery_embeddings(method)

    # ---- gallery -------------------------------------------------------
    def _add_pet(self, pet: dict, features: np.ndarray) -> None:
        self.pets[pet["id"]] = pet
        self._photo_paths.extend(pet["photos"])
        self._photo_owner.extend([pet["id"]] * len(pet["photos"]))
        self._features = np.vstack([self._features, features.astype(np.float32)])
        self.telemetry.register(pet["device_id"])
        self._embeddings.clear()

    def _gallery_embeddings(self, method: str) -> np.ndarray:
        if method not in self._embeddings:
            self._embeddings[method] = embed(method, self._features, self.trained)
        return self._embeddings[method]

    def _load_runtime_pets(self) -> None:
        if not RUNTIME_PETS.exists():
            return
        for pet in json.loads(RUNTIME_PETS.read_text(encoding="utf-8")):
            feats_path = RUNTIME_FEATURES / f"{pet['id']}.npy"
            if feats_path.exists():
                self._add_pet(pet, np.load(feats_path))

    def _save_runtime_pets(self) -> None:
        settings.RUNTIME_DIR.mkdir(exist_ok=True)
        registered = [p for p in self.pets.values() if p["registered_in_demo"]]
        RUNTIME_PETS.write_text(json.dumps(registered, indent=1, ensure_ascii=False), encoding="utf-8")

    def public_pet(self, pet_id: str) -> dict:
        pet = self.pets[pet_id]
        return {**pet, "location": self.telemetry.last(pet["device_id"])}

    def list_pets(self) -> list[dict]:
        return [self.public_pet(pet_id) for pet_id in self.pets]

    # ---- inference -----------------------------------------------------
    def _features_of(self, data: bytes) -> np.ndarray:
        image = load_image(data)
        return extract_features(self.backbone, to_array(image)[None])

    def identify(self, data: bytes, method: str | None = None) -> dict:
        method = method or self.calibration["selected_method"]
        if method not in METHODS:
            raise ImageValidationError(f"Método desconocido: {method}. Use baseline, siamese o pca_lda.")
        start = time.perf_counter()
        with self._lock:
            query = embed(method, self._features_of(data), self.trained)
            gallery = self._gallery_embeddings(method)
            ranked_ids, ranked_dist = metrics.rank(query, gallery, self._photo_owner)
        threshold = self.calibration["methods"][method]["threshold"]
        candidates = []
        for pet_id, distance in zip(ranked_ids[0, :TOP_K], ranked_dist[0, :TOP_K]):
            pet = self.pets[str(pet_id)]
            candidates.append(
                {
                    "pet_id": pet["id"],
                    "alias": pet["alias"],
                    "owner": pet["owner"],
                    "photo": pet["photos"][0],
                    "source": pet["source"],
                    "distance": round(float(distance), 4),
                    "below_threshold": bool(distance <= threshold),
                }
            )
        accepted = candidates[0]["below_threshold"]
        return {
            "method": method,
            "method_label": METHOD_LABELS[method],
            "threshold": round(threshold, 4),
            "accepted": accepted,
            "match": self.public_pet(candidates[0]["pet_id"]) if accepted else None,
            "candidates": candidates,
            "gallery_size": len(self.pets),
            "elapsed_ms": round((time.perf_counter() - start) * 1000),
        }

    def register(self, alias: str, owner: str, photos: list[bytes]) -> dict:
        alias, owner = alias.strip(), owner.strip()
        if not 1 <= len(alias) <= 30 or not 1 <= len(owner) <= 40:
            raise ImageValidationError("El nombre (1-30) y el dueño (1-40 caracteres) son obligatorios.")
        if not 2 <= len(photos) <= 4:
            raise ImageValidationError("Suba entre 2 y 4 fotos de la mascota.")
        images = [load_image(data) for data in photos]  # validate all before saving anything
        with self._lock:
            arrays = np.stack([to_array(image) for image in images])
            features = extract_features(self.backbone, arrays)
            pet_id = f"reg_{uuid.uuid4().hex[:8]}"
            RUNTIME_PHOTOS.mkdir(parents=True, exist_ok=True)
            RUNTIME_FEATURES.mkdir(parents=True, exist_ok=True)
            urls = []
            for n, image in enumerate(images):
                name = f"{pet_id}_{n}.jpg"
                image.thumbnail((640, 640))
                image.save(RUNTIME_PHOTOS / name, format="JPEG", quality=90)
                urls.append(f"/media/runtime/{name}")
            np.save(RUNTIME_FEATURES / f"{pet_id}.npy", features)
            number = sum(1 for p in self.pets.values() if p["registered_in_demo"]) + 1
            safe_alias = "".join(c for c in alias.upper() if c.isalnum())[:12] or "PET"
            pet = {
                "id": pet_id,
                "alias": alias,
                "owner": owner,
                "device_id": f"GPS-R{number:02d}-{safe_alias}",
                "source": "registrado en la demo",
                "photos": urls,
                "registered_in_demo": True,
            }
            self._add_pet(pet, features)
            self._save_runtime_pets()
        return self.public_pet(pet_id)

    def delete(self, pet_id: str) -> None:
        with self._lock:
            pet = self.pets.get(pet_id)
            if pet is None:
                raise KeyError(pet_id)
            if not pet["registered_in_demo"]:
                raise PermissionError("Solo se pueden eliminar mascotas registradas en la demo.")
            keep = [i for i, owner in enumerate(self._photo_owner) if owner != pet_id]
            self._features = self._features[keep]
            self._photo_paths = [self._photo_paths[i] for i in keep]
            self._photo_owner = [self._photo_owner[i] for i in keep]
            self._embeddings.clear()
            del self.pets[pet_id]
            self.telemetry.remove(pet["device_id"])
            for path in RUNTIME_PHOTOS.glob(f"{pet_id}_*.jpg"):
                path.unlink()
            (RUNTIME_FEATURES / f"{pet_id}.npy").unlink(missing_ok=True)
            self._save_runtime_pets()

    def ping(self, pet_id: str) -> dict:
        pet = self.pets.get(pet_id)
        if pet is None:
            raise KeyError(pet_id)
        return self.telemetry.ping(pet["device_id"])
