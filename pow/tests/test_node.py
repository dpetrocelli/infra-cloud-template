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
