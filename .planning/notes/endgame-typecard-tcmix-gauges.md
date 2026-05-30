---
title: Endgame Type Card — Re-add Conv/Recov as TC-mix-weighted Gauges
date: 2026-05-30
status: SUPERSEDED (2026-05-30, same day) — see notes/endgame-tc-disclosure-pattern.md
supersedes_followup_in: notes/endgame-type-card-drop-gauges.md
phase: Phase 98 (respecced — no longer TC-mix-weighted)
---

> **SUPERSEDED 2026-05-30 (same day).** A follow-up `/gsd-explore` session (Lichess Tutor
> research) replaced the TC-mix-weighted **blended band** approach below with **per-TC
> collapsible cards**: one full-width collapsible card per TC, most-active expanded, a 2×2
> type grid (rook/minor/pawn/queen — Mixed dropped) inside, and each card showing its own
> per-(class × TC) band. No TC-mix weighting, no per-(class×TC) eligible-count payload
> math. Conv/Recov gauges still return — but TC-honestly by segmentation, not by blending.
> See [[endgame-tc-disclosure-pattern]] and the respecced Phase 98 in `ROADMAP.md`.
> The benchmark facts below (Conv/Recov d≈1.2–1.7 on TC; per-(class×TC) IQRs feed the
> bands; sparse cells like queen/classical n≈30) remain accurate and carry into the
> respec. Only the *blending mechanism* is rejected.

# Endgame Type Card — Re-add Conv/Recov as TC-mix-weighted Gauges

## Context

On 2026-05-29 (quick-260529-une) the Conversion + Recovery gauges were removed from
`EndgameTypeCard` because their only band was `PER_CLASS_GAUGE_ZONES` — a single
neutral band per class, pooled across all time controls — and conv/recov are
strongly TC-dependent (benchmark Cohen's d ≈ 1.2–1.7 on the TC axis: conversion
rises 10–19pp bullet→classical, recovery falls 11–20pp; see
`reports/benchmark/benchmarks-latest.md` §per-class TC marginal). The pooled band
actively mispaints TC-concentrated users. See
[[endgame-type-card-drop-gauges]].

The removal was the right *interim* move (it stopped the active mispaint), but the
gauges had real value the bullets don't replace. This note records the decision to
bring them back in a TC-honest form.

## Why bring them back (the values that beat the redundancy argument)

- **Legibility.** "When you're ahead, do you win?" (conversion) and "when you're
  behind, do you save it?" (recovery) are immediately understandable. Achievable
  Score Gap ("did you beat the entry-eval sigmoid's expectation?") is precise but
  not legible. The Score/Score-Gap bullets technically capture much of the same
  signal, but not in a form a user reads at a glance.
- **Visual.** A gauge is a stronger glanceable "are you above/below normal" signal
  than a bullet.

The removal note argued these were redundant with Score + Score Gap. They are
*statistically* overlapping but not *experientially* — and legibility + glanceable
visual were the stated product reasons to keep them.

## Decision

Re-add Conversion + Recovery gauges to all 5 `EndgameTypeCard`s (rook, minor_piece,
pawn, queen, mixed) using:

- **Absolute 0–100% arc** — the same gauge idiom the Endgame Metrics (per-TC)
  section already uses. This keeps one gauge grammar on the page, so the Endgame
  Metrics section (Phase 97) is **left untouched** (no cascade).
- **Headline = the raw rate** (e.g. "72%") kept prominent above/with the gauge, so
  the legibility win is preserved. The gauge is the "vs typical" visual; the number
  is the easy read.
- **Blue band = TC-mix-weighted typical range.**
  `band = Σ_tc (user's share of eligible games in tc for this class) × (benchmark IQR for class × tc)`.
  Weight by **conversion-eligible** games per (class, tc) for the conversion gauge
  and **recovery-eligible** games for recovery — because the rate is conditional on
  entering ahead/behind and that entry frequency itself varies by TC.
- **Tooltip:** "Typical range for the time controls you play. Faster controls
  convert less and recover more."

The band is internally apples-to-apples: the user's TC-mixed rate is compared
against the benchmark median/IQR at that same TC mix. A player who is exactly
typical in each TC they play lands inside the band, whatever their mix.

