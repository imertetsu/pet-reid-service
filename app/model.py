"""ResNet50 feature extractor (reused) and the methods that compare its features.

- Baseline: ResNet50 ImageNet features (2048-d), L2-normalized, compared directly.
- Siamese: the same features go through a small head Dense -> L2 trained with
  contrastive loss (metric learning on pairs).
- PCA + LDA: classic ML. PCA reduces the features, then Linear Discriminant
  Analysis learns the projection that best separates the training dogs.
ResNet50 stays frozen in every method, so features are computed once and cached.

All methods compare L2-normalized vectors with the Euclidean distance. On unit
vectors d = sqrt(2 - 2 cos), so ranking is the same as with the cosine distance.
"""

from __future__ import annotations

import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

FEATURE_DIM = 2048
BACKBONE_INFO = {
    "architecture": "ResNet50",
    "weights": "imagenet (keras.applications, resnet50_weights_tf_dim_ordering_tf_kernels_notop.h5)",
    "include_top": False,
    "pooling": "avg",
    "trainable": False,
}


def build_backbone() -> keras.Model:
    return keras.applications.ResNet50(include_top=False, weights="imagenet", pooling="avg")


def extract_features(backbone: keras.Model, images: np.ndarray, batch_size: int = 32) -> np.ndarray:
    """RGB arrays (N, 224, 224, 3) in [0, 255] -> raw ResNet50 features (N, 2048)."""
    x = keras.applications.resnet50.preprocess_input(images.astype(np.float32, copy=True))
    return backbone.predict(x, batch_size=batch_size, verbose=0)


def l2_normalize(x: np.ndarray) -> np.ndarray:
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12)


def build_head(embedding_dim: int, activation: str | None = "relu") -> keras.Model:
    """Dense -> L2 head. ``activation=None`` gives a linear projection."""
    inputs = keras.Input(shape=(FEATURE_DIM,), name="features")
    x = layers.Dense(embedding_dim, activation=activation, name="embedding_dense")(inputs)
    outputs = layers.UnitNormalization(name="l2_normalize")(x)
    return keras.Model(inputs, outputs, name="siamese_head")


def build_siamese(head: keras.Model) -> keras.Model:
    """Two inputs share the same head; the output is the Euclidean distance."""
    a = keras.Input(shape=(FEATURE_DIM,), name="features_a")
    b = keras.Input(shape=(FEATURE_DIM,), name="features_b")
    ea, eb = head(a), head(b)
    squared = layers.Lambda(
        lambda t: tf.reduce_sum(tf.square(t[0] - t[1]), axis=1, keepdims=True),
        name="squared_distance",
    )([ea, eb])
    distance = layers.Lambda(lambda s: tf.sqrt(tf.maximum(s, 1e-12)), name="distance")(squared)
    return keras.Model([a, b], distance, name="siamese")


def contrastive_loss(margin: float):
    """L = y * D^2 + (1 - y) * max(0, margin - D)^2, with y = 1 for the same dog."""

    def loss(y_true, distance):
        y = tf.cast(tf.reshape(y_true, tf.shape(distance)), distance.dtype)
        positive = y * tf.square(distance)
        negative = (1.0 - y) * tf.square(tf.nn.relu(margin - distance))
        return tf.reduce_mean(positive + negative)

    return loss


def embed(method: str, features: np.ndarray, trained: dict | None = None) -> np.ndarray:
    """Raw ResNet50 features -> unit-length embeddings for the given method.

    ``trained`` holds the fitted parts: ``head`` (Keras model) for ``siamese`` and
    ``projection`` (W, b) for ``pca_lda``.
    """
    if method == "baseline":
        return l2_normalize(features)
    trained = trained or {}
    if method == "siamese":
        return trained["head"].predict(features, batch_size=256, verbose=0)
    if method == "pca_lda":
        weights, bias = trained["projection"]
        return l2_normalize(l2_normalize(features) @ weights + bias)
    raise ValueError(f"Unknown method: {method}")
