---
phase: 113
slug: opponent-flaw-materialization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase 113 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `113-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`asyncio_mode = "auto"`) + pytest-xdist |
| **Config file** | `pyproject.toml` (addopts, asyncio_mode) |
| **Quick run command** | `uv run pytest tests/services/test_flaws_service.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~120s full suite (parallel) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/services/test_flaws_service.py tests/test_flaws_materialization.py tests/test_flaw_predicate.py -x`
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds (targeted files)

---

## Per-Task Verification Map

> Filled per-plan during planning/execution. Requirement → behavior map below is the source.

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| FLAWX-01 | `is_opponent_expr` returns correct boolean for all 4 (ply parity × user_color) combinations | unit | `uv run pytest tests/services/test_flaws_service.py::TestIsOpponentExpr -x` | ❌ W0 |
| FLAWX-01 | After backfill, ungated query returns ~2x player-only baseline row count | integration | `uv run pytest tests/test_flaws_materialization.py::TestBothSidesMaterialization -x` | ❌ W0 |
| FLAWX-02 | Kernel emits opponent FlawRecords with correct `side` field | unit | `uv run pytest tests/services/test_flaws_service.py::TestClassifyBothColors -x` | ❌ W0 |
| FLAWX-02 | `lucky` tag on opponent end-of-game blunder uses opponent's result | unit | `uv run pytest tests/services/test_flaws_service.py::TestOpponentLuckyTag -x` | ❌ W0 |
| FLAWX-04 (D-04 gate) | `query_flaws` returns only player flaws after gating | integration | `uv run pytest tests/test_library_repository.py::TestPlayerOnlyGate -x` | ❌ W0 |
| FLAWX-04 (D-04 gate) | `fetch_page_game_flaws` returns only player flaws after gating | integration | `uv run pytest tests/test_library_repository.py::TestPageFlawsPlayerOnly -x` | ❌ W0 |
| FLAWX-04 (D-04 gate) | `fetch_stats_aggregates` counts unchanged vs pre-phase baseline | integration | `uv run pytest tests/test_library_repository.py::TestStatsAggregatesPlayerOnly -x` | ❌ W0 |
| FLAWX-04 (D-04 gate) | `flaw_exists_from_table` EXISTS matches only player flaws | integration | `uv run pytest tests/test_flaw_predicate.py::TestFlawExistsPlayerOnly -x` | ❌ W0 (extend) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_flaws_service.py::TestIsOpponentExpr` — FLAWX-01 parity correctness (all 4 combos; guards the documented off-by-one trap)
- [ ] `tests/services/test_flaws_service.py::TestClassifyBothColors` — FLAWX-02 kernel both-sides emission
- [ ] `tests/services/test_flaws_service.py::TestOpponentLuckyTag` — FLAWX-02 lucky tag uses per-mover `subject_result`
- [ ] `tests/test_flaws_materialization.py::TestBothSidesMaterialization` — FLAWX-01 row count roughly doubles
- [ ] `tests/test_library_repository.py::TestPlayerOnlyGate` — D-04 gating for `query_flaws`
- [ ] `tests/test_library_repository.py::TestPageFlawsPlayerOnly` — D-04 for `fetch_page_game_flaws`
- [ ] `tests/test_library_repository.py::TestStatsAggregatesPlayerOnly` — D-04 for aggregates (no-regression baseline)
- [ ] `tests/test_flaw_predicate.py::TestFlawExistsPlayerOnly` — D-04 for `flaw_exists_from_table` (extend existing file)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Benchmark cohort backfill writes both sides | FLAWX-04 | Long-running cohort job; do NOT gate phase completion on it (CONTEXT D-09) | Run `scripts/backfill_flaws.py` against benchmark DB; spot-check a sample of games show opponent-ply rows. HUMAN-UAT. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
