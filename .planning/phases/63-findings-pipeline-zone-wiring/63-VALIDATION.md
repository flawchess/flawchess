---
phase: 63
slug: findings-pipeline-zone-wiring
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-20
---

# Phase 63 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend), vitest (frontend — not used in this phase) |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/services/test_insights_service.py tests/services/test_endgame_zones.py tests/services/test_endgame_zones_consistency.py -x` |
| **Full suite command** | `uv run pytest tests/services/ -x` |
| **Estimated runtime** | ~30 seconds quick / ~3 min full |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite + `uv run ty check app/ tests/` + `uv run ruff check .` must be green; `python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` must exit 0
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> The planner populates this table per plan/task. Initial dimensions traced from RESEARCH.md §"Validation Architecture".

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 63-01-T1 | 63-01 | 1 | FIND-02 | — | Zone registry is Python source of truth; thresholds are named constants | unit (file + import check) | `uv run ty check app/services/endgame_zones.py && uv run ruff check app/services/endgame_zones.py` | ✅ | ⬜ pending |
| 63-01-T2 | 63-01 | 1 | FIND-02 (D-10) | — | Recovery band re-centered to [0.25, 0.35] in TSX | grep | `grep -c "from: 0.25, to: 0.35" frontend/src/components/charts/EndgameScoreGapSection.tsx` returns 1 | ✅ | ⬜ pending |
| 63-01-T3 | 63-01 | 1 | FIND-02 | — | assign_zone direction handling, NaN guard, D-10 band, registry sanity | unit | `uv run pytest tests/services/test_endgame_zones.py -x` | ✅ W0 | ⬜ pending |
| 63-02-T1 | 63-02 | 2 | FIND-02 (codegen) | — | `gen_endgame_zones_ts.py` produces committed file byte-for-byte | CI | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | ✅ | ⬜ pending |
| 63-02-T2 | 63-02 | 2 | FIND-02 (drift) | — | CI step enforces drift guard on every PR | CI | `grep -A 3 "Zone drift check" .github/workflows/ci.yml \| grep -q "git diff --exit-code frontend/src/generated/endgameZones.ts"` | ✅ | ⬜ pending |
| 63-02-T3 | 63-02 | 2 | FIND-02 (drift) | — | FE inline constants match Python registry until Phase 66 consumer switch | unit + drift | `uv run pytest tests/services/test_endgame_zones_consistency.py -x` | ✅ W0 | ⬜ pending |
| 63-03-T1 | 63-03 | 2 | FIND-01, FIND-05 | — | Pydantic schemas lock field order and types for Phase 65 consumers | unit (import + round-trip) | `uv run ty check app/schemas/insights.py && uv run python -c "from app.schemas.insights import EndgameTabFindings, FilterContext, SubsectionFinding; print('OK')"` | ✅ | ⬜ pending |
| 63-04-T1 | 63-04 | 3 | FIND-01, FIND-03, FIND-04, FIND-05 | — | compute_findings consumes only endgame_service, two sequential calls, no gather, no repo imports | integration (source grep + ty) | `grep -c "from app.repositories" app/services/insights_service.py` returns 0; `uv run ty check app/services/insights_service.py` exits 0 | ✅ | ⬜ pending |
| 63-05-T1 | 63-05 | 4 | FIND-01 | — | Module source has no repository imports and no asyncio.gather | unit | `uv run pytest tests/services/test_insights_service.py::TestComputeFindingsLayering -x` | ✅ W0 | ⬜ pending |
| 63-05-T1 | 63-05 | 4 | FIND-03 | — | Four cross-section flags fire/no-fire deterministically; thresholds from registry | unit | `uv run pytest tests/services/test_insights_service.py::TestComputeFlags -x` | ✅ W0 | ⬜ pending |
| 63-05-T1 | 63-05 | 4 | FIND-04 | — | Trend gate: count-fail, ratio-fail, both-pass, stable | unit | `uv run pytest tests/services/test_insights_service.py::TestComputeTrend -x` | ✅ W0 | ⬜ pending |
| 63-05-T1 | 63-05 | 4 | FIND-05 | — | findings_hash stable across invocations, NaN-safe, dict-order-invariant | unit | `uv run pytest tests/services/test_insights_service.py::TestComputeHash -x` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_insights_service.py` — stubs for FIND-01, FIND-03, FIND-04, FIND-05
- [ ] `tests/services/test_endgame_zones.py` — stubs for `assign_zone` direction handling
- [ ] `tests/services/test_endgame_zones_consistency.py` — FE-drift regex parser stub for FIND-02
- [ ] `tests/services/conftest.py` (or extend existing) — fixtures: `seeded_user` (Phase 61), `frozen_now` (`as_of` deterministic for hash-stability test)

*Phase 63 reuses `seeded_user` fixture from Phase 61; no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hash stability across Python process restarts (not just within one process) | FIND-05 | `pytest` runs in one process; cross-session hash determinism is the property the LLM cache (Phase 65) depends on | Run `uv run pytest tests/services/test_insights_service.py::test_findings_hash_stable` twice as separate `pytest` invocations and confirm the printed hash literal is identical |
| CI diff-guard exits non-zero when registry drifts | FIND-02 | Verifies the GitHub Actions step (not just local run) | After PR opens, manually edit `endgame_zones.py` typical_lower for one metric, push to a scratch branch, confirm CI fails on the `git diff --exit-code` step |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/services/test_insights_service.py`, `tests/services/test_endgame_zones.py`, `tests/services/test_endgame_zones_consistency.py`, `frontend/src/generated/endgameZones.ts` ignored in `frontend/knip.json`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
