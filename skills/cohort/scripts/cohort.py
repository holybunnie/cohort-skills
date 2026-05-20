#!/usr/bin/env python3
"""COHORT — Smart Money Convergence + Cohort Sell-Watch.

This is the engine the SKILL.md workflow delegates to. It composes real
OnchainOS CLI commands (when --demo is not set) or bundled fixtures.

It NEVER broadcasts a transaction by itself. Trade execution requires a
separate, explicit `confirm follow ...` invocation performed by the user
through Claude after reviewing the quote.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SUPPORTED_CHAINS = ["solana", "ethereum", "base", "bsc", "arbitrum", "polygon"]
SOLANA_ADDR_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
EVM_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
HERE = Path(__file__).resolve().parent


def is_valid_token_address(addr: str, chain: str) -> bool:
    if chain == "solana":
        return bool(SOLANA_ADDR_RE.match(addr))
    return bool(EVM_ADDR_RE.match(addr))


def load_demo() -> dict[str, Any]:
    with open(HERE / "demo_data.json") as f:
        return json.load(f)


def have_onchainos() -> bool:
    return shutil.which("onchainos") is not None


def run_onchainos(args: list[str]) -> dict[str, Any]:
    cmd = ["onchainos", *args, "--format", "json"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(f"onchainos failed: {' '.join(cmd)}\n{out.stderr}")
    return json.loads(out.stdout)


def aggregate_cohorts(signal_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group signal entries by token, count distinct SM wallets."""
    bucket: dict[str, dict[str, Any]] = {}
    for entry in signal_list:
        tok = entry["token_address"]
        bucket.setdefault(
            tok,
            {
                "token_address": tok,
                "name": entry.get("name", ""),
                "symbol": entry.get("symbol", ""),
                "wallets": set(),
            },
        )
        for w in entry.get("smart_money_wallets", []):
            bucket[tok]["wallets"].add(w)
    cohorts = []
    for c in bucket.values():
        cohorts.append({**c, "wallets": sorted(c["wallets"]), "wallet_count": len(c["wallets"])})
    cohorts.sort(key=lambda x: -x["wallet_count"])
    return cohorts[:5]


def verdict(enrich: dict[str, Any], sells: list[dict[str, Any]], cohort_size: int) -> str:
    if enrich.get("honeypot"):
        return "AVOID"
    if enrich.get("sell_tax_pct", 0) > 10 or enrich.get("buy_tax_pct", 0) > 10:
        return "AVOID"
    if not enrich.get("mint_authority_renounced") or not enrich.get("freeze_authority_renounced"):
        return "AVOID"
    if cohort_size > 0 and len(sells) / cohort_size >= 0.30:
        return "AVOID"
    if sells:
        return "WATCH"
    if cohort_size >= 4:
        return "FOLLOW"
    if cohort_size >= 3:
        return "WATCH"
    return "WATCH"


def build_report(mode: str, chain: str, data: dict[str, Any]) -> dict[str, Any]:
    cohorts = aggregate_cohorts(data["signal_list"])
    rows = []
    for c in cohorts:
        enrich = data["token_enrichment"].get(c["token_address"], {})
        sells = data["tracker_sells"].get(c["token_address"], [])
        rows.append(
            {
                "rank": len(rows) + 1,
                "symbol": c["symbol"],
                "name": c["name"],
                "token_address": c["token_address"],
                "wallet_count": c["wallet_count"],
                "sample_wallets": c["wallets"][:3],
                "price_usd": enrich.get("price_usd"),
                "market_cap_usd": enrich.get("market_cap_usd"),
                "liquidity_usd": enrich.get("liquidity_usd"),
                "change_24h_pct": enrich.get("change_24h_pct"),
                "honeypot": enrich.get("honeypot"),
                "buy_tax_pct": enrich.get("buy_tax_pct"),
                "sell_tax_pct": enrich.get("sell_tax_pct"),
                "mint_renounced": enrich.get("mint_authority_renounced"),
                "freeze_renounced": enrich.get("freeze_authority_renounced"),
                "sells_observed": len(sells),
                "verdict": verdict(enrich, sells, c["wallet_count"]),
            }
        )
    return {"mode": mode, "chain": chain, "generated_at": data.get("generated_at", ""), "rows": rows}


