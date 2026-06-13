---
phase: 117
slug: priority-queue-flaw-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 117 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 117-RESEARCH.md §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (per-run isolated Postgres, see tests/conftest.py) |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/services/test_full_eval_drain.py tests/services/test_eval_queue.py -x` |
| **Full suite command** | `uv run pytest -n auto` |
| **Estimated runtime** | quick ~20–40s · full ~30s (parallel) |

---

## Sampling Rate

- **After every task commit:** Run the quick command above
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full suite must be green (+ `ruff`, `ty`)
- **Max feedback latency:** ~40 seconds

---

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| EVAL-04 | `best_move` populated on all non-dedup'd plies | unit | `pytest tests/services/test_full_eval_drain.py -k best_move` | ❌ W0 | ⬜ pending |
| EVAL-04 | `best_move` transplanted via dedup (opening region) | unit | `pytest tests/services/test_full_eval_drain.py -k dedup_best_move` | ❌ W0 | ⬜ pending |
| EVAL-04 | `pv` written only at flaw-adjacent ply+1 | unit | `pytest tests/services/test_full_eval_drain.py -k flaw_pv` | ❌ W0 | ⬜ pending |
| EVAL-06 | `classify_game_flaws` runs after full eval complete | integration | `pytest tests/services/test_full_eval_drain.py -k classify_hook` | ❌ W0 | ⬜ pending |
| EVAL-06 | Oracle count columns written for engine-analyzed game | integration | `pytest tests/services/test_full_eval_drain.py -k oracle_counts` | ❌ W0 | ⬜ pending |
| QUEUE-01 | Tier-1 job picked before tier-3 | unit | `pytest tests/services/test_eval_queue.py -k tier_priority` | ❌ W0 | ⬜ pending |
| QUEUE-02 | Round-robin: user B gets turn after user A | unit | `pytest tests/services/test_eval_queue.py -k round_robin` | ❌ W0 | ⬜ pending |
| QUEUE-02 | TC ordering: classical before bullet within a user | unit | `pytest tests/services/test_eval_queue.py -k tc_ordering` | ❌ W0 | ⬜ pending |
| QUEUE-03 | Tier-1 fan-out: all plies gathered in parallel (outside session) | unit | `pytest tests/services/test_full_eval_drain.py -k gather_outside_session` | Partial (QUEUE-07 AST test) | ⬜ pending |
| QUEUE-05 | Tier-3 derived pick: game with no eval_jobs row | unit | `pytest tests/services/test_eval_queue.py -k tier3_derived` | ❌ W0 | ⬜ pending |
| QUEUE-06 | Lease claimed and reported; expired lease requeued | unit | `pytest tests/services/test_eval_queue.py -k lease_expiry` | ❌ W0 | ⬜ pending |
| QUEUE-08 | Guest games excluded from all tiers | unit | `pytest tests/services/test_eval_queue.py -k guest_exclusion` | ❌ W0 | ⬜ pending |
| D-117-07 | WR-02 gate uses `lichess_evals_at IS NULL` (not `white_blunders`) | unit | `pytest tests/services/test_full_eval_drain.py -k wr02_repointed` | ❌ W0 | ⬜ pending |
| D-117-10 | `lichess_evals_at` backfill marks only pre-existing analyzed games | integration | `pytest tests/test_migration_117.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_eval_queue.py` — new; covers QUEUE-01/02/05/06/08 (tier priority, round-robin, TC ordering, tier-3 derived pick, lease expiry/requeue, guest exclusion)
- [ ] `tests/test_migration_117.py` — new; covers D-117-10 backfill + the four nullable column additions
- [ ] Extend `tests/services/test_full_eval_drain.py` — EVAL-04 (`best_move` + dedup transplant + flaw `pv`), EVAL-06 (classify hook + oracle counts), D-117-07 (WR-02 repoint)
- [ ] Shared fixtures: a flawed-game PGN fixture + a multi-user/multi-TC game set for queue ordering tests (extend `tests/conftest.py` if not already present)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tier-1 fan-out completes in ~10s wall-clock on an idle pool | QUEUE-03 | Wall-clock latency depends on the real prod pool (6–8 workers, 1M nodes); not deterministic in CI | Post-deploy soak: fire the internal tier-1 trigger on an idle prod pool, measure wall-clock from enqueue to all-plies-evaluated; assert ≈10s (per spike 003) |
| Progressive flaw appearance + per-user debounced cache refresh feels live | EVAL-06 / D-117-11 | Cross-surface UX timing; visual | Import a chess.com account, watch flaws/library surfaces populate progressively without a manual refresh; confirm no invalidation storm in logs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
