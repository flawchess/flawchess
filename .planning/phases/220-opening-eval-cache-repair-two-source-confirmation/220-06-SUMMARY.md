---
phase: 220-opening-eval-cache-repair-two-source-confirmation
plan: 06
subsystem: database
tags: [opening-cache-repair, production, stockfish, acceptance, legacy-cohort]

# Dependency graph
requires:
  - phase: 220-05
    provides: Release 1 deployed to production (2ad90ce97), audit tables live, pipeline smoke-tested on dev
provides:
  - "The full repair pipeline run against production: 2,567,943 cache rows seeded, 4,097 confirmed_bad and repaired, 352,058 orphans deleted, 11,286 carrier cells rewritten, 13,197 games reclassified"
  - "Committed prod report reports/opening-cache-repair/opening-cache-repair-2026-09-11.md with the D-07 decision block appended"
  - "All 14 CACHEFIX-11 acceptance queries evidenced below; the primary histogram-vs-control signal converged in every band"
  - "LEGACY-COHORT-DECISION: NO BUILD (CACHEFIX-10 / D-07) with both rates, both denominators and the ply-20 split recorded"
  - "Measured prod confirm_floor for plan 07"
affects: [220-07, 220-08]

# Actuals
actuals:
  tokens: 0
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Every hash-list predicate against a prod-scale table is chunked (10k) under asyncpg's 32,767 bind-parameter cap; the dev smoke never reaches the cap, so prod is the first place it can bite"

key-files:
  created:
    - reports/opening-cache-repair/opening-cache-repair-2026-09-11.md
  modified:
    - scripts/opening_cache_repair.py
    - .claude/skills/db-report/SKILL.md

key-decisions:
  - "The 17 still-pending rows WITH a carrier were left pending, not re-walked: 14 are checkmate terminal positions inside 20 plies (the drain helper excludes game-over terminals by design, so no eval is ever read for them) and 3 are games imported after the walk cursor (2464845) that picked up a previously pending hash. None is a cut-short walk."
  - "The 163 rederive failures (all `GameNotAnalyzed: insufficient eval coverage`) are left as-is: 158 are games whose full-eval drain has not completed (`full_evals_completed_at IS NULL`), which the drain's own classifier will reclassify on completion; 4 are engine-complete games with eval holes below the classifier's minimum coverage; 1 is a lichess-eval game. No other error string appeared."
  - "The opening bounce 'band' rate is reported over ALL checked rows (the convention the seed's 0.235% / 0.298% baselines were measured with); the report writer and db-report Query 13 divided by the band's own drops and were fixed, and the committed report's line was hand-corrected with a provenance note."
  - "Legacy cohort: NO BUILD. `screen --legacy-cohort` is not proposed as a follow-up; the numbers are recorded below whichever way a future re-audit wants to read them."

patterns-established:
  - "Prod stage throughput: screen 2.57M rows in 10h48m (pool 28 over the tunnel); confirm 23,673 flagged rows at 1M nodes in 53 min at pool 28; propagate 4,097 hashes / 11,286 cells in 7 min; rederive 13,360 games in 1h21m (~165 games/min); legacy-sample 250 games x all plies at depth 15 in ~6 min at pool 6"

requirements-completed: [CACHEFIX-10, CACHEFIX-11]

