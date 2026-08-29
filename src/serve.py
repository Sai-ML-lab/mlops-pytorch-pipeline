"""FastAPI inference service for the trained CIFAR-10 classifier."""

from __future__ import annotations

import os
from pathlib import Path

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from torchvision import transforms

from model import get_model

CHECKPOINT_PATH = Path(
    os.environ.get("MODEL_CHECKPOINT", "/app/checkpoints/classifier_v1.pt")
)

app = FastAPI(title="MLOps PyTorch Model Serving", version="1.0.0")

model = None
class_names: list[str] = []
preprocess = transforms.Compose(
    [
        transforms.Resize((32, 32)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.4914, 0.4822, 0.4465],
            std=[0.2470, 0.2435, 0.2616],
        ),
    ]
)


def load_model() -> None:
    global model, class_names

    if not CHECKPOINT_PATH.exists():
        raise FileNotFoundError(f"Checkpoint not found: {CHECKPOINT_PATH}")

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location="cpu",
        weights_only=True,
    )
    architecture = checkpoint.get("architecture", "resnet18")
    num_classes = int(checkpoint.get("num_classes", 10))
    class_names = checkpoint.get(
        "class_names",
        [str(i) for i in range(num_classes)],
    )

    candidate = get_model(architecture=architecture, num_classes=num_classes)
    candidate.load_state_dict(checkpoint["model_state_dict"])
    candidate.eval()
    model = candidate


@app.on_event("startup")
def startup_event() -> None:
    load_model()


@app.get("/health")
def health() -> dict[str, str]:
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "ok"}


@app.post("/predict")
async def predict(image: UploadFile = File(...)) -> dict:
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload must be an image")

    try:
        raw = await image.read()
        pil_image = Image.open(__import__("io").BytesIO(raw)).convert("RGB")
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=400, detail="Invalid image") from exc

    tensor = preprocess(pil_image).unsqueeze(0)
    with torch.no_grad():
        logits = model(tensor)
        probabilities = torch.softmax(logits, dim=1)[0]

    pairs = [
        {"class": class_names[idx], "probability": round(float(probabilities[idx]), 6)}
        for idx in range(len(class_names))
    ]
    pairs.sort(key=lambda item: item["probability"], reverse=True)

    return {
        "predicted_class": pairs[0]["class"],
        "probabilities": pairs,
    }
