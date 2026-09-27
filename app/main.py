"""Servicio patron: the reference stateful HTTP service used in every class.

Contract (matches the class-1 lab exactly, just wrapped in FastAPI instead of
the stdlib http.server used there):
  - GET  /          -> plain-text hit counter, persisted on disk
  - GET  /healthz   -> liveness probe, always 200 if the process is up
  - GET  /metrics   -> Prometheus exposition format
  - POST /items     -> append a small JSON item to the persisted list
  - GET  /items     -> list the persisted items

State lives under DATA_DIR (default /data), which in every class is a
mounted persistent disk / PVC. Kill the container, keep the disk: the state
survives. That is the whole point of the class-1 demo.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel

# --- configuration (env vars, no hardcoded paths/ports) --------------------
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
COUNTER_FILE = DATA_DIR / "counter.txt"
ITEMS_FILE = DATA_DIR / "items.json"
PORT = int(os.environ.get("PORT", "8080"))

app = FastAPI(title="servicio-patron", version="1.0.0")

# --- metrics -----------------------------------------------------------
HITS = Counter("servicio_patron_hits_total", "Total requests received on /")
ITEMS_CREATED = Counter(
    "servicio_patron_items_created_total", "Items persisted via POST /items"
)
REQUEST_LATENCY = Histogram(
    "servicio_patron_request_seconds", "Request latency in seconds", ["path"]
)


class Item(BaseModel):
    name: str
    value: str | None = None


def _read_counter() -> int:
    if COUNTER_FILE.exists():
        return int(COUNTER_FILE.read_text().strip() or 0)
    return 0


def _write_counter(value: int) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    COUNTER_FILE.write_text(str(value))


def _read_items() -> list[dict[str, Any]]:
    if ITEMS_FILE.exists():
        return json.loads(ITEMS_FILE.read_text() or "[]")
    return []


def _write_items(items: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ITEMS_FILE.write_text(json.dumps(items))


@app.get("/")
def root() -> Response:
    start = time.time()
    HITS.inc()
    contador = _read_counter() + 1
    _write_counter(contador)
    body = f"Servicio patron activo. Visitas persistidas en disco: {contador}\n"
    REQUEST_LATENCY.labels(path="/").observe(time.time() - start)
    return Response(content=body, media_type="text/plain; charset=utf-8")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    HITS.inc(0)  # make sure the metric exists even before anyone hits "/"
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/items", status_code=201)
def create_item(item: Item) -> dict[str, Any]:
    start = time.time()
    items = _read_items()
    stored = item.model_dump()
    stored["created_at"] = time.time()
    items.append(stored)
    _write_items(items)
    ITEMS_CREATED.inc()
    REQUEST_LATENCY.labels(path="/items").observe(time.time() - start)
    return stored


@app.get("/items")
def list_items() -> list[dict[str, Any]]:
    return _read_items()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
