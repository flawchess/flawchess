---
phase: 134-trapped-piece-fixture-expansion-option-b-cook-predicate-reim
verified: 2026-06-23T18:00:00Z
status: passed
score: 6/6
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "Every committed fixture row that does NOT carry the trappedPiece theme is byte-identical between the old and new train+test CSVs (the only diff is added trappedPiece rows)"
    reason: "The committed fixtures were generated from an older lichess dump; the fresh 2026-06 dump shares zero row-level identity even under the identical sampling scheme (0/11,828 non-trapped rows survive a default re-run). Byte-identity is unattainable for any re-sample against a different dump. The per-motif Option-B mechanism was proven correct via same-dump isolation (0-line non-trapped diff between a default and a trapped-piece:250 run on the same dump). User approved full regen + re-measure approach per Rule 4 architectural checkpoint documented in 134-01-SUMMARY.md."
    accepted_by: "aimfeld"
    accepted_at: "2026-06-23T10:00:00Z"
---

# Phase 134: trapped-piece Fixture Expansion + Cook Predicate Reimplementation — Verification Report

**Phase Goal:** Close the trapped-piece gap that Phase 133 formally deferred. Make trapped-piece good enough to unsuppress via: (1) per-motif oversample cap (Option B) growing the fixture to ~1000 rows; (2) reimplement detect_trapped_piece from cook's capture-chain-anchored is_trapped predicate (no AGPL source copied); (3) conditional unsuppress gated on ~>=0.80 TRAIN holding on TEST.
**Verified:** 2026-06-23
**Status:** PASSED (with 1 documented override for the D-EXP-02 byte-identity gate)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | trapped-piece is genuinely shipped: absent from SUPPRESSED_MOTIFS and present in PRECISION_FLOOR at 0.92 | VERIFIED | `precision_floors.py` L200-223 confirms "trapped-piece is NO LONGER suppressed" comment in SUPPRESSED_MOTIFS block; PRECISION_FLOOR["trapped-piece"] = 0.92 at L326 with measurement comment |
| 2 | Precision gate test asserts the floor and passes | VERIFIED | `uv run pytest tests/scripts/tagger/test_detector_precision.py -x -q` ran and output "1 passed in 8.51s"; trapped-piece floor-gated at 0.92, measured TRAIN 1.000 clears it |
| 3 | detect_trapped_piece is capture-chain-anchored (no unconditional full-board `for sq in chess.SQUARES` firing driver); reuses _is_in_bad_spot; stays Tier 2 rank 6; nesting depth <=3 | VERIFIED | grep over detect_trapped_piece function body confirms no `for sq in chess.SQUARES`; `_piece_is_trapped` extracted helper calls `_is_in_bad_spot` (L898, L922); `_GEOMETRIC_REGISTRY` L2314 shows trapped-piece at rank 6; max nesting depth in `_piece_is_trapped` = 3 (function → for loop → if → nested if) |
| 4 | Expanded fixture committed with trapped-piece ~1065 combined; AGPL boundary held | VERIFIED | `grep -c trappedPiece fixtures/tagger/detector_fixture_train.csv` = 748; test CSV = 317; combined 1065. No `from cook`, `import cook`, or `util.is_trapped` symbol found in detector; reimplementation is original code from prose |
| 5 | D-EXP-02 byte-identity isolation gate | PASSED (override) | Override: fresh 2026-06 dump shares zero row-level identity with older-dump fixtures; byte-identity unattainable for any re-sample. Option-B mechanism proven correct via same-dump isolation (0-line non-trapped diff). User approved full-regen approach via Rule 4 checkpoint — documented in 134-01-SUMMARY.md Deviations section |
| 6 | hanging-piece detector geometry was NOT changed (D-EXP-01) — only its floor was lowered as a measurement consequence | VERIFIED | `detect_hanging_piece` function (L454-479) is unchanged: same first-move capture check, same `_is_hanging` call, same depth=0. Three floors lowered (pin 0.90→0.85, intermezzo 0.85→0.70, hanging-piece 0.90→0.68) are all lower-only — confirmed by PRECISION_FLOOR dict at L260, L296, L309 |

