---
phase: 132-tier-3-tactic-precision-hardening-via-cook-py-predicate-alig
plan: "05"
subsystem: tactic-detection
tags: [tactic-tagger, dev-backfill, final-gate, cook-py, precision-hardening, d04-backfill, d05-gate]
requires: [phase-132-04-floors, phase-132-03-floors, phase-132-02-floors]
provides: [phase-132-final-gate, dev-backfill-validation]
affects:
  - reports/tactic-tagger/tactic-tagger-2026-06-23.md
tech_stack:
  added: []
  patterns: [dev-rebackfill, test-split-gate, before-after-spot-check]
key_files:
  modified:
    - reports/tactic-tagger/tactic-tagger-2026-06-23.md
decisions:
  - "Dev re-backfill (D-04) validated: 26,195/73,318 flaw rows changed via the _detect_tactic_for_flaw kernel. Behavior matches cook-aligned detector changes (deflection -96%, clearance -64%, attraction 0 after suppression, x-ray strict 3-square guard). Parity confirmed: no discrepancies found."
  - "Final TEST gate confirmed: all 7 Phase 132 in-scope motifs are honestly shipped (deflection 1.000, clearance 0.954, capturing-defender 0.903, intermezzo 1.000, x-ray 1.000) or suppressed (attraction NaN D-03, sacrifice 1.000-when-wins D-02). Interference lock holds at 0.992 TEST (≥0.99 target)."
  - "precision_floors.py already fully reconciled in plans 02-04; no changes needed in plan 05. CI harness test_detector_precision_and_recall passes green (1/1)."
  - "Pre-existing ty errors in scripts/seed_cohort_cdf.py and scripts/seed_openings.py (Phase 99.1/92) are out-of-scope and pre-date Phase 132 by dozens of phases. Logged as deferred; app/ and tests/ are clean."
metrics:
  duration: "~9 minutes"
  completed: "2026-06-23"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
status: complete
---

# Phase 132 Plan 05: Dev Re-Backfill + Final TEST-Gate Validation Summary

Dev re-backfill ran 26,195 changes across 73,318 flaws via the live-drain kernel.
Final TEST gate confirms all Phase 132 in-scope motifs shipped or suppressed with interference lock at 0.992.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| Checkpoint | Confirm dev DB up + BEFORE counts | (auto-approved, no commit) | dev DB: 73,318 flaws / 29,752 tagged |
| 1 | Dev re-backfill and before/after spot-check | 43f3cda3 | reports/tactic-tagger/tactic-tagger-2026-06-23.md |
| 2 | Final TEST-split precision gate + reconcile precision_floors.py | 43f3cda3 | (precision_floors.py already correct) |

## Dev Re-Backfill Results (D-04)

**Scope:** Existing dev DB (73,318 total flaws, 29,752 tagged before backfill). No reset. No prod backfill.

**Dry-run:** 26,195/73,318 rows would change (35.7%). Confirmed before writing.

**Full run:** 26,195 rows changed via `_detect_tactic_for_flaw` kernel (parity with live drain guaranteed).

### Before vs After Per-Motif `game_flaws` Tag Counts

| Motif | Before | After | Delta | Notes |
|-------|--------|-------|-------|-------|
| clearance | 6,184 | 2,208 | -3,976 | Cook 9-condition AND-chain much tighter than voting |
| deflection | 5,119 | 205 | -4,914 | Cook 11-condition AND-chain eliminated ~96% of old FPs |
| hanging-piece | 4,372 | 4,372 | 0 | Unchanged (not in Phase 132 scope) |
| attraction | 2,574 | 0 | -2,574 | Suppressed (D-03 cutoff; cook §4 0 TP on TRAIN) |
| mate | 2,433 | 2,433 | 0 | Unchanged |
| fork | 2,332 | 2,605 | +273 | Absorbs rows freed from attraction/deflection in dispatch |
| pin | 1,959 | 2,333 | +374 | Absorbs rows freed from Tier-3 motifs |
| intermezzo | 952 | 268 | -684 | Cook zwischenzug AND-chain much tighter |
| capturing-defender | 850 | 323 | -527 | Cook init-board defender test tighter |
| x-ray | 808 | 15 | -793 | Three-same-square guard; only real x-rays survive |
| discovered-attack | 684 | 861 | +177 | Absorbs some freed rows |
| trapped-piece | 542 | 662 | +120 | Minor shift from freed dispatch slots |
| skewer | 333 | 431 | +98 | Absorbs freed rows |
| sacrifice | 0 | 1,225 | +1,225 | Cook §7 now fires (suppressed at query time via confidence=70) |
| discovered-check | 141 | 141 | 0 | Unchanged |
| back-rank-mate | 133 | 133 | 0 | Unchanged |
| interference | 66 | 105 | +39 | Minor shift (some Tier-3 rows released to interference) |
| promotion | 79 | 89 | +10 | Minor shift |
| double-check | 43 | 61 | +18 | Minor shift |
| dovetail-mate | 58 | 58 | 0 | Unchanged |
| en-passant | 40 | 40 | 0 | Unchanged |
| hook-mate | 25 | 25 | 0 | Unchanged |
| smothered-mate | 20 | 20 | 0 | Unchanged |
| under-promotion | 3 | 4 | +1 | Unchanged |
| anastasia-mate | 2 | 2 | 0 | Unchanged |

