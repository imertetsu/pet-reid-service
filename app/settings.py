"""Central configuration: paths, data protocol and upload limits."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
MANIFEST_PATH = DATA_DIR / "manifest.json"
DATASET_INFO_PATH = DATA_DIR / "dataset_info.json"
RAW_DIR = ROOT / "raw"
ARTIFACTS_DIR = ROOT / "artifacts"
FIGURES_DIR = ROOT / "figures"
FRONTEND_DIR = ROOT / "frontend"
RUNTIME_DIR = ROOT / "runtime"

SEED = 42

# DogFaceNet_224resized (Zenodo record 12578449, CC BY 4.0)
DOGFACENET_URL = (
    "https://zenodo.org/records/12578449/files/DogFaceNet_224resized.zip?download=1"
)
DOGFACENET_MD5 = "010c207e202bb499039452aa7363b015"
DOGFACENET_ARCHIVE = RAW_DIR / "DogFaceNet_224resized.zip"

# Data protocol
MIN_PHOTOS_PER_IDENTITY = 6
MAX_PHOTOS_PER_IDENTITY = 10
SPLIT_FRACTIONS = {"train": 0.6, "val": 0.2, "test": 0.2}
REGISTERED_FRACTION = 0.75  # in val/test, share of identities enrolled in the gallery
GALLERY_PHOTOS_PER_IDENTITY = 2
NEAR_DUPLICATE_MAX_BITS = 4  # dHash Hamming distance treated as the same photo

# Model input
IMAGE_SIZE = 224

# Upload limits
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MIN_IMAGE_SIDE = 96
MAX_IMAGE_PIXELS = 6_000_000
