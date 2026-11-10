---
phase: "248"
slug: "blunder-check-refutation-stats-and-calibration-seed-261108-dk0"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
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
| 248-01-T1 | 01 | 1 | D-01, D-02, D-20, D-22 | T-248-02 | three nullable columns, both stamps written together | migration + DB tracer | `uv run alembic upgrade head && uv run alembic check`; `uv run pytest tests/services/test_maia_flaw_scoring.py -k "refutation_tracer or schema" -x` | ✅ | ✅ green |
| 248-01-T2 | 01 | 1 | D-03, D-04, D-05, D-09, D-20 | T-248-01, T-248-02 | illegal/malformed refutation never reaches inference; fingerprint covers ply+1 inputs | pure + DB unit, mutation proofs | `uv run pytest tests/services/test_maia_flaw_stats.py tests/services/test_maia_flaw_scoring.py -x` | ✅ | ✅ green |
| 248-01-T3 | 01 | 1 | D-07, D-08 | T-248-02 | no-Maia reclassify preserves by omission, clears both stamps | DB unit + lane integration | `uv run pytest tests/services/test_maia_flaw_scoring.py -k reclassify -x`; `uv run pytest tests/services/test_full_eval_drain.py -k "maia_flaw or non_tier4b" -x`; `uv run pytest tests/test_eval_worker_endpoints.py -k maia -x` | ✅ | ✅ green |
| 248-02-T1 | 02 | 1 | D-13, D-16 | T-248-04 | ES from the classifier's own pass | pure tracer | `uv run pytest tests/scripts/test_blunder_check_metrics.py -x` | ✅ | ✅ green |
| 248-02-T2 | 02 | 1 | D-14, D-15, D-16, D-23 | T-248-04 | boundary rules pinned | pure unit, mutation proofs | `uv run pytest tests/scripts/test_blunder_check_metrics.py -x` | ✅ | ✅ green |
| 248-03-T1 | 03 | 2 | D-10, D-22 | T-248-05, T-248-07 | refutation mode writes only the pair + its stamp | script tracer | `uv run pytest tests/scripts/test_backfill_maia_flaws.py -k refutation_mode -x` | ✅ | ✅ green |
| 248-03-T2 | 03 | 2 | D-03, D-05, D-09, D-10 | T-248-06, T-248-07 | selector constants, bound params, own-stamp require_unstamped | script tests + dev smoke | `uv run pytest tests/scripts/test_backfill_maia_flaws.py tests/services/test_maia_flaw_scoring.py -x`; `uv run python scripts/backfill_maia_flaws.py --db dev --status --mode refutation --user-id 28` | ✅ | ✅ green |
| 248-04-T1 | 04 | 2 | D-13, D-14 | T-248-08 | report session is read-only (write raises) | DB tracer + dev run | `uv run pytest tests/scripts/test_blunder_check_calibration.py -x`; dev run of `scripts/blunder_check_calibration.py` | ✅ | ✅ green |
| 248-04-T2 | 04 | 2 | D-14, D-15, D-16, D-23 | T-248-09, T-248-10 | aggregates only, one connection, statement_timeout | render unit + dev run + cache diff | `uv run pytest tests/scripts/test_blunder_check_calibration.py tests/scripts/test_blunder_check_metrics.py -x` | ✅ | ✅ green |
| 248-05-T1 | 05 | 3 | D-17 | T-248-12 | Maia absent -> exit 3, no partial report | unit + real-ORT dev smoke | `uv run pytest tests/scripts/test_blunder_check_calibration.py -k "oddness or maia" -x` | ✅ | ✅ green |
| 248-05-T2 | 05 | 3 | D-18 | T-248-11 | spot-check holds no FlawChess user identifiers | unit + dev smoke + determinism diff | `uv run pytest tests/scripts/test_blunder_check_calibration.py tests/scripts/test_blunder_check_metrics.py -x` | ✅ | ✅ green |
| 248-06-T1 | 06 | 4 | D-11, D-12 | T-248-13, T-248-14 | owner go-ahead; 247-07 ended | checkpoint | manual (owner answer) | n/a | ✅ green |
| 248-06-T2 | 06 | 4 | D-11, D-19 | T-248-13 | deploy only via /deploy | gate + prod MCP | `git rev-list --left-right --count main...origin/main`; `uv run python scripts/backfill_maia_flaws.py --db prod --status --mode refutation` | n/a | ✅ green |
| 248-06-T3 | 06 | 4 | D-11 | T-248-14 | connection headroom recorded | prod MCP + Sentry | `git log origin/production -1 --format=%H` | n/a | ✅ green |
| 248-07-T1 | 07 | 5 | D-10, D-12 | T-248-15, T-248-16 | bounded slice before the long run | prod slice + MCP | `PYTHONUNBUFFERED=1 uv run python -u scripts/backfill_maia_flaws.py --db prod --mode refutation --shard 0 --num-shards 9 --limit 50` | n/a | ✅ green |
| 248-07-T2 | 07 | 5 | D-10 | T-248-15 | 9 shards max, no overlap | detached run | `grep -c "EXIT=0" temp/maia-refutation-backfill/prod-full.log` | n/a | ✅ green |
| 248-07-T3 | 07 | 5 | D-11, D-20, D-21 | T-248-16 | coverage >= 99.000 with buckets | catch-up + MCP coverage SQL | `grep -c "pct_scored" reports/maia-flaws-backfill/prod-refutation-coverage.md` | n/a | ✅ green |
| 248-08-T1 | 08 | 6 | D-13..D-17 | T-248-17 | read-only prod session | detached prod run | `grep -c "EXIT=0" temp/blunder-check/prod-run.log` | n/a | ✅ green |
| 248-08-T2 | 08 | 6 | D-11, D-18, D-19, D-23 | T-248-18 | committed files hold no user identifiers | committed report + spot-check | `git ls-files --error-unmatch reports/blunder-check/blunder-check-calibration-*.md reports/blunder-check/spot-check-*.md` | n/a | ✅ green |

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

- [x] `tests/scripts/test_blunder_check_calibration.py`: pure report functions (no DB)
- [x] Prod NULL-budget probe: done 2026-11-09 (CONTEXT D-21), structural NULLs ≈ 0.2% with the pv fallback
- [x] Fixtures: user blunder as final move (pv only), stalemating blunder, white and black users with distinct ratings, opponent blunder at the adjacent ply; unique `_TEST_USER_ID`, `finally` cleanup; backfill tests scoped with `--user-id`
- [x] Mutation proofs: drop the user-side check, Elo from `post.turn`, drop the refutation from the fingerprint, add a refutation key to `flaw_record_to_row`, clear only the base stamp; each must fail a test

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Prod coverage ≥ 99% with reason buckets | D-11 | prod data, orchestrator MCP only | run the research "Coverage SQL (D-11)" after backfill + catch-up |
| Calibration report and spot-check sample written and committed | D-18 | prod run over the tunnel | prod run of the report script; file committed under `reports/` |
| Deploy go-ahead | D-11 | owner's call | checkpoint before deploy |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-10 (343 tests green across the 7 phase test files, `alembic check` clean, mutation proofs in 248-01-SUMMARY.md; prod legs evidenced in 248-06..08 SUMMARYs)

## Validation Audit 2026-11-10

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
