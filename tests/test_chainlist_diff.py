from src.chainlist_diff import diff_new_chains, normalize_chains


def test_normalize_chains_keys_by_chain_id():
    raw = [
        {"chainId": 1, "name": "Mainnet"},
        {"chainId": "10", "name": "Optimism"},
    ]
    normalized = normalize_chains(raw)
    assert set(normalized.keys()) == {"1", "10"}


def test_diff_new_chains_detects_new_ids():
    current = normalize_chains(
        [
            {"chainId": 1, "name": "Mainnet", "rpc": ["a"], "explorers": []},
            {
                "chainId": 2,
                "name": "Chain Two",
                "nativeCurrency": {"symbol": "TWO"},
                "rpc": ["a", "b"],
                "explorers": [{"url": "https://example.com"}],
            },
        ]
    )
    previous = normalize_chains([{"chainId": 1, "name": "Mainnet"}])

    rows = diff_new_chains(current, previous)

    assert len(rows) == 1
    row = rows[0]
    assert row.chain_id == "2"
    assert row.name == "Chain Two"
    assert row.native_symbol == "TWO"
    assert row.rpc_count == 2
    assert row.explorer_url == "https://example.com"
