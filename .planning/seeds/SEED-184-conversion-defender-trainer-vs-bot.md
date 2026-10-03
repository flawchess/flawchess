---
id: SEED-184
status: dormant
planted: 2026-10-03
planted_during: no open milestone (after v2.21), Phase 228 (settings page) ready to execute; /gsd-explore training features
trigger_when: when planning the next Train feature milestone, or after the weekly Train leaderboard ships
scope: large (needs its own /gsd-explore first; likely 2+ phases)
---

# SEED-184: Conversion/defender trainer against a bot

Start the user in a winning position (convert it) or a losing/worse position (hold it)
taken from their OWN games, and have them play it out against a Maia-driven human-like
bot at their rating. Grade by the result (win/draw/loss, or eval held) rather than by a
single best move.

## Why This Matters

- Train is the only feature with daily return (growth report 2026-10-03: ~37 completed
  sessions/day, 76-100 weekly trainers since the Next Level Chess newsletter). New
  training modes are the lever for retention.
- Aimchess has the same idea as "Advantage Capitalization" and "Defender" trainers,
  but on generic positions (https://aimchess.com/). Ours would use the user's own
  squandered positions against a bot that defends like a real player at their level,
  which nobody else does as far as the 2026-10-03 research found.
- It is the one idea that combines three existing assets: `game_flaws` (squandered /
  reversed flags), the 24 human-like bots + FlawChess Engine, and the endgame
  conversion/recovery stats (a natural "train your weakest endgame class" entry point).
- It trains a skill the tactical drill cannot: technique over many moves, not one
  critical move.

## Evidence (prod, 2026-10-03)

- Supply is ample: median **232 games per active trainer** (registered, completed a
  session in the last 14 days, n=107) contain an `is_squandered` flaw.
- For comparison, the median active trainer has ~1,200 own blunders with an answer key,
  so the existing drill is not supply-limited either; this is about format, not content.

## Open design questions (for a dedicated /gsd-explore)

- **Format:** separate mode vs one "boss position" per Train session. A playout takes
  2-5 minutes, not a 30-second puzzle, so it does not slot in as just another puzzle.
- **Position selection:** eval band at the start (e.g. +2 to +5 for convert, -1 to -3
  for defend), game phase (endgame-only first?), the position before the squandering
  move vs N plies earlier.
- **Bot strength:** user's rating vs a chosen persona; Trickster/Wall styles map
  naturally onto defend/convert.
- **Grading and scheduling:** result-based grading; how a played-out position enters
  spaced repetition (retry the same position until converted?).
- **Interplay:** does it count toward the streak and the weekly leaderboard?
- **Engine cost:** a full playout runs the in-browser engine for many moves; check
  mobile/iOS budget (see memory on iOS wasm reservation budget).

## Breadcrumbs

- `app/services/train_pool.py` — pool-entry SQL (winnability floor, ply-parity gate)
- `app/repositories/train_repository.py` — session composition and materialization
- `app/models/drill_item.py`, `app/models/drill_solve.py` — SR item / solve models
- `frontend/src/pages/Bots.tsx` — bot play surface
- `reports/growth/growth-recommendations-2026-10-03.md` — Train retention context
- Related: SEED-114 (stronger bots above 1900)
