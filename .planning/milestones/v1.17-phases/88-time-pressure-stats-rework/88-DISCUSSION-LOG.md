# Phase 88: Time Pressure stats rework with hypothesis tests + CIs — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `88-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 88-time-pressure-stats-rework
**Areas discussed:** Empty pressure bin rendering, Score-Delta color-zone band width
**Areas not discussed (decisions carried forward from `.planning/notes/time-pressure-stats-rework.md`):** Sparse-TC card gating policy (hide entire card below MIN_GAMES_PER_TC_CARD ~20, matches Phase 87 pattern), card title content (planner picks consistent with existing per-TC patterns).

---

## Empty pressure bin rendering

### Round 1: render shape

Initial options presented:

| Option | Description | Selected |
|--------|-------------|----------|
| Dash + sample count, fixed row | Always render 5 rows; bullets below threshold show a dash + `n=X` inline. Cards identical height; visual rhythm preserved. | |
| Omit the bullet, keep axis tick | Render axis tick + label but no whisker / dot / CI. Sample count as small chip. Compromise. | |
| Omit the row entirely | Skip the row completely. Card height varies across the 4-card grid. Maximises density; sacrifices grid uniformity. | |

**User's response:** Requested clarification → "dim the row" (free-text). Suggested a fourth option using the `UNRELIABLE_OPACITY` pattern already in `EndgameTypeCard`.

### Round 2: threshold edges for the dimming policy

| Option | Description | Selected |
|--------|-------------|----------|
| Dim below MIN_GAMES, hide at n=0 | 0 < n < MIN_GAMES_PER_PRESSURE_BIN: dimmed bullet, no triple-gate font coloring. n=0: row slot reserved, dash + "no games". | ✓ |
| Dim below MIN_GAMES, omit at n=0 | Same dimming behavior, but n=0 omits the row entirely (card heights vary). | |
| One threshold: dim below MIN_GAMES, no hard floor | Any n ≥ 1 renders dimmed; only n=0 dashes. No hard hide. | |

**User's choice:** Dim below MIN_GAMES, hide at n=0.
**Notes:** Preserves identical card height across the 4-TC grid. Dimming reuses the existing `UNRELIABLE_OPACITY` constant from `frontend/src/lib/theme.ts` (same pattern as `EndgameTypeCard`). Captured as **D-01** in CONTEXT.md.

---

## Score-Delta color-zone band width

### Round 1: how to derive the band

Initial options presented:

| Option | Description | Selected |
|--------|-------------|----------|
| Tightened band, uniform across all 5 bins | One editorial half-width (e.g. ±3pt) for all 5 bins. Aligned with `feedback_zone_band_judgement.md`. Risk: extreme-quintile cohort noise misclassified. | |
| Per-bin band from cohort spread, capped | Use a fraction of per-bin cohort SD (e.g. 0.5·SD or IQR/4), cap at editorial max. Best honors per-bin reality. | |
| Project-default cohort IQR per bin | Standard project convention: per-bin neutral band = inter-quartile range of per-user delta distribution. Mechanical, no editorial judgement. | (leaning) |
| Single global band, editorial | One editorial band (e.g. ±5pt) across all bins AND TCs. Simplest. Trades per-bin sensitivity for grid consistency. | |

**User's response:** Requested clarification before answering → free-text: "I'm leaning 3. Project-default cohort IQR per bin. But we don't have IQRs per time control and 20% time pressure bins yet, see @reports/benchmarks-latest.md#L903-945. I expect the IQRs for the 0-20% remaining time at endgame entry bucket to be much lower."

### Round 2: Claude's first synthesis (later corrected by user)

Claude initially wrote the decision as **per `(TC × ELO × quintile)` IQR with editorial cap**. User immediately corrected: "we want IQRs per (TC, pressure_quintile), not ELO" — the band pools ELO, justified by the existing ELO-marginal collapse verdict (d=0.17) in `reports/benchmarks-latest.md` §3.3.2.

**Final decision:** Project-default cohort IQR per `(TC, quintile)` with editorial cap, ELO pooled.

**Notes:**
- 20 band entries total (4 TCs × 5 quintiles), not 100.
- The cohort `score` reference line (centre of each Score-Delta bullet) is a separate concern — it comes from live API mirror-bucket lookup against `(rating × TC × quintile × color × opponent-type)`, same pattern as Phases 85–87.
- The `/benchmarks` skill still computes the intermediate `(TC × ELO × quintile)` grid for the per-quintile Cohen's d collapse verdict; only the shipped band constants collapse ELO.
- Editorial cap (suggested ±6pt) protects against extreme-quintile small-N IQR inflation.
- Captured as **D-02** in CONTEXT.md; the `/benchmarks` skill consequences are captured as **D-03**.

---

## Claude's Discretion

The following are explicitly delegated to research/planning:

- Statistical test for Clock Gap (paired-diff z-test vs Wilcoxon) — distribution-shape dependent.
- Exact editorial cap value on the Score-Delta band half-width (suggested ±6pt).
- Exact values of `MIN_GAMES_PER_PRESSURE_BIN` (proposed 5) and `MIN_GAMES_PER_TC_CARD` (proposed 20) — planner confirms via a prod-DB sample-size sanity check.
- Card title content (TC name only vs TC + total games vs TC + base-clock context).
- Whether the `/benchmarks` skill emits 5 quintiles directly or 10 deciles for frontend pairwise collapse.
- Route / response-shape design for the new endpoint (extend existing routes, introduce a unified route, or fold into overview).
- File / module naming for the new helper and new components.

## Deferred Ideas

- LLM narration of time pressure — future phase. Apply `feedback_llm_significance_signal.md` when it lands.
- Per-move pressure analysis — future phase (current scope is endgame-entry snapshot only).
- Tier-gap baseline (your gap vs distribution of per-player gaps at your tier) — strongest signal per `v1.17-single-bullet-doctrine.md`, out of scope for v1.17.
- Time management on the Openings page — out of scope by design.
- Increment-aware base-clock normalization beyond `initial time only` — benchmark data shows it isn't needed.

## Areas not explicitly discussed (carried forward from design note + standard v1.17 conventions)

- Mirror-bucket cohort definition (rating × TC × color × opponent-type) — locked in `v1.17-single-bullet-doctrine.md`.
- `base_clock = initial time only` — locked in `time-pressure-stats-rework.md`.
- Triple-gate font coloring (`n ≥ threshold ∧ p < 0.05 ∧ outside neutral band`) — standard v1.17 convention.
- Phase 89 polish extends to the new card surfaces — standard precedent.
- New backend helper `compute_score_delta_vs_reference` shape — locked in design note.
- 4-col-on-xl / 2-col-on-lg / 1-col-below grid — matches Phase 87 per-type card layout.
