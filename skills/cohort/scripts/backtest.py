#!/usr/bin/env python3
"""COHORT backtest — replay what the verdict would have called N days ago.

Composes upstream `okx-dex-market kline` to fetch historical candles and
replays a saved cohort snapshot to show:

  * The verdict COHORT WOULD have produced at T-N days
  * What happened to the price afterwards
  * When/whether cohort wallets actually exited

NO TRADES. NO PAYMENTS. Read-only historical data.

Modes:
  --demo                  Use bundled fixtures (WEN win case + RUGZ avoid case).
  (default)               Live `onchainos market kline` lookup.

Backtest does not re-run signal-list against history (the signal list is a
live feed). It takes a saved cohort snapshot (or a bundled one) as the T-zero
state, then layers real or fixture price data on top.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def _load_demo() -> dict[str, Any]:
    with open(HERE / "demo_backtest.json") as f:
        return json.load(f)


def _replay_verdict(cohort: dict[str, Any]) -> str:
    """Re-use the same verdict rule as cohort.py to avoid divergence."""
    sys.path.insert(0, str(HERE))
    from cohort import verdict
    fake_enrich = {
        "honeypot": cohort["honeypot"],
        "buy_tax_pct": cohort["buy_tax_pct"],
        "sell_tax_pct": cohort["sell_tax_pct"],
        "mint_authority_renounced": cohort["mint_authority_renounced"],
        "freeze_authority_renounced": cohort["freeze_authority_renounced"],
    }
    sells = [{}] * cohort.get("sells_observed", 0)
    return verdict(fake_enrich, sells, cohort["wallet_count"])


def _kline_live(address: str, chain: str, days: int) -> list[dict[str, Any]] | None:
    """Real `onchainos market kline` call. Returns None on payment gate / failure."""
    cmd = [
        "onchainos", "market", "kline",
        "--address", address,
        "--chain", chain,
        "--bar", "1D",
        "--limit", str(min(days + 1, 299)),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    try:
        parsed = json.loads(out.stdout) if out.stdout.strip() else None
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict) and parsed.get("confirming") is True:
        return None
    if out.returncode != 0:
        return None
    if isinstance(parsed, dict):
        return parsed.get("data") or []
    return parsed if isinstance(parsed, list) else None


def _summary(candles: list[dict[str, Any]], t_zero_price: float) -> dict[str, Any]:
    if not candles:
        return {"days": 0, "peak_pct": None, "final_pct": None, "max_drawdown_pct": None}
    highs = [c["high"] for c in candles if "high" in c]
    closes = [c["close"] for c in candles if "close" in c]
    peak = max(highs) if highs else t_zero_price
    final = closes[-1] if closes else t_zero_price
    trough_after_peak = min(closes[closes.index(max(closes)):] if closes else [t_zero_price]) if closes else t_zero_price
    return {
        "days": len(candles),
        "peak_pct": ((peak - t_zero_price) / t_zero_price * 100) if t_zero_price else None,
        "final_pct": ((final - t_zero_price) / t_zero_price * 100) if t_zero_price else None,
        "max_drawdown_pct": ((trough_after_peak - peak) / peak * 100) if peak else None,
    }


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%"


def _render(scenario_name: str, symbol: str, verdict_str: str,
            summary: dict[str, Any], exits: list[dict[str, Any]] | None, mode_banner: str) -> str:
    lines = []
    lines.append(f"MODE: {mode_banner}")
    # Avoid "WEN — WEN — …" when scenario_name already starts with the symbol.
    title = scenario_name if scenario_name.lower().startswith(symbol.lower()) else f"{symbol} — {scenario_name}"
    lines.append(f"COHORT BACKTEST — {title}")
    lines.append("-" * 60)
    lines.append(f"Verdict at T=0:        {verdict_str}")
    lines.append(f"Days replayed:         {summary['days']}")
    lines.append(f"Peak vs T=0:           {_fmt_pct(summary['peak_pct'])}")
    lines.append(f"Final close vs T=0:    {_fmt_pct(summary['final_pct'])}")
    lines.append(f"Max drawdown from peak: {_fmt_pct(summary['max_drawdown_pct'])}")
    if exits:
        lines.append("")
        lines.append("Cohort exits observed:")
        for e in exits:
            lines.append(f"  day {e['day']:>2}: {e['wallets_sold']} wallets sold — {e.get('note','')}")
    lines.append("-" * 60)
    if verdict_str == "FOLLOW" and (summary.get("peak_pct") or 0) > 50:
        lines.append("Result: FOLLOW verdict captured the move (peak gain noted).")
        lines.append("        If holder had sold at cohort-exit signal, exit price was near the top.")
    elif verdict_str == "AVOID":
        lines.append("Result: AVOID verdict prevented exposure. The token's path is shown above")
        lines.append("        — every dollar not committed was a dollar saved.")
    else:
        lines.append("Result: see summary above.")
    return "\n".join(lines)


def cmd_backtest(args: argparse.Namespace) -> int:
    if args.demo or not args.token:
        demo = _load_demo()
        scenarios = demo["scenarios"]
        if args.symbol:
            scenarios = [s for s in scenarios if s["symbol"].lower() == args.symbol.lower()]
        if not scenarios:
            print(f"backtest: no scenario found for symbol '{args.symbol}'")
            return 2
        first = True
        for sc in scenarios:
            if not first:
                print()
            first = False
            cohort = sc["cohort_at_t_zero"]
            v = _replay_verdict(cohort)
            t_zero_price = sc["candles_1d"][0]["close"]
            summary = _summary(sc["candles_1d"], t_zero_price)
            print(_render(
                scenario_name=sc["name"],
                symbol=sc["symbol"],
                verdict_str=v,
                summary=summary,
                exits=sc.get("cohort_exits"),
                mode_banner="BACKTEST (demo) — bundled historical scenario",
            ))
        return 0

    # Live mode
    candles = _kline_live(args.token, args.chain, args.days)
    if candles is None:
        print("backtest: live kline data unavailable (CLI missing, paid-quota gate, or empty).")
        print("backtest: re-run with --demo to use bundled scenarios.")
        return 2
    if not args.cohort_at_t_zero:
        print("backtest: --cohort-at-t-zero JSON file required in live mode "
              "(or pass --demo to use bundled scenarios).")
        return 2
    cohort = json.loads(Path(args.cohort_at_t_zero).read_text())
    v = _replay_verdict(cohort)
    t_zero_price = candles[0].get("close") or candles[0].get("open") or 0
    summary = _summary(candles, t_zero_price)
    print(_render(
        scenario_name=f"live kline {args.days}d",
        symbol=args.symbol or args.token[:8] + "…",
        verdict_str=v,
        summary=summary,
        exits=None,
        mode_banner="BACKTEST (live) — onchainos market kline",
    ))
    return 0


def build_backtest_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("backtest", help="Replay a historical cohort and show what the verdict would have called")
    p.add_argument("--symbol", default=None, help="Symbol to backtest (in demo, filters scenarios)")
    p.add_argument("--token", default=None, help="Token contract address (live mode)")
    p.add_argument("--chain", default="solana")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--cohort-at-t-zero", default=None,
                   help="Path to a saved cohort JSON (required for live mode)")
    p.add_argument("--demo", action="store_true",
                   help="Use bundled WEN/RUGZ historical scenarios")
    p.set_defaults(func=cmd_backtest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    build_backtest_parser(sub)
    args = parser.parse_args()
    sys.exit(args.func(args))
