# Phase 237: Train Reveal Verdict Strip, Line Chips & One Move Tree - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-08
**Phase:** 237-train-reveal-chips-move-tree
**Areas discussed:** Tree & chip navigation, Verdict strip contents, Tour rewrite, Telemetry continuity

---

## Tree & chip navigation

**Chip tap while the board is 4 plies into another line**

| Option | Description | Selected |
|--------|-------------|----------|
| Jump to puzzle position | Board back to root with the tapped arrow lit; list switches (sketch behaviour) | ✓ |
| Jump to the line's first move | Board plays the chip's move | |
| Only switch the list | Board stays put | |

**Best = Game merge**

| Option | Description | Selected |
|--------|-------------|----------|
| Merge any coinciding roles | One chip per distinct first move | ✓ |
| Only merge You | Literal sketch rule | |

**Notes:** Owner: You = Best = Game is impossible; the game move is always a blunder, never the best move.

**Line length**

| Option | Description | Selected |
|--------|-------------|----------|
| Keep 12 plies | Today's `MAX_LINE_PLIES` | ✓ |
| Shorter (8 plies) | Tighter phone fit | |
| Fit to space | Clip to N rows | |

**Root-level fork matching no line**

| Option | Description | Selected |
|--------|-------------|----------|
| Sideline before move 1 | Active chip stays, arrows fade | |
| Deselect all chips | No chip active, list shows only the user's line | ✓ |
| Separate "Yours" row | Sketch variant B | |

---

## Verdict strip contents

**Strip one-line copy**

| Option | Description | Selected |
|--------|-------------|----------|
| D-23 clause + "best" split | Brackets stripped, "best move" when You = Best | |
| Plain D-23 clause | Six existing clauses | |
| Opener + clause | Warmer, truncates sooner | |

**User's choice (free text):** Use the D-23 clause + best/good/decent move.

**Expanded strip contents** (multi-select): user picked "Full bot verdict" only; on a follow-up
("where do Your-call feedback and Also fine go?" — drop / fold into verdict / I meant all of them)
the user chose **I meant all of them**.

**Default state**

| Option | Description | Selected |
|--------|-------------|----------|
| Always collapsed | Keeps no-scroll first view | ✓ |
| Open on 0–1 points | Look-closer visible when it matters | |
| Remember last state | localStorage | |

**Vocabulary scope**

| Option | Description | Selected |
|--------|-------------|----------|
| Everywhere | Strip, expanded verdict, desktop bubble | ✓ |
| Strip line only | Full verdict keeps "right move" | |

---

## Tour rewrite

**Tour structure**

| Option | Description | Selected |
|--------|-------------|----------|
| 6 steps as listed | strip, chips, stepping, board fork + ⏮, understand-don't-memorize, bar | ✓ |
| Merge stepping into chips (5) | Shorter tour | |
| Add a merge step (7) | Separate "You = Best" step | |

**Where the tour copy renders**

| Option | Description | Selected |
|--------|-------------|----------|
| Bubble in the strip's slot | Reuse TrainBotStepper | ✓ |
| Floating coachmark | New anchored popover | |
| Bottom sheet | Collides with the bar step | |

**Strip + tour coexistence** (step 1 spotlights the strip)

| Option | Description | Selected |
|--------|-------------|----------|
| Bubble stacked above strip | Both visible during the tour | ✓ |
| Strip inside the bubble | Fake UI | |
| Drop the strip step | Weaker intro | |

**Defaults accepted:** Claude drafts copy; agent runs browser UAT at 390x844, 375x667, desktop; real-phone tap leg to owner.

---

## Telemetry continuity

**Schema**

| Option | Description | Selected |
|--------|-------------|----------|
| v2: keep what carries, replace cards | Clean `v` boundary, small backend change | ✓ |
| Stay v1, remap silently | No backend change, semantics shift at deploy | |
| v1 + add strip key only | Backend change without the v boundary | |

**Hand-played move on a known line**

| Option | Description | Selected |
|--------|-------------|----------|
| Board move, not a fork | v1 meaning of explore/board moves kept; explored = forked | ✓ |
| Line step only | Counts as › | |
| Both | Increments both | |

**Umami**

| Option | Description | Selected |
|--------|-------------|----------|
| Low-frequency only | strip-expand, ⏮, ×, first fork | ✓ |
| All four from the roadmap | Per chip/step/fork/expand | |
| Counters only | No Umami successors | |

---

## Claude's Discretion

- Late-arriving (loading/failed) lines as chips and branches
- Root-fork reachability after a chip is tapped again
- Tree convention for three root branches vs the single `mainLine`
- Free-play engine lifetime and contention with grading / background search
- Umami target names, v2 key names, eval bar off-line, desktop keyboard details, file split seams
- Retiring `TrainLineStepper` and moving `trainArrows` to per-chip opacity

## Deferred Ideas

None.
