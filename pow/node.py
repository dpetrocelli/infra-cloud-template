"""HTTP node for the mini PoW blockchain (class 8, BC integrator case).

Endpoints:
  - GET  /chain            -> full local chain, as JSON
  - GET  /tx                -> pending tx pool
  - POST /tx                -> {"from": "...", "to": "...", "amount": 1} add tx to the pool
  - POST /mine               -> mine a block with the pending pool, add it to our chain
  - GET  /peers              -> configured peers
  - POST /peers/sync          -> ask every peer for its chain, keep the best valid one
  - GET  /metrics             -> Prometheus: block_height, peers, mining_seconds histogram

State (chain + difficulty) persists under DATA_DIR (default /data), same
convention as the servicio patron: kill the container, keep the disk.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from blockchain import (
    Block,
    chain_work,
    choose_best_chain,
    genesis,
    mine,
    new_block,
)
from fastapi import FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Histogram, generate_latest
from pydantic import BaseModel
from starlette.responses import Response

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
CHAIN_FILE = DATA_DIR / "chain.json"
DIFFICULTY = int(os.environ.get("DIFFICULTY", "4"))
PEERS = [p.strip() for p in os.environ.get("PEERS", "").split(",") if p.strip()]
PORT = int(os.environ.get("PORT", "8090"))

BLOCK_HEIGHT = Gauge("pow_block_height", "Height of the local chain (last block index)")
PEER_COUNT = Gauge("pow_peers", "Number of configured peers")
MINING_SECONDS = Histogram(
    "pow_mining_seconds", "Time spent mining a block, in seconds"
)

_pending_tx: list[dict[str, Any]] = []


class Tx(BaseModel):
    sender: str
    to: str
    amount: float


def _load_chain() -> list[Block]:
    if CHAIN_FILE.exists():
        raw = json.loads(CHAIN_FILE.read_text())
        return [Block.from_dict(b) for b in raw]
    genesis_block = genesis(DIFFICULTY)
    chain = [genesis_block]
    _save_chain(chain)
    return chain


def _save_chain(chain: list[Block]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHAIN_FILE.write_text(json.dumps([b.to_dict() for b in chain]))


def _update_gauges(chain: list[Block]) -> None:
    BLOCK_HEIGHT.set(chain[-1].index)
    PEER_COUNT.set(len(PEERS))


def on_startup() -> None:
    chain = _load_chain()
    _update_gauges(chain)


@asynccontextmanager
async def lifespan(_: FastAPI):
    on_startup()
    yield


app = FastAPI(title="pow-node", version="1.0.0", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/chain")
def get_chain() -> list[dict[str, Any]]:
    chain = _load_chain()
    return [b.to_dict() for b in chain]


@app.get("/tx")
def get_pending_tx() -> list[dict[str, Any]]:
    return _pending_tx


@app.post("/tx", status_code=201)
def add_tx(tx: Tx) -> dict[str, Any]:
    entry = tx.model_dump()
    entry["received_at"] = time.time()
    _pending_tx.append(entry)
    return entry


@app.post("/mine")
def mine_block() -> dict[str, Any]:
    chain = _load_chain()
    global _pending_tx
    txs = _pending_tx or [{"msg": "empty block"}]
    block = new_block(chain, txs, DIFFICULTY)

    start = time.time()
    mine(block)
    elapsed = time.time() - start
    MINING_SECONDS.observe(elapsed)

    chain.append(block)
    _save_chain(chain)
    _pending_tx = []
    _update_gauges(chain)
    return {"mined": block.to_dict(), "mining_seconds": elapsed}


@app.get("/peers")
def get_peers() -> list[str]:
    return PEERS


@app.post("/peers/sync")
def sync_peers() -> dict[str, Any]:
    """Longest-valid-chain rule: fetch every peer's chain, keep the best one
    (including our own) among those that pass validate_chain()."""
    local_chain = _load_chain()
    candidates = [local_chain]

    for peer in PEERS:
        try:
            resp = httpx.get(f"{peer}/chain", timeout=5.0)
            resp.raise_for_status()
            candidates.append([Block.from_dict(b) for b in resp.json()])
        except Exception:
            continue  # unreachable peer: skip it, do not fail the sync

    best = choose_best_chain(candidates)
    if best is None:
        raise HTTPException(500, "no valid chain found among self + peers")

    replaced = best is not local_chain and best != local_chain
    _save_chain(best)
    _update_gauges(best)
    return {"replaced": replaced, "height": best[-1].index, "work": chain_work(best)}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
