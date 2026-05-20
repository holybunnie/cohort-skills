"""Test `cohort backtest --demo` produces both scenarios with correct verdicts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    cmd = [
        sys.executable,
        str(ROOT / "skills" / "cohort" / "scripts" / "cohort.py"),
        "backtest", "--demo",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    print(out.stdout)
    if out.returncode != 0:
        print("FAIL: non-zero exit", out.stderr, file=sys.stderr)
        return 1
    fails = 0
    for needle in [
        "MODE: BACKTEST (demo)",
        "WEN — FOLLOW that worked",
        "Verdict at T=0:        FOLLOW",
        "RUGZ — AVOID that saved the user",
        "Verdict at T=0:        AVOID",
        "AVOID verdict prevented exposure",
    ]:
        if needle not in out.stdout:
            print(f"FAIL: missing {needle!r}", file=sys.stderr)
            fails += 1
    print()
    if fails:
        return 1
    # Also smoke a single-scenario filter
    cmd2 = [
        sys.executable,
        str(ROOT / "skills" / "cohort" / "scripts" / "cohort.py"),
        "backtest", "--demo", "--symbol", "RUGZ",
    ]
    out2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=20)
    if "WEN" in out2.stdout:
        print("FAIL: --symbol RUGZ leaked WEN scenario", file=sys.stderr)
        return 1
    if "RUGZ" not in out2.stdout:
        print("FAIL: --symbol RUGZ filter excluded RUGZ", file=sys.stderr)
        return 1
    print("OK   cohort backtest --demo prints both scenarios with correct verdicts.")
    print("OK   --symbol filter narrows correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
