# FlawChess Benchmarks — 2026-05-17

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-17
- **Population**: 2,415 users / 1,375,544 games / 95,040,660 positions; 1,912 completed (user, TC) checkpoints across 20 cells
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; tc_bucket from same table; per-user TC restricted to selected tc_bucket
- **Selection provenance**: 2026-03 Lichess monthly dump, 9,523 selected (lichess_username, tc_bucket) rows in the candidate pool; 1,912 ingested at the ≈100/cell target
- **Per-user history caveat**: `rating_bucket` is per-TC median rating at selection snapshot; each user contributes up to 1,000 games per TC over a 36-month window at varying ratings; "ELO bucket effect" = "current rating cohort effect" rather than "rating-at-game-time effect"
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket::text = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter)
- **Equal-footing filter (universal — all subchapters)**: `abs(opp_rating - user_rating) <= 100`, both ratings NOT NULL. Applied to every per-game CTE in Chapters 2 and 3 so benchmark zones are calibrated against the skill-at-equal-footing baseline. Live UI uses unfiltered games — the gap above the equal-footing baseline is the intended skill signal. See `.planning/notes/benchmark-equal-footing-framing.md`.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (or first ply of each class span in 3.4.1 / 3.4.2). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate scores force conv/recov; NULL → parity).
- **Eval coverage**: 100.00% at first endgame entry (767,395 / 767,398 qualifying games); 100.00% at first middlegame entry (1,299,252 / 1,299,252). NULL-eval is a rounding error.
- **Sparse-cell exclusion**: `(rating_bucket=2400, tc_bucket='classical')` has n=12 completed users, pool-exhausted (0 unattempted / 23 candidates). Kept in 5×4 cell-level tables with `n=12*` footnote; excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes.
- **Verdict thresholds**: Cohen's d < 0.20 collapse / 0.20 – 0.50 review / ≥ 0.50 keep separate
- **Sample floors**: per-subchapter, see individual sections. Cohen's d floor: ≥10 users per marginal level.

## Cell coverage (status='completed' users per cell)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 100 | 100 | 100 | 100 |
| 1200 | 100 | 100 | 100 | 100 |
| 1600 | 100 | 100 | 100 | 100 |
| 2000 | 100 | 100 | 100 | 100 |
| 2400 | 100 | 100 | 100 | 12* |

`*` Sparse cell — pool-exhausted (0 unattempted Lichess 2400-classical candidates after Stage-1 selection at the 2026-03 dump). Excluded from marginals and Cohen's d throughout this report.

## Status breakdown (selected highlights)

- All non-sparse cells: 100 completed + 0 – 28 skipped / failed + ~270 – 400 unattempted (replacements available if needed).
- `(2400, classical)`: 12 completed + 3 failed + 8 skipped + **0 unattempted** — structurally exhausted.
- `(800, classical)`: only cell with materially high `skipped` count (228) — many low-volume classical 800 players fall below the 100-game ingest floor; still hit 100 completed via slot-filling.

---

## 1. Stratified Sample

This chapter is the methodology preamble. The cell coverage table above is the headline. Eval coverage at both MG and EG entries is 100% (no flagging needed). Equal-footing retention is not re-summarized per subchapter; per the 2026-05-03 universal rule it is applied identically everywhere.

---

## 2. Openings

### 2.1 Middlegame-entry eval (centered, symmetric baseline)

**Currently set in code**

| Constant | Live value | File |
|---|---:|---|
| `EVAL_NEUTRAL_MIN_PAWNS` | `−0.30` | `frontend/src/lib/openingStatsZones.ts` |
| `EVAL_NEUTRAL_MAX_PAWNS` | `+0.30` | same |
| `EVAL_BULLET_DOMAIN_PAWNS` | `1.5` | same |
| `EVAL_BASELINE_PAWNS_WHITE` | `+0.25` | `app/services/opening_insights_constants.py` |
| `EVAL_BASELINE_PAWNS_BLACK` | `−0.25` | same (symmetric — verified) |
| `EVAL_CONFIDENCE_MIN_N` | `10` (unified with `OPENING_INSIGHTS_CONFIDENCE_MIN_N`) | same |

#### Symmetric baseline (pass 1 — deduped per physical game, white-POV)

| n_games | baseline_cp_white | median white-POV | SD white-POV |
|---:|---:|---:|---:|
| 1,246,674 | **+25 cp** | +24 cp | 238 cp |

Baseline confirms `+25 cp / −25 cp` symmetric construction matches live constants (`±0.25 pawns`). No update needed.

#### Centered pooled distribution (pass 2 — equal-footing, per-(user, color), sparse cell excluded)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3,496 | +4 cp | 58 cp | −94 cp | **−21 cp** | +7 cp | **+34 cp** | +87 cp |

#### p50 cell grid (centered cp, full 5×4)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −5 (198) | −1 (199) | +12 (196) | −15 (86) |
| 1200 | −10 (200) | +11 (200) | +18 (200) | +22 (145) |
| 1600 | −4 (200) | +8 (200) | +6 (200) | +18 (165) |
| 2000 | +9 (200) | +7 (198) | +9 (196) | +8 (127) |
| 2400 | +6 (200) | −1 (199) | +10 (187) | +3 (4)* |

`*` Sparse cell, n=4 user-color pairs (only 12 completed users overall, most below the ≥20 games-with-eval-at-MG-entry floor).

#### ELO marginal (centered, pooled across TC, sparse excluded)

| ELO | n | mean cp | SD cp | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 679 | −7 | 88 | −150 | −58 | 0 | +50 | +124 |
| 1200 | 745 | +7 | 70 | −104 | −29 | +13 | +49 | +102 |
| 1600 | 765 | +6 | 46 | −69 | −19 | +7 | +35 | +75 |
| 2000 | 721 | +8 | 35 | −50 | −12 | +9 | +29 | +61 |
| 2400 | 586 | +6 | 27 | −36 | −10 | +5 | +21 | +55 |

#### TC marginal (centered, pooled across ELO, sparse excluded)

| TC | n | mean cp | SD cp | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 998 | −5 | 68 | −123 | −32 | +4 | +34 | +86 |
| blitz | 996 | +3 | 47 | −80 | −16 | +4 | +29 | +73 |
| rapid | 979 | +10 | 48 | −63 | −13 | +11 | +35 | +80 |
| classical | 523 | +12 | 72 | −106 | −22 | +12 | +49 | +124 |

#### Collapse verdict

- TC axis: max |d| = **0.25** (bullet vs rapid) → **review**
- ELO axis: max |d| = **0.23** (800 vs 2000) → **review**

#### Recommendations

- **Baseline constant**: pass-1 produced **+25 cp** (white). Live `EVAL_BASELINE_PAWNS_WHITE = +0.25` matches; no change.
- **Neutral-zone bounds** (pooled centered `[p25, p75] = [−21 cp, +34 cp]`): symmetric `max(|p25|, |p75|) ≈ 35 cp ≈ 0.35 pawns`. Live `EVAL_NEUTRAL_MIN/MAX_PAWNS = ±0.30` is within rounding of the IQR-derived value. **Action: keep at ±0.30** (matches established editorial preference for round bounds when `|measured − constant| < 5 cp` holds).
- **Domain bounds** (pooled centered `[p05, p95] = [−94, +87]`): symmetric `max ≈ 95 cp ≈ 0.95 pawns`. Live `EVAL_BULLET_DOMAIN_PAWNS = 1.5` is well wider than the pooled p95 but explicitly sized to cover the 800-cohort tail (p05 = −150 cp). **Action: keep**.
- **Color symmetry**: `EVAL_BASELINE_PAWNS_BLACK = −0.25 = −EVAL_BASELINE_PAWNS_WHITE`. Symmetric — no violation.
- **Mate-row footnote**: pass-1 deduped rows applied `eval_mate IS NULL` filter; mate-row prevalence at MG entry is a rounding error (mate scores at move ~10–20 are exceedingly rare on Lichess analyzed games).

---

## 3. Endgames

### 3.1 Endgame Overall Performance

#### 3.1.1 Non-Endgame Score (per-user)

**Currently set in code (shared with Openings score bullet)**

| Constant | Live value | File |
|---|---:|---|
| `SCORE_BULLET_CENTER` | `0.5` | `frontend/src/lib/scoreBulletConfig.ts` |
| `SCORE_BULLET_NEUTRAL_MIN/MAX` | `−0.05 / +0.05` (→ `[0.45, 0.55]`) | same |
| `SCORE_BULLET_DOMAIN` | `0.25` (half-width, axis `[0.25, 0.75]`) | same |

#### Pooled distribution (sparse cell excluded)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,632 | 52.4% | 8.5% | 38.9% | **46.8%** | 52.1% | **57.4%** | 67.3% |

#### p50 cell grid (`p50 (n_users)`)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 50.4% (97) | 50.0% (97) | 51.4% (94) | 55.1% (24) |
| 1200 | 51.6% (97) | 51.5% (99) | 51.6% (98) | 55.4% (51) |
| 1600 | 50.9% (97) | 50.5% (99) | 51.1% (100) | 54.4% (66) |
| 2000 | 52.3% (100) | 52.9% (98) | 53.5% (95) | 56.0% (49) |
| 2400 | 51.0% (98) | 55.6% (96) | 56.0% (77) | 53.0% (1)* |

`*` Sparse cell, n=1 user.

#### ELO marginal (pooled across TC, sparse excluded)

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 312 | 50.5% | 7.1% | 38.0% | 46.3% | 50.6% | 55.0% | 62.0% |
| 1200 | 345 | 52.2% | 8.1% | 39.2% | 46.9% | 51.7% | 56.7% | 66.0% |
| 1600 | 362 | 51.6% | 8.9% | 38.6% | 45.5% | 51.3% | 56.5% | 67.3% |
| 2000 | 342 | 53.4% | 8.5% | 40.4% | 47.6% | 53.3% | 58.3% | 68.0% |
| 2400 | 271 | 54.6% | 9.5% | 38.5% | 48.5% | 54.7% | 60.3% | 70.8% |

#### TC marginal (pooled across ELO, sparse excluded)

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 489 | 51.2% | 8.1% | 37.1% | 46.5% | 51.3% | 55.6% | 64.0% |
| blitz | 489 | 52.0% | 7.8% | 39.2% | 46.5% | 51.9% | 56.9% | 65.4% |
| rapid | 464 | 52.7% | 8.4% | 39.9% | 47.2% | 52.7% | 57.8% | 67.1% |
| classical | 190 | 55.7% | 10.6% | 38.8% | 48.9% | 54.9% | 62.9% | 72.4% |

#### Collapse verdict

- TC axis: max |d| = **0.50** (bullet vs classical) → **keep separate**
- ELO axis: max |d| = **0.49** (800 vs 2400) → **review**

#### Recommendations

- **Cohort neutral band**: pooled `[p25, p75] = [46.8%, 57.4%]` widens the live `[45%, 55%]` band by ~2.4pp on the upper side. The pooled mean is **52.4%** (vs the 50% null) — non-EG games are systematically easier than EG-reaching ones (sampling selection: short decisive games end before reaching `phase=2`).
- **Routing**: `SCORE_BULLET_*` is shared with the Openings score bullet. The widened upper bound and pronounced TC stratification (classical median ~55%) argue for a **dedicated non-EG zones module** mirroring `endgameEntryEvalZones.ts` rather than retuning the shared constant.
- **Collapse verdict says "keep separate" on TC, "review" on ELO** — if a per-non-EG module is introduced, default to a single global band first (the 800–2400 ELO sweep is only 4pp wide), then revisit per-TC if classical drift is UX-meaningful.

---

#### 3.1.2 Endgame-entry eval (pawns)

**Currently set in code**

| Constant | Live value | File |
|---|---:|---|
| `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS` | `−0.75` | `frontend/src/lib/endgameEntryEvalZones.ts` |
| `ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS` | `+0.75` | same |
| `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | `2.25` | same |
| `ENDGAME_ENTRY_EVAL_CENTER` | `0` (uncentered tile) | same |
| `ZONE_REGISTRY["entry_eval_pawns"]` | `(−0.75, +0.75)` | `app/services/endgame_zones.py` |

#### Symmetric baseline (pass 1, deduped, white-POV)

| n_games | baseline_cp_white | median | SD |
|---:|---:|---:|---:|
| 801,065 | **+10 cp** | 0 cp | 443 cp |

EG entry baseline is much smaller than MG entry (+25 cp): once games reach a 6-ply endgame, the position is materially closer to balanced. (Median exactly 0 reflects the same.)

#### Pooled distribution (pass 2, equal-footing, sparse excluded)

| variant | n | mean cp | SD cp | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| uncentered | 3,304 | +9 | 117 | −186 | **−56** | +10 | **+75** | +199 |
| centered (−10 cp) | 3,304 | +9 | 117 | −183 | −54 | +11 | +75 | +197 |

#### p50 cell grid (uncentered user-POV cp, 5×4)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −25 (193) | −10 (190) | −25 (186) | −63 (36) |
| 1200 | −21 (200) | +8 (197) | +16 (195) | +6 (104) |
| 1600 | −10 (196) | +24 (200) | +11 (200) | +12 (141) |
| 2000 | +6 (200) | +27 (198) | +28 (193) | +21 (108) |
| 2400 | +15 (198) | +10 (194) | +24 (175) | +203 (2)* |

`*` Sparse cell, n=2 user-color pairs.

#### ELO marginal (uncentered, sparse excluded)

| ELO | n | mean cp | SD cp | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 605 | −5 | 170 | −278 | −129 | −21 | +92 | +262 |
| 1200 | 696 | +11 | 132 | −214 | −80 | +1 | +86 | +222 |
| 1600 | 737 | +25 | 100 | −147 | −51 | +14 | +77 | +182 |
| 2000 | 699 | +30 | 84 | −109 | −36 | +22 | +72 | +161 |
| 2400 | 567 | +31 | 67 | −78 | −25 | +17 | +64 | +134 |

#### TC marginal (uncentered, sparse excluded)

| TC | n | mean cp | SD cp | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 987 | +4 | 138 | −238 | −84 | −3 | +78 | +213 |
| blitz | 979 | +24 | 100 | −141 | −43 | +11 | +70 | +177 |
| rapid | 949 | +31 | 104 | −156 | −41 | +18 | +81 | +205 |
| classical | 389 | +15 | 125 | −201 | −61 | +14 | +71 | +208 |

#### Collapse verdict (on centered)

- TC axis: max |d| = **0.22** (bullet vs rapid) → **review**
- ELO axis: max |d| = **0.28** (800 vs 2400) → **review**

#### Recommendations

- **Neutral-zone bounds (uncentered)**: pooled `[p25, p75] = [−56 cp, +75 cp]` ≈ `[−0.56, +0.75] pawns`. Symmetric `max ≈ 0.75 pawns`. Live `±0.75 pawns` is exactly the IQR-derived bound. **Action: keep at ±0.75**. Memory `feedback_zone_band_judgement.md` previously argued for editorial tightening to ±0.50; the comment in the live file notes that was reverted back to the benchmark-recommended ±0.75. Confirmed.
- **Domain bounds**: pooled `[p05, p95] = [−186, +199] cp ≈ ±2.0 pawns`. Live `±2.25 pawns` is slightly wider, deliberately sized so the neutral band fills ~1/3 of the axis. **Action: keep**.
- **Center**: 0 (by construction, EG-entry tile is 0-centered). No change.

---

#### 3.1.3 Achievable Score

**Currently set in code**

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["entry_expected_score"]` | `(0.45, 0.55)` | `app/services/endgame_zones.py` |

