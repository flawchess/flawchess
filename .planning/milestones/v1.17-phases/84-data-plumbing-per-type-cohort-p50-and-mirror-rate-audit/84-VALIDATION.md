---
phase: 84
slug: data-plumbing-per-type-cohort-p50-and-mirror-rate-audit
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-12
---

# Phase 84 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `84-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (declared in `pyproject.toml`) |
| **Config file** | `pyproject.toml` (project standard) + existing `tests/` tree |
| **Quick run command** | `uv run pytest tests/services/test_endgame_zones.py tests/test_endgame_service.py -x` |
| **Full suite command** | `uv run pytest` |
| **Zone drift guard** | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` |
| **Type check** | `uv run ty check app/ tests/` (zero errors required per CLAUDE.md) |
| **Estimated runtime** | ~2 seconds (quick); ~60–90 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/services/test_endgame_zones.py tests/test_endgame_service.py -x`
- **After every plan wave:** Run `uv run pytest && uv run ty check app/ tests/ && uv run ruff check . && uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts`
- **Before `/gsd-verify-work`:** Full suite green, ty zero errors, codegen drift guard green
- **Max feedback latency:** ~2 seconds for the targeted quick run

---

## Per-Task Verification Map

> Plan IDs are placeholders pending plan-phase IDs (`84-01-*`, `84-02-*`, `84-03-*` per the D-11 3-plan layout). Update task IDs after plan-phase writes them.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 84-01-* | 01 | 1 | DATA-01 | — | N/A | unit | `uv run pytest tests/services/test_endgame_zones.py::TestPerClassP50 -x` | ❌ W0 | ⬜ pending |
| 84-01-* | 01 | 1 | DATA-01 | — | N/A | unit | per-class `test_<class>_p50_matches_benchmark` | ❌ W0 | ⬜ pending |
| 84-01-* | 01 | 1 | DATA-01 | — | N/A | integration | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | ✅ (`.github/workflows/ci.yml:47-50`) | ⬜ pending |
| 84-01-* | 01 | 1 | DATA-01 | — | N/A | unit | `test_p50_inside_iqr_for_most_classes` (sanity) | ❌ W0 | ⬜ pending |
| 84-02-* | 02 | 2 | DATA-02 | — | Pydantic v2 response-only schema; no new input validation | unit (schema shape) | `uv run pytest tests/test_endgame_service.py -k opponent -x` + `uv run ty check app/ tests/` | ✅ file / ❌ W0 tests | ⬜ pending |
| 84-02-* | 02 | 2 | DATA-02 | — | N/A | unit | `test_per_type_opponent_conversion_pct_mirror_identity` | ❌ W0 | ⬜ pending |
| 84-02-* | 02 | 2 | DATA-02 | — | N/A | unit | `test_per_type_opponent_recovery_pct_mirror_identity` | ❌ W0 | ⬜ pending |
| 84-02-* | 02 | 2 | DATA-02 | — | None-when-mirror-sample below `_MIN_OPPONENT_SAMPLE` | unit | `test_per_type_opponent_pct_none_below_threshold` | ❌ W0 | ⬜ pending |
| 84-02-* | 02 | 2 | DATA-02 | — | Computed at boundary (mirror sample == 10) | unit | `test_per_type_opponent_pct_at_threshold_10` | ❌ W0 | ⬜ pending |
| 84-02-* | 02 | 2 | DATA-02 | — | No DivByZero when class has zero games | unit | `test_per_type_opponent_zero_sample` | ❌ W0 | ⬜ pending |
| 84-03-* | 03 | 3 | DATA-01+DATA-02 | — | N/A (audit doc only) | manual review | inline `84-01-SUMMARY.md` cross-refs Phase 60 + new fields | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_endgame_zones.py::TestPerClassP50` — new test class covering DATA-01 (6 classes × p50 values, IQR sanity, types). Append to existing file structure (`TestAssignZone`, `TestRegistrySanity`, etc.).
- [ ] `tests/test_endgame_service.py::TestAggregateEndgameStats` per-type opponent tests — new tests for DATA-02 mirror identity, threshold semantics, zero-sample safety. Template: existing Phase 60 mirror tests at `:1405-1470`.
- [ ] (No new test FILES required.) (No framework install required.) (No conftest changes required.)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Audit doc accuracy: Phase 60 line refs valid, mirror-identity math correct, threshold convention documented | DATA-02 (audit deliverable, D-10) | Audit is prose; no automated check verifies cross-reference correctness | Reviewer reads `84-01-SUMMARY.md` audit section, confirms cited line numbers point to current code, and that mirror-identity formulas match the unit-test expectations. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (audit task is the one Manual-Only entry)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (TestPerClassP50 + per-type opponent test cases)
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s (quick run measured ~2s)
- [ ] `nyquist_compliant: true` set in frontmatter after plan-phase wires real task IDs

**Approval:** pending
