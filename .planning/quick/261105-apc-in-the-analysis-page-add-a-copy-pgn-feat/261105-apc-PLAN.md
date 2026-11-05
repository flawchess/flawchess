---
quick_id: 261105-apc
mode: quick
type: execute
files_modified:
  - frontend/src/lib/pgn.ts
  - frontend/src/lib/pgn.test.ts
  - frontend/src/components/analysis/AnalysisTabs.tsx
  - frontend/src/components/analysis/AnalysisDesktopCards.tsx
  - frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx
  - frontend/src/pages/Analysis.tsx
  - frontend/src/lib/analytics.ts
  - CHANGELOG.md
autonomous: true
---

# Quick 261105-apc: Copy PGN in the Analysis PGN/FEN menu

Add a "Copy PGN" item next to "Copy FEN" (quick-261104-t65) in the move-list header dropdown.

## Decisions

- Export the WHOLE move tree, not just the main line: free play keeps every move off `mainLine`
  (empty mainLine), so a mainline-only export would be empty there. Sidelines become PGN RAV
  variations `( ... )`. Primary continuation per node = the mainLine successor when the parent is on
  mainLine, else the lowest-id child (mirrors VariationTree's ordering rule).
- Headers: Seven Tag Roster with `?` placeholders, filled from the pasted PGN headers or, in
  `?game_id=` mode, the fetched game (usernames, ratings, played_at date, result from
  user_result+user_color). `[SetUp "1"]`/`[FEN]` when the root is not the standard start.
- PGN text is built lazily on click (`getPgn` callback), not every render.
- Umami: `board-tool` target `pgn-copy`. Clipboard failure = sonner error toast, no Sentry (same as FEN).

## Task 1: `buildAnalysisPgn` serializer + unit tests (lib/pgn.ts, lib/pgn.test.ts)
verify: `cd frontend && npx vitest run src/lib/pgn.test.ts`

## Task 2: Menu item + wiring + tracking test + changelog
verify: `cd frontend && npx vitest run src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx && npm run lint && npm run build`