#### Pooled distribution (sparse excluded)

| n | mean | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1,751 | 50.9% | 38.2% | **46.3%** | 51.0% | **55.4%** | 64.1% |

#### p50 cell grid (`p50 (n_users)`)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 49.5% (99) | 49.4% (100) | 49.8% (96) | 47.7% (41) |
| 1200 | 48.6% (100) | 51.3% (99) | 50.6% (100) | 51.9% (72) |
| 1600 | 49.2% (100) | 52.1% (100) | 51.7% (100) | 50.8% (85) |
| 2000 | 50.3% (100) | 51.7% (100) | 52.4% (98) | 51.8% (66) |
| 2400 | 50.5% (100) | 51.1% (100) | 51.7% (95) | 65.3% (2)* |

#### ELO marginal (sparse excluded)

| ELO | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 336 | 49.6% | 10.8% | 42.0% | 49.3% | 56.0% |
| 1200 | 371 | 50.8% | 9.2% | 45.1% | 50.4% | 56.2% |
| 1600 | 385 | 51.3% | 6.8% | 46.9% | 51.2% | 56.1% |
| 2000 | 364 | 51.5% | 5.8% | 47.9% | 51.6% | 55.5% |
| 2400 | 295 | 51.4% | 4.6% | 48.5% | 51.2% | 54.1% |

#### TC marginal (sparse excluded)

| TC | n | mean | SD | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|---:|
| bullet | 499 | 50.0% | 8.8% | 44.8% | 50.1% | 55.3% |
| blitz | 499 | 51.1% | 6.7% | 47.1% | 51.2% | 54.8% |
| rapid | 489 | 51.7% | 7.0% | 47.3% | 51.5% | 56.1% |
| classical | 264 | 51.0% | 9.0% | 45.6% | 50.9% | 56.3% |

#### Collapse verdict

- TC axis: max |d| = **0.22** (bullet vs rapid) → **review**
- ELO axis: max |d| = **0.23** (800 vs 2000) → **review**

#### Recommendations

- **Sanity check**: pooled mean = **50.9%**, within +1pp of the 50% chess-fairness null. Equal-footing filter doing its job.
- **Cohort neutral band**: pooled `[p25, p75] = [46.3%, 55.4%]` → round to `[0.46, 0.55]`. Live `ZoneSpec(0.45, 0.55)` is within rounding (lower bound 1pp wider). **Action: keep**. Editorial alignment with `endgame_score` band is intentional (per the registry comment) for visual parity.
- **Routing**: dedicated `entry_expected_score` registry entry already in place. No changes needed.

---

#### 3.1.4 Endgame Score (per-user, EG-only)

**Currently set in code**

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["endgame_score"]` | `(0.45, 0.55)` | `app/services/endgame_zones.py` |
| `SCORE_BULLET_*` (shared) | as in 3.1.1 | `frontend/src/lib/scoreBulletConfig.ts` |

#### Pooled distribution (sparse excluded)

| n | mean | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1,751 | 51.2% | 39.3% | **46.3%** | 50.9% | **55.8%** | 64.4% |

#### p50 cell grid

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 47.3% (99) | 47.8% (100) | 49.0% (96) | 43.9% (41) |
| 1200 | 49.2% (100) | 48.1% (99) | 51.3% (100) | 51.2% (72) |
| 1600 | 49.9% (100) | 50.4% (100) | 51.7% (100) | 50.0% (85) |
| 2000 | 50.6% (100) | 52.8% (100) | 52.2% (98) | 53.6% (66) |
| 2400 | 52.4% (100) | 54.1% (100) | 54.8% (95) | 77.4% (2)* |

#### ELO marginal (sparse excluded)

| ELO | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 336 | 47.9% | 9.0% | 42.3% | 47.4% | 52.3% |
| 1200 | 371 | 50.5% | 8.7% | 44.9% | 49.3% | 55.0% |
| 1600 | 385 | 51.1% | 7.2% | 46.2% | 50.4% | 55.4% |
| 2000 | 364 | 52.5% | 6.3% | 48.9% | 52.1% | 56.0% |
| 2400 | 295 | 54.6% | 6.4% | 50.4% | 53.9% | 58.1% |

#### TC marginal (sparse excluded)

| TC | n | mean | SD | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|---:|
| bullet | 499 | 50.3% | 6.4% | 46.1% | 50.0% | 53.9% |
| blitz | 499 | 51.3% | 6.9% | 46.8% | 51.1% | 55.8% |
| rapid | 489 | 52.3% | 8.5% | 47.1% | 52.2% | 56.9% |
| classical | 264 | 50.7% | 10.5% | 43.9% | 50.4% | 57.5% |

#### Collapse verdict

- TC axis: max |d| = **0.27** (bullet vs rapid) → **review**
- ELO axis: max |d| = **0.84** (800 vs 2400) → **keep separate**

#### Recommendations

- **Cohort neutral band**: pooled `[p25, p75] = [46.3%, 55.8%]`. Live `endgame_score: (0.45, 0.55)` is within rounding. **Action: keep** the global band.
- **ELO `keep separate` (d=0.84)**: per-ELO p50 spread from 47.4% (800) to 53.9% (2400) is **6.5pp** — wider than the pooled IQR width (9.5pp half-width 4.75pp). A per-ELO `ENDGAME_SCORE_ZONES` registry (mirroring how Conversion ELO worked pre-87.4) is the principled fix. **Action: defer stratification** until 2400/800 tile staleness becomes UX-visible.

---

#### 3.1.5 Achievable Score Gap

**Currently set in code**

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["achievable_score_gap"]` | `(−0.05, +0.05)` | `app/services/endgame_zones.py` |
| `ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN/MAX` | `−0.05 / +0.05` (generated) | `frontend/src/generated/endgameZones.ts` |

#### Pooled distribution (sparse excluded)

| n | mean | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1,751 | +0.3pp | −12.4pp | **−3.9pp** | +0.7pp | **+4.6pp** | +11.6pp |

#### p50 cell grid (per-user `actual − expected` in pp)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −0.3pp (99) | −1.1pp (100) | −1.2pp (96) | −4.1pp (41) |
| 1200 | +0.3pp (100) | −0.3pp (99) | −0.7pp (100) | −1.1pp (72) |
| 1600 | +0.7pp (100) | +0.0pp (100) | +0.8pp (100) | +0.5pp (85) |
| 2000 | +0.4pp (100) | +1.0pp (100) | +0.8pp (98) | +2.0pp (66) |
| 2400 | +3.4pp (100) | +4.3pp (100) | +3.5pp (95) | +12.1pp (2)* |

#### ELO marginal (sparse excluded)

| ELO | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 336 | −1.7pp | 9.0pp | −7.0pp | −1.3pp | +4.0pp |
| 1200 | 371 | −0.3pp | 7.3pp | −4.7pp | −0.6pp | +3.5pp |
| 1600 | 385 | −0.2pp | 6.9pp | −3.8pp | +0.5pp | +3.8pp |
| 2000 | 364 | +1.0pp | 7.0pp | −2.7pp | +1.2pp | +4.8pp |
| 2400 | 295 | +3.2pp | 6.3pp | −0.5pp | +3.5pp | +7.3pp |

#### TC marginal (sparse excluded)

| TC | n | mean | SD | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|---:|
| bullet | 499 | +0.4pp | 9.9pp | −5.5pp | +1.3pp | +6.7pp |
| blitz | 499 | +0.2pp | 6.4pp | −3.8pp | +0.7pp | +4.4pp |
| rapid | 489 | +0.6pp | 6.1pp | −2.6pp | +0.7pp | +4.1pp |
| classical | 264 | −0.3pp | 6.6pp | −4.7pp | −0.1pp | +3.9pp |

#### Collapse verdict

- TC axis: max |d| = **0.15** (classical vs rapid) → **collapse**
- ELO axis: max |d| = **0.62** (800 vs 2400) → **keep separate**

#### Recommendations

- **Sanity check on engine alignment**: pooled mean = **+0.3pp**, within the ±1pp engine-alignment null.
- **Cohort neutral band**: pooled `[p25, p75] = [−3.9pp, +4.6pp]` rounds to symmetric `±0.05`. Live `(−0.05, +0.05)` matches. **Action: keep** (already calibrated 260514-kei per the registry comment).
- **Domain bounds**: pooled `[p05, p95] = [−12.4pp, +11.6pp]` → asymmetric ~±12pp. Not currently surfaced; current `SCORE_GAP_DOMAIN = 0.20` for visual parity with 3.1.6 fits.
- **ELO `keep separate` (d=0.62)**: per-ELO p50 spread is **−1.3pp (800) → +3.5pp (2400) = 4.8pp**, exceeding the pooled IQR half-width (4.25pp). The 2400-cohort median sits inside the upper band; per-ELO stratification deferred per existing registry comment.
- **TC collapse confirmed** — single global band justified across TC.

---

#### 3.1.6 Endgame Score Gap and Timeline

