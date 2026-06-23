# Phase 131: Tactic precision hardening via cook.py predicate alignment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-22
**Phase:** 131-tactic-precision-hardening-cook-alignment
**Areas discussed:** Broken-motif effort policy, Workstream B comparator, Re-backfill & prod ship

> SEED-064 pre-locked most of this phase (cook-is-the-oracle, per-motif targets, the >0.9-or-suppress
> shipping gate, the shallowest-tactic-wins dispatch, AGPL boundary). The discussion covered only the
> genuinely-open gray areas. The user did not select "Phase split (A vs B)" from the gray-area menu, so
> the seed's recommendation — **one phase** — stands by default (CONTEXT D-01).

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Phase split (A vs B) | One phase vs splitting Workstream B out | |
| Broken-motif effort policy | How to handle skewer/discovered-attack which may not reach 0.9 | ✓ |
| Workstream B comparator | Dest-square match vs dest + captured-piece value | ✓ |
| Re-backfill & prod ship | Dev in-phase + prod deferred vs alternatives | ✓ |

**User's choice:** Discuss the latter three; skip phase split (accept seed default of one phase).

---

## Broken-motif effort policy

| Option | Description | Selected |
|--------|-------------|----------|
| Attempt full port, suppress if <0.9 | Complete cook rebuild for all four geometrics incl. skewer & discovered-attack; suppress any that miss 0.9 on TEST. Highest effort, max recall on trustworthy chips. (Seed's stated approach.) | ✓ |
| Pre-suppress the worst two | Suppress skewer + discovered-attack up front; invest only in fork/pin/back-rank/anastasia/hook. Smaller, lower-risk. | |
| Time-box the port | Attempt skewer & discovered-attack with one faithful port pass; suppress if still <0.9 after that single pass. | |

**User's choice:** Attempt full port, suppress if <0.9.
**Notes:** We want the real precision ceiling measured before suppressing, not a pre-suppression on
assumption. Suppressing skewer alone removes ~16% of all tags (mostly false) — an endorsed trade if
it can't clear the bar. → CONTEXT D-02.

---

## Workstream B comparator

| Option | Description | Selected |
|--------|-------------|----------|
| Destination-square match only | Suppress missed tactic when flaw-move.to == best-line first-move.to. Covers wrong-recapture cleanly; simplest. (Seed's recommendation.) | ✓ |
| Dest-square + captured-piece value | Also require same captured-piece value. Stricter but risks under-suppressing real wrong-recaptures + added complexity. | |
| Dest-square, start strict then relax | Ship dest-square-only, note that planner may add value check if fixtures expose false suppressions. | |

**User's choice:** Destination-square match only.
**Notes:** Validate separately from the puzzle harness via hand-built `(flaw_move, best_line)` unit
fixtures — the bug is invisible to the CC0 fixture. Revisit the value check only if a fixture surfaces
a false suppression. → CONTEXT D-03 / D-04.

---

## Re-backfill & prod ship

| Option | Description | Selected |
|--------|-------------|----------|
| Dev in-phase, prod to runbook | Re-run corrected detector over dev game_flaws in-phase (real-data validation); prod re-backfill is a runbook step outside the phase gate. No dev DB reset. (Phase 127 D-13 precedent.) | ✓ |
| Harness-only, defer all backfill | Gate purely on CC0 harness; skip even dev re-backfill. Leaves known-wrong tags in dev UI. | |
| Include prod ship in scope | Pull prod re-backfill + deploy into the completion gate. Larger blast radius. | |

**User's choice:** Dev in-phase, prod to runbook.
**Notes:** Matches Phase 127 D-13. Offline CC0 harness stays the authoritative precision signal; dev
re-backfill doubles as real-data validation. → CONTEXT D-12.

---

## Claude's Discretion

- Exact suppression mechanism per failing motif (reuse `tactic_confidence` query-suppression lever).
- TRAIN/TEST split mechanics and ΔP reporting format in the harness.
- Whether Workstream B unit fixtures live in `test_tactic_detector.py` or a sibling.
- The precise control-flow shape of the ply-outer/detector-inner dispatch walk.

## Deferred Ideas

- Prod re-backfill execution (runbook, post-ship).
- All Tier-3 tactics (separate later phase).
- Hand-labeled prod-flaw precision set (deferred; CC0 fixture stays ground truth).
- Adding captured-piece-value to the Workstream B comparator (only if fixtures demand it).
- SEED-058 (new motifs), SEED-062 (comparison orientation basis) — separate seeds.
