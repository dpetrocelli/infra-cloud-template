"""Minimal proof-of-work blockchain, adapted from the SDyPP 2026 clase-11
lab (same hashing/difficulty rule) for the class-8 BC integrator case.

Standard library only. Deliberately small: read it once, then extend it in
the TPI (see contracts/ and the BC "Curso 3 - TPI.3" PoW spec).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field

GENESIS_PREV = "0" * 64


@dataclass
class Block:
    index: int
    previous_hash: str
    transactions: list[dict]
    difficulty: int
    timestamp: float = field(default_factory=time.time)
    nonce: int = 0
    hash: str = ""

    def header(self) -> str:
        payload = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": self.transactions,
            "difficulty": self.difficulty,
            "timestamp": self.timestamp,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def compute_hash(self, nonce: int | None = None) -> str:
        n = self.nonce if nonce is None else nonce
        return hashlib.sha256(f"{self.header()}{n}".encode()).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        return cls(**data)


def meets_difficulty(block_hash: str, difficulty: int) -> bool:
    """Difficulty = number of required leading hex zeros."""
    return block_hash.startswith("0" * difficulty)


def mine(block: Block, max_attempts: int = 5_000_000) -> tuple[int, int]:
    """Brute-force the nonce. Returns (nonce, attempts)."""
    header = block.header()
    target = "0" * block.difficulty
    nonce = 0
    while nonce < max_attempts:
        h = hashlib.sha256(f"{header}{nonce}".encode()).hexdigest()
        if h.startswith(target):
            block.nonce, block.hash = nonce, h
            return nonce, nonce + 1
        nonce += 1
    raise ValueError(f"no nonce found within {max_attempts} attempts")


def genesis(difficulty: int = 1) -> Block:
    b = Block(
        0,
        GENESIS_PREV,
        [{"msg": "genesis catedra infra-cloud"}],
        difficulty,
        timestamp=0.0,
    )
    mine(b)
    return b


def new_block(chain: list[Block], transactions: list[dict], difficulty: int) -> Block:
    last = chain[-1]
    return Block(last.index + 1, last.hash, transactions, difficulty)


def validate_chain(chain: list[Block]) -> tuple[bool, str]:
    """Re-validate every block. Never trust a chain that arrived over the network."""
    if not chain:
        return False, "empty chain"
    if chain[0].previous_hash != GENESIS_PREV:
        return False, "bad genesis previous_hash"

    for i, b in enumerate(chain):
        if b.index != i:
            return False, f"block {i}: bad index {b.index}"
        if i > 0 and b.previous_hash != chain[i - 1].hash:
            return False, f"block {i}: previous_hash does not match block {i - 1}"
        expected_hash = b.compute_hash()
        if expected_hash != b.hash:
            return False, f"block {i}: stored hash does not match recomputed hash"
        if not meets_difficulty(b.hash, b.difficulty):
            return False, f"block {i}: hash does not meet its own difficulty"
    return True, "ok"


def chain_work(chain: list[Block]) -> int:
    """Cumulative 'work' proxy used to pick the longest VALID chain.

    Real chains sum actual hash-power; here, for teaching purposes, work is
    approximated as 16**difficulty per block (more leading zeros == harder).
    """
    return sum(16**b.difficulty for b in chain)


def choose_best_chain(candidates: list[list[Block]]) -> list[Block] | None:
    """Longest-valid-chain rule: among all VALID candidates, keep the one
    with the most cumulative work (ties broken by chain length)."""
    best = None
    best_score = (-1, -1)
    for candidate in candidates:
        ok, _ = validate_chain(candidate)
        if not ok:
            continue
        score = (chain_work(candidate), len(candidate))
        if score > best_score:
            best_score = score
            best = candidate
    return best
