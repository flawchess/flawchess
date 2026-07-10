# Phase 156: Board Arrows + Toggles (Free Analysis) - Discussion Log

**Gathered:** 2026-07-06

Human-reference log of the discuss-phase session. Not consumed by downstream agents
(they read CONTEXT.md).

## Phase-note directives (from the user, at invocation)

- Toggles are already built (Phase 155 card switches) → this phase is "just the arrows".
- Reduce clutter: show only the **top** arrow for Stockfish/FlawChess (top-1, not top-2).
- A future engine-settings panel will make the number of arrows configurable.

## Area selection

Presented 4 gray areas; user selected: **Arrow colors**, **Agreement/overlap**,
**Arrow width/emphasis**. Skipped: **Settings-readiness** (defaulted to a single
`ARROW_COUNT` constant, no settings plumbing).

## Q1 — Arrow colors

Options: (a) SF blue reuse + FC amber/gold [new token]; (b) two brand-new tokens;
(c) FC amber + SF teal.
**Selected: (a)** SF reuses `BEST_MOVE_ARROW` blue; FC = new amber `oklch(0.78 0.15 85)`.
→ D-04.

## Q2 — Agreement / overlap (same top move)

Options: (a) FC amber wins on collapse; (b) SF blue wins; (c) keep both, offset.
**User answered via "Other":** don't collapse — **nest concentric arrows** by width so
all layers stay visible. FC largest, SF medium, played-move (white) smallest. Render
order = smallest on top (draw FC → SF → white). → D-05, D-06.

## Q3 — Concrete widths

Options: (a) 0.7/0.5/0.18; (b) 0.8/0.5/0.18; (c) planner tunes.
**Selected: (b)** FC = 0.80, SF = 0.50, white = 0.18. → D-05.

## Deferred / redirected

- Configurable arrow count → constant only now; real settings panel = future milestone.
- Game-review arrows + played-move layer + game-review defaults → Phase 157.

## Claude's discretion (flagged to planner)

- Exact `dedupeArrowsByMove` bypass mechanism for the engine layer (D-06).
- Exact amber value tuning at UAT (D-04).
- Slot position of engine arrows in the `boardArrows` assembly; mobile parity.
