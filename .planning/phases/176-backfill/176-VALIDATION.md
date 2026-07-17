---
phase: 176
slug: backfill
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-17
---

# Phase 176 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (async, `pytest-asyncio`), backend, per-run cloned DB |
| **Config file** | `pyproject.toml` (pytest section) / `tests/conftest.py` (per-run DB template) |
| **Quick run command** | `uv run pytest tests/services/test_eval_queue.py tests/services/test_full_eval_drain.py tests/services/test_maia_engine.py -x` |
| **Full suite command** | `uv run pytest -n auto` |
| **Estimated runtime** | quick ~30–60s · full suite ~2–4 min |

---

## Sampling Rate

- **After every task commit:** Run the quick run command above.
- **After every plan wave:** Run `uv run pytest -n auto` (full backend suite).
- **Before `/gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** ~60 seconds (quick command).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 176-01-01 | 01 | 1 | BACK-01 | — | `best_moves_completed_at` column + partial index declared byte-identically in model and migration (`alembic check` clean) | migration | `uv run alembic upgrade head && uv run alembic check` | ✅ existing | ⬜ pending |
| 176-01-02 | 01 | 1 | BACK-01 (D-04) | — | One-time UPDATE stamps only games that already have a `game_best_moves` row | migration | `alembic upgrade head` / `downgrade -1` / `upgrade head` round-trip | ✅ existing | ⬜ pending |
| 176-01-03 | 01 | 1 | BACK-01 (D-05) | T-DoS (self-inflicted) | `BEST_MOVE_BACKFILL_ENABLED: bool = False` added beside `EVAL_AUTO_DRAIN_ENABLED` | unit | `uv run pytest tests/services/test_eval_queue.py -x` | ❌ W0 | ⬜ pending |
| 176-01-04 | 01 | 1 | BACK-01 | V5 (bound params) | `_claim_tier4_bestmove` picks a PV-complete, best-move-incomplete, non-lichess-eval, non-guest game; excludes lichess-eval (D-03); gated by BOTH flags (D-05) | unit | `uv run pytest tests/services/test_eval_queue.py::TestTier4bBestMoveBackfill -x` | ❌ W0 | ⬜ pending |
| 176-01-05 | 01 | 1 | BACK-01 (guardrail) | — | Maia-absent backend does NOT stamp `best_moves_completed_at` (negative assertion); stamp DOES fire with a session present | unit/integration | `uv run pytest tests/services/test_full_eval_drain.py::TestBestMoveBackfill -x` | ❌ W0 | ⬜ pending |
| 176-01-06 | 01 | 1 | BACK-01 | — | tier-4b claim routes through `_full_drain_tick` end-to-end, self-terminates (no re-draw after stamp) | integration | `uv run pytest tests/services/test_full_eval_drain.py::TestBestMoveBackfill -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task IDs are indicative — the planner sets final plan/task numbering.*

---

## Wave 0 Requirements

- [ ] `_insert_game` test helper (`tests/services/test_eval_queue.py:109-142`) gains an optional `best_moves_completed_at: datetime | None = None` kwarg (mirrors its existing `full_pv_completed_at`/`lichess_evals_at` kwargs).
- [ ] New `TestTier4bBestMoveBackfill` class in `tests/services/test_eval_queue.py` — mirror `TestTier4BlobBackfill`'s shape: null-pick, empty-queue, excludes-guests, excludes-pv-incomplete, **excludes-lichess-eval** (new, D-03-specific), excludes-already-stamped, dispatch-via-claim (after tier-3 AND tier-4-blob return None), gated-off-by-`BEST_MOVE_BACKFILL_ENABLED` (separate from `EVAL_AUTO_DRAIN_ENABLED`), claimed-job-fields.
- [ ] New `TestBestMoveBackfill` class in `tests/services/test_full_eval_drain.py` — mirror 174-07's `TestLichessBestMoveBackfill` end-to-end + double-claim-idempotency shape, for the engine-side (non-lichess) population.
- [ ] Dedicated **Maia-absent guardrail** test — the single most important new test. Mutation-test style: assert the NEGATIVE case explicitly (stamp stays NULL when `maia_engine._session = None`) AND the positive case (stamp fires with a session present). Reuse the `_session` monkeypatch pattern from `tests/services/test_maia_engine.py:33-39`. Per MEMORY.md "Mutation-test gap closures", prove the guardrail by the failing negative assertion, not by symbol presence.

*Migration round-trip + `alembic check` are manual/CLI verifications (174-07 precedent), not pytest tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration up/down/up round-trip + drift-free | BACK-01 (D-01/D-04) | Alembic migrations are verified via the CLI, not pytest (174-07 precedent) | `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head && uv run alembic check` — expect no drift and a clean one-time stamp |
| SC3 coverage-growth observation | BACK-01 (SC3) | Opportunistic, ES-lottery-driven, no ETA/100% promise (tier-4 backfill-measurement precedent) | Snapshot-diff `count(DISTINCT game_id)` in `game_best_moves` (or count of stamped games) over time; growth with `BEST_MOVE_BACKFILL_ENABLED=true` and idle drain running |
| Prod rollout gate | BACK-01 (D-05) | Flag flip is a deliberate, observed operation, NOT part of the code merge | Enable `BEST_MOVE_BACKFILL_ENABLED` in prod only after observing backend RSS/CPU (mirrors 174 D-03b) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
