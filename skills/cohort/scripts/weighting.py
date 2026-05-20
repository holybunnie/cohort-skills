#!/usr/bin/env python3
"""Leaderboard-weighted cohort confidence.

A 3-wallet cohort of top-5 traders should beat a 6-wallet cohort of randoms.
This module fetches a leaderboard (live or bundled) and produces:

  - per-wallet weight (default 1.0; >1.0 for ranked traders)
  - weighted cohort size for use in the verdict

Tier scheme:
   rank ≤ 5    → weight 3.0  (top-5 SM trader)
   rank ≤ 25   → weight 2.0
   rank ≤ 100  → weight 1.5
   ranked but lower → 1.2
   unranked    → 1.0

NEVER triggers a trade. Read-only.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def _load_demo() -> dict[str, Any]:
    with open(HERE / "demo_leaderboard.json") as f:
        return json.load(f)


def _weight_for_rank(rank: int | None) -> float:
    if rank is None:
        return 1.0
    if rank <= 5:
        return 3.0
    if rank <= 25:
        return 2.0
    if rank <= 100:
        return 1.5
    return 1.2


def _index_leaderboard(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for e in entries:
        w = e.get("walletAddress") or e.get("wallet")
        if w:
            out[w] = e
    return out


def fetch_leaderboard(chain: str, demo: bool = False,
                      time_frame: int = 4, sort_by: int = 2) -> dict[str, dict[str, Any]]:
    """Return wallet → leaderboard entry dict.

    Args:
        chain: chain name (e.g. 'solana').
        demo: if True, use bundled fixture.
        time_frame: 1=1D, 2=3D, 3=7D, 4=1M, 5=3M (CLI `--time-frame`).
        sort_by: 1=PnL, 2=Win Rate, 3=Tx count, 4=Volume, 5=ROI (CLI `--sort-by`).
    """
    if demo:
        return _index_leaderboard(_load_demo()["entries"])
    cmd = [
        "onchainos", "leaderboard", "list",
        "--chain", chain,
        "--time-frame", str(time_frame),
        "--sort-by", str(sort_by),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    try:
        parsed = json.loads(out.stdout) if out.stdout.strip() else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict) and parsed.get("confirming") is True:
        return {}  # paid gate — gracefully degrade to default weight=1.0
    if out.returncode != 0 or not isinstance(parsed, (dict, list)):
        return {}
    entries = parsed.get("data") if isinstance(parsed, dict) else parsed
    return _index_leaderboard(entries or [])


def weighted_cohort_size(wallets: list[str], leaderboard: dict[str, dict[str, Any]]) -> float:
    total = 0.0
    for w in wallets:
        entry = leaderboard.get(w)
        rank = entry.get("rank") if entry else None
        total += _weight_for_rank(rank)
    return total


def wallet_weights(wallets: list[str], leaderboard: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-wallet breakdown for display."""
    rows = []
    for w in wallets:
        entry = leaderboard.get(w)
        rows.append({
            "wallet": w,
            "rank": entry.get("rank") if entry else None,
            "winRate": entry.get("winRate") if entry else None,
            "weight": _weight_for_rank(entry.get("rank") if entry else None),
        })
    return rows
