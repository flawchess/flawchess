---
quick_id: 261007-axc
mode: quick
files_modified:
  - app/schemas/train.py
  - frontend/src/types/train.ts
  - frontend/src/lib/trainTelemetry.ts
  - frontend/src/hooks/useTrainFreePlay.ts
  - frontend/src/hooks/useTrainPuzzleTelemetry.ts
  - tests/schemas/test_train_telemetry_schema.py
  - frontend/src/hooks/__tests__/useTrainFreePlay.test.ts
  - frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
---

# Quick 261007-axc: separate telemetry counter for hand-played free moves

`review_explore_moves` counts board drops AND Stockfish engine-line clicks during
free play, so it cannot answer "how many moves did the user play by hand". Add
`review_board_moves`: only moves played on the board (`freePlay.start` +
successful `freePlay.playMove`). `review_explore_moves` / `review_explored`
keep their semantics.

## Task 1: backend schema
- `ReviewTelemetry.review_board_moves: TelemetryExploreMoves | None = None` (same cap, 50).
- Optional key, absence = older client, so no schema version bump and no migration (JSONB merge).
- Schema test: clamps to TELEMETRY_EXPLORE_MOVES_CAP, rejects bool.

## Task 2: frontend wiring
- `ExploreMoveSource = 'board' | 'engine-line'` in `lib/trainTelemetry.ts`.
- `useTrainFreePlay.onUserMove(source)`: start/playMove pass 'board', playLine 'engine-line'.
- `useTrainPuzzleTelemetry.onExploreMove(source)`: exploreMoves always +1, boardMoves +1 for 'board'.
- `ReviewCounters.boardMoves`, snapshot `boardMoves?` (guarded, seeded on restore), flush key `review_board_moves`.
- `types/train.ts` ReviewTelemetry mirror.

## Task 3: tests
- useTrainFreePlay: source argument per command.
- useTrainPuzzleTelemetry: board vs engine-line split, cap, snapshot round trip, closed key set (12).

Privacy page lists no individual counters: no copy change.
