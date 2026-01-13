"""Fetch Chainlist RPCs, detect new chains, and update snapshot."""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.emailer import send_email

SNAPSHOT_PATH = Path("data/chainlist_snapshot.json")
CHAINLIST_URL = "https://chainlist.org/rpcs.json"
USER_AGENT = "weekly-chainlist/1.0 (+https://github.com)"
TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class ChainReportRow:
    chain_id: str
    name: str
    native_symbol: str
    rpc_count: int
    explorer_url: str


def _chain_id_key(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def fetch_rpcs(url: str = CHAINLIST_URL) -> list[dict[str, Any]]:
    logging.info("Fetching chainlist data from %s", url)
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Expected list payload from chainlist")
    return data


def normalize_chains(raw_chains: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for chain in raw_chains:
        if not isinstance(chain, dict):
            continue
        chain_id = chain.get("chainId")
        if chain_id is None:
            continue
        chain_id_str = str(chain_id)
        normalized[chain_id_str] = chain
    return normalized


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        logging.info("Snapshot not found at %s, starting fresh", path)
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Snapshot must be a JSON object keyed by chainId")
    return data


def write_snapshot(snapshot: dict[str, dict[str, Any]], path: Path = SNAPSHOT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")


def diff_new_chains(
    current: dict[str, dict[str, Any]],
    previous: dict[str, dict[str, Any]],
) -> list[ChainReportRow]:
    previous_ids = set(previous.keys())
    new_rows: list[ChainReportRow] = []
    for chain_id, chain in current.items():
        if chain_id in previous_ids:
            continue
        name = str(chain.get("name") or "")
        native_symbol = ""
        native_currency = chain.get("nativeCurrency")
        if isinstance(native_currency, dict):
            native_symbol = str(native_currency.get("symbol") or "")
        rpcs = chain.get("rpc")
        rpc_count = len(rpcs) if isinstance(rpcs, list) else 0
        explorer_url = ""
        explorers = chain.get("explorers")
        if isinstance(explorers, list) and explorers:
            first = explorers[0]
            if isinstance(first, dict):
                explorer_url = str(first.get("url") or "")
        new_rows.append(
            ChainReportRow(
                chain_id=chain_id,
                name=name,
                native_symbol=native_symbol,
                rpc_count=rpc_count,
                explorer_url=explorer_url,
            )
        )
    new_rows.sort(key=lambda row: _chain_id_key(row.chain_id))
    return new_rows


def render_html_report(rows: list[ChainReportRow]) -> str:
    header = (
        "<tr>"
        "<th>chainId</th>"
        "<th>name</th>"
        "<th>nativeCurrency symbol</th>"
        "<th>rpc count</th>"
        "<th>first explorer URL</th>"
        "</tr>"
    )
    body_rows = []
    for row in rows:
        body_rows.append(
            "<tr>"
            f"<td>{row.chain_id}</td>"
            f"<td>{row.name}</td>"
            f"<td>{row.native_symbol}</td>"
            f"<td>{row.rpc_count}</td>"
            f"<td>{row.explorer_url}</td>"
            "</tr>"
        )
    body = "".join(body_rows)
    return f"<table>{header}{body}</table>"


def build_subject(count: int) -> str:
    date_stamp = datetime.now(timezone.utc).date().isoformat()
    return f"[Chainlist] {count} new chain(s) - {date_stamp}"


def parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y"}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    send_if_zero = parse_bool(os.getenv("SEND_IF_ZERO"))

    try:
        current_raw = fetch_rpcs()
    except Exception as exc:  # pragma: no cover - network errors
        logging.error("Failed to fetch chainlist data: %s", exc)
        return 1

    current_snapshot = normalize_chains(current_raw)
    try:
        previous_snapshot = load_snapshot()
    except Exception as exc:
        logging.error("Failed to load snapshot: %s", exc)
        return 1

    new_rows = diff_new_chains(current_snapshot, previous_snapshot)
    new_count = len(new_rows)
    logging.info("Found %s new chain(s)", new_count)

    if new_count == 0 and not send_if_zero:
        logging.info("No new chains and SEND_IF_ZERO is false; skipping email.")
    else:
        subject = build_subject(new_count)
        if new_count == 0:
            html_body = "<p>No new chains were detected this week.</p>"
        else:
            html_body = render_html_report(new_rows)
        try:
            send_email(subject=subject, html_body=html_body)
        except Exception as exc:
            logging.error("Failed to send email: %s", exc)
            return 1

    try:
        write_snapshot(current_snapshot)
    except Exception as exc:
        logging.error("Failed to write snapshot: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
