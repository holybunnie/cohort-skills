# cohort-skills

COHORT finds what smart money is **converging on** right now, then watches those same wallets for **exits** — composed from real [OKX OnchainOS](https://github.com/okx/onchainos-skills) commands.

It ships in three forms so it works with whatever you already use:

- **A plain Python CLI** — no AI assistant required, just `python3 scripts/cohort.py …`.
- **An MCP server** — install once, works in Claude Code, Claude Desktop, Cursor, OpenAI Codex CLI, Windsurf, or any other MCP-compatible client.
- **A Claude Code skill** (`SKILL.md`) — for users on Claude Code who want the richer trigger phrasing, workflow doc, and Mermaid diagram surfaced as a first-class skill.

<p align="center">
  <img src="docs/demo.svg" alt="COHORT demo run" width="760"/>
</p>

> **Not a trading bot.** COHORT is an analysis + alerting workflow. The only trade path is gated by a hard-stop confirmation phrase. See `skills/cohort/references/safety-gates.md`.

> **To record a real terminal GIF later:** install [vhs](https://github.com/charmbracelet/vhs) and run `vhs docs/demo.tape` (a tape file isn't included yet — `docs/demo.svg` is the current animated placeholder, served inline by GitHub on the README).

## What COHORT does

1. **Discover** — pulls smart-money buy signals (`onchainos signal list`) and aggregates by token, ranking by how many distinct SM wallets are converging.
2. **Assess** — for each top cohort token, fetches price, market cap, liquidity, honeypot, tax, mint/freeze authority status.
3. **Watch the same wallets for sells** — uses `onchainos tracker activities --tracker-type multi_address --trade-type 2` to detect when cohort members start exiting. This closes the loop that buy-only signal feeds normally leave open.
4. **Verdict** — `FOLLOW`, `WATCH`, or `AVOID` based on convergence size, safety flags, and exit activity.
5. **Optional gated follow** — if the user explicitly asks, COHORT quotes + simulates, then **stops and requires the user to type an exact confirmation phrase** before any swap is broadcast.

## Quick start

```bash
# 1. Demo mode (no CLI, no network — always works)
python3 skills/cohort/scripts/cohort.py run --demo

# 2. Generate and serve the HTML report
python3 skills/cohort/scripts/cohort.py run --demo --json-out report.json
python3 skills/cohort/scripts/report.py --input report.json --output cohort-report.html
python3 skills/cohort/scripts/serve.py
# → http://localhost:8765/cohort-report.html

# 3. Real-time sell-watch (live okx-dex-ws, falls back to demo replay)
python3 skills/cohort/scripts/cohort.py watch --demo --once

# 4. Historical replay — verdict on past cohorts
python3 skills/cohort/scripts/cohort.py backtest --demo

# 5. Leaderboard-weighted verdict (3 top-tier wallets > 6 random ones)
python3 skills/cohort/scripts/cohort.py run --demo --weighted

# 6. Dry-run against the real CLI (requires onchainos installed)
python3 skills/cohort/scripts/cohort.py run --dry-run

# 7. Gated follow (always prints HARD STOP; never broadcasts here)
python3 skills/cohort/scripts/cohort.py follow \
  --symbol WEN --token EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYLWbWQX1xx \
  --amount 0.1 --chain solana --demo

# 8. MCP server (works with any MCP-compatible client)
python3 skills/cohort/scripts/mcp_server.py
# → exposes cohort_run / cohort_watch / cohort_backtest / cohort_follow_dry_run
# See "Installing into your AI assistant" below for per-client config.
```

## Installing into your AI assistant

The cohort engine itself is Python — it has no dependency on any specific assistant. The supported integration paths are:

| Client | Path | Config file |
|---|---|---|
| **Claude Code** | MCP server **or** native skill (`SKILL.md`) | `.mcp.json` (project) or `~/.claude.json` |
| **Claude Desktop** | MCP server | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) / `%APPDATA%\Claude\claude_desktop_config.json` (Windows) |
| **Cursor** | MCP server | `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global) |
| **OpenAI Codex CLI** | MCP server | `~/.codex/config.toml` |
| **Windsurf** | MCP server | `~/.codeium/windsurf/mcp_config.json` |
| **Any other MCP client** | MCP server | client's `mcpServers` config |
| **No assistant** | Run the Python CLI directly | — |

### Shared prerequisite — install the OnchainOS CLI

Every path below shells out to the `onchainos` binary for live data (demo mode works without it). Install it once:

```bash
curl -sSL https://raw.githubusercontent.com/okx/onchainos-skills/main/install.sh | sh
onchainos --version       # → onchainos 3.3.6 or newer
```

### Option A — MCP server (Claude Code, Claude Desktop, Cursor, Codex, Windsurf, …)

Most clients use the same JSON shape. Copy `.mcp.json.example` into the right path for your client, replacing the relative `args` path with an absolute one if your client isn't launched from this repo.

**JSON-based clients** (Claude Code, Claude Desktop, Cursor, Windsurf, …):

```json
{
  "mcpServers": {
    "cohort": {
      "command": "python3",
      "args": ["/absolute/path/to/cohort-skills/skills/cohort/scripts/mcp_server.py"]
    }
  }
}
```

**OpenAI Codex CLI** uses TOML instead of JSON — put this in `~/.codex/config.toml`:

```toml
[mcp_servers.cohort]
command = "python3"
args = ["/absolute/path/to/cohort-skills/skills/cohort/scripts/mcp_server.py"]
```

After installing, the client will expose four tools: `cohort_run`, `cohort_watch`, `cohort_backtest`, `cohort_follow_dry_run`. None of them broadcasts a transaction — execution still requires the exact in-chat confirmation phrase routed through your assistant's normal tool path, not through MCP.

### Option B — Claude Code native skill

If you're on Claude Code specifically, you can install COHORT as a skill so it triggers on natural-language phrases (e.g. *"what is smart money converging on?"*) rather than requiring an explicit tool call. This path also pulls in the upstream OKX skills so cross-references in `SKILL.md` resolve.

```bash
# 1. Install the upstream skills plugin (Claude Code only)
mkdir -p ~/.claude/plugins/marketplaces
git clone https://github.com/okx/onchainos-skills.git \
  ~/.claude/plugins/marketplaces/onchainos-skills

# 2. Drop skills/cohort/ into your Claude Code skills directory
```

Verify the upstream plugin is visible:

```bash
ls ~/.claude/plugins/marketplaces/onchainos-skills/skills | head
```

### Option C — Just the Python CLI

If you don't use an AI assistant (or want to script COHORT from cron / a notebook / CI), the Python CLI in `skills/cohort/scripts/cohort.py` works on its own. See **Quick start** above.

### About the OKX paid quota

The OKX Market API has a free quota per installation. Past that quota the CLI returns `{ "confirming": true, ... }` and exits non-zero. COHORT detects this and falls back to demo mode with a clear in-band message — it does not auto-pay. To get live data through COHORT, resolve the payment gate through the upstream `okx-agent-payments-protocol` skill first.

## What's in this repo

| Path | Purpose |
|---|---|
| `skills/cohort/SKILL.md` | The skill definition (YAML frontmatter + workflow + Mermaid diagram) |
| `skills/cohort/scripts/cohort.py` | The composition engine (`run` / `follow` / `check` / lazy-wired `watch` + `backtest`) |
| `skills/cohort/scripts/watch.py` | Real-time cohort sell-watch via `onchainos ws` |
| `skills/cohort/scripts/backtest.py` | Historical replay via `onchainos market kline` |
| `skills/cohort/scripts/weighting.py` | Leaderboard-weighted confidence |
| `skills/cohort/scripts/mcp_server.py` | MCP server exposing cohort tools over stdio JSON-RPC 2.0 |
| `skills/cohort/scripts/report.py` | HTML report renderer |
| `skills/cohort/scripts/serve.py` | localhost HTTP server for the report |
| `skills/cohort/scripts/demo_*.json` | Bundled fixtures (signals, watch events, backtest scenarios, leaderboard) |
| `skills/cohort/references/onchainos-commands.md` | Cross-reference of every CLI command used to its upstream OnchainOS source |
| `skills/cohort/references/safety-gates.md` | The three serial gates protecting the swap-execute path |
| `.mcp.json.example` | Drop-in config to install COHORT as an MCP server |
| `docs/DEMO.md` | Step-by-step walkthrough a stranger can follow |
| `docs/demo.svg` | Animated SVG embedded in this README |
| `NOTES_FROM_REPO.md` | Honest accounting of what's verified vs substituted |
| `BUILD_LOG.md` | Exact commands run during build + what was observed |
| `tests/` | YAML, input validation, watch demo, backtest, weighting, and MCP server end-to-end |

## No CI

Intentional. The 12-check verification is documented in `BUILD_LOG.md` and was run by hand. A red CI badge that lies is worse than no badge.

## License

MIT.