**Currently set in code**

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["score_gap"]` | `(−0.10, +0.10)` | `app/services/endgame_zones.py` |
| `SCORE_GAP_NEUTRAL_MIN/MAX` | `−0.10 / +0.10` (generated) | `frontend/src/generated/endgameZones.ts` |
| `SCORE_GAP_DOMAIN` | `0.20` (half-width) | `frontend/src/components/charts/EndgameOverallShared.ts` |

#### Pooled distribution (eg − non_eg, sparse excluded)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,632 | −1.3pp | 12.9pp | −22.7pp | **−10.4pp** | −1.4pp | **+7.3pp** | +20.2pp |

eg_mean (pooled) = **51.1%**; non_eg_mean = **52.4%** → systematic ~1.3pp drop in EG.

#### p50 cell grid (`diff_p50 (n_users)`, in pp)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −3.6pp (97) | −2.4pp (97) | −2.3pp (94) | −13.4pp (24) |
| 1200 | −4.0pp (97) | −3.2pp (99) | +0.8pp (98) | −5.5pp (51) |
| 1600 | −1.7pp (97) | −0.1pp (99) | +0.7pp (100) | −4.8pp (66) |
| 2000 | −1.4pp (100) | +0.5pp (98) | +0.8pp (95) | −1.9pp (49) |
| 2400 | +2.3pp (98) | −0.2pp (96) | −0.9pp (77) | +6.4pp (1)* |

#### ELO marginal (sparse excluded)

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 312 | −2.5pp | 13.5pp | −24.2pp | −11.6pp | −3.6pp | +5.3pp | +21.9pp |
| 1200 | 345 | −2.1pp | 13.7pp | −23.7pp | −11.2pp | −3.1pp | +7.2pp | +21.2pp |
| 1600 | 362 | −0.7pp | 13.6pp | −23.1pp | −10.3pp | −0.9pp | +9.4pp | +21.0pp |
| 2000 | 342 | −1.0pp | 11.5pp | −20.6pp | −8.8pp | −0.4pp | +6.8pp | +16.4pp |
| 2400 | 271 | −0.4pp | 11.5pp | −19.7pp | −8.2pp | +0.1pp | +7.4pp | +16.7pp |

#### TC marginal (sparse excluded)

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 489 | −1.0pp | 11.8pp | −18.2pp | −9.5pp | −1.8pp | +6.4pp | +19.8pp |
| blitz | 489 | −0.7pp | 11.9pp | −19.1pp | −9.3pp | −0.9pp | +6.9pp | +19.5pp |
| rapid | 464 | −0.7pp | 13.2pp | −23.2pp | −9.5pp | −0.6pp | +8.2pp | +20.3pp |
| classical | 190 | −5.3pp | 16.2pp | −33.7pp | −15.1pp | −4.6pp | +6.5pp | +19.9pp |

#### Collapse verdict

- TC axis: max |d| = **0.34** (blitz vs classical) → **review**
- ELO axis: max |d| = **0.17** (800 vs 2400) → **collapse**

#### Recommendations

- **Score-gap neutral zone**: pooled `[p25, p75] = [−10.4pp, +7.3pp]` is asymmetric (median −1.4pp). Per memory `feedback_zone_band_judgement.md` keep symmetric `±10pp` unless `|median| ≥ 5pp` — here |median| = 1.4pp. **Action: keep ±0.10 / ±10pp**.
- **Score-gap domain half-width**: pooled `max(|p05|, |p95|) = 22.7pp`. Live `SCORE_GAP_DOMAIN = 0.20` (20pp) is slightly tighter; whiskers past ±20pp render open-ended. **Action: keep**.
- **Timeline Y-axis**: pooled `eg [46.3%, 55.8%]` ∩ `non_eg [46.8%, 57.4%]` → unified `[47.2%, 55.8%]`. Live `endgame_score_timeline` ZoneSpec is `(0.0, 1.0)` (no calibrated zone) per the registry comment. No change.
- **TC `review` (d=0.34, driven by classical at −5.3pp)**: classical-cohort median is −4.6pp, just below the |median| ≥ 5pp re-centering trigger. Holding symmetric ±10pp consistent with prior 2026-04-30 design decision.

---

### 3.2 Endgame Metrics and ELO

#### 3.2.1 Conversion / Parity / Recovery + Endgame Skill

**Currently set in code**

| Metric | Live band | File |
|---|---:|---|
| `BUCKETED_ZONE_REGISTRY["conversion_win_pct"]` | `(0.65, 0.77)` all buckets | `app/services/endgame_zones.py` |
| `BUCKETED_ZONE_REGISTRY["parity_score_pct"]` | `(0.45, 0.55)` all buckets | same |
| `BUCKETED_ZONE_REGISTRY["recovery_save_pct"]` | `(0.24, 0.36)` all buckets | same |
| `endgame_skill` ZoneSpec | **deleted in Phase 87.4** (composite retracted) | — |

#### Pooled distributions (sparse excluded)

| Metric | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| Conversion | 1,751 | 71.1% | 65.6% | 71.9% | 76.9% |
| Parity | 1,751 | 50.2% | 44.3% | 50.0% | 56.3% |
| Recovery | 1,751 | 30.5% | 24.3% | 30.1% | 36.4% |
| Endgame Skill | 1,751 | 50.6% | 46.6% | 50.8% | 54.8% |

#### Conversion — p50 cell grid

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 59.7% (99) | 70.1% (100) | 71.4% (96) | 71.4% (41) |
| 1200 | 62.5% (100) | 70.9% (99) | 73.4% (100) | 75.0% (72) |
| 1600 | 65.9% (100) | 71.2% (100) | 74.7% (100) | 77.5% (85) |
| 2000 | 67.2% (100) | 72.6% (100) | 74.9% (98) | 77.4% (66) |
| 2400 | 71.3% (100) | 74.4% (100) | 77.8% (95) | 79.4% (2)* |

#### Conversion — ELO marginal

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 336 | 66.8% | 59.9% | 68.4% | 73.9% |
| 1200 | 371 | 70.3% | 64.7% | 70.9% | 76.0% |
| 1600 | 385 | 71.7% | 66.7% | 72.1% | 77.6% |
| 2000 | 364 | 72.1% | 66.9% | 72.5% | 77.5% |
| 2400 | 295 | 74.9% | 69.8% | 74.3% | 79.9% |

#### Conversion — TC marginal

| TC | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| bullet | 499 | 65.1% | 58.3% | 65.8% | 72.0% |
| blitz | 499 | 71.6% | 67.4% | 71.8% | 76.1% |
| rapid | 489 | 74.3% | 69.7% | 74.5% | 78.7% |
| classical | 264 | 75.6% | 69.8% | 76.1% | 83.0% |

Verdict — TC d_max = **1.02** (bullet vs classical) → **keep separate**; ELO d_max = **0.82** (800 vs 2400) → **keep separate**.

#### Parity — p50 cell grid

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 50.0% (99) | 47.9% (100) | 50.0% (96) | 38.5% (41) |
| 1200 | 49.0% (100) | 48.9% (99) | 48.7% (100) | 50.0% (72) |
| 1600 | 51.5% (100) | 50.0% (100) | 50.0% (100) | 50.0% (85) |
| 2000 | 49.9% (100) | 51.3% (100) | 51.9% (98) | 52.1% (66) |
| 2400 | 52.2% (100) | 55.2% (100) | 54.0% (95) | 71.2% (2)* |

#### Parity — ELO marginal

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 336 | 47.0% | 38.3% | 50.0% | 55.3% |
| 1200 | 371 | 49.9% | 43.3% | 48.9% | 55.0% |
| 1600 | 385 | 49.7% | 44.1% | 50.0% | 55.4% |
| 2000 | 364 | 51.4% | 46.1% | 51.2% | 56.3% |
| 2400 | 295 | 53.7% | 48.6% | 53.9% | 58.1% |

#### Parity — TC marginal

| TC | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| bullet | 499 | 50.4% | 44.4% | 50.0% | 56.4% |
| blitz | 499 | 50.2% | 44.7% | 50.7% | 56.0% |
| rapid | 489 | 50.8% | 45.6% | 50.6% | 55.8% |
| classical | 264 | 49.1% | 39.5% | 50.0% | 58.3% |

Verdict — TC d_max = **0.12** → **collapse**; ELO d_max = **0.48** (800 vs 2400) → **review**.

#### Recovery — p50 cell grid

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 35.4% (99) | 29.0% (100) | 25.8% (96) | 20.3% (41) |
| 1200 | 36.5% (100) | 29.0% (99) | 28.6% (100) | 22.6% (72) |
| 1600 | 34.0% (100) | 28.7% (100) | 26.9% (100) | 22.2% (85) |
| 2000 | 34.4% (100) | 33.0% (100) | 26.4% (98) | 27.2% (66) |
| 2400 | 34.6% (100) | 31.7% (100) | 30.0% (95) | 25.0% (2)* |

#### Recovery — ELO marginal

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 336 | 29.7% | 23.4% | 29.7% | 35.7% |
| 1200 | 371 | 30.0% | 23.8% | 29.6% | 35.8% |
| 1600 | 385 | 29.3% | 23.1% | 28.7% | 35.3% |
| 2000 | 364 | 31.1% | 25.0% | 30.5% | 37.3% |
| 2400 | 295 | 33.0% | 27.5% | 32.3% | 38.0% |

#### Recovery — TC marginal

| TC | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| bullet | 499 | 35.6% | 30.2% | 35.3% | 40.5% |
| blitz | 499 | 30.3% | 25.1% | 30.4% | 35.5% |
| rapid | 489 | 28.6% | 23.3% | 27.7% | 32.8% |
| classical | 264 | 25.0% | 18.2% | 23.3% | 31.6% |

Verdict — TC d_max = **1.10** (bullet vs classical) → **keep separate**; ELO d_max = **0.40** (1600 vs 2400) → **review**.

#### Endgame Skill (per-user mean of conv/par/recov bucket rates)

#### Skill — p50 cell grid

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 48.1% (99) | 49.7% (100) | 49.3% (96) | 43.8% (41) |
| 1200 | 49.2% (100) | 49.6% (99) | 50.8% (100) | 49.6% (72) |
| 1600 | 50.9% (100) | 50.1% (100) | 50.7% (100) | 51.6% (85) |
| 2000 | 50.6% (100) | 52.1% (100) | 51.2% (98) | 52.3% (66) |
| 2400 | 52.8% (100) | 54.3% (100) | 54.4% (95) | 58.5% (2)* |

#### Skill — ELO marginal & TC marginal

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 336 | 47.8% | 42.8% | 48.9% | 52.8% |
| 1200 | 371 | 50.1% | 45.8% | 49.7% | 53.7% |
| 1600 | 385 | 50.2% | 46.6% | 50.7% | 54.4% |
| 2000 | 364 | 51.5% | 48.0% | 51.4% | 55.1% |
| 2400 | 295 | 53.9% | 49.9% | 53.9% | 57.5% |

| TC | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| bullet | 499 | 50.4% | 45.9% | 50.6% | 55.3% |
| blitz | 499 | 50.7% | 47.0% | 50.9% | 54.8% |
| rapid | 489 | 51.3% | 47.9% | 51.2% | 54.6% |
| classical | 264 | 49.9% | 44.5% | 49.9% | 54.9% |

Verdict — TC d_max = **0.18** → **collapse**; ELO d_max = **0.78** (800 vs 2400) → **keep separate**.

#### Recommendations (§3.2.1)

- **Conversion**: pooled `[p25, p75] = [65.6%, 76.9%]`. Live `[0.65, 0.77]` is within rounding. **Action: keep**. TC + ELO both `keep separate` — but the live band is shared across material buckets and the cell-spread inside the band is already covered by the same span. If a stratified gauge ships, base it on TC (max d=1.02) before ELO.
- **Parity**: pooled `[p25, p75] = [44.3%, 56.3%]`. Live `[0.45, 0.55]` is within 1.3pp on each side; **keep**. ELO `review` does not justify stratification.
- **Recovery**: pooled `[p25, p75] = [24.3%, 36.4%]`. Live `[0.24, 0.36]` matches exactly. **Action: keep**. TC `keep separate` (d=1.10) confirms recovery is the most TC-sensitive of the three.
- **Endgame Skill**: no live registry entry (Phase 87.4 dropped). Pooled `[p25, p75] = [46.6%, 54.8%]` for reference; ELO `keep separate` (d=0.78) — the original cohort-confounded argument is confirmed.

---

#### 3.2.2 Per-bucket ΔES Score Gap (Section 2)

**Currently set in code**

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["section2_score_gap_conv"]` | `(−0.11, 0.00)` | `app/services/endgame_zones.py` |
| `ZONE_REGISTRY["section2_score_gap_parity"]` | `(−0.04, +0.04)` | same |
| `ZONE_REGISTRY["section2_score_gap_recov"]` | `(+0.01, +0.11)` | same |
| `section2_score_gap_skill` ZoneSpec | **deleted in Phase 87.4** | — |

#### Pooled-by-bucket summary (sparse cell excluded)

| Bucket | n_users | pooled_mean | pooled_sd | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|---:|
| conversion | 1,657 | **−6.2pp** | 9.4pp | −10.8pp | −4.7pp | +0.2pp |
| parity | 1,508 | +0.1pp | 6.1pp | −3.5pp | +0.4pp | +3.7pp |
| recovery | 1,609 | **+6.4pp** | 7.6pp | +1.0pp | +5.6pp | +10.7pp |
| skill (equal-weighted) | 1,731 | +0.0pp | 4.9pp | −2.7pp | +0.3pp | +3.0pp |

**Sigmoid-bias check confirmed**: conversion skews −6pp (ceiling near 1.0), recovery skews +6pp (floor near 0.0), parity symmetric. Divergent per-bucket bands are correct.

#### Conversion bucket — p50 cell grid (in pp)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −21.8pp (96) | −9.9pp (96) | −8.2pp (92) | −10.8pp (21) |
| 1200 | −17.2pp (99) | −6.7pp (99) | −5.2pp (98) | −4.8pp (61) |
| 1600 | −11.7pp (97) | −4.1pp (100) | −1.3pp (100) | +0.4pp (72) |
| 2000 | −9.0pp (100) | −1.3pp (100) | +1.0pp (96) | +4.1pp (51) |
| 2400 | −4.7pp (100) | +1.9pp (97) | +3.4pp (82) | +12.1pp (1)* |

#### Conversion — ELO marginal

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 305 | −14.0pp | −19.2pp | −12.0pp | −7.1pp |
| 1200 | 357 | −8.8pp | −12.6pp | −7.2pp | −3.3pp |
| 1600 | 369 | −5.3pp | −9.2pp | −3.7pp | +0.3pp |
| 2000 | 347 | −2.6pp | −6.5pp | −1.5pp | +3.0pp |
| 2400 | 279 | −0.3pp | −4.4pp | +0.0pp | +4.3pp |

#### Conversion — TC marginal

| TC | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| bullet | 492 | −13.1pp | −19.7pp | −11.6pp | −5.2pp |
| blitz | 492 | −4.6pp | −8.8pp | −4.0pp | −0.0pp |
| rapid | 468 | −2.6pp | −6.6pp | −2.2pp | +2.2pp |
| classical | 205 | −2.0pp | −6.9pp | −0.8pp | +3.8pp |

Verdict — TC d_max = **1.20** (bullet vs rapid) → **keep separate**; ELO d_max = **1.62** (800 vs 2400) → **keep separate**.

#### Parity bucket — p50 cell grid (in pp)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −0.1pp (69) | −1.7pp (75) | +0.4pp (64) | −4.4pp (4) |
| 1200 | −1.2pp (93) | −1.1pp (98) | −0.6pp (90) | −0.9pp (31) |
| 1600 | +0.7pp (97) | −1.1pp (99) | +0.3pp (95) | −1.3pp (61) |
| 2000 | −0.6pp (99) | +1.6pp (99) | +1.0pp (94) | +1.0pp (54) |
| 2400 | +1.8pp (99) | +3.1pp (97) | +1.9pp (90) | −4.2pp (1)* |

#### Parity — ELO marginal

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 212 | −1.3pp | −5.0pp | −0.2pp | +3.3pp |
| 1200 | 312 | −0.8pp | −5.0pp | −1.1pp | +3.1pp |
| 1600 | 352 | −0.7pp | −4.0pp | −0.2pp | +2.7pp |
| 2000 | 346 | +0.8pp | −2.2pp | +0.8pp | +3.7pp |
| 2400 | 286 | +2.3pp | −0.8pp | +2.5pp | +5.2pp |

#### Parity — TC marginal

| TC | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| bullet | 457 | −0.2pp | −3.6pp | +0.1pp | +3.9pp |
| blitz | 468 | +0.0pp | −3.4pp | +0.4pp | +3.6pp |
| rapid | 433 | +0.6pp | −2.7pp | +0.7pp | +3.9pp |
| classical | 150 | −0.5pp | −4.6pp | −0.2pp | +3.4pp |

