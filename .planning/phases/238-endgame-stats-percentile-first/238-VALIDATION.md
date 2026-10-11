---
phase: "238"
slug: "endgame-stats-percentile-first"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-11"
---

# Phase 238 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `238-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (async, per-session cloned PG DB) + vitest |
| **Config file** | `tests/conftest.py`, `frontend/vite.config.ts` (test block), `frontend/src/vitest.setup.ts` |
| **Quick run command** | `uv run pytest tests/services/test_endgame_ranked_service.py tests/services/test_endgame_ranked_parity.py -x` / `cd frontend && npx vitest run src/components/endgames` |
| **Full suite command** | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | ~30 s quick, ~10 min full |

---

## Sampling Rate

- **After every task commit:** Run the quick-run file(s) for the touched layer
- **After every plan wave:** `uv run pytest -n auto -x` + `cd frontend && npm run build && npm test -- --run`
- **Before `/gsd-verify-work`:** Full pre-merge gate (CLAUDE.md) green, plus one serial `uv run pytest -x` before release
- **Max feedback latency:** 60 seconds (quick run)

---

## Per-Decision Verification Map

Task IDs are assigned by the planner; each plan task must map to one of these rows.

| Decision | Behavior | Test Type | Automated Command | Plan-Task | File Exists | Status |
|----------|----------|-----------|-------------------|-----------|-------------|--------|
| D-07 | Existing canonical builders byte-identical (golden hash, captured before edits) | unit | `uv run pytest tests/services/test_canonical_slice_sql.py -k golden -x` | 238-01-T1 | ❌ W0 | ⬜ pending |
| D-07 | `ranked_games_sql(tc)` reuses canonical prelude | unit | `uv run pytest tests/services/test_canonical_slice_sql.py -k ranked_games -x` | 238-01-T1 | ❌ W0 | ⬜ pending |
| D-07 | Benchmark-side CDF SQL golden unchanged | unit | `uv run pytest tests/scripts/test_gen_global_percentile_cdf_unchanged.py -x` | 238-01-T1 | ✅ | ⬜ pending |
| D-00b/D-07 | On-read value + n == Stage A/B oracle for all 11 metric families; entry flow actual - expected == achievable | integration | `uv run pytest tests/services/test_endgame_ranked_parity.py -x` | 238-01-T1, T2 | ❌ W0 | ⬜ pending |
| D-00b | WDL/rate consistency from same bucket counts | unit | `uv run pytest tests/services/test_endgame_ranked_service.py -k bucket -x` | 238-01-T3 | ❌ | ⬜ pending |
| D-09/D-10/D-11 | Rank status matrix (ranked / below_floor / unranked / pending, empty sample) | unit | `uv run pytest tests/services/test_endgame_ranked_service.py -k status -x` | 238-01-T3 | ❌ | ⬜ pending |
| D-14 | Zero-game TCs omitted, bullet→classical order | unit | `uv run pytest tests/services/test_endgame_ranked_service.py -k tcs_listed -x` | 238-01-T3 | ❌ | ⬜ pending |
| D-01 | `/endgames/ranked-stats` takes no filter params, auth required | router | `uv run pytest tests/test_endgames_router.py -k ranked -x` | 238-01-T1 | ❌ | ⬜ pending |
| T-238-02 | Two seeded users with distinct games and planted percentiles: each user's `/endgames/ranked-stats` response and `get_ranked_stats` / `fetch_ranked_games` result carry only their own count, value, n and percentile (replaces the V4 scoping test 238-08 deletes) | integration (router + service) | `uv run pytest tests/services/test_endgame_ranked_parity.py -k isolation -x` | 238-01-T1 | ❌ W0 | ⬜ pending |
| D-03 | Per-TC ranked Score Gap over Time + ELO Timeline series; `since` trims output | integration/unit | `uv run pytest tests/services/test_endgame_ranked_parity.py tests/services/test_endgame_ranked_service.py -k "timeline or elo" -x` | 238-02-T1 | ❌ | ⬜ pending |
| D-05/D-06 | Per-TC quintile curve, Clock Gap timeline, type categories from ranked games | unit | `uv run pytest tests/services/test_endgame_ranked_service.py -k "quintile or clock_diff or type_categories" -x` | 238-02-T2 | ❌ | ⬜ pending |
| D-01 (Games tab) | Filtered `/endgames/stats` honours filters | router | `uv run pytest tests/test_endgames_router.py -k EndgameStats -x` | 238-02-T3 | ❌ | ⬜ pending |
| D-00h | Aggregated cross-TC fields absent from schema | schema | `uv run pytest tests/schemas/test_endgames_schema.py -x` | 238-08-T1 | ⚠ rewrite | ⬜ pending |
| D-00h | `/endgames/overview` retired (404) | router | `uv run pytest tests/test_endgames_router.py -k overview_returns_404 -x` | 238-08-T1 | ❌ | ⬜ pending |
| D-04 | Insights filter-free, constant cache key, `endgame_v48`, findings == ranked values | router/service | `uv run pytest tests/test_insights_router.py tests/services/test_insights_service.py tests/services/test_insights_llm.py -x` | 238-04-T1, T2, T3 | ⚠ rewrite | ⬜ pending |
| D-04 | Golden user prompt deliberately regenerated; no scoping caveat in system prompt | unit | `uv run pytest tests/services/test_insights_llm.py -k golden -x && uv run pytest tests/prompts -x` | 238-04-T2, T3 | ⚠ regen | ⬜ pending |
| T-238-10 | A second user's successful llm_logs row matching every other cache key (current prompt version, model, opponent_strength "any") is a cache miss: filter-free `generate_insights(user_id, session)` returns status "fresh" (ported `test_other_users_log_not_returned`, assertion intact; fails when the user_id predicate is removed from the lookup) | integration (service + DB) | `uv run pytest tests/services/test_insights_llm.py -k other_users_log_not_returned -x` | 238-04-T2 | ⚠ port | ⬜ pending |
| D-00a | PercentileBar band/tick/dot colors, uncolored value, no icon overlay | component | `cd frontend && npx vitest run src/components/endgames/stats/PercentileBar.test.tsx` | 238-03-T1 | ❌ | ⬜ pending |
| D-00h/D-12/D-13/D-14 | Synced TC store, default rule, localStorage restore + fallback, no tracking on restore | hook | `cd frontend && npx vitest run src/hooks/__tests__/useEndgameStatsTc.test.ts` | 238-03-T1 | ❌ | ⬜ pending |
| D-00c/D-09/D-11/D-08 | Merged popover: disclosures, greyed stats footer; below-floor / pending / not-ranked slots; no drift state | component | `cd frontend && npx vitest run src/components/endgames/stats/RankedMetricPopover.test.tsx` | 238-03-T2 | ❌ | ⬜ pending |
| D-00g | Compared-to-peers dot plot, rows link to sections, hidden when unranked | component | `cd frontend && npx vitest run src/components/endgames/stats/ComparedToPeersCard.test.tsx` | 238-03-T3 | ❌ | ⬜ pending |
| D-10/D-01/D-00h | Empty ranked sample state copy; ranked hook called without filters; switch sync across sections | component | `cd frontend && npx vitest run src/components/endgames/EndgameStatsTab.test.tsx` | 238-03-T3 | ❌ | ⬜ pending |
| D-00i | Score Gap over Time + ELO Timeline visuals unchanged | component | `cd frontend && npx vitest run src/components/charts/__tests__/EndgameScoreOverTimeChart.test.tsx src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx` | 238-03-T3 | ✅ | ⬜ pending |
| D-00d | Metrics card: no gauge, bracket on WDL bar, rate and WDL from same games | component | `cd frontend && npx vitest run src/components/endgames/stats/MetricsCard.test.tsx` | 238-05-T1 | ❌ | ⬜ pending |
| D-00f/D-06 | Clock timeline + pressure curve: one grey band, neutral marks, no verdict text | component | `cd frontend && npx vitest run src/components/charts/__tests__/EndgameClockDiffOverTimeChart.test.tsx src/components/charts/__tests__/ScoreGapByTimePressureChart.test.tsx` | 238-05-T2 | ⚠ update | ⬜ pending |
| D-00e/D-05 | Type table: grey range, white tick, amber below typical, faded <100 games, stacked on mobile | component | `cd frontend && npx vitest run src/components/endgames/stats/TypeTable.test.tsx` | 238-05-T3 | ❌ | ⬜ pending |
| D-04 (FE) | Insights hook sends no filters, single cached report | hook | `cd frontend && npx vitest run src/hooks/__tests__/useEndgameInsights.test.tsx` | 238-07-T1 | ⚠ rewrite | ⬜ pending |
| D-02 | Filters hidden on Stats, shown on Games, applied state preserved | page | `cd frontend && npx vitest run src/pages/__tests__/Endgames.filterVisibility.test.tsx` | 238-07-T2 | ❌ | ⬜ pending |
| D-00c/D-00d/D-00h | Retired gauge / chip / stat-popover generation deleted with its tests; knip green; no retired component name left in frontend/src, app/ or tests/ (comments included) outside the five files 238-07/238-08 rewrite | static | `npm --prefix frontend run knip` plus the stale-reference grep in 238-06-PLAN.md Task 2 verify | 238-06-T1, T2 | ❌ | ⬜ pending |
| D-00h | Generator and generated zone file name no retired component; zone constants limited to live frontend consumers | static | `uv run python scripts/gen_endgame_zones_ts.py --check` and `npm --prefix frontend run knip` plus the grep in 238-08-PLAN.md Task 2 acceptance | 238-08-T2 | ✅ | ⬜ pending |
| Gate | Full CLAUDE.md pre-merge gate plus the final no-exclusion stale-reference grep over frontend/src, app/, tests/, scripts/ | all | see CLAUDE.md "Pre-merge gate" and 238-09-PLAN.md Task 1 verify | 238-09-T1 | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_canonical_slice_sql.py` — golden hash baseline of all existing builder outputs (capture BEFORE any edit)
- [ ] `tests/services/test_endgame_ranked_parity.py` + seed helper (NULL eval, sub-800, >2× clock, NULL base_time, multi-class spans, out-of-window/out-of-band games, chess.com Daily) + `test_ranked_stats_two_user_isolation` (T-238-02)
- [ ] `tests/services/test_endgame_ranked_service.py` — status matrix, bucket/WDL consistency, TC listing
- [ ] Frontend test files for new components, TC hook, and page filter visibility

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Desktop + mobile layout, popover on tap, stacked type rows, switch sync | D-00c/D-00e/D-00h | Visual layout across viewports | Run dev build, drive via Chrome extension at desktop and mobile widths (Claude runs it per memory) |
| Heavy-account latency of `/endgames/ranked-stats` | D-07 | Needs real dev data volume | Probe `get_ranked_stats` for dev users 7 and 14 (238-02-T3, re-measured in 238-09-T1); flag a median above ~2 s |
| Live Shelly generate on dev with a non-default filter applied | D-04 | Needs the LLM provider and real data | 238-09-T2 step 8: one report, filters untouched, numbers match the page |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
