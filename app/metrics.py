"""Open-set retrieval and verification metrics, and threshold calibration.

A query is compared with every enrolled identity; the distance to an identity is
the minimum distance to its gallery photos. Then:

- Top-1 / Recall@3 (known queries): is the true dog first / among the first three?
- With a threshold the system accepts the first candidate only if its distance is
  below it. Identification rate = known queries accepted with the right dog.
  Unknown FAR = non-enrolled queries that were (wrongly) accepted.
- Verification: every (query, enrolled identity) pair is a same / different
  decision; ROC-AUC and EER do not depend on the threshold.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve

MAX_UNKNOWN_FAR = 0.05


def identity_distances(query_emb, gallery_emb, gallery_ids):
    """Return (identities, matrix Q x I) with the min distance to each identity."""
    identities = sorted(set(gallery_ids))
    gallery_ids = np.asarray(gallery_ids)
    pairwise = np.linalg.norm(query_emb[:, None, :] - gallery_emb[None, :, :], axis=-1)
    matrix = np.stack(
        [pairwise[:, gallery_ids == identity].min(axis=1) for identity in identities], axis=1
    )
    return identities, matrix


def rank(query_emb, gallery_emb, gallery_ids):
    """Per query: candidate identities sorted by distance, and those distances."""
    identities, matrix = identity_distances(query_emb, gallery_emb, gallery_ids)
    order = np.argsort(matrix, axis=1)
    ranked_ids = np.asarray(identities)[order]
    ranked_dist = np.take_along_axis(matrix, order, axis=1)
    return ranked_ids, ranked_dist


def retrieval_metrics(ranked_ids, ranked_dist, query_ids, query_enrolled, threshold):
    query_ids = np.asarray(query_ids)
    known = np.asarray(query_enrolled, dtype=bool)
    unknown = ~known
    top1_ok = ranked_ids[:, 0] == query_ids
    top3_ok = (ranked_ids[:, :3] == query_ids[:, None]).any(axis=1)
    accepted = ranked_dist[:, 0] <= threshold
    return {
        "known_queries": int(known.sum()),
        "unknown_queries": int(unknown.sum()),
        "top1": float(top1_ok[known].mean()),
        "recall_at_3": float(top3_ok[known].mean()),
        "identification_rate": float((accepted & top1_ok)[known].mean()),
        "known_wrong_accepted": int((accepted & ~top1_ok & known).sum()),
        "known_rejected": int((~accepted & known).sum()),
        "unknown_accepted": int((accepted & unknown).sum()),
        "unknown_far": float(accepted[unknown].mean()) if unknown.any() else 0.0,
        "threshold": float(threshold),
    }


def verification_metrics(query_emb, query_ids, gallery_emb, gallery_ids, threshold):
    identities, matrix = identity_distances(query_emb, gallery_emb, gallery_ids)
    labels = (np.asarray(query_ids)[:, None] == np.asarray(identities)[None, :]).ravel()
    distances = matrix.ravel()
    scores = -distances  # higher score = more likely the same dog
    fpr, tpr, _ = roc_curve(labels, scores)
    eer_index = np.nanargmin(np.abs(fpr - (1 - tpr)))
    predicted = distances <= threshold
    tp = int((predicted & labels).sum())
    fp = int((predicted & ~labels).sum())
    fn = int((~predicted & labels).sum())
    tn = int((~predicted & ~labels).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "pairs": int(labels.size),
        "positive_pairs": int(labels.sum()),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "eer": float((fpr[eer_index] + 1 - tpr[eer_index]) / 2),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "far": fp / (fp + tn) if fp + tn else 0.0,
        "threshold": float(threshold),
    }


def calibrate_threshold(ranked_ids, ranked_dist, query_ids, query_enrolled):
    """Highest identification rate with unknown FAR <= MAX_UNKNOWN_FAR (validation only)."""
    candidates = np.unique(ranked_dist[:, 0])
    best_threshold, best_key = float(candidates[0]) - 1e-6, (-1.0, 0.0)
    for threshold in candidates:
        m = retrieval_metrics(ranked_ids, ranked_dist, query_ids, query_enrolled, threshold)
        if m["unknown_far"] > MAX_UNKNOWN_FAR:
            continue
        key = (m["identification_rate"], -m["known_wrong_accepted"])
        if key > best_key:
            best_threshold, best_key = float(threshold), key
    return best_threshold
