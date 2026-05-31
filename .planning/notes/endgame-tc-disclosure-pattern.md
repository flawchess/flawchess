---
title: TC disclosure pattern for the endgame page
date: 2026-05-30
context: /gsd-explore session — "we go through so much pain handling TC differences on the endgame page; how does Lichess Tutor handle it?"
status: decided (drives the Phase 98 respec)
---

# TC disclosure pattern for the endgame page

## The problem this resolves

Time control isn't just a filter on the endgame page — it's woven through the stat
model. The Endgame ELO timeline is per-(platform, TC), TC bucketing drives duration
estimates, and the benchmark layer computes per-metric Cohen's-d collapse verdicts to
decide whether a gauge band needs cell-specific bounds (per TC×ELO) or can collapse to a
global band. A lot of machinery exists to answer one question: *does this number mean
something different in bullet vs classical?*

The acute pain (raised 2026-05-30): we cleanly disentangled the per-TC **Endgame
Metrics** into TC-specific cards (Phase 97), but doing the same to the **Endgame Type
Breakdown** would multiply 5 type cards × 4 TCs = 20 cards. Phase 98 (as originally
specced) tried to dodge that by **TC-mix-weighted blended bands** — re-introducing the
very TC-blending complexity the disentangling had just removed.

## What Lichess Tutor does (the comparison point)

Researched from the lila source (`modules/tutor/`), authoritative:

- **Always per-speed, never pooled.** Tutor builds one `TutorPerfReport` per `PerfType`
  (bullet/blitz/rapid/classical). A single run produces N separate per-speed reports.
- **No upfront TC selector.** It computes all eligible speeds at once; you browse results
  by speed afterward. Default skews to your most-played speed.
- **30-game minimum per speed, not total.** A speed with <30 recent games gets no report.
  Thin players get no report for sparse speeds.
- **Benchmarking is always intra-speed.** "Better/worse than average" compares you to
  peers in that same perf tier. They never compare across speeds.
- **Older Insights** slices by broad speed category (Bullet/Blitz/Rapid), not exact clock
  settings; staff called exact-TC filtering infeasible.

Takeaway: Lichess has **no unification trick**. It sidesteps our entire collapse-verdict
apparatus by never trying to collapse — it segments by speed unconditionally and just
requires enough games per bucket. FlawChess's Cohen's-d machinery is *more* sophisticated;
the pain is the price of being cleverer than Lichess. That cleverness is worth keeping
where it pays (band calibration), not where it doesn't (blending the user's own rates).

## The pattern: per-metric TC strategy, default-active disclosure

Don't pick one global answer. Each section picks the cheapest mode that's honest for its
metric. Three modes:

1. **Pool** — one card, no TC split. Use when the benchmark collapse verdict says TC
   doesn't move the metric (Cohen's d < 0.2) **and** the bigger combined sample is pure
   upside. Example: per-class **Score Gap** (ΔES) collapses across TC at d ≈ 0.13 — a
   single per-class band is correct for all TCs; splitting it renders four identical bands.

2. **Overlay (the timeline trick)** — multi-series viz on shared axes: render the
   **most-active** TC series by default, let the user toggle the others on. Already live
   on the **Endgame ELO Timeline** (most-active platform/TC line shown, rest toggleable).
   Works for anything that overlays on shared axes (lines, grouped bars). Does **not**
   work for single-value gauges.

3. **Collapsible TC-specific cards (the accordion trick)** — one **full-width** card per
   TC, chevron in the header, **most-active TC expanded by default**, the rest collapsed.
   The accordion equivalent of the timeline trick, for sections built from single-value
   tiles/gauges rather than overlay-able series. Preserves correctness (each card is one
   TC — no pooling), keeps cross-TC comparison one chevron away, and avoids the N×4
   explosion. **Hard constraint: the TC cards must span full width and stack vertically.**
   In a multi-column grid, collapsed/expanded cards of unequal height go ragged.

### Why default-active, not "show everything"

Showing all four TCs at once is the explosion. Showing one is Lichess's model but loses
at-a-glance cross-TC comparison (e.g. time-pressure bullet vs rapid). Default-active +
opt-in to the rest is the best of both: glanceable by default, comparison on demand.

### Which TC is the default-active one (the "primary TC" heuristic)

