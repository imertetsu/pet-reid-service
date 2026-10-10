"""Train the methods on cached ResNet50 features and calibrate their thresholds.

Usage: python -m app.train

- siamese: Dense -> L2 head trained with contrastive loss (small grid).
- pca_lda: PCA (512) + Linear Discriminant Analysis (small grid).
- baseline: nothing to train; only its threshold is calibrated.

Only ``train`` (fitting) and ``val`` (model selection and thresholds) are used.
The test split is not read here.
"""

from __future__ import annotations

import json
import platform
import random
import time

import numpy as np
import sklearn
import tensorflow as tf
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from tensorflow import keras

from app import settings
from app.features import load_features, load_manifest
from app.model import BACKBONE_INFO, build_head, build_siamese, contrastive_loss, embed, l2_normalize
from app.protocol import evaluate_view, split_view

HEAD_WEIGHTS_PATH = settings.ARTIFACTS_DIR / "siamese_head.weights.h5"
PROJECTION_PATH = settings.ARTIFACTS_DIR / "pca_lda.npz"
CALIBRATION_PATH = settings.ARTIFACTS_DIR / "calibration.json"
TRAINING_PATH = settings.ARTIFACTS_DIR / "training.json"

METHODS = ("baseline", "siamese", "pca_lda")

SIAMESE_GRID = [
    {"embedding_dim": dim, "activation": activation, "margin": 0.5}
    for dim in (128, 256)
    for activation in ("relu", None)
]
MAX_EPOCHS = 30
PATIENCE = 8
BATCH_SIZE = 64
LEARNING_RATE = 1e-4

PCA_COMPONENTS = 512
LDA_GRID = [
    {"lda_components": k, "shrinkage": shrinkage}
    for k in (64, 128, 256)
    for shrinkage in (None, "auto")
]


def make_pairs(train_idx, train_ids, features, flipped, rng: np.random.Generator):
    """One positive and one negative pair per training image, resampled every epoch.
    Each side is randomly taken from the original or the flipped image."""
    by_identity: dict[str, list[int]] = {}
    for i, identity in zip(train_idx, train_ids):
        by_identity.setdefault(identity, []).append(i)
    identities = list(by_identity)
    left, right, labels = [], [], []
    for i, identity in zip(train_idx, train_ids):
        same = [j for j in by_identity[identity] if j != i]
        left.append(i)
        right.append(rng.choice(same))
        labels.append(1.0)
        other = identities[rng.integers(len(identities))]
        while other == identity:
            other = identities[rng.integers(len(identities))]
        left.append(i)
        right.append(rng.choice(by_identity[other]))
        labels.append(0.0)

    def pick(indices):
        use_flip = rng.random(len(indices)) < 0.5
        return np.where(use_flip[:, None], flipped[indices], features[indices])

    return pick(np.array(left)), pick(np.array(right)), np.array(labels, dtype=np.float32)


def train_siamese(config, data, val_view):
    keras.utils.set_random_seed(settings.SEED)
    rng = np.random.default_rng(settings.SEED)
    head = build_head(config["embedding_dim"], config["activation"])
    siamese = build_siamese(head)
    siamese.compile(
        optimizer=keras.optimizers.Adam(LEARNING_RATE),
        loss=contrastive_loss(config["margin"]),
    )
    best = {"top1": -1.0}
    best_weights = None
    history = []
    stale = 0
    for epoch in range(1, MAX_EPOCHS + 1):
        a, b, y = make_pairs(data["train_idx"], data["train_ids"], data["features"], data["flipped"], rng)
        fit = siamese.fit([a, b], y, batch_size=BATCH_SIZE, epochs=1, shuffle=True, verbose=0)
        result, _, _ = evaluate_view(val_view, embed("siamese", data["features"], {"head": head}))
        top1 = result["retrieval"]["top1"]
        history.append(
            {
                "epoch": epoch,
                "loss": float(fit.history["loss"][0]),
                "val_top1": top1,
                "val_identification_rate": result["retrieval"]["identification_rate"],
                "val_roc_auc": result["verification"]["roc_auc"],
            }
        )
        if top1 > best["top1"]:
            best = {"top1": top1, "epoch": epoch, "metrics": result}
            best_weights = head.get_weights()
            stale = 0
        else:
            stale += 1
            if stale >= PATIENCE:
                break
    head.set_weights(best_weights)
    return head, best, history


def fit_pca_lda(config, data):
    """Fit PCA + LDA on training features (original + flipped) and return the
    equivalent affine map (W, b) so inference needs only NumPy."""
    idx = data["train_idx"]
    x = np.vstack([l2_normalize(data["features"][idx]), l2_normalize(data["flipped"][idx])])
    y = np.concatenate([data["train_ids"], data["train_ids"]])
    pca = PCA(PCA_COMPONENTS, random_state=settings.SEED).fit(x)
    solver = "eigen" if config["shrinkage"] else "svd"
    lda = LinearDiscriminantAnalysis(
        n_components=config["lda_components"], solver=solver, shrinkage=config["shrinkage"]
    ).fit(pca.transform(x), y)

    def transform(z):
        return lda.transform(pca.transform(z))

    bias = transform(np.zeros((1, x.shape[1])))
    weights = transform(np.eye(x.shape[1])) - bias
    assert np.allclose(transform(x[:5]), x[:5] @ weights + bias, atol=1e-4)
    return weights.astype(np.float32), bias.astype(np.float32)


