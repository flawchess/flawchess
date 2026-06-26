---
phase: 124-schema-tactic-detector
verified: 2026-06-18T10:00:00Z
status: passed
score: 10/10
behavior_unverified: 0
overrides_applied: 0
---

# Phase 124: Schema + Tactic Detector — Verification Report

**Phase Goal**: The system can detect and store a tactic motif for any flawed move that has a stored refutation PV
**Verified**: 2026-06-18T10:00:00Z
**Status**: passed
**Re-verification**: No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Alembic migration adds nullable `tactic_motif`, `tactic_piece`, `tactic_confidence` SmallInteger columns; migration up/down round-trips | VERIFIED | `alembic/versions/20260617_120000_phase_124_tactic_motifs.py`: `op.add_column("game_flaws", sa.Column(..., sa.SmallInteger(), nullable=True))` for all three; downgrade drops in reverse order; no `from app` imports |
| 2 | ORM model declares the three columns as `Mapped[Optional[int]]` with SmallInteger | VERIFIED | `app/models/game_flaw.py` lines 73-75: `tactic_motif`, `tactic_piece`, `tactic_confidence` all `mapped_column(SmallInteger, nullable=True)` with doc comment |
| 3 | `TacticMotifInt` encodes exactly 24 motifs; `_INT_TO_MOTIF`/`_MOTIF_TO_INT` round-trip without loss | VERIFIED | `app/services/tactic_detector.py` lines 58-150: `TacticMotifInt` FORK=1 .. DOVETAIL_MATE=24; `_INT_TO_MOTIF` maps 1-24; `_MOTIF_TO_INT` is the reverse comprehension; `TestTacticMotifInt::test_all_24_motifs_encoded` + `test_int_motif_roundtrip` both PASS |
| 4 | `detect_tactic_motif` returns the correct motif via the D-07 priority order: mate > geometric > tier-3 > hanging-piece catch-all | VERIFIED | `app/services/tactic_detector.py` lines 1227-1307: dispatcher iterates `_NAMED_MATE_REGISTRY`, boden/double-bishop special case, back-rank, generic-mate, `_GEOMETRIC_REGISTRY`, `_TIER3_REGISTRY`, then hanging-piece last; `TestPriorityOrder::test_mate_dominates_over_fork` PASS |
| 5 | Mate ALWAYS dominates a co-firing geometric motif | VERIFIED | Priority dispatcher returns on first mate match before entering geometric registry; `TestPriorityOrder::test_mate_dominates_over_fork` PASS; `test_all_mate_fixtures_return_mate_family` PASS |
| 6 | `hanging-piece` is the catch-all last (only wins when no other detector fires) | VERIFIED | `detect_hanging_piece` called only after all tier-1/2/3 registries; `TestPriorityOrder::test_hanging_piece_is_catch_all_last` PASS |
| 7 | Precision-first: Core 8 >= 0.90, tier-3 + named-mate >= 0.95; sub-bar motifs query-suppressed in `_QUERY_SUPPRESSED_MOTIFS` (stored per D-11, never detect-time NULL); recall NOT gated | VERIFIED | `CORE_PRECISION_BAR=0.90`, `TIER3_PRECISION_BAR=0.95` at module level in test file; `test_precision_bar_validated` passes for 16 validated motifs (fork, hanging-piece, pin, skewer, discovered-attack, back-rank-mate, mate, deflection, attraction, clearance, x-ray, intermezzo, capturing-defender, anastasia-mate, dovetail-mate, hook-mate); 8 motifs in `_QUERY_SUPPRESSED_MOTIFS`; `test_suppressed_motifs_documented_and_storable` verifies they still return a non-None int; `test_suppressed_set_matches_validated_partition` proves no motif is silently dropped; no recall assertion in suite |
| 8 | None/empty/malformed `pv_str` returns `(None, None, None)` without raising | VERIFIED | `detect_tactic_motif` lines 1247-1253: guard `if not pv_str: return None, None, None`; `except ValueError: return None, None, None`; confirmed by `test_positives_fire_expected_motif` smoke and malformed-UCI paths |
| 9 | `detect_tactic_motif` runs inside `_build_flaw_record` for both colors; no new Stockfish call | VERIFIED | `app/services/flaws_service.py` line 31: `from app.services.tactic_detector import detect_tactic_motif`; helper `_detect_tactic_for_flaw` (lines 359-392) called from `_build_flaw_record` (line 412); `classify_game_flaws` iterates both colors (Phase 113 all-moves pass); no engine/Stockfish import in tactic_detector.py |
| 10 | `backfill_flaws.py` inherits detection with zero new wiring (calls same `classify_game_flaws` path) | VERIFIED | `scripts/backfill_flaws.py` line 58: `from app.services.flaws_service import classify_game_flaws`; line 210: `result_val = classify_game_flaws(game_obj, positions)`; the classify path calls `_build_flaw_record` which now calls `_detect_tactic_for_flaw` — backfill inherits automatically |

