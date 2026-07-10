---
quick_id: 260710-x3d
status: complete
date: 2026-07-10
commit: edce3687
---

# Quick Task 260710-x3d — Summary

## What changed

Replaced the `/analysis` free-play entry point's `?fen=` snapshot param with a
`?line=` param carrying the opening's moves as comma-separated UCI from the
standard start. The analysis board seeds these as its main line with the cursor
at the end, so the user can step all the way back to move 1 in the variation
tree. Game mode (`?game_id=&ply=`) was **kept** (user-confirmed) — it loads
imported games with flaw/tactic sidelines, eval chart and auto-flip, none of
which a URL move list can carry.

## Files

- `frontend/src/lib/analysisUrl.ts` — removed `buildAnalysisUrl`/`FEN_PARAM`;
  added `buildAnalysisLineUrl(sans)` (SAN→UCI) and `parseAnalysisLineParam(param)`
  (UCI→SAN, stops at the first illegal token so a bad URL degrades to its legal
  prefix). `buildGameAnalysisUrl` unchanged.
- `frontend/src/lib/analysisUrl.test.ts` — rewrote for the new helpers
  (round-trip, empty, illegal-stop, promotion, URL-safety).
- `frontend/src/pages/Openings.tsx` — analyze button passes
  `chess.moveHistory.slice(0, chess.currentPly)`.
- `frontend/src/pages/Analysis.tsx` — read `?line=`, seed the free-play main line
  once, free-play reset now keeps the seeded opening (clear sidelines + return to
  end) or wipes to bare start when no line; docblocks updated.
- `frontend/src/App.tsx` — `AnalysisRoute` keys on `?line=` so a second
  navigation remounts and re-seeds.
- `frontend/src/pages/__tests__/Analysis.test.tsx` — `?fen=` tests → `?line=`
  (seeds main line, malformed degrades, Maia orientation via line URLs).
- `CHANGELOG.md` — `[Unreleased] › Changed` bullet.

## Design decisions

- **UCI, not SAN, in the URL** — URL-safe with no encoding (SAN drags in `+`, `#`,
  `=`, `O-O`).
- **Cursor at end of line** — `loadMainLine` already lands the cursor on the last
  node; no extra work.
- **Malformed `?line=` degrades to the legal prefix** — mirrors the old FEN guard's
  defensive posture and `loadMainLine`'s "stop on illegal SAN" tolerance.

## Deviation from the task as phrased

The task said "the game mode … probably becomes obsolete and can be removed as
well." Flagged that game mode is a distinct, non-obsolete feature (flaw/tactic
sidelines, eval chart, auto-flip; used by LibraryGameCard + FlawCard). User
confirmed via AskUserQuestion to **keep game mode**; only the `fen` path was
replaced.

## Verification

- `npx tsc -b` — clean.
- `npm run knip` — clean.
- `npm run lint` — 0 errors (3 warnings in generated `coverage/`, pre-existing/unrelated).
- `npm test -- --run` — 139 files, 1749 tests passing.

Commit: `edce3687`
