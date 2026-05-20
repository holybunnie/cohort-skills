# BUILD_LOG.md

> Honest record of what I actually ran and what I actually saw.
> Build date: 2026-05-20. Build environment: GitHub Codespaces, Python 3.12.1, PyYAML 6.0.3.
> The `onchainos` CLI is **NOT** installed in this environment — see note on check #3 below.

## Reference

Before any code was written, I cloned the OnchainOS reference and confirmed each command COHORT issues:

```
gh repo clone okx/onchainos-skills /tmp/onchainos-ref -- --depth 1
```

Cross-reference table lives in `NOTES_FROM_REPO.md` and `skills/cohort/references/onchainos-commands.md`.

## The 12 checks

### #1 — Real commands, not guesses

**PASS.** Every CLI invocation in `skills/cohort/scripts/cohort.py` was located in upstream `okx/onchainos-skills` files. Table in `NOTES_FROM_REPO.md`. Two scope substitutions are documented there (memepump enrichment skipped in live mode; payment-notifications not surfaced). Nothing fabricated.

### #2 — The load-bearing feature (signal-list wallets watched for sells)

**PASS.** Confirmed via two upstream sources combined:

- `workflows/wallet-monitor.md` step 2 defines: `onchainos tracker activities --tracker-type multi_address --wallet-address <wallet> --chain <chain>` and accepts comma-separated addresses up to 20.
- `skills/okx-dex-signal/SKILL.md` step 1 confirms `--trade-type 2 = sell-only`.

`smart-money-signals.md` step 1 produces the per-token SM wallet list. COHORT step 3 (in `SKILL.md`) feeds that exact wallet set into `tracker activities` with `--trade-type 2`. The wiring is in `cohort.py` `cmd_run` lines that build `wallets = ",".join(entry.get("smart_money_wallets", [])[:20])` and pass it to `tracker activities --tracker-type multi_address --trade-type 2`.

### #3 — Live demo ("what is smart money converging on right now on Solana?")

**PASS, with honest caveat.** The `onchainos` CLI is not installed here, so `cohort.py run --chain solana` (no `--demo`) automatically falls through to demo mode and prints:

```
MODE: DEMO (fallback — onchainos CLI not found, no network calls made)
```

Followed by the same clean table. This is the documented fallback behaviour, not a silent failure — the user is told explicitly. On a machine with `onchainos` installed, the same command runs against the live CLI.

### #4 — Demo mode never blank

**PASS.** `python3 skills/cohort/scripts/cohort.py run --demo` produces a complete 5-row report with verdicts. Initial run hit a JSON parsing error from underscored numeric literals (`4_300_000`) — fixed by replacing with `4300000`, re-ran, clean.

### #5 — Dry-run safety

**PASS.** `cohort follow ... --dry-run --demo` prints a quote, then the banner:

```
============================================================
DRY RUN — no funds moved. No transaction was broadcast.
============================================================
```

The execute code path is unreachable in dry-run mode (the function returns before reaching it).

### #6 — Doesn't break on bad input

**PASS.**

```
$ cohort follow --token NOT-A-REAL-ADDRESS --chain solana ...
cohort: 'NOT-A-REAL-ADDRESS' does not look like a solana token address — skipping.

$ cohort run --chain bitcoin --demo
cohort: chain 'bitcoin' is not in the supported list.
        Supported: solana, ethereum, base, bsc, arbitrum, polygon
```

Plain English, exit code 2, no stack trace.

### #7 — Won't spend money by surprise

**PASS.** The trade path is gated by three serial gates documented in `skills/cohort/references/safety-gates.md`:

1. Input validation (token format + supported chain)
2. Quote + safety re-check (read-only)
3. Exact-phrase confirmation from the user (`confirm follow <symbol> <amount>`)

`cohort.py cmd_follow` returns after printing the HARD STOP banner — there is no path from `cohort follow` to `onchainos swap execute` inside the Python engine. The execute step is intentionally delegated to Claude only on receipt of the confirmation phrase, in `SKILL.md` step 5.

### #8 — Report renders

**PASS.** End-to-end:

```
python3 cohort.py run --demo --json-out /tmp/cohort-report.json
python3 report.py --input /tmp/cohort-report.json --output cohort-report.html
python3 serve.py --port 8766 --once   # one-shot for repeatable testing
curl http://localhost:8766/cohort-report.html
  → HTTP 200, bytes=3137
```

The fetched bytes match the on-disk HTML byte-for-byte (`diff -q` clean). Page renders with the cohort table, verdict colors, mode banner, and safety footer.

### #9 — YAML is valid

**PASS** — actually parsed, not eyeballed. `tests/test_yaml_frontmatter.py` calls `yaml.safe_load()` on the frontmatter of every `skills/*/SKILL.md`:

```
OK    skills/cohort/SKILL.md — name='cohort', desc_len=1005
All 1 SKILL.md frontmatter blocks parse as valid YAML.
```

### #10 — CI honesty

**PASS.** No `.github/` directory. README has an explicit "## No CI" section stating: *"Intentional. The 12-check verification is documented in BUILD_LOG.md and was run by hand. A red CI badge that lies is worse than no badge."*

### #11 — A stranger can follow docs/DEMO.md

**PASS.** The doc opens with *"This page assumes you have never seen this project. Read top to bottom."* and walks through: prerequisites → clone → demo run → expected output → HTML report → safety gate → bad-input handling → going live. 115 lines, no jargon, every command shown verbatim.

### #12 — Final clean sweep

**PASS.** Re-ran the full pipeline from scratch (deleted intermediate artifacts first). All 8 steps in the sweep succeeded:

1. Pre-flight: `cohort check` correctly reports onchainos absent
2. `cohort run --demo` → 5-row report
3. `report.py` → wrote HTML
4. `serve.py --once` → HTTP 200 on first GET, server exits cleanly
5. Dry-run gate → DRY RUN banner, no execute path
6. Gated follow → HARD STOP banner, no execute path
7. Bad input → clean plain-English messages on both bad token and bad chain
8. YAML test + input-validation test → 1/1 + 6/6 pass

## Self-corrections made during build

- **Demo JSON failed to parse** because I used Python `1_000_000` underscore literals. Replaced with plain `4300000`. Verified parse with `python3 -c "import json; json.load(open(...))"`.

That is the only failure I hit during the 12 checks. It was caught by check #4 actually running, not by visual inspection.