**Total tagged flaws:** 29,752 → 18,619 (-11,133). The reduction reflects suppressed motifs (attraction=2,574 gone; deflection massively cut). This is expected: the cook-aligned detectors are precision-first and suppress FPs via SUPPRESSED_MOTIFS at query time.

**Cardinality check:** Total flaw rows unchanged at 73,318. The backfill changes WHICH motif wins per flaw (or sets to NULL for formerly-tagged rows where no cook-aligned motif fires), not the flaw row count itself.

## Final TEST-Split Precision Gate (D-05)

**Command:** `PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals --eval-set test`

### Phase 132 In-Scope Motif Status Table

| Motif | P(train) | P(test) | Status | Notes |
|-------|----------|---------|--------|-------|
| deflection | 0.994 | **1.000** | SHIPPED | Cook 11-condition AND-chain; floor 0.93 |
| clearance | 0.917 | **0.954** | SHIPPED | Cook 9-condition AND-chain; floor 0.87 |
| capturing-defender | 0.876 | **0.903** | SHIPPED | Cook init-board defender test; floor 0.82 |
| intermezzo | 0.938 | **1.000** | SHIPPED | Cook zwischenzug AND-chain; floor 0.85 |
| x-ray | 1.000 | **1.000** | SHIPPED | Cook three-same-square guard; floor 0.93 |
| attraction | NaN | **NaN** | SUPPRESSED | D-03 cutoff: 0 TP on TRAIN after full cook §4 port |
| sacrifice | 1.000 | **1.000** | SUPPRESSED | D-02: co-tag/dispatch-cap (rarely wins dispatch); 1.000 when it wins |
| interference | 0.988 | **0.992** | LOCK HOLDS | ≥0.99 target; detect_interference UNCHANGED |

**In-scope ship/suppress resolution:**
- 5 shipped (deflection, clearance, capturing-defender, intermezzo, x-ray)
- 2 suppressed (attraction, sacrifice)
- 1 lock (interference ≥0.99)

**Interference lock:** P(test)=0.992 — above the 0.99 plan target. HOLDS.

**Overall gate:** 25/26 GOALS dimensions met on TEST. The single unmet goal is `hanging-piece` at 0.885 (needs 0.900), which is a pre-existing issue from before Phase 132 and not in Phase 132 scope. All 7 Phase 132 in-scope motifs are fully resolved.

## CI Gate Results

| Gate | Result |
|------|--------|
| `uv run pytest tests/scripts/tagger/ -v` | 1/1 PASSED |
| `uv run pytest -n auto -q` | 2,863 passed, 17 skipped |
| `uv run ruff check app/ tests/ scripts/` | All checks passed |
| `uv run ty check app/ tests/` | All checks passed |
| `uv run ty check scripts/` | 4 pre-existing errors in seed_cohort_cdf.py/seed_openings.py (Phase 99.1/92, out of scope) |

## Deviations from Plan

None. The plan executed exactly as written:
- Checkpoint auto-approved per auto-mode (dev DB confirmed up and healthy before execution)
- precision_floors.py was already internally consistent from plans 02-04 (no changes needed)
- No parity discrepancies found between the backfill kernel and the fixture-harness behavior
- The 4 ty errors in seed scripts are pre-existing (Phase 99.1/92) and out of scope per CLAUDE.md scope boundary

## Deferred Items

**Pre-existing ty errors in seed scripts:** `scripts/seed_cohort_cdf.py` and `scripts/seed_openings.py` have 4 type errors (`no-matching-overload`, `invalid-context-manager`) in their SQLAlchemy `sessionmaker` usage. These pre-date Phase 132 by many phases (last modified Phase 99.1/92). Logged to deferred-items for a future dedicated chore. Not a Phase 132 issue.

**hanging-piece goal gap:** P(test)=0.885 vs GOALS target 0.900 (gap +0.015). Pre-existing; out of Phase 132 scope. Candidate for a Phase 133 follow-up.

## Known Stubs

None. All detectors are fully wired. Suppressed motifs filtered at query time via `_TACTIC_CHIP_CONFIDENCE_MIN=70`.

## Threat Flags

None. This plan was read-only on code: only the dev DB was written (change-only UPDATEs via the backfill script), and no prod data was touched.

## Self-Check

### Created/modified files exist:
- `reports/tactic-tagger/tactic-tagger-2026-06-23.md` — FOUND (modified)

### Commits exist:
- 43f3cda3: chore(132-05): dev re-backfill + final TEST-gate validation — FOUND

### Test suite: 2863 passed, 17 skipped — PASSED

## Self-Check: PASSED
