# Phase 88: Time Pressure stats rework with hypothesis tests + CIs — Context

**Gathered:** 2026-05-17
**Status:** Ready for planning
**Source:** Captured from `/gsd-explore` thread on 2026-05-14 (`.planning/notes/time-pressure-stats-rework.md`) plus a 2-area discussion on 2026-05-17. Most macro decisions were already locked by the design note; this discussion resolved sparse-bin rendering and band-width policy.

<domain>
## Phase Boundary

Replace two table/chart surfaces on the Endgames page with one per-TC bullet-stack card (bullet / blitz / rapid / classical) that mirrors the v1.17 single-bullet doctrine:

1. Remove `frontend/src/components/charts/EndgameClockPressureSection.tsx` (Time Pressure at Endgame Entry table).
2. Remove `frontend/src/components/charts/EndgameTimePressureSection.tsx` (Time Pressure vs Performance line chart).

Render in their place a 4-column-on-`xl` / 2-col-on-`lg` / 1-col-below card grid. Each TC card stacks **1 Clock Gap bullet** at top + **5 Score-Delta bullets** (one per 20% pressure quintile of base-clock remaining at endgame entry):

- **Clock Gap** — metric `mean((my_clock − opp_clock) / base_clock)` at endgame entry. Centred on 0% (matched pace). Wilson-style CI. Color zone from benchmark global distribution (expected single global zone per /benchmarks collapse verdict).
- **Score-Delta per quintile** — metric `user_score − cohort_score` where `cohort_score` is the median of per-user scores in the matching mirror-bucket `(rating × TC × color × opponent-type)`. Centred on 0. Wilson CI on `user_score`, cohort N treated as fixed reference. Color zone from per-bin cohort IQR.

In scope: `/benchmarks` skill update (new metric-with-sub-bins pattern), backend math helper (`compute_score_delta_vs_reference`), backend service wiring on `/api/endgames/clock-pressure` + `/api/endgames/time-pressure` (or successor route), frontend types, per-TC card component, section orchestrator, popovers, sig-gating, tests, legacy deletion + knip clean.

Out of phase scope: LLM narration of time pressure (future phase), per-move pressure analysis (current scope is endgame-entry snapshot only), time management on the Openings page, increment-aware base-clock normalization beyond `initial time only` (benchmark data shows this collapses cleanly).

</domain>

<decisions>
## Implementation Decisions

### Sparse pressure-bin rendering (D-01 — LOCKED)

Per-bin gating uses two thresholds, with the lower one only hiding (not dimming):

- **`0 < n < MIN_GAMES_PER_PRESSURE_BIN`** (proposed 5; planner confirms with prod-DB sanity check): render the Score-Delta bullet at `UNRELIABLE_OPACITY` (reuse the constant already in `frontend/src/lib/theme.ts` used by `EndgameTypeCard`). Triple-gate font coloring (`n ≥ threshold ∧ p < 0.05 ∧ outside neutral band`) does **not** fire on dimmed bullets — `n < threshold` short-circuits the gate. Sample count chip (`n=X`) appears inline.
- **`n = 0`**: keep the row slot reserved. Render the axis tick + label (`0–20%` etc.) and a dash + "no games" inline. No bullet glyph. This guarantees identical card height across the 4-TC grid, preserving visual rhythm.
- TC-level card hide: separate threshold `MIN_GAMES_PER_TC_CARD` (proposed 20) — when total user games for this TC fall below it, the entire card is hidden (matches Phase 87 per-type card gating pattern). This is **not** discussed gray area; carried forward from design note.

Card heights are equal across the grid by construction at any reasonable user-game distribution.

### Score-Delta color-zone band (D-02 — LOCKED)

Per-bin cohort IQR with one editorial cap. **Band is per `(TC, quintile)` — ELO is pooled.**

