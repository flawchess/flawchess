---
quick_id: 260627-thl
slug: more-uat-feedback-for-phase-140-analysis
date: 2026-06-27
status: in-progress
---

# Quick Task: Phase 140 analysis-board UAT round 5

Five UAT tweaks for the full-game analysis board. Frontend-only.

## Items

### 1. Move list 25px shorter (desktop)
The desktop move list (`VariationTree` → `DesktopTree`) is `flex-1`, filling the side
panel so `BoardControls` bottom-align with the eval-chart slider. That is why earlier
`max-height` tweaks did nothing — flex-fill, not `max-height`, is the binding height.

**Fix:** add `mb-[25px]` to the DesktopTree scroll container. A flex-grow item's size is
reduced by its margins, so the visible list shrinks 25px while the controls stay
bottom-aligned (gap opens above the controls — user-confirmed layout).
- `frontend/src/components/analysis/VariationTree.tsx:622`

### 2. Best-move (blue) arrow is one ply behind the grey 2nd-best arrow
Confirmed against the DB: `game_positions[X].best_move` is the engine's best move **FROM
position X** (the decision position, before `move_san[X]`), while `game_positions[X].eval_cp`
is the **post-move** eval (position X+1). The board shows the position **after** the played
move = `mainLine[k]` = position `k+1`. So the best move from the *displayed* position is
`best_move` stored at row `k+1`, not row `k`. Current code uses `get(k)` → arrow points to
the move that *led into* the shown position, mismatching the live-engine grey arrow (which
is from the current position). The depth label paired with the old arrow was the
missed-tactic depth at the decision; since the arrow now means "best continuation from
here", that label no longer applies and is dropped (missed tactics remain in the move-list
chips; the allowed-tactic depth stays on the played-move corner glyph).

**Fix (both boards — user flagged LibraryGameCard has the same bug; FlawCard is correct
and untouched):**
- `frontend/src/hooks/useGameOverlay.ts` — blue arrow `bestMoveByPly.get(k + 1)`; drop the
  missed-depth label/labelColor from the blue arrow; drop now-unused `TAC_MISSED_LABEL`.
- `frontend/src/components/results/LibraryGameCard.tsx` — `bestMoveByPly.get(activePly + 1)`;
  drop `label: depths?.missed` from the arrow; fix the misleading comments.
- Update `frontend/src/hooks/__tests__/useGameOverlay.test.ts` blue-arrow source contract.

### 3. Show blunder/mistake icons in the move list even when a tactic chip is present
The severity glyph (`BlunderIcon`/`MistakeIcon`) already renders, but only when
`!hasTacticChip`. The user wants the icons shown for blunder/mistake regardless.

**Fix:** drop the `!hasTacticChip` / `!hasChip` gate on `showSeverityMarker` (desktop
`renderMoveButton` + mobile `MobileTree`).
- `frontend/src/components/analysis/VariationTree.tsx` (desktop ~527, mobile ~369)

### 4. Forward button steps into the sideline after opening a flaw line
After clicking a flaw chip, the board parks at the fork node. `goForward` picks the
lowest-id child = the main-line continuation (created before the grafted PV), so forward
steps down the main line instead of the sideline.

**Fix:** in `goForward`, when `pvLine` is non-empty and the current node is the parent of
`pvLine[0]` (the fork), advance into `pvLine[0]`.
- `frontend/src/hooks/useAnalysisBoard.ts` (`goForward`)

### 5. Miniboard tooltip on engine-move hover
Engine PV move chips have no hover preview. Add a `MiniBoard` tooltip showing the position
after that PV move (replayed from `baseFen`). Desktop hover only (Tooltip already suppresses
on touch).

**Fix:**
- `frontend/src/components/analysis/EngineLines.tsx` — replay PV to per-step `{san, fen}`;
  wrap each chip in `Tooltip` with a `MiniBoard` content; add a `flipped` prop.
- `frontend/src/pages/Analysis.tsx` — pass `flipped={boardFlipped}` to `EngineLines`.
- Tests: ensure `EngineLines.test.tsx` renders within a `TooltipProvider`.

## Verification
- `cd frontend && npm run lint && npm test -- --run && npx tsc -b`
- Manual: open `/analysis?game_id=…&ply=…`, check arrows match, icons show, forward steps
  into sideline, engine-move hover shows a miniboard, move list is shorter.

## Commits (atomic, one per item)
1. `feat(260627-thl): shrink desktop move list 25px (flex-margin, controls stay aligned)`
2. `fix(260627-thl): best-move arrow uses next-ply best_move (analysis board + game card)`
3. `feat(260627-thl): show blunder/mistake glyphs in move list even with a tactic chip`
4. `feat(260627-thl): forward button steps into the open flaw sideline`
5. `feat(260627-thl): miniboard tooltip on engine-move hover`
