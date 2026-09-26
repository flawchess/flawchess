---
quick_id: 260926-evd
slug: consolidate-static-analysis-gates-for-agentic-engineering
phase: quick-260926-evd
plan: 01
subsystem: dev-tooling
tags: [ruff, eslint, ci, pre-merge-gate, complexity]
status: complete
dependency graph:
  requires: []
  provides:
    - "depth-only nesting gate (scripts/check_function_size.py, eslint max-depth)"
    - "ruff TID251/B/ASYNC/DTZ rule adoption with documented scoping and per-file baseline"
    - "pre-merge gate parity with CI (npm run build, npm run knip)"
  affects:
    - pyproject.toml
    - scripts/check_function_size.py
    - frontend/eslint.config.js
    - .github/workflows/ci.yml
    - CLAUDE.md
    - docs/dev-tooling.md
    - frontend/CLAUDE.md
tech-stack:
  added: []
  patterns:
    - "Nesting depth is the only hard complexity gate on both stacks; LOC and cognitive complexity are soft, report-only guidance."
    - "Ruff category adoption: one commit per category, config-fix what's trivially safe (extend-immutable-calls for B008), scope out non-app dirs by glob, baseline the rest per file under a dated comment."
key-files:
  created: []
  modified:
    - pyproject.toml
    - scripts/check_function_size.py
    - tests/scripts/test_check_function_size.py
    - frontend/eslint.config.js
    - .github/workflows/ci.yml
    - CLAUDE.md
    - docs/dev-tooling.md
    - frontend/CLAUDE.md
    - app/repositories/library_repository.py
    - app/services/tactic_detector.py
    - frontend/src/pages/Analysis.tsx
decisions:
  - "D-01: pre-merge gate now runs npm run build (tsc -b + vite) and npm run knip, closing the CI-only gap through which a type error or dead-export finding could reach main via local squash-merge."
  - "D-02: adopted ruff TID251 (ban requests/berserk), B (bugbear, FastAPI Depends/Query/etc defaults cleared via extend-immutable-calls), ASYNC, DTZ — one commit per category, non-app dirs scoped out by glob, remaining app/tests findings baselined per file under a dated comment."
  - "D-03: nesting depth <= 4 is now the only hard complexity gate on both stacks. Dropped: ruff's mccabe/pylint complexity-count tables and their Phase 214 baseline; the script's LOC gate, allow-loc pragma and FunctionRecord.allow_loc fields; eslint complexity/max-statements and the entire Phase 215 baseline region (kept only the one max-depth override for a test file)."
metrics:
  duration: "~45 min"
  completed: "2026-09-26"
actuals:
  tokens: 10343
  tasks: 3
  commits: 6
plan_head_before: ab0eaa1daed95cb27ce6bd785ffdd6a5f8721f3c
---

# Quick Task 260926-evd: Consolidate static-analysis gates for agentic engineering Summary

Nesting depth is now the only hard complexity gate on both stacks (backend `scripts/check_function_size.py`, frontend eslint `max-depth`); ruff gained TID251/B/ASYNC/DTZ with FastAPI's B008 false-positive cleared by config and everything else pre-existing baselined per file; and the local pre-merge gate now runs `npm run build` and `npm run knip` so it matches CI.

## What Was Built

