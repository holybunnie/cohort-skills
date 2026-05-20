#!/usr/bin/env python3
"""COHORT MCP server — exposes cohort_run / cohort_watch / cohort_backtest /
cohort_follow_dry_run as MCP tools over JSON-RPC 2.0 on stdio.

Installs into any MCP-compatible client (Claude Desktop, Cursor, Windsurf,
Claude Code via .mcp.json):

    {
      "mcpServers": {
        "cohort": {
          "command": "python3",
          "args": ["/abs/path/to/skills/cohort/scripts/mcp_server.py"]
        }
      }
    }

NO TRADES. The follow tool runs in dry-run mode only; broadcast still
requires the user's exact confirmation phrase to Claude in the chat, which
the agent translates to a separate `onchainos swap execute` call through
its normal tool layer — not through this MCP server.

Implementation: minimal MCP protocol surface — `initialize`, `tools/list`,
`tools/call`. No external SDK dependency. ~200 lines.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Lazy imports of the cohort engine so the server starts fast.
def _engine():
    import cohort
    return cohort

def _backtest():
    import backtest
    return backtest

def _watch():
    import watch
    return watch


PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "cohort", "version": "0.3.0"}

TOOLS = [
    {
        "name": "cohort_run",
        "description": "Find what smart money is converging on right now. Returns the cohort table with verdicts (FOLLOW / WATCH / AVOID). Pass weighted=true to use leaderboard-quality-weighted verdicts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chain":    {"type": "string", "default": "solana"},
                "demo":     {"type": "boolean", "default": False},
                "weighted": {"type": "boolean", "default": False}
            },
            "additionalProperties": False
        }
    },
    {
        "name": "cohort_watch",
        "description": "Real-time cohort sell-watch via okx-dex-ws. Returns one tick of cohort EXIT alerts (since this is a single MCP call, not a stream). For continuous streaming, run `cohort watch` directly in a terminal.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "wallets": {"type": "array", "items": {"type": "string"},
                            "description": "Cohort wallet addresses; if omitted, uses the top demo cohort."},
                "chain":   {"type": "string", "default": "solana"},
                "demo":    {"type": "boolean", "default": True}
            },
            "additionalProperties": False
        }
    },
    {
        "name": "cohort_backtest",
        "description": "Replay a historical cohort against price data and show what the verdict would have called at T=0 plus what actually happened. Demo mode includes a FOLLOW win case (WEN) and an AVOID escape (RUGZ).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Optional symbol filter (WEN, RUGZ in demo)"},
                "demo":   {"type": "boolean", "default": True}
            },
            "additionalProperties": False
        }
    },
    {
        "name": "cohort_follow_dry_run",
        "description": "Dry-run the gated follow flow for a token: quote + safety re-check + HARD STOP banner. Does NOT execute any trade; cannot be made to execute through this server. Use this to preview what a follow would look like before issuing the actual confirmation phrase to Claude.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "token":  {"type": "string"},
                "amount": {"type": "number"},
                "chain":  {"type": "string", "default": "solana"},
                "demo":   {"type": "boolean", "default": True}
            },
            "required": ["symbol", "token", "amount"],
            "additionalProperties": False
        }
    }
]


def _capture(fn) -> str:
    """Capture stdout of an int-returning function and return it as a string."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn()
    finally:
        sys.stdout = old
    return buf.getvalue()


def _ns(d: dict[str, Any]):
    """Tiny argparse.Namespace stand-in for sub-funcs."""
    import argparse
    return argparse.Namespace(**d)


def tool_cohort_run(args: dict[str, Any]) -> str:
    engine = _engine()
    return _capture(lambda: engine.cmd_run(_ns({
        "chain":    args.get("chain", "solana"),
        "demo":     bool(args.get("demo", False)),
        "dry_run":  False,
        "weighted": bool(args.get("weighted", False)),
        "json_out": None,
    })))


def tool_cohort_watch(args: dict[str, Any]) -> str:
    w = _watch()
    return _capture(lambda: w.cmd_watch(_ns({
        "wallets":  args.get("wallets"),
        "chain":    args.get("chain", "solana"),
        "demo":     bool(args.get("demo", True)),
        "fallback_to_demo": True,
        "interval": 2.0,
        "speed":    0.0,
        "once":     True,  # MCP calls are single-shot; the in-terminal command can stream
    })))


def tool_cohort_backtest(args: dict[str, Any]) -> str:
    bt = _backtest()
    return _capture(lambda: bt.cmd_backtest(_ns({
        "symbol":            args.get("symbol"),
        "token":             None,
        "chain":             "solana",
        "days":              30,
        "cohort_at_t_zero":  None,
        "demo":              bool(args.get("demo", True)),
    })))


def tool_cohort_follow_dry_run(args: dict[str, Any]) -> str:
    engine = _engine()
    return _capture(lambda: engine.cmd_follow(_ns({
        "symbol":  args["symbol"],
        "token":   args["token"],
        "amount":  float(args["amount"]),
        "chain":   args.get("chain", "solana"),
        "demo":    bool(args.get("demo", True)),
        "dry_run": True,   # FORCED — MCP path cannot broadcast
    })))


TOOL_HANDLERS = {
    "cohort_run":            tool_cohort_run,
    "cohort_watch":          tool_cohort_watch,
    "cohort_backtest":       tool_cohort_backtest,
    "cohort_follow_dry_run": tool_cohort_follow_dry_run,
}


def _ok(rid: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _err(rid: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def handle(msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method")
    rid = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        return _ok(rid, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        })

    if method == "notifications/initialized":
        return None  # notification — no response

    if method == "tools/list":
        return _ok(rid, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            return _err(rid, -32601, f"unknown tool: {name}")
        try:
            text = handler(args)
        except Exception as e:
            return _ok(rid, {
                "content": [{"type": "text", "text": f"tool error: {e}"}],
                "isError": True,
            })
        return _ok(rid, {
            "content": [{"type": "text", "text": text or "(no output)"}],
            "isError": False,
        })

    if method == "ping":
        return _ok(rid, {})

    return _err(rid, -32601, f"method not found: {method}")


def serve_stdio() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(msg)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(serve_stdio())
