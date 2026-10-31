---
phase: "243"
slug: "out-of-the-opening-worse-better-rates"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-31"
---

# Phase 243 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `243-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (asyncio, per-session cloned Postgres DB) + vitest (`npm test` = `vitest run`) |
| **Config file** | `pyproject.toml` / `tests/conftest.py`; `frontend/vite.config.ts` |
| **Quick run command** | `uv run pytest tests/services/test_canonical_slice_sql.py tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py tests/scripts/test_gen_global_percentile_cdf_unchanged.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |
| **Estimated runtime** | ~30 s quick; full backend suite several minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick run command plus the task's own new test file
- **After every plan wave:** `uv run pytest -n auto -x`; frontend `npm test -- --run && npm run build`
- **Before `/gsd-verify-work`:** Full pre-merge gate (CLAUDE.md) green, plus a serial run of the touched DB test files
- **Max feedback latency:** ~60 seconds per task

---

## Per-Task Verification Map

Task IDs filled by the planner (2026-10-31). Each "❌ W0" file is created test-first inside the task that owns it.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 243-01-T1 | 01 | 1 | D-01/D-02 metric + edge cases | — | N/A | DB integration | `uv run pytest tests/services/test_opening_out_rates_parity.py -x` | ❌ W0 (created in T1) | ⬜ pending |
| 243-01-T1 | 01 | 1 | D-05 builder byte-identity | T-243-01 | f-string only Literals/int constants; user_id bindparam | unit | `uv run pytest tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py -x` | ✅ extend | ⬜ pending |
| 243-03-T2 | 03 | 2 | D-05 three-path parity | T-243-08 | N/A | DB integration | `uv run pytest tests/services/test_opening_out_rates_parity.py -k three_path -x` | ✅ (created in 243-01-T1) | ⬜ pending |
| 243-02-T1 | 02 | 2 | D-04 colour-aware CDF ranking + goldens | T-243-05 | benchmark-DB target guard | unit | `uv run pytest tests/scripts/test_gen_global_percentile_cdf_unchanged.py tests/scripts/test_gen_global_percentile_cdf_opening_out.py -x` | ❌ W0 (created in T1) | ⬜ pending |
| 243-02-T1, 243-02-T3 | 02 | 2 | Scoped regen merge mode, non-opening rows unchanged | T-243-06 | TSV diff vs main before commit | unit + diff | `uv run pytest tests/scripts/test_cohort_cdf_seed_artifact.py -x` | ✅ extend | ⬜ pending |
| 243-01-T2, 243-01-T3 | 01 | 1 | Storage migration (colour column, PK, TEXT + CHECK) | T-243-03 | dead-label delete logged | DB integration | `uv run pytest tests/integration/test_alembic_migrations.py tests/integration/test_benchmark_metric_check.py -x` | ✅ update (check test renamed from `test_benchmark_metric_enum.py`) | ⬜ pending |
| 243-01-T3, 243-03-T2 | 01, 03 | 1, 2 | Repo colour rows; Endgames read sees only 'all' | T-243-10 | keyword-only user_id | DB integration | `uv run pytest tests/repositories/test_user_benchmark_percentiles_repository.py -x` | ✅ extend | ⬜ pending |
| 243-03-T1, 243-03-T2 | 03 | 2 | Stage B opening family; endgame parity unchanged | T-243-09 | per-TC Sentry isolation | unit + DB | `uv run pytest tests/services/test_user_benchmark_percentiles_service.py tests/services/test_endgame_ranked_parity.py -x` | ✅ extend | ⬜ pending |
| 243-04-T2 | 04 | 3 | D-07/D-08 TC collapse, 95% gate, rank status | — | N/A | unit | `uv run pytest tests/services/test_opening_out_stats_service.py -x` | ❌ W0 (created in T2) | ⬜ pending |
| 243-04-T1 | 04 | 3 | API endpoint auth + schema | T-243-11, T-243-12 | user_id from `current_active_user` only | router | `uv run pytest tests/routers/test_openings_out_of_opening.py -x` | ❌ W0 (created in T1) | ⬜ pending |
| 243-01-T1, 243-02-T2/T3 | 01, 02 | 1, 2 | Per-eval-source check (not a gate) | — | N/A | DB unit + report | `uv run pytest tests/services/test_opening_out_rates_parity.py -k eval_source` (code path); report numbers in 243-02-SUMMARY | ❌ W0 (created in 243-01-T1) | ⬜ pending |
| 243-05-T1 | 05 | 4 | UI section card states | T-243-15 | React text nodes only | component | `npm --prefix frontend test -- src/components/openings/stats/__tests__/OutOfOpeningSection.test.tsx` | ❌ W0 (created in T1) | ⬜ pending |
| 243-05-T2 | 05 | 4 | D-09..D-12 popover content + disclosures | T-243-14 | fixed-literal popover testids | component | `npm --prefix frontend test -- src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx` | ❌ W0 (created in T2) | ⬜ pending |
| 243-05-T2, 243-05-T3 | 05 | 4 | Analytics target + cache invalidation | T-243-16 | N/A | unit | `npm --prefix frontend test -- src/lib/__tests__/analytics.test.ts src/pages/__tests__/Import.endgameOverviewInvalidation.test.ts` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_opening_out_rates_parity.py` — seeded edge-case user, every non-guest `Game` insert cleaned up in `finally`, benchmark selection rows for the CDF path
- [ ] `tests/services/test_opening_out_stats_service.py` — pure collapse/gate/status
- [ ] `tests/routers/test_openings_out_of_opening.py`
- [ ] `tests/scripts/fixtures/global_percentile_cdf/opening_{worse,better}_rate__{bullet,blitz,rapid,classical}.sql`
- [ ] `frontend/src/components/openings/stats/__tests__/OutOfOpeningSection.test.tsx`, `OutOfOpeningPopover.test.tsx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Scoped CDF regen against the benchmark DB (243-02-T2, orchestrator inline) | Peer basis | Needs `bin/benchmark_db.sh start`, ~10 min run | Run the regen with `--metrics` merge mode and the pinned snapshot date; 243-02-T3 confirms non-opening CDF rows byte-identical to main |
| Visual check of the section on the Stats tab (243-05-T1 human-check) | Frontend | Layout under sticky colour switch | Browser UAT on dev build, both colours, phone + desktop |
| Prod rollout (deploy, seed CDF, backfill) | Rollout | Owner-run prod ops | deploy → seed CDF in container → `uv run python -m scripts.archive.backfill_user_percentiles --target prod --skip-anchors` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
