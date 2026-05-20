"""End-to-end test of the COHORT MCP server over a real stdio pipe."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "skills" / "cohort" / "scripts" / "mcp_server.py"


def rpc(messages: list[dict]) -> list[dict]:
    """Send messages to the server, return parsed responses (skip notifications)."""
    payload = "\n".join(json.dumps(m) for m in messages) + "\n"
    out = subprocess.run(
        [sys.executable, str(SERVER)],
        input=payload, capture_output=True, text=True, timeout=30,
    )
    responses = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            responses.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return responses


def main() -> int:
    # 1. initialize
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "cohort_run", "arguments": {"demo": True}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "cohort_run", "arguments": {"demo": True, "weighted": True}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "cohort_backtest", "arguments": {"demo": True, "symbol": "WEN"}}},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
         "params": {"name": "cohort_follow_dry_run",
                    "arguments": {"symbol": "WEN",
                                  "token": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYLWbWQX1xx",
                                  "amount": 0.1, "chain": "solana", "demo": True}}},
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
         "params": {"name": "cohort_watch", "arguments": {"demo": True}}},
    ]
    responses = rpc(msgs)
    by_id = {r.get("id"): r for r in responses if "id" in r}

    failures = []

    init = by_id.get(1, {})
    if "result" not in init or init["result"].get("serverInfo", {}).get("name") != "cohort":
        failures.append(f"initialize: bad response {init}")

    tools = by_id.get(2, {}).get("result", {}).get("tools", [])
    tool_names = {t["name"] for t in tools}
    expected = {"cohort_run", "cohort_watch", "cohort_backtest", "cohort_follow_dry_run"}
    if not expected.issubset(tool_names):
        failures.append(f"tools/list missing: {expected - tool_names}")

    run = by_id.get(3, {}).get("result", {}).get("content", [{}])[0].get("text", "")
    if "MODE: DEMO" not in run or "FOLLOW" not in run:
        failures.append("cohort_run did not produce demo report")

    run_w = by_id.get(4, {}).get("result", {}).get("content", [{}])[0].get("text", "")
    if "WEIGHTED" not in run_w:
        failures.append("cohort_run --weighted: WEIGHTED column missing")

    bt = by_id.get(5, {}).get("result", {}).get("content", [{}])[0].get("text", "")
    if "MODE: BACKTEST" not in bt or "WEN" not in bt:
        failures.append("cohort_backtest missing expected output")

    follow = by_id.get(6, {}).get("result", {}).get("content", [{}])[0].get("text", "")
    if "DRY RUN" not in follow or "no funds moved" not in follow:
        failures.append("cohort_follow_dry_run missing DRY RUN banner")

    watch = by_id.get(7, {}).get("result", {}).get("content", [{}])[0].get("text", "")
    if "MODE: WATCH" not in watch:
        failures.append("cohort_watch missing WATCH banner")

    for r in responses:
        if "error" in r:
            failures.append(f"RPC error: {r['error']}")

    if failures:
        print("MCP server test FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"OK   MCP initialize → serverInfo.name=cohort")
    print(f"OK   tools/list returned {len(tools)} tools: {sorted(tool_names)}")
    print(f"OK   cohort_run produced demo report")
    print(f"OK   cohort_run weighted=True produced WEIGHTED column")
    print(f"OK   cohort_backtest WEN scenario produced output")
    print(f"OK   cohort_follow_dry_run printed DRY RUN banner (no funds path)")
    print(f"OK   cohort_watch printed WATCH banner")
    return 0


if __name__ == "__main__":
    sys.exit(main())
