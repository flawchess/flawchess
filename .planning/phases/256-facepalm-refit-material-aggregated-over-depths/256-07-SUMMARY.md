---
phase: 256-facepalm-refit-material-aggregated-over-depths
plan: 07
subsystem: scoring-fit
tags: [facepalm, refit, prod-features, calibration, owner-checkpoint, d-01, d-02, d-07, d-08, d-11, d-13]
requires: ["256-06"]
provides:
  - "reports/blunder-check/facepalm-features-2026-11-16.tsv: facts-schema features of all 290 label rows plus Window 14, pulled from prod"
  - "reports/blunder-check/facepalm-fit-2026-11-16.md: three-input refit on sets 1-8 with the set-8 hold-out and the owner section"
  - "reports/blunder-check/blunder-check-calibration-2026-11-16.md and spot-check-2026-11-16.md: 25 permille prod sample scored with the candidate constants"
  - "Owner decision (D-13): material input decaying_mean (CV choice, no forced flag), loss gate None, FACEPALM_SCORE_MIN = 0.5"
affects: [256-08]
tech-stack:
  added: []
  patterns: []
key-files:
  created:
    - reports/blunder-check/facepalm-features-2026-11-16.tsv
    - reports/blunder-check/facepalm-fit-2026-11-16.md
    - reports/blunder-check/blunder-check-calibration-2026-11-16.md
    - reports/blunder-check/spot-check-2026-11-16.md
  modified: []
key-decisions:
  - "Owner, D-13: input=decaying_mean (cv choice), FACEPALM_SCORE_MIN=0.5"
  - "The D-08 disagreement (depth_3 0.835 vs decaying_mean 0.821 on set 8) was settled for the CV choice: the set-8 gap is within its sampling noise (58 usable rows), the CV gap is about four seed spreads"
requirements-completed: [D-01, D-02, D-07, D-08, D-11, D-13]
duration: ~45 min (inline, orchestrator)
completed: 2026-11-16
status: complete
---

# Phase 256 Plan 07: Real refit on label sets 1-8 Summary

Run inline by the orchestrator from the main checkout on
`gsd/phase-256-facepalm-refit-material-aggregated-over-depths` (plan DISPATCH OVERRIDE). No code
changed; `app/services/blunder_check_rules.py` is unchanged in git.

## Owner decision (Task 3, D-13)

Reply, verbatim: `input=decaying_mean (cv choice), FACEPALM_SCORE_MIN=0.5`

