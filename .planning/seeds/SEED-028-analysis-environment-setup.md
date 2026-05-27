---
id: SEED-028
status: open
planted: 2026-05-27
planted_during: v1.18 (Phase 94.4 peer-relative percentile chip)
scope: tooling / cross-milestone
---

# SEED-028: Set up `analysis/` data-exploration environment

## Why This Matters

A lot of FlawChess design work — zone band calibration, cohort design (the
percentile-chip work in Phase 94.x is the latest example), benchmark validation,
import-pipeline profiling — boils down to running SQL against one of three
Postgres instances, shaping a DataFrame, and looking at a chart. Today that
work lives in:

- The `benchmarks` skill (calibrated, scripted, but rigid)
- The `db-report` skill (operational health, not exploration)
- Ad-hoc one-off scripts that don't get checked in
- The `mcp__flawchess-*-db__query` MCP tools (great for one-line lookups,
  terrible for "I want to look at this distribution and tweak the bin width")

There's no first-class interactive notebook surface. When a design question
needs "show me 5 chart variations to compare", we either build a throwaway
script or end up doing it in Claude's head, which is worse.

## When to Surface

**Trigger:** Any of the following:
- Next time a Phase plan calls for "exploratory data analysis" or "calibrate
  thresholds against data" and the existing skills don't fit
- Before starting v1.19 (or whatever milestone follows Phase 94.x percentile
  work) — the percentile-chip cohort work has already surfaced 2-3 questions
  that would have benefited from this
- Anytime the user invokes `/gsd-quick analysis setup` or similar

## What To Build (when seed germinates)

See [[analysis-environment-topology]] for the full reasoning. Concretely:

1. **Add uv workspace to root `pyproject.toml`:**
   ```toml
   [tool.uv.workspace]
   members = ["analysis"]
   ```
   Root stays as the `app` package (root-as-member layout).

2. **Create `analysis/pyproject.toml`** with:
   - `marimo` (latest)
   - DataFrame lib (decide: polars vs pandas — recommend polars)
   - Plotting lib (decide: plotly vs altair — recommend plotly for marimo
     interactivity)
   - `python-dotenv` for `.env` loading
   - DB driver: `psycopg[binary]` (sync; cleaner than asyncpg for notebook
     ergonomics — marimo cells can be `async def` but `pl.read_database`
     wants a sync connection / connection string)

3. **Create `analysis/db.py`:**
   ```python
   def get_conn(env: Literal["dev", "benchmark", "prod"]) -> Connection: ...
   def get_conn_str(env: Literal["dev", "benchmark", "prod"]) -> str: ...
   ```
   - Reads from `.env` (existing file at repo root)
   - For `prod`, asserts that `bin/prod_db_tunnel.sh` is running (port 15432
     reachable) — fail loudly with the right `bin/...` command in the error
     message
   - Respect [[project_benchmark_db_ro_password]] — benchmark RO password is
     not committed; pull from local `.env` only

4. **Create `analysis/notebooks/`** with one starter notebook
   (`example_cohort_query.py`) demonstrating the pattern: `db.get_conn`,
   `pl.read_database`, one chart. Keeps the dir non-empty in git and serves
   as the convention reference.

5. **Run `uv sync`** to populate the shared `.venv` with analysis deps.

6. **In PyCharm:** open the project, accept the "Enable Workspace mode?"
   prompt that should appear (requires PyCharm 2026.1.1+).

7. **Document the marimo edit workflow** in `analysis/README.md`:
   ```bash
   uv run marimo edit analysis/notebooks/foo.py
   ```
   (or `--watch` if editing the `.py` in PyCharm in parallel).

## Deferred Until Seed Fires

- **DataFrame and plotting lib choice** — see open research question
  Q-006. Recommendation today: polars + plotly. Settle for real
  when the first notebook is being written.
- **CI integration** (lint analysis/, run notebooks headless) — not worth
  it until there are >5 notebooks.
- **Reports promotion path** — whether finished analyses get HTML-exported
  to `reports/` or stay as `.py` notebooks under `analysis/notebooks/`.

## Estimate

~30-60 min if no surprises. Most of the time will be in choosing the
dataframe/plotting libs and validating the marimo + PyCharm workspace mode
flow actually works end-to-end.

## Related

- [[analysis-environment-topology]] — decided topology + research findings
- Research Q-006 — polars vs pandas + plotting lib for marimo