Verdict — TC d_max = **0.18** → **collapse**; ELO d_max = **0.57** (800 vs 2400) → **keep separate**.

#### Recovery bucket — p50 cell grid (in pp)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | +17.1pp (96) | +8.1pp (96) | +6.6pp (91) | +5.9pp (23) |
| 1200 | +14.6pp (100) | +5.8pp (97) | +4.6pp (94) | +2.1pp (52) |
| 1600 | +12.2pp (98) | +4.3pp (99) | +1.9pp (97) | −0.3pp (67) |
| 2000 | +11.2pp (100) | +4.7pp (96) | −0.1pp (93) | −2.2pp (42) |
| 2400 | +8.5pp (98) | +3.1pp (96) | −0.2pp (74) | (no users)* |

#### Recovery — ELO marginal

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 306 | +10.7pp | +5.3pp | +9.3pp | +15.0pp |
| 1200 | 343 | +7.8pp | +2.8pp | +6.7pp | +11.7pp |
| 1600 | 361 | +5.1pp | +0.2pp | +3.8pp | +9.3pp |
| 2000 | 331 | +4.1pp | −1.1pp | +3.7pp | +8.9pp |
| 2400 | 268 | +4.3pp | −0.2pp | +3.8pp | +8.1pp |

#### Recovery — TC marginal

| TC | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| bullet | 492 | +12.8pp | +7.7pp | +12.3pp | +17.6pp |
| blitz | 484 | +5.1pp | +1.2pp | +5.1pp | +8.3pp |
| rapid | 449 | +3.0pp | −0.4pp | +2.8pp | +6.3pp |
| classical | 184 | +1.0pp | −2.7pp | +0.3pp | +4.6pp |

Verdict — TC d_max = **1.63** (bullet vs classical) → **keep separate**; ELO d_max = **0.88** (800 vs 2400) → **keep separate**.

#### Skill aggregate (equal-weighted ΔES) — p50 cell grid (in pp)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −1.8pp (98) | −0.6pp (98) | −0.6pp (94) | −5.9pp (34) |
| 1200 | −0.7pp (99) | −0.5pp (99) | −0.2pp (99) | −1.5pp (63) |
| 1600 | +0.3pp (100) | +0.1pp (100) | +0.3pp (100) | +0.0pp (87) |
| 2000 | +0.2pp (100) | +1.1pp (100) | +0.5pp (98) | +1.3pp (67) |
| 2400 | +2.3pp (100) | +2.6pp (100) | +2.3pp (95) | +10.3pp (2)* |

#### Skill ΔES — ELO marginal & TC marginal

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 324 | −1.9pp | −5.7pp | −0.9pp | +1.8pp |
| 1200 | 360 | −0.6pp | −3.4pp | −0.8pp | +1.9pp |
| 1600 | 387 | −0.2pp | −2.6pp | +0.2pp | +2.6pp |
| 2000 | 365 | +0.8pp | −1.5pp | +0.7pp | +3.3pp |
| 2400 | 295 | +2.3pp | −0.2pp | +2.4pp | +4.8pp |

| TC | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| bullet | 497 | −0.1pp | −3.5pp | +0.3pp | +3.6pp |
| blitz | 497 | +0.1pp | −2.4pp | +0.5pp | +2.9pp |
| rapid | 486 | +0.3pp | −1.7pp | +0.5pp | +2.7pp |
| classical | 251 | −0.5pp | −3.6pp | −0.4pp | +2.8pp |

Verdict — TC d_max = **0.17** → **collapse**; ELO d_max = **0.81** (800 vs 2400) → **keep separate**.

#### Recommendations (§3.2.2)

- **Conversion ΔES**: pooled `[p25, p75] = [−10.8pp, +0.2pp]` rounds to **`(−0.11, 0.00)`**. Live `(−0.11, 0.00)` matches exactly. **Action: keep**. ELO d=1.62 confirms the stratification deferral noted in CONTEXT (scalar registry remains).
- **Parity ΔES**: pooled `[p25, p75] = [−3.5pp, +3.7pp]` rounds to **`(−0.04, +0.04)`**. Live `(−0.04, +0.04)` matches exactly. **Action: keep**.
- **Recovery ΔES**: pooled `[p25, p75] = [+1.0pp, +10.7pp]` rounds to **`(+0.01, +0.11)`**. Live `(+0.01, +0.11)` matches exactly. **Action: keep**. TC d=1.63 + ELO d=0.88 both `keep separate` — recovery ΔES is the strongest argument against scalar registry; if Section 2 stratification is revisited, start here.
- **Skill ΔES**: no live registry entry (Phase 87.4 dropped). Pooled `[p25, p75] = [−2.7pp, +3.0pp]` for reference.

---

#### 3.2.3 Rate vs. score-gap divergence (Conversion & Recovery cross-cut)

##### Axis-driver table

| metric | ELO sweep (raw rate) | ELO d / verdict | TC sweep (raw rate) | TC d / verdict | ELO sweep (score gap) | ELO d / verdict | TC sweep (score gap) | TC d / verdict |
|---|---|---|---|---|---|---|---|---|
| Conversion | 66.8% → 74.9% | 0.82 keep | 65.1% → 75.6% | 1.02 keep | −14.0pp → −0.3pp | 1.62 keep | −13.1pp → −2.0pp | 1.20 keep |
| Recovery | 29.7% → 33.0% | 0.40 review | 35.6% → 25.0% | 1.10 keep | +10.7pp → +4.3pp | 0.88 keep | +12.8pp → +1.0pp | 1.63 keep |

##### Findings

- **Conversion**: rate and gap agree — both axes are `keep separate`. Strong cohort effect on both axes. Conversion is a genuine two-axis metric.
- **Recovery**: raw-rate verdict is **TC-only** (TC keep / ELO review). The score-gap **re-exposes the ELO signal** (ELO keep at d=0.88). Mechanism: raw recovery is flat across ELO because opponents also convert better as the cohort strengthens; subtracting `ES_entry` removes the matched-opponent effect and exposes that weaker players over-perform the engine far more (+10.7pp) than strong ones (+4.3pp).
- **Mirror-axis note**: TC moves recovery and conversion **opposite directions** in raw rate — more time → less recovery (because opponents convert cleanly) but more conversion (because the user converts cleanly). On TC, the score gaps for both compress toward their bucket-specific sigmoid nulls as games slow.

##### Implication

The recovery-gap ELO `keep separate` (d=0.88) is the strongest single argument against the §3.2.2 scalar-registry decision. **Recommendation for this phase**: scalar pooled band ships unchanged (matches live). Flag recovery ΔES as the first candidate if/when per-(TC × ELO) stratification of Section 2 is revisited.

---

### 3.3 Time Pressure

#### 3.3.1 Clock pressure at endgame entry

**Currently set in code**

| Constant | Live value | File |
|---|---:|---|
| `NEUTRAL_PCT_THRESHOLD` | `5.0` (±5%) | `app/services/endgame_zones.py` |
| `NEUTRAL_TIMEOUT_THRESHOLD` | `5.0` (±5pp) | same |
| `ZONE_REGISTRY["avg_clock_diff_pct"]` | `(−5.0, +5.0)` | same |
| `ZONE_REGISTRY["net_timeout_rate"]` | `(−5.0, +5.0)` | same |

#### Pooled distributions (sparse excluded)

| Metric | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| Clock-diff % (user − opp / base time) | 1,743 | −1.3% | **−6.4%** | −0.5% | **+4.7%** |
| Net timeout rate (W − L / total · 100) | 1,743 | +0.1% | **−4.4pp** | +1.0pp | **+5.6pp** |

#### Clock-diff % — p50 cell grid

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −0.7% (98) | −0.8% (100) | +1.2% (96) | +0.2% (38) |
| 1200 | −0.4% (100) | −0.5% (99) | −0.1% (100) | +1.2% (72) |
| 1600 | −0.2% (99) | −1.7% (100) | −0.1% (100) | −0.2% (85) |
| 2000 | −1.5% (100) | −1.5% (100) | −1.3% (98) | −5.7% (64) |
| 2400 | +0.1% (99) | −0.0% (100) | −3.3% (95) | +4.3% (2)* |

#### Clock-diff % — ELO marginal

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 332 | −1.1% | −6.0% | −0.3% | +4.9% |
| 1200 | 371 | −1.2% | −6.1% | −0.2% | +5.1% |
| 1600 | 384 | −1.4% | −6.8% | −0.4% | +5.1% |
| 2000 | 362 | −2.2% | −8.1% | −1.8% | +3.2% |
| 2400 | 294 | −0.3% | −4.8% | −0.2% | +4.4% |

#### Clock-diff % — TC marginal

| TC | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| bullet | 496 | −0.2% | −3.8% | −0.4% | +2.8% |
| blitz | 499 | −1.4% | −7.1% | −0.8% | +4.7% |
| rapid | 489 | −1.5% | −8.2% | −0.3% | +5.3% |
| classical | 259 | −2.7% | −12.3% | −0.7% | +8.0% |

Verdict — TC d_max = **0.23** → **review**; ELO d_max = **0.21** (2000 vs 2400) → **review**.

#### Net timeout — p50 cell grid (in pp)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −5.3pp (98) | −0.3pp (100) | +1.3pp (96) | 0.0pp (38) |
| 1200 | −0.6pp (100) | +2.0pp (99) | +1.2pp (100) | 0.0pp (72) |
| 1600 | +2.0pp (99) | +1.1pp (100) | +2.0pp (100) | 0.0pp (85) |
| 2000 | +2.2pp (100) | +2.3pp (100) | +2.0pp (98) | +0.6pp (64) |
| 2400 | +5.5pp (99) | +2.0pp (100) | +2.4pp (95) | 0.0pp (2)* |

#### Net timeout — ELO marginal

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 332 | −2.0pp | −7.3pp | 0.0pp | +4.1pp |
| 1200 | 371 | −0.3pp | −4.2pp | +0.6pp | +4.3pp |
| 1600 | 384 | −0.2pp | −3.3pp | +1.2pp | +5.1pp |
| 2000 | 362 | +0.6pp | −4.8pp | +1.5pp | +6.4pp |
| 2400 | 294 | +2.8pp | −2.8pp | +3.1pp | +9.5pp |

#### Net timeout — TC marginal

| TC | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| bullet | 496 | +0.4pp | −11.4pp | +1.9pp | +11.5pp |
| blitz | 499 | −0.0pp | −5.9pp | +1.2pp | +7.7pp |
| rapid | 489 | +0.2pp | −1.7pp | +1.6pp | +3.9pp |
| classical | 259 | −0.3pp | 0.0pp | 0.0pp | +1.7pp |

Verdict — TC d_max = **0.07** → **collapse**; ELO d_max = **0.41** (800 vs 2400) → **review**.

#### Recommendations (§3.3.1)

- **Clock-diff %** pooled `[p25, p75] = [−6.4%, +4.7%]`. Live `±5%` is within 1.4pp on the lower side. **Action: keep**. TC + ELO both `review` (d ~0.22); no stratification trigger.
- **Net timeout rate** pooled `[p25, p75] = [−4.4pp, +5.6pp]`. Live `±5pp` is within 0.6pp. **Action: keep**. TC `collapse` (d=0.07) confirms net timeout is TC-independent at the user level.

---

#### 3.3.2 Time pressure vs performance

#### TC marginal (10 time-buckets, pool ELO across each TC, sparse cell excluded)

`tb` = floor(user_clock_pct/10), 0=most pressure, 9=full clock.

| tb | bullet n / score | blitz n / score | rapid n / score | classical n / score |
|---:|---:|---:|---:|---:|
| 0 | 15,275 / 26.0% | 14,823 / 33.4% | 5,686 / 33.8% | 1,391 / 41.0% |
| 1 | 25,401 / 39.9% | 16,660 / 43.7% | 5,987 / 44.1% | 945 / 45.2% |
| 2 | 27,230 / 49.1% | 17,700 / 49.2% | 7,563 / 46.9% | 1,125 / 46.8% |
| 3 | 30,735 / 53.0% | 21,039 / 51.8% | 9,892 / 50.8% | 1,325 / 47.5% |
| 4 | 31,404 / 55.2% | 24,283 / 53.4% | 12,704 / 53.2% | 1,596 / 47.8% |
| 5 | 29,148 / 56.4% | 26,875 / 54.8% | 16,604 / 53.3% | 2,002 / 48.7% |
| 6 | 23,294 / 56.3% | 26,851 / 54.4% | 21,177 / 52.9% | 2,556 / 50.5% |
| 7 | 14,683 / 55.3% | 21,931 / 54.2% | 24,233 / 52.3% | 3,173 / 51.0% |
| 8 | 5,843 / 54.2% | 12,420 / 53.4% | 20,363 / 52.4% | 3,750 / 50.2% |
| 9 | 1,235 / 50.0% | 4,776 / 52.3% | 9,602 / 52.4% | 9,857 / 51.0% |

#### ELO marginal (10 time-buckets, pool TC, sparse excluded)

