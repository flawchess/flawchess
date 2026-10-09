# Phase 233: Train Per-Puzzle Timing & Engagement Telemetry - Context

**Gathered:** 2026-10-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Record HOW each Train puzzle was solved, not just whether: client-measured think time (guess +
move), review time, a reveal-engagement summary, and a device class, all as keys in one nullable
`drill_solves.telemetry` JSONB written by two merging writes per puzzle (the existing solve POST,
plus a new review flush on Next / page unload). Go-forward only, no backfill. Telemetry is a
recorded outcome and never feeds grading, scoring or the leaderboard. Ship early: the data only
exists from the day it ships (leaderboard-effect revisit ~2026-10-25).

Not in scope: any UI that shows timing, any per-click event stream, any new Umami event.

</domain>

<decisions>
## Implementation Decisions

### Locked upstream (SEED-190 + ROADMAP Phase 233, owner 2026-10-05; do not re-open)
- **D-01 Storage:** one nullable `drill_solves.telemetry` JSONB, not individual columns. Validated
  at the API boundary by Pydantic models (`extra="forbid"`, typed and capped int/bool/Literal
  fields, a `v` schema-version key); nothing unvalidated reaches the column. Writes MERGE:
  `telemetry = coalesce(telemetry, '{}'::jsonb) || :patch`, never overwrite. When a request carries
  no telemetry, OMIT the column from the write so "no telemetry" stays SQL `IS NULL` (asyncpg writes
  Python `None` as JSON `null`, see memory `project_asyncpg_jsonb_null_vs_sql_null`). Promote a key
  to a real column only if it becomes product-facing.
  — **Reversibility:** costly — adds a column via Alembic migration; dropping it later loses the
  collected data, which cannot be regenerated.
- **D-02 Think time:** `guess_ms` (board shown -> guess pressed) and `move_ms` (guess pressed ->
  move played), measured client-side, sent as optional telemetry on `POST
  /train/sessions/{id}/solve` (`SolveRequest`). The server cannot measure this (puzzles are
  pre-materialized at composition, P-07). The telemetry part is optional so an old client (stale
  bundle) still solves.
- **D-03 Review time + engagement:** `review_ms` plus engagement counters accumulated in the reveal
  and flushed ONCE per puzzle via a new `POST /train/sessions/{id}/solves/{position}/review`, on
  Next and on `pagehide` (so the last puzzle of a session and abandons are not lost). No per-click
  events.
- **D-04 Data quality:** count only visible time (pause while `document.visibilityState` is
  `hidden`); store `hidden_ms` alongside; cap every stored duration at a named constant (~30 min).
- **D-05 Grading untouched:** telemetry is never an input to `move_quality`, `correct_guess`,
  scoring, SR ladder, or the leaderboard.

### Correction to the roadmap wording (transport)
- **D-06:** Do NOT use `navigator.sendBeacon` for the unload flush. Auth is FastAPI-Users
  `BearerTransport` (`app/users.py:198`) and sendBeacon cannot set an `Authorization` header, so a
  beacon would 401. Use `fetch(url, { keepalive: true, headers: { Authorization } })` (or axios with
  the fetch adapter + `fetchOptions: { keepalive: true }`) for the `pagehide` flush. Next can use the
  normal `apiClient` call. The roadmap's "sendBeacon" means "a write that survives unload".

### Owner picks from SEED-190 §4
- **D-07 shown / abandon signal: derive, no extra ping.** The review flush carries
  `exit: "next" | "pagehide"`. "Puzzle N was shown" is derived from puzzle N-1 having `exit = next`
  (position 0: `drill_sessions.entered_at`). No third write per puzzle. Accepted blind spot: a reload
  that resumes mid-session.
- **D-08 Leaderboard exposure: no impression event.** Owner only wants the Points/Accuracy toggle
  tracked, and it already is (`TrainLeaderboardCard.tsx:392`, Umami `tab-switch` with
  `LEADERBOARD_TAB_TARGET`). The plan verifies this (an existing or added test asserting the event
  fires on toggle) and adds nothing else. No IntersectionObserver impression.
- **D-09 Device class: telemetry key per solve.** `client: "mobile" | "desktop"` inside
  `telemetry`, a Pydantic `Literal`. No migration, no `drill_sessions` column, correct when a session
  is resumed on another device. Add one line to `frontend/src/pages/Privacy.tsx`.
- **D-10 No `train-review` Umami mirror:** The DB row is the single source; Umami stays funnels-only.

### Engagement counter rules
- **D-11 Card "opened":** mobile = a tap that spotlights a card. Desktop = a hover held for at least
  a named constant of 800 ms (drops pointer fly-overs on the way to Next); a desktop card CLICK
  (the board-departed branch that restores the solution and spotlights) counts immediately. Applies
  to line cards and the Also-fine card.
- **D-12 Distinct count:** `review_cards_opened` = distinct cards inspected at least once. Also
  store `review_cards_total` = number of cards shown on that reveal, so coverage is computable.
- **D-13 Walkthrough flag:** store `review_walkthrough: true` when the Phase 222 first-reveal
  walkthrough (`useTrainWalkthrough`) was active on that reveal. Counters are still recorded
  normally; analysis filters on the flag.
- **D-14 Counter set (closed):** `review_cards_opened`, `review_cards_total`, `review_line_steps`
  (prev/next/token, capped), `review_explored` (bool), `review_explore_moves` (capped),
  `review_analyze_opened` (bool), `review_walkthrough` (bool). NO flip counter, NO Solution-return
  counter (the return is already in Umami `train-solution`).

