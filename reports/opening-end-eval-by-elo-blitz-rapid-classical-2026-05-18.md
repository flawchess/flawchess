# Stockfish Eval at End of Opening Phase — Blitz + Rapid + Classical, by ELO Bucket

**Date:** 2026-05-18
**Source:** benchmark DB (`flawchess-benchmark-db`, Lichess two-stage stratified sample)
**Scope:** all TCs except bullet, pooled per ELO bucket, all 5 ELO buckets (800 / 1200 / 1600 / 2000 / 2400)

## Method

- **End of opening phase:** middlegame-entry position — `MIN(ply)` where `game_positions.phase = 1`, one per game.
- **Eval:** Stockfish `eval_cp`, user-POV signed (positive = cohort player stands better entering the middlegame).
- **Filters:** rated, non-computer games; equal-footing filter `abs(opp_rating − user_rating) ≤ 100` (both NOT NULL); drop `eval_mate IS NOT NULL` and `abs(eval_cp) ≥ 2000` (benchmark D-08).
- **Aggregation:** game-level pooled across blitz + rapid + classical within each ELO bucket; `n` is the game count.
- **Sparse-cell exclusion:** `(2400, classical)` is pool-exhausted and excluded — the 2400 row is blitz + rapid only; all other rows include all three TCs.

## Results — White (cohort user playing White)

| ELO bucket | n games | mean (cp) | SD (cp) |
|-----------:|--------:|----------:|--------:|
| **800**  | 49,003 | **+26.7** | 339.6 |
| **1200** | 70,337 | **+32.8** | 258.6 |
| **1600** | 78,123 | **+31.9** | 202.0 |
| **2000** | 63,578 | **+32.9** | 156.1 |
| **2400** | 38,728 | **+31.8** | 121.1 |

## Results — Black (cohort user playing Black)

| ELO bucket | n games | mean (cp) | SD (cp) |
|-----------:|--------:|----------:|--------:|
| **800**  | 49,128 | **−26.4** | 336.7 |
| **1200** | 70,129 | **−15.7** | 257.5 |
| **1600** | 77,754 | **−19.8** | 199.9 |
| **2000** | 63,183 | **−19.2** | 155.3 |
| **2400** | 38,908 | **−27.5** | 120.7 |

## Reading the numbers

- **Means are small and rating-flat.** White ≈ +27 to +33 cp, Black ≈ −16 to −28 cp at every level. The White-positive / Black-negative offset is first-move advantage plus Stockfish's opening asymmetry (~25 cp engine baseline), not a skill effect — it does not grow with rating.
- **SD collapses monotonically with ELO:** White 340 → 259 → 202 → 156 → 121 cp; Black 337 → 258 → 200 → 155 → 121 cp (~2.8× tighter from 800 to 2400). The ELO signal is *consistency at reaching a balanced middlegame*, not a better average position.
- White and Black SDs are within ~1% per bucket — opening volatility is color-independent.