- **Per `(TC, quintile)`**: each of the 5 pressure quintiles gets its own neutral band derived from the inter-user distribution of `user_score` in the matching `(TC, quintile)` cohort, pooled across ELO. Band edges = Q1 / Q3 of per-user scores in that cell. 20 band entries total (4 TCs × 5 quintiles), not 100.
- **Why pool ELO**: `reports/benchmarks-latest.md` §3.3.2 already shows ELO collapse for this metric (d=0.17, ELO marginal). Faceting the band by ELO would propagate small-N noise without adding signal. The new per-user IQR skill output should reconfirm the collapse verdict per quintile before the band ships per `(TC, quintile)` — if any quintile fails to collapse (Cohen's d above the skill's threshold across ELO), the planner promotes that quintile's band to `(TC, ELO, quintile)` faceting. Default is pool ELO.
- **Editorial cap**: cap the band half-width at an editorial maximum (planner picks; suggested ±6 score points) so extreme-quintile cohort noise (small per-user N → wide IQR) doesn't widen the band into uselessness. The cap rarely fires in middle quintiles; it activates mainly at tb=0 / tb=9 where cohort scores legitimately spread.
- **Why per-bin**: per `feedback_zone_band_judgement.md`, blindly applying IQR can swallow small but real effects. The cap is the protective half. The expectation from `reports/benchmarks-latest.md` §3.3.2 is that low-time-remaining bins (high pressure) will have **tighter** cohort IQRs because performance is compressed near a forced-loss outcome — a hypothesis the new skill output verifies directly.
- The band uses the cohort score's per-user IQR (inter-user spread of `user_score` per cell), NOT per-game score spread. This is a new shape vs prior /benchmarks metrics.
- **Distinct from the cohort reference line**: the delta is centred on `cohort_score`, which is a mirror-bucket lookup against `(rating × TC × quintile × color × opponent-type)` and comes from the live API (same pattern as Phases 85–87 — not from benchmark precomputation). The band (this decision) and the centre line (live mirror-bucket) are separate concerns.

### `/benchmarks` skill update (D-03 — LOCKED, in-scope per design note)

Two new metrics in `.claude/skills/benchmarks/SKILL.md`:

