# SEED-050: Distinct "no moves to analyze" library state

**Captured:** 2026-06-15 (deferred from quick task 260615-wjz)
**Status:** seed (not planned)

## Idea

Permanently-unanalyzable games (zero-move games — resigned / abandoned /
agreed-drawn before move 1 — and games too short to ever reach the 90% eval
coverage gate) currently fall into the library's generic `no_engine_analysis`
state. That reads as "we failed to analyze this game" when the truth is "this
game has no moves (or too few) to analyze."

Surface a distinct, honest state for these — e.g. a muted "No moves to analyze"
badge instead of the "Analyze" affordance / "no engine analysis" copy — so users
aren't misled into thinking analysis is pending or broken.

## Why deferred

Quick task 260615-wjz fixed the **progress badge denominator** (these games no
longer block "X of X analyzed"). The library-card UI state is a separate,
larger frontend change (new `analysis_state` variant, copy, desktop + mobile
card rendering, `data-testid`s) and was explicitly scoped out.

## Detection predicate (already derived)

A game is permanently unanalyzable when it has finished the full-eval drain yet
never reached `is_analyzed`:

```
full_evals_completed_at IS NOT NULL AND NOT is_analyzed   -- (white_blunders IS NULL)
```

Same predicate the badge fix used (inverse of `count_analyzable_games`). The
backend `analysis_state` in `library_service.py` would need a third value
(currently `"analyzed"` / `"no_engine_analysis"`).

## Scope estimate

Small-to-medium frontend + thin backend: add `analysis_state="no_moves"` (or
similar) in `library_service._build_card`, thread it through the library API
schema and `frontend/src/types/library.ts`, and render the muted state on both
desktop and mobile game cards. No DB migration.
