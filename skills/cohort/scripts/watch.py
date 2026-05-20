#!/usr/bin/env python3
"""COHORT watch — real-time cohort sell-watch via `onchainos ws`.

Composes upstream `okx-dex-ws` commands:

    onchainos ws start  --channel address-tracker-activity --wallet-addresses <list>
    onchainos ws poll   --id <session_id>
    onchainos ws stop   --id <session_id>

NEVER triggers a trade. NEVER auto-pays the OKX paid-quota gate.

Modes:
  --demo                  Replay bundled fixtures with synthetic delays.
  --dry-run               Real CLI; ws session is real; trades disabled by virtue
                          of this being a read-only feed.
  (default)               Same as --dry-run from a trade-safety POV — there is
                          no trade path in this command at all.

Use --once for a single poll tick (used by tests).
"""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def _load_demo_events() -> list[dict[str, Any]]:
    with open(HERE / "demo_watch_events.json") as f:
        return json.load(f)["events"]


def _format_alert(event: dict[str, Any], cohort_wallets: set[str], cohort_size: int,
                  seen_sells: dict[str, set[str]]) -> str | None:
    """Render an alert line. Returns None if the event isn't a cohort sell."""
    wallet = event.get("wallet", "")
    if wallet not in cohort_wallets:
        return None
    trade_type = event.get("tradeType")
    if trade_type != 2:
        return None  # not a sell
    token = event.get("tokenAddress", "")
    symbol = event.get("tokenSymbol", "?")
    amount = event.get("amountUsd", "?")
    price = event.get("price", "?")
    ts = event.get("ts", "")
    seen_sells.setdefault(token, set()).add(wallet)
    sold_count = len(seen_sells[token])
    return (
        f"[{ts}] COHORT EXIT — {symbol}\n"
        f"  wallet {wallet[:6]}…{wallet[-4:]} sold ${amount} at ${price}\n"
        f"  {sold_count}/{cohort_size} cohort wallets have now sold this token"
    )


def _ws_start(channel: str, wallet_addresses: list[str], chain: str) -> str:
    cmd = [
        "onchainos", "ws", "start",
        "--channel", channel,
        "--wallet-addresses", ",".join(wallet_addresses[:200]),
        "--chain", chain,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if out.returncode != 0:
        raise RuntimeError(f"ws start failed: {out.stderr or out.stdout[:200]}")
    parsed = json.loads(out.stdout)
    sid = parsed.get("data", {}).get("id") or parsed.get("id")
    if not sid:
        raise RuntimeError(f"ws start returned no session id: {out.stdout[:200]}")
    return sid


def _ws_poll(sid: str, channel: str) -> list[dict[str, Any]]:
    cmd = ["onchainos", "ws", "poll", "--id", sid, "--channel", channel]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if out.returncode != 0:
        return []
    try:
        parsed = json.loads(out.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        return parsed.get("data") or parsed.get("events") or []
    return parsed if isinstance(parsed, list) else []


def _ws_stop(sid: str) -> None:
    subprocess.run(["onchainos", "ws", "stop", "--id", sid],
                   capture_output=True, text=True, timeout=10)


def watch_demo(cohort_wallets: list[str], cohort_size: int,
               speed: float, once: bool) -> int:
    """Replay bundled events; no network, no CLI."""
    print("MODE: WATCH (demo) — replaying bundled sell events, no network")
    print(f"Tracking {len(cohort_wallets)} cohort wallets; tradeType=2 (sells) only")
    print("Press Ctrl+C to stop.")
    print("-" * 60)
    seen: dict[str, set[str]] = {}
    cw = set(cohort_wallets)
    events = _load_demo_events()
    printed_any = False
    for entry in events:
        time.sleep(min(entry["delay_s"], 0.05) if speed == 0 else entry["delay_s"] / speed)
        alert = _format_alert(entry["event"], cw, cohort_size, seen)
        if alert:
            print(alert)
            print()
            printed_any = True
            if once:
                break
    if not printed_any:
        print("(no cohort sells in this replay)")
    print("-" * 60)
    print("watch (demo): replay complete.")
    return 0


def watch_live(cohort_wallets: list[str], cohort_size: int,
               chain: str, interval_s: float, once: bool) -> int:
    """Real `onchainos ws` session. Read-only."""
    if not cohort_wallets:
        print("watch: no cohort wallets supplied; nothing to watch.")
        return 2
    print(f"MODE: WATCH (live) — starting real ws session on {chain}")
    print(f"Tracking {len(cohort_wallets)} cohort wallets; tradeType=2 (sells) only")
    try:
        sid = _ws_start("address-tracker-activity", cohort_wallets, chain)
    except Exception as e:
        print(f"watch: ws start failed: {e}")
        print("watch: falling back to demo replay.")
        return watch_demo(cohort_wallets, cohort_size, speed=1.0, once=once)
    print(f"ws session: {sid}")
    print("Press Ctrl+C to stop.")
    print("-" * 60)
    seen: dict[str, set[str]] = {}
    cw = set(cohort_wallets)
    stop_flag = {"stop": False}

    def _signal_handler(signum, frame):  # noqa: ANN001
        stop_flag["stop"] = True
    signal.signal(signal.SIGINT, _signal_handler)
    try:
        while not stop_flag["stop"]:
            events = _ws_poll(sid, "address-tracker-activity")
            for ev in events:
                alert = _format_alert(ev, cw, cohort_size, seen)
                if alert:
                    print(alert)
                    print()
            if once:
                break
            time.sleep(interval_s)
    finally:
        print("-" * 60)
        print("watch: stopping ws session.")
        try:
            _ws_stop(sid)
        except Exception:
            pass
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """Entry point — called by cohort.py's `watch` subparser."""
    cohort_wallets = list(args.wallets) if args.wallets else []
    # Default: derive from demo data if no wallets supplied (helpful for testing)
    if not cohort_wallets and (args.demo or args.fallback_to_demo):
        from cohort import load_demo, aggregate_cohorts  # local import to avoid cycle
        cohorts = aggregate_cohorts(load_demo()["signal_list"])
        if cohorts:
            cohort_wallets = cohorts[0]["wallets"]
            print(f"watch: no --wallets given; using top cohort from demo "
                  f"({cohorts[0]['symbol']}, {len(cohort_wallets)} wallets)")
    cohort_size = len(cohort_wallets)
    if args.demo:
        return watch_demo(cohort_wallets, cohort_size,
                          speed=args.speed, once=args.once)
    return watch_live(cohort_wallets, cohort_size,
                      chain=args.chain, interval_s=args.interval, once=args.once)


def build_watch_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("watch", help="Real-time cohort sell-watch via okx-dex-ws")
    p.add_argument("--wallets", nargs="*", default=None,
                   help="Cohort wallet addresses (space-separated). If omitted in demo, "
                        "top cohort from bundled fixtures is used.")
    p.add_argument("--chain", default="solana")
    p.add_argument("--demo", action="store_true",
                   help="Replay bundled events; no CLI required.")
    p.add_argument("--fallback-to-demo", action="store_true",
                   help="When derived wallets is empty in live mode, fall back to demo.")
    p.add_argument("--interval", type=float, default=2.0,
                   help="Poll interval in seconds (live mode only).")
    p.add_argument("--speed", type=float, default=1.0,
                   help="Demo replay speed multiplier (set 0 for instant).")
    p.add_argument("--once", action="store_true",
                   help="Single tick / single matched event then exit (for tests).")
    p.set_defaults(func=cmd_watch)


if __name__ == "__main__":  # standalone smoke test
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    build_watch_parser(sub)
    args = parser.parse_args()
    sys.exit(args.func(args))
