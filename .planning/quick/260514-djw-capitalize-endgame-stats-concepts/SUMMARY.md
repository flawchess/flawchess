---
slug: capitalize-endgame-stats-concepts
quick_id: 260514-djw
date: 2026-05-14
status: complete
---

# Summary

Title-cased every named concept from the "Endgame statistics concepts" panel across user-facing copy (Endgames Stats page, Home FAQ, AchievableScorePopover) and the LLM Insights prompt. Bumped `_PROMPT_VERSION` `endgame_v27` → `endgame_v28` to invalidate cached LLM reports so newly generated narration uses the capitalized terms.

## Concepts updated

- Endgame Phase, Endgame Type(s), Endgame Sequence
- Endgame Entry Eval, Achievable Score, Endgame Score, Non-Endgame Score

(Conversion / Parity / Recovery and Endgame Score Gap / Loss were already title-cased.)

## Verification

- `npm run lint`: clean
- `npm test`: 346/346 passing
- `uv run ty check app/ tests/`: clean
- `uv run ruff check app/ tests/`: clean
- `uv run pytest`: 1402/1402 passing
