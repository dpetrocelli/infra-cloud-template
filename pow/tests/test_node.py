import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DIFFICULTY", "1")  # keep tests fast
    already_imported = "node" in sys.modules
    import node as node_module

    if already_imported:
        importlib.reload(node_module)
    with TestClient(node_module.app) as test_client:
        yield test_client


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_chain_starts_with_genesis(client):
    chain = client.get("/chain").json()
    assert len(chain) == 1
    assert chain[0]["index"] == 0


def test_tx_and_mine(client):
    client.post("/tx", json={"sender": "alice", "to": "bob", "amount": 1})
    assert len(client.get("/tx").json()) == 1

    r = client.post("/mine")
    assert r.status_code == 200
    body = r.json()
    assert body["mined"]["index"] == 1
    assert client.get("/tx").json() == []  # pool cleared after mining

    chain = client.get("/chain").json()
    assert len(chain) == 2


def test_metrics_reports_block_height(client):
    client.post("/mine")
    m = client.get("/metrics").text
    assert "pow_block_height" in m
    assert "pow_mining_seconds" in m
    assert "pow_peers" in m


def test_concurrent_tx_and_mine_keep_the_chain_valid(client):
    """Regression test: /tx during /mine used to change a block after it was
    hashed, and concurrent /mine calls overwrote each other's blocks."""
    from concurrent.futures import ThreadPoolExecutor

    from blockchain import Block, validate_chain

    def send_tx(i):
        return client.post("/tx", json={"sender": f"u{i}", "to": "sink", "amount": 1})

    def do_mine(_):
        return client.post("/mine")

    with ThreadPoolExecutor(max_workers=8) as pool:
        tx_futures = [pool.submit(send_tx, i) for i in range(60)]
        mine_futures = [pool.submit(do_mine, i) for i in range(10)]
        results = [f.result() for f in tx_futures + mine_futures]

    assert all(r.status_code in (200, 201) for r in results)
    chain = [Block.from_dict(b) for b in client.get("/chain").json()]
    ok, reason = validate_chain(chain)
    assert ok, reason
    assert len(chain) == 11  # genesis + one block per /mine, none lost

    mined_tx = sum(
        1
        for b in chain[1:]
        for t in b.transactions
        if t.get("sender", "").startswith("u")
    )
    assert mined_tx + len(client.get("/tx").json()) == 60  # no tx lost or duplicated
