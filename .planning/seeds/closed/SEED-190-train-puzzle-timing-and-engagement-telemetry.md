---
id: SEED-190
status: closed. Resolved by Phase 233 (release #394). Closed at the v2.23 milestone close 2026-10-09.
promoted_to: Phase 233
promoted: 2026-10-05
planted: 2026-10-05
planted_during: ad-hoc prod analysis of Train puzzle difficulty and the weekly leaderboard (no phase)
trigger_when: before the leaderboard-effect revisit (~2026-10-25), or the next Train phase; ship early, the data only exists from the day it ships
scope: small-medium
---

# SEED-190: Train per-puzzle timing and engagement telemetry

## Why This Matters

The 2026-10-05 prod analysis (Train difficulty by time control, tempo tag,
eval gap; accuracy stability; leaderboard fairness) kept hitting the same wall:
we know WHETHER a puzzle was solved but not HOW. The only per-puzzle timestamp
is `drill_solves.solved_at` (written on the solve POST). We cannot tell:

- how long the user thought before moving (effort, guessing vs calculating),
- how long they studied the solution before pressing Next (learning effort),
- whether a points race (Phase 230 weekly leaderboard, live 2026-10-04) makes
  people faster and sloppier.

Current proxy, solve-to-solve gaps within a session (last 14 days): median 63s,
p10 22s, p90 218s, 6.6% over 5 min. It lumps together the previous reveal, the
verdict guess, the move, and breaks. Good enough for population medians, useless
per puzzle. First puzzle of a session uses `drill_sessions.entered_at`, which is
NULL on older sessions.

The server cannot measure any of this: a session's puzzles are pre-materialized
at composition (P-07), so the backend never knows when a given puzzle is shown.
Timing must be measured client-side.

## What

### 0. Storage: one `telemetry` JSONB column on `drill_solves` (owner decision 2026-10-05)

All fields below (`guess_ms`, `move_ms`, `review_ms`, `review_*` counters,
`hidden_ms`, ...) are KEYS in a single nullable `drill_solves.telemetry` JSONB,
not individual columns. Rationale: low-volume table (~8k rows, ~300/day) so no
storage/index cost; new counters need no migration; keeps behavioral data
visibly separate from grading fields (`move_quality`, `correct_guess`).

Rules:

- Validate at the API boundary with a Pydantic model (`extra="forbid"`, typed
  and capped int/bool fields, a `v` schema-version key). The model is the
  schema; nothing unvalidated reaches the column.
- Two writes per puzzle (solve POST, then review flush) MERGE:
  `telemetry = coalesce(telemetry, '{}'::jsonb) || :patch`. Never overwrite.
- asyncpg gotcha: Python `None` writes JSON `null`, not SQL NULL. Omit the
  column when there is nothing to store so "no telemetry" stays `IS NULL`.
- Promote a key to a real column only if it becomes product-facing (UI,
  scoring, leaderboard).

### 1. Think time (solve phase)

Client measures from "board shown" to submission and sends it with
`POST /train/sessions/{id}/solve` (`SolveRequest`, `app/schemas/train.py`).
Split it, since the verdict guess comes first:

- `guess_ms`: board shown -> guess button pressed
- `move_ms`: guess pressed -> move played

Stored as `telemetry` keys (section 0). Missing key = pre-seed row or a client
that did not send it; go-forward only, no backfill, same precedent as
`move_quality`.

### 2. Review time (reveal phase)

Time from the reveal appearing to pressing Next (`handleNextFromReveal`,
`frontend/src/components/train/TrainSolveScreen.tsx`; `handleNext` in
`frontend/src/pages/Train.tsx`). The solve POST has already happened when the
reveal opens, so this needs its own write. Options:

- (a) a small `POST /train/sessions/{id}/solves/{position}/review` on Next,
  plus `navigator.sendBeacon` on `pagehide` so the last puzzle / abandoned
  sessions are not lost. Recommended.
- (b) piggyback the previous puzzle's `review_ms` on the next solve POST.
  Simpler, but loses the last puzzle of every session and every abandon.

Key: `review_ms` in `telemetry`.

### 2b. Reveal engagement summary (one write per puzzle, not per click)

Already tracked in Umami (Phase 229 `trackFeature`): `action` with targets
`train-solution` (back to the solution after departing the board), `analyze`
(open the game in Analysis), `train-explore-exit`. NOT tracked: line-card
spotlights, TrainLineStepper steps (prev/next/token clicks), entering free-play
exploration, flipping during exploration, the Also-fine card.

Do not add per-click events. Accumulate counters in the reveal component and
flush them ONCE with the same write as `review_ms` (Next press or `pagehide`
beacon). Stored on the solve row so engagement joins to the outcome (wrong vs
right, source, move_quality) and to the next attempt at the same SR item, which
Umami data cannot do (no puzzle identity, only user + timestamp).

Suggested `telemetry` keys (small ints/bools, go-forward only):

- `review_cards_opened`: distinct line cards (plus Also-fine) the user
  inspected. Mobile: tap. Desktop: spotlight is hover-driven, so count a hover
  only if held >= a named threshold (~800 ms) to drop pointer fly-overs.
- `review_line_steps`: total stepper moves (prev/next/token), capped (e.g. 50).
- `review_explored`: boolean, entered free-play exploration (board moves).
- `review_explore_moves`: moves played during exploration, capped.
- `review_analyze_opened`: boolean (duplicates the Umami `analyze` action, but
  joinable).

Umami stays for funnels only. If a coarse Umami view is wanted, mirror ONE
`train-review` event per puzzle with bucketed string props
(`cards: 0|1|2|3+`, `steps: 0|1-3|4-10|11+`, `explored: on|off`), added to
`FeatureEventMap` in `frontend/src/lib/analytics.ts`. Pattern precedent:
`useDebouncedTrackFeature` (one event per burst, flush on unmount), but note it
has no `pagehide` flush, so the reveal flush needs its own.

### 3. Data-quality guard (applies to 1 and 2)

Count only visible time: pause the timer while `document.visibilityState` is
`hidden` (tab switched, phone locked). Optionally store `hidden_ms` so outliers
can be explained. Cap stored values (e.g. 30 min) as a named constant to keep
a forgotten tab from producing a 9-hour "think".

### 4. Other gaps worth closing in the same pass (owner to pick)

- **Puzzle shown, never solved.** Abandons are only visible at session level
  (`solved_at IS NULL`); we cannot tell "quit on seeing this puzzle" from "quit
  between puzzles". A `shown_at` stamp (set by the same review/visibility
  plumbing, or a tiny view ping) answers "which puzzles make people quit".
