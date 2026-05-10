---
id: SEED-015
status: dormant
planted: 2026-05-10
planted_during: /gsd-explore session immediately after SEED-014 (Stockfish-baseline expected score for endgame entries) was planted
trigger_when: SEED-014 has shipped (the "Predicted score" and "Endgame score" bullet charts are live in the twin-tile section), AND either (a) the visual juxtaposition feels insufficient — users keep asking "is my gap normal?", or (b) the next round of endgame analytics work is being scoped
scope: phase (single, ~2-3 plans) — gap as first-class metric (sig test + peer-calibrated benchmarks + optional dedicated bullet) + LLM prompt awareness
depends_on: SEED-014
---

# SEED-015: Predicted-vs-achieved endgame gap as a first-class metric

## Why This Matters

SEED-014 ships two bullet charts in the bottom row of the twin-tile section (`Predicted score` in "Where you start", `Endgame score` in "What you do with it"). They share an axis and cohort-band styling so users can eyeball the gap. That's the v1.

**The gap itself is the genuinely novel signal**, and it deserves consideration as a first-class metric in its own right:

- `endgame_score` mixes two things — quality of entry positions + conversion skill. A user who consistently enters endgames with bad positions has a low `endgame_score` but might convert *normally* given what they had to work with.
- `gap = endgame_score − predicted_score` (per-game, then averaged) **isolates conversion/defense skill from entry-position quality**. That's a distinct signal, not a re-statement of `endgame_score` and not derivable from either component bullet alone.

Without elevating the gap, the v1 ships with three failure modes:

1. **No significance verdict.** Users see the gap visually but cannot tell whether their gap is statistically different from zero (or from peers). The LLM can hand-wave this in prose, but the tile cannot.
2. **No peer calibration.** The Lichess sigmoid is fitted on 2300+ rapid games. A 1500 player has a systematically negative gap by construction. Without per-(ELO, TC) benchmarks, "my gap is -3pp" reads as "I'm bad at endgames" when it might mean "I'm closing the gap better than my peers (median 1500 bullet player is at -5pp)." This is the framing flip that turns a confusing tile into an actionable one.
3. **LLM cannot narrate the gap as a finding.** Without an explicit `endgame_gap` field plumbed through `insights_service.py`, the LLM only sees the two component metrics and has to derive the gap inline. With an explicit field carrying value + sig + peer-calibrated zone, the LLM can narrate "your conversion skill is below peer baseline" as cleanly as it narrates Conv/Recov today.

## When to Surface

Trigger any of:

1. SEED-014 has shipped and a user asks "is my gap normal?" or "should this gap be sig-tested?".
2. The next endgame-zones recalibration sweep (sister activity to SEED-002 / SEED-006).
3. Roadmap planning for an Endgame Insights v2 milestone.
4. The LLM narration on a striking case (large achieved-vs-predicted gap, e.g. user 28 from Phase 82) feels weaker than it should because the gap isn't an explicit finding.

**Do NOT trigger this seed before SEED-014 has shipped and been used in production for at least a phase cycle.** The whole point of deferring it is to see whether the visual juxtaposition alone is sufficient. If it is, this seed becomes lower priority.

## Proposed Scope (2-3 plans)

### Plan 1 — Per-game gap + sig test in the existing pipeline

Extend the SEED-014 plumbing in `endgame_repository.py` / `endgame_service.py`:

- Per game in the cohort, compute `gap_i = actual_score_i − predicted_score_i` where `actual_score_i ∈ {0, 0.5, 1}` and `predicted_score_i ∈ [0, 1]` from the Lichess sigmoid (mate handled per SEED-014 Plan 1).
- Aggregate per cohort: mean gap, n, plus a sig test against zero.
- **Methodology question** — pick one before planning the phase:
  - **(a) Wilcoxon signed-rank test on `gap_i`.** Statistically clean for paired continuous-vs-discrete data, but a new method to defend.
  - **(b) Per-game Wilson on `sign(gap_i)`.** Proxy: count games where actual > predicted vs games where actual < predicted (treat gap=0 as 0.5 contribution or drop). Reuses the project's chess-score Wilson util — per memory `feedback_wilson_chess_score`, prefer existing util.
  - **(c) Bootstrap CI on mean gap.** Conceptually simplest, no parametric assumption. Most expensive computationally.
  - **Lean (b)** for consistency with the rest of the project; document the choice in a 2-line comment, no methodology editorializing per memory `feedback_wilson_chess_score`.
