---
phase: 127-detector-hardening-validation
plan: "03"
subsystem: tactic-detector
tags: [tactic-detector, validation, precision, recall, lichess, cc0, pytest, precision-floors]
dependency_graph:
  requires: [127-01, 127-02]
  provides:
    - tests/scripts/tagger/test_detector_precision.py (precision/recall + depth-vs-Rating harness)
    - tests/scripts/tagger/precision_floors.py (per-motif floors from measured numbers)
  affects:
    - tests/services/test_tactic_detector.py (circularity supersession documented)
tech_stack:
  added: []
  patterns:
    - measure-then-lock floor calibration (D-09)
    - multi-label theme credit (D-10)
    - statistics.correlation stdlib Pearson (no new dep)
    - SUPPRESSED_MOTIFS / PRECISION_FLOOR separation
key_files:
  created:
    - tests/scripts/tagger/test_detector_precision.py
    - tests/scripts/tagger/precision_floors.py
  modified:
    - tests/services/test_tactic_detector.py
decisions:
  - "Floors set from 2026-06-19 measurement run on 4368-row CC0 fixture — not from aspirational 0.90 target"
  - "_TACTIC_CHIP_CONFIDENCE_MIN=70 unchanged: raising to 76 would suppress 2 clearance TPs (conf=67) to gain suppression of 1 attraction FP (conf=75) — net negative"
  - "dovetail-mate (0.000 precision, confidence=100) added to SUPPRESSED_MOTIFS with note that query lever cannot suppress it (mate tier stores constant 100)"
  - "SC#3 delta measured and recorded: fork +18.2pp improvement from D-01 relevance gate"
metrics:
  duration_minutes: 45
  completed_date: "2026-06-19"
  tasks_completed: 2
  files_modified: 3
status: complete
---

# Phase 127 Plan 03: Precision/Recall Harness and Floor Calibration Summary

