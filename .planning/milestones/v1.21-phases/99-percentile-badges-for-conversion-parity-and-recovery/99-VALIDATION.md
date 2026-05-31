---
phase: 99
slug: percentile-badges-for-conversion-parity-and-recovery
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-30
---

# Phase 99 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest), `frontend/vite.config.ts` (vitest) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest && (cd frontend && npm test -- --run)` |
| **Estimated runtime** | ~60–90 seconds (backend) + ~30 seconds (frontend) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q && (cd frontend && npm run lint && npm test -- --run)`
- **After every plan wave:** Run `uv run pytest && (cd frontend && npm test -- --run)`
- **Before `/gsd-verify-work`:** Full suite must be green (backend + frontend)
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

Phase 99 has no formal requirement IDs (endgame stats UX refinement). Coverage is driven by the 5 Success Criteria (SC-1..SC-5) from CONTEXT.md.

| SC | Behavior | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|----|----------|------------|-----------------|-----------|-------------------|-------------|--------|
| SC-2 | New rate builders (`conv_rate`/`parity_rate`/`recovery_rate` per TC) use the SAME pooled-per-user SQL for CDF construction and per-user lookup — drift structurally impossible | T-99-SQLi / — | `tc` is a 4-value Literal; no user string in SQL | unit | `uv run pytest tests/services/test_canonical_slice_sql.py -x` | ❌ W0 (extend) | ⬜ pending |
| SC-1 | Rate chip suppresses below the reused ≥30-span inclusion floor, per (metric, TC) | — | N/A | unit | `uv run pytest tests/services/test_canonical_slice_sql.py -x` | ❌ W0 (extend) | ⬜ pending |
| SC-2 | 12 new ENUM members present in both Postgres type and the SAEnum descriptor | — | N/A | unit | `uv run pytest tests/models/test_user_benchmark_percentile.py -x` | ❌ W0 (extend) | ⬜ pending |
| SC-3 | Cohort CDF regen produces non-empty tables for the 12 new metrics; regen report archived | — | N/A | manual (benchmark DB) | `bin/benchmark_db.sh start && uv run python scripts/gen_global_percentile_cdf.py` | ✅ | ⬜ pending |
| SC-2 | `rate_percentile` threads onto each per-TC block as a SEPARATE field from the existing gap `block.percentile` (D-01) | T-99-IDOR / — | `fetch_for_user(user_id=current_user.id)` unchanged | unit | `uv run pytest tests/services/test_endgame_service.py -x` | ❌ W0 (extend) | ⬜ pending |
| SC-1 / SC-4 | Title-line rate chip renders when percentile+anchor present, suppresses when null; tooltip bullet 1 is TC-scoped + names the raw rate noun (D-08) | — | N/A | frontend unit | `cd frontend && npm test -- --run EndgameMetricsByTcCard` | ❌ W0 (extend) | ⬜ pending |
| SC-5 | Backfill writes rows for the 12 new metrics on dev DB | T-99-ENV / — | `_assert_target_safe` port-check covers new metrics | manual | `uv run python scripts/backfill_user_percentiles.py` (dev) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_canonical_slice_sql.py` — extend with 3 new rate-builder tests (SC-1: floor `HAVING` clause; SC-2: source-parity between CDF and per-user paths; metric_value formula = wins/spans, score/spans, saves/spans)
- [ ] `tests/models/test_user_benchmark_percentile.py` — assert the 12 new ENUM members exist in the SAEnum descriptor (SC-2)
- [ ] `tests/services/test_endgame_service.py` — extend fixture/assertions for the new `rate_percentile` field on `PerTcBucketStats`, distinct from `percentile` (SC-2 / D-01)
- [ ] `frontend/src/components/charts/EndgameMetricsByTcCard.test.tsx` — extend with title-line rate-chip render + null-suppression assertions and TC-scoped tooltip content (SC-1 / SC-4)

---

## Manual-Only Verifications

| Behavior | SC | Why Manual | Test Instructions |
|----------|----|------------|-------------------|
| Cohort CDF regen for 12 new metrics | SC-3 | Requires benchmark DB (port 5433) and is a generation step, not a unit assertion | `bin/benchmark_db.sh start`, run `scripts/gen_global_percentile_cdf.py`, confirm non-empty CDF tables for the new metrics, archive the regen report |
| Backfill dev → prod-via-tunnel | SC-5 | Writes DB rows; prod requires `bin/prod_db_tunnel.sh` and sign-off (D-11) | Run backfill against dev; verify row counts for the 12 new metrics; prod run only after user sign-off |
| Desktop + mobile chip parity | SC-1 | Visual — confirm `MetricBlock` (shared renderer) shows the title-line chip on both layouts | Manual UAT on dashboard endgame metrics cards, narrow + wide viewport |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
