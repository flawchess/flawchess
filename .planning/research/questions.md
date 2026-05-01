# Open Research Questions

Open questions surfaced during exploration that need data or investigation before they
can be settled. Append new entries at the bottom; mark resolved entries with **Resolved:**
and a one-line answer + link to where the answer lives.

---

## Q-001: Effective independent test count for opening insights, post-dedupe

**Asked:** 2026-04-28 (during `/gsd-explore` on opening-insight statistical framing)

**Context:** The Phase 70/71 opening-insights classifier scans every `(entry_hash, candidate_san)` transition with `N >= 20` across plies 3..16, then collapses results via `_dedupe_within_section` (deepest-opening wins per `resulting_full_hash`) and `_dedupe_continuations` (drop downstream chains). The remaining surface is what users see.

If we ever apply multiple-comparisons correction (BH-FDR or similar — see SEED-007), we need to know roughly how many *effectively independent* tests survive dedupe per user. This sets the corrected per-test alpha needed to keep overall FDR ≤ 10%.

Anecdotally Adrian estimated 5-30 lines per typical user. We want a real distribution.

**How to answer:** One SQL query against `flawchess-prod-db` (read-only, via `mcp__flawchess-prod-db__query`):

1. For each user with ≥1000 games, replicate the `query_opening_transitions` aggregate (HAVING `N >= 20` AND `(L/N > 0.55 OR W/N > 0.55)`) for both colors under default filters (no time-control restriction, no recency cutoff, opponent_strength=any).
2. Approximate dedupe by counting distinct `resulting_full_hash` values surviving the HAVING clause (cheap proxy — the actual `_dedupe_continuations` chain-collapse is harder to express in SQL, so the count is an overcount, but a useful upper bound).
3. Report: median, p90, p99 of surviving tuple count per user, broken out by total game count (1k / 3k / 10k+).

**Why deferred:** Today the surface is positioned as "candidate hint, not diagnosis", so per-test FDR isn't load-bearing. The question becomes load-bearing when SEED-007 fires (LLM narration over opening findings, or feedback shows over-claiming).

**Resolved:** _(open)_

---

## Q-002: Per-ply signed material balance — stored or computed?

**Asked:** 2026-05-01 (during `/gsd-explore` on Library page milestone, SEED-010)

**Context:** SEED-010's new material-delta filter ("show games where I reached ≥+X material sustained ≥4 plies, anywhere") is filtered on-the-fly from `game_positions` rather than via precomputed columns on `games`. The query needs per-ply signed material balance from one side's POV.

If the value is already a column on `game_positions`, the filter is a window function over an indexed integer column — cheap. If it's computed at query time from board state (FEN/hashes), the filter cost balloons and we should consider materializing it as a column.

**How to answer:**
1. Read `app/models/game_position.py` to inspect columns.
2. If absent, grep `app/services/import_service.py` and `app/services/normalization*` for any current material-balance computation that could be persisted.
3. If absent and not derived elsewhere, the SEED-010 milestone planner should add a `material_balance_white_pov SmallInteger` column on `game_positions` populated at import + backfilled via `reclassify_positions.py`.

**Why deferred:** answer determines milestone phase decomposition for SEED-010 (with vs. without a data-prep phase that adds the column). Not needed until that milestone starts.

**Resolved:** _(open)_

---

## Q-003: Middlegame transition definition for phase markers

**Asked:** 2026-05-01 (during `/gsd-explore` on Library page milestone, SEED-010)

**Context:** The Analysis page viewer shows phase markers (opening / middlegame / endgame) on the timeline. Endgame transition is already classified at import (`endgame_start_ply` or similar). Middlegame transition is less obvious — common definitions:

- "Out of book" (last ply matching an opening in the openings table)
- Fixed move number (e.g. ply ≥ 20)
- Both castled or both committed kings
- Some heuristic on minor-piece development

**How to answer:**
1. Inspect `app/models/game.py` and `app/services/normalization*` to confirm whether `middlegame_start_ply` or equivalent already exists.
2. If not, the SEED-010 milestone needs to pick a definition. Lowest-friction: derive from "out of book" using the openings table (we already track the deepest opening match per game). Falls back to a fixed-move-number floor (e.g. ply 16) if a game never matches an opening.

**Why deferred:** determines whether SEED-010 needs a new column + reimport. Not needed until that milestone starts.

**Resolved:** _(open)_

---

## Q-004: Per-ply clock storage — confirmed for both chess.com and lichess?

**Asked:** 2026-05-01 (during `/gsd-explore` on Library page milestone, SEED-010)

**Context:** The Analysis viewer shows remaining clock per ply for both players. chess.com PGN provides `%clk` annotations; lichess provides `clk` arrays. Both should be stored on `game_positions` at import.

**How to answer:** inspect `app/models/game_position.py` for clock column(s), and confirm both `app/services/import_service.py` paths (chess.com vs. lichess) populate them. Sample a few imported games of each platform in the dev DB to verify presence.

**Why deferred:** if either path doesn't store per-ply clocks today, SEED-010 needs a backfill phase. Not needed until that milestone starts.

**Resolved:** _(open)_

---

## Q-005: Lichess imported Stockfish eval coverage — what % of games?

**Asked:** 2026-05-01 (during `/gsd-explore` on Library page milestone, SEED-010)

**Context:** Tactical filters (missed forks/pins, blunder-driven losses) are deferred from SEED-010 v1, gated on imported Stockfish eval coverage being high enough to make the feature reliable. Today only a minority of lichess games have evals (chess.com imports never do). The eval-bar / eval-timeline UI in the v1 viewer also only renders when the loaded game has evals.

We need a real number on prod: across imported lichess games, what fraction have per-ply evals? Broken out by user (some users may have a much higher fraction if they enable lichess server analysis).

**How to answer:** one SQL query against `flawchess-prod-db` (read-only, via `mcp__flawchess-prod-db__query`):

1. Count `game_positions` rows with non-null Stockfish eval, grouped by `games.platform`.
2. Compute coverage = (positions with eval) / (total positions) per platform, and per user for the top-N most active users.
3. Also report: % of *games* with at least one eval (vs. just position-level coverage).

**Why deferred:** sizes the eventual tactical-filter feature. If coverage is <10% across users, tactical filters need the client-side engine pipeline before they're useful. If coverage is 30%+ for engaged users, an "evals-only" tactical filter could ship without the engine pipeline.

**Resolved:** _(open)_
