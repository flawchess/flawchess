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

Rows mapped to the executed plans; status from the 239-09 pre-merge gate run (2026-10-13: backend 5390 passed, frontend 5578 passed).

| Decision | Plan / Task | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|-------------|----------|-----------|-------------------|-------------|--------|
| D-06/D-07/D-08 | 239-01 T1-T2 | §5 base on the full-analysis lane; 12 flaw + 38 tactic metric keys; no combos/flaw_rate | unit (SQL string) | `uv run pytest tests/scripts/test_chapter5_sql.py -x` | ✅ | ✅ green |
| D-06/D-07 | 239-06 T1 | Numbers reproduce the narrated report | integration (benchmark DB, on demand) | `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` | ✅ | ✅ green (4 passed, 239-06) |
| D-08/D-09/D-10 | 239-02 T1, 239-07 T1 | blitz/bullet → rapid zones; registry has exactly 12 flaw metrics; lookup per TC; accepted values pinned | unit | `uv run pytest tests/services/test_flaw_delta_zones.py -x` | ✅ | ✅ green |
| D-11/D-06 | 239-04 T1, 239-07 T1 | Tactic registry covers all families × Missed/Allowed; 9 accepted bands; unviable → `has_zone=False` | unit | `uv run pytest tests/services/test_tactic_delta_zones.py -x` | ✅ | ✅ green |
| D-02/D-03 | 239-02 T1-T2 | `tcs[]` lists only TCs with ≥1 analyzed game inside the TC filter; below-gate TC still has bullets | integration | `uv run pytest tests/services/test_flaw_comparison.py -x` | ✅ | ✅ green |
| D-00e/D-00f | 239-02 T1 | 12 bullets (blunder, mistake, 10 tags), no combos/flaw_rate | integration | `uv run pytest tests/services/test_flaw_comparison.py -x` | ✅ | ✅ green |
| D-00h/D-11 | 239-04 T1-T2 | Tactic bullets per 100 games, fixed order, all families, no top-6; zones from registry | integration | `uv run pytest tests/services/test_tactic_comparison_service.py -x` | ✅ | ✅ green |
| D-12 | 239-02 T2, 239-04 T2 | `low_sample` true below 40 you+opp flaws, false at 40 | integration | same two files | ✅ | ✅ green |
| D-00k | 239-02 T3 | `trend_by_tc` per TC; `analyzed_n` kept | integration | `uv run pytest tests/services/test_library_service.py -x -k flaw_stats` | ✅ | ✅ green |
| API | 239-02 T3, 239-04 T2 | Router shapes, 422 on bad params | integration | `uv run pytest tests/test_library_router.py tests/routers/test_library_tactic_comparison.py -x` | ✅ | ✅ green |
| D-00a/D-00b | 239-03 T1 | gap position (centre, band edges, saturation, zero-width guards), gap words, verdict | unit | `cd frontend && npm test -- --run src/lib/__tests__/gapBar.test.ts` | ✅ | ✅ green |
| D-00a/D-11/D-12 | 239-03 T1 | GapBar band/no band, blue dot when faded/zoneless | component | `cd frontend && npm test -- --run src/components/library/stats/__tests__/GapBar.test.tsx` | ✅ | ✅ green |
| D-00c | 239-03 T2 | Gap popover sections, "Too few flaws to call it", no range line when zoneless, CI/p footer | component | `cd frontend && npm test -- --run src/components/library/stats/__tests__/GapPopover.test.tsx` | ✅ | ✅ green |
| D-02/D-04/D-05 | 239-03 T3 | Default TC rule, separate key, stored TC ignored when not offered | hook | `cd frontend && npm test -- --run src/hooks/__tests__/useLibraryStatsTc.test.ts` | ✅ | ✅ green |
| D-00j/D-02 | 239-05 T1 | Flaw Stats tiles and synced TC switch, no refetch on TC change | component | `cd frontend && npm test -- --run src/components/library/stats/__tests__/FlawTiles.test.tsx src/components/library/stats/__tests__/LibraryStatsSections.test.tsx` | ✅ | ✅ green |
| D-00g/D-13 | 239-10 T1 | Top 3 per side by band-width distance; faded/zoneless excluded; Typical line; empty copy | component | `cd frontend && npm test -- --run src/components/library/stats/__tests__/WhatStandsOut.test.tsx` | ✅ | ✅ green |
| D-00f/D-03 | 239-10 T1 | Four cards, tag order, hints, gate slot "(12 of 20)" | component | `cd frontend && npm test -- --run src/components/library/stats/__tests__/ContextTagCards.test.tsx` | ✅ | ✅ green |
| D-00h/D-00i/D-03 | 239-08 T1-T2 | Three tables in TACTIC_GROUPS order, zero-count motifs under table, Advanced collapsed with hint | component | `cd frontend && npm test -- --run src/components/library/stats/__tests__/TacticTables.test.tsx` | ✅ | ✅ green |

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