## Division of labor (why TC-only, not TC+ELO)

The rate gauge is deliberately a **coarse, TC-only** instrument. ELO precision lives
in the **Score-Gap percentile chip** (per the architecture: the chips sit on the
Score Gap, not the rate, and are cohort-matched on TC **and** ELO via
`anchorRating`). A *band* cannot replicate TC+ELO matching: per-(class × TC × ELO)
conv/recov cells shatter on sparsity (queen/classical is already n≈30 in the
TC-only marginal; splitting by ELO bucket makes it unusable). The benchmark agrees —
for conv/recov rates ELO is "review/collapse" (d 0.2–0.49) while TC dominates
(d 1.2–1.7). So:

- **Rate gauge** = legible, glanceable, TC-oriented.
- **Score-Gap percentile chip** = precise TC+ELO diagnostic.

Don't pretend the gauge is more than the former.

## Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Revert to the old pooled band exactly | Actively mispaints slow-TC players (the old rook band ≈ bullet-centred, so a median classical player reads "elite"). |
| Per-(type × TC) cards (5 × 4 = 20 views) | Explodes the section; user explicitly wanted to avoid TC-specific versions of every card. |
| Conv/Recov **percentile** gauge (needle = percentile) | Less legible than a raw rate; loses the "72%" headline; rejected by user. |
| TC-scoped toggle on the breakdown | One TC at a time = extra click; closest to the per-TC explosion we wanted to avoid. |
| **Centered** deviation gauge (median always mid-arc) | Cosmetically nice and would rescue the "where's the band" worry, BUT a gauge must mean one thing per page → forces migrating the Endgame Metrics gauges to centered too (page-wide cascade), for a symmetry-only gain. Tooltip solves the same explainability problem for free on an absolute arc. |
| Pooled-IQR band + tooltip (frontend-only) | Cheapest and idiom-consistent, but still over/under-credits players whose TC mix is far from the population's. TC-mix weighting fixes exactly that for bounded backend cost. |

The decisive constraint was **page-wide idiom consistency**: any visual that differs
from the existing Endgame Metrics gauges forces a cascade. Absolute-arc + TC-mix
band + tooltip is the only option that is TC-honest, idiom-consistent, and leaves
the Metrics section alone.

## Open implementation items (planning inputs for Phase 98)

1. **Benchmark stats.** Produce per-(class × TC) IQRs (p25/p75) — and median if the
   band is centred on it — for conversion and recovery, into
   `frontend/src/generated/endgameZones.ts` via `app/services/endgame_zones.py` +
   `scripts/gen_endgame_zones_ts.py` (CI drift gate). The benchmark skill already
   emits per-(class, tc) marginals (`benchmarks-latest.md` lines 869–885).
2. **Backend payload.** The endgame breakdown response must expose per-(class × TC)
   **eligible-game counts** (conversion-eligible and recovery-eligible) so the
   frontend can compute the TC-mix weights. Today it sends only `category.total`
   summed across TCs.
3. **Sparse-cell fallback.** Define a min-n per (class × TC) cell below which that
   TC's weight is dropped or pooled (queen/classical n≈30; pawnless already
   excluded). Avoid letting a thin cell dominate the blended band.
4. **Frontend.** Reuse `EndgameGauge` (still imported by `EndgameMetricsByTcCard`);
   compute the TC-mix band client-side from the payload counts × generated zones;
   add the tooltip. Standard rules: `data-testid`, theme constants, mobile parity,
   `noUncheckedIndexedAccess`, `text-sm` floor (gauge labels), knip-clean.
5. **Reliability gating.** Reuse the existing `MIN_GAMES_FOR_RELIABLE_STATS` gate to
   decide when a gauge renders at all (conditional rates have thin denominators).
6. **Changelog.** This reverses the 2026-05-29 removal — needs its own
   `CHANGELOG.md` `[Unreleased]` entry on merge.

## Related

- [[endgame-type-card-drop-gauges]] — the 2026-05-29 removal this resolves.
- Phase 97 (Endgame Metrics by Time Control) — the sibling per-TC section whose
  gauge idiom we deliberately match and leave untouched.
