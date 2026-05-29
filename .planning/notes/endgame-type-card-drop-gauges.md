---
title: Drop Conv/Recov gauges from Endgame Type cards (no TC split)
date: 2026-05-29
context: /gsd-explore session on decluttering the Endgame Type Breakdown section
---

# Drop Conv/Recov gauges from Endgame Type cards

## Decision

Keep **one card per endgame type** (rook, minor_piece, pawn, queen, mixed — pawnless
hidden). Remove the two **Conversion / Recovery gauges** from each `EndgameTypeCard`.
Keep the rest: **WDL bar + Games link, Score bullet, Score Gap bullet**.

**No TC-specific cards.** The exploration started from "split the type cards into
TC-specific cards like other sections, keeping only Score Gap." That idea was rejected
on the data.

## Why the TC split was rejected (the data inverts the premise)

From `reports/benchmark/benchmarks-latest.md`:

- **Score Gap is the *one* metric in this section that collapses across TC** —
  per-class per-span ΔES Score Gap TC Cohen's d ≈ **0.13** (line 1064/1100), well under
  the 0.2 collapse floor. A single per-class `achievable_score_gap` band is correct for
  all TCs. Splitting it by TC would render four near-identical bands.
- **The metrics that *do* vary by TC are Conv/Recov** — d ≈ 1.19–1.67 (lines 917–921).
  They are exactly the metrics the original plan wanted to drop.
- So the plan split on the axis the surviving metric is flat across, while dropping the
  metrics that actually justify a split.

The stated drivers were (1) the section is information-overloaded and (2) the Conv/Recov
gauges mispaint by TC (§3.4.1, line 923: a bullet player is judged against slow-TC bands).
**Dropping the gauges serves both** — it declutters *and* kills the mispaint by removal,
so the deferred §3.4.1 "TC-specific conv/recov bands" work is no longer needed for this
surface. Keeping one card per type avoids the 5→20 card blow-up and the sparsity it would
cause (Score Gap needs ≥20 spans/user/class for a stable read, line 1003).

## Acknowledged cost

The type cards were the **only** place Conv and Recov appear broken out **by endgame
type** (`EndgameMetricsByTc` shows them by TC, not by type). Dropping the gauges trades
the conversion-vs-recovery decomposition per type for a single engine-adjusted Score Gap
(which blends conversion, parity, and recovery spans). Accepted knowingly.

## Consciously overrides two recorded benchmark decisions

- **Line 1022** "KEEP ALL THREE SIGNALS" (Score + Score Gap + Conv/Recov gauges, r≈0.10).
- **Line 1102** "keep layout."

Both predate this decluttering call. Do **not** "fix" the gauges back on the strength of
those lines — this note is the newer decision.

## Backend conv/recov is NOT dead (do not remove)

`insights_service.py:1017` (`_findings_conversion_recovery_by_type`) consumes
`cat.conversion.conversion_pct` / `recovery_pct` / `recovery_games` and runs them through
`assign_per_class_zone(...)` to build the **LLM endgame insights narration**. The
per-class conv/recov bands in `app/services/endgame_zones.py` feed that same pipeline.

Therefore the change is **frontend-only**:

- `EndgameTypeCard.tsx`: remove gauge rows (live render + empty-state shell), drop
  `convZones`/`recovZones`/`bands` derivation and the unused imports (`EndgameGauge`,
  `colorizeGaugeZones`, `PER_CLASS_GAUGE_ZONES`).
- The generated TS `PER_CLASS_GAUGE_ZONES` export becomes frontend-dead → **knip-ignore**
  it; do **not** trim `gen_endgame_zones_ts.py` (the Python registry still feeds insights).
- Update gauge assertions in the 3 frontend tests (`EndgameTypeCard.test.tsx`,
  `EndgameTypeBreakdownSection.test.tsx`, `Endgames.overallPerformance.test.tsx`).
- `category.conversion.*` stays on the `/stats` wire (insights needs the same response
  shape) — it just stops rendering on the cards.
- Trim the Conv/Recov metric definitions from the page-level `h2` InfoPopover in
  `Endgames.tsx`.

`EndgameGauge` the component survives — `EndgameMetricsByTcCard` still uses it.
