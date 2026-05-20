# COHORT Safety Gates

This file documents every place COHORT can spend money, and what stops it.

## Where money can move

There is exactly one path: a user, after seeing the COHORT report, decides to follow a cohort token and the agent runs `onchainos swap execute`.

That call is gated by three serial checks. All three must pass in the **same agent turn**. None of them can be inferred from prior context.

```
              cohort follow <symbol> <amount>
                          │
                          ▼
     ┌─────────────────────────────────────────────┐
     │ Gate 1: input validation                    │
     │   - token address matches chain format      │
     │   - chain in supported list                 │
     │   - amount > 0 and not absurd               │
     └─────────────────────────────────────────────┘
                          │ pass
                          ▼
     ┌─────────────────────────────────────────────┐
     │ Gate 2: quote + safety re-check             │
     │   - onchainos swap quote (read-only)        │
     │   - re-check honeypot flag from quote       │
     │   - re-check buy/sell tax from quote        │
     │   - print quote + sells observed so far     │
     └─────────────────────────────────────────────┘
                          │ printed
                          ▼
     ┌─────────────────────────────────────────────┐
     │ Gate 3: explicit user confirmation phrase   │
     │   user must type exactly:                   │
     │     confirm follow <symbol> <amount>        │
     │   any other reply cancels                   │
     └─────────────────────────────────────────────┘
                          │ matched
                          ▼
              onchainos swap execute
```

## What the agent is forbidden from doing

- Treating an enthusiastic "yes" or "do it" as confirmation — only the exact phrase counts.
- Calling `--force` to bypass risk warning 81362 (per `okx-dex-swap/SKILL.md`, that's "after explicit user confirmation" — and COHORT never asks the agent to do this).
- Inferring confirmation from earlier-turn statements like "I'll follow whatever you find."
- Caching a confirmation across symbols. Each follow is a fresh gate.

## Dry-run

`cohort follow ... --dry-run` runs gates 1 and 2 and then prints a `DRY RUN — no funds moved` banner instead of asking for confirmation. The execute path is unreachable.

## Demo

`cohort follow ... --demo` synthesizes the quote from fixtures and follows the same gate ordering. Execute is still unreachable.
