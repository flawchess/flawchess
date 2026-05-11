# Phase 83: Stockfish-baseline predicted endgame score - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 83-stockfish-baseline-predicted-endgame-score
**Areas discussed:** Plan scope, New chart label/framing, Popover framing, WDL chart placement

---

## Plan Scope (3 vs 5)

| Option | Description | Selected |
|--------|-------------|----------|
| 3 core plans only | Sigmoid util + repo/service plumbing + UI restructure. Seed default; Plans 4 and 5 framed as splittable/optional. | |
| All 5 plans in-phase | Add Plan 4 (formal `/benchmarks` calibration) and Plan 5 (LLM prompt awareness) to the core 3. | ✓ |

**User's choice:** All 5 plans in-phase (free-text: "we will do all 5 plans").
**Notes:** Logic mirrors Phase 82 D-13 — tile and LLM should agree on what is narratable from launch, and cohort bands should come from formal calibration to stay consistent with Phase 82's `entry_eval_pawns` band. Locked as D-01.

---

## New Chart Label / Framing

| Option | Description | Selected |
|--------|-------------|----------|
| Stockfish baseline | Aligned with the seed's framing decision. Engine-centric, doesn't claim the user "should" score this. | |
| Reference score | Neutral, doesn't editorialize. Reader has to dig into popover to learn it's the 2300+ Lichess baseline. | |
| Predicted score | Seed's working title. Risks "I should be scoring this" interpretation — exactly the bias the framing wants to avoid for weaker players. | |
| Ceiling score | Conveys "top of range" but unusual chess-UI phrasing. | |
| **Achievable score** | Free-text user response. Implies "reachable in principle" without prescribing — the popover qualifies that hitting it requires 2300+ play. | ✓ |

**User's choice:** "Achievable score" (free-text: "How about 'Achievable score'?").
**Notes:** Locked as D-09. Sidesteps both the predictive bias of "Predicted" and the sterile feel of "Baseline". Paired with the popover framing (next section) for honest sub-2300 messaging.

---

## Popover Framing for Sub-Baseline Gap

| Option | Description | Selected |
|--------|-------------|----------|
| Expected for sub-2300 play | "Lichess curve is fit on 2300+ players; scoring below from positive evals is normal at lower ratings." Avoids "underperformance" language entirely. | ✓ |
| Compare to your peers via Endgame score | Redirect: "Compare against the rating-matched Endgame score on the right, not against this baseline." Treats the baseline as engine-context only. | |
| No special framing | Just define the metric; let the LLM and the Endgame-score bullet handle the comparison. Minimal popover copy. | |

**User's choice:** Expected for sub-2300 play.
**Notes:** Locked as D-10. Popover must explicitly state that the Lichess curve was fitted on 2300+ rapid games and that scoring below from positive evals is normal at lower ratings. Do NOT use "underperformance" anywhere in user-facing copy.

---

## WDL Chart Placement in "What you do with it"

| Option | Description | Selected |
|--------|-------------|----------|
| Duplicate, keep table intact | Add a `MiniWDLBar` to the top of "What you do with it" AND keep the existing "Games with vs without Endgame" table unchanged. Some visual redundancy; table's endgame-vs-non-endgame comparison stays intact. | ✓ |
| Restructure table, lift WDL into tile | Move endgame WDL row into the tile; collapse the table to a single non-endgame row + gap indicator. More work; breaks symmetric two-row comparison; breaks existing tests. | |
| Skip top-row WDL, single-row tile | Don't add WDL to the tile. Symmetric: "Where you start" also becomes single-bullet. Simplest UI, but loses the 2×2 grid the seed wants. | |
| Skip WDL, stack the two new tiles only | "Where you start" = eval + achievable stacked; "What you do with it" = endgame-score bullet only (single row). Asymmetric heights but bottom-row comparison still works. | |

**User's choice:** Duplicate, keep table intact.
**Notes:** Locked as D-08. Visual redundancy on the endgame WDL accepted. Preserves the table's endgame-vs-non-endgame comparison and the Score Gap column it anchors. `MiniWDLBar` import lifted from `EndgamePerformanceSection.tsx`; no reimplementation (D-13).

---

## Claude's Discretion

- Final wording inside the popover paragraph (D-10): polish during implementation; can iterate on PR review.
- Final ordering of the LLM narration when entry_eval / achievable / endgame_score all fire in the same response (D-18): lead with the gap when it's the dominant signal, lead with entry_eval when entry_eval is dominant. Decide during Plan 5 execution.
- Exact placement of the new `MiniWDLBar` legend / aria-label inside the "What you do with it" tile (D-13): match surrounding tile-1 conventions.

## Deferred Ideas

- Per-eval-bin breakdown ("you score below baseline specifically when entering at +1.0…+2.0") — bigger UI lift, inconsistent with the bullet-chart idiom. Possible Endgame Insights v2.
- Paired sig test of the gap (achievable vs achieved) — statistically more precise than two independent Wilson CIs, but the visual juxtaposition is the actual UX goal. Defer indefinitely.
- Openings-side expected score — end-of-opening evals cluster around 0 cp, sigmoid emits ~0.50 everywhere, no signal. Out of scope (see SEED-014 "Why not Openings").
- Per-ELO `ENTRY_EXPECTED_SCORE_ZONES` — defer along the same lines as Phase 82 D-11's deferred per-ELO `ENDGAME_SCORE_ZONES`.
- WDL-in-table consolidation — if the duplication of endgame WDL (top of tile + table row) feels redundant in practice, revisit a follow-up phase to restructure the table.
