# DEMO — walking through COHORT for the first time

This page assumes you have never seen this project. Read top to bottom.

## What you need

- A computer with **Python 3.9 or newer**. To check: open a terminal and type `python3 --version`. If you see something like `Python 3.11.x`, you're fine.
- No API keys.
- No installation of OKX OnchainOS — demo mode does not need it.

That's everything.

## Step 1 — get the code

```bash
git clone https://github.com/holybunnie/cohort-skills.git
cd cohort-skills
```

## Step 2 — run demo mode

Type this:

```bash
python3 skills/cohort/scripts/cohort.py run --demo
```

You should see, as the very first line:

```
MODE: DEMO — using bundled fixtures, no network calls made
```

Followed by a table that looks roughly like this (numbers will match `scripts/demo_data.json`):

```
#  SYMBOL    WALLETS PRICE         MCAP      TAX b/s   SELLS  VERDICT
---------------------------------------------------------------------
1  WEN       6       $0.0000821    $82.10M   0/0%      0      FOLLOW
2  RUGZ      4       $0.0000012   $120.0K   0/99%     2      AVOID    HONEYPOT
3  PEPESOL   4       $0.0000063   $6.32M    1/1%      1      WATCH
4  PYTH      3       $0.14         $514.00M  0/0%      0      WATCH
5  JUP       2       $0.41         $561.00M  0/0%      0      WATCH
```

What you're looking at:

- **WALLETS** is how many distinct smart-money wallets all bought this token. More = stronger convergence.
- **SELLS** is how many of those same wallets have started exiting (read via the cohort sell-watch).
- **VERDICT** is the recommendation: `FOLLOW` means strong convergence and clean safety, `WATCH` means mixed signals, `AVOID` means honeypot/high tax/cohort already exiting.

If the table is broken or you got an error, stop here and report what you saw.

## Step 3 — see the HTML report

```bash
python3 skills/cohort/scripts/cohort.py run --demo --json-out /tmp/report.json
python3 skills/cohort/scripts/report.py --input /tmp/report.json --output cohort-report.html
python3 skills/cohort/scripts/serve.py
```

The server will print:

```
COHORT report served at http://localhost:8765/cohort-report.html
```

Open that URL in a browser. You should see the same data as a styled table with color-coded verdicts. Press Ctrl+C in the terminal when you're done.

## Step 4 — try the safety gate

```bash
python3 skills/cohort/scripts/cohort.py follow \
  --symbol WEN \
  --token EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYLWbWQX1xx \
  --amount 0.1 \
  --chain solana \
  --demo
```

You should see a quote, then a clearly framed message:

```
============================================================
HARD STOP — Claude must NOT call swap execute without the user
typing the following exact phrase in their next message:
  confirm follow WEN 0.1
Any other input cancels.
============================================================
```

That's the gate. The program ends here. There is no `--yes` flag and no environment variable that bypasses it. The only way past this point is the exact phrase, in the next user message, in a real Claude session — at which point the agent runs `onchainos swap execute`.

## Step 5 — try breaking it

These should all fail gracefully (clear messages, no stack traces):

```bash
# Made-up token address
python3 skills/cohort/scripts/cohort.py follow \
  --symbol FAKE --token NOT-A-REAL-ADDRESS \
  --amount 0.1 --chain solana --demo

# Unsupported chain
python3 skills/cohort/scripts/cohort.py run --chain bitcoin --demo
```

## Going live

Demo mode is what you just used. To use real data:

1. Install OnchainOS: <https://github.com/okx/onchainos-skills>
2. Run the same commands without `--demo`. Add `--dry-run` if you want real data but no risk of trading.

That's it. The same workflow — discovery, assessment, sell-watch — runs against the real CLI.
