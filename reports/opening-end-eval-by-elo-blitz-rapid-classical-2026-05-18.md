# Stockfish Eval at End of Opening Phase — Blitz + Rapid + Classical, by ELO Bucket

**Date:** 2026-05-18
**Source:** benchmark DB (`flawchess-benchmark-db`, Lichess two-stage stratified sample)
**Scope:** all TCs **except bullet** (`tc_bucket IN ('blitz','rapid','classical')`), pooled per ELO bucket, all 5 ELO buckets (800 / 1200 / 1600 / 2000 / 2400)

## Definitions

- **End of opening phase** — middlegame-entry position: `MIN(ply)` where `game_positions.phase = 1`, one per game (the import pipeline's `middlegame_entry` definition, Lichess `Divider.scala`).
- **Eval** — Stockfish `eval_cp`, **user-POV signed** (`eval_cp` for the cohort user's White games, `−eval_cp` for Black). Positive = cohort player stands better entering the middlegame.
- **White / Black** — split by the cohort user's color in the game.
- **Opponent strength match filter** — canonical equal-footing filter on every game: `abs(opp_rating − user_rating) ≤ 100`, both ratings `NOT NULL`.
- **Aggregation** — game-level pooled across blitz + rapid + classical within each ELO bucket; `n` is the game count.

### Methodology (matches `reports/benchmarks-latest.md` conventions)

- Cohort via `benchmark_selected_users` ⋈ `benchmark_ingest_checkpoints` (`status='completed'`) ⋈ `users`.
- Per-cell TC anchoring: `g.time_control_bucket::text = su.tc_bucket` (a multi-TC user contributes each TC's games to that TC).
- Base filter: `g.rated AND NOT g.is_computer_game`.
- Eval row handling (benchmark D-08): drop `eval_mate IS NOT NULL`; drop `abs(eval_cp) ≥ 2000`. Footnoted, never folded in.
- **Sparse-cell exclusion (applied):** `(rating_bucket=2400, tc='classical')` is structurally pool-exhausted at the 2026-03 dump (12 completed users). The benchmark skill mandates excluding it from every pooled/marginal aggregate. Since this report pools across TC within each ELO bucket, the 2400 row here is **blitz + rapid only** (no classical). All other buckets include all three TCs. This is the only asymmetry between the 2400 row and the rest.

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

All cells far above any sample floor (smallest ≈ 38.7k games at 2400-White).

## Reading the numbers

- **Means are small and rating-flat.** White ≈ +27 to +33 cp, Black ≈ −16 to −28 cp at every level. The persistent White-positive / Black-negative offset is first-move advantage plus Stockfish's opening asymmetry (~25 cp engine baseline in the benchmark skill), not a skill effect — it does not grow with rating.
- **SD collapses monotonically with ELO**: White 340 → 259 → 202 → 156 → 121 cp; Black 337 → 258 → 200 → 155 → 121 cp. ~2.8× tighter from 800 to 2400. As in the rapid-only report, the ELO signal is *consistency at reaching a balanced middlegame*, not a better average position.
- White and Black SDs are within ~1% per bucket — opening volatility is color-independent.
- Pooling blitz + rapid + classical shifts means by only a few cp vs the rapid-only report and leaves the SD-collapse pattern unchanged; the result is robust to TC mix.

## Footnotes

**Per-(ELO, TC) composition of the pooled n** (kept games after all filters — shows the TC mix inside each pooled row):

| ELO | blitz | rapid | classical | pooled total |
|----:|------:|------:|----------:|-------------:|
| 800  | 51,824 | 40,242 |  6,065 |  98,131 |
| 1200 | 70,818 | 54,176 | 15,472 | 140,466 |
| 1600 | 76,504 | 60,287 | 19,086 | 155,877 |
| 2000 | 65,641 | 50,326 | 10,794 | 126,761 |
| 2400 | 51,619 | 26,017 | — (excluded) | 77,636 |

Blitz dominates the pool at every ELO; classical is the minority TC (and absent at 2400 by the sparse-cell rule). If you need TC held constant rather than pooled, use the rapid-only companion report or ask for a per-TC breakdown.

**Equal-footing retention** (MG-entry rows kept by the opponent filter vs all, per ELO×TC):

| ELO | blitz | rapid | classical |
|----:|------:|------:|----------:|
| 800  | 84.9% | 82.3% | 53.5% |
| 1200 | 89.6% | 88.6% | 72.0% |
| 1600 | 89.0% | 88.1% | 71.4% |
| 2000 | 78.5% | 74.1% | 57.9% |
| 2400 | 62.1% | 51.7% | — |

Matches documented benchmark behavior: mid-ELO retains high, strong cohorts (2000/2400) and classical drop more — exactly the matchmaking confound the filter is designed to remove. No included cell falls below the sample floor.

**Dropped rows** (within equal-footing set, excluded from mean/SD per D-08): mate drops total 554+121+524 (800) down to 38+21 (2400), decreasing sharply with rating. Non-mate outliers (`abs(eval_cp) ≥ 2000`) are negligible — at most 1 row in any cell (800-blitz, 1200-classical, 2400-blitz), 3 rows total across the whole dataset. All benchmark games are Lichess-analyzed, so there are zero NULL-eval MG-entry rows.

## Caveats

- `rating_bucket` is the per-TC median rating at the 2026-03 selection snapshot, not rating-at-game-time. Interpret bucket effects as **current-rating-cohort** effects. Each user contributes up to 1000 games per TC over a 36-month window.
- Game-level pooling weights high-volume users more heavily within a bucket; combined with blitz dominating the TC mix, the pooled means lean toward high-volume blitz players. The SD-collapse trend is far too strong to be an artifact of either, but exact means could shift a few cp under per-user or per-TC-balanced weighting.
- The 2400 row excludes classical (sparse cell); every other row includes all three TCs. The 2400 vs lower-bucket comparison is therefore blitz+rapid vs blitz+rapid+classical — immaterial for the SD trend, worth noting for precise mean comparisons.