- **Leaderboard exposure.** The Points/Accuracy toggle is tracked
  (`tab-switch`, `TrainLeaderboardCard.tsx:392`), but simply seeing the card
  is not, and the default tab never fires. Without an exposure signal the
  leaderboard-effect analysis cannot separate users who saw it from users who
  did not. Cheap: one impression event per page visit when the card scrolls
  into view (IntersectionObserver), not per render.
- **Device class on the solve row.** Mobile vs desktop plausibly shifts both
  speed and accuracy; Umami has it but is not joinable per solve. A
  `client_kind` (`mobile`/`desktop`, TEXT + CHECK) on `drill_solves` or
  `drill_sessions` would make it a covariate.

## Analysis this unlocks

- Leaderboard effect on effort: think/review time before vs after, within user.
- Speed-accuracy trade-off per user (fast-and-wrong vs slow-and-right).
- Does review time predict the NEXT attempt at the same SR item? (Does
  studying the solution actually help?)
- Puzzle difficulty from time, not just success (two puzzles solved at 70%
  can differ 3x in think time).

## Notes

- Not a CLAUDE.md "dev clock" case: these are client-measured durations, not
  server `now()` calls.
- Keep grading untouched: timing fields are recorded outcomes, never inputs to
  `move_quality` / `correct_guess` / scoring (D-01 spirit).
- Privacy page (`frontend/src/pages/Privacy.tsx`) may need a line if device
  class is stored.
