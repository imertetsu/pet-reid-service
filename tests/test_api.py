"""End-to-end API tests with the real model (ResNet50 + trained head)."""

import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import settings
from app.evaluate import PREDICTIONS_PATH
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def predictions():
    return json.loads(PREDICTIONS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def selected(client):
    return client.get("/api/health").json()["selected_method"]


def upload(path):
    return {"image": (path.name, path.read_bytes(), "image/jpeg")}


def identify(client, path, method=None):
    data = {"method": method} if method else {}
    return client.post("/api/identify", files=upload(settings.DATA_DIR / path), data=data)


# ---- valid case ------------------------------------------------------------
def test_valid_case_known_dog_is_identified(client, predictions, selected):
    """A test query of an enrolled dog, correctly solved offline, must give the same answer."""
    sample = next(p for p in predictions if p["enrolled"] and p[selected]["correct"])
    response = identify(client, sample["path"])
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == selected
    assert body["accepted"] is True
    assert body["match"]["id"] == sample["identity"]
    assert body["match"]["location"]["simulated"] is True
    assert len(body["candidates"]) == 3
    distances = [c["distance"] for c in body["candidates"]]
    assert distances == sorted(distances)


@pytest.mark.parametrize("method", ["baseline", "siamese", "pca_lda"])
def test_api_matches_offline_evaluation(client, predictions, method):
    """The API runs the real model: its top-1 and distance match the evaluation script."""
    for sample in predictions[:5]:
        body = identify(client, sample["path"], method).json()
        expected = sample[method]["candidates"][0]
        assert body["candidates"][0]["pet_id"] == expected["identity"]
        assert body["candidates"][0]["distance"] == pytest.approx(expected["distance"], abs=1e-3)
        assert body["accepted"] == sample[method]["accepted"]


# ---- hard cases --------------------------------------------------------------
def test_hard_case_unknown_dog(client, predictions, selected):
    """A dog that is not in the gallery should be rejected; the offline evaluation
    records whether the model gets it right, and the API must agree with it."""
    sample = next(p for p in predictions if not p["enrolled"])
    body = identify(client, sample["path"]).json()
    assert body["accepted"] == sample[selected]["accepted"]
    if not body["accepted"]:
        assert body["match"] is None
    assert body["candidates"][0]["distance"] >= 0


def test_hard_case_known_dog_the_model_gets_wrong(client, predictions, selected):
    """A registered dog that the selected method misidentifies in the evaluation:
    the API reproduces the same (wrong) answer, a documented limitation."""
    sample = next(p for p in predictions if p["enrolled"] and not p[selected]["correct"])
    body = identify(client, sample["path"]).json()
    expected = sample[selected]["candidates"][0]["identity"]
    assert body["candidates"][0]["pet_id"] == expected
    assert body["accepted"] == sample[selected]["accepted"]


def test_hard_case_image_without_a_dog(client):
    """A valid image with no dog still gets an answer; the threshold should reject it."""
    buffer = io.BytesIO()
    Image.new("RGB", (300, 300), (120, 160, 200)).save(buffer, format="PNG")
    response = client.post("/api/identify", files={"image": ("sky.png", buffer.getvalue(), "image/png")})
    assert response.status_code == 200
    assert response.json()["accepted"] is False


# ---- invalid inputs ----------------------------------------------------------
def png_bytes(size):
    buffer = io.BytesIO()
    Image.new("RGB", size, "gray").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "files, data, status",
    [
        ({"image": ("notes.jpg", b"hello world", "image/jpeg")}, {}, 415),
        ({"image": ("tiny.png", png_bytes((40, 40)), "image/png")}, {}, 422),
        ({"image": ("big.jpg", b"0" * (settings.MAX_UPLOAD_BYTES + 10), "image/jpeg")}, {}, 413),
        ({"image": ("ok.png", png_bytes((200, 200)), "image/png")}, {"method": "knn"}, 422),
        (None, {}, 422),
    ],
    ids=["text-as-jpg", "too-small", "too-big", "bad-method", "missing-file"],
)
def test_invalid_inputs(client, files, data, status):
    response = client.post("/api/identify", files=files, data=data)
    assert response.status_code == status
    assert response.json()["detail"]


def test_register_requires_two_photos(client):
    files = [("photos", ("a.png", png_bytes((200, 200)), "image/png"))]
    response = client.post("/api/pets", data={"alias": "Solo", "owner": "Test"}, files=files)
    assert response.status_code == 422


# ---- full flow ---------------------------------------------------------------
def test_full_flow_register_identify_ping_delete(client, predictions):
    """Enroll an unknown test dog with 2 photos, find it with a third one, then clean up."""
    manifest = json.loads(settings.MANIFEST_PATH.read_text(encoding="utf-8"))["images"]
    unknown = [r for r in manifest if r["split"] == "test" and not r["enrolled"]]
    identity = unknown[0]["identity"]
    photos = [r["path"] for r in unknown if r["identity"] == identity]
    files = [
        ("photos", (f"p{i}.jpg", (settings.DATA_DIR / p).read_bytes(), "image/jpeg"))
        for i, p in enumerate(photos[:2])
    ]
    created = client.post("/api/pets", data={"alias": "Prueba", "owner": "Tester"}, files=files)
    assert created.status_code == 201
    pet = created.json()
    try:
        assert any(p["id"] == pet["id"] for p in client.get("/api/gallery").json())
        body = identify(client, photos[2]).json()
        assert pet["id"] in [c["pet_id"] for c in body["candidates"]]

        before = pet["location"]["timestamp"]
        moved = client.post(f"/api/pets/{pet['id']}/ping").json()
        assert moved["timestamp"] != before
    finally:
        assert client.delete(f"/api/pets/{pet['id']}").status_code == 204
    assert all(p["id"] != pet["id"] for p in client.get("/api/gallery").json())
    assert client.delete(f"/api/pets/{pet['id']}").status_code == 404


def test_dataset_pets_cannot_be_deleted(client):
    pet_id = client.get("/api/gallery").json()[0]["id"]
    assert client.delete(f"/api/pets/{pet_id}").status_code == 403


def test_frontend_and_model_info(client):
    assert client.get("/").status_code == 200
    info = client.get("/api/model").json()
    assert set(info["methods"]) == {"baseline", "siamese", "pca_lda"}
    assert "test" in info["test"]["methods"]["baseline"]


# ---- prepared demo -------------------------------------------------------------
def test_demo_examples_behave_as_labeled(client, selected):
    """The curated UI examples must keep the outcome their label promises."""
    samples = client.get("/api/samples").json()
    assert samples, "data/demo_examples.json should provide examples"
    for sample in samples:
        body = identify(client, sample["path"]).json()
        top = body["candidates"][0]["pet_id"]
        if sample["kind"] == "registrado":
            assert body["accepted"] and top == sample["identity"], sample
        elif sample["kind"] == "no registrado":
            assert not body["accepted"], sample
        elif sample["kind"] == "error: otro perro":
            assert body["accepted"] and top != sample["identity"], sample
        elif sample["kind"] == "error: no lo reconoce":
            assert not body["accepted"] and top == sample["identity"], sample
        else:
            raise AssertionError(f"Unknown kind: {sample['kind']}")
