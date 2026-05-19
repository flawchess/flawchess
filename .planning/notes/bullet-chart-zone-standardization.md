---
title: Bullet chart zone standardization — when to force 1/3 / 1/3 / 1/3 geometry
date: 2026-05-15
context: /gsd-explore session after Phase 87.1 (per-span Score Gap by Endgame Type), reviewing benchmarks-latest.md §3.4 calibration vs preference for symmetric round-number bands and visual standardization across stacked bullets
---

# When to standardize bullet chart neutral-zone geometry

## Design preferences (anchors)

- **Symmetric, round-number bands** preferred over raw IQR (e.g. `±5pp` over `[−4.2pp, +5.5pp]`).
- **IQR as a guide, not gospel** — editorial tightening / loosening is allowed when small effects need to paint or wide cohort IQRs would over-paint (per memory `feedback_zone_band_judgement.md`).
- **Stacked bullet visual comparability matters** — when 6 class rows render in one card, the eye should be able to compare across rows at a glance.
- The stacked-view read is **(1) categorical** ("am I red/blue/green per class?") + **(3) raw values on drill-in** — *not* (2) z-score-style "more out of cohort on rook than mixed". This pin matters.

## The design pattern: band width = domain width / 3

> Pick the band first (round, symmetric, IQR-informed). Then set the chart domain = 3× the band width, centered on the midpoint. Each bullet renders 1/3 red / 1/3 blue / 1/3 green by construction, and the axis stays linear so raw values remain readable.

This satisfies (1) + (3) without z-score gymnastics: the geometry is standardized, the axis still shows real numbers.

## Decision rule — when to apply it

Different stacks need different treatment. The split is by what the rows represent, not by component or page:

### Rule A. Per-class stacks of the same metric → apply Option B (per-row domain rescaled to 1/3/1/3/1/3)

**Example:** Endgame Type Breakdown, 6 class rows of chess-score (rook, minor_piece, pawn, queen, mixed, pawnless).

The rows are *the same metric measured against different cohorts*. The user's natural mental question is "where do I sit *relative to my cohort* on each class?" — a cohort-relative read by construction. Per-class bands (e.g. rook `[0.44, 0.57]`, queen `[0.41, 0.63]`, per `benchmarks-latest.md` §3.4.1) with per-row domains rescaled so each band fills the central 1/3 is honest: the marker means "relative to this cohort", and the domain encodes the cohort spread.

**Cost accepted:** axis tick marks differ row to row (rook 0.31→0.70, queen 0.25→0.74). Visually the colored bands align across the stack; the numbers under them don't. Acceptable because the comparison is cohort-relative, not absolute.

### Rule B. Same-unit metric stacks → keep shared domain, accept unequal blue widths

**Example:** Endgame Score Differences card with Achievable Score Gap (band ±5pp) + Endgame Score Gap (band ±10pp), both on a ±20pp domain. Today: 25% blue vs 50% blue on the same domain.

The rows are *different metrics that share a unit* (percentage points from baseline). Users will naturally compare positions across the rows ("how off-baseline am I on each"). If you give each row its own domain to force 1/3 blue:

- Achievable marker at "right edge of blue" = +5pp
- Endgame marker at "right edge of blue" = +10pp

Same visual position, different numbers — breaks the unit-eye comparability you get for free with a shared domain.

The wider blue on Endgame Score Gap is *doing work*: it signals "this comparison is genuinely noisier (two-sample variance vs paired variance) — don't over-read small deviations". Hiding that with a wider domain is dishonest about variance.

**Keep as-is.** The asymmetry is the signal.

### Rule C. Different-unit metrics in the same card → 1/3 standardization is free, apply it

**Example:** a hypothetical card mixing a conversion bullet (0–100%) and a score-gap bullet (±20pp). Axes already differ, so 1/3 / 1/3 / 1/3 doesn't cost anything that wasn't already gone.

## Surfaces to revisit under this rule

- **Endgame Type Breakdown** (Endgames page) → Rule A. Apply per-class bands from §3.4.1 (`rook [0.44, 0.57]`, `minor_piece [0.43, 0.58]`, `pawn [0.42, 0.59]`, `queen [0.41, 0.63]`, `mixed [0.46, 0.56]`, pawnless deferred). Per-row domain = 3× band width centered on 0.5. Codegen `PER_CLASS_SCORE_BULLET_ZONES` registry in `app/services/endgame_zones.py` → `endgameZones.ts`, consumed in `EndgameTypeCard.tsx`.
- **Endgame Score Differences** (Overall Performance section) → Rule B. **Keep as-is.** Document that the visual asymmetry between the two bullets is intentional.
- **Other stacks** (Conv/Parity/Recov peer bullets, Time Management) — re-check before committing the rule globally. The doctrine here is "rule first, then audit each stack", not "blanket rewrite".

## What this is not

- Not a z-score / standardized-distance encoding (rejected as design read (2)).
- Not a mandate that every bullet on the page must be 1/3 / 1/3 / 1/3 — Rule B explicitly preserves proportional widths where the cohort comparison isn't the implicit read.
- Not a deviation from `feedback_zone_band_judgement.md` — editorial tightening still applies within the IQR-informed band proposal.
