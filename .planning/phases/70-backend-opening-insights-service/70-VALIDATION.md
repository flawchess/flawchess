---
phase: 70
slug: backend-opening-insights-service
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-26
---

# Phase 70 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async via pytest-anyio) |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/services/test_opening_insights_service.py tests/repositories/test_openings_repository.py tests/routers/test_insights.py -x` |
| **Full suite command** | `uv run ruff check . && uv run ty check app/ tests/ && uv run pytest -x` |
| **Estimated runtime** | ~30 seconds quick, ~120 seconds full |

---

## Sampling Rate

- **After every task commit:** Run quick command for the touched layer.
- **After every plan wave:** Run full suite (ruff + ty + pytest).
- **Before `/gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 30 seconds.

---

## Per-Task Verification Map

> Filled in by gsd-planner during planning. One row per task.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 70-01-01 | 01 | 1 | INSIGHT-CORE-01..09 | — | N/A (read model) | unit | `uv run pytest tests/schemas/test_opening_insights.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/schemas/test_opening_insights.py` — Pydantic round-trip + Literal enum coverage for `OpeningInsightFinding`
- [ ] `tests/repositories/test_openings_repository.py::test_next_ply_wdl_aggregation` — synthetic `game_positions` rows covering boundary plies (1, 2, 3, 4, 16, 17, 18) and the partial-index predicate
- [ ] `tests/services/test_opening_insights_service.py` — boundary fixtures at n=9/10/11 games, loss_rate=0.54/0.55/0.56, score=0.59/0.60/0.61, dedup collisions across opening paths
- [ ] `tests/routers/test_insights.py::test_post_openings_insights_*` — auth contract, filter equivalence, response schema
- [ ] `tests/migrations/test_ix_gp_user_game_ply.py` (or alembic test) — verifies `EXPLAIN` uses partial index on the canonical query
- [ ] `tests/conftest.py` — extend if needed; reuse `user_with_games` and `game_positions` factories

*Frontend constants-consistency test is deferred to the frontend phase; backend phase covers a regex-parse stub if `frontend/src/lib/insights.ts` exists at execution time.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration `CONCURRENTLY` index build runs in `entrypoint.sh` deploy without timeout on prod-scale data | INSIGHT-CORE-09 | Cannot reproduce 5.7M row scan in CI; first project migration using `postgresql_concurrently=True` | Apply via `bin/prod_db_tunnel.sh` + `alembic upgrade --sql`, time the build; if > 90 s, pre-apply during a maintenance window |
| Latency budget for typical user (≤2k games) under default DB pool | INSIGHT-CORE-09 | Production-scale latency, requires real game volume | Hit `POST /api/insights/openings` against staging or prod-tunnel data; assert P95 < 1s without service-layer cache |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
