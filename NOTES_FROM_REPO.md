# NOTES_FROM_REPO.md

> Required by check #1: every CLI command COHORT issues, confirmed against the official OnchainOS reference at <https://github.com/okx/onchainos-skills>.

The reference repo was cloned at build time to `/tmp/onchainos-ref` and each command below was located in a named source file. Nothing is paraphrased — the file path is the proof.

## Commands COHORT issues — all confirmed in upstream

| # | COHORT call | Upstream source (in `okx/onchainos-skills`) |
|---|---|---|
| 1 | `onchainos signal list --chain <chain>` | `workflows/smart-money-signals.md` step 1; `skills/okx-dex-signal/SKILL.md` Commands table cmd #3 |
| 2 | `onchainos signal chains` | `skills/okx-dex-signal/SKILL.md` Commands table cmd #2 (used to validate `--chain`) |
| 3 | `onchainos token price-info --address <token> --chain <chain>` | `workflows/smart-money-signals.md` step 2 |
| 4 | `onchainos token advanced-info --address <token> --chain <chain>` | `workflows/smart-money-signals.md` step 2 |
| 5 | `onchainos security token-scan --tokens "<chainIndex>:<token>"` | `workflows/smart-money-signals.md` step 2 |
| 6 | `onchainos tracker activities --tracker-type multi_address --wallet-address <wallets> --trade-type 2 --chain <chain>` | `workflows/wallet-monitor.md` step 2 (multi-address polling) + `skills/okx-dex-signal/SKILL.md` step 1 (`--trade-type 2` = sell-only; "Multiple addresses comma-separated, max 20") |
| 7 | `onchainos wallet status` | `skills/okx-dex-swap/SKILL.md` step 2 ("Wallet: run `onchainos wallet status`") |
| 8 | `onchainos swap quote --from --to --readable-amount --chain` | `skills/okx-dex-swap/SKILL.md` Command Index cmd #4 |
| 9 | `onchainos swap execute --from --to --readable-amount --chain --wallet` | `skills/okx-dex-swap/SKILL.md` Command Index cmd #5 |

Every row in this table maps a COHORT step to a real upstream file. No `onchainos cohort ...` subcommand exists or is fabricated; COHORT composes the above in Python.

## What I substituted, and why

- **Memepump enrichment** (`onchainos memepump token-dev-info`, `token-bundle-info`) is referenced in `smart-money-signals.md` only when `advanced-info.protocolId` is non-empty. The COHORT engine declines to call these in live mode rather than guessing the shape — the report renders without them. The demo fixtures include `dev_holding_pct` / `bundle_pct` so the table column structure is exercised.
- **`--mev-protection`, `--force`, `--gas-level`** (all valid `swap execute` flags per the upstream SKILL) are intentionally NOT exposed by COHORT. Adding them would require defaulting them, and a wrong default could spend more or bypass risk warning 81362. If a user wants these, they pass them in via a future user-facing wrapper; the engine does not opt into them.
- **`--format json`**: the upstream CLAUDE.md says scripts should append `--format json` to all CLI commands. COHORT does this in `run_onchainos()`.

## Verified against the actual installed CLI

After the first version of this file was written, both the `onchainos` CLI binary and the upstream skills plugin were installed in this codespace and every command above was verified against the live `--help` output:

```
onchainos --version
  → onchainos 3.3.6
~/.claude/plugins/marketplaces/onchainos-skills/.claude-plugin/plugin.json   (22 SKILL.md files)
```

All 9 commands pass `onchainos <cmd> --help` without error. The load-bearing one — `onchainos tracker activities --tracker-type multi_address --wallet-address <...> --trade-type 2` — has its flags confirmed verbatim by the CLI's own help text (`Trade type: 0=all (default), 1=buy, 2=sell`, `Wallet addresses (required for multi_address), comma-separated, max 20`).

## What I did NOT confirm

One honest gap:

- **No live signal/tracker data was retrieved.** A fresh CLI install returns `{"confirming": true, "notifications": [...]}` on every market-API call — the free quota for this install is exhausted and the endpoint requires per-call payment via the OKX Agent Payments Protocol. COHORT detects this in `run_onchainos()`, surfaces the gate in plain English, and falls back to demo mode. To get real data through COHORT, the user needs to resolve the gate through the upstream `okx-agent-payments-protocol` skill — COHORT will not auto-pay.

This is not a fabricated command; it's an honest interaction with a paid API that COHORT handles instead of pretending to succeed.
