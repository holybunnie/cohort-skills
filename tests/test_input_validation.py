"""Direct tests of the input-validation logic in cohort.py."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "cohort" / "scripts"))

import cohort  # noqa: E402


def main() -> int:
    cases = [
        # (label, fn, args, expected)
        ("solana valid", cohort.is_valid_token_address,
         ("EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYLWbWQX1xx", "solana"), True),
        ("solana too short", cohort.is_valid_token_address,
         ("abc", "solana"), False),
        ("solana invalid chars (0,O,I,l)", cohort.is_valid_token_address,
         ("0OIl000000000000000000000000000000000", "solana"), False),
        ("evm valid", cohort.is_valid_token_address,
         ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "ethereum"), True),
        ("evm wrong length", cohort.is_valid_token_address,
         ("0xA0b86991", "ethereum"), False),
        ("evm missing 0x", cohort.is_valid_token_address,
         ("A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "ethereum"), False),
    ]
    fails = 0
    for label, fn, args, expected in cases:
        got = fn(*args)
        ok = got == expected
        marker = "OK   " if ok else "FAIL "
        print(f"{marker} {label}: got={got} expected={expected}")
        if not ok:
            fails += 1
    if fails:
        print(f"\n{fails} test(s) failed")
        return 1
    print(f"\nAll {len(cases)} input-validation tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
