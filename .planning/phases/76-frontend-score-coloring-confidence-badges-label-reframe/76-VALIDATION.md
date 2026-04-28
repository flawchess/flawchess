---
phase: 76
slug: frontend-score-coloring-confidence-badges-label-reframe
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 76 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 8.x (`uv run pytest`) |
| **Backend type-check** | `uv run ty check app/ tests/` (CI gate, must pass with zero errors) |
| **Backend lint** | `uv run ruff check . && uv run ruff format --check .` |
| **Frontend framework** | Vitest 1.x with jsdom (per-file env via `// @vitest-environment jsdom`) |
| **Frontend type-check** | `cd frontend && npx tsc --noEmit` |
| **Frontend lint** | `cd frontend && npm run lint && npm run knip` |
| **Quick run command (touched-file)** | `uv run pytest tests/services/test_score_confidence.py tests/services/test_opening_insights_service.py tests/services/test_opening_insights_arrow_consistency.py -x` and `cd frontend && npx vitest run src/lib/__tests__/arrowColor.test.ts src/components/insights/__tests__/OpeningFindingCard.test.tsx src/components/insights/__tests__/OpeningInsightsBlock.test.tsx src/components/move-explorer/__tests__/MoveExplorer.test.tsx` |
| **Full suite command** | `uv run pytest && uv run ty check app/ tests/ && cd frontend && npm run lint && npm run knip && npx tsc --noEmit && npx vitest run` |
| **Estimated runtime (quick)** | ~25 seconds |
| **Estimated runtime (full)** | ~3-4 minutes |

---

## Sampling Rate

