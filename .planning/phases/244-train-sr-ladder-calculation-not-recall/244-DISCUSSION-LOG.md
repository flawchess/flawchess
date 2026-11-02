# Phase 244: Train SR Ladder Rework, Calculation Not Recall (SEED-207) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-02
**Phase:** 244-train-sr-ladder-calculation-not-recall
**Areas discussed:** Migration mechanics (offered but not selected: Copy wording, Post-ship re-check hook)

---

## Migration mechanics

### Round 1

| Question | Options | Selected |
|---|---|---|
| Mechanism | Alembic data migration (rec.) / Manual script with dry-run | Other: "Do we even have to migrate in-flight items?" |
| Snapping of pushed due dates | Snap to weekday mask (rec.) / Raw date | Other: "Not sure we should consider a user's train schedule when setting item due dates. The schedule can change and I don't see an advantage of snapping" |
| Overdue items | Leave as is, max() (rec.) / Recompute from scratch | Leave as is |
| Open-session items | Nothing special (rec.) / Pull from open sessions | Nothing special |

Follow-up analysis: the streak remap (2 -> 1) is a no-op at threshold 2. Prod query showed 363 streak-1 items
(57 active users) that would master on a ~3-day repeat without a migration, 619 streak-2 items inside the new
14d window, 87 failed items inside the 4d window.

### Round 2

| Question | Options | Selected |
|---|---|---|
| How much to migrate | Push all three paths (rec.) / Push streak-1 only / No migration | Push all three paths |
| Snapping in apply_result itself | Drop snapping (rec.) / Keep snapping (SEED-207) | Drop snapping |

**Notes:** Drop snapping overrides the ROADMAP/SEED-207 line that due dates keep snapping via
`next_scheduled_day`.

---

## Claude's Discretion

- Copy wording (Home, README, MASTERED/PARKED strings, other Train copy).
- Post-ship re-check hook (optional STATE.md thread at most).
- UTC vs local date for solve dates in the migration; migration test approach.

## Deferred Ideas

- Post-ship re-check of SEED-207 Tables 2/3; same-motif mastery check; fast-correct recall flag (all already
  out of scope per ROADMAP).