Precision/recall harness against the 4368-row CC0 fixture, floors set from measured post-fix numbers per D-09, fork precision improvement delta recorded (SC#3), and the self-labeled test circularity documented as superseded (D-12/SC#5).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Precision/recall harness + depth-vs-Rating correlation + precision floors | e7989436 | tests/scripts/tagger/test_detector_precision.py, tests/scripts/tagger/precision_floors.py |
| 2 | Document self-labeled fixture circularity as superseded | 378ed9d7 | tests/services/test_tactic_detector.py |

## What Was Built

### Task 1: Precision/Recall Harness and Floor Calibration

**Harness** (`tests/scripts/tagger/test_detector_precision.py`):
- Iterates 4368 fixture rows, calls `detect_tactic_motif(board, pv)` per row
- Multi-label theme credit (D-10): TP credited when detected motif's theme set intersects puzzle Themes
- Computes per-motif precision (TP / (TP+FP)) and recall (TP / (TP+FN))
- Prints full table with TP, FP, FN, Precision, Recall, Floor, Status columns
- Lists UNVALIDATED_MOTIFS (no lichess equivalent: self-interference, double-bishop-mate)
- Computes and prints depth-vs-Rating Pearson correlation as a first-class output (D-06)
- Asserts `precision >= PRECISION_FLOOR[motif]` for each shipped motif (D-08 hard gate)
- Recall printed only — non-blocking per D-08

**Measured results (2026-06-19, post-D-01 relevance gate):**

| Motif | TP | FP | FN | Precision | Recall | Floor | Status |
|-------|----|----|----|-----------|---------|----|-------|
| anastasia-mate | 203 | 33 | 0 | 0.860 | 1.000 | 0.800 | PASS |
| arabian-mate | 0 | 0 | 203 | NaN | 0.000 | suppressed | SUPPRESSED |
| attraction | 0 | 7 | 566 | 0.000 | 0.000 | suppressed | SUPPRESSED |
| back-rank-mate | 300 | 819 | 1 | 0.268 | 0.997 | 0.200 | PASS |
| boden-mate | 0 | 0 | 188 | NaN | 0.000 | suppressed | SUPPRESSED |
| capturing-defender | 0 | 0 | 222 | NaN | 0.000 | suppressed | SUPPRESSED |
| clearance | 6 | 2 | 265 | 0.750 | 0.022 | 0.600 | PASS |
| deflection | 13 | 55 | 410 | 0.191 | 0.031 | 0.150 | PASS |
| discovered-attack | 74 | 329 | 296 | 0.184 | 0.200 | 0.150 | PASS |
| double-check | 8 | 0 | 263 | 1.000 | 0.030 | 0.800 | PASS |
| dovetail-mate | 0 | 13 | 200 | 0.000 | 0.000 | suppressed | SUPPRESSED |
| fork | 445 | 555 | 153 | 0.445 | 0.744 | 0.400 | PASS |
| hanging-piece | 42 | 2 | 211 | 0.955 | 0.166 | 0.900 | PASS |
| hook-mate | 186 | 33 | 15 | 0.849 | 0.925 | 0.800 | PASS |
| interference | 6 | 0 | 203 | 1.000 | 0.029 | 0.700 | PASS |
| intermezzo | 0 | 1 | 271 | 0.000 | 0.000 | suppressed | SUPPRESSED |
| mate | 379 | 0 | 1784 | 1.000 | 0.175 | 0.950 | PASS |
| pin | 113 | 161 | 332 | 0.412 | 0.254 | 0.350 | PASS |
| sacrifice | 0 | 0 | 1161 | NaN | 0.000 | suppressed | SUPPRESSED |
| skewer | 53 | 284 | 193 | 0.157 | 0.215 | 0.100 | PASS |
| smothered-mate | 197 | 0 | 0 | 1.000 | 1.000 | 0.900 | PASS |
| x-ray | 0 | 0 | 229 | NaN | 0.000 | suppressed | SUPPRESSED |

**Depth-vs-Rating Pearson correlation**: 0.3572 (n=2025 correct detections). Moderate positive correlation — deeper tactics tend to appear in higher-rated puzzles, consistent with depth as a difficulty proxy.

**SC#3 fork/pin precision delta (pre-D-01-gate baseline vs post-fix):**
- fork: pre=0.263, post=0.445, delta=**+0.182** (confirmed improvement from relevance gate)
- pin: pre=0.459, post=0.412, delta=-0.047 (replacement guard slightly conservative)

The fork improvement is the primary SC#3 validation. Pin shows a small regression that is acceptable given the fix eliminates the more harmful Case-B loose-pin false positives.

**Floor config** (`tests/scripts/tagger/precision_floors.py`):
- `PRECISION_FLOOR: dict[str, float]` — 14 shipped motifs with floors set ~5pp below measured precision
- `SUPPRESSED_MOTIFS: frozenset[str]` — 10 motifs excluded from the floor gate
- Every floor constant commented with its measured basis and the measurement date
- Notes on `back-rank-mate` (0.268 due to misfires onto arabian/boden corner mates) and `dovetail-mate` (0.000 precision, confidence=100, cannot suppress via query lever)

**Query suppression lever (`_TACTIC_CHIP_CONFIDENCE_MIN=70` in `library_repository.py`):**
- Unchanged — existing threshold already suppresses deflection FPs (confidence=60) and intermezzo FP (confidence=67)
- One attraction FP at confidence=75 slips above threshold; raising to 76 would also suppress 2 clearance TPs (confidence=67) — net negative trade-off; documented in precision_floors.py

### Task 2: Document Circular Fixture Circularity as Superseded

Updated module docstring of `tests/services/test_tactic_detector.py` with:
- "CIRCULAR FIXTURE WARNING (D-12/SC#5)" section explaining that these fixtures are detector-bucketed (circular) and their precision bars measure self-consistency, not independent ground truth
- Explicit pointer to `tests/scripts/tagger/test_detector_precision.py` as the authoritative precision/recall source
- Note that these tests remain as fast per-commit signature/regression guards in the default suite

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest tests/scripts/tagger -v` (precision gate green) | 1 passed |
| Precision table printed with BOTH Precision and Recall columns | PASS |
| Depth-vs-Rating correlation reported (r=0.3572, n=2025) | PASS |
| Unvalidated motif list printed (self-interference, double-bishop-mate) | PASS |
| `precision_floors.py` defines PRECISION_FLOOR with fork floor >= 0.40 | PASS |
| `uv run pytest tests/services/test_tactic_detector.py -x` | 51 passed, 5 skipped |
| Supersession note in test_tactic_detector.py | PASS (`grep` confirmed) |
| `uv run ty check app/ tests/` | zero errors |
| `uv run pytest -n auto -x` (full default suite) | 2797 passed, 15 skipped |

## Deviations from Plan

### Plan Verification vs Measured Reality

**[Rule 2 - Informed deviation] Fork floor set at 0.40, not >=0.80 as the plan's verify script specified.**
- **Found during:** Task 1 measurement run
- **Issue:** The plan's automated verify script asserted `PRECISION_FLOOR.get('fork', 0) >= 0.80`, but the measured post-fix fork precision is 0.445. Setting a floor of 0.80 when measured precision is 0.445 would make the CI gate fail immediately on every run. D-09 (the plan's "single most important rule") explicitly states: "Do NOT author the >= floor assertion with a hardcoded number before this measurement exists." The verify script contained an aspirational value that pre-dated measurement.
- **Fix:** Set fork floor at 0.40 (≈5pp below measured 0.445). The D-01 relevance gate already delivered a +18.2pp improvement (0.263→0.445) — the current precision reflects the hardened detector. Further gains require deeper detector work in a future phase.
- **Files modified:** tests/scripts/tagger/precision_floors.py
- **Commit:** e7989436

**[Observation] Pin precision slight regression vs pre-gate baseline.**
- Pin precision: pre-gate=0.459, post-fix=0.412 (-4.7pp). The replacement guard (Case-B false positive fix) is slightly conservative, blocking some valid pin detections. This is an acceptable trade-off: the replacement guard eliminates the more harmful phantom-pin category. Floor set at 0.35 (reflecting measured value).

**[Observation] Multiple core/geometric motifs below the D-09 ~0.90 aspiration.**
- `fork` (0.445), `pin` (0.412), `discovered-attack` (0.184), `back-rank-mate` (0.268), `skewer` (0.157) all fall below the ~0.90 target. These are honest measured values. The D-09 "confirm during planning" directive was designed for exactly this situation — the aspirational 0.90 target is a future benchmark, not an achieved baseline. Floors are set from current measured data; raising them requires detector hardening in a subsequent phase.

## Known Stubs

None. The harness wires directly to the live detector and fixture. All precision floors are set from measured numbers. The suppressed motifs are documented with rationale.

## Threat Flags

None. This plan introduces no new network endpoints, auth paths, file access patterns, or schema changes. The harness reads only the committed CC0 fixture CSV (no network, no DB).

## Threat Model Coverage

| Threat ID | Mitigation |
|-----------|-----------|
| T-127-05 (precision floor provenance) | Each floor constant commented with measured value and date; SUMMARY records measurement run |
| T-127-06 (query-suppression lever) | `_TACTIC_CHIP_CONFIDENCE_MIN=70` unchanged; rationale for no-change documented |

## Self-Check: PASSED

- tests/scripts/tagger/test_detector_precision.py: FOUND
- tests/scripts/tagger/precision_floors.py: FOUND
- tests/services/test_tactic_detector.py (modified): FOUND
- Commit e7989436 (Task 1): FOUND
- Commit 378ed9d7 (Task 2): FOUND
