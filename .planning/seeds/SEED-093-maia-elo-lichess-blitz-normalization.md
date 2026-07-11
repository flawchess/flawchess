---
title: Maia ELO slider default — normalize player ratings to Lichess-blitz equivalent
trigger_condition: Next /gsd-new-milestone selection, or promote directly to a small phase; ready to plan
planted_date: 2026-07-11
source: /gsd-explore session 2026-07-11 (Adrian's proposal + design convergence)
---

# SEED-093: Maia ELO Lichess-blitz normalization

When the analysis board opens for a game, the Maia ELO slider default and the per-player Maia
ELO are set from the players' **raw** ratings at game time (`useMaiaEloDefault.ts` →
`deriveRawDefault`, reading `gameData.white_rating` / `black_rating`, clamped to the 600–2600
ladder). But Maia-3 was trained on **Lichess-blitz** games
([arxiv 2605.19091](https://arxiv.org/pdf/2605.19091)), so a rating on any other scale mis-sets
both the slider and Maia's move prediction:

- **chess.com** ratings run systematically ~150–250 **below** the Lichess-blitz equivalent.
- **Lichess non-blitz** ratings run **above** Lichess-blitz — ~200 at the low end (Lichess-Blitz
  1030 ↔ Lichess-Rapid 1205; 1145 ↔ 1340), shrinking higher up.

We already own the conversion tables (`app/services/chesscom_to_lichess.py`, ChessGoals snapshot
2026-05-27); this seed reuses them to normalize every player rating to a Lichess-blitz equivalent
before it reaches the slider. This is the machinery [[project_flawchess_engine_prior_art]] flagged
as "per-move clock/skill conditioning" and that SEED-091 (bot play) already **assumes exists** for
its save-time player-rating conversion — so building it here unblocks that too.

## Design (converged in the explore session)

**Normalize everything to Lichess-blitz. Backend computes it; frontend reads a number.**

| Game source | TC | Path to Lichess-blitz |
|---|---|---|
| chess.com | blitz | Table 2 `blitz` column (existing `convert_chesscom_to_lichess(r, "blitz", "blitz")`) |
| chess.com | bullet / rapid | invert Table 1 → chesscom-blitz anchor → Table 2 `blitz` column (existing chain, target `blitz`) |
| chess.com | daily | `None` → caller falls back to raw rating |
| Lichess | blitz | identity (already the target scale) |
| Lichess | bullet / rapid / classical | **new:** invert Table 2 on that Lichess column → chesscom-blitz anchor → read Table 2 `blitz` column |
| Lichess | correspondence / out-of-range | `None` → raw fallback |

**Key insight (no new table needed).** Table 2 (`CHESSCOM_BLITZ_TO_LICHESS`) lists all four Lichess
columns against each chesscom-blitz anchor, so every row's `(rapid, blitz)` / `(bullet, blitz)` /
`(classical, blitz)` pair *is* the Lichess-intra-TC correspondence for free. We do **not** need
ChessGoals "Table 3" — inverting Table 2 on the source Lichess column recovers the same mapping.
(Verified on line 131: chesscom-blitz 1000 → Lichess-blitz 1420 / Lichess-rapid 1615, a +195 gap
matching Table 3 exactly.)

**Backend work**
- Generalize the inversion primitive in `chesscom_to_lichess.py`: `_invert_intra_tc` currently
  inverts only the two chess.com columns of Table 1. Extend/parameterize it (or add a sibling) to
  invert on any Lichess column of Table 2, returning the chesscom-blitz anchor. Then read that
  row's `blitz` column. Same `_interp_int_column` linear-interp + monotonicity + None-gap +
  clamp-to-published-range discipline as today.
- Add one public entry, e.g. `normalize_to_lichess_blitz(rating, platform, source_tc) -> int | None`,
  that dispatches per the table above. `platform: Literal["chess.com", "lichess"]`,
  `source_tc: Literal[...]` per platform. Returns `None` (not a guess) for daily / correspondence /
  out-of-published-range, so the caller falls back to the raw rating.
- Full unit coverage per source path, including the new Lichess-intra inversions and every
  `None`/fallback edge. This is model-facing math — the tests are the point.

**Expose to the frontend**
- Add `white_rating_lichess_blitz` / `black_rating_lichess_blitz` (nullable ints) to the game data
  the analysis board already loads. **Both colors** — side-to-move varies, and `deriveRawDefault`
  picks the mover's color.
- **Additive, never replacing.** The existing raw `white_rating` / `black_rating` fields stay
  untouched. The analysis page must keep displaying the **original platform/TC-specific player ELO**
  (the game's real rating, e.g. "1720 chess.com blitz") — that display reads the raw field
  (`Analysis.tsx:2056`) and does not change. Only the Maia slider default (`useMaiaEloDefault`)
  consumes the normalized `*_lichess_blitz` field. So a game can show the player's real 1720 in the
  header while the slider seats Maia at, say, ~1900 Lichess-blitz-equivalent — two different numbers
  serving two different purposes, both visible.
- **Open sub-decision (settle at plan time): on-read vs stored.** Lean = compute on-read during
  API serialization: it's a pure function of `(platform, tc_bucket, rating)` already on the `games`
  row, so no migration and no backfill. Stored columns (computed at import) are the alternative if
  a query needs to filter/sort on it later — not currently needed.

**Frontend work**
- Add the two nullable fields to `MaiaEloGameData` (and the underlying game-data type).
- `useMaiaEloDefault.ts` `deriveRawDefault`: read the normalized field for the side-to-move color,
  **fall back to raw `white_rating`/`black_rating` when `None`**. Keep the ladder clamp
  (`clampToLadderBounds`), the user-override lock (`userOverrodeRef`), and free-play behavior
  (`profile.current_rating` / 1500) unchanged.

## Scope / routing

Cross-stack but small: one generalized backend helper + one dispatch function + tests, two computed
serialized fields, one frontend hook change + type + hook test. Recommended as a **light proper
phase** rather than `/gsd-quick` — the model-facing conversion math wants planner/checker test rigor,
and the serialization touchpoint (where analysis-board game data is assembled) wants the
phase-researcher step. `/gsd-quick` is viable if doing that exploration inline.

## Edge cases to carry into the plan

- Out-of-published-range ratings (below ~500 / above ~3000 chesscom-blitz equivalent): converter
  returns `None` → raw fallback, never an extrapolated guess.
- chess.com daily and Lichess correspondence: `None` → raw fallback.
- Guests / games with NULL ratings: nothing to normalize; existing free-play/1500 path applies.
- Don't snap the normalized value to ladder rungs — `useMaiaEngine` already picks the nearest rung
  at read time; keep the unsnapped clamp.

## Related

- SEED-091 (bot play) assumes this conversion exists for save-time player-rating recording — this
  seed delivers the shared machinery.
- [[project_flawchess_engine_prior_art]] — per-move skill conditioning as an unclaimed hook.
