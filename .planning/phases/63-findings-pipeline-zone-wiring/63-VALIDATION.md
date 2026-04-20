---
phase: 63
slug: findings-pipeline-zone-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 63-XX-XX | TBD | TBD | FIND-01 | — | findings service consumes only `endgame_service.get_endgame_overview` | integration | `uv run pytest tests/services/test_insights_service.py::test_consumes_overview_only` | ❌ W0 | ⬜ pending |
| 63-XX-XX | TBD | TBD | FIND-02 | — | gauge thresholds sourced from `endgame_zones.ZONE_REGISTRY`, FE inline values match | unit + drift | `uv run pytest tests/services/test_endgame_zones_consistency.py` | ❌ W0 | ⬜ pending |
| 63-XX-XX | TBD | TBD | FIND-03 | — | four cross-section flags fire deterministically against fixture | unit | `uv run pytest tests/services/test_insights_service.py::test_cross_section_flags` | ❌ W0 | ⬜ pending |
| 63-XX-XX | TBD | TBD | FIND-04 | — | trend gates on weekly count AND slope/volatility ratio | unit | `uv run pytest tests/services/test_insights_service.py::test_trend_gating` | ❌ W0 | ⬜ pending |
| 63-XX-XX | TBD | TBD | FIND-05 | — | `findings_hash` stable across two sessions, unchanged across days | unit | `uv run pytest tests/services/test_insights_service.py::test_findings_hash_stable` | ❌ W0 | ⬜ pending |
| 63-XX-XX | TBD | TBD | FIND-02 (codegen) | — | `gen_endgame_zones_ts.py` output equals committed file | CI | `python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | ❌ W0 | ⬜ pending |

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
