---
phase: 81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table
plan: 05
subsystem: uat
tags: [endgames, twin-tile, manual-uat]
requires:
  - 81-04 (page wire-up)
provides:
  - User approval of the visual / interactive layer
  - Three follow-up amendments folded back into the phase
affects: []
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - app/services/endgame_service.py (D-22 entry-eval source switch)
    - tests/test_endgame_service.py (TestEntryEvalAggregation rewrite)
    - frontend/src/components/charts/EndgameStartVsEndSection.tsx (label rename + mobile stack)
    - frontend/src/pages/Endgames.tsx (accordion label rename, accordion paragraph rename)
    - frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx (assertion updates)
    - .planning/phases/81-.../81-CONTEXT.md (D-22 amendment)
decisions:
  - "Approved manual UAT against user 28 (chess.com + lichess, mixed time controls). Visual parity with Openings ExplorerTab confirmed; mobile stacking, three-state color verdict, popover content, and accordion copy all pass."
  - "D-22 amendment (commit 6a45b695): entry-eval aggregation now consumes bucket_rows (one row per game, eval at first chronological endgame position) instead of per-class entry_rows. Fixes the 'n=2907 vs WDL=2960' discrepancy surfaced during UAT — the per-class pipeline excluded games whose total endgame plies met the 6-ply threshold but no single class span did. Invariant entry_eval_n + mate_excluded == endgame_wdl.total now holds by construction."
  - "UI polish (commit f71a6c9c): inline label 'Avg eval at endgame entry:' shortened to 'Endgame entry eval:' (matching accordion paragraph rename); per-tile inner grid stacks chart below label-row on mobile, side-by-side at lg+ where each tile has horizontal room. Accordion paragraph for second tile shortened earlier from 'Absolute endgame score:' to 'Endgame score:' to match the inline label."
metrics:
  duration_minutes: 90
  completed: 2026-05-09
---

# Phase 81 Plan 05: Manual UAT Summary

Manual UAT against user 28 on the live dev environment. All 9 checks passed after three follow-up amendments were folded into the phase based on UAT findings.

## UAT Verdict — Approved

| # | Check | Verdict |
|---|-------|---------|
| 1 | Section placement (D-01) above WDL table | PASS |
| 2 | Two tiles side-by-side on desktop (D-04) | PASS |
| 3 | Mobile stacking + entry-eval first (D-04, D-17) | PASS — after follow-up making per-tile chart drop below label-row |
| 4 | Visual parity with Openings score bullet (D-16) | PASS |
| 5 | Three-state color verdict (D-09, D-10) | PASS |
| 6 | Popover content (D-03) | PASS |
| 7 | Concept-explainer accordion (D-13, D-14) | PASS — after copy shortening for label/explainer consistency |
| 8 | Hide-when-empty (D-06) | PASS |
| 9 | Sentry / console sanity | PASS — no new errors |

## Amendments folded back from UAT

### D-22 — Entry-eval source: bucket_rows, not entry_rows

User reported `entry_eval_n = 2907` against `endgame_wdl.total = 2960` and asked whether eval data was missing. SQL audit showed:

- 0 games with `eval_cp = NULL` on the chosen span (no actual missing eval).
- 48 games where the lowest-class span had `eval_mate` set (D-07 mate exclusion).
- **5 games** where total endgame plies ≥ 6 across the game but no single per-class span reached the 6-ply threshold (e.g. `1 ply rook + 5 plies mixed`). Counted in WDL (game-level `HAVING`), excluded from entry-rows (per-class `HAVING`).

The per-class entry-rows pipeline was solving a problem the entry-eval tile doesn't have: it was designed for stats categorization, where per-class spans matter. For a single "where you start" mean, the chronologically-first endgame position is the right anchor.

Fix: `_get_endgame_performance_from_rows` now consumes `query_endgame_bucket_rows` directly. Per-game dedup loop removed. Both callers (`get_endgame_performance` and `get_endgame_overview`) updated. After the change, for user 28: `entry_eval_n = 2918` (+11 over the old pipeline; +5 from sub-threshold games, +6 from chronological-first picking a cp-eval where lowest-class picked a mate-eval), `mate_excluded = 42`. Sum 2960 = WDL total.

Codified as `D-22 (LOCKED)` in `81-CONTEXT.md` under "UAT Amendment".

### UI polish — label shortening + mobile chart stacking

- "Avg eval at endgame entry:" → "Endgame entry eval:" in both the inline tile label and the matching accordion explainer paragraph.
- "Absolute endgame score:" → "Endgame score:" in the accordion paragraph (matches the inline label, applied earlier by user during UAT).
- Per-tile inner grid: was `grid-cols-[auto_minmax(0,1fr)]` at every viewport, squeezing the bullet chart on phones. Now `grid-cols-1 lg:grid-cols-[auto_minmax(0,1fr)]` — chart stacks below the label-row on mobile, side-by-side at lg+ where each tile has room.

## Verification

- Backend: ruff + ty clean; `tests/test_endgame_service.py + tests/test_endgames_router.py` 227/227 pass.
- Frontend: lint + tsc + knip clean; vitest 337/337 pass.
- Live dev environment: hot-reload picked up backend + frontend changes; user verified the new numbers and copy in browser.

## Commits introduced by Plan 05

- `6a45b695` — fix(81): switch entry-eval aggregation to bucket_rows (D-22 UAT amendment)
- `f71a6c9c` — fix(81): shorten entry-eval label and stack chart on mobile (UAT polish)
- (this) — docs(81-05): complete manual UAT plan summary