- **Material input:** `decaying_mean`, the cross-validated choice. No forced flag.
- **Loss gate:** `None` (a row loses material when its loss is above 0), as the fit chose (D-11).
- **FACEPALM_SCORE_MIN:** 0.5 (unchanged from the shipped value).
- **Constants come from:** `reports/blunder-check/facepalm-fit-2026-11-16.md`, section "## Constants".
- **Exact fit command** (plan 08's `--check-constants` repeats the same flags, none forced):
  `uv run python scripts/blunder_check/fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-16.tsv --labels reports/blunder-check/facepalm-labels.tsv --out reports/blunder-check/facepalm-fit-2026-11-16.md`
- **D-08 disagreement:** flagged by the report (CV choice decaying_mean, set-8 AUC 0.821; depth_3
  scores 0.835 on set 8). Settled by the owner for the CV choice.
- **Window 14** (game 2099808 ply 23): unscored under the shipped and the candidate model (NULL
  loss input on prod: `line_loss_3 None`), so it stays below the cut.
- **Assumptions A1 and A2:** shown at the checkpoint; the owner raised no objection. A1 does not
  affect the shipped input (it concerns `first_stable` only).

Constants to ship in plan 08:

```python
FACEPALM_INTERCEPT: float = -1.2172
FACEPALM_PLAYED_COEF: float = -0.6083
FACEPALM_SPREAD_COEF: float = -0.3617
FACEPALM_LOSS_COEF: float = 1.1643
FACEPALM_LOSS_FLOOR: int | None = 0
FACEPALM_MATERIAL_FORM: MaterialForm = "split"
FACEPALM_MISSED_COEF: float = 0.3538
FACEPALM_MISSED_FLOOR: int | None = 0
FACEPALM_MISSED_CAP: int = 5
FACEPALM_MISSED_MATE: int = 5
FACEPALM_SPREAD_FORM: SpreadForm = "best_prob_for_misses"
FACEPALM_BEST_PROB_COEF: float = 1.9618
FACEPALM_PRE_SPREAD_COEF: float = 0.0000
FACEPALM_MATERIAL_INPUT: MaterialInput = "decaying_mean"
FACEPALM_LOSS_GATE: float | None = None
```

## Task 1: label gate and rehearsal

- D-01 check: `60 set-8 rows, 0 unlabelled:` (exit 0). The set-8 labels were committed as
  `e4f4c3483` before this plan ran.
- Cell-wise comparison against `2a4549903`: `290 rows compared, 0 unexpected cell changes:` (exit 0).
- Rehearsal fit on `facepalm-features-2026-11-15.tsv` with `--labels`: exit 0; the report has
  "## Material input", "## Owner checks" and a constants block with `FACEPALM_MATERIAL_INPUT` and
  `FACEPALM_LOSS_GATE`.
- `bin/prod_db_tunnel.sh` exists; the tunnel was already open on port 15432.
- Owner-fixture one-liner:

```
uv run python -c "
from tests.services.facepalm_owner_fixtures import OWNER_FIXTURE_FACTS as F; from tests.facepalm_models import PHASE_254_MODEL as M; from app.services.facepalm_score import facepalm_score as s, FACEPALM_MODEL as N; from app.services.blunder_check_rules import FACEPALM_DRILL_LAMBDA as L
for f in F: print(f.game_id, f.ply, 'old', round(s(f.facts,lam=L,model=M),4), 'new', round(s(f.facts,lam=L,model=N),4))"
```

Rehearsal output (shipped constants on both sides):

```
817357 24 old 0.1458 new 0.1458
820181 65 old 0.154 new 0.154
```

## Task 2: prod features, fit, calibration

- **Prod state before the run:** 13 connections, 1 active (this session's query); no other
  operator process.
- **Phase 252 state at the pull (D-02):** plans 252-01 to 252-05 are complete (code, deploy,
  baselines). The prod line repair (252-06) and the re-walk feed and retag (252-07) had not run;
  ROADMAP shows 5/9 plans executed on this branch and on `main`. The 254 D-21 gap-fill line pass
  had not run either. The fit therefore sees the stored lines as they are now, unrepaired
  (research Pitfall 12: features recompute lines from `game_positions.pv`).
- **Features:** `rows 291; pv_source: db 279, db_none 12; cache mismatches 0; rows with a NULL
  score input 21; rows with a NULL best line 25`. 290 label rows (sets 1-8: 20/20/20/20/50/50/50/60)
  plus one `extra` row; nine `played_mat_*` columns. About 2 min 40 s.
- **Fit:** 261 usable rows (136 fair, 125 unfair); 11 undecided, 18 with a NULL loss feature.

| input | CV AUC mean | spread | fair share at 0.7 | set-8 AUC | set-8 fair / unfair at 0.7 |
|---|---|---|---|---|---|
| decaying_mean (chosen) | 0.902 | 0.006 | 0.887 | 0.821 | 9 / 5 |
| first_stable | 0.877 | 0.009 | 0.901 | 0.727 | 6 / 2 |
| depth_3 | 0.879 | 0.008 | 0.881 | 0.835 | 9 / 2 |

  D-05 / D-12 counts: every spread form and gate fits all 261 rows; 0 rows excluded for a NULL
  reply_spread or a NULL best_prob; 0 rows qualify only under a gated form.
- **Owner fixtures with the candidate constants pasted in the working tree:**

```
817357 24 old 0.1458 new 0.0632
820181 65 old 0.154 new 0.1044
```

- **Calibration:** `--db prod --sample-permille 25`, cache `temp/blunder-check/prod-cache-2026-11-16.json`
  (gitignored, version 4). 26,920 games sampled, 22,773 per-user groups, 9,000 Good moves scored.
  Duration about 18 minutes (20:18 to 20:36 UTC).
- `git restore app/services/blunder_check_rules.py` done; `git status --short` on it prints nothing.
- Commit: `a869c5940 docs(256-07): refit features, three-input fit and calibration on label sets 1-8`.

## What the owner saw at the checkpoint

Fair / unfair among passers and the pool, candidate model (shipped model, calibration of
2026-11-15, in brackets):

| cut | labels, out-of-fold | set-8 hold-out | pure-miss pass, prod | "neither" pass, prod | own pool p25 / median |
|---|---|---|---|---|---|
| 0.5 | 109 / 26 | 12 / 11 | 33.0% (26.6%) | 14.3% (8.6%) | 123 / 478 (133 / 508) |
| 0.6 | 106 / 20 | 10 / 9 | 25.8% (16.5%) | 9.4% (3.7%) | 108 / 414 (113 / 434) |
| 0.7 | 88 / 11 | 9 / 5 | 18.9% (7.4%) | 5.5% (0.8%) | 91 / 349 (97 / 368) |
| 0.8 | 77 / 8 | 9 / 5 | 11.7% (1.1%) | 2.8% (0.0%) | 75 / 285 (81 / 302) |

The orchestrator recommended raising the cut to 0.7 (false alarms on set 8 and on "neither" rows);
the owner kept 0.5.

## Deviations from Plan

None. The tunnel was already open, so `bin/prod_db_tunnel.sh` was not started again.

## Notes for plan 08

- Paste the constants block above; `FACEPALM_SCORE_MIN` stays 0.5.
- `--check-constants` runs against `reports/blunder-check/facepalm-features-2026-11-16.tsv` with
  no forced flags.
- Both owner fixtures score lower under the shipped candidate (0.0632 and 0.1044); the tests that
  pin them must read these values, not the Phase 254 ones.
- One unidentified test failed once in the post-merge suite after wave 3 and passed on three
  reruns; not seen again in waves 4 to 6.

## Self-Check: PASSED

- The four reports of 2026-11-16 are committed (`a869c5940`).
- `app/services/blunder_check_rules.py` is unchanged in git.
- The owner's answer is recorded in the resume-signal format.
