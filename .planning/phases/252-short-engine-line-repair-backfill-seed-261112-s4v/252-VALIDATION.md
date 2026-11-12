---
phase: "252"
slug: "short-engine-line-repair-backfill-seed-261112-s4v"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-12"
---

# Phase 252 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `252-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (`asyncio_mode = "auto"`), xdist locally |
| **Config file** | `pyproject.toml` (`addopts` ignores `tests/scripts/benchmarks` and `tests/scripts/tagger`) |
| **Quick run command** | `uv run pytest tests/test_eval_worker_endpoints.py tests/services/test_eval_apply.py tests/scripts/test_repair_short_lines.py -n auto -q -k "flaw_blob or blob or repair"` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | quick ~60 seconds, full suite several minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched area
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full pre-merge gate (CLAUDE.md) green, plus a serial run of the eval-lane test files
- **Max feedback latency:** ~60 seconds (quick command)

---

## Per-Task Verification Map

Task IDs are filled in by the planner; the rows below are the behaviors each plan must map onto.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 252-01-T2 | 01 | 1 | S1 / D-01 | T-252-02 | `root_moves` reaches `protocol.analysis`; default None unchanged | unit | `uv run pytest tests/services/test_engine_bound_lines.py -q` | ✅ extend | ⬜ pending |
| 252-01-T1 | 01 | 1 | S1 / D-01 | T-252-02 | Real pinned search: `pv[0] == pin`, more than 2 plies | integration (real Stockfish) | `uv run pytest tests/services/test_engine_nodes.py -q -k Pinned` | ✅ extend | ⬜ pending |
| 252-01-T1 | 01 | 1 | S1 / D-01 | T-252-02 | Tracer: one short line re-searched pinned and written end to end | DB + real Stockfish | `uv run pytest tests/scripts/test_repair_short_lines.py -q -k tracer` | ❌ W0 (created in T1) | ⬜ pending |
| 252-01-T2 | 01 | 1 | S1 / D-02 | T-252-02 | NULL or illegal `best_move` gives a free search and writes `best_move`; a legal one is never overwritten | unit + DB | `uv run pytest tests/scripts/test_repair_short_lines.py -q` | ❌ W0 | ⬜ pending |
| 252-01-T2 | 01 | 1 | S1 / S3 / D-04 / D-13 | T-252-02 | Mate (row k-1) and game-over endings excluded; `[]` sentinels at ply <= 20; guests excluded; newest first; guard skip on concurrent change; dry-run writes nothing | DB integration (fake evaluator) | `uv run pytest tests/scripts/test_repair_short_lines.py -q` | ❌ W0 | ⬜ pending |
| 252-01-T3 | 01 | 1 | D-10 | T-252-01, T-252-03 | Gates trip strictly above thresholds; pilot slice; failed batch exits 3; lane scope; report | unit + DB | `uv run pytest tests/scripts/test_repair_short_lines.py -q` | ❌ W0 | ⬜ pending |
| 252-02-T1 | 02 | 1 | S2 / D-03 | T-252-04 | Lease covers only the NULL line; submit writes only that line and its 4 tag columns; other blob byte-identical | endpoint integration | `uv run pytest tests/test_eval_worker_endpoints.py -n auto -q -k blob` | ✅ extend | ⬜ pending |
| 252-02-T2 | 02 | 1 | S2 / D-03 | T-252-04, T-252-05 | Sentinel/over-cap fill-NULL-only; `blobs_completed_at` stays NULL while a line is NULL; both-NULL regression; foreign-line token 422 | endpoint + DB | `uv run pytest tests/test_eval_worker_endpoints.py tests/services/test_eval_apply.py -n auto -q -k "blob or fill_null or refresh_blobs"` | ✅ extend | ⬜ pending |
| 252-03-T1 | 03 | 2 | S2 / D-12, D-05, D-06 | T-252-06 | A tier-4 server-pool drain tick leaves `eval_cp`, `eval_mate`, the flaw set and `game_best_moves` untouched (mutation-checked) | integration | `uv run pytest tests/services/test_full_eval_drain.py -n auto -q -k Tier4BlobDrainTick` | ✅ extend | ⬜ pending |
| 252-03-T3 | 03 | 2 | D-15 | T-252-23 | Version-2 workers get 204 on every lane that could reach a re-walk game; entry lane cannot claim it; `/atomic-lease` 204s tier-4/4b claims (mutation-checked) | endpoint integration | `uv run pytest tests/test_eval_worker_endpoints.py -n auto -q -k MixedFleetRewalkSafety` | ✅ extend | ⬜ pending |
| 252-04-T1 | 04 | 2 | S2 / D-11, D-03 | T-252-08 | Feeder NULLs only the repaired line with SQL NULL; the per-line lease then covers only it | DB integration | `uv run pytest tests/scripts/test_repair_short_lines.py -q -k feed_tracer` | ❌ W0 | ⬜ pending |
| 252-04-T2 | 04 | 2 | D-11, D-04, D-10, D-15 | T-252-08, T-252-09 | Newest first, low-water windows, idempotent, repair-cursor fence, 8-week gate on measured drain, eval-fingerprint guard, NULL-window report | DB integration | `uv run pytest tests/scripts/test_repair_short_lines.py -q -k "feed or status"` | ❌ W0 | ⬜ pending |
| 252-04-T3 | 04 | 2 | S5 / D-05, D-10 | — | Flip function: stored vs re-searched severity, mate ladder routed; control arm; read-only; 2% gate | unit + DB | `uv run pytest tests/scripts/test_repair_short_lines.py -q -k flip` | ❌ W0 | ⬜ pending |
| 252-09-T1 | 09 | 7 | S4 | T-252-21 | §5 numbers after the refresh | gate (explicit path) | `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` | ✅ regenerate | ⬜ pending |
| 252-09-T3 | 09 | 7 | S4 | T-252-21 | Zone registry pins | unit | `uv run pytest tests/services/test_tactic_delta_zones.py -q` | ✅ update | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/scripts/test_repair_short_lines.py` — selector, pin, guard, dry-run, re-walk ordering, flip function
- [ ] `tests/services/engine_fakes.py` — `ScriptedAnalysisProtocol.analysis` records `root_moves`
- [ ] Worktree setup: `uv sync --group maia-inference` and `cd frontend && npm ci`

Test conventions: every test inserting a non-guest `Game` deletes it in `finally` (global eval-lottery isolation); real-Stockfish tests use a generous timeout constant in the test and never patch the prod constant; each gap closure is proven by reverting the fix and watching the test fail.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 1% pilot gates on prod (still-short share, throughput, failed batches, connections and latency, flip rate) | D-10 | Runs against the live prod DB with real engines; one-way writes | Plan 06 (orchestrator-inline): read-only preview, one-way checkpoint, pilot chained into the full run; each report states gate values against named thresholds |
| Full prod line repair and re-walk complete on the fleet as it is | S1, S2, D-15 | Multi-day/multi-week operator runs | Plans 06-07: final reports, feed eval-fingerprint guard, residual short-line and 1-element-blob shares re-measured through the prod MCP |
| Benchmark repair, re-walk, retag and §5 zone refresh | S4 | Long benchmark-DB runs and an owner check on the changed `has_zone` set | Plans 07 (repair), 08 (re-walk, retag), 09 (§5 fast path, owner checkpoint, registry) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