**Task 1 — Depth-only complexity gate end-to-end.** TDD: replaced `test_cli_exits_one_when_loc_threshold_breached` with `test_cli_does_not_gate_logic_loc`, confirmed RED (the script's default `--fail-over-loc 200` still gated the 250-line flat function), then removed LOC gating entirely from `scripts/check_function_size.py` — deleted `_DEFAULT_MAX_LOGIC_LOC`, `_PRAGMA_PREFIX`, `_pragma_for_def`, `FunctionRecord.allow_loc`/`allow_loc_reason`, the `--fail-over-loc` CLI flag, and the LOC branch of `_breaches`. `raw_loc`/`logic_loc` are still computed and reported via `--json` for human/`/simplify` review. Removed ruff's `[tool.ruff.lint.mccabe]`/`[tool.ruff.lint.pylint]` tables and the Phase 214 `C901`/`PLR0912`/`PLR0915` baseline block from `pyproject.toml`. Removed `complexity`/`max-statements` from `frontend/eslint.config.js`'s base TS/TSX rules (kept `max-depth: 4`) and deleted the entire Phase 215 baseline region except the one `reminderSlotState.test.ts` `max-depth: 10` override. Updated the CI `Function-size gate` step and the CLAUDE.md pre-merge gate to invoke `--fail-over-depth 4` only, and added `npm run build`/`npm run knip` to the pre-merge gate's frontend line (D-01).

**Task 2 — Ruff TID251/B/ASYNC/DTZ, one commit per category.** Re-measured every category live against ruff 0.16.6 rather than trusting planning-time numbers (all matched):
- **TID251**: banned `requests` and `berserk` repo-wide (0 pre-existing findings — codebase already httpx-only). Added a comment explaining `datetime.now`/`utcnow` is deliberately NOT banned (legitimate tz-aware use; DTZ005 catches the naive form).
- **B (bugbear)**: `extend-immutable-calls` for `fastapi.Depends`/`Query`/`Path`/`Body`/`Header`/`Cookie`/`Security`/`Form`/`File` cleared all 60 pre-existing B008 findings. Scoped `scripts/**`/`analysis/**`/`alembic/**` out of B/ASYNC/DTZ entirely, and `tests/**` out of ASYNC/DTZ plus B905 only. Remaining 29 findings baselined per file: `app/routers/auth.py` B904, `app/routers/imports.py` B904, `app/services/endgame_service.py` B905, `app/services/maia_encoding.py` B905, `tests/repositories/test_opening_insights_repository.py` B007, `tests/services/test_push_crypto.py` B017, `tests/test_eval_worker_endpoints.py` B017, `tests/test_main_lifespan.py` B904, `tests/test_alembic_autogen_filter.py` B010 (never autofixed — verified the autofix produces a ty invalid-assignment error on the alembic.context proxy).
- **ASYNC**: 1 pre-existing finding baselined (`app/services/engine.py` ASYNC109).
- **DTZ**: 7 pre-existing findings baselined across 4 files (`insights_llm.py`/`insights_service.py`/`user_benchmark_percentiles_service.py` DTZ011 `date.today()`; `normalization.py` DTZ007 naive `strptime`).

No category needed a global rule ignore instead of per-file baselining — all four categories' app/tests findings were small enough to baseline individually.

**Task 3 — Condensed prose, cleaned stale references.** Rewrote CLAUDE.md's "Keep functions small and shallow"/"Refactor bloated code on sight" bullets to state depth as the only hard rule (198 words, budget 230) and LOC/cognitive complexity as soft, report-only guidance. Rewrote `docs/dev-tooling.md`'s "## Scripts" tooling bullets to match the new ruff/eslint reality (510 words, budget 560). Updated `frontend/CLAUDE.md` line 10 and added the `npm run build` type-check reminder. Removed the now-inert `# check-function-size: allow-loc` pragma and its explanatory comment from `app/repositories/library_repository.py`; reworded two "PLR0912 gate" comments in `app/services/tactic_detector.py` to describe readability rather than a specific ruff rule; dropped the stale "sits at its max-statements/complexity baseline" clause from `frontend/src/pages/Analysis.tsx`.

## Planning-Time Corrections (both verified true during execution)

1. `scripts/check_function_size.py` defaulted its LOC threshold to 200 even when `--fail-over-loc` wasn't passed on the CLI — dropping the flag from CI alone would NOT have dropped the LOC gate. Fixed by removing LOC gating from the script itself (Task 1), not just the CLI invocation.
2. `datetime.datetime.now`/`utcnow` is NOT banned via TID251 despite D-02's original framing — it has ~9 legitimate tz-aware call sites in app/ (middleware, import-job, eval-lease code). TID251 bans a name regardless of arguments, so banning it would have also banned the legitimate tz-aware form. DTZ005 (naive-only) is the correct, narrower rule; it was already 0 findings and required no baseline.

## Deviations from Plan

None — plan executed exactly as written. All finding counts were re-measured live (ruff 0.16.6) before baselining rather than trusting the plan's planning-time numbers, and every measured count matched the plan's expectations exactly (TID251: 0; B008 cleared by config: 60; B remainder: 29 across 9 files; ASYNC: 1; DTZ: 7 across 4 files).

## Verification

Full plan `<verification>` block passed:
- `uv run ruff format --check app/ tests/ scripts/ analysis/` — pass
- `uv run ruff check .` — pass (0 findings)
- `uv run ty check app/ tests/ scripts/` — pass
- `uv run --project analysis --with ty ty check analysis/` — pass
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4` — pass (1068 functions scanned, no breaches)
- `uv run pytest tests/scripts/test_check_function_size.py -q` — pass (18 passed)
- `( cd frontend && npm run lint && npm run build && npm run knip )` — pass

Per-task `<verify>` blocks (RED/GREEN TDD proof for Task 1, all rule-scoping probes for Task 2, word-budget + negative-reference sweep for Task 3) also passed — see task actions above for detail.

## Known Stubs

None.

## Threat Flags

None — this plan only changes which static-analysis checks run and how prose describes them; no new network endpoints, auth paths, file-access patterns, or schema changes were introduced.

## Self-Check: PASSED

- `pyproject.toml`, `scripts/check_function_size.py`, `tests/scripts/test_check_function_size.py`, `frontend/eslint.config.js`, `.github/workflows/ci.yml`, `CLAUDE.md`, `docs/dev-tooling.md`, `frontend/CLAUDE.md`, `app/repositories/library_repository.py`, `app/services/tactic_detector.py`, `frontend/src/pages/Analysis.tsx` — all FOUND and modified as described.
- Commits verified present in `git log --oneline`:
  - `66276848f` chore(quick-260926-evd): make nesting depth the only hard complexity gate — FOUND
  - `7a094e7d4` chore(quick-260926-evd): ban requests and berserk via ruff TID251 — FOUND
  - `614f5ca6c` chore(quick-260926-evd): adopt ruff flake8-bugbear (B) — FOUND
  - `4f1b59836` chore(quick-260926-evd): adopt ruff flake8-async (ASYNC) — FOUND
  - `b78f42dab` chore(quick-260926-evd): adopt ruff flake8-datetimez (DTZ) — FOUND
  - `a8a81362f` docs(quick-260926-evd): condense complexity guidance to a depth-only hard rule — FOUND
