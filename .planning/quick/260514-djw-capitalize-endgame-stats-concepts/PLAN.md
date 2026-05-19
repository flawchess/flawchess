---
slug: capitalize-endgame-stats-concepts
quick_id: 260514-djw
date: 2026-05-14
---

# Quick Task: Capitalize Endgame Stats concepts in user-facing copy

Title-case every reference to the named concepts on the Endgames -> Stats page (concept accordion, popovers, aria-labels, gauge labels), the Home page FAQ, and the LLM Insights prompt:

- Endgame Phase
- Endgame Type / Endgame Types
- Endgame Sequence
- Endgame Entry Eval
- Achievable Score
- Endgame Score
- Non-Endgame Score

(Conversion / Parity / Recovery and Endgame Score Gap / Loss were already title-cased.)

## Files touched

- `frontend/src/pages/Endgames.tsx` — concept accordion + games-tab dropdown label + dialog text
- `frontend/src/pages/Home.tsx` — FAQ "endgame type" → "Endgame Type"
- `frontend/src/components/charts/EndgameOverallEntryCard.tsx` — labels + aria-labels
- `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx` — popover aria-labels + tooltip prose
- `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` — popover aria-label + tooltip prose
- `frontend/src/components/charts/EndgameWDLChart.tsx` — descriptions, aria-labels, table aria-label
- `frontend/src/components/charts/EndgameConvRecovChart.tsx` — popover prose
- `frontend/src/components/charts/EndgameTimePressureSection.tsx` — popover prose
- `frontend/src/components/popovers/AchievableScorePopover.tsx` — aria-label + body copy
- `app/prompts/endgame_insights.md` — UI-label table + glossary + prose
- `app/services/insights_llm.py` — overall_wdl description string + recovery typical-bands inline note + `_PROMPT_VERSION` bumped v27 → v28
- `frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx` — assertion regexes
- `frontend/src/components/popovers/__tests__/AchievableScorePopover.test.tsx` — assertion regex
- `tests/services/test_insights_llm.py` — version assertion + glossary assertion
- `CHANGELOG.md` — Unreleased Changed entry

## Verification

- `npm run lint` — clean
- `npm test` — 346/346 passing
- `uv run ty check app/ tests/` — clean
- `uv run ruff check app/ tests/` — clean
- `uv run pytest` — 1402/1402 passing (6 skipped, pre-existing)