| tb | 800 n / score | 1200 n / score | 1600 n / score | 2000 n / score | 2400 n / score |
|---:|---:|---:|---:|---:|---:|
| 0 | 5,390 / 26.6% | 7,308 / 28.3% | 8,383 / 30.4% | 9,617 / 33.2% | 6,477 / 33.6% |
| 1 | 6,569 / 38.1% | 9,620 / 40.0% | 10,763 / 40.1% | 11,859 / 43.3% | 10,182 / 46.1% |
| 2 | 7,060 / 46.9% | 10,340 / 47.3% | 11,754 / 48.4% | 13,029 / 49.4% | 11,435 / 51.1% |
| 3 | 8,135 / 51.1% | 12,427 / 51.2% | 14,257 / 51.6% | 15,140 / 52.5% | 13,032 / 53.8% |
| 4 | 9,083 / 53.1% | 14,200 / 53.0% | 16,479 / 53.5% | 16,248 / 54.2% | 13,977 / 56.3% |
| 5 | 9,698 / 53.8% | 15,517 / 53.2% | 18,660 / 53.7% | 16,957 / 56.3% | 13,797 / 57.5% |
| 6 | 10,174 / 52.6% | 16,274 / 52.7% | 19,217 / 53.7% | 15,824 / 55.9% | 12,389 / 57.5% |
| 7 | 9,267 / 51.5% | 15,453 / 51.8% | 17,516 / 53.2% | 12,845 / 55.2% | 8,939 / 57.1% |
| 8 | 6,820 / 49.7% | 11,898 / 51.8% | 12,070 / 52.4% | 7,419 / 55.3% | 4,169 / 57.1% |
| 9 | 5,320 / 49.0% | 8,527 / 50.1% | 7,433 / 53.7% | 3,316 / 54.7% | 874 / 56.4% |

#### Collapse verdict

- TC axis: d_max across time-buckets = **0.34** (tb=0, bullet vs classical) → **review**
- ELO axis: d_max across time-buckets = **0.17** (tb=1, 800 vs 2400) → **collapse**

#### Recommendations

- **ELO `collapse` (d=0.17)**: time-pressure curve is well-collapsed across ELO buckets. Pooling ELO when displaying the curve is justified.
- **TC `review` (d=0.34)**: driven entirely by tb=0 (severe time pressure < 10% remaining): bullet 26.0% vs classical 41.0%. At low time pressure (tb≥4) TC differences shrink to d~0.1. The curve **shape** is TC-similar but the **severe-pressure floor** is markedly lower in bullet. Live overlay-by-TC is justified at the low-pressure end; consider a per-TC curve series even though the rest collapses.

#### §3.3.1 clock-gap-% submetric

**Question:** How does per-user mean `(user_clock - opp_clock) / base_clock` at endgame entry distribute, and can TC and ELO be pooled for a single scalar zone band?

**Snapshot:** 2026-05-17 benchmark DB. Equal-footing filter applied (`|opp − user| ≤ 100`). Sparse cell `(2400, classical)` excluded. Minimum 20 games per user per cell. Total pooled n = 1,743 users.

##### Per-(ELO, TC) cell table

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −0.51% (n=98) | −2.82% (n=100) | −0.59% (n=96) | −1.73% (n=38) |
| 1200 | −0.16% (n=100) | −1.48% (n=99) | −1.66% (n=100) | −1.46% (n=72) |
| 1600 | −0.29% (n=99) | −1.54% (n=100) | −1.44% (n=100) | −2.65% (n=85) |
| 2000 | −1.12% (n=100) | −2.02% (n=100) | −1.91% (n=98) | −4.76% (n=64) |
| 2400 | −0.01% (n=99) | +0.85% (n=100) | −1.79% (n=95) | — (sparse)* |

`*` Sparse cell excluded.

Note: values in percent (`mean_gap_frac * 100`). Near-zero medians throughout; gap_p50 in the pooled range is approximately 0.

##### TC marginal (ELO pooled, sparse excluded)

| TC | n_users | gap_mean | gap_var |
|---:|---:|---:|---:|
| bullet | 496 | −0.22% | 0.003358 |
| blitz | 499 | −1.40% | 0.008632 |
| rapid | 489 | −1.48% | 0.009814 |
| classical | 259 | −2.71% | 0.026778 |

##### ELO marginal (TC pooled, sparse excluded)

| ELO | n_users | gap_mean | gap_var |
|---:|---:|---:|---:|
| 800 | 332 | −1.07% | 0.009405 |
| 1200 | 371 | −1.17% | 0.011204 |
| 1600 | 384 | −1.43% | 0.012988 |
| 2000 | 362 | −2.23% | 0.010784 |
| 2400 | 294 | −0.29% | 0.005393 |

##### Collapse verdicts

Cohen's d formula: `d = |mean_a - mean_b| / pooled_sd`.

- **TC axis:** d_max = **0.23** (bullet vs classical) → **review** (0.20–0.50). Largest gap is bullet (+0.22%) vs classical (−2.71%) = 2.49pp difference, pooled SD ≈ 10.9pp.
- **ELO axis:** d_max = **0.21** (2000 vs 2400) → **review** (0.20–0.50). Largest gap is 2000 (−2.23%) vs 2400 (−0.29%) = 1.94pp difference.

Both axes are "review" (d ~0.21–0.23). No axis reaches the 0.5 keep-separate threshold.

##### Pooled IQR band

From the pooled distribution across all cells (n=1,743):

| n | gap_p25 | gap_p50 | gap_p75 |
|---:|---:|---:|---:|
| 1,743 | −6.41% | ≈0% | +4.66% |

**Conclusion:** Both axes are "review" but neither reaches "keep separate". The pooled band `[−0.0641, +0.0466]` is the calibrated zone for `ZONE_REGISTRY["clock_gap_pct"]`. This is asymmetric (lower = −6.4%, upper = +4.7%) because blitz/rapid/classical users tend to enter endgames with a slight clock deficit.

**Recommended value:** `ZoneSpec(typical_lower=-0.065, typical_upper=0.047, direction="higher_is_better")`. Rounded to 3dp from the exact pooled IQR.

---

#### §3.3.3 chess-score-per-pressure-bin

**Question:** How does per-user chess score distribute across clock-pressure quintiles per (TC, ELO) cell, and can ELO (and TC) be pooled per quintile for a calibrated neutral-zone band?

**Snapshot:** 2026-05-17 benchmark DB. Equal-footing filter applied. Sparse cell `(2400, classical)` excluded. Minimum 5 games per user per (TC, quintile) cell for the per-user quintile aggregation; minimum 10 users per cell for group statistics. Total rows: 92 cells across the full 5 × 5 × 4 grid (quintile × ELO × TC, sparse excluded + some below 10-user floor dropped).

##### Per-(quintile, ELO, TC) cell table (selected cells)

Full raw output (92 rows). Key cells:

| quintile | elo_bucket | tc | n_users | mean_score | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 800 | bullet | 98 | 0.3200 | 0.2598 | 0.3212 | 0.3694 |
| 0 | 800 | classical | — | — | — | — | — |
| 0 | 2400 | bullet | 99 | 0.3971 | 0.3346 | 0.4000 | 0.4634 |
| 0 | 2400 | rapid | 84 | 0.4541 | 0.3687 | 0.4485 | 0.5116 |
| 4 | 800 | bullet | 34 | 0.5713 | 0.5000 | 0.5465 | 0.6758 |
| 4 | 2400 | blitz | 83 | 0.6034 | 0.5242 | 0.6000 | 0.6667 |

##### Collapse verdicts per quintile

Cohen's d computed from TC and ELO marginals. Max pairwise d across 4 TC levels (6 pairs) and 5 ELO levels (10 pairs), sparse cell excluded.

| Quintile | Range | TC axis d_max (worst pair) | TC verdict | ELO axis d_max (worst pair) | ELO verdict |
|---:|---:|---:|---:|---:|---:|
| Q0 | 0–20% clock | **0.63** (bullet vs classical) | **keep separate** | **0.79** (800 vs 2400) | **keep separate** |
| Q1 | 20–40% | 0.29 (bullet vs classical) | review | 0.43 (800 vs 2400) | review |
| Q2 | 40–60% | **0.63** (bullet vs classical) | **keep separate** | **0.58** (1200 vs 2400) | **keep separate** |
| Q3 | 60–80% | 0.39 (bullet vs classical) | review | **0.61** (1200 vs 2400) | **keep separate** |
| Q4 | 80–100% | 0.22 (bullet vs classical) | review | **0.71** (800 vs 2400) | **keep separate** |

**Summary:**
- TC axis: Q0 and Q2 `keep separate` (d ≥ 0.5); Q1, Q3, Q4 `review` (0.2–0.5).
- ELO axis: ALL 5 quintiles are `keep separate` or `review` — ELO does NOT collapse for any quintile. Q0 is the most extreme (d=0.79), Q1 is the mildest (d=0.43).

**This is a blocking decision point** — the Plan 03 scaffolded 4×5 (TC, quintile) shape assumes ELO collapse per quintile. The data contradicts that assumption across all quintiles. See Plan 08 Task 2 checkpoint for resolution options.

##### TC marginals per quintile (ELO pooled, for TC axis verdict)

| Quintile | bullet (n, mean) | blitz (n, mean) | rapid (n, mean) | classical (n, mean) |
|---:|---:|---:|---:|---:|
| Q0 | 493, 0.3531 | 475, 0.3903 | 338, 0.4012 | 82, 0.4236 |
| Q1 | 497, 0.5192 | 494, 0.5159 | 429, 0.5055 | 122, 0.4874 |
| Q2 | 496, 0.5661 | 492, 0.5519 | 474, 0.5479 | 160, 0.4979 |
| Q3 | 488, 0.5670 | 492, 0.5593 | 485, 0.5450 | 211, 0.5205 |
| Q4 | 309, 0.5538 | 435, 0.5444 | 434, 0.5366 | 305, 0.5197 |

##### ELO marginals per quintile (TC pooled, for ELO axis verdict)

| Quintile | 800 (n, mean) | 1200 (n, mean) | 1600 (n, mean) | 2000 (n, mean) | 2400 (n, mean) |
|---:|---:|---:|---:|---:|---:|
| Q0 | 233, 0.3326 | 257, 0.3562 | 297, 0.3740 | 318, 0.4021 | 283, 0.4306 |
| Q1 | 268, 0.4879 | 303, 0.5026 | 334, 0.5107 | 346, 0.5184 | 291, 0.5368 |
| Q2 | 287, 0.5372 | 328, 0.5324 | 364, 0.5386 | 350, 0.5558 | 293, 0.5881 |
| Q3 | 307, 0.5256 | 351, 0.5302 | 374, 0.5471 | 355, 0.5714 | 289, 0.5920 |
| Q4 | 273, 0.4830 | 328, 0.5292 | 346, 0.5365 | 319, 0.5650 | 217, 0.5901 |

##### 4×5 pooled (TC, quintile) IQR band table — ELO collapsed

This table shows the shipped band shape if ELO is accepted as pooled-with-caveat (the per-ELO divergence is acknowledged but not stratified at the schema level). Editorial cap `PRESSURE_BIN_NEUTRAL_CAP = 0.06` applied symmetrically around p50 when half-width > 0.06.

| tc | quintile | n_users | p25 | p50 | p75 | half_w | band_lower | band_upper | cap? |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 0 | 493 | 0.2872 | 0.3495 | 0.4138 | 0.0633 | 0.2895 | 0.4095 | yes |
| bullet | 1 | 497 | 0.4645 | 0.5126 | 0.5650 | 0.0502 | 0.4645 | 0.5650 | — |
| bullet | 2 | 496 | 0.5198 | 0.5578 | 0.6071 | 0.0437 | 0.5198 | 0.6071 | — |
| bullet | 3 | 488 | 0.5066 | 0.5629 | 0.6230 | 0.0582 | 0.5066 | 0.6230 | — |
| bullet | 4 | 309 | 0.4414 | 0.5455 | 0.6538 | 0.1062 | 0.4855 | 0.6055 | yes |
| blitz | 0 | 475 | 0.3070 | 0.3889 | 0.4667 | 0.0799 | 0.3289 | 0.4489 | yes |
| blitz | 1 | 494 | 0.4554 | 0.5133 | 0.5784 | 0.0615 | 0.4533 | 0.5733 | yes |
| blitz | 2 | 492 | 0.4930 | 0.5487 | 0.6017 | 0.0544 | 0.4930 | 0.6017 | — |
| blitz | 3 | 492 | 0.5000 | 0.5598 | 0.6146 | 0.0573 | 0.5000 | 0.6146 | — |
| blitz | 4 | 435 | 0.4615 | 0.5500 | 0.6250 | 0.0818 | 0.4900 | 0.6100 | yes |
| rapid | 0 | 338 | 0.3000 | 0.4000 | 0.5000 | 0.1000 | 0.3400 | 0.4600 | yes |
| rapid | 1 | 429 | 0.4340 | 0.5000 | 0.5753 | 0.0707 | 0.4400 | 0.5600 | yes |
| rapid | 2 | 474 | 0.4858 | 0.5421 | 0.6111 | 0.0627 | 0.4821 | 0.6021 | yes |
| rapid | 3 | 485 | 0.4808 | 0.5390 | 0.6000 | 0.0596 | 0.4808 | 0.6000 | — |
| rapid | 4 | 434 | 0.4688 | 0.5370 | 0.6077 | 0.0695 | 0.4770 | 0.5970 | yes |
| classical | 0 | 82 | 0.3290 | 0.4183 | 0.5515 | 0.1113 | 0.3583 | 0.4783 | yes |
| classical | 1 | 122 | 0.3718 | 0.5000 | 0.5833 | 0.1058 | 0.4400 | 0.5600 | yes |
| classical | 2 | 160 | 0.3919 | 0.5000 | 0.5897 | 0.0989 | 0.4400 | 0.5600 | yes |
| classical | 3 | 211 | 0.4198 | 0.5000 | 0.6124 | 0.0963 | 0.4400 | 0.5600 | yes |
| classical | 4 | 305 | 0.4205 | 0.5183 | 0.6094 | 0.0945 | 0.4583 | 0.5783 | yes |

Cap activated in 12 of 20 cells. The editorial cap prevents extreme IQR widths (especially in classical and Q0/Q4 extreme quintiles) from creating unusably wide bands.

##### Ready-to-use Python dict (accept-pooled-with-caveat resolution)

