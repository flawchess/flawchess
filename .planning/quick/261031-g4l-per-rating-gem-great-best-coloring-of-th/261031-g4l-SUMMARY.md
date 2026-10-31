---
quick_id: 261031-g4l
status: complete
date: 2026-10-31
commit: a02ca1788
---

# Quick 261031-g4l: per-rating gem/great/best coloring of the best-move line

## What changed
- `gemMove.ts`: `rareTierForProbability(prob)` (<=0.3 gem, <=0.7 great, else best) and
  `onlyGoodMoveSan(qualityBySan, bestSan, mover)` (stored gem/great tag OR live C2 gate).
- `MovesByRatingChart.tsx`: new `tieredSan` prop. That line is stroked with a vertical
  userSpaceOnUse gradient with hard stops at the y-pixels of 0.7 and 0.3. Tooltip rows and the
  pinned FlawChess row use the hovered rung's tier (icon, word, color); row colors now derive
  from quality instead of the payload stroke. End label takes its tier at the selected ELO (follow-up), matching the move-list icon.
- `MaiaHumanPanel.tsx`: computes `tieredSan`; popover gains one sentence on per-rating coloring.
- CHANGELOG `[Unreleased]` bullet.

## Decisions
- The chart answers "at this rating": the color at the dashed selected-ELO line may differ
  from the game-rung gem/great badge (user decision in /gsd-explore, 2026-10-31).
- Executed inline (sequential), not via planner/executor subagents.

## Verification
- `npm run lint`, `npm run build`, `npm test -- --run` (339 files / 5677 tests), `npm run knip`: all pass.
- No browser check yet; the user will review visually.
