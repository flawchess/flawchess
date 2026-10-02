---
id: SEED-175
status: dormant
planted: 2026-09-29
planted_during: Phase 226 executing (SEED-171); /gsd-explore session
trigger_when: after Phase 226 (browser engine throughput) merges to main, since both touch the engine-lines/arrow wiring
scope: medium (one frontend-only phase; no backend)
---

# SEED-175: Settings page (sound toggle + per-engine lines/arrows)

## Why This Matters

Sound has had no off switch since Phase 223 retired the account-menu toggle. Its
`lib/sounds.ts` header says a later phase should ship "a proper disable option",
and the plumbing was left in place for that phase. Engine line and arrow counts
are hard-coded (2 card lines, 1 arrow per engine). Users who want more Stockfish
lines, or fewer arrows cluttering the board, cannot change that. A cogwheel
settings page gives both a home and leaves room for later board and piece
preferences.

## When to Surface

**Trigger:** after Phase 226 merges to main. Phase 226 reworks the engine
dispatch/grading paths that the line/arrow settings feed into, so planning this
before it lands would target moving code.

## Scope Estimate

**Medium**: one frontend-only phase. The page and the typed settings module are
small. The work is in threading the counts through the cards, arrows and
MultiPV, and in the badge/arrow restyle.

## Locked decisions (from /gsd-explore 2026-09-29)

**Entry point:** cogwheel icon in the header. The route `/settings` is an
assumption; the user did not name one. Placement in the desktop header and in
the mobile nav is still to be decided.

**Persistence:** localStorage only (per device, works for guests, no backend).
Build a small typed settings module (`useSyncExternalStore`, the same shape as
`useMuted` in `lib/sounds.ts`), so a later swap to account sync touches only
that module.

**Settings:**

| Setting | Range | Default |
|---|---|---|
| Sound | on/off | on |
| FlawChess engine lines | 1-5 | 2 |
| FlawChess engine arrows | 0-3 | 1 |
| Stockfish lines | 1-5 | 2 |
| Stockfish arrows | 0-3 | 1 |

- Lines and arrows are **separate** settings per engine. Both engines render at
  the same time, so a user may want e.g. more Stockfish card lines without more
  arrows.
- 0 arrows hides that engine's arrows while keeping its card.
- Sound reuses the existing `useMuted`/`setMuted` in `frontend/src/lib/sounds.ts`
  (key `flawchess_bot_sound_muted`). They have had no production caller since
  Phase 223.

**Surfaces:**
- `/analysis`: both engines.
- Train puzzle reveal, free-play mode: Stockfish settings only (Train does not
  use the FlawChess engine).

**Styling:** the primary line is solid; **all** non-primary lines use one
fairly translucent color per engine (translucent blue for Stockfish, translucent
gold for FlawChess), on both board arrows and card badges. No eval-proportional
transparency (lichess doesn't do it either). This replaces the FlawChess card's
three rank-based `FLAWCHESS_ENGINE_BADGE_SHADES` and Stockfish's light-blue
second-best badge/arrow.

**Out of scope:**
- Search time and thread settings. The FlawChess engine budget is a node cap
  (`FLAWCHESS_ENGINE_MAX_NODES = 400`) that defines what the engine is. Pool
  size is device-bounded by the iOS budget of about 3 wasm reservations per
  page, and Phase 226 is still tuning it. A Stockfish-only "search longer"
  toggle could be reconsidered once Phase 226 has settled.
- Board colors, piece sets, sound sets.

## Breadcrumbs

- `frontend/src/lib/sounds.ts`: `MUTE_KEY`, `useMuted`, `setMuted`,
  `playSound` (honours a persisted `'1'`).
- `frontend/src/components/analysis/EngineLines.tsx:38`: `MAX_LINES = 2`;
  badge color by rank at ~266 (`BEST_MOVE_ARROW` / `SECOND_BEST_ARROW`).
- `frontend/src/components/analysis/FlawChessEngineLines.tsx:48`:
  `MAX_LINES = 2`; `FLAWCHESS_ENGINE_BADGE_SHADES` from `lib/theme`.
- `frontend/src/hooks/analysis/useAnalysisBoardArrows.ts:60`: `ARROW_COUNT = 1`.
- `frontend/src/hooks/analysis/useAnalysisEngineLines.ts`: imports both
  `MAX_LINES`; SF card sourced from the grading run via
  `ranked.slice(0, SF_MAX_LINES)`.
- `frontend/src/pages/Analysis.tsx`: `FC_MAX_LINES` slice at ~931.
- `frontend/src/hooks/useStockfishEngine.ts`: `MULTIPV = 2`,
  `MOVETIME_MS = 1500`, `MAX_NODES`.
- `frontend/src/hooks/useTrainFreePlay.ts` + `components/train/TrainReveal.tsx`:
  Train free-play Stockfish search and card.
- `frontend/src/App.tsx`: header/nav (lucide icons imported at line 13).

## Verify in planning

- **Train free-play cost:** `useTrainFreePlay` runs `useStockfishEngine` at a
  fixed `MULTIPV = 2`. Stockfish lines above 2 there mean
  MultiPV = max(SF lines, SF arrows), so each line gets less depth in the same
  movetime.
- **Analysis cost:** on `/analysis` the SF card reads from the shared grading
  run, so extra lines are likely near-free. Confirm the free-search MultiPV
  still matters for the arrows there.
- **FC line count:** check that `flawChessEngine.rankedLines` reliably yields
  up to 5 lines (it is bounded by the candidate count).
- **Stale constants:** tests pin `MAX_LINES = 2` (e.g.
  `FlawChessEngineLines.test.tsx`). Update them to read the setting's default.
