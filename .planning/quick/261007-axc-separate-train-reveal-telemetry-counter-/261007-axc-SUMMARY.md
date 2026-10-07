---
quick_id: 261007-axc
status: complete
commit: 27ce3d361
date: 2026-10-07
---

# Quick 261007-axc: review_board_moves telemetry counter

New Train reveal telemetry key `review_board_moves`: free-play moves played on the
board by hand (`freePlay.start` + successful `playMove`). Desktop drag and mobile
tap-to-move both route through `ChessBoard.onPieceDrop` (ChessBoard.tsx:337/381),
so the counter covers both clients. Stockfish engine-line clicks (`playLine`) still
count toward `review_explore_moves` but not `review_board_moves`.

- Backend: `ReviewTelemetry.review_board_moves` (same 50 cap). Optional key: no schema version bump, no migration.
- Frontend: `ExploreMoveSource` type; `useTrainFreePlay.onUserMove(source)`; counters, snapshot (restore-safe) and flush key in `useTrainPuzzleTelemetry` / `trainTelemetry`.
- Tests: free-play source tags, hook split/cap/snapshot round trip/closed key set, TrainSolveScreen integration (2 board + 1 engine-line -> explore 3, board 2), schema clamp + bool reject. Mutation (engine-line tagged 'board') fails 2 tests.
- Privacy copy unchanged (generic wording covers it). No changelog entry (internal telemetry).

Data from before this deploy has no `review_board_moves` key; query `telemetry ? 'review_board_moves'` to restrict to new clients.
