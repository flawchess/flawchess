---
phase: 249-blunder-check-playable-mvp
plan: 03
subsystem: blunder-check
tags: [blunder-check, session-composition, fastapi, selection, beta-gate]
status: complete

requires:
  - phase: 249-01
    provides: judge_game, assign_windows, draw_window_shape, selection constants
  - phase: 249-02
    provides: insert_session, pick/load/served repository reads, BetaUser router, seed helper
provides:
  - app/services/blunder_check_selection.py (compose_windows, snapshot builder, pinned-Elo reference, selection constants)
  - app/services/blunder_check_service.py (compose_or_resume)
  - POST /api/blunder-check/sessions (beta-gated start-or-resume)
affects: [249-04, 249-05, phase-251]

tech-stack:
  added: []
  patterns:
    - "Shape-first composition: draw all slots, fill own pool first, foreign pool only for still-empty slots, then redraw only empty slots against already-loaded pools"
    - "Bounded query budget per start (MAX_OWN_BATCHES, FOREIGN_ELO_BANDS, MAX_SHAPE_REDRAWS reuse loaded batches)"
    - "Positions renumbered contiguously after snapshot failures so short sessions stay gap-free"

key-files:
  created:
    - app/services/blunder_check_selection.py
    - app/services/blunder_check_service.py
    - tests/services/test_blunder_check_selection.py
  modified:
    - app/routers/blunder_check.py
    - tests/routers/test_blunder_check_sessions.py

key-decisions:
  - "Foreign games are judged from the owner's side (user_is_white = owner's user_color), the mover the Maia values were computed for; the caller's served sets still apply (D-10)"
  - "The foreign Elo band is checked on pinned Elo after load; the raw-rating SQL prefilter is band + FOREIGN_RAW_PREFILTER_MARGIN wide because platform scales differ"
  - "Seen-but-filtered foreign ids stay in the pool's exclude list so a widened band never re-loads them"
  - "POST /sessions returns 409 when nothing could be composed; the expected 409 is rolled back but not sent to Sentry"

patterns-established:
  - "Tests force a shape by monkeypatching blunder_check_selection.draw_window_shape, and the RNG by monkeypatching new_session_rng"

requirements-completed: [D-02, D-03, D-07, D-09, D-10, D-11, D-15]

actuals:
  tokens: 22000
  tasks: 2
  commits: 2
plan_head_before: 4ada2c984c0317533b33a0846507e1ed91536584
plan_head_after: 58f68597efebb512476a047552456d2a68a2e74c
---

# Phase 249 Plan 03: Session composition and POST /sessions Summary

A beta user can press Start: `POST /api/blunder-check/sessions` draws 6 shapes, fills them from the user's own unserved evaluated games, falls back to Elo-banded strangers' games only for slots own supply cannot fit, snapshots each window and persists the session, resuming the open one when it exists.

## Tasks

1. **Task 1 (tracer)**, commit `5c0013bcc`: `blunder_check_selection` (constants, `new_session_rng`, `mover_pinned_elo`, `reference_elo`, `build_snapshot`, `legal_key_plies`, `compose_windows`), `compose_or_resume`, the POST route, and router tests (6 own windows, payload key set with no `game_id`/`ply`/`case`/`is_own` anywhere, DB rows with legal snapshot and key move, 403 non-beta, 409 no supply). The tracer verified end to end before expansion.
2. **Task 2**, commit `58f68597e`: 11 selection tests (own-first with the foreign pick patched to raise, banded non-guest foreign fallback, D-03 fit, three D-10 repeat cases, D-07 miss lead-in, short session, snapshot and reference-Elo helpers) plus router tests for resume, concurrent start and GET-open-after-POST.

## Verification

- `uv run pytest tests/services/test_blunder_check_selection.py tests/routers/test_blunder_check_sessions.py`: 22 passed. Wave 1 suites (repository, candidates, rules): 66 passed.
- `ruff check`, `ruff format`, `ty check app/ tests/ scripts/`: clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches. `asyncio.gather` count in the selection module: 0.
- Mutation checks (reverted afterwards): passing an empty prompted set to `judge_game` fails the prompted-repeat test; disabling the post-load pinned-Elo band check fails the foreign-fallback test (after tightening it: 2 in-band games plus 6 inside the raw prefilter but outside the band, so a missing exact check tops the session up with out-of-band games).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test strength] Foreign band test originally could not detect a missing exact Elo check**
- **Found during:** Task 2 mutation check
- **Issue:** The far-Elo games (2400) were already removed by the raw-rating SQL prefilter, and an 8-vs-2 mix could pass by chance.
- **Fix:** Far games rated inside the prefilter but outside the widest band; 2 in-band vs 6 far games; assert the composed set equals the in-band set.
- **Files modified:** tests/services/test_blunder_check_selection.py

No other deviations. Judgement calls: `lead_in_plies` stores `first_ply - lead_in_start(first_ply)` (0..3, clamped at game start); a window whose snapshot cannot be built is dropped and positions renumbered.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. T-249-07 (response carries no key material) is asserted by the router test; T-249-08 (only game ids of non-guest strangers stored, no other-user identifiers on windows) holds by construction and is asserted for owner/guest in the foreign test; T-249-09 (bounded queries per start, one open session so repeat POSTs resume) is enforced by the constants and the resume test.

## Hand-off notes for plans 04 and 05

- Windows store `key_uci` (best move at the blunder ply) and `refutation_uci` (opponent best reply, else first pv token) for blunder windows, both NULL for herrings; `move_ucis` runs from the lead-in start through the reply after the last judged move when it exists.
- `first_ply - lead_in_plies` is the ply of `move_ucis[0]`; the board before ply P is `start_fen` plus the first `P - (first_ply - lead_in_plies)` moves.
- Tests that need a deterministic composition monkeypatch `blunder_check_selection.new_session_rng` and/or `blunder_check_selection.draw_window_shape`; the service reads both through the module attribute.

## Self-Check: PASSED

- Files exist: selection module, service module, both test files, router edit.
- Commits `5c0013bcc` and `58f68597e` are ancestors of HEAD.
