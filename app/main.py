"""FastAPI application: REST API + static frontend.

Run with ``python run.py`` (http://127.0.0.1:9100, docs at /docs).
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import settings
from app.evaluate import METRICS_PATH
from app.images import ImageValidationError
from app.service import METHOD_LABELS, ReidService
from app.train import TRAINING_PATH

state: dict = {}


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


DEMO_EXAMPLES_PATH = settings.DATA_DIR / "demo_examples.json"


def build_samples() -> list[dict]:
    """Curated example queries for the UI (test split, never used for training)."""
    identity_by_path = {
        r["path"]: r["identity"] for r in read_json(settings.MANIFEST_PATH, {"images": []})["images"]
    }
    samples = []
    for example in read_json(DEMO_EXAMPLES_PATH, {"examples": []})["examples"]:
        if example["path"] not in identity_by_path:
            continue
        samples.append(
            {
                "kind": example["kind"],
                "path": example["path"],
                "identity": identity_by_path[example["path"]],
                "url": f"/media/data/{example['path']}",
            }
        )
    return samples


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = ReidService()
    state["service"] = service
    state["samples"] = build_samples()
    yield
    state.clear()


app = FastAPI(
    title="Reidentificación de mascotas",
    description="Microservicio que compara la foto de un perro con la galería de mascotas registradas.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(ImageValidationError)
async def validation_handler(request: Request, exc: ImageValidationError):
    return JSONResponse(status_code=exc.status, content={"detail": str(exc)})


def service() -> ReidService:
    return state["service"]


@app.get("/api/health")
def health():
    svc = service()
    return {
        "status": "ok",
        "selected_method": svc.calibration["selected_method"],
        "gallery_size": len(svc.pets),
    }


@app.get("/api/model")
def model_info():
    svc = service()
    training = read_json(TRAINING_PATH, {})
    return {
        "methods": METHOD_LABELS,
        "selected_method": svc.calibration["selected_method"],
        "selection_rule": svc.calibration["selection_rule"],
        "thresholds": {m: v["threshold"] for m, v in svc.calibration["methods"].items()},
        "validation": {m: v["val"] for m, v in svc.calibration["methods"].items()},
        "test": read_json(METRICS_PATH, {}),
        "training": {
            "backbone": training.get("backbone"),
            "siamese": {k: v for k, v in training.get("siamese", {}).items() if k != "grid"},
            "pca_lda": {k: v for k, v in training.get("pca_lda", {}).items() if k != "grid"},
            "versions": training.get("versions"),
        },
        "dataset": read_json(settings.DATASET_INFO_PATH, {}),
    }


@app.get("/api/samples")
def samples():
    return state["samples"]


@app.get("/api/gallery")
def gallery():
    return service().list_pets()


async def read_upload(upload: UploadFile) -> bytes:
    # Read one byte past the limit so oversized files are rejected without loading them fully
    data = await upload.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise ImageValidationError("La imagen supera el máximo de 5 MB.", status=413)
    return data


@app.post("/api/identify")
async def identify(image: UploadFile = File(...), method: str | None = Form(None)):
    data = await read_upload(image)
    return service().identify(data, method)


@app.post("/api/pets", status_code=201)
async def register_pet(
    alias: str = Form(...),
    owner: str = Form(...),
    photos: list[UploadFile] = File(...),
):
    data = [await read_upload(photo) for photo in photos]
    return service().register(alias, owner, data)


@app.delete("/api/pets/{pet_id}", status_code=204)
def delete_pet(pet_id: str):
    try:
        service().delete(pet_id)
    except KeyError:
        raise HTTPException(404, "Mascota no encontrada.")
    except PermissionError as exc:
        raise HTTPException(403, str(exc))


@app.post("/api/pets/{pet_id}/ping")
def ping(pet_id: str):
    try:
        return service().ping(pet_id)
    except KeyError:
        raise HTTPException(404, "Mascota no encontrada.")


settings.RUNTIME_DIR.mkdir(exist_ok=True)
settings.FIGURES_DIR.mkdir(exist_ok=True)
app.mount("/media/figures", StaticFiles(directory=settings.FIGURES_DIR), name="figures")
app.mount("/media/data", StaticFiles(directory=settings.DATA_DIR), name="data")
app.mount("/media/runtime", StaticFiles(directory=settings.RUNTIME_DIR), name="runtime")
app.mount("/static", StaticFiles(directory=settings.FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(settings.FRONTEND_DIR / "index.html")
