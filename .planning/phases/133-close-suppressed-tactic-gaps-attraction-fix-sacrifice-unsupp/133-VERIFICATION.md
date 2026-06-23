---
phase: 133-close-suppressed-tactic-gaps-attraction-fix-sacrifice-unsupp
verified: 2026-06-23T07:45:00Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "trapped-piece oversample trappedPiece theme + re-judge D-06 detector"
    addressed_in: "follow-on quick task"
    evidence: "ROADMAP.md Phase 133 descope note: 'trapped-piece fixture expansion is OUT of scope. Raising SAMPLES_PER_STRATUM reshuffles ALL motifs' fixtures and forces re-measuring every committed precision floor (blast radius). Deferred to a follow-on quick task (per-motif oversample cap, Option B).'"
---

# Phase 133: Close Suppressed-Tactic Gaps Verification Report

**Phase Goal:** Ship the remaining floor-gateable suppressed motifs that 131/132 left behind, so they surface as chips at >=0.90 TEST precision (recall ungated, precision-first). In scope: (1) attraction fix off-by-one; (2) sacrifice unsuppress-only; (3) arabian-mate / boden-mate / dovetail-mate cook geometry ports; (4) correct two stale docstrings. [Trapped-piece formally descoped per ROADMAP and RESEARCH.md.]
**Verified:** 2026-06-23T07:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Trapped-Piece Descope Note

The phase goal text included "(4) trapped-piece — oversample trappedPiece theme + re-judge D-06 detector". The ROADMAP.md Phase 133 block contains an explicit descope notice — "trapped-piece fixture expansion is OUT of scope" — with justification: raising `SAMPLES_PER_STRATUM` reshuffles all motifs' fixtures, forcing re-measurement of every committed precision floor (blast-radius risk). RESEARCH.md Section "Trapped-Piece" and the investigation note independently confirm this decision. The executed plans (133-01 and 133-02) each explicitly direct leaving `trapped-piece` in `SUPPRESSED_MOTIFS`. This item is recorded as deferred (not as a gap) because the ROADMAP owner explicitly removed it from scope before execution started.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | attraction detector fixed: boards[k+3] attacker check replaces boards[k+2] off-by-one | VERIFIED | `tactic_detector.py` L1610: `board_k3 = boards[k + 3]`; precision harness TRAIN: 654 TP / 0 FP / precision 1.000 PASS |
| 2 | arabian-mate detector fires on its TRAIN fixture rows with ~553 TP / 0 FP | VERIFIED | `detect_arabian_mate` uses `boards[-1].attackers(pov, rook_sq)` + `(r_diff==2, f_diff==2)` check; harness TRAIN 553 TP / 0 FP / precision 1.000 PASS |
| 3 | boden-mate detector fires on its TRAIN fixture rows with ~435 TP / 0 FP | VERIFIED | `detect_boden_or_double_bishop_mate` iterates `chess.SQUARES` with `square_distance < 2`, rejects any non-bishop attacker; harness TRAIN 435 TP / 0 FP / precision 1.000 PASS |
| 4 | dovetail-mate detector fires only on true positives (~543 TP, 0 FP); 23 prior FPs are gone | VERIFIED | `detect_dovetail_mate` has same-file/rank reject, distance>1 reject, escape-square loop; harness TRAIN 543 TP / 0 FP / precision 1.000 PASS |
| 5 | attraction, sacrifice, arabian-mate, boden-mate, dovetail-mate not in SUPPRESSED_MOTIFS; each clears PRECISION_FLOOR 0.93 on TRAIN | VERIFIED | `precision_floors.py` SUPPRESSED_MOTIFS contains only {self-interference, double-bishop-mate, trapped-piece, en-passant, under-promotion}; PRECISION_FLOOR has all five at 0.93; harness exits 0, all five show PASS |
| 6 | FAMILY_TO_MOTIF_INTS has 17 family keys including new "attraction" and "sacrifice" families | VERIFIED | `library_repository.py` L177-182: `"attraction": [10]`, `"sacrifice": [17]`; `test_family_mapping_ten_families` (asserts 17 keys) PASSES; count confirmed programmatically |
| 7 | attraction + sacrifice surface as "advanced"-group filter chips in the frontend; tsc -b and frontend tests green | VERIFIED | `tacticComparisonMeta.ts` has `TacticFamily` union with `'attraction'` + `'sacrifice'`; TACTIC_COMPARISON_FAMILIES has advanced-group entries for both; `theme.ts` exports `TAC_ATTRACTION`, `TAC_ATTRACTION_BG`, `TAC_SACRIFICE`, `TAC_SACRIFICE_BG`; `./node_modules/.bin/tsc -b` exits 0; `npm test -- --run` exits 0 (1093 tests passed) |
| 8 | two stale docstrings in precision_floors.py corrected: attraction no longer claims "PV depth", sacrifice no longer claims "never wins single-winner dispatch" | VERIFIED | L87-91 describes actual off-by-one root cause (boards[k+2]->boards[k+3]); L97-103 describes actual dispatch-shadowing cause; neither stale phrase appears in the file |