def fmt_usd(v: Any) -> str:
    if v is None:
        return "—"
    if v >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v/1_000:.1f}K"
    if v < 1:
        return f"${v:.7f}".rstrip("0").rstrip(".")
    return f"${v:.2f}"


def render_text_report(report: dict[str, Any]) -> str:
    lines = []
    lines.append(f"MODE: {report['mode']}")
    lines.append(f"COHORT — Smart Money Convergence — chain={report['chain']}")
    if report["generated_at"]:
        lines.append(f"Snapshot: {report['generated_at']}")
    lines.append("")
    header = f"{'#':<3}{'SYMBOL':<10}{'WALLETS':<8}{'PRICE':<14}{'MCAP':<10}{'TAX b/s':<10}{'SELLS':<7}{'VERDICT':<8}"
    lines.append(header)
    lines.append("-" * len(header))
    for r in report["rows"]:
        tax = f"{r.get('buy_tax_pct') or 0:.0f}/{r.get('sell_tax_pct') or 0:.0f}%"
        flag = ""
        if r.get("honeypot"):
            flag = "  HONEYPOT"
        elif not r.get("mint_renounced") or not r.get("freeze_renounced"):
            flag = "  MINT/FREEZE NOT RENOUNCED"
        lines.append(
            f"{r['rank']:<3}{r['symbol']:<10}{r['wallet_count']:<8}"
            f"{fmt_usd(r['price_usd']):<14}{fmt_usd(r['market_cap_usd']):<10}"
            f"{tax:<10}{r['sells_observed']:<7}{r['verdict']:<8}{flag}"
        )
    lines.append("")
    lines.append("Verdict legend: FOLLOW = strong convergence, clean safety, no exits.")
    lines.append("                WATCH  = converging but mixed signals or early exits.")
    lines.append("                AVOID  = honeypot, high tax, or cohort already exiting.")
    lines.append("")
    lines.append("Next actions:")
    lines.append("  - 'research <symbol>' — open per-token detail")
    lines.append("  - 'follow <symbol> <amount>' — gated buy (quote → STOP for confirmation)")
    lines.append("  - 'watch <symbol>' — start cohort sell-watch in background")
    return "\n".join(lines)


def cmd_run(args: argparse.Namespace) -> int:
    if args.chain not in SUPPORTED_CHAINS:
        print(f"cohort: chain '{args.chain}' is not in the supported list.")
        print(f"        Supported: {', '.join(SUPPORTED_CHAINS)}")
        return 2

    if args.demo:
        mode = "DEMO — using bundled fixtures, no network calls made"
        data = load_demo()
    elif not have_onchainos():
        mode = "DEMO (fallback — onchainos CLI not found, no network calls made)"
        data = load_demo()
    else:
        if args.dry_run:
            mode = "DRY RUN — real CLI data, NO funds moved, NO trades possible"
        else:
            mode = "LIVE — read-only analysis (no trades without explicit confirmation)"
        raw = run_onchainos(["signal", "list", "--chain", args.chain])
        signal_list = raw.get("data", raw) if isinstance(raw, dict) else raw
        enrich: dict[str, Any] = {}
        sells: dict[str, list] = {}
        for entry in signal_list[:5]:
            tok = entry["token_address"]
            try:
                p = run_onchainos(["token", "price-info", "--address", tok, "--chain", args.chain])
                a = run_onchainos(["token", "advanced-info", "--address", tok, "--chain", args.chain])
            except Exception as e:
                print(f"cohort: enrichment failed for {tok}: {e}", file=sys.stderr)
                continue
            enrich[tok] = {**(p.get("data", p) or {}), **(a.get("data", a) or {})}
            wallets = ",".join(entry.get("smart_money_wallets", [])[:20])
            if wallets:
                try:
                    s = run_onchainos(
                        ["tracker", "activities", "--tracker-type", "multi_address",
                         "--wallet-address", wallets, "--trade-type", "2", "--chain", args.chain]
                    )
                    sells[tok] = s.get("data", []) or []
                except Exception:
                    sells[tok] = []
        data = {
            "signal_list": signal_list,
            "token_enrichment": enrich,
            "tracker_sells": sells,
            "generated_at": "",
        }

    report = build_report(mode, args.chain, data)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2))
        print(f"cohort: wrote {args.json_out}")
    print(render_text_report(report))
    return 0


