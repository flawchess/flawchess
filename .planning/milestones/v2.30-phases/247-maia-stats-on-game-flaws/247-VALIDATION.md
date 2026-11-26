---
phase: "247"
slug: "maia-stats-on-game-flaws"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-08"
---

# Phase 247 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (asyncio_mode=auto), per-xdist-worker cloned Postgres |
| **Config file** | `pyproject.toml` (`addopts` ignores `tests/scripts/benchmarks`, `tests/scripts/tagger`) |
| **Quick run command** | `uv run pytest tests/services/test_maia_flaw_stats.py tests/services/test_maia_flaw_scoring.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` (CI runs serially; run the serial suite once before release) |
| **Estimated runtime** | ~30 seconds quick, ~6 minutes full |

---

## Sampling Rate

- **After every task commit:** Run the quick run command plus the touched test file(s)
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full pre-merge gate (CLAUDE.md) green; dev smoke of the backfill (`--db dev --user-id 28 --limit 200`) and a benchmark dry-run
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Filled by the planner per task. Requirement → test map from RESEARCH.md § Validation Architecture:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| D-01 | rank (ties, strict >), entropy → effective moves, top, single legal move, missing best/second, `su==best` | unit (pure) | `uv run pytest tests/services/test_maia_flaw_stats.py -x` | ❌ W0 | ⬜ pending |
| D-01 | migration adds the columns; model matches | integration | `uv run pytest tests/services/test_maia_flaw_scoring.py -k schema -x` | ❌ W0 | ⬜ pending |
| D-04 | `full_policy` sums to 1 over legal moves; `score_move == full_policy[played]`; `start_maia(intra_op_num_threads=1)` loads | unit, real ORT (importorskip) | `uv run pytest tests/services/test_maia_engine.py -x` | ✅ extend | ⬜ pending |
| D-05 | no stamp when Maia absent; no stamp on scorer exception; zero-flaw game stamped | integration | `uv run pytest tests/services/test_maia_flaw_scoring.py -k stamp -x` | ❌ W0 | ⬜ pending |
| D-06 | backfill uses replayed FEN (castling/ep case); `fen_mismatch` counted | integration | `uv run pytest tests/scripts/test_backfill_maia_flaws.py -k replay -x` | ❌ W0 | ⬜ pending |
| D-08 | drain + atomic-submit apply with Maia writes all 8 cols for new AND surviving plies and stamps | integration | `uv run pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py -k maia_flaw -x` | ✅ extend | ⬜ pending |
| D-09 | Maia-absent reclassify: survivors keep values, new plies NULL, deleted rows gone, stamp cleared | integration | `uv run pytest tests/services/test_maia_flaw_scoring.py -k reclassify -x` | ❌ W0 | ⬜ pending |
| D-09/D-11 | `backfill_flaws.py` and opening_cache_repair clear the stamp + print the reminder | integration | `uv run pytest tests/test_backfill_flaws.py tests/scripts/test_opening_cache_repair.py -k maia -x` | ✅ extend | ⬜ pending |
| D-10 | `--db benchmark` resolves; shard residue partitions disjointly and exhaustively | integration | `uv run pytest tests/scripts/test_backfill_maia_flaws.py -x` | ❌ W0 | ⬜ pending |
| D-11 | re-run idempotent (no stamped game re-scored) | integration | `uv run pytest tests/scripts/test_backfill_maia_flaws.py -k rerun -x` | ❌ W0 | ⬜ pending |
| golden | write-path goldens unchanged | regression | `uv run pytest tests/services/test_flaw_upsert_equivalence.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Mutation discipline: prove each D-09 test by reverting the clear/omission and confirming it fails.

---

## Wave 0 Requirements

- [ ] `tests/services/test_maia_flaw_stats.py`: pure stats
- [ ] `tests/services/test_maia_flaw_scoring.py`: scorer read/score/guarded write, guardrail, reclassify semantics
- [ ] `tests/scripts/test_backfill_maia_flaws.py`: selector, shards, replay reasons, idempotence
- [ ] Update `tests/services/test_full_eval_drain.py::test_non_tier4b_claim_still_takes_full_path` (sentinel `_session = object()`) to patch the new inference entry point

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Go-forward scoring ships to prod | D-12 | Deploy is the owner's call | Owner go-ahead, then `/deploy` |
| Full prod backfill + catch-up re-run | D-12 | Multi-hour operator run over the prod tunnel | Orchestrator runs it detached (setsid nohup + Monitor), RESEARCH.md Pattern 6 |
| Prod coverage ≥ 99% with NULL remainder bucketed | D-12 | Prod-only SQL | Pattern 6 coverage SQL via the prod DB MCP |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
