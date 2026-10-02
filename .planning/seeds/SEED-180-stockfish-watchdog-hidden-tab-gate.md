---
id: SEED-180
status: dormant
planted: 2026-10-02
planted_during: no open milestone (after v2.19), during Phase 226 (SEED-171); Sentry prod triage
trigger_when: FLAWCHESS-9G escalates in Sentry, or the next engine worker-pool touch
scope: small (frontend-only quick task, one extra gate plus a test)
---

# SEED-180: Stockfish grading watchdog, hidden-tab gate (FLAWCHESS-9G third pass)

## Why This Matters

FLAWCHESS-9G (`Stockfish worker pool: grading watchdog timeout`) regressed a
third time. All 5 recent events are ONE session (trace
`cd34f71688c94460b13f79c4aa9605b9`, Mac Chrome 153, 2026-09-28 23:30-23:38 UTC),
firing every 1-2 minutes. The liveness fix from #324 is in production, and the
`stockfishWatchdog` context classifies the event cleanly:

| Field | Value | Reading |
|---|---|---|
| `elapsedMs` | 60264 | on time, so not page suspension (suspend gate skipped) |
| `sinceLastInfoMs` | 41957 | worker silent, so liveness gate skipped |
| `gradesAccumulated` / `candidateCount` | 5 / 5 | search essentially done, `bestmove` never arrived |
| `visibilityState` | `hidden` | background tab |
| `slotRespawns` | 7 | repeated false kills in the same session |

Shape: Chrome throttles a hidden tab's workers hard enough that they go quiet,
while the host `setTimeout` still fires on time. Neither existing gate in
`fireWatchdog` (`frontend/src/lib/engine/workerPoolWatchdog.ts`) can see that.
Each false fire costs a worker respawn and settles the request with an empty
grade map.

## What

Add a third re-arm gate in `fireWatchdog`, before the kill path: if
`document.visibilityState === 'hidden'`, re-arm instead of killing, bounded by a
new `MAX_WATCHDOG_HIDDEN_REARMS` constant (and a `hiddenRearms` slot counter
reset wherever the other two counters are), so a genuinely wedged worker in a
long-hidden tab still reaches the kill path. Add `hiddenRearms` to the
`stockfishWatchdog` Sentry context. Unit test: hidden + silent + on-time fire
re-arms, and the bound still kills.

## Not In Scope

`fireStopWatchdog` / `armStopWatchdog` stay unchanged (same reasoning as the
first pass). No change to the timeout constant itself.

## Trigger

FLAWCHESS-9G was left unresolved on 2026-10-02; if it fires again from a
different session, or with `visibilityState: "visible"`, re-read the context
before applying this gate (a visible-tab fire is a different shape).