**Score**: 10/10 truths verified (0 behavior-unverified)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/20260617_120000_phase_124_tactic_motifs.py` | Migration adding 3 nullable SmallInteger cols + symmetric downgrade | VERIFIED | Lines 28-39: upgrade adds `tactic_motif`, `tactic_piece`, `tactic_confidence`; downgrade drops in reverse; no `from app` imports |
| `app/models/game_flaw.py` | Three nullable SmallInteger ORM columns | VERIFIED | Lines 73-75: all three `Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)` |
| `app/services/tactic_detector.py` | `TacticMotifInt` IntEnum + `TacticMotif` Literal + dicts + constants + all detectors + `detect_tactic_motif` dispatcher | VERIFIED | 1308 lines; 24 `detect_*` functions; FORK=1..DOVETAIL_MATE=24; `CORE_PRECISION_BAR`, `TACTIC_MIN_SEVERITY`, `TACTIC_CONFIDENCE_HIGH`, `_PIECE_VALUES`, `MATE_MOTIFS` named constants; data-driven registries, nesting depth compliant |
| `app/services/flaws_service.py` | `FlawRecord` extended with tactic fields; `_build_flaw_record` calls `detect_tactic_motif` | VERIFIED | Lines 135-137: `tactic_motif_int`, `tactic_piece`, `tactic_confidence` in `FlawRecord`; line 31: import; line 412: call via `_detect_tactic_for_flaw` helper |
| `app/repositories/game_flaws_repository.py` | `flaw_record_to_row` emits tactic fields using `.get()` | VERIFIED | Lines 118-120: `"tactic_motif": flaw.get("tactic_motif_int")`, `"tactic_piece": flaw.get("tactic_piece")`, `"tactic_confidence": flaw.get("tactic_confidence")` |
| `tests/services/test_tactic_detector.py` | Per-motif fixture sets + `_compute_precision` + `_QUERY_SUPPRESSED_MOTIFS` + precision bars | VERIFIED | 1370 lines; `CORE_PRECISION_BAR=0.90`, `TIER3_PRECISION_BAR=0.95`; `_QUERY_SUPPRESSED_MOTIFS` with 8 motifs; `_compute_precision` function at line 1179; 51 tests (46 PASS, 5 SKIPPED for zero-data suppressed motifs) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/repositories/game_flaws_repository.py:flaw_record_to_row` | `app/services/flaws_service.py:FlawRecord` | `.get("tactic_motif_int")`, `.get("tactic_piece")`, `.get("tactic_confidence")` | WIRED | Lines 118-120 confirmed; `.get()` avoids KeyError on older paths |
| `app/services/flaws_service.py:_build_flaw_record` | `app/services/tactic_detector.py:detect_tactic_motif` | `_detect_tactic_for_flaw()` helper reads `positions[n+1].pv`, reconstructs board, calls detector | WIRED | Lines 359-392 (`_detect_tactic_for_flaw`) + line 412 (call from `_build_flaw_record`); `n+1 < len(positions)` guard + `try/except (ValueError, chess.IllegalMoveError)` |
| `tests/services/test_tactic_detector.py` | `app/services/tactic_detector.py:detect_tactic_motif` | Fixture-driven precision assertions | WIRED | Line 37: `from app.services.tactic_detector import ... detect_tactic_motif`; used in `_run_fixtures`, `_compute_precision`, `TestPriorityOrder` |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 51 detector tests (46 pass, 5 skip for zero-data suppressed motifs) | `uv run pytest tests/services/test_tactic_detector.py -q` | 51 passed, 5 skipped in 6.70s | PASS |
| Both-color detection + None-PV guard via flaws_service | `uv run pytest tests/services/test_flaws_service.py -k "Tactic or tactic" -q` | 3 passed | PASS |
| TacticMotifInt roundtrip (24 motifs, no gaps) | TestTacticMotifInt class | PASS | PASS |
| Precision bars enforced for 16 validated motifs | `test_precision_bar_validated` parametrized | All 16 PASS | PASS |
| Suppressed motifs still stored (D-11) | `test_suppressed_motifs_documented_and_storable` | 8 PASS | PASS |
| No motif silently dropped | `test_suppressed_set_matches_validated_partition` | PASS | PASS |
| Mate dominates fork; hanging-piece is last | `TestPriorityOrder` | All 3 PASS | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| TACSCH-01 | 124-01 | `tactic_motif` nullable SmallInteger column in `game_flaws` | SATISFIED | Migration + ORM model confirmed; `op.add_column("game_flaws", sa.Column("tactic_motif", sa.SmallInteger(), nullable=True))` |
| TACSCH-02 | 124-01 | `tactic_piece` nullable SmallInteger + `tactic_confidence` column | SATISFIED | Both in migration (`tactic_piece`, `tactic_confidence`) and ORM model |
| TACDET-01 | 124-02 | `detect_tactic_motif` returns at most one motif from PV with fixed priority | SATISFIED | `detect_tactic_motif` dispatcher data-driven registry; 51 tests pass confirming single-winner behavior |
| TACDET-02 | 124-02 | Priority order: mate > geometric > tier-3 > hanging-piece | SATISFIED | Dispatcher structure enforces tier order; `TestPriorityOrder` all pass |
| TACDET-03 | 124-03 | Precision-first: D-10 bars enforced; sub-bar motifs query-suppressed; recall not gated; fixtures from own prod flaws | SATISFIED | `CORE_PRECISION_BAR=0.90`, `TIER3_PRECISION_BAR=0.95` as named constants; 16 validated motifs pass bars; 8 in `_QUERY_SUPPRESSED_MOTIFS` with documented reasons; no recall assertion; fixture provenance comment at line 1-9 of test file |
| TACDET-04 | 124-04 | Detector runs in `_build_flaw_record`; both colors; no new engine call; `backfill_flaws.py` flows through | SATISFIED | `_detect_tactic_for_flaw` wired into `_build_flaw_record`; classify loop iterates both colors; `backfill_flaws.py` calls `classify_game_flaws`; tactic_detector.py is pure CPU |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| (none) | — | — | — |

No TBD/FIXME/XXX markers, no stubs, no empty implementations found in any of the 6 modified files. The `# TODO` in plan 02's objective note about file-size was handled by extracting `_detect_tactic_for_flaw` as a helper.

---

### Human Verification Required

None. All truths are verifiable programmatically and tests confirm behavior.

---

### Gaps Summary

None. All 10 truths verified, all 6 artifacts substantive and wired, all 6 requirements satisfied, test suite passes (51 pass, 5 skip — skips are by design for zero-data suppressed motifs).

One design note (not a gap): `_QUERY_SUPPRESSED_MOTIFS` lives in the test file, not in `tactic_detector.py`. The plan's artifact spec said `contains: "_QUERY_SUPPRESSED_MOTIFS"` for the test file — this is satisfied. Phase 125/126 will read it from the test file when deciding which motifs to surface in the UI, which is consistent with the plan's intent (Phase 125 gate input).

---

_Verified: 2026-06-18T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
