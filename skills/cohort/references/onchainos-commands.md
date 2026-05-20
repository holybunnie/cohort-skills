# OnchainOS Command Cross-Reference

Every CLI command COHORT delegates to, with its source in the upstream `okx/onchainos-skills` repo. This file exists so reviewers (and Claude) can verify each command without guessing.

Upstream: <https://github.com/okx/onchainos-skills>

| COHORT step | Command | Source file in upstream | Verified |
|---|---|---|---|
| 1. Collect signals | `onchainos signal list --chain <chain>` | `workflows/smart-money-signals.md` step 1; `skills/okx-dex-signal/SKILL.md` cmd #3 | yes |
| 1a. Validate chain | `onchainos signal chains` | `skills/okx-dex-signal/SKILL.md` cmd #2 | yes |
| 2. Per-token price | `onchainos token price-info --address <token> --chain <chain>` | `workflows/smart-money-signals.md` step 2 | yes |
| 2. Per-token advanced | `onchainos token advanced-info --address <token> --chain <chain>` | `workflows/smart-money-signals.md` step 2 | yes |
| 2. Token security scan | `onchainos security token-scan --tokens "<chainIndex>:<token>"` | `workflows/smart-money-signals.md` step 2 | yes |
| 3. Cohort sell-watch (load-bearing) | `onchainos tracker activities --tracker-type multi_address --wallet-address <wallets> --trade-type 2 --chain <chain>` | `workflows/wallet-monitor.md` step 2 + `skills/okx-dex-signal/SKILL.md` step 1 ("`--trade-type` defaults to `0` (all); use `1` for buy-only, `2` for sell-only", "Multiple addresses comma-separated, max 20") | yes |
| 5a. Wallet status | `onchainos wallet status` | `skills/okx-dex-swap/SKILL.md` step 2 ("Wallet: run `onchainos wallet status`") | yes |
| 5b. Quote | `onchainos swap quote --from <addr> --to <addr> --readable-amount <n> --chain <chain>` | `skills/okx-dex-swap/SKILL.md` cmd #4 | yes |
| 5c. Execute (gated) | `onchainos swap execute --from --to --readable-amount --chain --wallet [--force]` | `skills/okx-dex-swap/SKILL.md` cmd #5 | yes |

## Substitutions / things I did NOT do

- I did not invent any `onchainos cohort ...` subcommand. COHORT is composed in Python from the commands above; it is not a CLI extension.
- I did not use `onchainos memepump token-dev-info` / `token-bundle-info` even though they appear in `smart-money-signals.md` step 2 — those run only when `protocolId` is non-empty. Demo fixtures include the fields so the report renders; live mode skips them rather than guess shape.
- I did not use `--mev-protection` or `--force` in any code path. If a future user wants them, they pass `confirm follow ...` and Claude appends them; the engine does not opt into them.

## Things to verify before running in live mode

The skill's `Pre-flight Checks` section enforces:

1. `onchainos` is on PATH. If not, fall back to demo mode with a banner.
2. `--chain` is in the result of `onchainos signal chains`. Don't guess.