**Score:** 6/6 truths verified (1 via accepted override for the byte-identity gate)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/select_tagger_fixtures.py` | --oversample-motifs CLI arg + oversample_map + per-motif RNG re-seed | VERIFIED | `oversample_map` appears 7 times; `_per_motif_seed` at L260 uses SHA-1 for determinism; `--oversample-motifs` parsed at L465-498 |
| `tests/scripts/test_select_tagger_fixtures.py` | Unit test proving cap raises target, isolates control | VERIFIED | File exists; `uv run pytest tests/scripts/test_select_tagger_fixtures.py -x -q` = "2 passed" |
| `fixtures/tagger/detector_fixture_train.csv` | ~748 trappedPiece rows | VERIFIED | 748 trappedPiece rows confirmed; total rows 18,632 (header + data) |
| `fixtures/tagger/detector_fixture_test.csv` | ~317 trappedPiece rows | VERIFIED | 317 trappedPiece rows confirmed; total rows 8,017 (header + data) |
| `app/services/tactic_detector.py` | Reimplemented detect_trapped_piece + _piece_is_trapped helper | VERIFIED | `_piece_is_trapped` at L854; `detect_trapped_piece` at L929; `_escape_squares_all_lose_material` absent (dead code removed per plan) |
| `tests/scripts/tagger/precision_floors.py` | trapped-piece removed from SUPPRESSED_MOTIFS; PRECISION_FLOOR["trapped-piece"]=0.92 added; measurement note refreshed | VERIFIED | L205-208 confirms removal from SUPPRESSED_MOTIFS with historical note; L324-326 shows floor at 0.92; L142-148 has refreshed measurement note |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `select_tagger_fixtures.py::_stratified_sample` | `fixtures/tagger/detector_fixture_train.csv` | oversample_map raises per-stratum cap for trapped-piece | VERIFIED | `cap = oversample_map.get(motif, samples_per_stratum)` at L325; fixture grew 28→748 trapped-piece train rows |
| `fixtures/tagger/detector_fixture_train.csv` | `tests/scripts/tagger/test_detector_precision.py` | harness reads committed fixtures to score TRAIN precision floor | VERIFIED | gate ran and passed; trapped-piece TRAIN precision 1.000 >= floor 0.92 |
| `detect_trapped_piece` | `detect_tactic_motif` | Tier 2 rank 6 dispatch registry | VERIFIED | `_GEOMETRIC_REGISTRY` L2314: ("trapped-piece", TacticMotifInt.TRAPPED_PIECE) at rank 6; `_GEOMETRIC_DETECTOR_FNS` L2324 maps it |
| `PRECISION_FLOOR["trapped-piece"]` | `test_detector_precision.py` | gate asserts TRAIN precision >= floor for all non-suppressed motifs | VERIFIED | test ran: "1 passed in 8.51s"; trapped-piece is floor-gated and meets 0.92 |

---

## Data-Flow Trace (Level 4)

Not applicable — this phase produces no dynamic-data-rendering UI components. All artifacts are: a Python maintenance script, CSV fixtures, a test constants module, and a service function. Data flow is harness-to-fixtures-to-gate, fully verified by the passing precision gate test.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Precision gate passes with trapped-piece floor-gated | `uv run pytest tests/scripts/tagger/test_detector_precision.py -x -q` | 1 passed in 8.51s | PASS |
| Selector unit test: cap raises target, isolates control | `uv run pytest tests/scripts/test_select_tagger_fixtures.py -x -q` | 2 passed in 3.43s | PASS |
| Structural unit fixtures for trapped-piece | `uv run pytest tests/services/test_tactic_detector.py -k trapped -x -q` | 11 passed, 75 deselected in 2.34s | PASS |
| Type check on tactic_detector.py | `uv run ty check app/services/tactic_detector.py` | All checks passed (0 errors) | PASS |

---

## Probe Execution

No probes declared. The phase plan's verification commands were run above as behavioral spot-checks.

---

## Requirements Coverage

No formal REQ-IDs mapped in any plan. Traceability is via ROADMAP Phase 134 locked decisions D-EXP-01/02/03. All three decisions have been verified:

| Decision | Description | Status |
|----------|-------------|--------|
| D-EXP-01 | Do not touch hanging-piece geometry | VERIFIED — detect_hanging_piece unchanged; only floor lowered as measurement consequence |
| D-EXP-02 | Per-motif cap (Option B); byte-identical isolation for non-trapped rows | PASSED (override) — mechanism proven correct; same-dump isolation 0-line; cross-dump identity unattainable; user approved full-regen |
| D-EXP-03 | Unsuppress only if P(train) >=0.80 holding on TEST | VERIFIED — SHIP branch applied; P(train)=1.000, P(test)=1.000, delta=0.000 |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TBD/FIXME/XXX/TODO/PLACEHOLDER/HACK markers found in the files modified by this phase. No empty return stubs, no hardcoded placeholders, no orphaned dead code. The `_escape_squares_all_lose_material` function (previously dead after the rewrite) was removed; confirmed absent by grep.

---

## Human Verification Required

None. All observable truths are mechanically verifiable and verified by automated checks. The D-EXP-02 deviation is documented and carries a user-accepted override. No visual behavior, real-time behavior, or external service integration is involved.

---

## Gaps Summary

No gaps. One planned must-have (D-EXP-02 byte-identity isolation gate) could not be achieved due to a planning-premise failure: the plan assumed the committed fixtures came from a current lichess dump, but they came from an older one. The fresh dump required by the plan's Task 2 shares zero row-level identity with the older-dump fixtures, making byte-identity inherently unattainable. The underlying Option-B isolation mechanism is correct and was proven via same-dump comparison. This deviation was identified during execution, surfaced to the user as a Rule-4 architectural checkpoint, and approved before proceeding. It is documented in 134-01-SUMMARY.md and carries an override in this file's frontmatter.

---

## Success Criteria Assessment

| SC | Statement | Verdict | Evidence |
|----|-----------|---------|----------|
| SC-1 | --oversample-motifs works and is unit-tested; per-motif re-seed makes isolation exact for non-co-occurring motifs | ACHIEVED | 7 occurrences of `oversample_map` in selector; SHA-1 seed at L260; selector unit test 2 passed |
| SC-2 | trapped-piece combined ground-truth count is ~1000 (≈700 train / ≈300 test) in the committed fixtures | ACHIEVED | 748 train + 317 test = 1065 combined |
| SC-3 | Only leakage-moved floors were re-measured (none raised); the harness is green | ACHIEVED (with approved override) | 3 floors lowered (pin/intermezzo/hanging-piece), all lower-only; gate passes; full-regen approach approved by user |
| SC-4 | detect_trapped_piece is capture-chain-anchored and mirrors cook's is_trapped via the existing ports | ACHIEVED | Capture-chain walk confirmed in L961-988; `_is_in_bad_spot` reused at L898/L922; `_piece_value` reused at L902/L917; 5-gate predicate implemented; no source copied |
| SC-5 | Post-dispatch trapped-piece precision is materially above 0.000 and recorded | ACHIEVED | P(train)=1.000, P(test)=1.000, ΔP=0.000 — recorded in 134-02-SUMMARY.md |
| SC-6 | No shipped motif regresses; hanging-piece untouched (D-EXP-01) | ACHIEVED | Full suite 2872 passed; detect_hanging_piece unchanged; hanging-piece floor lowered only as measurement re-calibration |
| SC-7 | The D-EXP-03 decision is applied as exactly one explicit branch (SHIP) | ACHIEVED | SHIP branch applied: trapped-piece removed from SUPPRESSED_MOTIFS, PRECISION_FLOOR 0.92 added |
| SC-8 | No family-map / frontend / family-count-test edits needed (Phase 129 already wired them) | ACHIEVED | FAMILY_TO_MOTIF_INTS["trapped_piece"] confirmed at library_repository.py:137; tacticComparisonMeta.ts:260 confirmed; no edits to either file |

---

_Verified: 2026-06-23T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
