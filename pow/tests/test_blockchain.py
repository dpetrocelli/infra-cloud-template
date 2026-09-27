from blockchain import (
    Block,
    choose_best_chain,
    genesis,
    mine,
    new_block,
    validate_chain,
)


def test_genesis_meets_its_own_difficulty():
    g = genesis(difficulty=1)
    assert g.hash.startswith("0")


def test_mine_produces_valid_hash():
    g = genesis(difficulty=1)
    b = new_block([g], [{"a": 1}], difficulty=1)
    nonce, attempts = mine(b)
    assert b.hash.startswith("0")
    assert attempts >= 1
    assert b.nonce == nonce


def test_validate_chain_detects_tampering():
    g = genesis(difficulty=1)
    b1 = new_block([g], [{"a": 1}], difficulty=1)
    mine(b1)
    chain = [g, b1]
    ok, _ = validate_chain(chain)
    assert ok

    # tamper with a transaction after mining: hash no longer matches
    chain[1].transactions = [{"a": 999}]
    ok, reason = validate_chain(chain)
    assert not ok
    assert "hash" in reason


def test_choose_best_chain_picks_longest_valid():
    g = genesis(difficulty=1)
    short_chain = [g]

    long_chain = [g]
    for i in range(2):
        b = new_block(long_chain, [{"i": i}], difficulty=1)
        mine(b)
        long_chain.append(b)

    best = choose_best_chain([short_chain, long_chain])
    assert best is not None
    assert len(best) == len(long_chain)


def test_choose_best_chain_ignores_invalid_candidates():
    g = genesis(difficulty=1)
    b1 = new_block([g], [{"a": 1}], difficulty=1)
    mine(b1)
    valid_chain = [g, b1]

    broken = Block(0, "0" * 64, [{"x": 1}], 1, timestamp=0.0)  # never mined, bad hash
    invalid_chain = [broken]

    best = choose_best_chain([invalid_chain, valid_chain])
    assert best == valid_chain
