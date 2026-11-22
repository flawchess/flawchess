# Phase 260: Facepalm as a First-Class Move Quality - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-22
**Phase:** 260-Facepalm as a First-Class Move Quality
**Areas discussed:** Blunder vs Facepalm row, Facepalm filter button, Desktop card height, Chart dots and emphasis

---

## Blunder vs Facepalm row

| Option | Description | Selected |
|--------|-------------|----------|
| Split | Blunder row = "??" moves only, Facepalm row = "???" moves; disjoint like Best vs Gem / Great | ✓ |
| Overlap | Blunder row keeps the full Lichess count, Facepalm is a subset counted twice | |

**User's choice:** Split.

| Option | Description | Selected |
|--------|-------------|----------|
| Definition + one sum sentence | Facepalm definition; "blunders and facepalms together match the Lichess blunder count" | ✓ |
| Definition only | Leave the Lichess sentence untouched | |
| Reword Blunder too | Blunder definition also says it was not an easy one to see | |

**User's choice:** Definition + one sum sentence.
**Notes:** Facepalm is the last row after Blunder, same in the compact row and on /analysis; unscored
blunders stay in Blunder. Accepted without further questions.

---

## Facepalm filter button

| Option | Description | Selected |
|--------|-------------|----------|
| Shortcut onto the slider | Button sets the High preset; one state, no API change | first pick, withdrawn |
| Own flag, independent of slider | Separate on/off filter with its own API parameter | |
| Button replaces the High chip | Same single state, the slider loses its High chip | |

**User's choice:** Shortcut at first. Then the owner stopped the follow-up question about Mistakes: tags in
the same section combine with OR, so Mistakes and Facepalm selected together should list both, which a
shortcut onto the score range cannot do.

Claude then offered A (Facepalm as a real third OR value in the row, backend change) and B (no button in
the row; mark the High preset).

**User's choice:** B. Put the "???" icon on the High preset. Treat the Facepalm Score range as part of the
Flaws section, applying to blunders only and not to mistakes. Example: Blunders + Mistakes with the Low
range lists blunders with a low score plus all mistakes.

| Option | Description | Selected |
|--------|-------------|----------|
| Option 1 | Mistakes pass through only when Mistakes is explicitly selected; an empty row with a narrowed range lists blunders in range only | ✓ |
| Option 2 | Strict "empty = both": an empty row with a narrowed range lists blunders in range plus all mistakes | |

**User's choice:** Option 1.
**Notes:** Needs a small backend change in the shared flaw clause builder, so the phase is no longer
frontend only. The hint "Mistakes are excluded" and the popover line "shows blunders only" must change.

---

## Desktop card height

| Option | Description | Selected |
|--------|-------------|----------|
| Tighter rows, same height | Drop the row padding so 8 rows fit under the 225px board (Claude's recommendation) | |
| Let the card grow | Card about 24px taller than the board | |
| Grow the miniboard too | Keep the row spacing and enlarge the board so both end level | ✓ |

**User's choice:** Grow the miniboard too.

---

## Chart dots and emphasis

| Option | Description | Selected |
|--------|-------------|----------|
| Ring what the filter covers | Blunders at All rings Blunder and Facepalm; a narrowed range rings the cells it reaches | ✓ |
| Severity only, as today | The range never affects the ring | |
| Only the "???" High preset rings Facepalm | Blunders rings Blunder only | |

**User's choice:** Ring what the filter covers.
**Notes:** Chart defaults stated by Claude and accepted with "I'm ready for context": every facepalm
blunder dot is dark red (`SEV_FACEPALM`, both sides), its tooltip shows "???", and cell cycling highlights
only the matching dots.

---

## Revision after the areas closed (same session)

The owner reopened the filter decision: add a separate Facepalms tag and drop the Facepalm Score range
filter. Blunders would list blunders below the cut, Facepalms those at or above it, both together all
blunders, matching the move quality list and the Gem / Great tags. Named downside: no filter for very
hard-to-see flaws.

Claude first argued from Umami usage of the range filter. The owner rejected that: the score had just been
added, and the question must be settled from first principles, not preliminary data. Claude's first-
principles case for the tag model: the control should not be finer than the measurement; the app already
treats such quantities as categories (Gem / Great, severities); a hard-to-see blunder is the unremarkable
case; the loss is the 0 to 30% vs 30 to 70% separation only; the change is cheap to undo.

| Option | Description | Selected |
|--------|-------------|----------|
| Three OR tags, no range filter | Blunders, Mistakes, Facepalms; remove the slider | ✓ |
| Keep the earlier outcome | "???" on the High preset; range applies to blunders only | |

**User's choice:** "Confirmed, switch to tags and remove the backend parameters too."
**Notes:** The parameter removal is the last plan, after Phase 259 has merged. The filter ring simplifies to
"ring the cells whose tags are selected".

**Follow-up from the owner:** relabel the flaw filter tags to the singular, consistent with Gem / Great:
Facepalm, Blunder, Mistake. Recorded as the label set and the order (the order is Claude's reading of the
list as written).

---

## Claude's Discretion

- Wording of the popover and hint copy.
- Placement of the "???" icon on the High preset chip.
- The wire name and type of the facepalm filter value.
- Type shape for the 8th category and for a multi-cell ring.

## Deferred Ideas

- A filter for very hard-to-see blunders, lost with the range filter.
