---
phase: 88-time-pressure-stats-rework
plan: 12
subsystem: benchmarks
tags: [endgame-analytics, time-pressure, pressure-bin-zones, recalibration, sanity-rerun, checkpoint]

status: checkpoint — awaiting user decision
gap_closure: true

requires:
  - phase: 88-08
    provides: PRESSURE_BIN_SCORE_NEUTRAL_ZONES delta-IQR calibration under cohort semantics
  - phase: 88-09
    provides: same-game opp-quintile split (D-07 supersedes D-05); the live frontend now consumes user_score − opp_score, not user_score − cohort_score
provides:
  - reports/benchmarks-latest.md §3.3.3.b — opp-quintile rerun (per-(TC, quintile) delta-IQR table; rerun-derived bands; per-cell comparison vs 88-08; verdict line)
affects:
  - app/services/endgame_zones.py PRESSURE_BIN_SCORE_NEUTRAL_ZONES (no change yet — pending Task 2 decision)
  - frontend/src/generated/endgameZones.ts (no change yet — pending Task 2 decision)

tech-stack:
  added: []
  patterns:
    - "Same-game opp-quintile delta-IQR rerun: union the user-side and opp-side of each filtered game into a single per-(user, tc, quintile, side) bucket, then per-user delta = AVG(user_score) − AVG(opp_score) inside each (tc, quintile) cell. The MIN_GAMES_PER_PRESSURE_BIN=5 gate applies per-side. ELO pooled (Phase 88-08 accept-pooled-with-caveat resolution preserved)."

key-files:
  modified:
    - reports/benchmarks-latest.md

key-decisions:
  - "Rerun confirms VERIFICATION.md line 211 in shape (editorial cap dominates) but contradicts it on the asymmetric-structure point: 6 asymmetric 88-08 cells would all flatten to the ±0.06 cap under the new semantics."
  - "Recommendation pending user verification at the Task 2 decision checkpoint."

requirements-completed: []

duration: ~30min (Task 1 only)
started: 2026-05-17
completed: <pending>
---

# Phase 88.1 Plan 12: Sanity-rerun §3.3.3 under opp-quintile semantics — Summary

> **Status: CHECKPOINT — awaiting user decision.**
> Task 1 (benchmark rerun + report subsection) is complete and committed. Task 2 (keep-as-is vs recalibrate decision) is `checkpoint:decision`. Task 3 (conditional retune) has not run. STATE.md and ROADMAP.md are intentionally not updated.

## What Task 1 did

Ran the `/benchmarks` §3.3.3 chess-score-per-pressure-bin query against the benchmark DB (snapshot 2026-05-01, 1912 users), but with the **opp-quintile semantics** the live `/api/endgames/overview` route now ships (Plan 88-09, D-07 supersedes D-05):

- For each filtered game, derive both `user_clk_pct` (user's clock at endgame entry / base_clock) and `opp_clk_pct` (the same for the opponent's clock from the same ply).
- Bucket the user side into quintile = `LEAST(4, FLOOR(user_clk_pct/20))` and the opp side into quintile = `LEAST(4, FLOOR(opp_clk_pct/20))`. The same game contributes one row to a (tc, user_quintile, side='user') cell and one row to a (tc, opp_quintile, side='opp') cell — usually different quintiles within the same game. Opp's score is `1 - user_score` (mapped from the inverted result).
- Per user per (tc, quintile): `user_mean_score` = AVG(score | side='user'), `opp_mean_score` = AVG(score | side='opp'). Require `n_user >= 5` AND `n_opp >= 5` (MIN_GAMES_PER_PRESSURE_BIN per side).
- Per user per (tc, quintile): `delta = user_mean_score − opp_mean_score`.
- Per (tc, quintile): p25 / p50 / p75 of those per-user deltas (ELO pooled, sparse cell `(2400, classical)` excluded).

Applied the 88-08 delta-IQR transform to the rerun: `lower = max(p25-p50, -0.06)`, `upper = min(p75-p50, +0.06)`.

Appended a new subsection `§3.3.3.b chess-score-per-pressure-bin — opp-quintile rerun (Phase 88.1 / 2026-05-17)` to `reports/benchmarks-latest.md`, below (not replacing) the existing 2026-05-17 §3.3.3 table.

## Comparison: shipped 88-08 vs rerun (after delta-IQR transform)

Both sides have already had the editorial cap applied. Flag = `|Δ| ≥ 0.02` on either bound.

| tc | q | rerun_lower | rerun_upper | shipped_lower | shipped_upper | Δlower | Δupper | flag |
|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| bullet | 0 | -0.06 | 0.06 | -0.06   | 0.06   |  0.0000 |  0.0000 | |
| bullet | 1 | -0.06 | 0.06 | -0.0481 | 0.0524 | -0.0119 |  0.0076 | |
| bullet | 2 | -0.06 | 0.06 | -0.0380 | 0.0493 | -0.0220 |  0.0107 | **YES** |
| bullet | 3 | -0.06 | 0.06 | -0.0563 | 0.06   | -0.0037 |  0.0000 | |
| bullet | 4 | -0.06 | 0.06 | -0.06   | 0.06   |  0.0000 |  0.0000 | |
| blitz  | 0 | -0.06 | 0.06 | -0.06   | 0.06   |  0.0000 |  0.0000 | |
| blitz  | 1 | -0.06 | 0.06 | -0.0579 | 0.06   | -0.0021 |  0.0000 | |
| blitz  | 2 | -0.06 | 0.06 | -0.0557 | 0.0530 | -0.0043 |  0.0070 | |
| blitz  | 3 | -0.06 | 0.06 | -0.0598 | 0.0548 | -0.0002 |  0.0052 | |
| blitz  | 4 | -0.06 | 0.06 | -0.06   | 0.06   |  0.0000 |  0.0000 | |
| rapid  | 0 | -0.06 | 0.06 | -0.06   | 0.06   |  0.0000 |  0.0000 | |
| rapid  | 1 | -0.06 | 0.06 | -0.06   | 0.06   |  0.0000 |  0.0000 | |
| rapid  | 2 | -0.06 | 0.06 | -0.0563 | 0.06   | -0.0037 |  0.0000 | |
| rapid  | 3 | -0.06 | 0.06 | -0.0582 | 0.06   | -0.0018 |  0.0000 | |
| rapid  | 4 | -0.06 | 0.06 | -0.06   | 0.06   |  0.0000 |  0.0000 | |
| classical | 0-4 | -0.06 | 0.06 | -0.06 | 0.06 | 0.0000 | 0.0000 | |

