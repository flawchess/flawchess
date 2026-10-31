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

Task IDs are filled by the planner; rows below are keyed by decision until then.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | D-01/D-02 metric + edge cases | — | N/A | DB integration | `uv run pytest tests/services/test_opening_out_rates_parity.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-05 builder byte-identity | T-243 SQLi | f-string only Literals/int constants; user_id bindparam | unit | `uv run pytest tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py -x` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | D-05 three-path parity | — | N/A | DB integration | `uv run pytest tests/services/test_opening_out_rates_parity.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-04 colour-aware CDF ranking + goldens | — | N/A | unit | `uv run pytest tests/scripts/test_gen_global_percentile_cdf_unchanged.py tests/scripts/test_gen_global_percentile_cdf_pooled.py -x` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | Scoped regen merge mode | — | N/A | unit | `uv run pytest tests/scripts/test_cohort_cdf_seed_artifact.py -x` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | Storage migration (colour column, PK, CHECK/enum) | — | N/A | DB integration | `uv run pytest tests/integration/test_alembic_migrations.py tests/integration/test_benchmark_metric_enum.py -x` | ✅ update | ⬜ pending |
| TBD | TBD | TBD | Repo colour filter (Endgames unaffected) | — | N/A | DB integration | `uv run pytest tests/repositories/test_user_benchmark_percentiles_repository.py -x` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | Stage B opening family; endgame parity unchanged | — | N/A | unit + DB | `uv run pytest tests/services/test_user_benchmark_percentiles_service.py tests/services/test_endgame_ranked_parity.py -x` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | D-07/D-08 TC collapse, 95% gate, rank status | — | N/A | unit | `uv run pytest tests/services/test_opening_out_stats_service.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | API endpoint auth + schema | T-243 V4 | user_id from `current_active_user` only | router | `uv run pytest tests/routers/test_openings_out_of_opening.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Per-eval-source check (not a gate) | — | N/A | DB unit + report | `uv run pytest tests/services/test_opening_out_rates_parity.py -k eval_source` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UI section card states | — | N/A | component | `cd frontend && npx vitest run src/components/openings/stats/__tests__/OutOfOpeningSection.test.tsx` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-09..D-12 popover content + disclosures | — | N/A | component | `cd frontend && npx vitest run src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Analytics target + cache invalidation | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts src/pages/__tests__` | ✅ extend | ⬜ pending |

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
| Scoped CDF regen against the benchmark DB | Peer basis | Needs `bin/benchmark_db.sh start`, ~10 min run | Run the regen with `--metrics` merge mode and the pinned snapshot date; confirm non-opening CDF rows byte-identical |
| Visual check of the section on the Stats tab | Frontend | Layout under sticky colour switch | Browser UAT on dev build, both colours, phone + desktop |
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
