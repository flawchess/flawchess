---
id: SEED-042
status: dormant
planted: 2026-06-12
planted_during: v1.26 Full-Game Eval Pipeline
trigger_when: when touching opening insights, the import/normalization pipeline, or the games schema
scope: medium
---

# SEED-042: Custom-FEN games silently evict legitimate opening transitions from /api/insights/openings

## Why This Matters

Custom-FEN games (chess.com thematic tournaments and custom-position "Let's Play!"
games carrying `[SetUp "1"][FEN ...]` PGN headers, but standard rules) silently
drop **entire aggregated opening transitions** from a user's opening insights, not
just the single odd game.

Observed in prod (Sentry **FLAWCHESS-5E**): an Evans Gambit thematic position with a
50-game transition (W34/D0/L16) was dropped from insights because its chosen sample
representative was custom-FEN game `1345513`. The endpoint does not crash (the drop is
caught and Sentry-captured), so `Users Impacted: 0` — but real, popular lines vanish
from the feature output.

## Root Cause

1. **Filter gap:** `normalization.py` only excludes non-standard variants via
   `rules == "chess"`. Custom-position games use standard rules, so they pass.
2. **Import stores a mid-game ply 0:** `zobrist.py:170` uses `board = game.board()`,
   which honors the SetUp/FEN header. So the game's ply 0 is the custom mid-game
   position and `move_san[0]` is a mid-game move (e.g. `"Bxb4"`).
3. **Biased sample selection:** `query_opening_transitions` picks the sample
   representative via `func.min(ARRAY[ply, game_id])` (`openings_repository.py:667`) —
   shallowest ply wins. A custom-FEN game reaches a shared entry position at a
   *shallower* ply than standard games (it skips the opening half-moves baked into its
   FEN), so `MIN(ply)` **systematically prefers the custom-FEN game** as the
   representative whenever one exists for that `entry_hash`. (Prod case: entry reached
   at ply 7 in the custom game vs ~ply 13 in standard games.)
4. **Replay fails, whole transition dropped:** `_wrap_transition_row`
   (`opening_insights_service.py:491-511`) replays that representative's SAN prefix from
   a fresh `chess.Board()` (standard start). The prefix is unreachable, so `push_san`
   throws `IllegalMoveError`, the row returns `None`, and the **entire** transition
   (all 50 games) is dropped.

## When to Surface

**Trigger:** when touching opening insights, the import/normalization pipeline, or the
`games` schema. Natural fit alongside any milestone that revisits import or opening
analytics.

## Scope Estimate

**Medium** — a planned phase, not a quick task. Needs:

- Schema migration: add `has_custom_start: bool` to the `games` table.
- Import change: set the flag by detecting the `[SetUp "1"]`/`[FEN ...]` header in
  **both** the chess.com and lichess normalizers.
- Query change: exclude `has_custom_start` games' positions from
  `query_opening_transitions` (and `query_transition_prefixes`) so a standard game
  supplies the representative and SAN replay always succeeds.
- One-off backfill of the ~176 affected prod games.

**Do NOT** drop custom-FEN games entirely at import — they are valid standard-rules
games that legitimately participate in position matching (openings, endgames). Only
their use as a SAN-path representative is the problem.

## Related Quick Fix (independent, smaller)

Separate from this seed: the `capture_exception` in `_wrap_transition_row` models a
handled/expected drop as an escalating Sentry error. Demote it to
`capture_message(level="warning")` (keep the existing `set_context`/`set_tag`) so the
issue stops escalating while preserving rate visibility. Can ship independently as a
`/gsd-quick`.

## Breadcrumbs

- `app/repositories/openings_repository.py:667` — `func.min(ARRAY[ply, game_id])` sample selection
- `app/repositories/openings_repository.py:610-614` — existing comment acknowledging custom-FEN survivors (~176 / 344k ply-0 rows)
- `app/repositories/openings_repository.py:713` — `query_transition_prefixes`
- `app/services/opening_insights_service.py:491-511` — `_wrap_transition_row` replay + drop + Sentry capture
- `app/services/zobrist.py:170` — `board = game.board()` honors SetUp/FEN header
- `app/services/normalization.py:198` — chess.com variant filter (`rules == "chess"` only)
- `app/models/game.py` — `Game` model (no custom-start flag today)
- Sentry: FLAWCHESS-5E (issue 126278993)

## Notes

Captured 2026-06-12 from a Sentry FLAWCHESS-5E analysis. Full root-cause confirmed in
code, not inferred.
