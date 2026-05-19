---
created: 2026-05-19T16:05:11.933Z
title: Fix rating-lag selection bias in /benchmarks skill (SQL-only SKILL.md update)
area: skills / benchmarks
files:
  - .claude/skills/benchmarks/SKILL.md (Standard CTE selected_users; §"Sample-shape implications"; subchapters 3.1.3, 3.1.4; §1 before "### Target")
  - reports/opening-end-eval-by-elo-blitz-rapid-classical-2026-05-18.md (symptom only — do NOT re-add the reverted 2026-05-19 addendum)
  - scripts/select_benchmark_users.py (root-cause reference: _rating_bucket(median_elo_in_tc), D-01 no cheat-filtering)
---

## Problem

The /benchmarks skill buckets every game by the player's **March-2026 snapshot-month median rating** (`bsu.rating_bucket`), not the rating they had when the game was played. Each user contributes a 36-month game history, so climbing/improving players' early (underrated) games are filed under their final rating bucket. The equal-footing opponent filter equalizes *rating*, not *strength*, so the cohort systematically outplays its "equal-rated" opponents and the bias grows monotonically with ELO. This distorts absolute zone levels and, critically, the **ELO-axis Cohen's-d collapse verdicts** — the skill's core architectural output.

This is **executable right away without a dedicated phase**: it is a SQL/labeling fix plus documentation in SKILL.md against the **existing** benchmark sample. NO re-ingest, NO re-selection. (Distinct from `2026-04-30-benchmark-rebuild-per-tc-selection.md`, which is a pipeline rebuild — complementary, not a duplicate.)

### Evidence already gathered (benchmark DB, blitz+rapid+classical, 2400 excl. classical)

- Eval-free proof — cohort score vs equal-rated opponents (rating predicts 0.5000): 800→0.496, 1200→0.505, 1600→0.506, 2000→0.523, 2400→0.538 (monotone ramp = the bias). In underrated-climb slices (rating-at-game >150 below selection rating) cohort scores 0.52–0.62.
- Per-color asymmetry symptom: 1200 White +32.8 / Black −15.7 instead of symmetric ±X (reproduces the published opening-end-eval report exactly).
- Confirmed NOT side-to-move (≈50/50 White-to-move, uncorrelated with cohort color) and NOT removable by tightening the opponent window (±100→±50: 0.561→0.561).
- Selection-proximity filter `|rating_at_game − median_elo| ≤ 50` collapses the rating-lag half (800/2400 become symmetric; 1200 midpoint +8.6→+6.5) but leaves a small **winrate-neutral opening-style residual** (+4–6 cp mid-ELO) that is NOT SQL-fixable (it's a selection-membership artifact of the ≥10-analyzed-games eligibility; document, don't re-collect).

### Root cause (verified in SKILL.md)

"Standard CTE — selected_users" selects `bsu.rating_bucket`; "Cells are formed from `(su.rating_bucket, su.tc_bucket)`". `bsu.rating_bucket` = `_rating_bucket(median_elo_in_tc)` in `select_benchmark_users.py` — median Elo scanned from the single 2026-03 dump month, frozen onto all of that user's games. Per-game `games.white_rating`/`black_rating` (rating-at-game-time, already stored) are never used for ELO bucketing.

## Solution

### 1. Rebucket by rating-at-game-time (pure SQL, existing sample)
In the canonical `selected_users` CTE / per-metric projections, replace `su.rating_bucket` as the ELO bucket with a per-game expression: bucket the cohort user's own rating in that game (`games.white_rating` if cohort user is White else `games.black_rating`) using the same 400-wide anchors (800/1200/1600/2000/2400, <800 dropped). 36-month history stays intact; only the `elo_bucket` label changes. Keep `bsu.median_elo` as an additional column so longitudinal/trajectory analysis stays possible (the bias is an aggregation/labeling artifact, not a collection one — full history + per-user rating variance preserved).

### 2. Rework the per-user aggregation model that depends on the old bucketing
Cells become **(user × ELO bucket)** — a user spans 2–3 ELO buckets across their career. Recompute Cohen's-d marginals, the per-user value computation, and re-verify the ≥10-users/cell floor on the new membership; footnote thinner cells / widen per-cell pool guidance if needed.

### 3. Fix two mis-calibrated sanity checks (subchapters 3.1.3 Achievable Score, 3.1.4 Endgame Score)
"pooled mean should sit within ±1 pp of 0.50 (sanity check on equal-footing filter); flag if `|mean−0.50|>0.01`" is wrong at 2000/2400 — rating lag + documented no-cheat-filtering (D-01) leave a legitimate monotone-rising residual there even with the filter correctly applied. Reword: expect ≈0.50 only at 800–1600; treat a monotone 2000/2400 residual as the known bias, NOT a filter failure to be "fixed" by relaxing the filter.

### 4. Repair the already-applied partial edit
A strengthened "Selection vs game-time rating — RATING-LAG SELECTION BIAS" bullet was added to §"Sample-shape implications for downstream queries" but cites a "(2026-05-19 addendum)" in `reports/opening-end-eval-by-elo-blitz-rapid-classical-2026-05-18.md` that **no longer exists** (report was reverted to original 2026-05-18 state). Change the citation to reference the report only as the visible *symptom* (asymmetric per-color split); move the full diagnosis/mitigation/per-analysis-impact into a dedicated SKILL.md subsection.

### 5. Add a dedicated subsection (before "### Target" in chapter 1)
Document: the confound, affected analyses, robust ones, mitigation, acceptance test.

- **Distorted** (absolute level + inflated ELO ramp + ELO Cohen's-d separation): 3.1.1 Non-EG Score, 3.1.3 Achievable Score, 3.1.4 EG Score, 3.2.1 Conversion/Parity/Recovery + composite Endgame Skill, per-endgame-class score/conv/recov, every ELO-axis collapse verdict.
- **Robust / immune** (cite as the template): 2.1 Symmetric baseline (already deduped to physical games — the correct mitigation, already documented); all within-user score-gap differences (level shift cancels in the difference).
- **Behavior change to flag**: any single whole-career per-user scalar (e.g. composite Endgame Skill per user) is no longer one number under game-time bucketing — it becomes per-bucket or a trajectory; the live-UI comparator must absorb this.

### Acceptance test (must pass post-fix)
- Cohort score vs equal-rated opponents flat ≈0.500 across all 5 ELO buckets (no monotone ramp).
- Per-color means are mirror images (±X) at every bucket.

### Out of scope / separate caveat
2000/2400 upward drift is partly cheat contamination (`select_benchmark_users.py` D-01: no cheat-filtering). NOT fixed by rebucketing — keep separate when validating; rely on Phase-70 per-class gate / TOS-ban exclusion as a distinct concern.

### Execution note
SKILL.md is agent-loaded config; the auto-mode permission classifier blocks edits to `.claude/skills/**` ("Self-Modification" soft block) after the first bullet edit landed. Executing this requires the user to grant a permission rule for `.claude/skills/**`, approve interactively, or paste edits manually.
