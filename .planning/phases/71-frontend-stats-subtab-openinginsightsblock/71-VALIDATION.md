---
phase: 71
slug: frontend-stats-subtab-openinginsightsblock
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 71 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest 4.x + @testing-library/react |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npm test -- --run` |
| **Full suite command** | `cd frontend && npm test -- --run && npm run build && npm run lint && npm run knip` |
| **Estimated runtime** | ~30s quick, ~90s full |

For backend changes (Phase 70 contract amendment):

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Quick run command** | `uv run pytest tests/test_opening_insights_service.py -x` |
| **Full suite command** | `uv run pytest && uv run ty check app/ tests/ && uv run ruff check .` |
| **Estimated runtime** | ~20s targeted, ~120s full |

---

## Sampling Rate

- **After every task commit:** Run quick run command for the affected stack (frontend or backend).
- **After every plan wave:** Run full suite command for any stack the wave touched.
- **Before `/gsd-verify-work`:** Full suite green for both stacks.
- **Max feedback latency:** 30 seconds.

---

## Per-Task Verification Map

(Filled in by planner — every task gets a `verify` command. See PLAN.md `<automated>` blocks.)

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/openingInsights.test.ts` — unit tests for `trimMoveSequence` (covers all D-05 edge cases) and severity-color mapping
- [ ] `frontend/src/components/insights/OpeningFindingCard.test.tsx` — render tests for severity accents, prose templates, deep-link click
- [ ] `frontend/src/components/insights/OpeningInsightsBlock.test.tsx` — render tests for the four section states (loading skeleton, error, empty, populated)
- [ ] `frontend/src/hooks/useOpeningInsights.test.ts` — hook test with mocked endpoint, filter forwarding, debounce behavior
- [ ] `tests/test_opening_insights_service.py` — extend existing tests to cover `entry_san_sequence` field on `OpeningInsightFinding` (Phase 70 contract amendment per RESEARCH §"Phase 70 Contract Amendment")

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mobile layout at 375px width — no horizontal scroll, ≥ 44px touch targets | INSIGHT-STATS-05 | Visual / responsive correctness | Open `/openings` → Stats tab in DevTools 375px viewport; confirm cards stack vertically, board renders ~105px, no scrollbar appears, click target ≥ 44px |
| Severity border-left color matches arrow color on Move Explorer after deep-link | INSIGHT-STATS-02 | Visual color match across components | Click a "major weakness" card, observe explorer arrow renders the same dark-red shade the card border used |
| Skeleton matches eventual layout (no layout-shift on data arrival) | INSIGHT-STATS-04 | Visual perception / CLS | Throttle network to Slow 3G; confirm skeleton renders 4 section headers and 2-3 placeholder cards each, no shift when data arrives |
| Deep-link sets the global `color` filter, scrolls to top, navigates to `/openings/explorer` with board pre-loaded at entry FEN | INSIGHT-STATS-02, INSIGHT-STATS-06 | Multi-state mutation across page | Click any finding card; confirm URL = `/openings/explorer`, color filter chip reflects finding's color, board flipped if Black, position matches `entry_fen` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
