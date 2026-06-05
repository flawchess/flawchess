---
phase: 106
slug: games-surface-backend-mistake-filter-per-game-counts-stats-aggregates-on-the-fly
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-05
---

# Phase 106 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (per-run isolated PostgreSQL DB; see `tests/conftest.py`) |
| **Config file** | `pyproject.toml` (addopts, asyncio mode; slow dirs via `--ignore`) |
| **Quick run command** | `uv run pytest tests/test_library_repository.py tests/services/test_library_service.py -x` |
| **Full suite command** | `uv run pytest -n auto` |
| **Estimated runtime** | ~20s full suite (parallel) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (scoped to the touched test file)
- **After every plan wave:** Run `uv run pytest -n auto`
- **Before `/gsd-verify-work`:** Full suite green + `uv run ruff check . && uv run ruff format --check . && uv run ty check app/ tests/`
- **Max feedback latency:** ~20 seconds

---

## Per-Task Verification Map

> Planner fills this from the task breakdown. Anchor rows from RESEARCH.md §"Phase Requirements → Test Map":

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 106-01-02 | 01 | 1 | LIBG-08 | T-106-01 | EXISTS severity filter selects only games with ≥1 **USER** ply of the severity (opponent-only blunder excluded — B1) | integration | `uv run pytest tests/test_library_repository.py -k exists_filter -x` | ✅ (106-01 T2) | ⬜ pending |
| 106-01-02 | 01 | 1 | LIBG-08 | — | **SQL drop math == user-color-filtered M+B subset of the Python kernel** on a fixture game (cross-check, criterion 5 / B2) | integration | `uv run pytest tests/test_library_repository.py -k cross_check -x` | ✅ (106-01 T2) | ⬜ pending |
| 106-01-01 | 01 | 1 | LIBG-08 | T-106-AC | chess.com / unanalyzed game → "no engine analysis", never 0/0/0 | unit/integration | `uv run pytest tests/services/test_library_service.py -k no_engine_analysis -x` | ✅ (106-01 T1) | ⬜ pending |
| 106-02-02 | 02 | 2 | LIBG-08 | — | per-game B/M/I counts (incl. inaccuracy) + curated/deduped chips (phase excluded) | unit | `uv run pytest tests/services/test_library_service.py -k chips -x` | ✅ (106-01 T1 scaffold) | ⬜ pending |
| 106-03-01 | 03 | 3 | LIBG-09 | — | analyzed-% denominator (≥90% coverage) + analyzed N stated in response | integration | `uv run pytest tests/test_library_repository.py -k analyzed_denominator -x` | ✅ (106-01 T2 scaffold) | ⬜ pending |
| 106-03-02 | 03 | 3 | LIBG-09 | — | per-severity rates (per game / per 100 user-moves); tag distribution (defined result-changing denom); rolling-game trend series | unit/integration | `uv run pytest tests/services/test_library_service.py -k stats -x` | ✅ (106-01 T1 scaffold) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

> Plan 106-01 (Wave 1, the first wave) creates BOTH test scaffold files in its two tasks — these
> stand in for a dedicated Wave-0 pass since the scaffolds are co-created with the first kernel/SQL seam.

- [x] `tests/test_library_repository.py` — scaffolded by 106-01 Task 2: EXISTS filter (incl. opponent-only-blunder exclusion), window-scan, **SQL↔kernel cross-check fixture** (user-color-filtered M+B), analyzed-denominator placeholder (DB-backed; reuse `_seed_game`/`_seed_position` helpers from `tests/test_mistakes_repository.py`)
- [x] `tests/services/test_library_service.py` — scaffolded by 106-01 Task 1: counts/chips curation, no-engine-analysis state, stats aggregates, trend placeholders (mostly pure; build positions in memory à la `tests/services/test_mistakes_service.py`)
- [x] No framework install needed — pytest/pytest-asyncio + isolated-DB harness already exist

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Index decision (criterion 1) | LIBG-08 | Requires `EXPLAIN ANALYZE` against a real DB to confirm the `(game_id, user_id, ply)` PK serves the window-scan | Run the EXISTS/window-scan query under `EXPLAIN ANALYZE` on dev DB; add a `(game_id, ply)` index ONLY if the plan shows the PK isn't used. Document the result in VERIFICATION.md |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (both scaffold files created in 106-01)
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
