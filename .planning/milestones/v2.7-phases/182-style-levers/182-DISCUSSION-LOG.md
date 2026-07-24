# Phase 182: Style Levers - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-21
**Phase:** 182-Style Levers
**Areas discussed:** Style param shape, Opening books, Resign & draw policy, Tuning & verification

---

## Style param shape

| Option | Description | Selected |
|--------|-------------|----------|
| Raw knobs + style bundles as data | Engine consumes only numeric BotStyleParams; 4 named style→knob bundles ship as data constants for Phase 183 | ✓ |
| Raw knobs only | Same seam, no named bundles this phase; tests use throwaway configs | |
| Named style enum in engine | selectBotMove takes style: 'attacker' \| ... and maps internally | |

**User's choice:** Raw knobs + style bundles as data (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Absent = untouched code path | Style optional everywhere; undefined runs the exact current code | ✓ |
| Neutral default object | NEUTRAL_STYLE (multipliers 1.0, bonus 0) always flows through the new paths | |

**User's choice:** Absent = untouched code path (Recommended)

---

## Opening books

| Option | Description | Selected |
|--------|-------------|----------|
| Re-weight within ECO | Curated SAN-prefix list + boost via the existing BookWeightingFn seam; menu/exit rules untouched | ✓ |
| Union prefix sets | Extend the menu with style lines outside ECO | |
| Replace ECO per style | Bot only plays its style lines while in book | |

**User's choice:** Re-weight within ECO (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Claude curates from ECO | Per-style white+black lists curated from openings.tsv at plan/execute time; user reviews in UAT | ✓ |
| You hand-pick now | User names specific openings during discussion | |
| Heuristic auto-derive | Programmatic classification of ECO lines by features | |

**User's choice:** Claude curates from ECO (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Strong boost | ~×20–50 multiplier; style lines dominate whenever available | ✓ |
| Soft nudge | ~×3–5; subtler, less perceptible | |
| Deterministic follow | Always play a style-line continuation when one exists | |

**User's choice:** Strong boost (Recommended)

---

## Resign & draw policy

| Option | Description | Selected |
|--------|-------------|----------|
| Policy only, offer UI in 183 | Pure policy functions + wiring now; resignation surfaces now; outgoing-offer UI in Phase 183 | ✓ |
| Full offer UX now | Minimal bot-offers-draw banner in this phase | |
| Bot never offers, ever | Styles differ only in accept-contempt and resign policy | |

**User's choice:** Policy only, offer UI in 183 (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Human rungs never resign | Light/Deep resign on practicalScore threshold with hysteresis; Human rungs play to the end | ✓ |
| Material heuristic for Human rungs | chess.js material-deficit fallback so 800-rung personas can resign | |
| Material heuristic everywhere | One uniform material-based signal for all rungs | |

**User's choice:** Human rungs never resign (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| One contempt knob, two consumers | Single signed value feeds accept gate (draw worth 0.5 − contempt) and Deep-regime score shaping | ✓ |
| Separate accept-band + shaping knobs | Independent params for gate asymmetry and shaping bonus | |
| Accept-gate only | Contempt never affects move choice | |

**User's choice:** One contempt knob, two consumers (Recommended)

---

## Tuning & verification

| Option | Description | Selected |
|--------|-------------|----------|
| Additive spread field on RankedLine | mctsSearch reports child-score spread as a new optional field | ✓ |
| Proxy from existing fields | Approximate sharpness from exported fields | |
| Defer variance to later | Ship score shaping without the variance bonus | |

**User's choice:** Additive spread field on RankedLine (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Unit tests + measurement script | Deterministic tests + Node feature-frequency-shift report into reports/data/ | ✓ |
| Unit tests only | Stubbed distribution tests, no aggregate measurement | |
| Play harness games now | Actual style-vs-baseline games this phase | |

**User's choice:** Unit tests + measurement script (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Claude hand-tunes via the script | Starting constants at execute time, iterated against the measurement script, documented | ✓ |
| Decide magnitudes now | Lock specific numbers in this discussion | |
| Config-file-driven sweep | Mini parameter-sweep mode + grid winners | |

**User's choice:** Claude hand-tunes via the script (Recommended)

---

## Claude's Discretion

- Exact `BotStyleParams` sub-structure and file placement
- Prior-reweighting feature set details and per-style multiplier values
- Resign threshold/hysteresis defaults, draw-offer trigger conditions and cooldowns
- Measurement-script position sampling strategy and N
- Specific curated line lists per style (user reviews in UAT)

## Deferred Ideas

- Bot outgoing draw-offer UI — Phase 183
- Per-persona strength offsets / measured ELO labels — Phase 184
- Personas above 1800 — SEED-114 (dormant)
- Todos reviewed and not folded (keyword-noise matches): 172-deferred-review-findings, bitboard-storage note, WR-01 Tailwind axis label
