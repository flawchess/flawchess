# Phase 80: Opening stats — middlegame-entry eval and clock-diff columns - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns
**Areas discussed:** Eval column display, Confidence visualization, Clock diff units, Mobile layout, Bullet chart zones

---

## Eval column display

| Option | Description | Selected |
|--------|-------------|----------|
| Pawns, ±std, signed | e.g. "+0.42 ± 0.85". Std shows volatility. Matches chess conventions; matches Phase 81 endgame-entry tile plan. | |
| Pawns, signed, no spread | e.g. "+0.42". Cleaner column; spread info shifts to tooltip / confidence column. | |
| Centipawns, ±std, signed | e.g. "+42 ± 85". More precise integers; less familiar to casual players. | |
| Pawns mean + 95% CI | e.g. "+0.42 [+0.21, +0.63]". CI directly visualises significance, denser cell. | |
| Bullet chart with 95% CI whisker (free-text) | Reuse existing `MiniBulletChart`, extend with optional `ciLow` / `ciHigh` props for a whisker overlay. Hide the board on the Stats subtab to free width. | ✓ |

**User's choice:** Bullet chart (extended `MiniBulletChart`) with 95% CI whisker. Hide the chess board on the Openings → Stats subtab (like mobile already does) to free horizontal space.
**Notes:** Anchors the row visually; CI whisker carries the uncertainty story so a redundant `±std` text isn't needed.

---

## Confidence visualization

| Option | Description | Selected |
|--------|-------------|----------|
| Drop the bucket pill entirely | CI whisker shows uncertainty. Simpler column. Still gate when n<10. | |
| Keep low/medium/high pill, separate column | Mirrors opening-insights cards exactly. Explicit verbal anchor for users who don't read CI bars. | ✓ |
| No pill, but mute eval cell when n<10 | Just dim the bullet chart; CI whisker carries the rest. | |
| Pill embedded in eval cell | Small "H/M/L" badge tucked in with the bullet chart — saves a column but couples confidence to eval. | |

**User's choice:** Separate column with low/medium/high pill, matching opening-insights cards.
**Notes:** Statistical procedure differs from `compute_confidence_bucket` (one-sample t-test vs trinomial Wald), so a new helper is needed; the N≥10 + p-value thresholds carry over.

---

## Clock diff units

| Option | Description | Selected |
|--------|-------------|----------|
| % of base time, seconds in parens | e.g. "+8.2% (+24s)". Mirrors `EndgameClockPressureSection`. Same formatter, consistent reading across pages. | ✓ |
| Seconds only, signed | e.g. "+24s". Simpler; avoids base-time variability across mixed-TC openings. | |
| % only, signed | e.g. "+8.2%". TC-normalized; no raw seconds. | |
| Bullet chart for clock diff too | Reuse `MiniBulletChart` for visual consistency with the eval column; doubles chart count per row. | |

**User's choice:** % of base time with seconds in parentheses.
**Notes:** Direct visual parity with the existing endgame clock-diff cell.

---

## Mobile layout

| Option | Description | Selected |
|--------|-------------|----------|
| Stacked row card on mobile | Top line = name+games+WDL (current); second line = bullet chart + confidence pill + clock diff stacked. Dense, no taps required. | ✓ |
| Same row, all 3 columns inline | Keep horizontal row; risks scroll / cramped cells. | |
| New columns desktop-only, expandable on mobile | Hide on mobile; tap to expand. Cleaner scan but hides important info. | |
| Same desktop layout, mobile drops the bullet chart | Replace bullet chart with a signed number on mobile to save width. | |

**User's choice:** Stacked row card on mobile.
**Notes:** Keeps the existing scan flow on top, adds the new metrics in a second tier below — no new affordances to learn.

---

## Bullet chart zones

| Option | Description | Selected |
|--------|-------------|----------|
| Neutral ±0.20 pawns, domain ±1.0 | Tight neutral; full pawn fills the bar. | |
| Neutral ±0.30 pawns, domain ±1.5 | Wider neutral matching "book equal" heuristic; more headroom. | |
| Neutral ±0.50 pawns, domain ±1.0 | Conservative — only big edges get colored. | |
| Defer — calibrate from benchmark DB during research | Researcher pulls population distribution per ELO/TC bucket; proposes zones from that. | ✓ |

**User's choice:** Defer to benchmark research.
**Notes:** Same calibration approach used for other Phase 1.10+ benchmark-anchored metrics. Researcher should also report a Cohen's-d collapse verdict (whether zones can be globally collapsed across TC/ELO).

---

## Claude's Discretion

- Mate handling at middlegame entry (likely exclude `eval_mate IS NOT NULL` rows from the mean; researcher confirms incidence).
- Backend payload shape — extending `OpeningWDL` with new optional fields is the obvious choice; planner confirms.
- SQL aggregation pattern (`ROW_NUMBER` window vs `DISTINCT ON` vs correlated subquery) — planner picks the cheaper shape using endgame-entry prior art.
- Sortability of new columns — likely yes, deferred to planner.
- Tooltip / column header info popovers — apply the existing pattern from `EndgameClockPressureSection.tsx`.

## Deferred Ideas

- Tabled phase-aware analytics ideas in `.planning/notes/phase-aware-analytics-ideas.md` (Middlegame ELO, Opening ELO, bleed-cp decomposition, phase-conditional conv/recov, time-vs-phase correlation, phase-flip game filter, opponent diff per phase, LLM narrative upgrade) — feed the v1.16 brainstorm pool, not in Phase 80.
- Phase 81 (endgame-entry eval twin-tile) — already on roadmap; independent.
- Concept-explainer accordion on the Stats subtab — separate UX phase if wanted later.