**Summary.**
- 14 of 20 cells: zero change (already capped on both edges in 88-08; still capped under the rerun).
- 6 of 20 cells (bullet Q1-Q3, blitz Q1-Q3): partially uncapped in 88-08, fully capped under rerun. Each widens by 0.0–0.024 per edge.
- 1 cell flagged (bullet/Q2): Δlower = -0.0220 — the lower edge would widen by ~22pp on the score-delta scale. The upper edge widens by 11pp.
- Raw delta-IQR widths under opp-quintile semantics are ~2× wider than under cohort semantics (most p75−p25 widths are 0.16–0.20 vs 0.08–0.12 in 88-08). The ±0.06 editorial cap is the *only* thing that defines the bands under the new semantics.

## Verdict & recommendation

VERIFICATION.md line 211 (user, 2026-05-17): *"the editorial cap (±0.06) and asymmetric structure will look very similar."*

- **Editorial cap.** Confirmed. 14/20 cells unchanged; the cap dominates the entire grid.
- **Asymmetric structure.** Refuted. The 6 partially-uncapped cells in 88-08 (asymmetric: one edge narrower than ±0.06) would all flatten to symmetric ±0.06 under the rerun. The "asymmetric shape" was an artefact of the cohort-version IQR being narrower; under opp-quintile semantics there is no asymmetry left.

**Recommendation: `keep-as-is` (with one judgment cell flagged).**

Reasoning:
1. Functionally, only 6 cells differ, all in bullet/blitz mid-quintiles. The maximum per-edge difference is ~0.024 (bullet/Q2 lower edge). At the consumer call site (`endgameZoneFor` → tile shading on the user's `delta = user_score − opp_score`), this is the difference between "the band's lower edge sits at -0.038 vs -0.060". For a user whose delta lands at, say, -0.05, that flips the tile from "weak/red" (under 88-08) to "neutral" (under rerun) in those 6 cells.
2. Whether that flip is desirable is the editorial call. Under the new semantics, the data actually supports the more permissive ±0.06 cap (the raw IQR is wide), so a recalibration is *statistically* justified.
3. Against that: the 88-08 narrower bands paint more deltas as non-neutral, which is product-louder. If we want the time-pressure tile coloring to remain product-loud in bullet/blitz Q1-Q3, keep-as-is is the right call. If we want the bands to reflect the actual variance of the new delta, recalibrate.
4. Edge case worth surfacing for the user: bullet/Q2 is the one cell where |Δ| crosses the 0.02 flag threshold. The lower edge widens from -0.038 to -0.060 (a 0.022 widening). If the user wants a "minimal-touch" recalibration, this is the cell to retune.

### Options for the Task 2 decision

- **`keep`** — ship gap closure with no code change to `endgame_zones.py` / `endgameZones.ts`. The §3.3.3.b sanity report is on file; future readers see both the cohort version and the opp-quintile rerun. This is the recommended path.
- **`recalibrate selective`** — update only flagged cells. Under |Δ|≥0.02, that's just bullet/Q2: `PressureBinBand(-0.0380, 0.0493)` → `PressureBinBand(-0.06, 0.06)`. The grid becomes 15/20 fully capped (one more than today).
- **`recalibrate all`** — flatten all 20 cells to `PressureBinBand(-0.06, 0.06)`. Structurally identical to the original Plan 88-08 placeholder shape, but the comments would cite §3.3.3.b. This removes all asymmetric calibration.

## Deviations from Plan

None. Task 1 executed exactly as specified. Task 2 / Task 3 are pending the checkpoint.

## Issues Encountered

- The MCP tool `mcp__flawchess-benchmark-db__query` is not exposed in the worktree agent's tool surface (consistent with the 88-08 SUMMARY note about #3098). Ran the rerun query via `docker compose ... exec -T db psql` against the `flawchess_benchmark` superuser instead. The query is read-only; results are identical to what the MCP wrapper would have returned.

## Self-Check (Task 1 only)

- [x] `e32a2e26` exists: Task 1 §3.3.3.b rerun committed
- [x] `grep -c "opp-quintile rerun" reports/benchmarks-latest.md` returns 1
- [x] `grep -c "§3.3.3.b" reports/benchmarks-latest.md` returns 1
- [x] `grep -c "^\*\*Verdict\.\*\*" reports/benchmarks-latest.md` returns 1
- [x] No changes to `app/services/endgame_zones.py` (verified via `git diff HEAD~1`)
- [x] No changes to `frontend/src/generated/endgameZones.ts`
- [x] No changes to `.planning/STATE.md` or `.planning/ROADMAP.md`

## Self-Check: PASSED (Task 1)

Task 2 and Task 3 will produce their own self-check entries after the user's decision.

---
*Phase: 88-time-pressure-stats-rework (Phase 88.1 gap closure)*
*Status: checkpoint — awaiting user decision on `keep` vs `recalibrate`*
*Task 1 completed: 2026-05-17*
