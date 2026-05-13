---
phase: 84-data-plumbing-per-type-cohort-p50-and-mirror-rate-audit
verified: 2026-05-13T10:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
---

# Phase 84: Data plumbing — mirror-rate audit — Verification Report

**Phase Goal:** Audit that mirror-bucket peer rates (`opponent_score` / `opponent_games`) are already exposed on `/api/endgames/overview` for Section 2 (Conv/Parity/Recov rows, plus `opp_conv` + `opp_recov` consumed by the derived Skill peer baseline) and Section 3 (per-type Conv/Recov). Prerequisite for the peer bullets in Section 2 + 3.

**Verified:** 2026-05-13T10:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

The phase pivoted during planning: Section 2 (MaterialRow) peer rates were already wired by Phase 60, but Section 3 (per-type ConversionRecoveryStats) was NOT — so plan 84-01 shipped the minimal backend extension via the same mirror-identity pattern. The success criterion explicitly permits this ("OR a minimal backend extension is shipped"). Both halves are verified in the codebase: the Section 2 audit is documented with file:line evidence that matches the actual code, and the Section 3 extension is shipped and tested.

### Observable Truths

| #   | Truth | Status     | Evidence       |
| --- | ----- | ---------- | -------------- |
| 1 | ConversionRecoveryStats carries four opponent-baseline fields per endgame class | VERIFIED | `app/schemas/endgames.py:52-59` — `opponent_conversion_pct: float \| None`, `opponent_conversion_games: int`, `opponent_recovery_pct: float \| None`, `opponent_recovery_games: int`, all REQUIRED |
| 2 | opponent_conversion_pct computed via mirror identity `(recovery_games - recovery_wins - recovery_draws) / recovery_games` rounded 1 dp, 0-100 | VERIFIED | `app/services/endgame_service.py:363-368` — `recovery_losses = recovery_games - recovery_wins - recovery_draws; opponent_conversion_pct = round(recovery_losses / recovery_games * 100, 1)`. Test `test_per_type_opponent_baseline_symmetric_60_40` asserts == 60.0 |
| 3 | opponent_recovery_pct computed via mirror identity `(conversion_losses + conversion_draws) / conversion_games` rounded 1 dp, 0-100 | VERIFIED | `app/services/endgame_service.py:371-377` — `opponent_recovery_pct = round((conversion_losses + conversion_draws) / conversion_games * 100, 1)`. Test asserts == 40.0 |
| 4 | opponent_conversion_pct is None when recovery_games < 10; opponent_recovery_pct is None when conversion_games < 10 | VERIFIED | `endgame_service.py:364, 367-368, 372, 376-377` — both gates use `>= _MIN_OPPONENT_SAMPLE` (= 10 at line 234). Test `test_per_type_opponent_baseline_below_threshold` verifies both sides at games=9 → None |
| 5 | opponent_conversion_games == recovery_games (int, possibly 0); opponent_recovery_games == conversion_games | VERIFIED | `endgame_service.py:369, 378` — direct assignments outside gate, always int. Test `test_per_type_opponent_baseline_zero_sample` asserts both equal 0 without ZeroDivisionError |
| 6 | Audit paragraph in SUMMARY.md cites file:line evidence for Section 2 wiring + Opp Skill derivation note | VERIFIED | `84-01-SUMMARY.md:84-105` — cites `MaterialRow.opponent_score` at `endgames.py:252-254`, `_compute_score_gap_material` at `endgame_service.py:851-870`, frontend `EndgameScoreGapSection.tsx:114-145`. Skill derivation note for Phase 86 present at lines 102-105 |
| 7 | All existing endgame_service tests pass; new mirror-identity tests pass; ty and ruff green | VERIFIED | `pytest tests/test_endgame_service.py` 237 passed; full touched-files run 327 passed; `ty check app/ tests/` reports "All checks passed!"; `ruff check` and `ruff format --check` on modified files clean |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app/schemas/endgames.py` | ConversionRecoveryStats with 4 new opponent_* fields appended after recovery_draws | VERIFIED | Fields present at lines 52-59 in exact specified order with `float \| None` / `int` types and per-field docstrings. Class docstring updated with Phase 84 paragraph at lines 31-36 |
| `app/services/endgame_service.py` | _aggregate_endgame_stats wiring populates 4 fields via mirror identities + _MIN_OPPONENT_SAMPLE gating | VERIFIED | Mirror-identity block at lines 358-378; constructor kwargs at lines 391-394; `_MIN_OPPONENT_SAMPLE = 10` at line 234 reused (no parallel constant introduced); `_compute_score_gap_material` (Section 2 path) intact at lines 723+/851-870 |
| `tests/test_endgame_service.py` | Unit tests for symmetric mirror, below-threshold None, at-threshold computed, zero-sample safety, schema shape | VERIFIED | Five new tests at lines 393-499 inside `TestAggregateEndgameStats`: `test_per_type_opponent_baseline_symmetric_60_40`, `_below_threshold`, `_at_threshold_10`, `_zero_sample`, `_schema_shape`. All 5 pass; class total 17 tests green |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `endgame_service.py:_aggregate_endgame_stats` | `endgames.py:ConversionRecoveryStats` | constructor kwargs | WIRED | `endgame_service.py:380-395` constructs `ConversionRecoveryStats(...)` passing all 4 new kwargs |
| Phase 84 mirror block | `_MIN_OPPONENT_SAMPLE` (line 234) | threshold gate on mirror bucket size | WIRED | Both gates (lines 364, 372) reference `_MIN_OPPONENT_SAMPLE`; no parallel constant grep-confirmed (grep `PER_CLASS_OPPONENT_SAMPLE_MIN` returns 0 matches) |
| Backend payload | `/api/endgames/overview` | `EndgameCategoryStats.conversion: ConversionRecoveryStats` → `EndgameStatsResponse` / `EndgameOverviewResponse` | WIRED | `endgames.py:78` embeds `ConversionRecoveryStats` in `EndgameCategoryStats.conversion`; reaches `/api/endgames/overview` via `EndgameOverviewResponse` (used by `_aggregate_endgame_stats` call at `endgame_service.py:2121`) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `ConversionRecoveryStats.opponent_*` | `opponent_conversion_pct`, `opponent_recovery_pct` | Computed inline from `conv_data` / `recov_data` accumulators at `endgame_service.py:340-378`; populated by `wdl`/`conv`/`recov` Counters fed from `_aggregate_endgame_stats(rows)` input which originates from the existing endgame DB rows | FLOWING | Tests use real `_aggregate_endgame_stats(rows)` calls with synthetic rows and observe correct percentages (60.0 / 40.0) — confirms data flows through the accumulator → arithmetic → schema chain |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Schema introspection: 4 new fields present and required | `python -c "from app.schemas.endgames import ConversionRecoveryStats; f = ConversionRecoveryStats.model_fields; print(all(n in f and f[n].is_required() for n in ('opponent_conversion_pct','opponent_conversion_games','opponent_recovery_pct','opponent_recovery_games')))"` (via test_per_type_opponent_baseline_schema_shape) | passed | PASS |
| Mirror identity 60/40 produces documented values | `pytest tests/test_endgame_service.py::TestAggregateEndgameStats::test_per_type_opponent_baseline_symmetric_60_40` | passed | PASS |
| Below-threshold gating returns None | `pytest tests/test_endgame_service.py -k "below_threshold"` | passed | PASS |
| At-threshold (=10) computes non-None | `pytest tests/test_endgame_service.py -k "at_threshold"` | passed | PASS |
| Zero-sample safety (no ZeroDivisionError) | `pytest tests/test_endgame_service.py -k "zero_sample"` | passed | PASS |
| Full TestAggregateEndgameStats green | `pytest tests/test_endgame_service.py::TestAggregateEndgameStats -x` | 17 passed | PASS |
| Touched-files regression | `pytest tests/test_endgame_service.py tests/services/test_insights_llm.py tests/services/test_insights_service_series.py` | 327 passed | PASS |
| ty check zero errors | `uv run ty check app/ tests/` | All checks passed! | PASS |
| ruff lint clean (modified files) | `uv run ruff check app/schemas/endgames.py app/services/endgame_service.py tests/test_endgame_service.py ...` | All checks passed! | PASS |
| ruff format check (modified files) | `uv run ruff format --check ...` | 5 files already formatted | PASS |

### Probe Execution

No project-conventional `scripts/*/tests/probe-*.sh` declared in PLAN or SUMMARY. The phase's verification contract is the `pytest` + `ty` + `ruff` block in PLAN `<verification>`, which is fully covered above as behavioral spot-checks.

SKIPPED (no probes declared).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| DATA-02 | 84-01 | Mirror-bucket peer rates exposed on `/api/endgames/overview` for Section 2 (Conv/Parity/Recov + Skill components) and per-type Conv/Recov in Section 3 | SATISFIED | Section 2: audited as already wired via Phase 60 (`MaterialRow.opponent_score/games` at `endgames.py:252-254` + `_compute_score_gap_material` at `endgame_service.py:851-870` + frontend consumer at `EndgameScoreGapSection.tsx:114-145`). Section 3: shipped via 4 new fields on `ConversionRecoveryStats` populated by mirror identity (`endgame_service.py:358-394`). Skill derivation note documents Phase 86 client-side computation from existing `MaterialRow[conversion].opponent_score` + `MaterialRow[recovery].opponent_score` — no new payload field needed |

No orphaned requirements: REQUIREMENTS.md line 110 maps `DATA-02 → Phase 84 → Pending`, and 84-01-PLAN.md's `requirements: [DATA-02]` claims it. SEC2-05, SEC3-03, DATA-01 were intentionally dropped on 2026-05-12 per the single-bullet doctrine pivot (`.planning/REQUIREMENTS.md:117`) — not orphaned.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `app/services/endgame_service.py` | 968 | `TODO (Phase 56): deduplicate with the backend endgame_skill() port` | Info | Pre-existing, unrelated to Phase 84 changes (modifications are at lines 358-394 and 380-395 only). Not introduced by this phase. References Phase 56 follow-up. Not a blocker for this phase. |

No new debt markers added by Phase 84. `git diff` over the phase commits shows no `+` lines containing `TODO`, `FIXME`, `XXX`, `HACK`, or `PLACEHOLDER`.

### Out-of-Scope Files Check

Per PLAN `<verification>` block: `app/services/endgame_zones.py`, `scripts/gen_endgame_zones_ts.py`, `frontend/src/generated/endgameZones.ts`, `tests/services/test_endgame_zones.py` must be UNCHANGED. `git diff --name-only HEAD~5 HEAD | grep -E "(endgame_zones\.py|gen_endgame_zones_ts\.py|endgameZones\.ts|test_endgame_zones\.py)"` returns empty — confirmed clean.

### Human Verification Required

None. The phase deliverable is a backend schema extension + an audit prose paragraph. Both are fully verifiable through code introspection and the test suite (which exercises the mirror identities with deterministic inputs against documented expected outputs). No UI/UX, no real-time behavior, no external service — Phase 86 and Phase 87 are the consumers and will surface UI bugs in their own verifications.

### Gaps Summary

None. All seven must-have truths verified; all three artifacts present and substantive; all three key links wired; data flows correctly through the accumulator → arithmetic → schema chain; behavioral spot-checks all pass; DATA-02 satisfied through the documented audit + minimal backend extension; no out-of-scope files touched; no debt markers introduced.

The phase pivoted scope mid-flight (per the planning notes the audit revealed Section 3 was NOT already wired and a minimal extension was required) — the success criterion explicitly permits this via its "OR a minimal backend extension is shipped" clause. The shipped extension follows the established Phase 60 mirror-identity pattern, with the documented asymmetry (Conv = win-rate, Recov = save-rate) correctly preserved in both code and tests.

---

_Verified: 2026-05-13T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
