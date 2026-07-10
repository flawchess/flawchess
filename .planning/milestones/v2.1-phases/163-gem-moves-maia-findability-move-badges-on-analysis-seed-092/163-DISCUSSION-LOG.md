# Phase 163: Gem moves — Maia-findability move badges on /analysis (SEED-092) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-10
**Phase:** 163-gem-moves-maia-findability-move-badges-on-analysis-seed-092
**Areas discussed:** Qualification edges, Rating source & whose moves, Badge timing & stability, Threshold & calibration scope

---

## Qualification edges

| Option | Description | Selected |
|--------|-------------|----------|
| Keep (Recommended) | Finding the only defensive resource deserves celebration — the seed's lean; es gap ≥ 0.10 guarantees the move mattered | ✓ |
| Exclude still-losing | Chesskit-style: no gem when position stays lost (es below ~0.5) | |
| Keep, higher bar | Lost-position gems only at ≥ 2× MISTAKE_DROP saved gap | |

**User's choice:** Keep
**Notes:** Explicitly rejects Chesskit's still-losing exclusion.

| Option | Description | Selected |
|--------|-------------|----------|
| No guard (Recommended) | Trust the free-lunch guards; a rating-matched badge on sharp theory peers don't find is deserved; revisit at UAT if inflated | ✓ |
| Exclude first N plies | Hard cutoff (e.g. no gems before ply 12/16) | |

**User's choice:** No guard

---

## Rating source & whose moves

| Option | Description | Selected |
|--------|-------------|----------|
| Page ELO (Recommended) | Same selected-ELO the chart and findability ranking use; badges update live with the slider | ✓ |
| Rating at game time | Per-color rating from the imported game, slider-independent, needs free-analysis fallback | |
| Current user rating | current_rating always | |

**User's choice:** Page ELO

| Option | Description | Selected |
|--------|-------------|----------|
| Both players (Recommended) | Symmetric with the flaw-glyph pipeline; opponent gems informative in loss review | ✓ |
| Only the user's color | Personal achievement badge; needs a color filter | |

**User's choice:** Both players

---

## Badge timing & stability

| Option | Description | Selected |
|--------|-------------|----------|
| Any board move (Recommended) | Mainline AND freely-explored moves, mirroring liveFlawByNode | ✓ |
| Mainline game moves only | Review-only badge | |

**User's choice:** Any board move

| Option | Description | Selected |
|--------|-------------|----------|
| Classify at commit (Recommended) | Once per ply at grading bestmove commit, cached, never flickers | |
| Stream with min-depth gate | Badge at depth threshold, may flicker until commit | |
| You decide | Claude picks during planning | |

**User's choice:** Other (free text): "Let's use the same mechanism as for free move flaw tagging"
**Notes:** Interpreted as the `useLiveMoveFlaw` pattern — memo classification as soon as engine data exists, no explicit depth gate, sticky per node via a Map cache in Analysis.tsx. Replaces the seed's open "min-depth stability gate" tunable.

---

## Threshold & calibration scope

| Option | Description | Selected |
|--------|-------------|----------|
| 2% (Recommended) | Strict side of the seed's 2-3% range | |
| 3% | The seed's ~3% anchor — more badges day one | ✓ |
| You decide | Claude picks within 2-3% | |

**User's choice:** 3%

| Option | Description | Selected |
|--------|-------------|----------|
| Dev tabulation helper (Recommended) | Dev-gated per-rung would-badge frequency output for UAT data gathering | |
| Nothing — UAT eyeballs it | Ship the constant only | ✓ |
| Full iso-rarity curve in-phase | Derive the per-ELO curve from real games now | |

**User's choice:** Nothing — UAT eyeballs it

---

## Claude's Discretion

- Detection module location/shape; how C2 reads the Phase 162 reconciled grading map.
- MaiaMoveQualityBar folding and UnifiedMovePopover labeling for the gem bucket.
- SVG-icon marker variant design (lucide Gem in the existing circle-badge geometry) + move-list icon component.
- Popover/tooltip copy wording.
- Free-lunch-guard test fixtures.
- Cache invalidation when the ELO slider moves.

## Deferred Ideas

- Iso-rarity ELO-conditioned threshold curve (post-UAT, slope inverted vs pRefForElo).
- Calibration dev tooling (rejected for this phase; only if UAT eyeballing proves insufficient).
