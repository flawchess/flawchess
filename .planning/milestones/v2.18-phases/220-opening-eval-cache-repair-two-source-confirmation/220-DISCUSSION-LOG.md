# Phase 220: Opening Eval Cache Repair & Two-Source Confirmation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-09
**Phase:** 220-opening-eval-cache-repair-two-source-confirmation
**Areas discussed:** Ship order & dedup-off window, Prod run choreography, Herrings & drills at repaired plies, Nightly check & agree tolerance (all delegated to Claude)

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Ship order & dedup-off window | Hardening before/after the prod repair; what happens to the 2.57M legacy rows when `confirmed` lands | (delegated) |
| Prod run choreography | Pause drain/workers or not; strict vs pipelined stage gating; when the CACHEFIX-10 sample runs | (delegated) |
| Herrings & drills at repaired plies | herring_pool delete-vs-keep; drill_items prune details | (delegated) |
| Nightly check & agree tolerance | Manual db-report section vs in-app tick; 50cp vs expected-score agree tolerance | (delegated) |

**User's choice:** "I'll let you decide" (all four areas).
**Notes:** None.

## Todos

| Option | Description | Selected |
|--------|-------------|----------|
| None, skip them | All four `todo.match-phase` hits are keyword noise | ✓ |
| Show me the matches first | Print title + reason before deciding | |

**User's choice:** None, skip them.

---

## Claude's Discretion

All four areas. Alternatives weighed (see CONTEXT.md D-01..D-13 for the chosen side):

- Ship order: hardening-first (dedup-off window on prod, or lying `confirmed=true` on
  unscreened rows) vs repair-first (chosen).
- Choreography: pause lotteries during rederive (fallback only) vs game-row lock +
  no-resurrect invariant (chosen); pipelined confirm-behind-screen vs strict gating
  (chosen); legacy sample before screen vs after report (chosen).
- Herrings: delete at repaired plies vs keep (chosen; ladder is self-sufficient).
- Integrity check: in-app daily asyncio tick vs db-report skill section (chosen).
- Agree tolerance: 50cp vs expected-score constant from the calibrated floor (chosen).
- Disagreement Sentry: per event vs at `disagreements >= 2` on a row (chosen).
- Added: `source_game_id` column to block self-promotion (not in the seed).

## Deferred Ideas

- Optional confirmed-hit canary (only if trivial).
- Post-hardening re-audit mode in the repair script (documented, not built).
