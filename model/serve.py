"""Tiny inference server used in class 7 (IA: Vertex AI / Ollama / vast.ai
alternatives) and in the class-8 integrator case.

Endpoints:
  - POST /predict  -> {"features": [sepal_len, sepal_wid, petal_len, petal_wid]}
                      returns {"class": "...", "confidence": 0.9x}
  - GET  /metrics   -> Prometheus exposition format
  - GET  /healthz   -> liveness probe

Loads model.joblib produced by train.py at image build time -- no training
happens on the request path.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import joblib
from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel

MODEL_PATH = Path(os.environ.get("MODEL_PATH", "model.joblib"))
PORT = int(os.environ.get("PORT", "8081"))

app = FastAPI(title="model-server", version="1.0.0")

PREDICTIONS = Counter("model_predictions_total", "Total predictions served")
PREDICT_LATENCY = Histogram("model_predict_seconds", "Prediction latency in seconds")

_bundle = None


def _load_bundle():
    global _bundle
    if _bundle is None:
        if not MODEL_PATH.exists():
            raise RuntimeError(
                f"model file not found at {MODEL_PATH}; run train.py first"
            )
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


class PredictRequest(BaseModel):
    features: list[float]


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    PREDICTIONS.inc(0)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict")
def predict(req: PredictRequest) -> dict[str, object]:
    if len(req.features) != 4:
        raise HTTPException(
            400,
            "expected 4 features (iris: sepal_len, sepal_wid, petal_len, petal_wid)",
        )

    start = time.time()
    bundle = _load_bundle()
    model = bundle["model"]
    proba = model.predict_proba([req.features])[0]
    idx = int(proba.argmax())
    PREDICTIONS.inc()
    PREDICT_LATENCY.observe(time.time() - start)
    return {"class": bundle["target_names"][idx], "confidence": float(proba[idx])}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
