# Phase 159: FlawChess Engine policy temperature + root-move findability (SEED-085) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-07
**Phase:** 159-flawchess-engine-policy-temperature-root-move-findability-se
**Areas discussed:** Findability mechanism, Temperature scope, Slider UX, Verdict copy gating

---

## Findability mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Saturating soft floor | Rank by min(1, P_you/P_ref)^β · V with ELO-scaled P_ref; modal move can't be boosted above its V | ✓ |
| Raw P^β·V | User's initial lean; narrow position-dependent β window, risks promoting high-probability mistakes | |
| Hard floor | Rank by V over moves with P_you ≥ floor(ELO); cliff effects, needs empty-set fallback | |

**User's choice:** Saturating soft floor, with β simplified to a fixed 1 (Claude's suggestion after the user asked which of soft-floor vs hard-floor was simpler).
**Notes:** User initially leaned toward raw P^β·V and asked for the issues. The numeric analysis (in the 600-ELO case, keeping Rxf2 down while sinking Nb5 needs β ∈ ~(0.15, 0.25) — a knife's edge) moved them off it. User then hesitated between saturating soft floor and hard floor ("don't want to overcomplicate"); recommendation went to saturating-with-β=1 as the actually-simpler option (no empty-set fallback branch, smooth behavior under live slider drags). Explicitly locked.

| Option | Description | Selected |
|--------|-------------|----------|
| Cases + rough anchors | Lock 3 regression cases + rough anchors (P_ref ≈10% @600 → ~0 by ~2200) | |
| Fully Claude's discretion | Only the 3 regression cases locked; anchors/shape free | ✓ |
| Pin exact numbers now | Decide exact per-ELO values in discussion | |

**User's choice:** Fully Claude's discretion for the P_ref(ELO) curve.

| Option | Description | Selected |
|--------|-------------|----------|
| V badge, no marker | Badge keeps practical score V; ordering silently weighted | ✓ |
| Subtle 'hard to find' hint | Marker on below-P_ref moves | |
| Show the weighted score | Badge shows rank score instead of V | |

**User's choice:** V badge, no marker.

---

## Temperature scope

| Option | Description | Selected |
|--------|-------------|----------|
| Self only | Flattens only the user's policy; monotone 'model my fallibility' dial | ✓ |
| Both sides | Global humanness dial; effects partially cancel (fallible opponent favors sharp moves) | |
| Two knobs | Separate self/opponent temperatures | |

**User's choice:** Self only.

| Option | Description | Selected |
|--------|-------------|----------|
| Search + findability only | Adjusted P feeds MCTS + findability factor; chart stays raw | ✓ |
| Everything including chart | Chart reshapes with the slider | |
| Search only | Findability reads raw P (contradicts SEED-085) | |

**User's choice:** Search + findability only.

| Option | Description | Selected |
|--------|-------------|----------|
| Before truncation | T>1 genuinely widens the searched candidate set | ✓ |
| After truncation | Candidate set fixed by raw policy; T only reweights | |
| You decide | Planner picks | |

**User's choice:** Before truncation.

---

## Slider UX

| Option | Description | Selected |
|--------|-------------|----------|
| 0.5–2.0 log-symmetric | 1.0 at visual center, halve/double equidistant | ✓ |
| 0.5–2.0 linear | 1.0 off-center | |
| Wider (0.25–4.0) | More headroom, mostly-useless extremes | |

**User's choice:** 0.5–2.0, log-symmetric.

| Option | Description | Selected |
|--------|-------------|----------|
| Plain-language endpoints | 'Play style'/'Fallibility' label, 'Sharper' ↔ 'More human' captions, subtle numeric T | ✓ |
| 'Temperature' + number | Technical name | |
| Endpoints only, no number | No numeric value anywhere | |

**User's choice:** Plain-language endpoints.

| Option | Description | Selected |
|--------|-------------|----------|
| Session-only | Default 1.0 each load; matches ELO slider behavior | ✓ |
| localStorage | Sticky across sessions | |

**User's choice:** Session-only.

---

## Verdict copy gating

| Option | Description | Selected |
|--------|-------------|----------|
| Relative + plotted | P(FC pick) > P(SF best) by named margin AND pick in chart's plotted set | ✓ |
| Relative only | Probability comparison regardless of chart visibility | |
| Absolute threshold only | P(FC pick) ≥ floor | |

**User's choice:** Relative + plotted.

| Option | Description | Selected |
|--------|-------------|----------|
| Claim only what's backed | Fallback prose: nearly as good / safer follow-ups, no findability claim | ✓ |
| Generic neutral copy | One catch-all sentence | |
| You decide | Claude drafts during planning | |

**User's choice:** Claim only what's backed.

| Option | Description | Selected |
|--------|-------------|----------|
| Raw Maia at selected ELO | Same distribution the chart displays; exact non-contradiction | ✓ |
| Temperature-adjusted | Consistent with the engine's ranking but can contradict the raw chart at T≠1 | |

**User's choice:** Raw Maia at selected ELO.

---

## Claude's Discretion

- P_ref(ELO) anchors and interpolation shape (only the 3 regression cases are locked)
- Temperature transform (p^(1/T) renormalized or equivalent) and pipeline placement (provider vs search layer)
- Named hard cap on root candidates under extreme flattening
- Slider styling/step count (follow ELO slider look; desktop + mobile)
- Verdict gate margin constant and fallback wording (popover-copy-minimalism norm)
- ROOT_PRIOR_FLOOR left as-is unless research finds a reason to touch it
- Test strategy (vitest, pure lib functions)

## Deferred Ideas

- Two-track "findable vs ideal" arrows / teaching surface (rated below chosen approach in SEED-085)
- Per-side temperature knobs for time-pressure modeling (SEED-082 vision)
- Played-move vs recommended comparison (SEED-086)
- "Hard to find" marker on demoted-but-shown FC moves
- Reviewed todos, not folded (keyword false-positives): bitboard storage for partial-position queries; WR-01 Tailwind score-axis label