```python
PRESSURE_BIN_SCORE_NEUTRAL_ZONES = {
    "bullet": {
        0: PressureBinBand(0.2895, 0.4095),  # editorial cap; raw IQR [0.2872, 0.4138], half-width 0.0633
        1: PressureBinBand(0.4645, 0.5650),  # raw IQR; half-width 0.0502
        2: PressureBinBand(0.5198, 0.6071),  # raw IQR; half-width 0.0437
        3: PressureBinBand(0.5066, 0.6230),  # raw IQR; half-width 0.0582
        4: PressureBinBand(0.4855, 0.6055),  # editorial cap; raw IQR [0.4414, 0.6538], half-width 0.1062
    },
    "blitz": {
        0: PressureBinBand(0.3289, 0.4489),  # editorial cap; raw IQR [0.3070, 0.4667], half-width 0.0799
        1: PressureBinBand(0.4533, 0.5733),  # editorial cap; raw IQR [0.4554, 0.5784], half-width 0.0615
        2: PressureBinBand(0.4930, 0.6017),  # raw IQR; half-width 0.0544
        3: PressureBinBand(0.5000, 0.6146),  # raw IQR; half-width 0.0573
        4: PressureBinBand(0.4900, 0.6100),  # editorial cap; raw IQR [0.4615, 0.6250], half-width 0.0818
    },
    "rapid": {
        0: PressureBinBand(0.3400, 0.4600),  # editorial cap; raw IQR [0.3000, 0.5000], half-width 0.1000
        1: PressureBinBand(0.4400, 0.5600),  # editorial cap; raw IQR [0.4340, 0.5753], half-width 0.0707
        2: PressureBinBand(0.4821, 0.6021),  # editorial cap; raw IQR [0.4858, 0.6111], half-width 0.0627
        3: PressureBinBand(0.4808, 0.6000),  # raw IQR; half-width 0.0596
        4: PressureBinBand(0.4770, 0.5970),  # editorial cap; raw IQR [0.4688, 0.6077], half-width 0.0695
    },
    "classical": {
        0: PressureBinBand(0.3583, 0.4783),  # editorial cap; raw IQR [0.3290, 0.5515], half-width 0.1113
        1: PressureBinBand(0.4400, 0.5600),  # editorial cap; raw IQR [0.3718, 0.5833], half-width 0.1058
        2: PressureBinBand(0.4400, 0.5600),  # editorial cap; raw IQR [0.3919, 0.5897], half-width 0.0989
        3: PressureBinBand(0.4400, 0.5600),  # editorial cap; raw IQR [0.4198, 0.6124], half-width 0.0963
        4: PressureBinBand(0.4583, 0.5783),  # editorial cap; raw IQR [0.4205, 0.6094], half-width 0.0945
    },
}
```

**Caveat:** ELO does NOT collapse for any quintile (d=0.43–0.79). The pooled bands above fold a real ELO gradient into a single wide band — the editorial cap then truncates that width. A higher-rated user (ELO 2400) has a meaningfully different score distribution than a lower-rated user (ELO 800) within the same pressure bin, particularly at Q0 (800 mean=0.33 vs 2400 mean=0.43). The pooled band centered near the population median is a fair approximation but will mis-classify the extremes.

---

### 3.4 Endgame Type Breakdown

#### 3.4.1 Per-class score / conversion / recovery

**Currently set in code**

| Constant | Live value | File |
|---|---:|---|
| `PER_CLASS_GAUGE_ZONES.<class>.conversion` / `.recovery` | per-class IQR-derived bands | `app/services/endgame_zones.py` |
| Score-bullet (per-class card) | shared global `SCORE_BULLET_NEUTRAL_*` = `[0.45, 0.55]` | `frontend/src/lib/scoreBulletConfig.ts` |

Phase 87 retired the per-class score-diff bullet and replaced it with an absolute chess-score bullet vs 50%.

#### Pooled-by-class (cell-level, equal-footing applied, sparse cell included in totals)

| endgame_class | games | users | score | score_diff | conv_games | conversion | recov_games | recovery |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rook | 94,106 | 1,848 | 50.8% | +1.5pp | 32,586 | 71.0% | 30,814 | 29.6% |
| minor_piece | 70,396 | 1,831 | 51.0% | +2.1pp | 23,987 | 69.5% | 23,239 | 32.8% |
| pawn | 37,466 | 1,752 | 51.1% | +2.1pp | 14,637 | 73.8% | 13,920 | 27.5% |
| queen | 34,432 | 1,764 | 50.8% | +1.6pp | 14,419 | 77.4% | 13,790 | 23.4% |
| mixed | 529,701 | 1,894 | 50.6% | +1.1pp | 204,411 | 69.4% | 199,182 | 31.1% |
| pawnless | 5,847 | 1,365 | 50.7% | +1.4pp | 2,515 | 79.1% | 2,363 | 19.8% |

#### Per-class chess-score IQR (per-user, ≥10 games/class, sparse excluded)

| endgame_class | n_users | mean | p10 | p25 | p50 | p75 | p90 |
|---|---:|---:|---:|---:|---:|---:|---:|
| rook | 1,533 | 50.4% | 37.5% | 44.0% | 50.0% | 57.1% | 63.4% |
| minor_piece | 1,417 | 50.4% | 35.7% | 43.3% | 50.8% | 57.8% | 65.0% |
| pawn | 1,149 | 50.2% | 34.4% | 42.1% | 50.0% | 58.9% | 66.7% |
| queen | 1,149 | 51.7% | 32.1% | 41.1% | 52.4% | 62.5% | 70.6% |
| mixed | 1,815 | 51.4% | 41.9% | 46.1% | 50.9% | 56.1% | 61.7% |
| pawnless | 119 | 43.6% | 25.0% | 30.3% | 40.0% | 54.8% | 68.2% |

#### Per-class score — p50 cell grid + marginals

##### rook

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 47.3% (77) | 48.9% (85) | 45.6% (82) | 38.7% (9) |
| 1200 | 48.5% (95) | 50.0% (98) | 49.1% (92) | 50.0% (46) |
| 1600 | 48.8% (96) | 50.0% (98) | 51.4% (93) | 50.0% (61) |
| 2000 | 49.9% (100) | 52.4% (95) | 53.3% (90) | 52.9% (43) |
| 2400 | 52.9% (98) | 53.1% (95) | 55.0% (80) | (no users)* |

| TC | n | mean | | ELO | n | mean |
|---|---:|---:|---|---:|---:|---:|
| bullet | 466 | 49.4% | | 800 | 253 | 47.9% |
| blitz | 471 | 50.8% | | 1200 | 331 | 49.0% |
| rapid | 437 | 51.6% | | 1600 | 348 | 50.2% |
| classical | 159 | 49.2% | | 2000 | 328 | 51.7% |
| | | | | 2400 | 273 | 53.4% |

Verdict — TC d_max = **0.21** → review; ELO d_max = **0.53** (800 vs 2400) → **keep separate**.

##### minor_piece

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 44.8% (53) | 48.0% (71) | 50.0% (66) | 56.4% (4) |
| 1200 | 49.5% (93) | 48.1% (94) | 46.0% (78) | 49.3% (27) |
| 1600 | 51.6% (94) | 51.9% (98) | 50.0% (91) | 45.2% (52) |
| 2000 | 50.0% (98) | 53.4% (96) | 52.0% (93) | 53.3% (40) |
| 2400 | 52.5% (99) | 54.3% (94) | 55.6% (76) | (no users)* |

| TC | n | mean | | ELO | n | mean |
|---|---:|---:|---|---:|---:|---:|
| bullet | 437 | 49.6% | | 800 | 194 | 47.6% |
| blitz | 453 | 50.9% | | 1200 | 292 | 47.9% |
| rapid | 404 | 51.1% | | 1600 | 335 | 50.0% |
| classical | 123 | 49.3% | | 2000 | 327 | 51.8% |
| | | | | 2400 | 269 | 54.1% |

Verdict — TC d_max = **0.14** → collapse; ELO d_max = **0.57** (800 vs 2400) → **keep separate**.

##### pawn

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 41.7% (27) | 50.0% (52) | 53.3% (35) | 36.7% (2) |
| 1200 | 46.7% (70) | 45.8% (83) | 49.3% (66) | 44.5% (12) |
| 1600 | 50.0% (83) | 52.8% (90) | 48.1% (84) | 50.0% (36) |
| 2000 | 50.0% (94) | 53.9% (92) | 51.4% (81) | 53.7% (20) |
| 2400 | 51.2% (94) | 52.8% (80) | 52.1% (48) | (no users)* |

| TC | n | mean | | ELO | n | mean |
|---|---:|---:|---|---:|---:|---:|
| bullet | 368 | 49.3% | | 800 | 116 | 48.5% |
| blitz | 397 | 50.9% | | 1200 | 231 | 47.4% |
| rapid | 314 | 50.5% | | 1600 | 293 | 50.3% |
| classical | 70 | 49.3% | | 2000 | 287 | 51.2% |
| | | | | 2400 | 222 | 52.5% |

Verdict — TC d_max = **0.13** → collapse; ELO d_max = **0.42** (1200 vs 2400) → **review**.

##### queen

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 50.0% (33) | 51.7% (62) | 50.0% (57) | 32.4% (3) |
| 1200 | 47.8% (69) | 50.0% (85) | 53.5% (74) | 47.5% (13) |
| 1600 | 47.9% (82) | 52.7% (86) | 60.1% (74) | 58.0% (28) |
| 2000 | 52.9% (95) | 51.2% (87) | 54.2% (70) | 53.9% (12) |
| 2400 | 52.5% (93) | 53.8% (84) | 52.4% (42) | (no users)* |

| TC | n | mean | | ELO | n | mean |
|---|---:|---:|---|---:|---:|---:|
| bullet | 372 | 50.6% | | 800 | 155 | 49.9% |
| blitz | 404 | 51.8% | | 1200 | 241 | 49.7% |
| rapid | 317 | 52.7% | | 1600 | 270 | 52.8% |
| classical | 56 | 51.7% | | 2000 | 264 | 52.7% |
| | | | | 2400 | 219 | 52.4% |

Verdict — TC d_max = **0.14** → collapse; ELO d_max = **0.19** (1200 vs 2000) → **collapse**.

##### mixed

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 47.4% (99) | 47.7% (100) | 48.8% (100) | 44.8% (60) |
| 1200 | 49.2% (100) | 48.2% (100) | 50.7% (100) | 51.1% (89) |
| 1600 | 49.8% (100) | 50.2% (100) | 51.7% (100) | 50.6% (94) |
| 2000 | 50.6% (100) | 52.6% (100) | 52.3% (100) | 54.1% (76) |
| 2400 | 52.4% (100) | 54.1% (100) | 55.0% (97) | 60.7% (4)* |

| TC | n | mean | | ELO | n | mean |
|---|---:|---:|---|---:|---:|---:|
| bullet | 499 | 50.3% | | 800 | 359 | 47.9% |
| blitz | 500 | 51.4% | | 1200 | 389 | 50.7% |
| rapid | 497 | 52.4% | | 1600 | 394 | 51.2% |
| classical | 319 | 51.4% | | 2000 | 376 | 52.9% |
| | | | | 2400 | 297 | 54.7% |

Verdict — TC d_max = **0.26** → review; ELO d_max = **0.81** (800 vs 2400) → **keep separate**.

##### pawnless — small samples; cells with n < 10 are noisy

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | — | 40.9% (17) | 40.3% (16) | — |
| 1200 | 25.0% (1) | 32.5% (10) | 40.9% (11) | 57.9% (2) |
| 1600 | 42.1% (2) | 40.0% (7) | 43.9% (12) | — |
| 2000 | 5.0% (1) | 40.0% (7) | 39.8% (4) | — |
| 2400 | 36.4% (7) | 40.4% (12) | 49.2% (10) | — |

| TC | n | mean | | ELO | n | mean |
|---|---:|---:|---|---:|---:|---:|
| bullet | 7 | 40.2% | | 800 | 33 | 46.3% |
| blitz | 53 | 42.8% | | 1200 | 23 | 42.0% |
| rapid | 53 | 45.6% | | 1600 | 19 | 43.6% |
| classical | 2 | 57.9% | | 2000 | 11 | 39.4% |
| | | | | 2400 | 29 | 45.7% |

Verdict — TC d_max = **0.16** → collapse; ELO d_max = **0.39** (2000 vs 2400) → review (low-confidence — most cells below n=10).

#### Recommendations (§3.4.1)

- **Per-class Score-bullet neutral zone** vs global `[0.45, 0.55]`: pooled p25/p75 by class:
  - rook `[0.44, 0.57]` — wider on upper, narrower on lower
  - minor_piece `[0.43, 0.58]`
  - pawn `[0.42, 0.59]`
  - queen `[0.41, 0.63]` — widest IQR (variance highest)
  - mixed `[0.46, 0.56]` — closest to global band
  - pawnless `[0.30, 0.55]` — heavy left skew (mean 43.6%) with very small per-cell n
  
  **Action**: every class's `[p25, p75]` midpoint stays within `[49.5%, 51.7%]` (within ±1pp of 0.50), so the global band's center is correct. The widths drift more (rook ±6.5pp, queen ±10.7pp). Per the threshold in SKILL ("propose per-class override if midpoint shifts >1pp from 0.50 OR width widens/narrows by >2pp"), **queen and pawn warrant a per-class override** (wider band) and **mixed warrants a slight tightening**. The principled fix is a new `PER_CLASS_SCORE_BULLET_ZONES` map in `endgame_zones.py`, codegen'd to TS. Suggested values:
  - rook: `(0.44, 0.57)`, minor_piece: `(0.43, 0.58)`, pawn: `(0.42, 0.59)`, queen: `(0.41, 0.63)`, mixed: `(0.46, 0.56)`, pawnless: hold global `(0.45, 0.55)` until sample density improves.

