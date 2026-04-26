---
phase: 70
slug: backend-opening-insights-service
status: revised
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-26
revised: 2026-04-26
---

# Phase 70 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Regenerated 2026-04-26 to address BLOCKER-3: stale fixtures (loss_rate
> 0.54/0.55/0.56, score-based n=9/10/11) replaced with the locked
> D-04 strict `>0.55` boundaries and D-33 evidence floor n=20.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio (verified `tests/services/__pycache__/*.cpython-313-pytest-9.0.3.pyc`) |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/schemas/test_opening_insights.py tests/services/test_opening_insights_service.py tests/services/test_opening_insights_arrow_consistency.py tests/repositories/test_opening_insights_repository.py tests/routers/test_insights_openings.py -x` |
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

> One row per task across all five plans. The `<automated>` command is the
> exact verify line from each plan's task. `Status` flips from ⬜ to ✅
> as plans land.

| Task ID | Plan | Wave | Requirements | Threat Refs | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|--------------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 70-01-01 | 01 | 1 | INSIGHT-CORE-01, 08 | T-70-01-01..04 | Pydantic v2 Literal enums reject invalid recency / strength / color; `entry_full_hash: str` & `resulting_full_hash: str` prevent JS precision loss; no `user_id` field | unit | `uv run python -c "from app.schemas.opening_insights import OpeningInsightsRequest, OpeningInsightFinding, OpeningInsightsResponse; ..." && uv run ty check app/schemas/opening_insights.py` | ❌ W0 | ⬜ pending |
| 70-01-02 | 01 | 1 | INSIGHT-CORE-01..09 | T-70-01-04 | Wave 0 test scaffolds collect cleanly; tests fail by design until downstream waves land | unit | `uv run pytest tests/services/test_opening_insights_service.py tests/repositories/test_opening_insights_repository.py tests/services/test_opening_insights_arrow_consistency.py tests/routers/test_insights_openings.py --co -q` | ❌ W0 | ⬜ pending |
| 70-02-01 | 02 | 1 | INSIGHT-CORE-09 | T-70-02-01..04 | Partial composite covering index built CONCURRENTLY; column order load-bearing for LAG; rollback symmetric | migration | `uv run python -c "..." && uv run alembic upgrade head && docker compose ... -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename='game_positions' AND indexname='ix_gp_user_game_ply';" \| grep -c "user_id, game_id, ply"` | ❌ W0 | ⬜ pending |
| 70-02-02 | 02 | 1 | INSIGHT-CORE-09 | T-70-02-03 | Declarative `Index()` matches migration so autogenerate proposes no diff | unit | `grep -c "ix_gp_user_game_ply" app/models/game_position.py \| grep -q "^1$" && uv run ty check app/models/game_position.py && uv run python -c "from app.models.game_position import GamePosition; ..."` | ❌ W0 | ⬜ pending |
| 70-03-01 | 03 | 2 | INSIGHT-CORE-01..05 | T-70-03-01..04 | LAG partitioned by game_id (no cross-game leak); HAVING `cast(wins, Float) / cast(n_games, Float) > 0.55` strict; SAN sequence + resulting_full_hash surfaced for D-21 / D-34; EXPLAIN uses Index Only Scan | repo SQL | `uv run pytest tests/repositories/test_opening_insights_repository.py -x && uv run ty check app/repositories/openings_repository.py tests/repositories/test_opening_insights_repository.py && uv run ruff check app/repositories/openings_repository.py tests/repositories/test_opening_insights_repository.py` | ❌ W0 | ⬜ pending |
| 70-03-02 | 03 | 2 | INSIGHT-CORE-06 | T-70-03-01 | `query_openings_by_hashes` filters NULL full_hash, picks max(ply_count); empty input bypasses SQL | repo SQL | `uv run pytest tests/repositories/test_opening_insights_repository.py -x && uv run ty check app/repositories/openings_repository.py` | ❌ W0 | ⬜ pending |
| 70-04-01 | 04 | 3 | INSIGHT-CORE-01, 04, 05, 06, 07, 08 | T-70-04-01..04 | Sequential awaits (no asyncio.gather); two-pass attribution with `ctypes.c_int64` signed-int64 conversion; D-34 unmatched-lineage findings DROPPED (Sentry tag `openings.attribution.unmatched_dropped`); Sentry context capture not f-string interpolation; module constants mirror arrowColor.ts | unit | `uv run pytest tests/services/test_opening_insights_service.py tests/services/test_opening_insights_arrow_consistency.py -x && uv run ty check app/services/opening_insights_service.py tests/services/test_opening_insights_service.py && uv run ruff check app/services/opening_insights_service.py tests/services/test_opening_insights_service.py` | ❌ W0 | ⬜ pending |
| 70-05-01 | 05 | 4 | INSIGHT-CORE-01, 08 | T-70-05-01..04 | `Depends(current_active_user)` enforces auth; `model_config = ConfigDict(extra="forbid")` rejects user_id in body; route does NOT call `_validate_full_history_filters` | router contract | `uv run pytest tests/routers/test_insights_openings.py -x && uv run ty check app/routers/insights.py tests/routers/test_insights_openings.py app/schemas/opening_insights.py && uv run ruff check app/routers/insights.py tests/routers/test_insights_openings.py app/schemas/opening_insights.py` | ❌ W0 | ⬜ pending |
| 70-05-02 | 05 | 4 | INSIGHT-CORE-01..09 | T-70-05-05 | REQUIREMENTS / ROADMAP / CHANGELOG amendments ship in same commit as code; old wording removed | docs | `grep -c "MIN_GAMES_PER_CANDIDATE = 20" .planning/REQUIREMENTS.md && grep -c "transition aggregation" .planning/milestones/v1.13-ROADMAP.md && grep -c "Phase 70" CHANGELOG.md && grep -c "ix_gp_user_game_ply" CHANGELOG.md && uv run ruff check . && uv run ty check app/ tests/ && uv run pytest -x -q 2>&1 \| tail -5` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

