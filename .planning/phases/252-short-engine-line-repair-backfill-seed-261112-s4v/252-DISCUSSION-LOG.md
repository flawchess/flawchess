# Phase 252: Short Engine Line Repair Backfill - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-12
**Phase:** 252-Short Engine Line Repair Backfill
**Areas discussed:** Best-move mismatch, Re-walk scope and order, Bound-valued evals, Run mechanics

---

## Best-move mismatch

| Option | Description | Selected |
|--------|-------------|----------|
| Pin to stored best move | Restrict the re-search to the stored best move; nothing downstream changes | ✓ |
| Free search, update best move | Overwrite best move on mismatch; best-move rows, badges, Maia scores go stale | |
| Free search, skip mismatches | Write only matching lines; unknown share stays short | |

**User's choice:** Pin to stored best move.

| Option | Description | Selected |
|--------|-------------|----------|
| Free search, write both | No stored best move: store line and its first move as best move | ✓ |
| Free search, line only | Store the line, leave best move empty | |
| Skip these rows | Leave as is, report the count | |

**User's choice:** Free search, write both.

---

## Re-walk scope and order

| Option | Description | Selected |
|--------|-------------|----------|
| Only the repaired line | About 26M searches; needs a selector change for one NULL line | ✓ |
| Both lines of the flaw | Simpler selector, about 42M searches | |

**User's choice:** Only the repaired line.

| Option | Description | Selected |
|--------|-------------|----------|
| Active users first | Users active in the last 30 days first (recommended by Claude) | |
| Newest games first | Strictly by game date across all users | ✓ |
| No ordering | Existing random lottery | |

**User's choice:** Newest games first.

---

## Bound-valued evals

| Option | Description | Selected |
|--------|-------------|----------|
| Measure first, decide after | Pilot measures the classification flip rate; evals untouched | ✓ |
| Leave them, no measurement | Accept the noise | |
| Re-evaluate everything | 3-4 months of fleet time, flaw sets reshuffle | |

**User's choice:** Measure first, decide after.

| Option | Description | Selected |
|--------|-------------|----------|
| Leave as they are | Untouched walks and best-move rows keep their values | ✓ |
| Include in the measurement | Also estimate badge flips | |

**User's choice:** Leave as they are.

---

## Run mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Operator script on your box | Resumable script, local engines, DB tunnel, about 5 days | ✓ |
| New worker lane on the fleet | About 3 days, needs endpoint and worker release | |

**User's choice:** Operator script on your box.

| Option | Description | Selected |
|--------|-------------|----------|
| Stop and report first | Explicit go before each long run (recommended by Claude) | |
| Proceed automatically | Full runs start if the pilot meets thresholds | ✓ |

**User's choice:** Proceed automatically.
**Notes:** Follow-up on stop rules: all four selected (repair does not stick, time estimate blown, write errors or
DB load, high eval flip rate).

| Option | Description | Selected |
|--------|-------------|----------|
| Prod lines, prod walks, then benchmark | Benchmark line repair alongside the prod re-walk | ✓ |
| Finish prod completely first | | |
| Benchmark first | Full rehearsal on the smaller DB | |

**User's choice:** Prod lines, prod walks, then benchmark.

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed engine count, worker keeps running | Recommended by Claude | |
| Stop the worker, use all engines | Fastest repair on that box | ✓ |
| You decide per run | | |

**User's choice:** Stop the worker, use all engines.

| Option | Description | Selected |
|--------|-------------|----------|
| Require updated Hetzner workers | Script refuses without another version-3 worker (recommended by Claude) | |
| Server pool is enough | Start regardless, no check | ✓ |
| Warn only | | |

**User's choice:** Server pool is enough.

---

## Claude's Discretion

Batch sizes, commit cadence, reporting; implementation of the ordered re-walk claim; whether benchmark runs need
lane-specific handling; the SQL for excluding legitimately short lines.

## Deferred Ideas

Re-evaluation of bound-valued evals (only if the measurement warrants it), badge recompute, regrading solved
drills, the stale `ANALYSIS_FREE_RUN_MIN_MULTIPV` comment.
