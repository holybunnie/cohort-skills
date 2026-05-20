#!/usr/bin/env python3
"""Render a COHORT report JSON to a self-contained HTML page."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path


def fmt_usd(v):
    if v is None:
        return "—"
    if v >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v/1_000:.1f}K"
    if v < 1:
        return f"${v:.7f}".rstrip("0").rstrip(".")
    return f"${v:.2f}"


def verdict_class(v: str) -> str:
    return {"FOLLOW": "ok", "WATCH": "warn", "AVOID": "bad"}.get(v, "")


TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>COHORT — {chain}</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ font-family: -apple-system, system-ui, sans-serif; background: #0b0e14; color: #d6deeb; margin: 0; padding: 32px; }}
  h1 {{ margin: 0 0 4px; font-weight: 600; }}
  .mode {{ background: #1e3a5f; color: #aee; padding: 6px 12px; border-radius: 4px; display: inline-block; margin-bottom: 24px; font-family: monospace; font-size: 13px; }}
  .mode.demo {{ background: #4a3a1f; color: #fda; }}
  .mode.dry {{ background: #3a1f1f; color: #faa; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 1200px; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #1e2436; }}
  th {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #6f7c98; }}
  tr.verdict-ok td.v {{ color: #6ee7a0; font-weight: 600; }}
  tr.verdict-warn td.v {{ color: #ffd166; font-weight: 600; }}
  tr.verdict-bad td.v {{ color: #ff6e6e; font-weight: 600; }}
  .small {{ font-size: 11px; color: #6f7c98; font-family: monospace; }}
  .flag {{ display: inline-block; background: #3a1f1f; color: #ff8a8a; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-left: 6px; }}
  footer {{ margin-top: 32px; color: #6f7c98; font-size: 12px; }}
</style></head><body>
<h1>COHORT — Smart Money Convergence</h1>
<div class="small">chain={chain} · generated_at={generated_at}</div>
<div class="mode {mode_class}">MODE: {mode}</div>
<table><thead><tr>
  <th>#</th><th>Symbol</th><th>Wallets</th><th>Price</th><th>MCap</th>
  <th>Liquidity</th><th>Tax b/s</th><th>Sells</th><th>Verdict</th>
</tr></thead><tbody>
{rows}
</tbody></table>
<footer>
  Verdict legend: <b>FOLLOW</b> = strong convergence, clean safety, no exits. <b>WATCH</b> = mixed signals or early exits. <b>AVOID</b> = honeypot, high tax, or cohort already exiting.<br>
  Sell-watch is wired through <code>onchainos tracker activities --tracker-type multi_address --trade-type 2</code> on the exact wallets that discovered the cohort.
</footer>
</body></html>
"""


def render(report: dict) -> str:
    rows_html = []
    for r in report["rows"]:
        flag = ""
        if r.get("honeypot"):
            flag = '<span class="flag">HONEYPOT</span>'
        elif not r.get("mint_renounced") or not r.get("freeze_renounced"):
            flag = '<span class="flag">MINT/FREEZE LIVE</span>'
        tax = f"{(r.get('buy_tax_pct') or 0):.0f}/{(r.get('sell_tax_pct') or 0):.0f}%"
        v = r["verdict"]
        rows_html.append(
            f'<tr class="verdict-{verdict_class(v)}">'
            f'<td>{r["rank"]}</td>'
            f'<td><b>{html.escape(r["symbol"])}</b>{flag}<div class="small">{html.escape(r["name"])}</div></td>'
            f'<td>{r["wallet_count"]}</td>'
            f'<td>{fmt_usd(r.get("price_usd"))}</td>'
            f'<td>{fmt_usd(r.get("market_cap_usd"))}</td>'
            f'<td>{fmt_usd(r.get("liquidity_usd"))}</td>'
            f'<td>{tax}</td>'
            f'<td>{r["sells_observed"]}</td>'
            f'<td class="v">{html.escape(v)}</td>'
            f"</tr>"
        )

    mode = report["mode"]
    mode_class = ""
    if mode.startswith("DEMO"):
        mode_class = "demo"
    elif "DRY RUN" in mode:
        mode_class = "dry"

    return TEMPLATE.format(
        chain=html.escape(report["chain"]),
        generated_at=html.escape(report.get("generated_at", "") or "—"),
        mode=html.escape(mode),
        mode_class=mode_class,
        rows="\n".join(rows_html),
    )


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Report JSON from cohort.py --json-out")
    p.add_argument("--output", required=True, help="HTML output path")
    args = p.parse_args(argv)
    report = json.loads(Path(args.input).read_text())
    Path(args.output).write_text(render(report))
    print(f"report: wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
