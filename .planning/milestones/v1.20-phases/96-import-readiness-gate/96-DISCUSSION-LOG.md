# Phase 96: Import Readiness Gate - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-28
**Phase:** 96-import-readiness-gate
**Areas discussed:** Incremental-import Endgames lock

---

## Area selection

The canonical spec (`.planning/notes/import-readiness-gate.md`) already locked the
tier model, 7 constraints, CTA mechanics, and rejected alternatives. Four still-open
areas were offered:

| Area | Description | Selected |
|------|-------------|----------|
| Tier-2 readiness signal | How the backend authoritatively detects "percentiles persisted" (Constraint 1 race) | |
| Readiness endpoint shape | New `/imports/readiness` vs. extend `/imports/eval-coverage`; poll cadence | |
| Locked-route UX | Redirect vs in-place locked state vs disabled nav, replacing `profileHasCompletedImport()` | |
| Incremental-import Endgames lock | Does Endgames lock for returning users on incremental imports | ✓ |

**User's choice:** Discuss only "Incremental-import Endgames lock". The other three
deferred to research/planning within Constraint 1 + the spec.

---

## Incremental-import Endgames lock

Tension surfaced: the spec's "partial-eval stats are biased" justification is strong
for first imports (small biased subset) but weak for incremental (small pending tail
on a large fully-evaluated corpus).

| Option | Description | Selected |
|--------|-------------|----------|
| Keep showing prior data + badge | Endgames stays usable with existing stats + a "refreshing — analyzing N new games" badge; reactive reveal at Tier 2 | |
| Lock fully (per notes) | Endgames locks into the processing state for the whole drain, identical to first import; uniform rule | ✓ |
| Lock only if drain is material | Threshold-based: keep usable when pending tail is small, lock when batch is large enough to shift stats | |

**User's choice:** Lock fully (per notes).
**Notes:** Chose the simple uniform rule — one gate behavior regardless of import
type, zero risk of surfacing a mid-drain number — over keeping prior data or a
threshold knob. Accepts that returning users are pulled out of correct data.

---

## Lock copy (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct returning-user copy | "Re-analyzing your endgames with N new games — stats will refresh shortly (X/Y)" | |
| Same generic processing state | Reuse the first-import "Analyzing endgames (X/Y)" state regardless of import type | ✓ |

**User's choice:** Same generic processing state.
**Notes:** One component, one message; eval X/Y counter is the only progress signal.
No prior-data acknowledgment.

---

## Claude's Discretion

Deferred to research/planning by explicit user choice (guided by Constraint 1 + the spec):
- Tier-2 readiness signal detection mechanism
- Readiness endpoint shape + poll cadence
- Locked-route UX (redirect / in-place / disabled nav)

## Deferred Ideas

None — discussion stayed within phase scope. Threshold-based incremental locking and
returning-user-specific lock copy were considered and rejected (see D-01/D-02 in CONTEXT.md).
