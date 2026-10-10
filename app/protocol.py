"""Gallery / query views of a split, shared by training (val) and evaluation (test)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app import metrics


@dataclass
class SplitView:
    gallery_idx: np.ndarray
    gallery_ids: list[str]
    query_idx: np.ndarray
    query_ids: list[str]
    query_enrolled: np.ndarray


def split_view(records: list[dict], split: str) -> SplitView:
    gallery = [i for i, r in enumerate(records) if r["split"] == split and r["role"] == "gallery"]
    query = [i for i, r in enumerate(records) if r["split"] == split and r["role"] == "query"]
    if not gallery or not query:
        raise ValueError(f"Split '{split}' has no gallery or query images.")
    return SplitView(
        gallery_idx=np.array(gallery),
        gallery_ids=[records[i]["identity"] for i in gallery],
        query_idx=np.array(query),
        query_ids=[records[i]["identity"] for i in query],
        query_enrolled=np.array([records[i]["enrolled"] for i in query]),
    )


def evaluate_view(view: SplitView, embeddings: np.ndarray, threshold: float | None = None):
    """Retrieval + verification metrics. Without a threshold it is calibrated here
    (only allowed on validation)."""
    query_emb = embeddings[view.query_idx]
    gallery_emb = embeddings[view.gallery_idx]
    ranked_ids, ranked_dist = metrics.rank(query_emb, gallery_emb, view.gallery_ids)
    if threshold is None:
        threshold = metrics.calibrate_threshold(
            ranked_ids, ranked_dist, view.query_ids, view.query_enrolled
        )
    retrieval = metrics.retrieval_metrics(
        ranked_ids, ranked_dist, view.query_ids, view.query_enrolled, threshold
    )
    verification = metrics.verification_metrics(
        query_emb, view.query_ids, gallery_emb, view.gallery_ids, threshold
    )
    return {"retrieval": retrieval, "verification": verification}, ranked_ids, ranked_dist
