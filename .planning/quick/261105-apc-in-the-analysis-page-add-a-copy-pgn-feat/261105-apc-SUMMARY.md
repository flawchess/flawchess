---
quick_id: 261105-apc
status: complete
commit: 6088226c7
---

# Quick 261105-apc: Copy PGN in the Analysis PGN/FEN menu

- `buildAnalysisPgn` (frontend/src/lib/pgn.ts): serializes the whole analysis move tree, sidelines as
  RAV variations. Primary continuation = mainLine successor, else lowest-id child, so free play
  (empty mainLine) still gets a main line. STR headers with `?` placeholders; SetUp/FEN for non-standard roots.
- `gamePgnHeaders`: game-mode headers from the fetched game; Result derived from user_result + user_color.
- Menu: "Import PGN/FEN", "Copy PGN", "Copy FEN". PGN built lazily via a `getPgn` callback. Umami
  `board-tool` target `pgn-copy`. Clipboard failure = toast, no Sentry.
- Tests: 8 new serializer tests (including a chess.js loadPgn round-trip), 1 new menu tracking test.
- Gate: eslint, build (tsc -b), full vitest (5738 passed), knip all green.
- Browser UAT not completed: the Chrome extension disconnected mid-check.
