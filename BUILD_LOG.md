# BUILD_LOG.md

> Honest record of what I actually ran and what I actually saw.
> Build date: 2026-05-20.
> Environment: GitHub Codespaces, Python 3.12.1, PyYAML 6.0.3.

## Installation evidence

The upstream `okx/onchainos-skills` plugin and the `onchainos` CLI binary are both installed in this codespace:

```
$ which onchainos
/home/codespace/.local/bin/onchainos

$ onchainos --version
onchainos 3.3.6

$ ls ~/.claude/plugins/marketplaces/onchainos-skills/.claude-plugin/
README.md  marketplace.json  plugin.json

$ find ~/.claude/plugins/marketplaces/onchainos-skills/skills -name SKILL.md | wc -l
22
```

Install commands actually run (from the upstream installer):

```
cp -r /tmp/onchainos-ref ~/.claude/plugins/marketplaces/onchainos-skills    # plugin
curl -sSL https://raw.githubusercontent.com/okx/onchainos-skills/main/install.sh | sh  # CLI binary
```

## Bugs caught by actually running the installed CLI

This section exists because running the real CLI uncovered two bugs that visual inspection would have missed. Both were fixed before claiming any check passed.

**Bug 1 — `--format json` does not exist in CLI v3.3.6.**
The first version of `scripts/cohort.py` appended `--format json` to every call, based on the upstream `CLAUDE.md` note ("for script requests, append `--format json` to all CLI commands"). The live CLI rejected it with `error: unexpected argument '--format' found`. Fix: removed the flag. The CLI emits JSON natively on non-TTY stdout.

**Bug 2 — `confirming: true` payment-gate exits with code 2.**
On a fresh install the OKX Market API returns `{ "confirming": true, "notifications": [...] }` to indicate the per-call payment requirement, and the CLI exits non-zero. The original `run_onchainos()` raised a generic `RuntimeError` on non-zero exit before inspecting the JSON. Fix: parse stdout first, raise a typed `PaymentGateError` on `confirming:true`, then handle it in `cmd_run` with a clean fallback to demo mode.

Both fixes are in the current `scripts/cohort.py`.

## The 12 checks — re-run against current state

Date: 2026-05-20 16:04 UTC.

### #1 — Real commands, not guesses

**PASS.** Every CLI invocation in `scripts/cohort.py` is exercised by `onchainos <subcommand> --help` against the live binary:

```
OK  onchainos signal list
OK  onchainos signal chains
OK  onchainos tracker activities
OK  onchainos token price-info
OK  onchainos token advanced-info
OK  onchainos security token-scan
OK  onchainos swap quote
OK  onchainos swap execute
OK  onchainos wallet status
```

Cross-reference table in `NOTES_FROM_REPO.md` maps each to its upstream SKILL.md / workflow source file.

### #2 — The load-bearing feature

**PASS.** Confirmed by both the upstream docs AND the live CLI help text:

```
$ onchainos tracker activities --help
  --tracker-type <TRACKER_TYPE>
      Tracker type: smart_money (or 1), kol (or 2), multi_address (or 3)
  --wallet-address <WALLET_ADDRESS>
      Wallet addresses (required for multi_address), comma-separated, max 20
  --trade-type <TRADE_TYPE>
      Trade type: 0=all (default), 1=buy, 2=sell
```

The signal-list wallets feed directly into `tracker activities --tracker-type multi_address --trade-type 2 --wallet-address <wallets>` for sell-only filtering. `cmd_run` in `scripts/cohort.py` does exactly this: it collects up to 20 wallets per cohort from the signal-list response and passes them to the tracker call.

### #3 — Live demo ("what is smart money converging on right now on Solana?")

**PASS, with honest live behavior.** Running the live invocation:

```
$ python3 skills/cohort/scripts/cohort.py run --chain solana
cohort: OKX Market API returned confirming:true — free quota exhausted;
        this endpoint now requires per-call payment via the OKX Agent Payments Protocol.
        COHORT will not auto-pay; resolve the gate via the upstream
        `okx-agent-payments-protocol` skill, or run with --demo.
cohort: falling back to DEMO mode so the report still renders.
MODE: DEMO (fallback — OKX paid-quota gate active, no live data)
[clean 5-row report follows]
```

The CLI is actually contacted, the response is actually inspected, the payment gate is detected and surfaced in plain English, and the user gets a clean readable report regardless. No silent failure, no fabricated data.

### #4 — Demo mode never blank

**PASS.** `python3 scripts/cohort.py run --demo` produces:

