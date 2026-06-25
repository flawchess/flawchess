---
phase: 132-tier-3-tactic-precision-hardening-via-cook-py-predicate-alig
plan: "01"
subsystem: tactic-detection
tags: [tactic-tagger, precision-harness, cook-py, goals-dict, baseline]
requires: []
provides: [phase-132-goals-dict, phase-132-baseline-snapshot]
affects: [scripts/tactic_tagger_report.py, reports/tactic-tagger/]
tech_stack:
  added: []
  patterns: [check-goals-harness, post-dispatch-scoring, eval-set-split]
key_files:
  modified:
    - scripts/tactic_tagger_report.py
    - reports/tactic-tagger/tactic-tagger-2026-06-22.md
decisions:
  - "GOALS raised to 0.90 precision for six Tier-3 motifs (deflection, clearance, capturing-defender, attraction, intermezzo, x-ray); recall ungated (None) per D-01"
  - "interference GOALS entry left at 0.80 — it is the regression lock (1.00 TEST), not an optimization target"
  - "sacrifice GOALS entry deferred — added only if it achieves any TP (D-02)"
metrics:
  duration: "~5 minutes"
  completed: "2026-06-23"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
status: complete
---

# Phase 132 Plan 01: Raise GOALS and Record Baseline Summary

Raised the `GOALS` dict in `scripts/tactic_tagger_report.py` to precision 0.90 (recall ungated) for the six in-scope Tier-3 motifs and captured the fresh post-dispatch baseline on both eval splits. Interference confirmed at 1.000 TEST before any detector edits.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Raise GOALS to 0.90 for the six in-scope Tier-3 motifs | e7ada25a | scripts/tactic_tagger_report.py |
| 2 | Record fresh post-dispatch baseline for both eval splits | 2c8fd83e | reports/tactic-tagger/tactic-tagger-2026-06-22.md |

## GOALS Changes

| Motif | Before | After | Recall |
|-------|--------|-------|--------|
| deflection | 0.50 | **0.90** | None (ungated) |
| clearance | 0.70 | **0.90** | None (ungated) |
| capturing-defender | absent | **0.90** | None (ungated) |
| attraction | absent | **0.90** | None (ungated) |
| intermezzo | absent | **0.90** | None (ungated) |
| x-ray | absent | **0.90** | None (ungated) |
| interference | 0.80 | 0.80 (unchanged) | None — regression lock |
| sacrifice | absent | absent (deferred, D-02) | — |

## Phase 132 Post-Dispatch Baseline Snapshot

**Captured:** 2026-06-23, after GOALS update, before any detector rewrites.
**Source:** `PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals --eval-set {train,test}`

### TRAIN split (11,855 rows) — verbatim from check-goals output

```
Goals met: 21/27 dimensions across 19 motifs.
Unmet (6), worst gap first:
  x-ray               precision  0.033 -> need 0.900 (gap +0.867) (TP=1 FP=29 FN=641)
  attraction          precision  0.060 -> need 0.900 (gap +0.840) (TP=26 FP=406 FN=1577)
  intermezzo          precision  0.100 -> need 0.900 (gap +0.800) (TP=2 FP=18 FN=700)
  deflection          precision  0.235 -> need 0.900 (gap +0.665) (TP=304 FP=991 FN=873)
  capturing-defender  precision  0.240 -> need 0.900 (gap +0.660) (TP=6 FP=19 FN=604)
  clearance           precision  0.348 -> need 0.900 (gap +0.552) (TP=65 FP=122 FN=660)
```

### TEST split (5,164 rows) — verbatim from check-goals output

```
Goals met: 20/27 dimensions across 19 motifs.
Unmet (7), worst gap first:
  x-ray               precision  0.000 -> need 0.900 (gap +0.900) (TP=0 FP=18 FN=274)
  attraction          precision  0.043 -> need 0.900 (gap +0.857) (TP=8 FP=176 FN=669)
  intermezzo          precision  0.167 -> need 0.900 (gap +0.733) (TP=2 FP=10 FN=322)
  deflection          precision  0.210 -> need 0.900 (gap +0.690) (TP=119 FP=447 FN=382)
  capturing-defender  precision  0.250 -> need 0.900 (gap +0.650) (TP=4 FP=12 FN=281)
  clearance           precision  0.371 -> need 0.900 (gap +0.529) (TP=46 FP=78 FN=288)
  hanging-piece       precision  0.885 -> need 0.900 (gap +0.015) (TP=216 FP=28 FN=90)
```

### Per-Motif Baseline Table (from tactic-tagger-2026-06-22.md)

| Motif | P(train) | P(test) | TP(train) | FP(train) | n(train) | n(test) | Status |
|-------|----------|---------|-----------|-----------|----------|---------|--------|
| deflection | 0.235 | 0.210 | 304 | 991 | 1177 | 501 | shipped (pre-port) |
| clearance | 0.348 | 0.371 | 65 | 122 | 725 | 334 | shipped (pre-port) |
| capturing-defender | 0.240 | 0.250 | 6 | 19 | 610 | 285 | suppressed |
| attraction | 0.060 | 0.043 | 26 | 406 | 2246 | 677 | suppressed |
| intermezzo | 0.100 | 0.167 | 2 | 18 | 702 | 324 | suppressed |
| x-ray | 0.033 | 0.000 | 1 | 29 | 642 | 274 | suppressed |
| sacrifice | NaN | NaN | 0 | 0 | 3142 | 1377 | suppressed |
| interference | 0.990 | 1.000 | — | — | 596 | 257 | shipped (REGRESSION LOCK) |

### Regression Lock Confirmation

**interference P(test) = 1.000** — regression lock intact before any detector edits. This is the required baseline confirmation before Phase 132 detector rewrites begin.

### Exit Codes

- TRAIN: exit 1 (expected — goals unmet pre-port)
- TEST: exit 1 (expected — goals unmet pre-port)

Both are the correct pre-port state. Each subsequent wave will compare ΔP against these numbers.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

None. Pure CPU script/config edit; no security-relevant surface changes.

## Self-Check

### Created files exist:
- `scripts/tactic_tagger_report.py` — FOUND (modified, not created)
- `reports/tactic-tagger/tactic-tagger-2026-06-22.md` — FOUND

### Commits exist:
- e7ada25a: feat(132-01): raise GOALS to 0.90 for six in-scope Tier-3 motifs — FOUND
- 2c8fd83e: chore(132-01): regenerate tagger report with updated GOALS baseline — FOUND

## Self-Check: PASSED