coverage:
  - id: P1
    description: "Every stage finished on prod in order; the audit table has 0 orphan candidates and 0 flagged/confirmed_bad rows left; opening_cache_repair_games has 0 pending"
    requirement: CACHEFIX-11
    verification:
      - kind: other
        ref: "opening_cache_repair_progress: all seven tracked *_finished_at stamps set (seed 11:37Z 09-10 ... rederive 13:15Z 09-11, report 13:15Z, legacy_sample 13:23Z); repair-games status: reclassified 13,197 / failed 163 / pending 0"
        status: pass
    human_judgment: false
  - id: P2
    description: "Primary acceptance signal: the residual delta histogram matches the lichess-internal IQR control in every band above the noise floor"
    requirement: CACHEFIX-11
    verification:
      - kind: other
        ref: "Q8 below: 150-250cp 50->14 (ctrl 20), 250-400cp 35->2 (ctrl 6), >400 4->4 (all four individually explained under Q9)"
        status: pass
    human_judgment: false
  - id: P3
    description: "Legacy cohort measured with the pre-committed D-07 rule"
    requirement: CACHEFIX-10
    verification:
      - kind: other
        ref: "LEGACY-COHORT-DECISION: NO BUILD; legacy 965/9,164 = 10.53% vs control 176/1,949 = 9.03% beyond ply 20; ratio 1.17 < 2.0"
        status: pass
    human_judgment: true

# Metrics
duration: ~26h wall clock across two days (seed 2026-09-10 11:36Z to legacy-sample 2026-09-11 13:23Z), of which ~14h engine time
completed: 2026-09-11
status: complete
---

# Phase 220 Plan 06: Production repair run, acceptance queries, legacy-cohort decision