def cmd_follow(args: argparse.Namespace) -> int:
    """Gated trade flow. Always quotes. NEVER executes without explicit confirmation."""
    if not is_valid_token_address(args.token, args.chain):
        print(f"cohort: '{args.token}' does not look like a {args.chain} token address — skipping.")
        return 2
    if args.chain not in SUPPORTED_CHAINS:
        print(f"cohort: chain '{args.chain}' is not supported. Supported: {', '.join(SUPPORTED_CHAINS)}")
        return 2

    print(f"MODE: {'DRY RUN' if args.dry_run else 'GATED FOLLOW'} — confirmation required before any broadcast")
    print()
    if args.demo or not have_onchainos():
        print(f"[demo] would call: onchainos swap quote --from <native> --to {args.token} "
              f"--readable-amount {args.amount} --chain {args.chain}")
        print(f"[demo] quote: out=~{args.amount*0.98:.6f} (token), price impact 0.4%, route Jupiter")
    else:
        try:
            q = run_onchainos([
                "swap", "quote", "--from", "11111111111111111111111111111111",
                "--to", args.token, "--readable-amount", str(args.amount), "--chain", args.chain,
            ])
            print("Quote:")
            print(json.dumps(q.get("data", q), indent=2))
        except Exception as e:
            print(f"cohort: quote failed: {e}")
            return 1

    print()
    if args.dry_run:
        print("=" * 60)
        print("DRY RUN — no funds moved. No transaction was broadcast.")
        print("=" * 60)
        return 0

    print("=" * 60)
    print("HARD STOP — Claude must NOT call swap execute without the user")
    print("typing the following exact phrase in their next message:")
    print(f"  confirm follow {args.symbol} {args.amount}")
    print("Any other input cancels.")
    print("=" * 60)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Print whether onchainos is installed (used by `cohort pre-flight`)."""
    if have_onchainos():
        print("onchainos: FOUND on PATH")
        return 0
    print("onchainos: NOT FOUND — install from https://github.com/okx/onchainos-skills")
    print("           COHORT will fall back to demo mode.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cohort", description="Smart-money convergence + cohort sell-watch.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Discover what smart money is converging on")
    run.add_argument("--chain", default="solana")
    run.add_argument("--demo", action="store_true", help="Use bundled fixtures, no network")
    run.add_argument("--dry-run", action="store_true", help="Real CLI, but no trades possible")
    run.add_argument("--json-out", default=None, help="Also write structured report to this path")
    run.set_defaults(func=cmd_run)

    follow = sub.add_parser("follow", help="Gated trade flow (quote then STOP for confirmation)")
    follow.add_argument("--symbol", required=True)
    follow.add_argument("--token", required=True, help="Full token contract address")
    follow.add_argument("--amount", required=True, type=float, help="Amount in native token (SOL/ETH/...)")
    follow.add_argument("--chain", default="solana")
    follow.add_argument("--demo", action="store_true")
    follow.add_argument("--dry-run", action="store_true")
    follow.set_defaults(func=cmd_follow)

    check = sub.add_parser("check", help="Pre-flight: is onchainos installed?")
    check.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
