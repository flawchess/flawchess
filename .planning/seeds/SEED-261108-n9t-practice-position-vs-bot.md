---
id: SEED-261108-n9t
status: dormant
planted: 2026-11-08
planted_during: v2.27, phase 246 (training-features research session)
trigger_when: when planning the next Train or Bots feature milestone
scope: phase (v1 = Practice button + bot game from a given position, no scheduling)
depends_on: SEED-149
supersedes: narrows SEED-184 to a first step (SEED-184 stays the scheduled, graded version)
---

# SEED-261108-n9t: Practice a position against a bot

## Why This Matters

Train only drills single critical moves. Playing a position out against a human-like bot trains technique over many moves, and drawing the start positions from the user's own weak spots is something the 2026-11-08 research did not find elsewhere. Aimchess has generic convert/defend trainers, and maiachess.com starts Maia games after the opening, but neither uses the user's own games. It reuses existing assets: the 24 bots, the FlawChess Engine, and the "Moves that Cost You" findings.

## Decisions (owner, 2026-11-08)

- **v1 is a plain "Practice" button**, with no Train scheduling, grading or goals around it.
- **First surface: "Moves that Cost You" cards** (`OpeningFindings.tsx`), since the card already knows the position. The analysis board comes second.
- **Flow:** the user picks a bot, and a game starts from the given position.
- **Later (separate seed or phase):** a training feature with a weekly schedule and goals. Example goal: practice at least 3 games from a "move that cost you" position. A game passes if it continues for N moves without the eval dropping more than X. SEED-184 (convert/defend from the user's own squandered positions) is the same direction.

## Open Questions

- **Default bot:** a persona near the user's rating, or always ask?
- **Opening book:** each persona has a pinned book. Starting mid-opening, the book either covers the position (realistic) or drops out at once. Decide on purpose, don't leave it to chance.
- **Library:** do practice games land in the Library like other bot games? If yes, SEED-149 must ship first (see below).
- **Side to move:** the user plays the colour they had in the source position.

## Implementation Notes

- **Bots likely can't start from a position yet (not verified).** Bot games are played client-side and stored via `POST /bots/games` (`app/routers/bots.py`). No start-FEN parameter was seen on the bot path. The analysis side already handles custom starts (`games.initial_fen`, Phase 210).
- **SEED-149 is a prerequisite if practice games are stored.** `games.initial_fen IS NOT NULL` marks custom-start games, but only one aggregate (opening insights) excludes them today. Without SEED-149, practice games would flow into opening, endgame and library stats, and could even feed Train.
- **Analytics:** register a `trackFeature` event for the Practice button in `FeatureEventMap`.
- **Engine cost:** a playout runs the in-browser engine for many moves. Check the mobile and iOS budget (memory: iOS wasm reservation budget).

## Breadcrumbs

- `frontend/src/components/openings/stats/OpeningFindings.tsx`: "Moves that Cost You" cards
- `frontend/src/pages/Bots.tsx`, `frontend/src/components/bots/`: bot game surface
- `app/routers/bots.py`: bot game storage
- `app/models/game.py`: `initial_fen`
- `.planning/seeds/SEED-149-exclude-custom-start-games-from-analytics.md`
- `.planning/seeds/SEED-184-conversion-defender-trainer-vs-bot.md`