**Measured prod calibration (plan 07's source): `confirm_floor = 0.029419322`, `screen_floor = 0.041077532`, `calibration_n = 500`, calibrated 2026-09-10 11:47:37Z, Stockfish 18.**

## Stage transcript (times UTC)

| Stage | Started | Finished | Result |
|---|---|---|---|
| seed | 09-10 11:36:17 | 09-10 11:37:16 | 2,567,943 audit rows `pending` |
| calibrate | 09-10 11:47:37 | 09-10 11:47:37 | n=500, screen_floor 0.0411, confirm_floor 0.0294 |
| screen | 09-10 11:48:03 | 09-10 22:36:03 | cursor 2,464,845; screened_clean 2,192,195 / flagged 23,673 / pending 352,075 |
| orphans (dry-run) | 09-11 ~11:20 | | first run died: `the number of query arguments cannot exceed 32767` (352k hashes in one `IN`); fixed in `36e05d890` and re-run |
| orphans | 09-11 ~11:40 | | 352,058 orphans deleted (no carrier at ply 1-20 in any game); 17 pending WITH a carrier left (see decisions) |
| confirm | 09-11 05:29:05 | 09-11 06:21:48 | 4,097 `confirmed_bad`, 19,576 `confirmed_clean` (confirm ran before orphans; it gates on screen only, and orphans does not affect it) |
| propagate (dry-run) | 09-11 ~11:45 | | 4,097 unpropagated; magnitude cross-checked by SQL: 11,286 carrier cells across 10,071 games still held the exact old value, 3,845 of 4,097 hashes had at least one (lower bound from the seed: 4,361 games for the 85 lichess-detectable values) |
| propagate | 09-11 11:47:05 | 09-11 11:54:09 | 4,097 `repaired`, 11,286 `opening_cache_repair_rows`, 13,360 games queued (best_move/pv rewrites touch games beyond the 10,071) |
| rederive | 09-11 11:54:43 | 09-11 13:15:35 | reclassified 13,197 / failed 163 / pending 0 |
| report | 09-11 13:15:51 | 09-11 13:16:31 | `reports/opening-cache-repair/opening-cache-repair-2026-09-11.md` |
| legacy-sample | 09-11 13:17:23 | 09-11 13:23:36 | `LEGACY-COHORT-DECISION: NO BUILD`, appended to the report |

Stage 1 (`seed`, `calibrate`, `screen`) and `confirm` were run by the operator from a terminal; `orphans`, `propagate` and `rederive` were run by the operator on the agent's instruction (the auto-mode classifier refuses prod writes from the session); `report` and `legacy-sample` ran from the session (`legacy-sample` as a `setsid nohup` process with a Monitor).

### Rederive failures (163, one distinct error string)

`GameNotAnalyzed: insufficient eval coverage` x 163. Breakdown by game state: 158 with `full_evals_completed_at IS NULL` (drain not finished, ids up to 2,463,577), 4 engine-complete with eval holes, 1 lichess-eval game. No other error string.

### Flaw-level outcome (from the report §5)

Blunders 67,339 -> 60,741 (7,191 spurious flaws removed, 590 added), mistakes 38,686 -> 38,683, 4,079 games with a changed blunder count, mean accuracy +0.725, mean ACPL -2.57, 5 drill items pruned, 2 herring-pool rows touched. 284 users had at least one affected game (top: user 95 with 917, user 11 with 810).

## The 14 CACHEFIX-11 acceptance queries

### Q1 — cache row repaired
`SELECT eval_cp, best_move FROM opening_position_eval WHERE full_hash = -3185735734450884963;` -> `10, e2e3`. **PASS** (expect ≈ +9 / e2e3).

### Q2 — audit status
`SELECT status, old_cp, full_cp, delta_score ...` -> `repaired, 305, 10, 0.2453`. **PASS**.

### Q3 — discovery game evals
`game_positions` game 2356581 plies 4/5/6 -> `9, 10, 12`. **PASS** (plies 4 and 6 unchanged; ply 5 was 305).

### Q4 — discovery game flaws
`game_flaws` game 2356581 -> one row: ply 21, severity 2, lucky/miss/squandered false/false/false. **PASS** (no ply 5/6 rows; ply-21 blunder survived).

### Q5 — oracle counts
`white_blunders=0, black_blunders=1, white_accuracy=93.0643, white_acpl=19`. **PASS** (was 1 / 2).

### Q6 — carriers cleared
Carriers of 305 at hash -3185735734450884963 -> `0`. **PASS** (baseline 226).

### Q7 — the nine named hashes
All nine (`3250950765068847520, -1357424544074167494, 3912952322572315143, -4495720059219567338, -3692655065124884866, 6991966663941067682, -4230257548248121256, -7106566961782875842, -3185735734450884963`) -> `repaired`. **PASS**.

### Q8 — PRIMARY: residual histogram vs lichess-internal IQR control

| abs(delta) band | after n_cache | after n_ctrl | before n_cache | before n_ctrl |
|---|---|---|---|---|
| < 25 | 22,193 | 24,156 | 21,987 | 24,000 |
| 25-50 | 3,107 | 1,143 | 3,064 | 1,132 |
| 50-75 | 207 | 182 | 203 | 183 |
| 75-100 | 47 | 65 | 52 | 66 |
| 100-150 | 36 | 38 | 49 | 37 |
| 150-250 | 14 | 20 | 50 | 20 |
| 250-400 | 2 | 6 | 35 | 6 |
| > 400 | 4 | 0 | 4 | 0 |

**PASS.** 150-250 and 250-400 converged to below the control; 100-150 went from 49 vs 37 to 36 vs 38. The 25-50 excess is the known 1M-node-vs-lichess-cloud systematic offset (seed §Blast radius), unchanged. The four > 400 rows are the top four residuals in Q9, each a `screened_clean` depth disagreement.

### Q9 — lichess cross-check
`n_checked = 25,610, n_bad = 19` (baseline 25,444 / 87). **PASS with each residual explained.** Every residual was re-evaluated on a hash-asserted board during `screen` (depth 15) and reproduced the cached value; none was a misaligned write. Columns: ply, SAN into the position, lichess games n, lichess median, cache cp, screen cp, audit status.

| # | full_hash | ply | SAN | n | lichess med | cache | screen | status | Explanation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -4639909347211013503 | 12 | Kh1 | 3 | -1217 | -485 | -463 | screened_clean | Already lost for White (Qxf2-type collapse); depth disagreement on how fast it ends; both ≈ 0 expected score |
| 2 | -2215275624244327441 | 5 | Be7 | 12 | 887 | 442 | 420 | screened_clean | Qxh8 rook-in-the-corner grab after ...Be7; lichess cloud (deeper) sees the full material haul |
| 3 | 4032502771626528110 | 11 | Bg7 | 6 | 900 | 478 | 511 | screened_clean | Same Qxh8 family (pv `d7d5 h8g8`); same depth effect |
| 4 | -473218139384267232 | 7 | Bc5 | 5 | 976 | 565 | 551 | screened_clean | Rook-grab trap line (pv `e8f8 ... h8h7`); depth |
| 5 | 8783630112179301152 | 10 | Nxd8 | 3 | 755 | 359 | 342 | screened_clean | Queen trade-down after a piece win; depth on the follow-up |
| 6 | -8915570946090691922 | 12 | Qxa8 | 3 | 600 | 308 | 304 | screened_clean | The seed's own example: Qf3xa8 rook grab, +300 at 1M nodes vs +500/600 cloud |
| 7 | 738741505411020697 | 11 | Qxe4+ | 3 | -770 | -522 | -527 | screened_clean | Black already winning a piece with check; depth on conversion |
| 8 | -5717788197687902180 | 12 | Nb5 | 4 | 612 | 369 | 382 | screened_clean | Nb5 fork threat in a trap line; depth |
| 9 | 4069217099007822612 | 10 | Nc3 | 8 | 498 | 289 | 280 | screened_clean | pv `d1f3 ... f3a8`: another Qxa8 grab; depth |
| 10 | 189257114834417253 | 6 | Ke2 | 4 | -631 | -423 | -410 | screened_clean | King walk after an early Qh4 attack; depth |
| 11 | -8227916192101226681 | 12 | Nd5 | 3 | 555 | 360 | 379 | screened_clean | Same game family as #13 (sample game 1214967); depth |
| 12 | -7473483678694444301 | 11 | Nxe4 | 4 | -448 | -259 | -247 | screened_clean | Fried-liver-style ...Nxe4 / ...Bxf2+ line; depth |
| 13 | 2109195260532564357 | 11 | Bg6 | 3 | 546 | 360 | 355 | screened_clean | Same game as #11; depth |
| 14 | -9053721415056630353 | 11 | Nc6 | 5 | 504 | 319 | 298 | screened_clean | pv `a7a6 f3a8`: Qxa8 grab again, same game as #6 (1063597); depth |
| 15 | 4506398023894081584 | 10 | Bxb5 | 3 | 422 | 253 | 256 | screened_clean | Piece-up after a pawn-grab miscue; depth |
| 16 | -4865912886671691353 | 12 | Qe2+ | 3 | -392 | -224 | -227 | screened_clean | Check-and-win-material line; depth |
| 17 | -6851391846893241766 | 9 | Be7 | 9 | 651 | 491 | 458 | screened_clean | Qxh8 family, same game as #3 (755869); depth |
| 18 | -9157663420186175472 | 8 | O-O | 3 | 527 | 372 | 353 | screened_clean | pv `f3h4 ... c3d4`: piece-winning tactic; depth |
| 19 | 8843396510889171800 | 10 | Kf1 | 5 | 302 | 147 | 212 (full 162) | confirmed_clean | Flagged by screen, re-evaluated at 1M nodes -> 162, within confirm_floor of the cached 147; lichess median 302 is the deeper view |

Shared property: every residual is a large-magnitude tactical position (|lichess median| ≥ 302) where the expected-score delta between the two engine views is small (both sides of the disagreement are "clearly winning"); the delta_score against the fresh depth-15 eval was ≤ 0.0154 for all 18 `screened_clean` rows, well under `screen_floor` 0.0411. Residuals 2/3/17, 6/14 and 11/13 come from the same three games.

### Q10 — opening bounce rate (coarse)
Any bounce 0.62% (62,404 / 10,075,456); 250-360cp band 0.22% (22,569 / 10,075,456; 124,323 drops in band). Baselines: benchmark DB (cache-free) 0.618% / 0.235%; prod legacy 0.798% / 0.298%; mid 0.625% / 0.243%; recent 0.844% / 0.271%. **PASS** (not above legacy; matches the cache-free floor). Denominator note: the report writer divided the band count by the band's own drops (18.15%) while every recorded baseline is over all checked rows; both the writer and db-report Query 13 were fixed in this plan's commit and the committed report line was hand-corrected with a provenance note.

### Q11 — benchmark DB baseline
`SELECT count(*) FROM opening_position_eval;` on `localhost:5433` before Release 1: **0** (recorded in 220-02-SUMMARY, 2026-09-09). **PASS**.

### Q12 — benchmark lane gains dedup
Same query 2026-09-11 13:20Z: **9,681** rows. **PASS** (the submit-path cache write fires).

### Q13 — no benchmark re-clone / gen_benchmarks
Operator attestation: none. `git log --oneline -30 -- reports/benchmark/` last touches 2026-08-18 (`ff52867b2`); no commit since 2026-09-08 mentions benchmarks or gen_benchmarks. **PASS**.

### Q14 — changelog
The user-facing bullet is `CHANGELOG.md:12` under `## [Unreleased]` / `### Fixed` ("Some opening moves in older games ... were marked as blunders because a shared cache ..."). `git diff origin/production -- CHANGELOG.md` is empty because Release 1 (`2ad90ce97`) already carried it to production. **PASS**.

## CACHEFIX-10 legacy-cohort decision (D-07)

```
legacy-sample: D-07 decision
- legacy cohort: 200 games, 3862 rows ply<=20 (17 disagree), 9164 rows ply>20 (965 disagree, 10.53%)
- control cohort: 50 games, 930 rows ply<=20 (6 disagree), 1949 rows ply>20 (176 disagree, 9.03%)
- rule: build only when legacy_rate_ply_gt_20 > LEGACY_BUILD_RATIO * control_rate_ply_gt_20 AND (legacy_rate - control_rate) >= LEGACY_BUILD_MIN_EXCESS_PP
LEGACY-COHORT-DECISION: NO BUILD
```

Ratio 10.53 / 9.03 = 1.17 (rule needs > 2.0); excess 1.50pp (rule needs ≥ 1.0, satisfied on its own). Beyond ply 20 both cohorts disagree with a depth-15 re-eval at roughly one row in ten, which is the depth-15-vs-1M-node noise floor in middlegame positions, not a legacy-specific poison signal. Below ply 20 the rates are 0.44% (17/3,862) legacy vs 0.65% (6/930) control. `screen --legacy-cohort` is **not** built and is not proposed as a follow-up phase.

## Defects found on prod (fixed in this plan)

1. **`orphans` exceeded asyncpg's 32,767 bind-parameter cap** (`36e05d890`). The stage put every still-pending hash into one `IN (...)`; prod had 352,075 of them. The carrier lookup, the status update and the cache delete are now chunked at 10,000 hashes. The dev smoke's 24,029 orphans were under the cap, which is why it never showed.
2. **Bounce band-rate denominator** (this plan's second commit). Report writer and db-report Query 13 now divide by all checked rows, matching the recorded baselines.

## Deviations from the plan

- `orphans` was skipped before `confirm` (the plan's Task 2 precondition names an `orphans_finished_at` column that does not exist; `orphans` is stampless by design). `confirm` gates on `screen_finished_at` only, so the order did not affect any result; `orphans` was run before `propagate`, and the report shows `pending, no carrier = 0`.
- The plan says the `propagate --dry-run` reports the matched `game_positions` count; it only reports the unpropagated audit count. The magnitude check was done with a direct SQL replica of the propagate predicate (11,286 rows / 10,071 games / 3,845 hashes) before running the write.
- `report` was regenerated once after `36e05d890`; the file's `Script revision` reads `36e05d890`, and the band-rate line was hand-corrected as noted.

## Follow-ups (not built here)

- 163 `failed` repair-games rows remain as a trail; 158 will be reclassified by the drain on eval completion. A later re-audit could re-run `rederive` for the 4 engine-complete games with holes, or leave them: their surviving flaws were never touched.
- Plan 07 takes `confirm_floor = 0.029419322` (`calibration_n = 500`).
