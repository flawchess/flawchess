---
quick_id: 260615-wjz
slug: fix-eval-coverage-badge-denominator
title: Fix eval-coverage progress badge so "X of X games analyzed" is reachable
status: complete
date: 2026-06-15
commit: 74cc0636
---

# Summary — 260615-wjz

## What changed

`GET /api/imports/eval-coverage` now computes its `total_count` (and the
`pct_complete` denominator) from **analyzable** games only, instead of every
imported game. The "N of M games analyzed" badge can therefore finish at M of M.

- **`app/repositories/game_repository.py`** — new `count_analyzable_games(session, user_id)`:
  `WHERE is_analyzed OR full_evals_completed_at IS NULL`. `count_games_for_user`
  (raw imported total, used elsewhere) was left untouched.
- **`app/routers/imports.py`** — `get_eval_coverage` uses `count_analyzable_games`
  as `total`; `pct` numerator clamped at `>= 0` as defensive insurance against the
  rare full-drain-before-entry-drain ordering edge.
- **`tests/routers/test_imports_eval_coverage.py`** — `_make_unanalyzable_game`
  helper + 2 tests: unanalyzable games excluded from `total_count` while in-flight
  games stay counted; `analyzed_count == total_count` (X of X) once the drain is done.
- **`CHANGELOG.md`** — `### Fixed` bullet under `[Unreleased]`.

## Why this predicate

A game with `full_evals_completed_at IS NOT NULL AND NOT is_analyzed` has already
been through the full-eval drain's classify step and produced no flaw counts —
it's degenerate-length (zero moves, or too short to reach `EVAL_COVERAGE_MIN`),
so `classify_game_flaws` returns `GameNotAnalyzed` and `white_blunders` stays
NULL forever. Mid-drain games keep `full_evals_completed_at` NULL, so they remain
counted and the badge still climbs during import. `pending ⊆ analyzable`, so
`pct_complete == 100` still fires at the exact moment the last entry-ply eval
completes — the readiness gate is unchanged.

## Verification

- `ruff format` (1 file reformatted), `ruff check` clean, `ty check` clean.
- Full backend suite: **2673 passed, 10 skipped** (`uv run pytest -n auto -x`).
- New tests + `tests/test_game_repository.py`: 25 passed.
- Frontend deliberately untouched (response keys unchanged); frontend gate not run.

## Prod context (diagnosis that triggered this)

Verified via the prod read-only DB: user 28 had exactly 9 such games (all
zero-move: movetext is just the result token after resign/abandon/draw-agree),
user 3 had 6 (3 zero-move + 3 ultra-short, e.g. coverage 6/7 = 0.857).

## Deferred (out of scope)

Distinct library UI state ("no moves to analyze" vs generic "no engine
analysis") captured as **SEED-050**. Frontend `MAX_STALL_POLLS` backstop left
in place as insurance against a genuine engine outage.