- **After every task commit:** Run touched-file quick command (≤25s)
- **After every plan wave:** Run full suite (~3-4min)
- **Before `/gsd-verify-work`:** Full suite must be green AND manual mobile QA at 375px viewport
- **Max feedback latency:** 30 seconds for unit-level signal

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 76-01-01 | 01 (backend) | 1 | INSIGHT-UI-03 (D-06) | — | New shared module — formula single source of truth | unit | `uv run pytest tests/services/test_score_confidence.py -x` | ❌ W0 | ⬜ pending |
| 76-01-02 | 01 (backend) | 1 | INSIGHT-UI-03 (D-06) | — | Migration leaves no dangling import | unit | `uv run pytest tests/services/test_opening_insights_service.py -x && uv run ty check app/services/opening_insights_service.py` | ✅ | ⬜ pending |
| 76-01-03 | 01 (backend) | 1 | INSIGHT-UI-03 (D-03) | — | Re-sort key changes deterministically | unit | `uv run pytest tests/services/test_opening_insights_service.py::test_ranking -x` | ✅ | ⬜ pending |
| 76-02-01 | 02 (backend) | 2 | INSIGHT-UI-03 (D-05/D-07) | — | Score/confidence/p_value populated on every NextMoveEntry | unit + schema | `uv run pytest tests/services/test_openings_service.py -k next_moves -x && uv run ty check app/schemas/openings.py app/services/openings_service.py` | ✅ | ⬜ pending |
| 76-02-02 | 02 (backend) | 2 | INSIGHT-UI-03 (D-22) | — | CI consistency test asserts both call sites use the shared helper | unit | `uv run pytest tests/services/test_opening_insights_arrow_consistency.py -x` | ✅ | ⬜ pending |
| 76-03-01 | 03 (frontend types) | 2 | INSIGHT-UI-05 (D-21) | — | Type catch-up — kills "NaN%" runtime bug | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |
| 76-04-01 | 04 (frontend arrow/color) | 3 | INSIGHT-UI-01, INSIGHT-UI-02 (D-12/D-13/D-15) | — | Score-based bucket boundaries match backend constants | unit | `cd frontend && npx vitest run src/lib/__tests__/arrowColor.test.ts` | ❌ W0 | ⬜ pending |
| 76-04-02 | 04 (frontend openingInsights.ts) | 3 | INSIGHT-UI-06 (D-17/D-20) | — | Stale constants removed, popover copy constant added | unit + knip | `cd frontend && npx vitest run src/lib/__tests__/openingInsights.test.ts && npm run knip` | ✅ | ⬜ pending |
| 76-05-01 | 05 (MoveExplorer) | 4 | INSIGHT-UI-02, INSIGHT-UI-03, INSIGHT-UI-07 (D-08/D-11/D-13/D-14) | — | New "Conf" column renders, score-based row tint, mute extension | component | `cd frontend && npx vitest run src/components/move-explorer/__tests__/MoveExplorer.test.tsx` | ✅ | ⬜ pending |
| 76-06-01 | 06 (OpeningFindingCard) | 4 | INSIGHT-UI-05 (D-02/D-09/D-10/D-11/D-19) | — | Prose migration removes broken loss_rate read; confidence line + tooltip render | component | `cd frontend && npx vitest run src/components/insights/__tests__/OpeningFindingCard.test.tsx` | ✅ | ⬜ pending |
| 76-07-01 | 07 (OpeningInsightsBlock) | 4 | INSIGHT-UI-06 (D-16/D-18) | — | Four InfoPopover icons render with shared copy; sort survives | component | `cd frontend && npx vitest run src/components/insights/__tests__/OpeningInsightsBlock.test.tsx` | ✅ | ⬜ pending |
| 76-08-01 | 08 (verify) | 5 | INSIGHT-UI-01..07 minus 04 | — | Whole-suite regression + ROADMAP/REQUIREMENTS amendments | suite | `uv run pytest && uv run ty check app/ tests/ && cd frontend && npm run lint && npm run knip && npx tsc --noEmit && npx vitest run` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_score_confidence.py` — boundary tests for `compute_confidence_bucket(w, d, l, n)` (n=10 floor, half_width=0.10 exact, half_width=0.20 exact, w/d/l = 0 edges, near-pivot scores)
- [ ] `frontend/src/lib/__tests__/arrowColor.test.ts` — score-based bucket boundary tests (≥0.60 DARK_GREEN, ≥0.55 LIGHT_GREEN, ≤0.40 DARK_RED, ≤0.45 LIGHT_RED, else GREY); MIN_GAMES_FOR_COLOR guard; isHovered short-circuit; signature change (no winPct/lossPct)
- [ ] `frontend/src/lib/__tests__/openingInsights.test.ts` — verify popover copy constant exported; verify removed constants (`LIGHT_COLOR_THRESHOLD`, `DARK_COLOR_THRESHOLD`, `INSIGHT_RATE_THRESHOLD`, `INSIGHT_THRESHOLD_COPY`) cause import errors if reintroduced (regression guard via knip + tsc)

*Existing tests cover the rest:*
- `tests/services/test_opening_insights_service.py` — extended for D-03 sort
- `tests/services/test_opening_insights_arrow_consistency.py` — extended for D-22
- `tests/services/test_openings_service.py` — extended for `score`/`confidence`/`p_value` on `NextMoveEntry`
- Existing component test files for MoveExplorer / OpeningFindingCard / OpeningInsightsBlock — extended for new fields

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mobile parity at 375px viewport — no horizontal scroll on Move Explorer table with new "Conf" column | INSIGHT-UI-07 (D-08, D-25) | Real device rendering depends on text-wrapping, font metrics, and Tailwind's `text-xs` resolution that jsdom can't faithfully simulate | 1. `bin/run_local.sh` 2. Open Chrome DevTools, set viewport to iPhone SE (375×667) 3. Navigate to Openings → Moves tab 4. Verify all four columns (Move, Games, Conf, WDL) render without horizontal scroll 5. Verify `low/med/high` text legible at `text-xs` 6. Tap a "Confidence: …" indicator on a card — tooltip should appear and not require hover |
| InfoPopover tap-target on touch devices for the four section-title `?` icons | INSIGHT-UI-06, INSIGHT-UI-07 | Touch interaction can't be authenticated by jsdom event simulation | Same setup. Tap each `?` icon next to "White Opening Weaknesses / Strengths" / "Black …" — popover should open on first tap and dismiss on outside tap or second tap. ≥44px effective touch area. |
| Score-prose rounding edge case — display % never contradicts section title | INSIGHT-UI-05 (D-02, Claude's Discretion) | Edge-case visual sanity that's cheaper to eyeball than exhaustively unit-test | Force-seed a finding with `score = 0.499` (weakness section, would round to 50%); verify display falls back to `.toFixed(1)` (`49.9%`) rather than `50%`. Sanity check: red-tinted card never shows ≥50; green-tinted card never shows ≤50. |
| Visual mute (`UNRELIABLE_OPACITY = 0.5`) merges correctly with deep-link pulse and tintColor on rows | INSIGHT-UI-03, INSIGHT-UI-07 (D-11) | Animation + multiple CSS layers compositing better verified by eye | Bookmark a low-confidence position (n_games < 10), navigate to it via deep link — pulse should fire over the muted (0.5 opacity) row tint without one wiping the other. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (3 new test files: `test_score_confidence.py`, `arrowColor.test.ts`, `openingInsights.test.ts`)
- [ ] No watch-mode flags (all `npx vitest run`, `pytest -x`)
- [ ] Feedback latency < 30s for quick command
- [ ] `nyquist_compliant: true` set in frontmatter after Wave 0 lands

**Approval:** pending
