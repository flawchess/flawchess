---
phase: 252-short-engine-line-repair-backfill-seed-261112-s4v
plan: 06
subsystem: operations
tags: [prod, line-repair, backfill]

requires:
  - phase: 252-05
    provides: Phase 252 code live in production, pre-repair baselines
provides:
  - "game_positions.pv repaired on prod for all 1,056,391 non-guest work-list games"
  - "prod repair completion time for the Phase 250 / 254 line pass: 2026-11-18 about 21:40 UTC"
affects: [252-07, 252-08, 252-09, 250, 254]
---

# Plan 252-06: prod line repair

The prod line repair is complete. All tasks were performed by the orchestrator session.

## Owner answers (verbatim)

- Task 2 (how to run): **"Pilot then full (Recommended)"**
- Flip gate STOP (25.9% stored-vs-exact against a 24.7% control): **"Not material, capture a seed (Recommended)"**.
  Seed: `.planning/seeds/SEED-261112-f7q-mistake-blunder-label-reproducibility.md`.
- 2026-11-13: the owner moved the run to a 32-thread Windows machine ("let's stop the phase 252 on this machine and
  continue it on the windows machine").

## Measurements before the first write

| Check | Result |
|---|---|
| Flip share, stored vs exact (199 games, 12,864 plies per arm) | 365 / 1,410 = 0.2589 |
| Flip share, control (exact vs exact) | 355 / 1,439 = 0.2467 |
| Dry-run pilot (2,000 games) | 5,510 searched, 0 still short, 0 pin mismatch, 0 failed, projected 7.31 days |
| Sentry re-read about 2 h after the deploy | no new issues |

## Run history

| Segment | Machine | Games (cursor) | Lines written | Still short | Failed | Report |
|---|---|---|---|---|---|---|
| Pilot, 2026-11-12 20:28 to 22:07 UTC | owner's Linux box, 8 engines | 0 to 10,564 | 30,652 | 0 | 0 | `repair-prod-all-pilot-20261112T2207Z.md` |
| Full, to the owner's pause 2026-11-13 09:55 UTC | Linux box | to 86,564 | 225,818 | 0 | 0 | `repair-prod-all-full-20261113T0955Z.md` |
| Full, to the handoff 2026-11-13 22:38 UTC | Linux box | to 145,164 | 175,729 | 0 | 0 | `repair-prod-all-full-20261113T2238Z.md` |
| Full, 2026-11-13 about 23:00 to 2026-11-18 about 21:40 UTC | Windows laptop, 28 engines | to 1,056,391 | not available here | not available here | not available here | reports stayed on the Windows machine |

The Windows segment was interrupted by a prod reboot (2026-11-14 02:15 UTC) and at least two further restarts; each
resumed from the saved cursor. Its per-segment reports were never copied to this machine, so its counters are not in
the repo. Completion was established from prod itself (below), not from an exit marker: no `EXIT_FULL=0` line exists
on this machine for that segment.

All gates passed in every segment recorded here (pilot: still_short 0/0.03, projected days 6.87/10, pin mismatch 0,
failed batches 0, connections 21/29, commit latency ratio 1.01/3).

## Completion check on prod (read-only, 2026-11-18 21:44 to 22:12 UTC)

Selector A of `scripts/repair_short_lines.py` run over the whole frozen work list in chunks of 4,000 games:

| Measure | Value |
|---|---|
| Flaw-line start rows examined | 12,747,771 |
| Rows still shorter than 3 plies | 5,946 (0.047%) in 5,012 games |
| Spread over the work list | even, 243 to 400 per 50,000 games |
| Pre-repair share (plan time) | about 28% |

## Residual pass (2026-11-18 22:15 to 22:19 UTC, owner: "fill remaining gaps if possible")

The repair was run a second time from this machine over only those 5,012 games (dry run first, then the write):

| Counter | Value |
|---|---|
| Line already ends the game (never searched) | 5,880 |
| Searched | 67 |
| Written | 4 |
| Short mate lines (legitimate) | 40 |
| Failed (engine returned no line after the retry) | 25 |
| Still short, pin mismatch, failed batches | 0 |

So after the repair 25 rows on prod remain unrepaired; every other short row is a line that legitimately ends within
two plies. Reports: `repair-prod-residual-pass-dryrun-20261118T2215Z.md`, `repair-prod-residual-pass-20261118T2218Z.md`.

## Notes for Phase 250 / 254

- The prod pv repair finished 2026-11-18 at about 21:40 UTC (last four rows written 22:18 UTC).
- Another session started the Maia-free line pass on prod at 22:14 UTC
  (`backfill_maia_flaws.py --db prod --mode line --cutoff 2026-11-18T22:14:00+00:00`), after release #488 (line facts
  for opponent blunders). It reads the repaired lines.

## Deviations

- The run moved machines at cursor 145,164; the Windows reports are missing from the repo.
- The frontier was tracked by sampling prod because the Windows cursor was not visible from this session.
- The local repair cursor file was set to 1,056,391 by hand after the completion check, so the plan 07 feeder's
  fence matches the real state (the previous local value, 145,164, is kept as
  `temp/line-repair/prod-all-repair-cursor.stale-145164.json`).
- The benchmark line repair (plan 07 Task 2) ran early, 2026-11-14 to 2026-11-16, at the owner's request.
- This SUMMARY was written by the orchestrator instead of a continuation executor.

## Self-Check: PASSED
