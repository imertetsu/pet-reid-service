"""Validation and preprocessing of input images (no TensorFlow needed)."""

import io

import numpy as np
import pytest
from PIL import Image

from app import settings
from app.images import ImageValidationError, load_image, to_array


def encode(image: Image.Image, fmt: str = "PNG", **kwargs) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


def test_valid_png_becomes_224_rgb_array():
    data = encode(Image.new("RGBA", (300, 200), (10, 20, 30, 128)))
    array = to_array(load_image(data))
    assert array.shape == (settings.IMAGE_SIZE, settings.IMAGE_SIZE, 3)
    assert array.dtype == np.float32
    assert 0 <= array.min() and array.max() <= 255


def test_exif_orientation_is_applied():
    image = Image.new("RGB", (300, 150), "white")
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees when displayed
    data = encode(image, "JPEG", exif=exif.tobytes())
    assert load_image(data).size == (150, 300)


@pytest.mark.parametrize(
    "data, status",
    [
        (b"", 422),
        (b"this is not an image", 415),
        (encode(Image.new("RGB", (50, 50))), 422),
        (encode(Image.new("RGB", (200, 200)), "GIF"), 415),
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, 415),
    ],
    ids=["empty", "text", "too-small", "gif", "corrupt-png"],
)
def test_invalid_inputs_are_rejected(data, status):
    with pytest.raises(ImageValidationError) as error:
        load_image(data)
    assert error.value.status == status


def test_too_large_file_is_rejected():
    with pytest.raises(ImageValidationError) as error:
        load_image(b"0" * (settings.MAX_UPLOAD_BYTES + 1))
    assert error.value.status == 413