These are the test files Plan 70-01 must scaffold (failing-by-design) so
downstream plans can flip them green. Test paths reflect the actual layout
in the plans (NOT the stale paths from the pre-revision draft):

- [ ] `tests/schemas/test_opening_insights.py` — Pydantic v2 round-trip + Literal enum coverage for `OpeningInsightsRequest`, `OpeningInsightFinding`, `OpeningInsightsResponse`. Round-trip a representative finding; reject `recency="all_time"`; reject `severity="medium"`; reject `entry_full_hash=12345` (int); reject unknown body fields under `model_config = ConfigDict(extra="forbid")` (added in Plan 70-05).
- [ ] `tests/repositories/test_opening_insights_repository.py` — SQL contract tests for `query_opening_transitions` against the dev DB. Covers entry-ply boundaries (3, 16 inclusive; 2, 17 excluded), LAG NULL on first ply of each game, `MIN_GAMES_PER_CANDIDATE` floor, strict `>0.55` HAVING, `resulting_full_hash` and `entry_san_sequence` Row contract (BLOCKER-6), and EXPLAIN partial-index alignment (precondition: `uv run alembic upgrade head` per BLOCKER-4).
- [ ] `tests/services/test_opening_insights_service.py` — service unit tests. Boundary fixtures REVISED per the locked decisions (D-04 strict `>0.55`, D-05 severity at `>=0.60`, D-33 floor n=20):
  - **Evidence floor:** n=19 (excluded), n=20 (included), n=21 (included).
  - **Loss rate boundary:** loss_rate = 0.549 (neutral), 0.550 (neutral — strict `>`), 0.551 (minor weakness).
  - **Loss rate severity tier:** loss_rate = 0.599 (minor), 0.600 (major), 0.650 (major).
  - **Win rate boundary:** win_rate = 0.549, 0.550 (neutral), 0.551 (minor strength).
  - **Win rate severity tier:** win_rate = 0.599 (minor), 0.600 (major), 0.700 (major).
  - **Concrete W/D/L counts at boundaries (n=20):**
    - 11/4/5 → win_rate=0.55 → NEUTRAL (strict `>`)
    - 12/4/4 → win_rate=0.60 → MAJOR strength
    - 5/4/11 → loss_rate=0.55 → NEUTRAL (strict `>`)
    - 4/4/12 → loss_rate=0.60 → MAJOR weakness
  - Dedupe collisions across resulting_full_hash within section (D-21).
  - Cross-color same-hash preserved as two findings (D-21).
  - **D-34 drop test:** `test_attribution_drops_finding_when_no_lineage_match` — when neither direct nor parent-lineage attribution matches, the finding is DROPPED from the response (Sentry tag set).
- [ ] `tests/services/test_opening_insights_arrow_consistency.py` — regex-parses `frontend/src/lib/arrowColor.ts` for `LIGHT_COLOR_THRESHOLD = 55` and `DARK_COLOR_THRESHOLD = 60`; asserts equality with Python service constants × 100.
- [ ] `tests/routers/test_insights_openings.py` — six router-contract tests: 401 without auth, four-section response, 422 on invalid recency, 422 on `user_id` in body (extra=forbid), no `_validate_full_history_filters`, filter equivalence.

*The migration test is bundled into the repository EXPLAIN test (`test_partial_index_predicate_alignment` in `tests/repositories/test_opening_insights_repository.py`) — no separate `tests/migrations/` directory required. The Plan 70-01 router-test scaffold uses `pytest.importorskip` so it is collectable but inert until 70-04/05 land (see Plan 70-04 WARN-4 — 70-04 and 70-05 ship in a single commit / PR).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration `CONCURRENTLY` index build runs in `entrypoint.sh` deploy without timeout on prod-scale data | INSIGHT-CORE-09 | Cannot reproduce 5.7M-row scan in CI; first project migration using `postgresql_concurrently=True` | Apply via `bin/prod_db_tunnel.sh` + `alembic upgrade --sql`, time the build; if > 90 s, pre-apply during a maintenance window |
| Latency budget for typical user (≤2k games) under default DB pool | INSIGHT-CORE-09 | Production-scale latency, requires real game volume | Hit `POST /api/insights/openings` against staging or prod-tunnel data; assert P95 < 1 s without service-layer cache |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (every task in the per-task map carries the verbatim verify command from its plan).
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task is automated).
- [x] Wave 0 covers all MISSING references (schemas, repository, service, arrow-consistency, router tests).
- [x] No watch-mode flags.
- [x] Feedback latency < 30 s for the per-layer quick command.
- [x] `nyquist_compliant: true` set in frontmatter (boundary fixtures cover D-04 strict `>0.55`, D-05 severity at `>=0.60`, and D-33 evidence floor n=20).

**Approval:** revised 2026-04-26 — addresses BLOCKER-3 (stale fixtures), BLOCKER-1/2/5/6 (test paths and Row contract surfaced via the per-task map), BLOCKER-4 (EXPLAIN precondition documented in Wave 0 Requirements).
