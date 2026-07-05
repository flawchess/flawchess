# Phase 151: Maia in the Browser + All-Position Surfaces - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-05
**Phase:** 151-maia-in-the-browser-all-position-surfaces
**Areas discussed:** Layout & placement, Maia WDL bar render, ELO basis / free play, Model size & quality gate

Note: this phase was heavily pre-locked by SEED-081, REQUIREMENTS.md, and spikes 004–006.
Discussion targeted only the genuinely-open HOW decisions. The AGPL relicense (LIC-01),
client-side worker architecture, ephemeral cache, and chart line-cap rule were already decided
and not re-litigated.

---

## Layout & placement — chart home (desktop)

| Option | Description | Selected |
|--------|-------------|----------|
| Below the board | Board-column width; natural reading flow; recommended | |
| Right side panel | Under engine card, ~360px — cramped for an ELO chart | |
| Dedicated tab (desktop) | New desktop tab strip | |
| **3-column: Maia chart \| bar+board \| engine+moves** (user's refinement) | Chart in a left column, human-left / engine-right symmetry | ✓ |

**User's choice:** Custom — "On the left side of the board and Maia Eval bar." Refined via
follow-up to the **3-column** arrangement (Maia chart left column | Maia bar + board + SF bar |
engine + move list right).
**Notes:** User wanted the Maia surfaces grouped on the LEFT (human side) to mirror
engine-on-the-right, matching the product thesis. Accepted trade-off: narrower chart (fewer ELO
ticks) vs a wider below-board chart.

## Layout & placement — chart home (mobile)

| Option | Description | Selected |
|--------|-------------|----------|
| New 'By rating' tab | 4th tab alongside Moves \| Eval \| Tags | |
| Directly below the board | Always visible, competes for vertical space | |
| **New 'Human' tab, order Moves \| Eval \| Human \| Tags** (user's refinement) | 4th tab named "Human" in a specific order | ✓ |

**User's choice:** New **"Human"** tab; explicit order **Moves | Eval | Human | Tags**.
**Notes:** Free-play mobile (no tab strip today) still needs the chart — left as a planning
detail in CONTEXT.md (D-03), not a user decision.

---

## Maia eval bar render

| Option | Description | Selected |
|--------|-------------|----------|
| 3-segment W/D/L stacked | Win/draw/loss segments in WDL brand colors; surfaces draw mass | |
| **Single expected-score fill** | E = W + 0.5·D, one vertical fill mirroring the SF cp bar | ✓ |
| Stacked + expected-score marker | Richest, busier | |

**User's choice:** **Single expected-score fill.**
**Notes:** Clean side-by-side mirror of the Stockfish cp bar. Full WDL vector still computed
(feeds chart + future Phase 152 practical-severity reframe); only the bar is collapsed to E.

---

## ELO basis / free play

| Option | Description | Selected |
|--------|-------------|----------|
| User's rating, else 1500 default (no selector) | Minimal scope | |
| **Interactive ELO selector** | Draggable "you are here"; scouting tool | ✓ |
| Fixed 1500 always | Ignores user's level | |

**User's choice:** **Interactive ELO selector.**
**Notes:** Selector available across modes; defaults to user's color rating-at-game-time (game
mode) / current profile rating else 1500 (free play). Game-mode default rating remains locked to
`white_rating`/`black_rating` (MAIA-04). Ladder range/granularity left to the hands-on ONNX
contract check (provisional ~1100–2000/100).

---

## Model size & quality gate

| Option | Description | Selected |
|--------|-------------|----------|
| **Smallest/simplified + WASM, WebGPU opportunistic** | Ship maia3_simplified.onnx; upgrade gated on VALID-01 | ✓ |
| Commit to 23M up front | ~90MB, no prior measurement | |
| WASM only (no WebGPU) | Skip WebGPU | |

**User's choice:** **Smallest/simplified + WASM baseline, opportunistic WebGPU; upgrade only if
VALID-01 calibration is poor.**
**Notes:** VALID-01 is measure-and-judge (the ephemeral surface is the gate), not a hard
ship-block. Size/latency measured during the phase (MAIA-06).

## Claude's Discretion

- Chart candidate-line color mapping (theme.ts; played + best emphasized) — spike 006 shape.
- `useMaiaEngine` worker hook shape (mirror `useStockfishEngine`), ephemeral cache scope.
- Attribution notice surface (LIC-02).
- ELO ladder range/granularity — confirm against the model's supported range during the hands-on pass.

## Deferred Ideas

- Phase 152: salience×trainability verdict, practical-severity flaw reframe, precision-first withhold.
- v2 (persistence-gated): Pillar C aggregate rollup, `game_flaws` schema + backfill, SEED-082.
- 3-segment W/D/L bar rendering (offered, not chosen) — noted for possible Phase 152 use.
- Reviewed-not-folded todos: bitboard partial-position storage (off-scope, DB); pt-33 Tailwind
  axis-label nit (unrelated chart).
