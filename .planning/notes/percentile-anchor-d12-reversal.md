---
title: Percentile anchor — D-12 reversal (game-weighted blended)
date: 2026-05-27
context: Phase 94.4 amendment, surfaced during /gsd-explore
supersedes: D-12 (Lichess-precedence rule) in 94.4-CONTEXT.md §Post-research user decisions
---

# Percentile anchor — D-12 reversal (game-weighted blended)

## The problem

Phase 94.4's original D-12 rule: "any Lichess games in TC ⇒ Lichess source for the anchor". For a user with N lichess games and M chess.com games in a TC (N ≥ 1), the anchor was the user's lichess median rating — full stop. Chess.com→Lichess conversion only fired as a fallback when N = 0.

But the metric value that anchor is used to look up (per `canonical_slice_sql.per_user_cte_score_gap_tc`) pools games **across both platforms** with no per-platform cap. Typical FlawChess user: M ≫ N (way more chess.com games than lichess). The metric value is overwhelmingly chess.com-shaped, but D-12 anchored that value to the user's lichess ladder position — which can be wildly different.

Concrete: user has 4000 chess.com blitz @ 2200 (≈2050 lichess via ChessGoals) and 100 lichess blitz @ 1900.
- **D-12 anchor**: 1900 (pure lichess median)
- **Blended anchor**: (4000·2050 + 100·1900) / 4100 ≈ **2046**

That's a ~150-Elo difference, ~3 grid steps in the 50-Elo cohort-CDF. The user's metric was computed from mostly 2200-strength chess.com play; 2046 (lichess-equivalent) is the representative anchor, 1900 is not.

## The fix

Per-game conversion + pooled median:

1. For each canonical-slice game in the TC, take rating-at-game-time:
   - lichess game → as-is
   - chess.com non-Daily → convert via ChessGoals per-TC table
   - chess.com Daily → drop from anchor pool (conversion undefined); game still feeds the metric
2. Pool the converted-chess.com + native-lichess ratings into one set.
3. Median → anchor.

Naturally game-count weighted. Handles within-window rating drift gracefully (e.g. user who climbed 300 Elo over 18 months gets a median that reflects their play distribution, not their latest snapshot).

## Why this isn't a retreat from "ladder purity"

D-12's stated motivation was "mixes-two-ladders avoidance." But the fallback already accepted ChessGoals conversion — pure-chess.com users got a converted anchor. The current rule applies conversion only when lichess is empty, an arbitrary cutoff. The blended rule applies the conversion **uniformly** across all users. More principled, not less safe. If you accept ChessGoals as the bridge in the fallback case, you've already accepted it as the bridge; D-12's exception was inconsistent.

## Risk profile (why this is surgical)

- **Pure-lichess users** (N > 0, M = 0): unchanged. No conversion in play, anchor = lichess median.
- **Pure-chess.com users** (N = 0, M > 0): get nearly identical anchors to today. Median commutes with the ChessGoals monotonic mapping within a single piecewise segment, so `median(map(games))` ≈ `map(median(games))` for most users.
- **Mixed-platform users** (N > 0, M > 0): anchor shifts toward the platform contributing more games. **Exactly the population the original concern targeted.**

So the fix doesn't disturb users who weren't affected; it corrects only the population that was being misanchored.

## What stays the same

- The benchmark CDF itself is built from Lichess monthly dumps (`scripts/select_benchmark_users.py`) and remains lichess-rated. The anchor change is **user-side only** — how we choose the Elo to index into the CDF. The cohort definition is untouched.
- ChessGoals snapshot (`CHESSCOM_BLITZ_TO_LICHESS` family, per-TC) is the same conversion source D-12 already used. Same conversion, applied more consistently.
- The 50-Elo grid and the ±150-Elo cohort window are unchanged.
- Existing suppression rules carry over: a user with no non-Daily chess.com games and no lichess games in the TC still has no anchor.

## Caveats / known imperfections

- **Conversion tail uncertainty.** ChessGoals is well-calibrated 1200–2200 chess.com; below ~1000 and above ~2300 the mapping is sparser. The blended rule makes converted anchors *more frequent* across the user base. This is a known limitation — already accepted under D-12's fallback path, just more often triggered now. Long-term fix: forward-fit conversion from internal data once dual-platform N is sufficient (already deferred in 94.4 §Deferred Ideas).
- **Chess.com Daily asymmetry.** Daily games contribute to the metric but not to the anchor (conversion undefined). For Daily-heavy users this is an inconsistency. The alternative — suppress the whole chip whenever the user has any Daily play — is worse. Document, don't fix.
- **Median commutativity assumption for pure-chess.com users.** Holds within a single ChessGoals piecewise segment. A user whose games straddle a segment boundary will see a tiny shift (typically ≤20 Elo) vs the D-12 fallback anchor. Below noise.

## Schema impact

`user_rating_anchors` reshapes (drop-and-recreate, no data preservation):

```
user_id                  INTEGER FK → users.id
time_control_bucket      tc_bucket_enum
anchor_rating            INTEGER          -- blended median (lichess-equivalent)
n_chesscom_games         INTEGER
n_lichess_games          INTEGER
chesscom_median_native   INTEGER NULL     -- tooltip disclosure
lichess_median_native    INTEGER NULL     -- tooltip disclosure
PRIMARY KEY (user_id, time_control_bucket)
```

`source_platform` and `chesscom_raw_rating` are dropped. The two native medians are preserved purely so the tooltip can truthfully disclose composition ("blending N chess.com games at median ≈Y with M lichess games at median ≈Z").

Both `user_rating_anchors` and `user_benchmark_percentiles` are TRUNCATEd and recomputed at phase end. They're derived tables; no user-facing data loss.

## Tooltip implication

The `feedback_percentile_chip_tooltip_disclosure` memory's 4-bullet contract was already flagged in 94.4 §Deferred Ideas for a post-merge update (the 4th bullet flipping from rating-correlation to rating-anchor disclosure). This amendment makes that update slightly larger — the tooltip now needs to disclose the *composition* of the anchor, not just its value. Still falls under the same memory update follow-up.

## Cross-reference

Full amendment with implementation touchpoints + planner discretion notes lives at:
- `.planning/phases/94.4-peer-relative-percentile-chip-refinement/94.4-CONTEXT.md` §Amendment — D-12 Reversal: Game-Weighted Blended Anchor (2026-05-27)
