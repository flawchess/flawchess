---
phase: "239"
slug: "library-stats-you-vs-opponents"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-12"
---

# Phase 239 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ pytest-asyncio, xdist) backend; vitest frontend |
| **Config file** | `pyproject.toml` (benchmark gates `--ignore`d by default); `frontend/vite.config.ts` test block |
| **Quick run command** | `uv run pytest tests/services/test_flaw_comparison.py tests/services/test_tactic_comparison_service.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |
| **Estimated runtime** | ~240 seconds (full); ~30 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run the matching row's command from the map below
- **After every plan wave:** Backend `uv run pytest -n auto -x`; frontend `npm test -- --run && npm run build && npm run knip`
- **Before `/gsd-verify-work`:** Full pre-merge gate from CLAUDE.md must be green, plus `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` once after Plan 01
- **Max feedback latency:** 60 seconds per task command

---

## Per-Task Verification Map

Task IDs are filled in once plans exist; rows are keyed by decision.

| Decision | Plan | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|------|----------|-----------|-------------------|-------------|--------|
| D-06/D-07/D-08 | 01 | §5 base uses `benchmark_selection` (classical+rapid, completion predicates incl. blobs); 12 flaw + tactic metric keys; no combos/flaw_rate | unit (SQL string) | `uv run pytest tests/scripts/test_chapter5_sql.py -x` | ❌ W0 | ⬜ pending |
| D-06/D-07 | 01 | Numbers reproduce the narrated report | integration (benchmark DB, on demand) | `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` | ✅ (regenerate EXPECTED_*) | ⬜ pending |
| D-08/D-09/D-10 | 01 | blitz/bullet → rapid zones; registry has exactly 12 flaw metrics; lookup per TC | unit | `uv run pytest tests/services/test_flaw_delta_zones.py -x` | ❌ W0 | ⬜ pending |
| D-11/D-06 | 01 | Tactic registry covers all families × Missed/Allowed; unviable → `has_zone=False` | unit | `uv run pytest tests/services/test_tactic_delta_zones.py -x` | ❌ W0 | ⬜ pending |
| D-02/D-03 | 02 | `tcs[]` lists only TCs with ≥1 analyzed game inside the TC filter; below-gate TC still has bullets | integration | `uv run pytest tests/services/test_flaw_comparison.py -x` | ✅ rewrite | ⬜ pending |
| D-00e/D-00f | 02 | 12 bullets (blunder, mistake, 10 tags), no combos/flaw_rate | integration | `uv run pytest tests/services/test_flaw_comparison.py -x` | ✅ rewrite | ⬜ pending |
| D-00h/D-11 | 02 | Tactic bullets per 100 games, fixed order, all families, no top-6; zones from registry | integration | `uv run pytest tests/services/test_tactic_comparison_service.py -x` | ✅ rewrite | ⬜ pending |
| D-12 | 02 | `low_sample` true below 40 you+opp flaws, false at 40 | integration | same two files | ❌ new tests | ⬜ pending |
| D-00k | 02 | `trend_by_tc` per TC; `analyzed_n` kept | integration | `uv run pytest tests/services/test_library_service.py -x -k flaw_stats` | ✅ extend | ⬜ pending |
| API | 02 | Router shapes, 422 on bad params | integration | `uv run pytest tests/test_library_router.py -x` | ✅ update | ⬜ pending |
| D-00a/D-00b | 03 | gap position (centre, band edges, saturation, zero-width guards), gap words, verdict | unit | `cd frontend && npm test -- --run src/lib/__tests__/gapBar.test.ts` | ❌ W0 | ⬜ pending |
| D-00a/D-11/D-12 | 03 | GapBar band/no band, blue dot when faded/zoneless | component | `cd frontend && npm test -- --run src/components/library/stats/__tests__/GapBar.test.tsx` | ❌ W0 | ⬜ pending |
| D-00c | 03 | Gap popover sections, "Too few flaws to call it", no range line when zoneless, CI/p footer | component | `cd frontend && npm test -- --run src/components/library/stats/__tests__/GapPopover.test.tsx` | ❌ W0 | ⬜ pending |
| D-02/D-04/D-05 | 03 | Default TC rule, separate key, stored TC ignored when not offered | hook | `cd frontend && npm test -- --run src/hooks/__tests__/useLibraryStatsTc.test.ts` | ❌ W0 | ⬜ pending |
| D-00g/D-13 | 03 | Top 3 per side by band-width distance; faded/zoneless excluded; Typical line; empty copy | component | `cd frontend && npm test -- --run src/components/library/stats/__tests__/WhatStandsOut.test.tsx` | ❌ W0 | ⬜ pending |
| D-00f/D-03 | 03 | Four cards, tag order, hints, gate slot "(12 of 20)" | component | `cd frontend && npm test -- --run src/components/library/__tests__/FlawComparisonGrid.test.tsx` | ✅ rewrite | ⬜ pending |
| D-00h/D-00i/D-03 | 03 | Three tables in TACTIC_GROUPS order, zero-count motifs under table, Advanced collapsed with hint | component | `cd frontend && npm test -- --run src/components/library/__tests__/TacticComparisonGrid.test.tsx` | ✅ rewrite | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/scripts/test_chapter5_sql.py` — DB-free; NOT under `tests/scripts/benchmarks/` (that dir is `--ignore`d by `pyproject.toml` addopts)
- [ ] `tests/services/test_flaw_delta_zones.py`, `tests/services/test_tactic_delta_zones.py`
- [ ] `frontend/src/lib/__tests__/gapBar.test.ts`
- [ ] `frontend/src/components/library/stats/__tests__/{GapBar,GapPopover,WhatStandsOut}.test.tsx`
- [ ] `frontend/src/hooks/__tests__/useLibraryStatsTc.test.ts`
- Prove new tests by reverting the fix once (mutation check), not by symbol presence.

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Desktop + mobile look matches sketch 010 round 5; TC switch syncs across all three sections | D-00a..D-00k, D-02 | Visual layout | Claude-in-Chrome on the dev build, desktop and phone widths |
| D-12 40-flaw constant sanity check vs CI width | D-12 | Needs dev DB data + new bands | Run the RESEARCH.md SQL on dev data after Plan 01; adjust constant only if clearly off |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