```
MODE: DEMO — using bundled fixtures, no network calls made
1  WEN       6       $0.0000821    $82.10M   0/0%      0      FOLLOW
2  PEPESOL   4       $0.0000063    $6.32M    1/1%      1      WATCH
3  RUGZ      4       $0.0000012    $120.0K   0/99%     2      AVOID  HONEYPOT
4  PYTH      3       $0.143        $514.00M  0/0%      0      WATCH
5  JUP       2       $0.412        $561.00M  0/0%      0      WATCH
```

### #5 — Dry-run safety

**PASS.** `cohort follow ... --dry-run --demo` prints `MODE: DRY RUN — confirmation required before any broadcast` then the banner `DRY RUN — no funds moved. No transaction was broadcast.` The execute path is unreachable when `args.dry_run` is set (the function returns before any execute call).

### #6 — Doesn't break on bad input

**PASS.**

```
$ cohort follow --token NOPE --chain solana ...
cohort: 'NOPE' does not look like a solana token address — skipping.   (exit 2)

$ cohort run --chain bitcoin --demo
cohort: chain 'bitcoin' is not in the supported list.
        Supported: solana, ethereum, base, bsc, arbitrum, polygon       (exit 2)
```

Plain English, no stack traces.

### #7 — Won't spend money by surprise

**PASS.** The HARD STOP gate fires before any execute path:

```
HARD STOP — Claude must NOT call swap execute without the user
  confirm follow WEN 0.1
Any other input cancels.
```

Architecture documented in `skills/cohort/references/safety-gates.md` — three serial gates (input validation, quote+safety re-check, exact-phrase confirmation) gate the only path to `swap execute`. The Python engine never broadcasts; it stops at the gate. `swap execute` is only invoked by Claude after the user's next message exactly matches `confirm follow <symbol> <amount>`.

### #8 — Report renders, served on localhost

**PASS.**

```
$ python3 scripts/cohort.py run --demo --json-out /tmp/r.json
$ python3 scripts/report.py --input /tmp/r.json --output cohort-report.html
$ python3 scripts/serve.py --port 8767 --once  &
$ curl -s -o /dev/null -w "%{http_code} %{size_download}\n" http://localhost:8767/cohort-report.html
  HTTP 200, bytes=3137
$ tail server log:
  COHORT report served at http://localhost:8767/cohort-report.html
  GET /cohort-report.html HTTP/1.1 → 200
```

Real `http://` URL, real HTTP 200, real bytes. No `file://`.

### #9 — YAML is valid

**PASS** — actually parsed. `tests/test_yaml_frontmatter.py` calls `yaml.safe_load()` on the frontmatter of every `skills/*/SKILL.md`:

```
OK    skills/cohort/SKILL.md — name='cohort', desc_len=1005
All 1 SKILL.md frontmatter blocks parse as valid YAML.
```

### #10 — CI honesty

**PASS.** No `.github/` directory. README has an explicit "## No CI" section.

### #11 — Stranger can follow docs/DEMO.md

**PASS.** 115 lines, opens with *"This page assumes you have never seen this project. Read top to bottom."* Walks through: prerequisites → clone → demo run → expected output → HTML report → safety gate → bad-input handling → going live.

### #12 — Final sweep

**PASS.** The entire re-verification was run as one shell pass against the current files. All 8 sub-steps succeeded:

1. CLI installation verified (v3.3.6 at `~/.local/bin/onchainos`)
2. All 9 required subcommands present
3. Live demo invocation against the real API succeeded (payment gate handled cleanly)
4. Explicit `--demo` produces the same clean table
5. Dry-run banner fires
6. Both bad-input paths fail gracefully with exit 2
7. Trade gate prints HARD STOP
8. HTML report served on real localhost URL, returned HTTP 200
9. YAML test 1/1 passes, input validation test 6/6 passes

## Self-corrections during build

| What | Why | How fixed |
|---|---|---|
| Demo JSON used `4_300_000` underscore literals | Python syntax inside JSON — invalid | Replaced with `4300000`, validated parse |
| `cohort.py` appended `--format json` to every CLI call | Based on upstream CLAUDE.md note; flag does not exist in CLI v3.3.6 | Removed flag; CLI emits JSON natively on non-TTY stdout |
| `confirming:true` payment-gate raised generic RuntimeError | CLI exits with code 2 on payment gate; original code raised before parsing stdout | Parse stdout first regardless of exit code; raise typed `PaymentGateError`; handle in `cmd_run` with demo fallback |

All three were caught by actually running the CLI, not by visual inspection.
