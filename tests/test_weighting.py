"""Test `cohort run --demo --weighted` promotes PYTH from WATCH to FOLLOW
because all 3 PYTH cohort wallets are top-25 leaderboard traders."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    cmd = [
        sys.executable,
        str(ROOT / "skills" / "cohort" / "scripts" / "cohort.py"),
        "run", "--demo", "--weighted",
        "--json-out", "/tmp/cohort_weighted.json",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    print(out.stdout)
    if out.returncode != 0:
        print("FAIL: non-zero exit", out.stderr, file=sys.stderr)
        return 1
    if "WEIGHTED" not in out.stdout:
        print("FAIL: WEIGHTED column missing from header", file=sys.stderr)
        return 1
    if "WEN" not in out.stdout or "PYTH" not in out.stdout:
        print("FAIL: rows missing", file=sys.stderr)
        return 1

    report = json.loads(Path("/tmp/cohort_weighted.json").read_text())
    if not report.get("weighted"):
        print("FAIL: report.weighted flag not set", file=sys.stderr)
        return 1

    row_by_symbol = {r["symbol"]: r for r in report["rows"]}
    pyth = row_by_symbol["PYTH"]
    if pyth["wallet_count"] != 3:
        print(f"FAIL: PYTH wallet_count expected 3 got {pyth['wallet_count']}", file=sys.stderr)
        return 1
    if pyth["weighted_count"] is None or pyth["weighted_count"] < 5.0:
        print(f"FAIL: PYTH weighted_count expected >= 5.0, got {pyth['weighted_count']}", file=sys.stderr)
        return 1
    if pyth["verdict"] != "FOLLOW":
        print(f"FAIL: weighted PYTH should be FOLLOW, got {pyth['verdict']}", file=sys.stderr)
        return 1

    # And without --weighted, PYTH should be WATCH (3 wallets, no sells)
    cmd2 = [sys.executable, str(ROOT / "skills" / "cohort" / "scripts" / "cohort.py"),
            "run", "--demo", "--json-out", "/tmp/cohort_plain.json"]
    subprocess.run(cmd2, capture_output=True, text=True, timeout=20)
    plain = json.loads(Path("/tmp/cohort_plain.json").read_text())
    plain_pyth = next(r for r in plain["rows"] if r["symbol"] == "PYTH")
    if plain_pyth["verdict"] != "WATCH":
        print(f"FAIL: unweighted PYTH should be WATCH, got {plain_pyth['verdict']}", file=sys.stderr)
        return 1

    print("OK   PYTH: WATCH (unweighted) → FOLLOW (weighted, all 3 wallets top-25)")
    print(f"OK   WEN weighted_count: {row_by_symbol['WEN']['weighted_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
