"""Image validation and preprocessing shared by training, evaluation and the API.

This module does not depend on TensorFlow, so it can be tested quickly.
The ResNet50-specific normalization is applied in ``app.model``.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app import settings

ALLOWED_FORMATS = {"PNG", "JPEG"}


class ImageValidationError(ValueError):
    """Raised when an uploaded image is not acceptable. ``status`` maps to HTTP."""

    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def load_image(data: bytes) -> Image.Image:
    """Decode and validate raw bytes; return an RGB image with EXIF orientation applied."""
    if not data:
        raise ImageValidationError("El archivo está vacío.")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise ImageValidationError("La imagen supera el máximo de 5 MB.", status=413)
    try:
        image = Image.open(io.BytesIO(data))
        image_format = image.format
        width, height = image.size
        if width * height > settings.MAX_IMAGE_PIXELS:
            raise ImageValidationError("La imagen supera el máximo de 6 megapíxeles.")
        image.load()
    except UnidentifiedImageError as exc:
        raise ImageValidationError(
            "El archivo no es una imagen PNG o JPEG válida.", status=415
        ) from exc
    except (OSError, Image.DecompressionBombError) as exc:
        raise ImageValidationError("La imagen está dañada o no se puede leer.") from exc

    if image_format not in ALLOWED_FORMATS:
        raise ImageValidationError("Solo se aceptan imágenes PNG o JPEG.", status=415)
    if min(width, height) < settings.MIN_IMAGE_SIDE:
        raise ImageValidationError(
            f"La imagen es muy pequeña: mínimo {settings.MIN_IMAGE_SIDE} píxeles por lado."
        )
    image = ImageOps.exif_transpose(image)
    return to_rgb(image)


def to_rgb(image: Image.Image) -> Image.Image:
    """Convert to RGB, compositing transparency over white."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    return image.convert("RGB")


def center_square(image: Image.Image, size: int = settings.IMAGE_SIZE) -> Image.Image:
    """Crop the central square and resize it to ``size`` x ``size``."""
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    square = image.crop((left, top, left + side, top + side))
    return square.resize((size, size), Image.Resampling.BILINEAR)


def to_array(image: Image.Image) -> np.ndarray:
    """RGB image -> float32 array (H, W, 3) in [0, 255]."""
    return np.asarray(center_square(image), dtype=np.float32)


def load_path(path) -> np.ndarray:
    """Read a dataset image from disk and return the model-ready RGB array."""
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        return to_array(to_rgb(image))
