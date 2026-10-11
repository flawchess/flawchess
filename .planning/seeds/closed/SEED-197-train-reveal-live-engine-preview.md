---
id: SEED-197
status: closed. Resolved by quick 261011-lwy (squash 9fd9f3425 on main, 2026-10-11), including the UAT follow-ups (items 6, 7, 10).
planted: 2026-10-11
planted_during: Phase 238 (Endgame Stats percentile-first), ad-hoc Train reveal UX discussion
trigger_when: owner picks a Train reveal / puzzle solution screen UX pass, or any rework of useTrainRevealTree / trainRevealLines
scope: medium (one phase, mostly frontend; reworks the Phase 237 reveal tree, adds a preview render mode to VariationTree)
---

# SEED-197: Train reveal, live engine preview instead of fixed chip lines

## Why This Matters

On the puzzle solution screen each chip (Move / Best / Game) pre-loads its line into the move tree
as fixed nodes, capped at `MAX_LINE_PLIES` (12). Owner feedback (2026-10-11):

- The link between the chip's eval and the line shown in the move list is not intuitive.
- The line never updates while stepping through it, although the live engine is already searching
  every shown node and gives better continuations a few plies deep.

Facts behind it (verified in code, 2026-10-11):

- None of these lines come from the server. The reveal endpoint deliberately carries no `pv`/eval
  (190.1-03 D-01, `frontend/src/types/train.ts` ~318); only the key move is server-picked (Phase 235 D-09).
  Best = grading engine's after-key search (`keyedAnchorFrom` / `GradeResult.bestLine`), Move =
  after-played search (`playedLine`, possibly clamped by `clampLineEvalToBest`, so the chip eval is not
  always the raw eval of the line shown), Game = the reveal-time "played in game" search. All run at
  1.5s movetime, the same as the live engine.
- The tail of a single 1.5s root PV is its least reliable part, while the live engine
  (`useTrainRevealTree`, `useStockfishEngine`) already searches each stepped node at full movetime.
  Today that fresher reading is demoted: the Stockfish row drops the line move (`dropLineMove`,
  `allSecondary`) and live arrows draw as secondaries under the fixed line's pointer
  (`buildTrainStepOverlayArrows`).

## Design (agreed in discussion)

1. **Chip owns only its first move.** Role, first move, quality mark and eval stay. The chip eval stays
   frozen (it is the graded reading the verdict and mark are based on); give it a "graded eval" label or
   tooltip so it is not confused with the live badge.
2. **Everything after the first move is a free node.** The known-line vs free-node split disappears past
   the first move. The chip's main line becomes "first move + first-added continuation under each node";
   later additions render as sidelines (analysis-board semantics).
3. **Dimmed live preview at the end of a branch.** When the current node is a leaf (main line or a user
   sideline, inside its parentheses), the list shows a dimmed preview of the live engine's top line from
   that position. Until the live search there is deep enough, the preview is the remaining tail of the
   previous preview; at open it is seeded from the grading PV, so the reveal looks as full as today.
4. **› / ArrowRight at a leaf commits the preview's next move** into the tree. Instant, so rapid stepping
   stays fast; the line refines whenever the user pauses. Committed nodes never change (no flicker on
   step-back). Tapping a preview token commits up to it (like `playLine` from the Stockfish row).
5. **No preview when stepped back** to a node that already has children. Existing moves show the
   continuation; › follows last-visited child as today.
6. ~~**Live eval badge leads the preview**~~ Dropped in UAT (2026-10-11): an eval badge inside the move
   list was confusing. The preview is dimmed tokens only.
7. **Stockfish row:** always lines 1..N (UAT 2026-10-11; first build showed 2..N at a leaf). Line 1 is
   the same top line as the preview and carries its live eval. Replaces `dropLineMove` / `allSecondary`.
   Brief mismatch accepted: until the live search reaches `TRAIN_LIVE_ALT_MIN_DEPTH` the preview shows
   the inherited/seed line while row 1 shows the shallow live line.
10. **Minimum preview length (UAT 2026-10-11):** chip move + at least 5 preview plies. A live line
   shorter than `TRAIN_PREVIEW_MIN_PLIES` (5) yields to a longer stored/seed/inherited line that agrees
   on its first move; a live line that disagrees on the first move always wins (never padded).
8. Playing a move that differs from the preview just commits it (new sideline if needed); previews are
   ephemeral and never persisted.
9. **Edge cases:** no preview at mate/stalemate; `MAX_LINE_PLIES` no longer caps committed nodes, only
   the preview length. Restore snapshot / Analyze handoff persist committed paths only (the
   `RevealTreeSnapshot` sideline-path mechanism mostly covers it); the preview regenerates.

## Open Questions

- Mobile space: the list is two rows (`TRAIN_MOVE_TREE_HEIGHT_CLASS = 'h-18 lg:h-30'`). Auto-scroll to
  the current node vs clipping the preview to ~4-6 plies. Settle with a sketch first.
- Minimum live depth before a node's own PV replaces the inherited preview tail.
- Whether the Game chip still needs its own full-line search or only the first-move eval + initial preview.

## Scope Estimate

**Medium**, one phase. Removes much of the Phase 237 known-line machinery (`stepInfo` overlays,
`dropLineMove`, known/free split in `resolveForwardTarget`, `capLineUcis`), adds a preview render mode to
`VariationTree` and commit-on-step navigation.

## Breadcrumbs

- `frontend/src/lib/trainRevealLines.ts` (chip model, `MAX_LINE_PLIES`, `capLineUcis`, `resolveForwardTarget`, snapshot)
- `frontend/src/hooks/useTrainRevealTree.ts` (~515-560: the one reveal engine, `knownIds`, `isOffLine`)
- `frontend/src/components/train/TrainMoveTreeList.tsx` (`TrainStockfishRow`, `dropLineMove`, `allSecondary`)
- `frontend/src/components/train/TrainSolveScreen.tsx` (`resolveRevealBoardOverlay`, `buildTrainStepOverlayArrows`)
- `frontend/src/hooks/trainGradingSupport.ts` (`keyedAnchorFrom`, `clampLineEvalToBest`)
- `frontend/src/components/analysis/VariationTree.tsx` (needs a preview/ghost mode)
- `.planning/seeds/closed/SEED-194-train-reveal-chips-and-move-tree.md` (the design this reworks)