def main() -> None:
    random.seed(settings.SEED)
    records = load_manifest()
    cache = load_features()
    assert list(cache["paths"]) == [r["path"] for r in records], "Cache desactualizada"
    train_idx = np.array([i for i, r in enumerate(records) if r["split"] == "train"])
    data = {
        "features": cache["features"],
        "flipped": cache["flipped"],
        "train_idx": train_idx,
        "train_ids": [records[i]["identity"] for i in train_idx],
    }
    val_view = split_view(records, "val")
    val_metrics = {}

    val_metrics["baseline"], _, _ = evaluate_view(val_view, embed("baseline", data["features"]))
    print(f"baseline: Top-1 val {val_metrics['baseline']['retrieval']['top1']:.3f}")

    # ---- siamese head ----
    siamese_runs, best_siamese = [], None
    for config in SIAMESE_GRID:
        start = time.time()
        head, best, history = train_siamese(config, data, val_view)
        run = {
            "config": config,
            "best_epoch": best["epoch"],
            "epochs_run": len(history),
            "val_top1": best["top1"],
            "val_identification_rate": best["metrics"]["retrieval"]["identification_rate"],
            "seconds": round(time.time() - start, 1),
            "history": history,
        }
        siamese_runs.append(run)
        print(f"siamese {config} -> Top-1 val {best['top1']:.3f} (época {best['epoch']}, {run['seconds']} s)")
        key = (run["val_top1"], run["val_identification_rate"])
        if best_siamese is None or key > best_siamese["key"]:
            best_siamese = {"key": key, "run": run, "head": head, "metrics": best["metrics"]}
    best_siamese["head"].save_weights(HEAD_WEIGHTS_PATH)
    val_metrics["siamese"] = best_siamese["metrics"]

    # ---- PCA + LDA ----
    lda_runs, best_lda = [], None
    for config in LDA_GRID:
        projection = fit_pca_lda(config, data)
        result, _, _ = evaluate_view(val_view, embed("pca_lda", data["features"], {"projection": projection}))
        run = {
            "config": config,
            "val_top1": result["retrieval"]["top1"],
            "val_identification_rate": result["retrieval"]["identification_rate"],
        }
        lda_runs.append(run)
        print(f"pca_lda {config} -> Top-1 val {run['val_top1']:.3f}")
        key = (run["val_top1"], run["val_identification_rate"])
        if best_lda is None or key > best_lda["key"]:
            best_lda = {"key": key, "run": run, "projection": projection, "metrics": result}
    np.savez_compressed(PROJECTION_PATH, weights=best_lda["projection"][0], bias=best_lda["projection"][1])
    val_metrics["pca_lda"] = best_lda["metrics"]

    def selection_key(method):
        r = val_metrics[method]["retrieval"]
        return (r["top1"], r["identification_rate"])

    selected = max(METHODS, key=selection_key)
    calibration = {
        "selection_rule": "mayor Top-1 en validación; desempate por tasa de identificación",
        "max_unknown_far": 0.05,
        "selected_method": selected,
        "siamese_config": best_siamese["run"]["config"],
        "pca_lda_config": best_lda["run"]["config"],
        "methods": {
            name: {"threshold": val_metrics[name]["retrieval"]["threshold"], "val": val_metrics[name]}
            for name in METHODS
        },
    }
    training = {
        "backbone": BACKBONE_INFO,
        "seed": settings.SEED,
        "augmentation": "volteo horizontal (características en caché)",
        "siamese": {
            "head": "Dense(embedding_dim, activation) -> normalización L2",
            "loss": "contrastiva",
            "optimizer": {"name": "Adam", "learning_rate": LEARNING_RATE},
            "batch_size": BATCH_SIZE,
            "max_epochs": MAX_EPOCHS,
            "patience": PATIENCE,
            "pairs_per_epoch": int(2 * len(train_idx)),
            "grid": siamese_runs,
            "selected_config": best_siamese["run"]["config"],
        },
        "pca_lda": {
            "pipeline": f"normalización L2 -> PCA({PCA_COMPONENTS}) -> LDA -> normalización L2",
            "grid": lda_runs,
            "selected_config": best_lda["run"]["config"],
        },
        "versions": {
            "python": platform.python_version(),
            "tensorflow": tf.__version__,
            "scikit-learn": sklearn.__version__,
            "numpy": np.__version__,
        },
    }
    CALIBRATION_PATH.write_text(json.dumps(calibration, indent=2, ensure_ascii=False), encoding="utf-8")
    TRAINING_PATH.write_text(json.dumps(training, indent=2, ensure_ascii=False), encoding="utf-8")
    for name in METHODS:
        r = val_metrics[name]["retrieval"]
        print(
            f"{name:9s} val: Top-1 {r['top1']:.3f} | R@3 {r['recall_at_3']:.3f} | "
            f"identificación {r['identification_rate']:.3f} | FAR desconocidos "
            f"{r['unknown_far']:.3f} | umbral {r['threshold']:.3f}"
        )
    print(f"Método seleccionado por validación: {selected}")


if __name__ == "__main__":
    main()
