# FlawChess Benchmarks — 2026-05-11

- **DB**: benchmark (Docker on `localhost:5433`, `flawchess_benchmark`)
- **Population**: 2,415 users / 1,327,623 rated games / 95,040,660 positions (same snapshot as 2026-05-10)
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; `tc_bucket` from same table; per-user TC restricted to selected `tc_bucket`
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user `g.time_control_bucket = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter)
- **Equal-footing filter (universal)**: `abs(opp_rating - user_rating) <= 100`. Applied to remove matchmaking confound.
- **Sparse-cell exclusion**: `(2400, classical)` excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d. Cell shown in cell-level tables with footnote.
- **Verdict thresholds**: Cohen's d < 0.2 collapse / 0.2–0.5 review / ≥ 0.5 keep separate
- **Sample floor**: ≥20 endgame-entry games per user per cell (matches §0)

---

## 5. Stockfish-baseline expected score at endgame entry

Per-game `expected_score` at the first endgame-class ply, computed from the Stockfish eval at that ply via the Lichess winning-chances sigmoid (`cp`) or direct 0/1 mapping (`mate`), from the user's perspective. Per-user `entry_xs = avg(expected_score)` over endgame-reaching games in the user's selected TC.

This metric answers: **"At endgame entry, what score does Stockfish predict for this player given the position they walked into?"** It separates the "where you start" signal (this metric, position quality at endgame onset) from the "what you do with it" signal (final endgame score). A user who consistently enters endgames with an expected score below cohort norm is reaching endgames from worse positions — either opening/middlegame errors, bad time management leading to inaccuracies, or systematic risk-taking that costs material before endgames.

### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `entry_expected_score` ZoneSpec | `typical_lower=0.45, typical_upper=0.55` | `app/services/endgame_zones.py` |
| `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN` | `0.45` | `frontend/src/generated/endgameZones.ts` |
| `ENTRY_EXPECTED_SCORE_NEUTRAL_MAX` | `0.55` | `frontend/src/generated/endgameZones.ts` |
| `entryExpectedScoreZoneColor()` | (generated) | `frontend/src/generated/endgameZones.ts` |

Band locked by operator (Phase 83 D-15 editorial call): chose `[0.45, 0.55]` over the strict pooled IQR `[0.4629, 0.5536]` for round numbers, near-IQR proximity, and visual parity with the `endgame_score` (§0 final-score) ZoneSpec which uses the identical band. `direction="higher_is_better"`.

### Cell table — per-user `entry_xs` `p25 / p50 / p75 (n)`

|       | bullet | blitz | rapid | classical |
|-------|--------|-------|-------|-----------|
| 800   | 0.40 / 0.50 / 0.56 (99)  | 0.44 / 0.49 / 0.54 (100) | 0.42 / 0.50 / 0.58 (96) | 0.39 / 0.48 / 0.54 (41) |
| 1200  | 0.43 / 0.49 / 0.55 (100) | 0.46 / 0.51 / 0.56 (99)  | 0.47 / 0.51 / 0.57 (100) | 0.43 / 0.52 / 0.57 (72) |
| 1600  | 0.43 / 0.49 / 0.56 (100) | 0.48 / 0.52 / 0.56 (100) | 0.48 / 0.52 / 0.56 (100) | 0.47 / 0.51 / 0.57 (85) |
| 2000  | 0.46 / 0.50 / 0.56 (100) | 0.48 / 0.52 / 0.55 (100) | 0.48 / 0.52 / 0.56 (98) | 0.49 / 0.52 / 0.55 (66) |
| 2400  | 0.47 / 0.51 / 0.54 (100) | 0.49 / 0.51 / 0.53 (100) | 0.49 / 0.52 / 0.55 (95) | 0.63 / 0.65 / 0.68 (n=2\*) |

`*` Sparse cell `(2400, classical)`: 2 users met the ≥20-game floor (12 completed users overall, most below floor). Excluded from marginals and pooled stats per universal SKILL convention.

### TC marginal (excl. sparse)

| TC        | n_users |   mean |    p05 |    p25 |    p50 |    p75 |    p95 |
|-----------|--------:|-------:|-------:|-------:|-------:|-------:|-------:|
| bullet    | 499     | 0.4998 | 0.3586 | 0.4478 | 0.5010 | 0.5533 | 0.6473 |
| blitz     | 499     | 0.5112 | 0.4100 | 0.4710 | 0.5115 | 0.5478 | 0.6238 |
| rapid     | 489     | 0.5171 | 0.4074 | 0.4725 | 0.5146 | 0.5606 | 0.6332 |
| classical | 264     | 0.5102 | 0.3640 | 0.4564 | 0.5087 | 0.5631 | 0.6688 |

### ELO marginal (excl. sparse)

| ELO  | n_users |   mean |    p05 |    p25 |    p50 |    p75 |    p95 |
|------|--------:|-------:|-------:|-------:|-------:|-------:|-------:|
| 800  | 336     | 0.4961 | 0.3252 | 0.4197 | 0.4929 | 0.5595 | 0.6836 |
| 1200 | 371     | 0.5080 | 0.3658 | 0.4509 | 0.5043 | 0.5624 | 0.6712 |
| 1600 | 385     | 0.5130 | 0.4063 | 0.4690 | 0.5119 | 0.5606 | 0.6331 |
| 2000 | 364     | 0.5155 | 0.4214 | 0.4789 | 0.5158 | 0.5547 | 0.6071 |
| 2400 | 295     | 0.5144 | 0.4430 | 0.4845 | 0.5122 | 0.5413 | 0.5987 |

### Pooled overall

| n_users |    mean |    p05 |        p25 |    p50 |        p75 |    p95 |
|--------:|--------:|-------:|-----------:|-------:|-----------:|-------:|
| 1,751   | **0.5094** | 0.3821 | **0.4629** | 0.5095 | **0.5536** | 0.6410 |

### Recommendations

- **Sanity check on equal-footing filter**: pooled p50 = 0.5095, pooled mean = 0.5094. Offset from 50% baseline is +0.94 pp — within the ±1 pp tolerance §0 also satisfies (its mean = 0.5123, +1.2 pp). Equal-footing filter is working; small positive offset is the residual benchmark skill edge (selected users average slightly above cohort match-quality at endgame entry).
- **Proposed cohort neutral band**: pooled `[p25, p75] = [0.4629, 0.5536]` ≈ **`[0.46, 0.55]`** (rounded to 2 decimal places). Asymmetric around 0.5 baseline by 0.04/0.05 — tracks the +0.94 pp cohort skill edge naturally.
- **Editorial tightening (D-15)**: **No editorial tightening recommended.** The pooled IQR width is 0.0907 (≈ 9 pp). Compared to Phase 82's `entry_eval_pawns` calibration where the pooled IQR was `[-0.56, +0.75]` pawns (width 1.31) and was tightened to ±0.50 (per memory `feedback_zone_band_judgement.md`), `entry_expected_score`'s pooled IQR is already narrow enough that meaningful signal reaches the colored zone. Tightening further would over-narrate small effects.
- **Routing**: This is a dedicated EG-entry score band — it does **not** share constants with the Openings score bullet's `SCORE_BULLET_NEUTRAL_*` (which is for the per-position WDL bullet on a different population). A new `entry_expected_score` entry in `ENDGAME_ZONES` registry is appropriate; the generated TS file gains `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN/MAX` and `entryExpectedScoreZoneColor`.

### Collapse verdict

- **TC axis**: `max |d| = 0.218` (bullet vs rapid) → **review** (≥ 0.2, < 0.5)
- **ELO axis**: `max |d| = 0.224` (800 vs 2000) → **review** (≥ 0.2, < 0.5)

Both axes' max d sit just above the 0.2 collapse threshold but well below the 0.5 keep-separate threshold. **Single global zone is justified.** Per-ELO stratification is deferred per CONTEXT.md "Deferred Ideas" — if a future snapshot shows ELO d ≥ 0.5, mirror `ENDGAME_SCORE_ZONES` per-ELO structure.

Heatmap of per-user `entry_xs` `p50` (excl. sparse):

```
           bullet   blitz   rapid   classical
  800       0.50    0.49    0.50    0.48
  1200      0.49    0.51    0.51    0.52
  1600      0.49    0.52    0.52    0.51
  2000      0.50    0.52    0.52    0.52
  2400      0.51    0.51    0.52     —*
```

The cohort centers tightly on ~0.50 across the (TC × ELO) grid. ELO ramp (800 → 2400) on the median is +0.02 (well below pooled IQR width 0.09), confirming the collapse verdict.

---
