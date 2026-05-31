# Phase 91: Two-lane import — defer Stockfish eval to in-process cold drain - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** 91-Two-lane import — defer Stockfish eval to in-process cold drain
**Areas discussed:** Header bar — endpoint + placement; Per-metric caveat plumbing; Migration backfill strategy; Cold-drain pick order

**Pre-discussion context:** The architectural decisions for this phase were locked earlier on 2026-05-20 via `/gsd-explore` (see `.planning/notes/2026-05-20-import-pipeline-rethink.md`). That session produced SEED-023, marked SEED-022 superseded, and inserted Phase 91 into ROADMAP. The discuss-phase session below focused only on the four implementation-detail gray areas SEED-023 explicitly handed off to discuss-phase.

---

## Header Bar — Endpoint + Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Extend GET /imports/active | Include `eval_coverage` field per user; ties to existing import-progress endpoint | |
| New GET /imports/eval-coverage | Dedicated endpoint, independent from import job lifecycle | ✓ (Claude's discretion) |
| Topbar placement (global) | Visible across all pages | |
| Page-level on Endgames + Openings/Stats | Only where Stockfish-dependent metrics live | ✓ (Claude's discretion) |
| Sticky beneath import progress bar | Tied to import flow | |

**User's choice:** "I'll let you decide on all points."

**Notes:** Claude selected the dedicated endpoint because `/imports/active` returns a `list`, not an envelope object — there's no clean place to attach a sibling `eval_coverage` field without breaking existing callers. Page-level placement on Endgames + Openings/Stats avoids both topbar chrome (irrelevant on Bookmarks/Library/Import pages) and double-bar noise on the Import page itself. Polling cadence 10s with TanStack Query `refetchInterval: pct === 100 ? false : 10_000` to stop polling at 100%. See CONTEXT.md D-01 through D-04.

---

## Per-Metric Caveat Plumbing

| Option | Description | Selected |
|--------|-------------|----------|
| Centralized hook `useEvalCoverage()` | Single source of truth; fewer touch sites; shared TanStack Query key with header bar | ✓ (Claude's discretion) |
| Per-component prop drilling | Explicit, test-friendly, harder to drift | |

**User's choice:** "I'll let you decide on all points."

**Notes:** Centralized hook selected because the pending count is per-user (not per-component or per-metric) — there's one number to share. Sharing the TanStack Query key with the header bar means one HTTP call per page regardless of popover count. Caveat copy is a single conditional `<p>` inside existing popover bodies; no new component family. See CONTEXT.md D-05 through D-07.

---

## Migration Backfill Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Mark all existing complete | `evals_completed_at = COALESCE(updated_at, created_at, NOW())` for every row | ✓ (Claude's discretion) |
| Detect missing evals | One-time SQL pass; leaves NULL for rows with NULL entry-ply eval; creates large cold-lane backlog on first deploy | |

**User's choice:** "I'll let you decide on all points."

**Notes:** Mark-all-complete selected because every pre-Phase-91 game already passed through the in-transaction eval pass. Rows that ended up with NULL eval_cp/eval_mate on entry plies are there because the engine returned `(None, None)` for that position (D-11 path, captured to Sentry at the time). Re-running them on every backend startup would be unbounded retry against engine errors that won't change without engine config changes. Operators who want to retroactively retry can run `scripts/backfill_eval.py --db prod` manually — already exists. See CONTEXT.md D-08 through D-10.

---

## Cold-Drain Pick Order

| Option | Description | Selected |
|--------|-------------|----------|
| FIFO (`ORDER BY id ASC`) | Oldest pending first; simple, predictable | |
| LIFO (`ORDER BY id DESC`) | Newest first; user sees evals fill in for the games they just imported | ✓ (Claude's discretion) |

**User's choice:** "I'll let you decide on all points."

**Notes:** LIFO selected because the user-visible feedback loop matters more than backlog-fairness. With FIFO, User B's fresh import waits behind any leftover backlog from User A's previous failed import. With LIFO, User B's evals start completing within seconds of their import landing. No DB cost difference — B-tree indexes scan in either direction. Per-user fairness ordering (round-robin) is unnecessary at current concurrent-user counts; revisit if real production traffic shows starvation. See CONTEXT.md D-11 through D-13.

---

## Claude's Discretion

All four gray areas above were explicitly delegated by the user ("I'll let you decide on all points"). Decisions D-01 through D-13 in CONTEXT.md are the locked outcomes. Planner has flexibility on filename conventions, exact copy wording (within the project's existing voice constraints from `feedback_popover_copy_minimalism`), and test structure (matching prior import-pipeline phases).

## Deferred Ideas

- Concurrent-import admission control (SEED-022 option F).
- Scheduled backend restart cadence (SEED-022 option G).
- Idempotent `on_game_fetched` for lichess stream-retry (SEED-022 option A′).
- Per-user fairness in cold-lane pick order.
- Per-ply (not per-game) eval pending state.
- Retroactive re-eval of historical engine-failure rows.

All preserved in CONTEXT.md `<deferred>` section.
