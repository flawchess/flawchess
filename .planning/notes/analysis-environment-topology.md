---
title: Analysis environment topology — uv workspace + marimo + PyCharm
date: 2026-05-27
context: /gsd-explore session on setting up a data exploration/visualization environment
---

# Analysis environment topology

Captures the decided shape (and the reasoning) for adding a data-exploration
subproject to FlawChess. Not a plan — a reference for when SEED-028 fires.

## Goals

- A dedicated `analysis/` area for ad-hoc data exploration, calibration work
  (zone bands, percentile cohort design), and reproducible reports beyond what
  `reports/benchmarks-latest.md` and `reports/db-report-*.md` already give us.
- Notebooks under version control, reviewable in diffs.
- Works in PyCharm and Claude Code without friction.
- Mostly raw SQL against the three Postgres instances; occasional imports from
  `app/` when a notebook needs an existing service or model.

## Decided shape

```
flawchess/
  pyproject.toml          # add [tool.uv.workspace] members = ["analysis"]
                          # root stays the main `app` package — root-as-member
  app/                    # unchanged
  analysis/
    pyproject.toml        # marimo + dataframe lib + plotting lib
    db.py                 # get_conn("dev"|"benchmark"|"prod") from .env
    notebooks/            # checked-in .py marimo notebooks
```

### Why uv workspace (not a separate repo, not a sibling venv)

- One shared `.venv` at the root — no duplicate FastAPI / python-chess /
  SQLAlchemy installs for the ~10% of notebooks that import from `app/`.
- Lockfile coherence: when `app/` bumps a dep, `analysis/` sees the same version.
- Root-as-member is the right shape because `app/` already lives at the repo
  root with its own `pyproject.toml`. We don't want to move it into `app/app/`.

### Why a `db.py` helper (not raw asyncpg per-notebook, not SQLAlchemy reuse)

- Three Postgres instances (dev `:5432`, benchmark `:5433`, prod-via-tunnel
  `:15432`) — credentials and connection strings shouldn't sprawl across
  every notebook.
- Raw SQL is the path of least resistance for ad-hoc analysis. SQLAlchemy
  is overkill and drags a heavy dep into a notebook context.
- One source of truth for "which DB am I hitting" via `get_conn("dev"|...)`
  reading from `.env`.
- Note: respect [[project_benchmark_db_ro_password]] — benchmark RO password
  is local-only, not committed.

## Marimo specifics

- Notebooks are `.py` files (cells are decorated functions). Reviewable diffs,
  no JSON merge conflicts, no nbstripout dance.
- **No official PyCharm marimo plugin** as of 2026-05 (open feature request
  at marimo-team/marimo#6297). Workflow:
  1. Edit `analysis/notebooks/foo.py` in PyCharm normally
  2. Run `marimo edit --watch analysis/notebooks/foo.py` in a side terminal
  3. View / interact in browser; saves reflect back into the `.py` file
- VS Code/Cursor have a marimo extension; PyCharm does not. Don't pick the
  IDE around marimo — pick it around the FastAPI work (95% of the codebase).

## PyCharm Workspaces (the IDE feature, not the uv concept)

**Important:** "PyCharm Python Workspaces" and "uv workspaces" are different
concepts with confusingly similar names.

- **uv workspace** = monorepo packaging model (root `pyproject.toml`,
  `[tool.uv.workspace] members = [...]`, shared lockfile, shared venv).
- **PyCharm Workspace mode** = IDE project model that natively understands
  uv/Poetry/Hatch workspace topology. Shipped in PyCharm 2026.1.1 (May 2026),
  still tagged **Beta**.

When PyCharm opens a directory containing nested `pyproject.toml` files, it
detects `[tool.uv.workspace]` and offers to enable Workspace mode. Members
become first-class managed sub-projects with auto-resolved dependencies.

- One window, one interpreter (`.venv` at workspace root), per-member dep
  awareness. No "attach project" trick.
- Beta → expect some rough edges (dep graph refresh, env auto-detection).
  Fall back to single-root mode if it misbehaves — no lock-in.

Sources:
- https://www.jetbrains.com/help/pycharm/python-workspaces.html
- https://blog.jetbrains.com/pycharm/2026/05/support-for-uv-poetry-and-hatch-workspaces-beta/
- https://docs.astral.sh/uv/concepts/projects/workspaces/

## Deferred choices (not blocking, settle when setup happens)

- **DataFrame lib:** polars (faster, modern, native `pl.read_database` against
  asyncpg/psycopg connection strings) vs pandas (familiar, integrates with
  sklearn/seaborn if we ever go there). See research questions Q-006.
- **Plotting lib:** plotly (interactive HTML, marimo renders natively),
  altair (declarative, ships in marimo examples), matplotlib (universal,
  static). marimo's docs lean toward plotly/altair for the interactive story.

## Out of scope for this note

- Whether `analysis/` reports promote into `reports/`, or live entirely under
  `analysis/notebooks/`. Decide when the first report exists.
- Whether marimo notebooks ever get exported to HTML for sharing (marimo
  supports WASM export → standalone HTML). Defer until there's a need.
- CI for `analysis/` (lint, typecheck, notebook-runs-clean). Likely
  not worth it until the directory has >5 notebooks.
