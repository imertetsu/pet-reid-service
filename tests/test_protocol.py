"""The data protocol must not leak identities or images between splits."""

import hashlib
import json
from collections import defaultdict

import pytest

from app import settings


@pytest.fixture(scope="module")
def records():
    manifest = json.loads(settings.MANIFEST_PATH.read_text(encoding="utf-8"))
    return manifest["images"]


def test_identities_do_not_cross_splits(records):
    splits_by_identity = defaultdict(set)
    for record in records:
        splits_by_identity[record["identity"]].add(record["split"])
    assert all(len(splits) == 1 for splits in splits_by_identity.values())


def test_no_identical_image_in_two_splits(records):
    split_by_hash = {}
    for record in records:
        digest = hashlib.sha256((settings.DATA_DIR / record["path"]).read_bytes()).hexdigest()
        assert split_by_hash.setdefault(digest, record["split"]) == record["split"]


def test_gallery_and_query_roles(records):
    by_identity = defaultdict(list)
    for record in records:
        if record["split"] != "train":
            by_identity[(record["split"], record["identity"])].append(record)
    for items in by_identity.values():
        roles = [r["role"] for r in items]
        if items[0]["enrolled"]:
            assert roles.count("gallery") == settings.GALLERY_PHOTOS_PER_IDENTITY
            assert roles.count("query") >= 1
        else:
            assert set(roles) == {"query"}


def test_every_split_has_unknown_identities(records):
    for split in ("val", "test"):
        unknown = {r["identity"] for r in records if r["split"] == split and not r["enrolled"]}
        assert unknown, f"{split} needs non-enrolled identities to measure rejection"
