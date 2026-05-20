"""Test that `cohort watch --demo --once` exits cleanly and prints a cohort exit alert."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    cmd = [
        sys.executable,
        str(ROOT / "skills" / "cohort" / "scripts" / "cohort.py"),
        "watch", "--demo", "--once", "--speed", "0",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    print(out.stdout)
    if out.returncode != 0:
        print("FAIL: non-zero exit", out.stderr, file=sys.stderr)
        return 1
    if "MODE: WATCH (demo)" not in out.stdout:
        print("FAIL: missing demo mode banner", file=sys.stderr)
        return 1
    if "COHORT EXIT" not in out.stdout:
        print("FAIL: no cohort exit alert printed", file=sys.stderr)
        return 1
    print("OK   cohort watch --demo --once produces a cohort exit alert and exits clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
