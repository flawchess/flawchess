---
phase: "248"
slug: "blunder-check-refutation-stats-and-calibration-seed-261108-dk0"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-09"
---

# Phase 248 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Seeded from 248-RESEARCH.md
> "Validation Architecture"; the planner fills the per-task map.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-xdist, real PostgreSQL per worker (`tests/conftest.py` template clone) |
| **Config file** | `pyproject.toml`, `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/services/test_maia_flaw_stats.py tests/services/test_maia_flaw_scoring.py tests/scripts/test_backfill_maia_flaws.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` (plus one serial run before release) |
| **Estimated runtime** | quick ~30 s; full ~110 s with `-n auto` |

---

## Sampling Rate

- **After every task commit:** the quick run command for the touched modules
- **After every plan wave:** `uv run pytest -n auto -x`
- **Before the squash-merge:** the full CLAUDE.md pre-merge gate
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (planner fills) | | | D-01..D-23 | | | | | | ⬜ pending |

Requirement → test map (from research):

| Req | Behavior | Test Type | Command |
|-----|----------|-----------|---------|
| D-01 | columns REAL/SMALLINT + stamp TIMESTAMPTZ nullable, no default; rank strict-greater/ties | migration + unit | `uv run alembic upgrade head && uv run alembic check`; `pytest tests/services/test_maia_flaw_stats.py -k refutation` |
| D-02/D-20 | refutation from ply+1 `best_move`, pv[0] fallback, illegal → reason | DB unit (`fake_full_policy`) | `pytest tests/services/test_maia_flaw_scoring.py -k refutation` |
| D-03 | only user-side blunders scored, both user colors | DB unit | same |
| D-04 | Elo = blunderer's pinned Elo (spy on `full_policy`) | DB unit | same |
| D-05 | post board from replay, castling/ep exact, target board not mutated | DB unit | same |
| D-07 | drain, atomic submit, blob submit write the pair + both stamps | integration | `pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py -k maia` |
| D-08 | no-Maia reclassify keeps survivors, new rows NULL, both stamps cleared | DB unit + mutation proof | `pytest tests/services/test_maia_flaw_scoring.py -k reclassify` |
| D-09/D-22 | Maia absent → no stamp; zero-blunder game stamped; fingerprint covers ply+1 inputs | DB unit | `-k "stamp or fingerprint"` |
| D-10 | `--mode refutation` selector, writes 2 cols + stamp, rerun selects nothing, shard partition | script test | `pytest tests/scripts/test_backfill_maia_flaws.py` |
| D-13..D-16 | miss-case boundaries, hazard weights, herring runs, window fit, cap math | pure unit | `pytest tests/scripts/test_blunder_check_calibration.py` |
| D-13 | stored-vs-recomputed flaw control ≥ 99% | dev smoke | `uv run python scripts/blunder_check_calibration.py --db dev ...` |
| D-17 | arrow-oddness runs with real ORT | dev smoke | small `--oddness-sample` |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/scripts/test_blunder_check_calibration.py`: pure report functions (no DB)
- [x] Prod NULL-budget probe: done 2026-11-09 (CONTEXT D-21), structural NULLs ≈ 0.2% with the pv fallback
- [ ] Fixtures: user blunder as final move (pv only), stalemating blunder, white and black users with distinct ratings, opponent blunder at the adjacent ply; unique `_TEST_USER_ID`, `finally` cleanup; backfill tests scoped with `--user-id`
- [ ] Mutation proofs: drop the user-side check, Elo from `post.turn`, drop the refutation from the fingerprint, add a refutation key to `flaw_record_to_row`, clear only the base stamp; each must fail a test

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Prod coverage ≥ 99% with reason buckets | D-11 | prod data, orchestrator MCP only | run the research "Coverage SQL (D-11)" after backfill + catch-up |
| Calibration report and spot-check sample written and committed | D-18 | prod run over the tunnel | prod run of the report script; file committed under `reports/` |
| Deploy go-ahead | D-11 | owner's call | checkpoint before deploy |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