- New schema fields: `endgame_gap` (mean), `endgame_gap_n`, `endgame_gap_p_value`, `endgame_gap_ci_lo`, `endgame_gap_ci_hi`.

### Plan 2 — Peer-calibrated benchmarks via `/benchmarks`

Extend `.claude/skills/benchmarks/SKILL.md` with a new section `### N. Endgame predicted-vs-achieved gap (per-user)`:

- Canonical CTE per the skill (lichess_username join, `bic.status='completed'`, equal-footing filter, sparse-cell exclusion — see SEED-013 "Methodology Lessons" section, every gotcha applies).
- Per-user mean gap, sample floor `endgame_gap_n >= 20`.
- Cell tables (5×4, sparse-cell footnoted), TC marginal, ELO marginal, pooled, Cohen's d collapse verdicts.
- Run /benchmarks, write `reports/benchmarks-YYYY-MM-DD.md` with the new section appended.
- Almost certainly **per-ELO** stratification (the gap shrinks with rating: a 2400 player closes the Stockfish-baseline gap better than an 800 player by construction; that's the whole rating-tilt point). Confirm with formal Cohen's d before locking; if confirmed, mirror the `PER_ELO_GAUGE_ZONES` dispatch pattern.
- Lock bands into `app/services/endgame_zones.py` as `ENDGAME_GAP_ZONES`. Regenerate `frontend/src/generated/endgameZones.ts`.

This is the **critical** plan. Without peer calibration, Plan 1 ships a metric that is dominated by rating tilt and tells weaker users they're worse than they are.

### Plan 3 — UI surface decision (pick one)

Two paths, decide based on how busy the section feels post-SEED-014:

**(a) Single-line verdict, no new chart.** Add a line between the two score-axis bullets in the twin-tile section: e.g., "Gap to Stockfish baseline: -3pp (sig, p<0.01) — wider than 78% of peers at your level." Compact, low visual cost, all the information in text. Best if the 2×2 layout already feels full.

**(b) Dedicated mini bullet chart.** Add a third element in the section, styled like the Diff bullet in `EndgameScoreGapSection.tsx` — signed-diff axis, peer-calibrated neutral band from `ENDGAME_GAP_ZONES`. Single-row, mini-height to keep the section scannable. Best if the section has visual room and the gap deserves chart-level prominence.

Lean **(a)** for v1 of this seed. The dedicated chart is cheap to add later if (a) feels insufficient, but starting with (a) avoids visual bloat and keeps the SEED-014 layout intact.

### Plan 4 — (Optional, small) LLM prompt awareness

Add `endgame_gap` to the glossary in `app/prompts/endgame_insights.md`. Expand the `endgame_start_vs_end` subsection guidance: the LLM should narrate the gap as the **headline conversion-skill diagnostic** — distinct from `endgame_score` (which mixes entry quality and conversion skill). Pair `gap=below_peers` with `entry_eval=above_zero` to land the user-28 pattern as "you arrive at endgames with the upper hand, but you cash in less of that advantage than your peers do" instead of two separate findings the LLM has to glue together. Bump `_PROMPT_VERSION` in `insights_llm.py`.

This can split as a /gsd-quick task after Plans 1-3 ship.

## Design Decisions Captured Now

- **Why elevate the gap as a separate metric, not just a derived display.** The gap isolates conversion/defense skill from entry quality. Two users with identical `endgame_score=0.50` can have wildly different conversion skill: user A enters at predicted=0.65 (winning positions, scored only 0.50 — bad converter), user B enters at predicted=0.35 (losing positions, scored 0.50 — good defender). Without the gap, the tile cannot tell them apart.
- **Why peer-calibrated bands matter more here than for the components.** The Lichess sigmoid baseline introduces systematic rating tilt into the gap. A 1500 player has a structurally negative gap. Without `/benchmarks` per-ELO calibration, the metric is misleading. With it, the framing flips from "you underperform Stockfish" to "you under/over-perform your peers' ability to close the Stockfish gap" — actionable.
- **Why ship SEED-014 first, then this.** Two reasons. First, the SEED-014 visual juxtaposition might be sufficient on its own — ship and observe. Second, even if it isn't, the gap metric requires the predicted-score plumbing from SEED-014; this seed cannot ship before SEED-014.
- **Why not subsume Conv/Parity/Recov diff bullets in `EndgameScoreGapSection`.** Different stories, different axes:
  - Conv/Parity/Recov uses 3 hard-thresholded buckets vs **opponent-mirror** baseline (peer-calibrated).
  - Predicted-vs-achieved gap uses continuous eval vs **Stockfish-ceiling** baseline (engine-calibrated, then peer-calibrated for the band).
  - Both are "score gap" stories. They answer different questions: "how do you do vs your opponent" (Conv/Recov) vs "how close to optimal play do you score" (gap). Keep them separate; each earns its place.
- **Sig test methodology — pick (b) Wilson on sign(gap) for v1.** Mirrors the project's existing util, no new method to defend, conservative (loses information about gap magnitude but errs on caution). Upgrade to Wilcoxon or bootstrap only if (b) consistently produces verdicts that visibly disagree with the gap's apparent magnitude. Per memory `feedback_wilson_chess_score`, do not editorialize the choice in design docs.

## Open Decisions (defer until phase planning)

- Plan 3 path (a) vs (b) — decide based on how the SEED-014 layout actually looks in production.
- Whether `gap_i` for mate-result games (predicted = 0 or 1, actual ∈ {0, 0.5, 1}) deserves special handling. A forced mate against the user with actual=0.5 (somehow drew?) is a near-impossible event but contributes a +0.5 gap that's not really a "skill" signal. Probably exclude mate-pred games from the gap aggregation, even though SEED-014 includes them in the predicted-score component. Confirm with cohort prevalence — if mate-pred is <1% of endgames, the decision doesn't matter.
- Whether to display the gap on the LLM glossary as `endgame_gap` or `endgame_conversion_gap` to distinguish from any future "opening gap" metric. Lean `endgame_gap` for now; rename when a sister metric appears.
- Naming for `ENDGAME_GAP_ZONES` per-ELO bands — match the `ENDGAME_SKILL_ZONES` / `ENDGAME_SCORE_ZONES` family conventions when SEED-014 lands and we see what naming pattern got picked there.

## Methodology Lessons Inherited from SEED-013 / SEED-014

If Plan 2 (formal /benchmarks section) is on the table — and it should be — copy the canonical CTE verbatim from `/benchmarks` SKILL.md. Every gotcha from SEED-013 "Methodology Lessons" applies: lichess_username join (NOT benchmark_user_id), `bic.status='completed'`, equal-footing `|opp_rating - user_rating| <= 100`, sparse-cell exclusion, mate handling per SEED-014 Plan 1. A spike that bypasses the canonical CTE will produce wrong distributions and wrong bands.

## Estimated Effort

2-3 plans. Plan 1 (~half a day): mostly mirrors SEED-014 plumbing. Plan 2 (~half a day): /benchmarks territory, well-trodden by SEED-013/014. Plan 3 (~2-4 hours depending on path (a) or (b)). Plan 4 (~1 hour): /gsd-quick task. Smaller than SEED-014 because the data plumbing piggybacks on it.

## Cross-references

- Predecessor seed: `.planning/seeds/SEED-014-stockfish-baseline-vs-achieved-endgame-score.md` — required to ship before this
- Predecessor seed: `.planning/seeds/SEED-013-llm-prompt-awareness-of-endgame-start-vs-end.md` — established the `verdict` field pattern this seed reuses
- Phase 81 (twin-tile section): `.planning/phases/81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table/`
- Phase 82 (LLM prompt awareness): `.planning/phases/82-llm-prompt-awareness-of-endgame-start-vs-end-metrics/`
- Existing gap pattern to mirror visually: `frontend/src/components/charts/EndgameScoreGapSection.tsx` (Diff column + bullet chart with self-calibrated neutral band)
- Conv/Recov eval thresholds (the discrete sister metric): `app/services/endgame_service.py:162-211`
- Per-ELO band dispatch pattern: `app/services/endgame_zones.py` (`ENDGAME_SKILL_ZONES`, `PER_ELO_GAUGE_ZONES`)
- /benchmarks skill: `.claude/skills/benchmarks/SKILL.md`
- Wilson chess-score util: project memory `feedback_wilson_chess_score.md` (do not editorialize methodology)
