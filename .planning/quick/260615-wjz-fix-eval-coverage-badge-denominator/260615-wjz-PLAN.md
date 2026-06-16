---
quick_id: 260615-wjz
slug: fix-eval-coverage-badge-denominator
title: Fix eval-coverage progress badge so "X of X games analyzed" is reachable
status: in-progress
date: 2026-06-15
---

# Quick Task 260615-wjz: Fix eval-coverage badge denominator

## Problem

`GET /api/imports/eval-coverage` returns:
- `total_count` = `count_games_for_user` (ALL games)
- `analyzed_count` = `count_is_analyzed_games` (`Game.is_analyzed` = `white_blunders IS NOT NULL`)

Degenerate-length games can never become `is_analyzed`:
- **Zero-move games** — resigned / abandoned / agreed-drawn before move 1 → 0 `game_positions` rows.
- **Ultra-short games** — 4-5 moves; eval coverage is structurally `< EVAL_COVERAGE_MIN` (0.90) because the unevaluable terminal plies dominate the tiny `(COUNT - 1)` denominator.

`classify_game_flaws` returns `GameNotAnalyzed` for these, so `white_blunders` stays NULL forever and `analyzed_count < total_count` permanently — the badge never reaches "X of X". The `useEvalCoverage` `MAX_STALL_POLLS` backstop was added precisely to tolerate this.

Verified in prod: user 28 has exactly 9 such games (all zero-move); user 3 has 6 (3 zero-move + 3 ultra-short).

## Fix (backend only)

Exclude permanently-unanalyzable games from the badge denominator.

**Predicate:** `Game.is_analyzed OR Game.full_evals_completed_at IS NULL`

A game with `full_evals_completed_at IS NOT NULL AND NOT is_analyzed` has already been through the full-eval drain's classify step and produced no oracle counts → permanently stuck. Games still mid-drain keep `full_evals_completed_at IS NULL`, so they remain counted as not-yet-analyzed and the bar still climbs during import.

Gate-safety: `pending` (evals_completed_at IS NULL) ⊆ analyzable, so `pending <= total` and `pct_complete == 100` still fires at the exact same moment the last entry-ply eval completes (readiness gate unchanged).

## Tasks

1. **`app/repositories/game_repository.py`** — add `count_analyzable_games(session, user_id)` using the predicate above. Do NOT touch `count_games_for_user` (used elsewhere as the raw imported-game total).
2. **`app/routers/imports.py`** — `get_eval_coverage`: use `count_analyzable_games` as `total` (drives both `total_count` and the `pct_complete` denominator). Clamp `pct` numerator at `>= 0` as defensive insurance.
3. **`tests/routers/test_imports_eval_coverage.py`** — add a test: permanently-unanalyzable game (full_evals SET, white_blunders NULL) excluded from `total_count`; in-flight game (all NULL) still counted; analyzed game counted; "X of X" reachable when only analyzable + unanalyzable games remain.
4. **`CHANGELOG.md`** — `### Fixed` bullet under `[Unreleased]`.

## Out of scope (captured as seed)

Distinct library UI state ("no moves to analyze" vs generic "no engine analysis"). Frontend `MAX_STALL_POLLS` backstop stays as-is (insurance against a real engine outage).

## Verify

- `uv run ruff format app/ tests/ && uv run ruff check app/ tests/ --fix`
- `uv run ty check app/ tests/`
- `uv run pytest -n auto tests/routers/test_imports_eval_coverage.py tests/test_game_repository.py`
