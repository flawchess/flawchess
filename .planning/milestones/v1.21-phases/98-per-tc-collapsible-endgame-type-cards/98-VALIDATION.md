---
phase: 98
slug: per-tc-collapsible-endgame-type-cards
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-30
---

# Phase 98 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest) · `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest -x` · `( cd frontend && npm test -- --run )` |
| **Full suite command** | `uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest && ( cd frontend && npm run lint && npm test -- --run && npm run knip )` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick run command (backend `uv run pytest -x`, frontend `npm test -- --run`)
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green (incl. `gen_endgame_zones_ts.py` drift gate)
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

> Populated by the planner per PLAN.md. Rows below are the validation-critical behaviors derived from RESEARCH.md "## Validation Architecture" and the ROADMAP success criteria. The planner maps each to a concrete task.

| Behavior | Wave | Success Criteria | Test Type | Automated Command | Status |
|----------|------|------------------|-----------|-------------------|--------|
| `endgame_zones.py` emits 20 per-(class × TC) Conv + 20 Recov bands + per-(class × TC) ΔES bands | 1 | SC-6 | unit | `uv run pytest tests/ -k endgame_zones` | ⬜ pending |
| `endgameZones.ts` codegen drift gate green after band additions | 1 | SC-6 | gate | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | ⬜ pending |
| `/stats` exposes per-(class × TC) rates + counts (`categories_by_tc`) | 1 | SC-8 | unit | `uv run pytest tests/ -k endgame_service` | ⬜ pending |
| LLM path (`_findings_conversion_recovery_by_type` / `assign_per_class_zone`) response shape unchanged (D-15) | 1 | SC-8 | unit | `uv run pytest tests/ -k insights` | ⬜ pending |
| `primaryTc` util: argmax(games × NOMINAL_DURATION) over TCs passing games floor | 2 | SC-2 | unit | `( cd frontend && npm test -- --run primaryTc )` | ⬜ pending |
| Section renders full-width collapsible per-TC cards (no `grid-cols-3`); primary TC expanded | 2 | SC-1, SC-2 | component | `( cd frontend && npm test -- --run EndgameTypeBreakdownSection )` | ⬜ pending |
| Each TC card renders 2×2-family grid of 4 tiles (rook/minor/pawn/queen), Mixed absent | 2 | SC-3 | component | `( cd frontend && npm test -- --run EndgameTypeCard )` | ⬜ pending |
| Tile shows restored 5-element anatomy w/ Conv+Recov gauges banded per-(class × TC) | 2 | SC-4, SC-5 | component | `( cd frontend && npm test -- --run EndgameTypeCard )` | ⬜ pending |
| TC card / tile self-suppress below games floor | 2 | SC-7 | component | `( cd frontend && npm test -- --run EndgameTypeBreakdownSection )` | ⬜ pending |
| Accordion reset-to-primary on filter change (D-12) | 2 | SC-2 | component | `( cd frontend && npm test -- --run EndgameTypeBreakdownSection )` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* Backend pytest + frontend vitest are established; the `endgameZones.ts` codegen drift gate already runs in CI. No new framework install needed. Existing `EndgameTypeCard` / `EndgameTypeBreakdownSection` tests must be **updated** (locked `grid-cols-*` and Mixed-tile assertions change) — that is task work, not Wave 0 scaffolding.

---

## Manual-Only Verifications

| Behavior | Success Criteria | Why Manual | Test Instructions |
|----------|------------------|------------|-------------------|
| Desktop + mobile responsive staircase (4×1 → 2×2 → 1×4) renders cleanly with divider grammar (not boxes) | SC-9 | Visual layout / divider rendering across breakpoints not reliably asserted in jsdom | Open Endgames page on desktop + narrow viewport; confirm collapsible per-TC cards full-width, four tiles with vertical+horizontal dividers at 2×2, two gauges readable on mobile |
| Primary-TC default-expand picks the time-weighted (not count-weighted) TC for a real multi-TC user | SC-2 | Requires real imported game distribution | With a user concentrated in rapid but high bullet count, confirm rapid card is expanded by default |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