**Score:** 8/8 truths verified

### Deferred Items

Items not yet met but explicitly removed from scope before execution with documented rationale.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | trapped-piece oversample trappedPiece theme + re-judge D-06 detector | follow-on quick task | ROADMAP.md Phase 133 descope: "trapped-piece fixture expansion is OUT of scope... Deferred to a follow-on quick task (per-motif oversample cap, Option B)." RESEARCH.md and investigation note confirm the blast-radius justification. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/tactic_detector.py` | Fixed `_attraction_fires_at` (boards[k+3]) + cook geometry for arabian/boden/dovetail | VERIFIED | boards[k+3] at L1610; arabian-mate attacker-of-rook-sq at L1297-1303; boden-mate near-king loop at L1341-1346; dovetail same-file/rank reject + escape loop at L1396-1433 |
| `tests/scripts/tagger/precision_floors.py` | Five motifs removed from SUPPRESSED_MOTIFS; PRECISION_FLOOR entries added at 0.93; stale docstrings corrected | VERIFIED | SUPPRESSED_MOTIFS has 5 entries (none of the five); PRECISION_FLOOR L304-308 has all five at 0.93; Phase 133 measurement block L112-135 present; stale phrases absent |
| `app/repositories/library_repository.py` | FAMILY_TO_MOTIF_INTS attraction + sacrifice family keys | VERIFIED | L177-182 present; 17 total keys confirmed |
| `frontend/src/lib/theme.ts` | TAC_ATTRACTION / TAC_SACRIFICE color tokens | VERIFIED | L125-128: TAC_ATTRACTION, TAC_ATTRACTION_BG, TAC_SACRIFICE, TAC_SACRIFICE_BG all defined |
| `frontend/src/lib/tacticComparisonMeta.ts` | attraction + sacrifice in TacticFamily union, color/icon records, TACTIC_COMPARISON_FAMILIES advanced group | VERIFIED | TacticFamily union at L124-125; TACTIC_FAMILY_COLORS at L151-152; TACTIC_FAMILY_ICON at L172-173; TACTIC_COMPARISON_FAMILIES advanced entries at L363-379 |
| `reports/tactic-tagger/tactic-tagger-2026-06-23.md` | Regenerated report showing five motifs with measured (non-NaN) precision | VERIFIED | File exists; all five show "shipped" with P(train)=1.000, P(test)=1.000 |
| `tests/services/test_tactic_comparison_service.py` | family-count test asserts 17; suppressed-tier3 test asserts {14} only | VERIFIED | test_family_mapping_ten_families asserts 17 keys; test_family_mapping_excludes_suppressed_tier3 asserts {14}; all 5 family mapping tests PASS |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `precision_floors.py::PRECISION_FLOOR` | `test_detector_precision.py` | harness asserts TRAIN precision >= floor for five motifs | VERIFIED | Harness exits 0; all five show PASS at floor 0.93 |
| `library_repository.py::FAMILY_TO_MOTIF_INTS` | `tacticComparisonMeta.ts::TACTIC_COMPARISON_FAMILIES` | cross-stack family contract (string-for-string) | VERIFIED | Backend "attraction" -> [10], "sacrifice" -> [17]; frontend 'attraction' and 'sacrifice' in TacticFamily union and TACTIC_COMPARISON_FAMILIES |

### Data-Flow Trace (Level 4)

The modified artifacts are backend detector logic (Python), precision floors (test configuration), and frontend metadata/theme constants. None render dynamic data from a DB — the detector logic produces tactic motif ints that flow through the existing dispatch pipeline (unchanged); the frontend metadata drives filter chip rendering via TACTIC_COMPARISON_FAMILIES (data-driven, not rendering a DB query directly). Level 4 data-flow trace is not applicable for these artifact types; the wiring is verified via the precision harness and family mapping tests.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Precision harness: all five motifs gate PASS at floor 0.93 | `uv run pytest tests/scripts/tagger/test_detector_precision.py -s` | 1 passed in 6.98s; attraction/arabian/boden/dovetail/sacrifice all show PASS | PASS |
| Family mapping tests: 17-family count, corrected suppressed-tier3 set | `uv run pytest tests/services/test_tactic_comparison_service.py -k test_family_mapping -v` | 5 passed; all family mapping tests green | PASS |
| Full backend suite | `uv run pytest -n auto -x` | 2862 passed, 18 skipped, 3 warnings in 28.60s | PASS |
| Frontend type check | `./node_modules/.bin/tsc -b` (from frontend/) | Exits 0, no errors | PASS |
| Frontend tests | `npm test -- --run` | 91 test files, 1093 tests passed | PASS |
| ty check | `uv run ty check app/ tests/` | All checks passed | PASS |
| ruff check | `uv run ruff check app/ tests/` | All checks passed | PASS |

### Probe Execution

No declared probes in PLAN.md or SUMMARY.md. The CC0 fixture harness (`test_detector_precision.py`) serves as the functional gate; it was run and passed (see Behavioral Spot-Checks).

### Requirements Coverage

No requirement IDs are mapped to Phase 133 (plans declare `requirements: []`). Traceability is via CONTEXT.md decisions and the investigation note (as documented in both plans). REQUIREMENTS.md cross-reference: `TACDET-EXT-01` covers the broader deferred tier-3 and named-mate scope; the Phase 133 work implements the gateable subset of that item. No orphaned requirements identified.

### Anti-Patterns Found

No TBD, FIXME, or XXX markers found in the modified files. No stub patterns (empty returns, placeholder JSX, disconnected props) identified. The fixture reclassification cascade in `test_tactic_detector.py` (37 dispatcher fixtures reclassified from fork/pin/skewer/etc. to 'attraction' due to depth-primary dispatch semantics) is correct behavior per the Phase 131/132 precedent — it reflects real dispatch priority, not a stub.

Notable deviation (documented in SUMMARY, non-blocking): dovetail-mate was moved to `_SUPPRESSED_FIXTURE_SETS` and `_QUERY_SUPPRESSED_MOTIFS` at the fixture-dispatch level. The cook port's strict `queen-diagonally-adjacent-to-king` constraint means the 13 existing TRAIN test fixtures dispatch as generic 'mate'. The CC0 precision harness still shows dovetail-mate at 1.000 TRAIN / 1.000 TEST (543/230 TP respectively), confirming the detector is correct; the fixture reclassification is a test-bookkeeping update. The motif is unsuppressed in `precision_floors.py` and has a PRECISION_FLOOR at 0.93.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none found) | — | — | — | — |

### Human Verification Required

No human verification items. The manual-only items from VALIDATION.md are addressed:

1. Stale docstring corrections: verified programmatically — neither "Lure+4-move sequence rarely survives Stockfish PV depth limit" nor "material-diff predicate never wins single-winner dispatch" appears in `precision_floors.py`. The corrected text is present in the Phase 133 measurement block (lines 87-103).

2. Tactic-tagger report regeneration: `reports/tactic-tagger/tactic-tagger-2026-06-23.md` exists and shows all five motifs with `shipped` status at P(train)=1.000, P(test)=1.000.

3. Frontend chip surfacing: verified via tsc -b (0 errors) and 1093 frontend tests passing. The `TacticFamily` union exhaustiveness check in `Record<TacticFamily, ...>` guards runtime undefined color/icon. Visual chip appearance in the app UI is a production-only concern (no server running locally); however, the data-driven rendering path (TACTIC_COMPARISON_FAMILIES -> filter panel) is fully wired and type-safe.

### Gaps Summary

No gaps. All 8 must-have truths are verified. The trapped-piece scope item is formally deferred (not a gap) per an explicit ROADMAP descope decision made before execution.

---

_Verified: 2026-06-23T07:45:00Z_
_Verifier: Claude (gsd-verifier)_