Decided 2026-05-30. **Rank TC buckets by coarse time spent:**

```
score(tc) = games_in_bucket(tc) × NOMINAL_DURATION[tc]
primary   = argmax score(tc)  over TCs whose card passes the games floor
```

- **Coarse, not per-game.** `NOMINAL_DURATION` is a fixed per-bucket constant (named, not
  magic — e.g. roughly bullet ≈ 2 min, blitz ≈ 5 min, rapid ≈ 20 min, classical ≈ 45–60
  min; exact values tunable in planning). We do **not** sum each game's real duration —
  the bucket weight is enough. It's a weighted game count where the weights neutralize
  bullet's volume advantage (a pile of 2-min bullet games loses to fewer 20-min rapid).
- **No recency weighting.** Flat, all-time over the available games.
- **Only among renderable TCs.** Never default-expand a suppressed/sparse card — take the
  argmax over TCs that pass the games floor.
- **Tracks the active filters.** Computed over the currently-filtered game set, so the
  default reflects what the user is actually looking at.

This deliberately replaces the **Endgame ELO Timeline's** default-line algo, which ranks
by raw game count and so always picks bullet. Aligning the timeline to this same primary-TC
heuristic is a **flagged follow-up**, not Phase 98 scope — but the heuristic should live in
one shared util so the page agrees with itself about "your main TC."

## Separate two things the collapse verdict gets conflated into

- **Zone calibration** — what gauge band counts as "typical" rook conversion in blitz vs
  classical. This *legitimately* needs the benchmark collapse verdict (it sets band
  bounds), and it's cheap. Keep it.
- **User-data pooling** — merging *your* bullet + classical rook endgames into one rate.
  This is the correctness hazard. Avoid it. With per-TC cards, each card shows that TC's
  own band against that TC's own rate — apples-to-apples, no blending math.

The TC-mix-weighted band (original Phase 98) tried to make pooling honest via weighting.
Per-TC cards make pooling unnecessary instead. Simpler and more correct.

## Drop the Mixed endgame-type card

Going to a 2×2 type grid (rook/minor/pawn/queen) inside each TC card drops **Mixed**.
Honest rationale (not "redundant"): Mixed is the catch-all material bucket, the **least
actionable** type (you can't train "mixed-material endgames" the way you train rook
endgames), and as the largest fuzziest bucket its WDL tends to track the overall endgame
number anyway. Dropping it buys a clean 2×2 with no awkward 6th-slot gap. If certainty is
wanted before cutting: one benchmark-DB query — is per-user Mixed WDL close to overall
endgame WDL across the cohort? (Pawnless is already hidden.)

## Application

- **Endgame ELO Timeline** → mode 2 (done).
- **Endgame Type Breakdown** → mode 3. This is the Phase 98 respec: per-TC collapsible
  cards, 2×2 type grid (Mixed dropped), per-TC bands, Conv/Recov gauges return TC-honestly
  without blending. See Phase 98 and [[endgame-typecard-tcmix-gauges]] (superseded).
- **Endgame Metrics by TC** (Phase 97, shipped) → already per-TC; could adopt mode 3's
  collapsible affordance as a follow-up, but it's out of Phase 98 scope.
- **Score Gap** within the type breakdown → **forced per-TC for visual consistency**
  (decided 2026-05-30). Statistically it's TC-flat (per-class ΔES TC d≈0.13), so the four
  per-TC bands will be **near-identical** — that's the textbook mode-1 "pool" case. But
  Score Gap conceptually belongs to the endgame type tile alongside the TC-varying
  Conv/Recov gauges, and a single hoisted band would break the per-TC card's visual
  cohesion. So it gets a per-(class × TC) band like the other tile metrics, accepting the
  near-identical bands as the cost of one consistent card grammar. **Do not "fix" this
  back to a single band** on the strength of the d≈0.13 finding — the redundancy is known
  and chosen.

## Related

- [[endgame-typecard-tcmix-gauges]] — the TC-mix-weighted-band approach this supersedes.
- [[endgame-type-card-drop-gauges]] — the 2026-05-29 gauge removal and the d-values that
  prove Conv/Recov need a TC split but Score Gap does not.
- [[endgame-elo-pr-direct-rebuild]] — the timeline whose most-active-line default is the
  template for mode 2 (and the inspiration for mode 3's most-active-expanded default).
