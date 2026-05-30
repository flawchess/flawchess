---
id: SEED-007
title: Rebuild /benchmarks as deterministic generator + LLM narration
status: open
planted: 2026-05-30
trigger: When ready to harden the /benchmarks skill (source of truth for shipped gauge zone
  constants) against LLM transcription/arithmetic drift, and to make methodology changes attributable
recommended_vehicle: Separate milestone with two phases (faithful port, then methodology) — NOT
  /gsd-quick. See "Sizing" below. Get explicit consent before creating the milestone/phases.
---

# SEED-007: Rebuild /benchmarks as deterministic generator + LLM narration

## Context

`/benchmarks` today is an LLM running ~40 inline SQL blocks via the benchmark MCP and hand-computing
Cohen's d / IQRs / midpoint drifts into a hand-authored `reports/benchmark/benchmarks-latest.md`. That
report is the **source of truth** for shipped gauge-zone constants (`app/services/endgame_zones.py` →
`frontend/src/generated/endgameZones.ts`), so the hand-computation is a real fragility (transcription /
arithmetic risk, non-deterministic across runs). The production percentile path was already made
deterministic in Phase 93/94 (`scripts/gen_global_percentile_cdf.py`,
`app/services/global_percentile_cdf.py`, `canonical_slice_sql.py`); this seed brings the
zone-calibration report in line.

Grew out of a 10-point methodology review of the skill + report (2026-05-30). Most points were dismissed
by design or already covered by Phases 97–99 (see triage below); what survived is the deterministic
rebuild plus two methodology tweaks.

## Triage of the review (for the record)

- **#1 Lichess-only cohort / cross-platform** — not a problem by design. chess.com ELO is converted to
  lichess ELO (or reported separately in ELO-timeline charts); collapsed charts generalize across TC/ELO,
  non-collapsible metrics get TC-specific charts and/or TC+ELO-specific percentile badges. chess.com ≈
  lichess players modulo rating system.
- **#2 Equal-footing bands vs all-games UI values** — not a problem by design. All metrics except
  percentile badges respond to current filter settings; zone bands are a *stable frame of reference*, not
  exact IQR ranges per filter combination.
- **#3 Known TC mispaint shipped as "keep"** — already being addressed: Phase 97 (TC-specific Endgame
  Metrics cards, shipped), Phase 98 (TC-mix bands on Endgame Type cards), Phase 99 (per-(metric,TC)
  percentile chips).
- **#4 `max|d|` biased/unstable** — worth improving (in scope here). Bands respond to filters so stakes
  are lower, but a more stable statistic is wanted: metric-vs-ELO correlation (Spearman/Pearson) +
  a TC effect measure, with round-number-band miscoverage as a sanity check.
- **#5 Same users across ELO buckets (non-independence)** — not a big problem; only 1000 most-recent
  games/user are used, ELO crossings limited, previously quantified and accepted.
- **#6 No conditional-opportunity floor for conv/recov** — worth looking into (in scope here). Today's
  floors gate on total endgame games, not the winning-advantage / losing entry counts the conditional
  rates actually depend on; 0/3-style noise inflates per-user IQR band tails. Not expected to change the
  big picture.
- **#7 IQR-as-neutral marks 50% atypical** — debatable design decision; recorded as an open question,
  not in scope.
- **#8 Classical thin / looser selection drives biggest TC contrasts** — acknowledged; we may have
  over-conceded (e.g. TC-specific cards) to less-frequent classical players. Retro observation feeding
  #3 scoping, not separate work.
- **#9 LLM-narrated report fragile for source-of-truth constants** — accepted; drives this seed.
- **#10 Full rerun, drop cross-snapshot comparison** — accepted; do the rerun after methodology changes
  land, and drop the in-report cross-snapshot diff section (Claude can still diff against a prior report
  on demand if supplied one).

## Locked design decisions

1. **Faithful port first, methodology second.** First port the *existing* methodology (max|d|, IQR bands,
   current floors, sparse-cell exclusion, equal-footing filter, game-time ELO bucketing) into deterministic
   code, validated by diffing script output against the current `benchmarks-latest.md` within rounding.
   That diff is a clean regression oracle. Only then layer in #4 and #6 as isolated, attributable commits.
   Doing both in one pass entangles port bugs with intended method changes and hides the port bugs.
2. **Code/LLM seam: code emits numbers, LLM applies verdicts + narrates.** The deterministic script
   computes all distributions / d-values (or successors) / IQRs / correlations into a structured artifact
   (JSON + markdown tables). The LLM applies the fixed collapse thresholds (collapse/review/keep) and
   writes prose interpretation + recommendations. **Consequence:** the port diff validates the *numbers*,
   not the verdicts (LLM-authored, may vary run-to-run). Acceptable because verdicts derive from numbers
   via a fixed threshold table; if verdict reproducibility is ever needed, move threshold application into
   code (the one knob to reconsider).
3. **Methodology scope = #4 + #6 only.** #7 is an open question, not scheduled. #1/#2/#5 dismissed.
   #3/#8 covered by Phases 97–99.
4. **Full rerun (#10) + drop the cross-snapshot section** comes with the methodology change, not the port.

## What to do (when triggered)

Recommend splitting into two phases (see Sizing):

**Phase A — deterministic generator (faithful port):**
1. Write a committed generator (e.g. `scripts/gen_benchmarks.py`, `--db benchmark` guarded like
   `backfill_eval.py`) that emits the full benchmark data artifact (JSON + MD tables) from the benchmark DB.
2. Reproduce the existing methodology verbatim; extract pure functions (bucketing, Cohen's d, IQR) with
   unit tests.
3. Gate: numeric output matches current `benchmarks-latest.md` within rounding for every metric, marginal,
   and d; resolve or footnote any discrepancy as a fixed prior transcription error.
4. Update `.claude/skills/benchmarks/SKILL.md` to invoke the generator and narrate the artifact (preserve
   display-formatting, table-rendering, and report-rotation rules; LLM applies the fixed verdict
   thresholds).

**Phase B — methodology + rerun:**
5. #4: replace/supplement `max|d|` with ELO-correlation + TC effect measure + band-miscoverage sanity
   check; record old→new verdict deltas.
6. #6: add a conditional-opportunity denominator floor for conv/recov; validate the minimums against
   benchmark-DB distributions; document.
7. Each change a separate attributable commit vs the Phase-A baseline.
8. Full rerun through the generator (rotate prior latest per the date-based rule); drop the in-report
   cross-snapshot section.
9. Surface any materially-moved zone constants as recommendations (no silent constant changes).

## Sizing — recommend phases, not /gsd-quick

This is too large for `/gsd-quick`: it's a new committed generator script with a regression-oracle gate,
a SKILL.md rewrite, then a separate methodology pass with its own validation and a full rerun. Recommend
a **dedicated milestone with two phases** (faithful port; then methodology + rerun), with the port's
numeric-diff gate as Phase A's exit criterion. **Do not create the milestone/phases without explicit
user consent.**

## Related

- Report reviewed: `reports/benchmark/benchmarks-latest.md` (2026-05-27 snapshot)
- Skill: `.claude/skills/benchmarks/SKILL.md`
- Prior deterministic precedent: Phase 93/94 percentile pipeline
- Memory: `feedback_benchmark_source_of_truth`, `feedback_no_dev_db_reset_in_plans`,
  `project_benchmark_outliers_unfiltered`, `feedback_persist_discuss_before_clear`
- Supersedes the ad-hoc rerun TODO `.planning/todos/pending/2026-05-03-rerun-benchmarks-equal-footing.md`
  intent (the rerun now rides on Phase B)
