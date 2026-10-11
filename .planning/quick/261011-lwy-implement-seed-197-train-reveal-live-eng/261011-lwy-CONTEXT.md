# Quick Task 261011-lwy: Implement SEED-197 (Train reveal live engine preview instead of fixed chip lines) - Context

**Gathered:** 2026-10-11
**Status:** Ready for planning

<domain>
## Task Boundary

Implement SEED-197 (`.planning/seeds/SEED-197-train-reveal-live-engine-preview.md`) on the Train puzzle
solution (reveal) screen: chips own only their first move; everything after is free nodes; a dimmed live
engine preview renders at the end of the current branch and is committed on ›/ArrowRight or token tap.
Frontend-only. The seed's "Design (agreed in discussion)" section items 1-9 are LOCKED requirements.

Work happens in the dedicated worktree `/home/aimfeld/Projects/Python/flawchess-seed197` on branch
`quick/seed-197-live-engine-preview` (forked from `main` at 8db01db3c). Never touch the main checkout
`/home/aimfeld/Projects/Python/flawchess` (another session owns it on a phase branch).

</domain>

<decisions>
## Implementation Decisions

### Seed design (locked, from SEED-197 "Design" items 1-9)
- Chip owns only its first move; chip eval stays frozen with a "graded eval" label/tooltip.
- Everything after the first move is a free node (analysis-board semantics: first-added child = main line, later = sidelines).
- Dimmed live preview at a leaf only; seeded from the grading PV at open; inherits the previous preview's remaining tail until the live search is deep enough.
- › / ArrowRight at a leaf commits the preview's next move instantly; tapping a preview token commits up to it. Committed nodes never change.
- No preview when the current node already has children (› follows last-visited child as today).
- Live eval badge (`formatScore` styling) leads the preview.
- Stockfish row: at a leaf shows lines 2..N only; elsewhere all N. Replaces `dropLineMove` / `allSecondary`.
- Playing a different move just commits it; previews are ephemeral and never persisted.
- No preview at mate/stalemate; `MAX_LINE_PLIES` caps only the preview, not committed nodes; snapshot / Analyze handoff persist committed paths only.

### Mobile fit (open question 1)
- Clip the preview to ~6 plies on all viewports (named constant, e.g. `TRAIN_PREVIEW_MAX_PLIES = 6`) AND auto-scroll the move list so the current node stays visible.

### Preview replacement depth (open question 2)
- Reuse the existing `TRAIN_LIVE_ALT_MIN_DEPTH = 10` (`frontend/src/lib/trainArrows.ts`) as the minimum live depth before a node's own PV replaces the inherited preview tail. No new depth constant.

### Game chip search (open question 3)
- Keep the Game chip's reveal-time full-line search: it supplies the first-move eval and seeds the initial preview.

### Grading of preview-committed moves (post-research, research A2)
- Do NOT grade moves committed from the preview (› or token tap). Track them (e.g. a `previewCommittedIds` set) and exclude them from `useTreeMoveGrading` badges. Moves the user plays themselves on the board stay graded as today.

### Preview at open (post-research, research A1)
- At open, the preview hangs off the active chip's first move while that node has no children, seeded from the grading PV, so the list looks as full as today.

### Claude's Discretion
- How the preview render mode is added to `VariationTree` (prop shape, dim styling via existing theme tokens).
- Module seams for the preview state (pure helpers in `lib/` with unit tests preferred over hook-internal logic).
- Which Phase 237 known-line machinery to delete vs adapt, as long as the locked behavior holds and no dead code remains (knip must pass).

</decisions>

<specifics>
## Specific Ideas

- Breadcrumbs listed in the seed: `lib/trainRevealLines.ts`, `hooks/useTrainRevealTree.ts` (~515-560), `components/train/TrainMoveTreeList.tsx`, `components/train/TrainSolveScreen.tsx` (`resolveRevealBoardOverlay`, `buildTrainStepOverlayArrows`), `hooks/trainGradingSupport.ts`, `components/analysis/VariationTree.tsx`.
- The reveal endpoint carries no pv/eval; all lines are client-side 1.5s searches. No backend change.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/seeds/SEED-197-train-reveal-live-engine-preview.md` (the spec)
- `.planning/seeds/closed/SEED-194-train-reveal-chips-and-move-tree.md` (the design this reworks)
- `frontend/CLAUDE.md` (styling, testids, Umami rules)

</canonical_refs>