### Claude's Discretion (owner accepted these defaults)
- **Timer interruptions:** a reload/remount mid-puzzle that loses the in-memory timer stores what
  was measured from the restart plus `resumed: true`. The Analyze round-trip (reveal remount via the
  `restoredSolve` cache) keeps ONE review timer across the remount (persist the start/accumulated
  values in the same cache), so `review_ms` covers the whole reveal.
- **Flush semantics:** per-key last write wins via the jsonb `||` merge. Once Next has flushed a
  puzzle, a later `pagehide` for that puzzle is a no-op (client-side "flushed" guard). The review
  endpoint accepts a flush only for a SOLVED row (`solved_at IS NOT NULL`) owned by the caller (user
  id from `current_active_user`, never the body), and DOES accept it after the session is
  completed or expired: it is the user's own row and the last puzzle's flush always lands after
  completion.
- **`review_explored` definition:** true once the user plays at least one free-play move on the
  reveal board (entering exploration happens by moving a piece).
- **Caps / constants:** exact cap values for durations (~30 min) and counters (line steps ~50,
  explore moves similar), each a named constant shared by the Pydantic model and the client.
- **`client` detection:** reuse an existing signal (e.g. the UA check in `useInstallPrompt`) rather
  than inventing a new one; pick whatever is already the project's mobile definition.
- **Schema version:** `v: 1` on both patches.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source
- `.planning/seeds/SEED-190-train-puzzle-timing-and-engagement-telemetry.md` — full rationale,
  storage rules, suggested keys, analyses this unlocks.
- `.planning/ROADMAP.md` § "Phase 233" — locked scope (note D-06 supersedes its "sendBeacon").

### Backend
- `app/models/drill_solve.py` — `DrillSolve` (add `telemetry` JSONB; module docstring explains the
  pre-materialized rows).
- `app/schemas/train.py` — `SolveRequest` (add optional telemetry), new review-flush request model.
- `app/routers/train.py` — `solve_puzzle` (~line 134), `mark_session_entered` (~186, the shape for
  a small 204 write), `reveal_puzzle` (~214, the solved-row ownership gate to mirror).
- `app/repositories/train_repository.py` — `record_solve` (~2870), `stamp_session_entered` (~905).
- `app/users.py:198` — `BearerTransport` (why sendBeacon is out).

### Frontend
- `frontend/src/components/train/TrainSolveScreen.tsx` — guess/move flow, `handleNextFromReveal`
  (~1596), `restoredSolve` reveal cache, `isBoardDeparted`, free-play wiring.
- `frontend/src/components/train/TrainReveal.tsx` — card spotlight handlers (~120-175, mobile tap vs
  desktop hover), Also-fine entry, exploration card.
- `frontend/src/components/train/TrainLineStepper.tsx` — `onStepChange` (line steps).
- `frontend/src/hooks/useTrainWalkthrough.ts` — walkthrough active state (D-13).
- `frontend/src/hooks/useTrainFreePlay.ts` — exploration moves.
- `frontend/src/pages/Train.tsx` — `handleNext`.
- `frontend/src/api/client.ts` — axios `apiClient` + Bearer interceptor (keepalive flush needs the
  token).
- `frontend/src/hooks/useBotGameClock.ts` (~260, ~322) — existing visibility-pause timer pattern.
- `frontend/src/hooks/useInstallPrompt.ts:190` — existing `isMobile` UA check.
- `frontend/src/components/train/TrainLeaderboardCard.tsx:392` + `frontend/src/lib/analytics.ts` —
  existing `tab-switch` tracking (D-08).
- `frontend/src/pages/Privacy.tsx` — one line for the device class (D-09).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useBotGameClock` visibility handling: a working pause-on-hidden / resume-on-visible timer to
  copy for the think and review timers.
- `useInstallPrompt().isMobile`: the project's existing mobile definition for `client`.
- `restoredSolve` reveal cache in `TrainSolveScreen`: already survives the Analyze round-trip; the
  review timer state rides along there.
- `mark_session_entered` route: the template for a small authenticated 204 write with the
  Sentry-capture/rollback shape.

### Established Patterns
- Router: user id only from `current_active_user`, `sentry_sdk.set_context("train", ...)` +
  `capture_exception()` on unexpected errors, rollback then 404 when the row is not found.
- JSONB writes: omit the column for SQL NULL (asyncpg None -> JSON null).
- Pydantic at the boundary, `Literal` for fixed sets, named constants for every cap/threshold.
- Phase 229 `trackFeature` for Umami; nothing new needed there this phase.

### Integration Points
- `SolveRequest` gains an optional telemetry object; `record_solve` merges it into the row it already
  updates (single statement, no second round-trip).
- New `POST /train/sessions/{session_id}/solves/{position}/review` route (relative path under the
  existing `/train` router prefix).
- Alembic migration adding the nullable JSONB column (no index; ~8k rows, ~300/day).

</code_context>

<specifics>
## Specific Ideas

- Analyses the data must support (SEED-190): within-user think/review time before vs after the
  leaderboard launch; speed-accuracy trade-off; whether review time predicts the next attempt at the
  same SR item; puzzle difficulty from time, not just success.
- Abandon analysis relies on `exit` (D-07), so `exit` must be set on every review flush.

</specifics>

<deferred>
## Deferred Ideas

- Leaderboard exposure impression (IntersectionObserver, one per visit): declined by owner for now;
  revisit only if the ~2026-10-25 analysis cannot separate exposure from visiting /train.
- Bucketed `train-review` Umami event: declined (D-10).
- Explicit per-puzzle shown ping: declined in favour of deriving from `exit` (D-07).

</deferred>

---

*Phase: 233-train-puzzle-timing-telemetry*
*Context gathered: 2026-10-05*
