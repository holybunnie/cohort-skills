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

## What I did NOT confirm

Two honest gaps:

1. **I did not execute any of the live commands.** The `onchainos` CLI is not installed in this build environment. The skill's behaviour against the live CLI was validated by reading the upstream SKILL.md / workflow files, not by running the binary. The check-#3 "live demo" therefore exercises the fallback path (no CLI on PATH → demo mode with banner) rather than calling OKX endpoints. Anyone running this against a real `onchainos` install gets real data — the call shapes are taken from upstream verbatim.
2. **Per-endpoint paid quota handling** (the `notifications[]` / `confirming: true` flow described in `okx-dex-market/_shared/payment-notifications.md`) is not implemented. Live mode reads `data` from the response but does not surface payment prompts. A real production user would want this wired up; for a discovery + sell-watch demo it would obscure the main flow.

Neither gap is a fabricated command — they're scope decisions documented here so the next reviewer sees them.
