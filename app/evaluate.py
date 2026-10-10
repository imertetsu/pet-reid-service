"""Final evaluation on the test split (run once).

Usage: python -m app.evaluate

Thresholds and the selected method come from ``artifacts/calibration.json``
(validation). Nothing here changes the model.
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.metrics import roc_curve

from app import metrics, settings
from app.features import load_features, load_manifest
from app.model import build_head, embed
from app.protocol import evaluate_view, split_view
from app.train import CALIBRATION_PATH, HEAD_WEIGHTS_PATH, METHODS, PROJECTION_PATH

METRICS_PATH = settings.ARTIFACTS_DIR / "metrics.json"
PREDICTIONS_PATH = settings.ARTIFACTS_DIR / "test_predictions.json"
LABELS = {
    "baseline": "ResNet50 (línea base)",
    "siamese": "ResNet50 + cabeza siamesa",
    "pca_lda": "ResNet50 + PCA + LDA",
}
COLORS = {"baseline": "#eb6834", "siamese": "#1baf7a", "pca_lda": "#2a78d6"}
INK, INK_SECONDARY, GRID_COLOR = "#0b0b0b", "#52514e", "#e4e3df"


def style_axes(ax, title):
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(INK_SECONDARY)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    ax.grid(color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)


def load_trained(calibration) -> dict:
    """Load the fitted parts of the trained methods."""
    config = calibration["siamese_config"]
    head = build_head(config["embedding_dim"], config["activation"])
    head.load_weights(HEAD_WEIGHTS_PATH)
    with np.load(PROJECTION_PATH) as projection:
        return {"head": head, "projection": (projection["weights"], projection["bias"])}


def plot_roc(view, embeddings_by_method, path):
    fig, ax = plt.subplots(figsize=(5, 4.2), dpi=150)
    for method, emb in embeddings_by_method.items():
        identities, matrix = metrics.identity_distances(
            emb[view.query_idx], emb[view.gallery_idx], view.gallery_ids
        )
        labels = (np.asarray(view.query_ids)[:, None] == np.asarray(identities)[None, :]).ravel()
        fpr, tpr, _ = roc_curve(labels, -matrix.ravel())
        ax.plot(fpr, tpr, color=COLORS[method], linewidth=2, label=LABELS[method])
    ax.plot([0, 1], [0, 1], color=INK_SECONDARY, linewidth=1, linestyle=":")
    ax.set_xlabel("Tasa de falsos positivos", color=INK_SECONDARY)
    ax.set_ylabel("Tasa de verdaderos positivos", color=INK_SECONDARY)
    style_axes(ax, "Curva ROC de verificación (prueba)")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_topk(results_ranked, view, path):
    fig, ax = plt.subplots(figsize=(5, 4.2), dpi=150)
    known = view.query_enrolled
    truth = np.asarray(view.query_ids)[known]
    ks = np.arange(1, 11)
    for method, (ranked_ids, _) in results_ranked.items():
        hits = ranked_ids[known][:, :10] == truth[:, None]
        curve = [hits[:, :k].any(axis=1).mean() for k in ks]
        ax.plot(ks, curve, color=COLORS[method], linewidth=2, marker="o", markersize=4,
                label=LABELS[method])
    ax.set_xticks(ks)
    ax.set_xlabel("k (candidatos mostrados)", color=INK_SECONDARY)
    ax.set_ylabel("Recall@k", color=INK_SECONDARY)
    style_axes(ax, "Recall@k en consultas registradas (prueba)")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_distances(results_ranked, view, thresholds, path):
    fig, axes = plt.subplots(1, len(METHODS), figsize=(13, 3.8), dpi=150, sharey=False)
    known = view.query_enrolled
    for ax, method in zip(axes, METHODS):
        _, ranked_dist = results_ranked[method]
        top = ranked_dist[:, 0]
        bins = np.linspace(top.min(), top.max(), 30)
        ax.hist(top[known], bins=bins, color=COLORS[method], alpha=0.85,
                label="Perro registrado", edgecolor="white", linewidth=0.5)
        ax.hist(top[~known], bins=bins, color=INK_SECONDARY, alpha=0.55,
                label="Perro sin registro", edgecolor="white", linewidth=0.5)
        ax.axvline(thresholds[method], color=INK, linewidth=1.2, linestyle="--")
        ax.text(thresholds[method], ax.get_ylim()[1] * 0.95, " umbral", color=INK, fontsize=8, va="top")
        ax.set_xlabel("Distancia al primer candidato", color=INK_SECONDARY)
        style_axes(ax, LABELS[method])
        ax.legend(frameon=False, fontsize=8)
    axes[0].set_ylabel("Consultas", color=INK_SECONDARY)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_errors(records, predictions, method, path, limit=6):
    """Worst errors of the selected method: wrong dog accepted and unknown dog accepted."""
    errors = [p for p in predictions if p[method]["accepted"] and not p[method]["correct"]]
    errors.sort(key=lambda p: p[method]["candidates"][0]["distance"])
    errors = errors[:limit]
    if not errors:
        return
    gallery_photo = {}
    for r in records:
        if r["split"] == "test" and r["role"] == "gallery":
            gallery_photo.setdefault(r["identity"], r["path"])
    fig, axes = plt.subplots(len(errors), 2, figsize=(4.4, 2.2 * len(errors)), dpi=120)
    axes = np.atleast_2d(axes)
    for row, p in zip(axes, errors):
        candidate = p[method]["candidates"][0]
        row[0].imshow(Image.open(settings.DATA_DIR / p["path"]).convert("RGB"))
        kind = "registrado" if p["enrolled"] else "sin registro"
        row[0].set_title(f"Consulta ({kind})", fontsize=8, color=INK)
        row[1].imshow(Image.open(settings.DATA_DIR / gallery_photo[candidate["identity"]]).convert("RGB"))
        row[1].set_title(f"Sugerido: {candidate['identity']} d={candidate['distance']:.2f}", fontsize=8, color=INK)
        for ax in row:
            ax.axis("off")
    fig.suptitle(f"Aceptados con la identidad equivocada — {LABELS[method]}", fontsize=9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    records = load_manifest()
    cache = load_features()
    assert list(cache["paths"]) == [r["path"] for r in records], "Cache desactualizada"
    calibration = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    trained = load_trained(calibration)
    embeddings = {m: embed(m, cache["features"], trained) for m in METHODS}
    thresholds = {m: calibration["methods"][m]["threshold"] for m in METHODS}

    output = {
        "selected_method": calibration["selected_method"],
        "thresholds_from": "validación",
        "splits": {},
        "methods": {m: {} for m in METHODS},
    }
    predictions: list[dict] = []
    ranked_test = {}
    for split in ("test",):
        view = split_view(records, split)
        output["splits"][split] = {
            "gallery_images": int(len(view.gallery_idx)),
            "enrolled_identities": len(set(view.gallery_ids)),
            "known_queries": int(view.query_enrolled.sum()),
            "unknown_queries": int((~view.query_enrolled).sum()),
        }
        for method in METHODS:
            result, ranked_ids, ranked_dist = evaluate_view(view, embeddings[method], thresholds[method])
            output["methods"][method][split] = result
            if split == "test":
                ranked_test[method] = (ranked_ids, ranked_dist)
        if split == "test":
            for q, index in enumerate(view.query_idx):
                record = records[index]
                entry = {"path": record["path"], "identity": record["identity"], "enrolled": bool(record["enrolled"])}
                for method in METHODS:
                    ranked_ids, ranked_dist = ranked_test[method]
                    accepted = bool(ranked_dist[q, 0] <= thresholds[method])
                    entry[method] = {
                        "candidates": [
                            {"identity": str(ranked_ids[q, k]), "distance": round(float(ranked_dist[q, k]), 4)}
                            for k in range(3)
                        ],
                        "accepted": accepted,
                        # correct = accepted the right dog, or rejected an unknown dog
                        "correct": bool(ranked_ids[q, 0] == record["identity"]) if accepted else not record["enrolled"],
                    }
                predictions.append(entry)
            test_view = view

    settings.FIGURES_DIR.mkdir(exist_ok=True)
    plot_roc(test_view, embeddings, settings.FIGURES_DIR / "roc_test.png")
    plot_topk(ranked_test, test_view, settings.FIGURES_DIR / "recall_at_k_test.png")
    plot_distances(ranked_test, test_view, thresholds, settings.FIGURES_DIR / "distances_test.png")
    plot_errors(records, predictions, calibration["selected_method"], settings.FIGURES_DIR / "errors_test.png")

    METRICS_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    PREDICTIONS_PATH.write_text(json.dumps(predictions, indent=1, ensure_ascii=False), encoding="utf-8")

    for split in output["splits"]:
        print(f"\n== {split} ==")
        for method in METHODS:
            r = output["methods"][method][split]["retrieval"]
            v = output["methods"][method][split]["verification"]
            print(
                f"{method:9s} Top-1 {r['top1']:.3f} | R@3 {r['recall_at_3']:.3f} | "
                f"identificación {r['identification_rate']:.3f} | FAR desconocidos {r['unknown_far']:.3f} | "
                f"AUC {v['roc_auc']:.3f} | EER {v['eer']:.3f}"
            )


if __name__ == "__main__":
    main()