- **Per-class Conv/Recov gauges** (live `PER_CLASS_GAUGE_ZONES`): pooled rates vs live midpoints:
  - rook: live conv `(0.65, 0.75)`, recov `(0.26, 0.36)`. Pooled 71.0% / 29.6% — inside. **Keep**.
  - minor_piece: live conv `(0.63, 0.73)`, recov `(0.31, 0.41)`. Pooled 69.5% / 32.8% — inside. **Keep**.
  - pawn: live conv `(0.67, 0.79)`, recov `(0.23, 0.34)`. Pooled 73.8% / 27.5% — inside. **Keep**.
  - queen: live conv `(0.73, 0.83)`, recov `(0.20, 0.30)`. Pooled 77.4% / 23.4% — inside. **Keep**.
  - mixed: live conv `(0.65, 0.75)`, recov `(0.28, 0.38)`. Pooled 69.4% / 31.1% — inside. **Keep**.
  - pawnless: live conv `(0.70, 0.80)`, recov `(0.21, 0.31)`. Pooled 79.1% / 19.8% — at the edge; mean conversion exceeds live upper bound by 1pp. **Consider widening to `(0.70, 0.82)`**; recovery `(0.18, 0.28)` would re-center.

- **Collapse verdict per (metric × class)**: aggregated by axis the strongest signals are ELO `keep separate` on rook (d=0.53), minor_piece (d=0.57), and mixed (d=0.81); ELO `review` on pawn (d=0.42) and pawnless (d=0.39); ELO `collapse` on queen (d=0.19). TC collapses everywhere except rook (d=0.21 review) and mixed (d=0.26 review). Mixed is the only class with a strong ELO ramp; per-ELO stratification of the per-class score-bullet zones is the natural extension if Phase 87 wants to go further than per-class.

---

#### 3.4.2 Per-span Score Gap by Endgame Type