1. **`clock-gap-%`** — distribution of `(my_clock − opp_clock at endgame entry) / base_clock` per `(TC, ELO)`. User-level metric, then aggregated across users. Expected to collapse to a single global zone band (confirm via Cohen's d collapse verdict). Single dimension — fits the existing skill pattern.
2. **`chess-score-per-pressure-bin`** — new "metric-with-sub-bins" shape. Per-user score per `(TC × ELO × pressure_quintile)` cell **for the collapse-verdict computation**. **Cohen's d collapse verdict runs per pressure bin separately** (not across the whole metric) — cohort spread shifts with pressure, so a global verdict would average away the signal at extreme quintiles. **Shipped band output is per `(TC, quintile)` with ELO pooled** (default, expected) — only quintiles that fail the collapse verdict across ELO get promoted to `(TC, ELO, quintile)` faceting. Output must include per-`(TC, quintile)` Q1/Q3 (for the IQR band). The `cohort_score` reference line is NOT in this output — it comes from live API mirror-bucket lookup, not benchmark precomputation.

Three practical implications the planner must resolve:

- The current `reports/benchmarks-latest.md` §3.3.2 has **10 time-buckets (deciles)**, not 5 quintiles. The skill update can either emit 5-bucket data directly (matching the card design) or emit 10 and collapse pairwise at the consumer. Either is acceptable; planner picks based on benchmark-script complexity vs frontend constant clarity. Recommendation: emit 5 directly so the generated `frontend/src/generated/endgameZones.ts` (or sibling) carries 5 entries per cell, not 10.
- The current report shows only aggregate score per cell, not the per-user inter-user distribution. The new metric shape requires per-user metric → per-cell distribution → per-cell IQR. This is the bulk of the skill change.
- Collapse-verdict computation needs the full `(TC × ELO × quintile)` grid as intermediate data; the **shipped** band constants are `(TC × quintile)` after collapse confirms. Planner picks whether the intermediate grid is also surfaced in the report (for auditability) or only as an internal step.

### Statistical foundation (D-04 — carried forward from design note)

- **Clock Gap**: per-game paired diff `(my − opp)/base_clock`, one-sample test against 0%. Reuse `compute_paired_difference_test` from Phase 85.1 (test choice — z vs Wilcoxon — is a planner/researcher decision based on distribution shape, not a vision decision).
- **Score-Delta**: new helper `compute_score_delta_vs_reference(user_w, user_d, user_l, user_n, cohort_score) → (delta, p_value, ci_low, ci_high)`. Treats `cohort_score` as a fixed reference (cohort N >> user N per bin, so cohort SE contributes negligibly). Wilson CI on `user_score`, transplanted onto the delta. Unit-tested at boundaries (n=0, all-wins, all-losses, `user_score == cohort_score`).
- **Triple-gate font coloring** applied per bullet: `n ≥ threshold ∧ p < 0.05 ∧ delta outside neutral band` — same convention as Phases 85.1, 87.2.

### Cohort definition (D-05 — carried forward)

Mirror-bucket per v1.17 doctrine: same `(rating tier × TC × color × opponent-type)` as the user's games in the cell. Filter-responsive. Matches Phases 85–87 exactly so the page-wide "you vs comparable peers" frame stays consistent.

### Base clock (D-06 — carried forward)

`base_clock = initial time only` (no increment). Confirmed by `reports/benchmarks-latest.md` to collapse cleanly across ELO and TC. Edge cases for unusual TC strings (`30+30`, `1+30` correspondence) are bucketed to bullet/blitz/rapid/classical anyway — planner sanity-checks during plan-phase.

### D-07 (revised cohort design — supersedes D-05; LOCKED 2026-05-17 post-verification)

The mirror-bucket cohort framing locked in D-05 is retired. The Phase 88
implementation (88-01..88-08) shipped an unfiltered global cohort query
that violated D-05 doctrine and risked OOM at production scale (see
88-VERIFICATION.md CR-01). The Phase 88.1 gap closure replaces the entire
cohort layer with a same-game opponent-quintile split:

- **Comparison set:** the user's own filtered games. No cross-user query.
- **Two parallel quintile splits within the same game-set:**
  - `user_quintile_wdl[tc][q]` — user WDL bucketed by USER's clock-pct at endgame entry.
  - `opp_quintile_wdl[tc][q]` — opponent WDL bucketed by OPPONENT's clock-pct
    at endgame entry, with inverted result (user-win = opp-loss).
- **Delta:** `delta = user_score_in_Q − opp_score_in_Q` (each side scored
  from its own quintile of the same filtered game-set).
- **Significance test:** unpaired two-sample Wilson via existing
  `compute_score_difference_test` (the two splits are independent because
  user and opp clocks fall in different quintiles within the same game).
- **n-gate:** `min(n_user_in_Q, n_opp_in_Q) >= MIN_GAMES_PER_PRESSURE_BIN`.
  Subsumes the small-N cohort cell gate flagged in REVIEW.md WR-01.
- **Schema:** `PressureQuintileBullet.cohort_score` → `opp_score`.
- **Popover copy:** "vs cohort" → "vs opponent".

D-02's per-(TC, quintile) neutral band stays valid as a band on
`user_score − opp_score` — the band shape is independent of which reference
is subtracted. A sanity recalibration runs as Plan 88-12 to confirm the
existing values still apply; expect the ±0.06 editorial cap to dominate
as before. The retired global cohort query, the `compute_score_delta_vs_reference`
helper, and the `_compute_cohort_lookup` aggregator are all deleted.

### Claude's Discretion

Areas the user didn't lock and explicitly delegated to research/planning:

- Statistical test for Clock Gap (paired-diff z-test vs Wilcoxon) — distribution-shape dependent; researcher picks based on benchmark data.
- Exact value of the editorial cap on Score-Delta band half-width (D-02) — planner suggests; ±6pt is a starting proposal.
- Exact values of `MIN_GAMES_PER_PRESSURE_BIN` (proposed 5) and `MIN_GAMES_PER_TC_CARD` (proposed 20) — planner confirms with a prod-DB sample-size sanity check before locking.
- File/module names for the new helper, the new card component, the section orchestrator — planner picks.
- Whether the /benchmarks skill emits 5 quintiles directly or 10 deciles for the frontend to collapse pairwise — planner picks (recommendation in D-03 is 5).
- Card title content (TC name only vs TC + total games vs TC + base-clock context) — not discussed; planner picks, consistent with the existing per-TC pattern from Phase 87.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase design + page doctrine
- `.planning/notes/time-pressure-stats-rework.md` — full Phase 88 design discussion (delta-vs-paired reasoning, statistical foundation, /benchmarks update pattern, open plan-phase decisions). **Primary source.**
- `.planning/notes/v1.17-single-bullet-doctrine.md` — page-wide doctrine: peer/reference vs 0 single-bullet pattern, mirror-bucket cohort definition. All v1.17 phases follow this.
- `.planning/notes/endgame-stats-card-redesign.md` — original v1.17 design document for the Endgames page card refactor.
- `.planning/milestones/v1.17-ROADMAP.md` §"Phase 88" (lines 347–355) — success criteria + dependency on Phase 87 card layout pattern.
- `reports/benchmarks-latest.md` §3.3.2 (lines 903–945) — current TC marginal + ELO marginal + collapse verdict for time-pressure-vs-performance. Confirms ELO collapse (d=0.17), TC review (d=0.34 driven by tb=0 floor). Note: marginals only — per-cell per-user IQR is what the skill update must add.

### Frontend primitives + patterns
- `frontend/src/components/charts/MiniBulletChart.tsx` — bullet primitive reused on every card.
- `frontend/src/components/charts/EndgameTypeCard.tsx` — Phase 87 per-type card pattern (sparse-handling, dimming, sig-gating). Closest analog for Phase 88 cards.
- `frontend/src/lib/scoreBulletConfig.ts` — bullet domain + zone color helpers; new pressure-bullet config likely co-locates here.
- `frontend/src/lib/theme.ts` — `UNRELIABLE_OPACITY`, `MIN_GAMES_FOR_RELIABLE_STATS`, zone colors used by D-01.
- `frontend/src/generated/endgameZones.ts` — where the new metric's per-bin thresholds will land (codegen target).

### Backend math precedent
- `app/services/endgame_math.py` (Phase 85.1) — `compute_paired_difference_test`, `compute_score_difference_test` precedent. New `compute_score_delta_vs_reference` lives alongside.
- `app/services/endgame_zones.py` — codegen source for `endgameZones.ts`. New `chess_score_per_pressure_bin` zone constants emit through here.

### Legacy surfaces (to delete)
- `frontend/src/components/charts/EndgameClockPressureSection.tsx` — current Time Pressure at Endgame Entry table.
- `frontend/src/components/charts/EndgameTimePressureSection.tsx` — current Time Pressure vs Performance line chart.
- Backend `/api/endgames/clock-pressure` and `/api/endgames/time-pressure` response shapes — planner picks whether to replace fields, route, or both. Knip + test sweep at end of phase.

### Memories
- `feedback_zone_band_judgement.md` — tighten band when small effects matter; informs D-02's editorial cap.
- `feedback_llm_significance_signal.md` — don't add parallel sig fields to the LLM payload (out of phase scope this round, but binding when LLM narration of time pressure lands in a future phase).

### Recent related task
- `.planning/quick/260414-u88-aggregate-time-controls-in-time-pressure/260414-u88-SUMMARY.md` — the quick task on 2026-04-14 that aggregated TCs into a single line on the legacy `EndgameTimePressureSection`. Phase 88 reverses that direction (per-TC cards return) now that hypothesis-tested CIs + sparse-TC gating make the per-TC view honest. Useful for understanding why the legacy chart looks the way it does today.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`MiniBulletChart`** (`frontend/src/components/charts/MiniBulletChart.tsx`) — the bullet primitive. 6 bullets per card × 4 cards = 24 instances on `xl`. No new primitive needed.
- **`MetricStatPopover`** (`frontend/src/components/popovers/MetricStatPopover.tsx`) — per-bullet popover convention from Phase 85.1+. Reused per bullet here.
- **`UNRELIABLE_OPACITY` + `MIN_GAMES_FOR_RELIABLE_STATS`** (`frontend/src/lib/theme.ts`) — D-01 directly reuses these.
- **`scoreZoneColor` + `clampScoreCi`** (`frontend/src/lib/scoreBulletConfig.ts`) — domain/zone helpers; the new pressure-bullet config likely follows this module's pattern (one file per metric family).
- **`isConfident`** (`frontend/src/lib/significance.ts`) — triple-gate helper shared across cards.
- **`wilsonBounds`** (`frontend/src/lib/scoreConfidence.ts`) — Wilson CI on user score; transplant onto the delta for D-04.
- **`compute_paired_difference_test`** (`app/services/endgame_math.py`) — Clock Gap reuse per D-04.
- **`endgame_zones.py` codegen pipeline** — emits the `endgameZones.ts` constants; the new metric extends this pipeline.

### Established Patterns
- **Per-TC card grid layout** — Phase 87's `EndgameTypeBreakdownSection` is the closest sibling (5 type cards). Phase 88 uses 4 TC cards on the same grid breakpoints (xl 4-col, lg 2-col, md/below 1-col).
- **Triple-gate font coloring** — `n ≥ threshold ∧ p < 0.05 ∧ outside neutral band` (`isConfident`). Applies per-bullet in D-04.
- **Sparse-card hiding** — Phase 87 per-type card hides when its total games < threshold. Phase 88 mirrors this at the TC-card level.
- **Codegen drift CI** — `bin/gen_endgame_zones_ts.py` regenerates `endgameZones.ts` from `endgame_zones.py`; CI fails on drift. New metric must thread through both.

### Integration Points
- New section component mounts on the Endgames page in the slot currently occupied by `EndgameClockPressureSection` + `EndgameTimePressureSection`.
- Side-panel filter plumbing (TC, ELO, color, opponent type, recency) flows through unchanged — same hooks as Phases 85–87.
- `/api/endgames/*` route shape: planner picks whether to (a) extend `/api/endgames/clock-pressure` and `/api/endgames/time-pressure` in-place, (b) introduce a unified `/api/endgames/time-pressure-cards` route, or (c) fold into the existing `overview` payload. Legacy callers must be removed in the same phase to keep knip clean.

</code_context>

<specifics>
## Specific Ideas

- Adrian explicitly cited `reports/benchmarks-latest.md#L903-945` to ground the IQR discussion — that table is the source-of-truth check for whether the new per-bin metric collapses across ELO. The aggregate-score collapse verdict already in the report (ELO d=0.17 → collapse; TC d=0.34 → review, driven by tb=0 floor) is what justifies D-02's "band per `(TC, quintile)`, pool ELO" default.
- **Explicit correction during discussion:** the band is per `(TC, quintile)`, NOT per `(TC, ELO, quintile)`. ELO is pooled. This is the design Adrian intends; the planner must not silently re-expand the band dimension. The intermediate `(TC × ELO × quintile)` grid exists only as input to the per-quintile collapse verdict — it is not the shipped band shape.
- Adrian's hypothesis: per-user IQR at the 0–20% remaining time bin is lower than at mid quintiles, because performance is compressed near a forced-loss outcome. The new skill output verifies this directly — if confirmed, the per-bin IQR band tightens naturally at extreme pressure. If disproved (users diverge into clock-managers vs flaggers), the band widens naturally. Either way, D-02 is self-correcting.

</specifics>

<deferred>
## Deferred Ideas

- **LLM narration of time pressure** — referenced in the design note as out of scope. Future phase; when it lands, apply `feedback_llm_significance_signal.md` (no parallel sig fields; tighten band instead).
- **Per-move pressure analysis** — current scope is the endgame-entry snapshot only. Per-move time-pressure analytics is a future phase.
- **Tier-gap baseline** (your gap vs distribution of per-player gaps at your tier) — flagged in `v1.17-single-bullet-doctrine.md` as the strongest signal of the three weighed during v1.17 design but out of scope for v1.17 (new benchmark precomputation needed). Carried forward as a future-milestone seed candidate.
- **Time management on the Openings page** — explicitly out of phase scope.
- **Increment-aware base-clock normalization beyond `initial time only`** — benchmark data shows it isn't needed; revisit only if the per-cell IQR check turns up surprises for high-increment classical games.

</deferred>

---

*Phase: 88-time-pressure-stats-rework*
*Context gathered: 2026-05-17*
