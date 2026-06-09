# Phase 112: Flaws Subtab Card Rework - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** 112-flaws-subtab-card-rework
**Areas discussed:** Eval swing presentation, Grid responsiveness, View-game trigger surface, Modal mechanics + states, game_flaws schema (raised by user mid-discussion)

---

## Eval swing presentation

Initially framed as ES (expected-score) formatting. The user redirected: use Stockfish
eval at 1-decimal precision via the inverse-sigmoid helper in `tagDefinitions.ts`, then
redirected again: don't round-trip through ES at all — read `eval_cp`/`eval_mate` from
`game_positions` to preserve mate-in-N.

| Option | Description | Selected |
|--------|-------------|----------|
| Before → after pair | Both evals shown; mover/user POV; shows whether you were winning + how far you fell | ✓ |
| Single delta (pawns) | One number (after − before); compact but conflates the nonlinear scale | |

**User's choice:** Before → after pair, sourced from `eval_cp`/`eval_mate` (not ES).
**Notes:** Key insight from the user — ES saturates near ±1, so mate vs +9 collapse to
the same number; raw eval preserves mate. Display is user-POV (negate white-POV storage
for black). Reuse a formatter extracted from `EvalChart.formatEval`.

---

## Grid responsiveness

| Option | Description | Selected |
|--------|-------------|----------|
| 1 → 2-up (lg+) | `grid-cols-1 lg:grid-cols-2`; ~600px/card on a 1280 desktop; never 3-up | ✓ |
| 1 → 2 → 3-up (2xl) | Adds 3-up at ≥1536px | |

**User's choice:** 1 → 2-up at `lg`.
**Notes:** Supersedes the original "2 or 3 columns" framing from the explore session.

---

## game_flaws schema (user-raised)

User asked whether `es_before`/`es_after` columns are still needed once eval is displayed,
then extended it to `move_san`.

| Option | Description | Selected |
|--------|-------------|----------|
| Swap ES → eval columns | Store `eval_cp/eval_mate` before/after in `game_flaws`; self-contained read | |
| Drop ES, join game_positions | Drop ES with no replacement; read eval via join at list time | ✓ |

**User's choice:** Drop ES (and `move_san`); join `game_positions`. Keep `fen`.
**Notes:** Leaner table preferred over denormalization — `(game_id, ply)` is indexed and
a page is 20 flaws, so the join is negligible. `move_san` rides on the same joined row.
`fen` stays because `game_positions` has no FEN column (hashes only). Eval-join offset
flagged as a regression-guard pitfall.

---

## Modal mechanics + states

| Option | Description | Selected |
|--------|-------------|----------|
| Dialog desktop + Drawer mobile | Two paths, best per-device fit | |
| One responsive Dialog (both) | Single path; caveat re: overflowVisible tooltip clipping | ✓ |
| Drawer (both) | Consistent with filter drawers; less desktop width | |

**User's choice:** One responsive Dialog.
**Notes:** Loading = spinner, error = shared `LoadError` (locked by convention, not asked).

---

## View-game trigger surface

| Option | Description | Selected |
|--------|-------------|----------|
| 'View game' button only | Clean, accessible; avoids click-target conflicts | ✓ |
| Button + miniboard click | Two affordances; board needs role/aria/keyboard | |
| Whole card clickable | Conflicts with inner interactive elements | |

**User's choice:** 'View game' button only.

---

## Platform link

| Option | Description | Selected |
|--------|-------------|----------|
| Keep in header + add View game | Exact-ply external deep-link + in-app modal (two destinations) | ✓ |
| Drop it, View game only | Loses the exact-ply deep link | |

**User's choice:** Keep exact-ply platform link in header + add View game button.

---

## Claude's Discretion

- "View game" button label/icon/placement; spinner vs skeleton; `Dialog` max-width;
  metadata ordering within the content stack; `data-testid`/ARIA naming.

## Deferred Ideas

- Modal auto-scrub/highlight to the specific flaw's ply (needs a controlled-ply prop on
  the standalone `LibraryGameCard`). Default this phase: no auto-scrub.