**Currently set in code**

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["endgame_type_achievable_score_gap"]` | `(−0.04, +0.04)` | `app/services/endgame_zones.py` |
| `PER_CLASS_GAUGE_ZONES.{class}.achievable_score_gap` | per-class (see registry) | same |

#### Pooled-by-class IQR (sparse cell excluded)

| endgame_class | n_users | pooled_mean | pooled_sd | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rook | 1,309 | −0.6pp | 8.0pp | −14.3pp | **−5.0pp** | +0.1pp | **+4.3pp** | +11.5pp |
| minor_piece | 1,129 | +0.4pp | 8.4pp | −13.2pp | **−4.2pp** | +0.6pp | **+5.5pp** | +12.9pp |
| pawn | 795 | +0.3pp | 6.8pp | −11.0pp | **−4.0pp** | +0.4pp | **+4.9pp** | +10.7pp |
| queen | 744 | −0.1pp | 7.6pp | −13.0pp | **−4.6pp** | +0.2pp | **+4.6pp** | +10.8pp |
| mixed | 1,743 | +0.2pp | 6.0pp | −9.9pp | **−3.1pp** | +0.5pp | **+3.5pp** | +9.1pp |
| pawnless | 7 | +0.9pp | 3.0pp | −3.5pp | +0.6pp | +1.3pp | +2.0pp | +4.1pp |

#### Per-class p50 cell grids + marginals

##### rook (per-class score-gap, in pp)

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −2.8pp (65) | −0.5pp (68) | +1.2pp (58) | −3.3pp (5) |
| 1200 | +0.5pp (89) | −0.2pp (92) | −0.3pp (79) | −3.5pp (20) |
| 1600 | +1.5pp (92) | −0.7pp (94) | +0.6pp (85) | −1.1pp (33) |
| 2000 | −1.4pp (97) | +0.6pp (92) | +1.4pp (80) | +0.7pp (20) |
| 2400 | +0.7pp (97) | +1.7pp (90) | +2.4pp (53) | (no users)* |

| TC | n | mean / sd | | ELO | n | mean / sd |
|---|---:|---|---|---:|---:|---|
| bullet | 440 | −1.3pp / 10.2pp | | 800 | 196 | −1.6pp / 8.4pp |
| blitz | 436 | −0.5pp / 7.0pp | | 1200 | 280 | −0.9pp / 7.8pp |
| rapid | 355 | +0.4pp / 6.6pp | | 1600 | 304 | −1.3pp / 8.3pp |
| classical | 78 | −1.2pp / 5.0pp | | 2000 | 289 | −0.1pp / 7.8pp |
| | | | | 2400 | 240 | +1.0pp / 7.7pp |

Verdict — TC d_max = **0.25** (rapid vs classical) → **review**; ELO d_max = **0.32** (800 vs 2400) → **review**.

##### minor_piece

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −4.9pp (27) | −1.3pp (45) | +3.5pp (33) | — |
| 1200 | +0.3pp (73) | −0.8pp (78) | −1.3pp (57) | −1.5pp (11) |
| 1600 | +0.5pp (86) | +0.0pp (89) | −0.2pp (78) | −2.7pp (29) |
| 2000 | +1.1pp (93) | +1.0pp (92) | +0.3pp (77) | +3.8pp (22) |
| 2400 | +2.0pp (97) | +2.5pp (90) | +3.2pp (52) | (no users)* |

| TC | n | mean / sd | | ELO | n | mean / sd |
|---|---:|---|---|---:|---:|---|
| bullet | 376 | +0.1pp / 11.0pp | | 800 | 105 | −0.4pp / 9.2pp |
| blitz | 394 | +0.3pp / 7.1pp | | 1200 | 219 | −0.9pp / 9.1pp |
| rapid | 297 | +0.8pp / 6.6pp | | 1600 | 282 | −0.3pp / 8.5pp |
| classical | 62 | +0.0pp / 5.6pp | | 2000 | 284 | +0.6pp / 8.3pp |
| | | | | 2400 | 239 | +2.3pp / 7.1pp |

Verdict — TC d_max = **0.12** → **collapse**; ELO d_max = **0.39** (1200 vs 2400) → **review**.

##### pawn

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −0.3pp (10) | +0.8pp (29) | −0.1pp (11) | — |
| 1200 | −1.7pp (44) | −2.5pp (63) | +1.1pp (44) | −0.7pp (4) |
| 1600 | +2.5pp (64) | −0.5pp (74) | +0.7pp (62) | +2.4pp (13) |
| 2000 | −0.6pp (80) | +0.7pp (68) | −0.5pp (56) | +4.2pp (8) |
| 2400 | +1.0pp (83) | +2.5pp (54) | +1.0pp (28) | (no users)* |

| TC | n | mean / sd | | ELO | n | mean / sd |
|---|---:|---|---|---:|---:|---|
| bullet | 281 | +0.3pp / 8.3pp | | 800 | 50 | +0.1pp / 6.2pp |
| blitz | 288 | +0.2pp / 6.2pp | | 1200 | 155 | −0.9pp / 7.4pp |
| rapid | 201 | +0.3pp / 5.5pp | | 1600 | 213 | +0.8pp / 6.5pp |
| classical | 25 | +1.9pp / 4.6pp | | 2000 | 212 | +0.2pp / 7.3pp |
| | | | | 2400 | 165 | +0.9pp / 6.3pp |

Verdict — TC d_max = **0.31** (rapid vs classical) → **review**; ELO d_max = **0.25** (1200 vs 2400) → **review**.

##### queen

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | +2.8pp (9) | +1.7pp (40) | +1.3pp (27) | — |
| 1200 | −1.8pp (43) | −2.6pp (57) | +1.2pp (42) | +0.4pp (6) |
| 1600 | +1.7pp (63) | −1.5pp (61) | +1.0pp (44) | −1.6pp (9) |
| 2000 | −1.0pp (80) | −0.0pp (58) | +1.9pp (42) | −3.1pp (5) |
| 2400 | +1.8pp (85) | −1.0pp (53) | −0.7pp (20) | (no users)* |

| TC | n | mean / sd | | ELO | n | mean / sd |
|---|---:|---|---|---:|---:|---|
| bullet | 280 | −0.0pp / 8.8pp | | 800 | 76 | +1.9pp / 6.6pp |
| blitz | 269 | −0.7pp / 7.3pp | | 1200 | 148 | −0.7pp / 6.9pp |
| rapid | 175 | +0.8pp / 6.0pp | | 1600 | 177 | +0.1pp / 7.3pp |
| classical | 20 | −2.1pp / 4.8pp | | 2000 | 185 | −0.3pp / 7.7pp |
| | | | | 2400 | 158 | −0.6pp / 8.7pp |

Verdict — TC d_max = **0.49** (rapid vs classical) → **review** (borderline keep); ELO d_max = **0.39** (800 vs 1200) → **review**.

##### mixed

| ELO \\ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | +0.8pp (98) | −0.9pp (100) | −1.1pp (96) | −3.6pp (40) |
| 1200 | +0.4pp (100) | −0.2pp (99) | −0.0pp (100) | −1.1pp (71) |
| 1600 | +0.6pp (100) | −0.4pp (100) | +0.3pp (100) | −0.5pp (83) |
| 2000 | +0.5pp (100) | +1.4pp (100) | +0.1pp (98) | +1.0pp (64) |
| 2400 | +2.0pp (100) | +3.1pp (100) | +1.9pp (94) | +6.2pp (2)* |

| TC | n | mean / sd | | ELO | n | mean / sd |
|---|---:|---|---|---:|---:|---|
| bullet | 498 | +0.2pp / 7.7pp | | 800 | 334 | −1.4pp / 7.9pp |
| blitz | 499 | +0.2pp / 5.1pp | | 1200 | 370 | −0.2pp / 6.0pp |
| rapid | 488 | +0.3pp / 4.6pp | | 1600 | 383 | −0.2pp / 5.4pp |
| classical | 258 | −0.5pp / 5.8pp | | 2000 | 362 | +0.7pp / 4.9pp |
| | | | | 2400 | 294 | +2.3pp / 4.5pp |

Verdict — TC d_max = **0.15** → **collapse**; ELO d_max = **0.57** (800 vs 2400) → **keep separate**.

##### pawnless — sample density too low for cell-level analysis (n=7 users pooled).

#### Recommendations (§3.4.2)

- **Per-class achievable_score_gap bands**: pooled `[p25, p75]` by class vs current `PER_CLASS_GAUGE_ZONES`:
  - rook: pooled `(−5.0pp, +4.3pp)` ≈ `(−0.05, +0.04)`. Live `(−0.05, 0.04)` matches. **Keep**.
  - minor_piece: pooled `(−4.2pp, +5.5pp)` ≈ `(−0.04, +0.06)`. Live matches exactly. **Keep**.
  - pawn: pooled `(−4.0pp, +4.9pp)` ≈ `(−0.04, +0.05)`. Live matches. **Keep**.
  - queen: pooled `(−4.6pp, +4.6pp)` ≈ `(−0.05, +0.05)`. Live matches. **Keep**.
  - mixed: pooled `(−3.1pp, +3.5pp)` ≈ `(−0.03, +0.04)`. Live matches. **Keep**.
  - pawnless: pooled (n=7) `(+0.6pp, +2.0pp)`. Live `(−0.05, +0.05)` is a defensible default (sample below floor). **Keep**.
- **Global band `endgame_type_achievable_score_gap`**: pooled-across-classes `[p25, p75]` ≈ `(−3.9pp, +4.3pp)` ≈ `(−0.04, +0.04)`. Live matches. **Keep**.
- **Collapse verdicts**: mixed is the only class where ELO `keep separate` (d=0.57); per-class plus per-ELO stratification deferred to a follow-on phase.

---

#### 3.4.3 Endgame Type Score vs Score Gap — agreement / redundancy

##### Per-class summary table (5 visible classes; sparse excluded)

| endgame_class | n_users | pearson_r | sign_agreement | zone_strict_agreement | strong_disagreement | score_stdev | gap_stdev |
|---|---:|---:|---:|---:|---:|---:|---:|
| rook | 1,309 | 0.592 | 66.8% | 58.0% | 3.1% | 0.0959 | 0.0804 |
| minor_piece | 1,129 | 0.599 | 71.9% | 57.3% | 1.8% | 0.1031 | 0.0839 |
| pawn | 795 | 0.535 | 69.1% | 54.7% | 2.1% | 0.1078 | 0.0683 |
| queen | 744 | 0.228 | 55.5% | 42.1% | 6.5% | 0.1378 | 0.0760 |
| mixed | 1,743 | 0.423 | 63.1% | 50.8% | 5.2% | 0.0800 | 0.0595 |

##### Per-class IQR band edges (used for zone classification)

| endgame_class | n_users | score_p25 | score_p75 | gap_p25 | gap_p75 |
|---|---:|---:|---:|---:|---:|
| rook | 1,309 | 44.3% | 56.7% | −5.0pp | +4.3pp |
| minor_piece | 1,129 | 44.3% | 57.4% | −4.2pp | +5.5pp |
| pawn | 795 | 43.9% | 58.7% | −4.0pp | +4.9pp |
| queen | 744 | 40.9% | 60.8% | −4.6pp | +4.6pp |
| mixed | 1,743 | 46.2% | 55.8% | −3.1pp | +3.5pp |

##### Effect-size ratio table (stdev / IQR-half-width)

| endgame_class | score_eff_ratio | gap_eff_ratio |
|---|---:|---:|
| rook | 1.55 | 1.72 |
| minor_piece | 1.57 | 1.74 |
| pawn | 1.46 | 1.55 |
| queen | 1.38 | 1.65 |
| mixed | 1.67 | 1.81 |

All ratios > 1.4 — both distributions have heavier tails than a perfectly uniform distribution across the IQR ±domain. Gauges will routinely paint extreme outside the IQR for both metrics.

##### Decision rubric per class

Applying the rubric from SKILL §3.4.3:

| endgame_class | r | strict agree | strong disagree | Verdict |
|---|---:|---:|---:|---|
| rook | 0.592 | 58.0% | 3.1% | **Drop WDL bar** (r 0.60–0.85 band borderline; strict 55–75% / strong < 10%) |
| minor_piece | 0.599 | 57.3% | 1.8% | **Drop WDL bar** |
| pawn | 0.535 | 54.7% | 2.1% | **Drop WDL bar** (strict ≈ 55%, strong < 10%) |
| queen | 0.228 | 42.1% | 6.5% | **Keep all three** (r < 0.6; strict < 55%; strong > 5%) |
| mixed | 0.423 | 50.8% | 5.2% | **Keep all three** |

**Mode verdict across the 5 visible classes**: **Drop WDL bar** (3 of 5 classes). Queen and mixed argue for "keep all three" but queen's r=0.23 is the outlier — different mechanisms dominate (high score-variance on queen endgames because they're typically decisive).

**Action recommendation**: Pursue "Drop WDL bar" — keeps Score + Score Gap as the two complementary bullets, plus Conv + Recov gauges as the glanceable anchor. Queen is the exception worth a footnote, not a card-layout branch. Layout decision, no code-constant action.

---

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | Subchapter | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|---|
| Middlegame-entry eval (centered) | 2.1 | review (0.25) | review (0.23) | Single global band defensible; live ±0.30 pawns matches |
| Non-Endgame Score (per-user) | 3.1.1 | **keep (0.50)** | review (0.49) | TC stratification candidate if dedicated non-EG module is built |
| Endgame-entry eval (uncentered, pawns) | 3.1.2 | review (0.22) | review (0.28) | Single global band justified; live ±0.75 pawns matches |
| Achievable Score | 3.1.3 | review (0.22) | review (0.23) | Single global band; live `(0.45, 0.55)` matches |
| Endgame Score (per-user, EG-only) | 3.1.4 | review (0.27) | **keep (0.84)** | Strong ELO ramp; per-ELO stratification deferred |
| Achievable Score Gap | 3.1.5 | collapse (0.15) | **keep (0.62)** | Live `(−0.05, +0.05)` matches; per-ELO deferred |
| Endgame Score Gap (eg − non_eg) | 3.1.6 | review (0.34) | collapse (0.17) | Symmetric ±10pp justified; classical −5.3pp drift below trigger |
| Conversion (per-user) | 3.2.1 | **keep (1.02)** | **keep (0.82)** | Two-axis metric; live `(0.65, 0.77)` matches |
| Parity (per-user) | 3.2.1 | collapse (0.12) | review (0.48) | Live `(0.45, 0.55)` matches |
| Recovery (per-user) | 3.2.1 | **keep (1.10)** | review (0.40) | TC-stratification candidate; live `(0.24, 0.36)` matches |
| Endgame Skill (composite, retracted) | 3.2.1 | collapse (0.18) | **keep (0.78)** | Confirms Phase 87.4 retraction rationale |
| ΔES — Conversion bucket | 3.2.2 | **keep (1.20)** | **keep (1.62)** | Live `(−0.11, 0.00)` matches |
| ΔES — Parity bucket | 3.2.2 | collapse (0.18) | **keep (0.57)** | Live `(−0.04, +0.04)` matches |
| ΔES — Recovery bucket | 3.2.2 | **keep (1.63)** | **keep (0.88)** | Live `(+0.01, +0.11)` matches; strongest two-axis signal in report |
| ΔES — Skill aggregate (retracted) | 3.2.2 | collapse (0.17) | **keep (0.81)** | No live entry |
| Clock pressure %-of-base | 3.3.1 | review (0.23) | review (0.21) | Live ±5% within 1.4pp of pooled |
| Net timeout rate | 3.3.1 | collapse (0.07) | review (0.41) | Live ±5pp matches |
| Time-pressure curve (per-bucket) | 3.3.2 | review (0.34 @ tb=0) | collapse (0.17) | TC-overlay justified at severe-pressure end only |
| Clock gap % at endgame entry | §3.3.1 clock-gap-% | review (0.23) | review (0.21) | Pooled IQR `[−0.0641, +0.0466]`; pooled band justified |
| Chess score per pressure bin Q0 | §3.3.3 | **keep (0.63)** | **keep (0.79)** | ELO does NOT collapse; blocking decision required |
| Chess score per pressure bin Q1 | §3.3.3 | review (0.29) | review (0.43) | ELO does NOT collapse; blocking decision required |
| Chess score per pressure bin Q2 | §3.3.3 | **keep (0.63)** | **keep (0.58)** | ELO does NOT collapse; blocking decision required |
| Chess score per pressure bin Q3 | §3.3.3 | review (0.39) | **keep (0.61)** | ELO does NOT collapse; blocking decision required |
| Chess score per pressure bin Q4 | §3.3.3 | review (0.22) | **keep (0.71)** | ELO does NOT collapse; blocking decision required |
| Per-class score — rook | 3.4.1 | review (0.21) | **keep (0.53)** | Per-class score-bullet band recommended |
| Per-class score — minor_piece | 3.4.1 | collapse (0.14) | **keep (0.57)** | Per-class score-bullet band recommended |
| Per-class score — pawn | 3.4.1 | collapse (0.13) | review (0.42) | Per-class score-bullet band recommended |
| Per-class score — queen | 3.4.1 | collapse (0.14) | collapse (0.19) | Per-class score-bullet band (wider, highest variance) |
| Per-class score — mixed | 3.4.1 | review (0.26) | **keep (0.81)** | Strongest ELO ramp of any class |
| Per-class score — pawnless | 3.4.1 | collapse (0.16) | review (0.39) | Low-confidence (small n); defer |
| Per-class ΔES gap — rook | 3.4.2 | review (0.25) | review (0.32) | Live `(−0.05, +0.04)` matches |
| Per-class ΔES gap — minor_piece | 3.4.2 | collapse (0.12) | review (0.39) | Live `(−0.04, +0.06)` matches |
| Per-class ΔES gap — pawn | 3.4.2 | review (0.31) | review (0.25) | Live `(−0.04, +0.05)` matches |
| Per-class ΔES gap — queen | 3.4.2 | review (0.49) | review (0.39) | Live `(−0.05, +0.05)` matches |
| Per-class ΔES gap — mixed | 3.4.2 | collapse (0.15) | **keep (0.57)** | Live `(−0.03, +0.04)` matches; ELO drift not yet stratified |

---

## Recommended thresholds summary

| Metric | Subchapter | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|---|
| MG eval baseline (white) | 2.1 | `EVAL_BASELINE_PAWNS_WHITE` | `+0.25` | `+0.25` (measured +25 cp) | TC review / ELO review | **keep** |
| MG eval neutral band (pawns) | 2.1 | `EVAL_NEUTRAL_MIN/MAX_PAWNS` | `±0.30` | `±0.30` | TC review / ELO review | **keep** |
| MG eval bullet domain | 2.1 | `EVAL_BULLET_DOMAIN_PAWNS` | `1.5` | `1.5` | n/a | **keep** |
| Non-EG score band | 3.1.1 | shared `SCORE_BULLET_NEUTRAL_*` | `±0.05` → `[0.45, 0.55]` | dedicated non-EG `[0.47, 0.57]` | TC keep / ELO review | **introduce dedicated non-EG zones module** when needed |
| EG-entry eval neutral (pawns) | 3.1.2 | `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` | `±0.75` | `±0.75` | TC review / ELO review | **keep** |
| EG-entry eval domain | 3.1.2 | `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | `2.25` | `2.25` | n/a | **keep** |
| Achievable Score band | 3.1.3 | `entry_expected_score` | `(0.45, 0.55)` | `(0.46, 0.55)` | TC review / ELO review | **keep** |
| Endgame Score band | 3.1.4 | `endgame_score` | `(0.45, 0.55)` | `(0.46, 0.56)` | TC review / ELO keep | **keep** global; defer per-ELO stratification |
| Achievable Score Gap band | 3.1.5 | `achievable_score_gap` | `(−0.05, +0.05)` | `(−0.04, +0.05)` | TC collapse / ELO keep | **keep** |
| Score Gap (eg − non_eg) band | 3.1.6 | `score_gap` | `(−0.10, +0.10)` | `(−0.10, +0.10)` | TC review / ELO collapse | **keep** |
| Score Gap domain | 3.1.6 | `SCORE_GAP_DOMAIN` | `0.20` | `0.20` | n/a | **keep** |
| Conv (per-user) | 3.2.1 | `conversion_win_pct` | `(0.65, 0.77)` | `(0.66, 0.77)` | TC keep / ELO keep | **keep** |
| Parity (per-user) | 3.2.1 | `parity_score_pct` | `(0.45, 0.55)` | `(0.44, 0.56)` | TC collapse / ELO review | **keep** |
| Recov (per-user) | 3.2.1 | `recovery_save_pct` | `(0.24, 0.36)` | `(0.24, 0.36)` | TC keep / ELO review | **keep** |
| ΔES Conv band | 3.2.2 | `section2_score_gap_conv` | `(−0.11, 0.00)` | `(−0.11, 0.00)` | TC keep / ELO keep | **keep** |
| ΔES Parity band | 3.2.2 | `section2_score_gap_parity` | `(−0.04, +0.04)` | `(−0.04, +0.04)` | TC collapse / ELO keep | **keep** |
| ΔES Recov band | 3.2.2 | `section2_score_gap_recov` | `(+0.01, +0.11)` | `(+0.01, +0.11)` | TC keep / ELO keep | **keep** |
| Clock-diff % band | 3.3.1 | `NEUTRAL_PCT_THRESHOLD` | `±5%` | `±5%` | TC review / ELO review | **keep** |
| Net timeout band | 3.3.1 | `NEUTRAL_TIMEOUT_THRESHOLD` | `±5pp` | `±5pp` | TC collapse / ELO review | **keep** |
| Time-pressure curve | 3.3.2 | (chart config) | n/a | per-TC overlay at tb=0 end | TC review / ELO collapse | **keep**; optional per-TC overlay at severe-pressure end |
| Clock gap % band | §3.3.1 clock-gap-% | `clock_gap_pct` ZoneSpec | `(−0.05, 0.05)` (placeholder) | `(−0.065, 0.047)` | TC review / ELO review | **update** |
| Chess score per pressure bin | §3.3.3 | `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` | all `(−0.06, 0.06)` (placeholder) | 20-cell table above | TC keep Q0/Q2 / ELO keep all | **blocking decision** — see checkpoint |
| Per-class score bullet (rook) | 3.4.1 | shared `SCORE_BULLET_NEUTRAL_*` | `[0.45, 0.55]` | `(0.44, 0.57)` per-class | TC review / ELO keep | **introduce `PER_CLASS_SCORE_BULLET_ZONES`** |
| Per-class score bullet (minor_piece) | 3.4.1 | shared | `[0.45, 0.55]` | `(0.43, 0.58)` | TC collapse / ELO keep | per-class override |
| Per-class score bullet (pawn) | 3.4.1 | shared | `[0.45, 0.55]` | `(0.42, 0.59)` | TC collapse / ELO review | per-class override |
| Per-class score bullet (queen) | 3.4.1 | shared | `[0.45, 0.55]` | `(0.41, 0.63)` | TC collapse / ELO collapse | per-class override (widest variance) |
| Per-class score bullet (mixed) | 3.4.1 | shared | `[0.45, 0.55]` | `(0.46, 0.56)` | TC review / ELO keep | per-class override (close to global) |
| Per-class score bullet (pawnless) | 3.4.1 | shared | `[0.45, 0.55]` | hold `(0.45, 0.55)` (low sample) | TC collapse / ELO review | **keep** until sample density improves |
| Per-class pawnless Conv/Recov | 3.4.1 | `PER_CLASS_GAUGE_ZONES.pawnless` | conv `(0.70, 0.80)` recov `(0.21, 0.31)` | conv `(0.70, 0.82)` recov `(0.18, 0.28)` | n/a | optional re-center |
| Per-class ΔES gap (rook) | 3.4.2 | `.rook.achievable_score_gap` | `(−0.05, +0.04)` | `(−0.05, +0.04)` | TC review / ELO review | **keep** |
| Per-class ΔES gap (minor_piece) | 3.4.2 | `.minor_piece.achievable_score_gap` | `(−0.04, +0.06)` | `(−0.04, +0.06)` | TC collapse / ELO review | **keep** |
| Per-class ΔES gap (pawn) | 3.4.2 | `.pawn.achievable_score_gap` | `(−0.04, +0.05)` | `(−0.04, +0.05)` | TC review / ELO review | **keep** |
| Per-class ΔES gap (queen) | 3.4.2 | `.queen.achievable_score_gap` | `(−0.05, +0.05)` | `(−0.05, +0.05)` | TC review / ELO review | **keep** |
| Per-class ΔES gap (mixed) | 3.4.2 | `.mixed.achievable_score_gap` | `(−0.03, +0.04)` | `(−0.03, +0.04)` | TC collapse / ELO keep | **keep** |
| Global ΔES gap | 3.4.2 | `endgame_type_achievable_score_gap` | `(−0.04, +0.04)` | `(−0.04, +0.04)` | n/a | **keep** |
| Per-type card layout | 3.4.3 | (`EndgameTypeCard.tsx` chart inventory) | Score + Score Gap + WDL + Conv + Recov | **Drop WDL bar** (mode verdict; queen+mixed footnote) | n/a | layout proposal, not a code constant |

---

*Report generated 2026-05-17 from the benchmark DB. Equal-footing filter (`|opp − user| ≤ 100`) universal across all subchapters. Sparse cell `(2400, classical)` excluded from marginals and Cohen's d throughout.*
