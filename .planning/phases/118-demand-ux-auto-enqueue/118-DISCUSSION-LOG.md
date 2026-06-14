# Phase 118: Demand UX + Auto-Enqueue - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** 118-Demand UX + Auto-Enqueue
**Areas discussed:** Auto-enqueue triggers, "Analyze more" affordance, Coverage indicators, In-flight status & guests

---

## Auto-enqueue triggers (QUEUE-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy on eval-surface load | Idempotent enqueue on Library load, debounced per session | |
| On login/session start | Enqueue once per session boot | |
| Import completion only | Drop activity trigger; rely on tier-3 | |

**User's choice (activity trigger):** Free-text — "use the last_activity timestamp in the users table. is this about tier 3?" Clarified tier-2 vs tier-3, then offered the `last_activity`-hook design.

| Window option | Description | Selected |
|---------------|-------------|----------|
| 200 most recent | Matches ROADMAP "~200", <1-day catch-up | ✓ |
| 500 most recent | ~2-day, deeper | |
| Constant to tune | 200 as a named constant | (folded in) |

**Follow-up — Trigger mechanism:**

| Option | Description | Selected |
|--------|-------------|----------|
| Hook into last_activity write | Tier-2 enqueue piggybacks the ≤1/hr middleware write | ✓ |
| Periodic backend sweep | Scheduled scan of recent users | |
| Frontend lazy trigger | Client calls "ensure window" on load | |

**Follow-up — Tier-3 ordering:**

| Option | Description | Selected |
|--------|-------------|----------|
| Leave out of scope | Tier-3 stays global played_at order | |
| Fix tier-3 ordering too | Add last_activity-desc (D-4 intent) | ✓ |

**Notes:** User correctly identified `last_activity` as the trigger lever. Confirmed
auto-enqueue is tier-2, not tier-3. Window = 200, extracted as constant.

---

## "Analyze more" affordance (EVUX-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Both: per-game + bulk | tier-1 per-game button + tier-2 bulk button | ✓ |
| Bulk only | EVUX-01 button only | |
| Per-game only | tier-1 only | |

**Bulk scope:**

| Option | Description | Selected |
|--------|-------------|----------|
| Next chunk, repeatable | next ~200 into tier-2 | (refined below) |
| Filter-scoped batch | import-style filters | |
| All remaining recent | one-shot all | |

**User's choice:** Free-text skepticism — "Not sure this is a good idea. Would this button
be disabled until all tier-2 games are processed?" Surfaced the fixed-throughput-pool
reality. Re-asked with three honest models:

| Model | Description | Selected |
|-------|-------------|----------|
| Disabled-until-drained chunk | next ~200 only when window empty; "Analyzing… N of M" otherwise | ✓ |
| One-time escalation toggle | "Prioritize all my games" | |
| Drop bulk; CTA + per-game | no standalone bulk button | |

**Progress:**

| Option | Description | Selected |
|--------|-------------|----------|
| Poll eval-coverage | reuse useEvalCoverage interval | ✓ |
| New analysis-job entity | tracked job per click | |

**Notes:** User confirmed bulk = tier-2, single = tier-1. Disabled-until-drained prevents
meaningless pile-up on a reorder-only (not accelerate) queue.

---

## Coverage indicators (EVUX-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Library flaw surfaces | upgrade existing badge family; replace "coming soon" copy | ✓ |
| All eval-dependent surfaces | also redo Endgames/Openings | |

| CTA threshold | Description | Selected |
|---------------|-------------|----------|
| Extract as a constant | LOW_COVERAGE_THRESHOLD, default ~<80% | ✓ |
| Below 50% | quieter | |
| Any games pending | most aggressive | |

| Coverage basis | Description | Selected |
|----------------|-------------|----------|
| Single: is_analyzed | gate on flaw counts (lichess OR engine) | ✓ |
| Split eval vs PV now | two numbers | |

**User's choice + directive:** "Single: is_analyzed. But make sure that lichess games with
imported evals (no best_move, no pv) are not queued in tier 2. And they should be
prioritized last in tier 3 as well." → D-118-03 (tier-2 excludes lichess-eval games) +
D-118-04 (tier-3 pushes them last). The D-118-07 assumption (tier-1 explicit re-analyzes
them) was **rejected by the user on follow-up (2026-06-14)**: lichess-eval games are
excluded from tier-1 too — the per-game button is hidden for them; best_move/PV is
backfilled in the background (tier-3 tail) only when a PV-consuming surface needs it.

---

## In-flight status & guests (EVUX-03 + ROADMAP criterion 5)

| Granularity | Description | Selected |
|-------------|-------------|----------|
| Aggregate + per-game for tier-1 | aggregate badge + local "Analyzing…" on clicked game | ✓ |
| Aggregate only | no per-game feedback | |
| Per-game everywhere | every card has state | |

| Status source | Description | Selected |
|---------------|-------------|----------|
| Extend eval-coverage endpoint | one polled call drives all three | ✓ |
| Separate status endpoint | two polls | |

| Guests | Description | Selected |
|--------|-------------|----------|
| Swap CTA for sign-up prompt | "Sign up to unlock full-game analysis" | ✓ |
| Disabled buttons + tooltip | reads as broken | |

**Notes:** User confirmed bulk=tier-2 / single=tier-1 mapping again here. One polled
`/imports/eval-coverage` call is the single source of truth for coverage %, bulk-button
disabled-state, and in-flight counts.

## Claude's Discretion

- Constant values (window 200, threshold ~80%), poll cadence, user-facing tier-1 endpoint
  shape, the "user has tier-2 in-flight" SQL + index, bulk-label numbers, new upsell
  component vs inline.

## Deferred Ideas

- Engine-best-move step-through display (ROADMAP-118 doesn't list it; D-117-01 ambiguity).
- Separate PV/best_move coverage indicator (SEED-039 surface).
- Filter-scoped analysis batch; Endgames/Openings coverage redo; per-card spinners.
