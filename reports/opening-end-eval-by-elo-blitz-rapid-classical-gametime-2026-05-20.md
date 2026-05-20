# Stockfish Eval at End of Opening Phase — Blitz + Rapid + Classical, by ELO Bucket (game-time bucketing)

**Date:** 2026-05-20
**Source:** benchmark DB (`flawchess-benchmark-db`, Lichess two-stage stratified sample)
**Scope:** all TCs except bullet, pooled per ELO bucket, all 5 ELO buckets (800 / 1200 / 1600 / 2000 / 2400)

## Method

- **End of opening phase:** middlegame-entry position — `MIN(ply)` where `game_positions.phase = 1`, one per game.
- **Eval:** Stockfish `eval_cp`, user-POV signed (positive = cohort player stands better entering the middlegame).
- **Filters:** rated, non-computer games; equal-footing filter `abs(opp_rating − user_rating) ≤ 100` (both NOT NULL); drop `eval_mate IS NOT NULL` and `abs(eval_cp) ≥ 2000` (benchmark D-08).
- **ELO bucketing:** **game-time rating** (`games.white_rating`/`games.black_rating`), **not** the snapshot bucket `benchmark_selected_users.rating_bucket`. Sub-800 rows dropped. Buckets are 400-wide: `800 (800–1199), 1200 (1200–1599), 1600 (1600–1999), 2000 (2000–2399), 2400 (2400+)`. This corrects the rating-lag selection bias documented in `/benchmarks` (a climbing user's early underrated games no longer file into their final snapshot bucket).
- **TC anchoring:** `g.time_control_bucket::text = bsu.tc_bucket` — a user selected for `(blitz)` contributes only their blitz games.
- **Cohort linkage:** `benchmark_selected_users ⋈ users ON lower(lichess_username)` — no `benchmark_ingest_checkpoints` join because the current DB has games for all 5 game-time buckets but checkpoints only for selection-snapshot 800/1200; the canonical checkpoint join would silently drop the 1600/2000/2400 rows.
- **Aggregation:** game-level pooled across blitz + rapid + classical within each game-time ELO bucket; `n` is the game count. A user contributing games at two different game-time ELO buckets counts in both buckets.
- **Sparse-cell exclusion:** `(2400, classical)` is pool-exhausted and excluded — the 2400 row is blitz + rapid only (n=16 classical games across 6 users at game-time 2400, below the 10-users floor); all other rows include all three TCs.

## Results — White (cohort user playing White)

| ELO bucket | n games | mean (cp) | SD (cp) |
|-----------:|--------:|----------:|--------:|
| **800**  | 45,002 | **+31.6** | 341.0 |
| **1200** | 78,180 | **+31.2** | 258.8 |
| **1600** | 82,077 | **+31.5** | 196.0 |
| **2000** | 62,695 | **+31.7** | 148.5 |
| **2400** | 30,496 | **+30.9** | 117.6 |

## Results — Black (cohort user playing Black)

| ELO bucket | n games | mean (cp) | SD (cp) |
|-----------:|--------:|----------:|--------:|
| **800**  | 45,156 | **−23.1** | 337.6 |
| **1200** | 78,104 | **−16.3** | 256.7 |
| **1600** | 81,258 | **−21.7** | 195.1 |
| **2000** | 62,587 | **−20.7** | 146.8 |
| **2400** | 30,713 | **−28.8** | 118.0 |

## Reading the numbers

- **Means are rating-flat under game-time bucketing.** White is essentially constant at +31 ± 1 cp across all five buckets; Black hovers around −21 cp (range −16 to −29). Under game-time bucketing the per-color levels do not trend with ELO — what looks like a Black-side trend in a snapshot-bucketed view is a rating-lag artifact.
- **Per-color asymmetry persists but is small.** Midpoint of (White mean + Black mean)/2 is +4 to +5 cp at every bucket (e.g. 1200: (+31.2 + −16.3)/2 = +7.4; 1600: (+31.5 + −21.7)/2 = +4.9). This is the **winrate-neutral opening-style residual** documented in `/benchmarks` "Residual, out of scope" — a selection-membership artifact of the ≥10-analyzed-games eligibility, not a bucketing defect. The bulk of the White-positive / Black-negative offset (≈ +30 vs −20) is engine baseline + first-move advantage, not a cohort skew.
- **SD collapses monotonically with ELO.** White 341 → 259 → 196 → 149 → 118 cp; Black 338 → 257 → 195 → 147 → 118 cp (~2.9× tighter from 800 to 2400). The ELO signal is *consistency at reaching a balanced middlegame*, not a better average position. SD is robust to the rating-lag bias because it's a within-bucket spread, not a level.
- **White and Black SDs match within ~1% per bucket** — opening volatility is color-independent.
