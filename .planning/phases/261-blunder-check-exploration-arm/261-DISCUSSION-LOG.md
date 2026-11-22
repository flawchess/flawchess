# Phase 261: Blunder-Check Exploration Arm (SEED-261121-t50) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-22
**Phase:** 261-blunder-check-exploration-arm
**Areas discussed:** Feedback display and copy, "Hard to catch" cut, Type line rule details

The session started with the re-measurement the roadmap asks for (prod, Phase 259 score); the numbers are in
CONTEXT.md under Specifics. Offered but not selected: "Record, script, acceptance".

---

## Feedback display and copy

### How the score is shown

| Option | Description | Selected |
|--------|-------------|----------|
| Library Facepalm chip | Reuse the chip from the Flaws card: percent, level color, popover | ✓ |
| Plain sentence | "Facepalm score: 34%." No color, no popover | |
| Chip plus sentence | A sentence that embeds the chip | |

### Placement

| Option | Description | Selected |
|--------|-------------|----------|
| After the verdict | A second short paragraph under the points sentence | ✓ |
| Before the verdict | Type line and score first, then the points sentence | |
| Merged into the sentence | "Nxe6 was a blunder that allows a material loss." | |

### Which windows

| Option | Description | Selected |
|--------|-------------|----------|
| Every blunder window | Caught or missed, both arms, whenever a snapshot exists | ✓ |
| Only below the main cut | Feedback only when the snapshot is under 0.70 | |

**User's choice:** the recommended option in all three.

---

## "Hard to catch" cut

### Cut

| Option | Description | Selected |
|--------|-------------|----------|
| Below 50% | Caught rate drops clearly only below 0.5; fires on about 10% of all blunder windows | ✓ |
| Below 70% | Everything the main arm would not serve; 0.5 to 0.7 was caught 48% | |
| Below 30% | Only the bottom band | |

### Wording

| Option | Description | Selected |
|--------|-------------|----------|
| Keep both as written | "This one was hard to catch." / "Well spotted, this one was hard to catch." | ✓ |
| Keep, but soften | "This one was probably hard to catch." | |

### False alarm before a low-score blunder

| Option | Description | Selected |
|--------|-------------|----------|
| No, nothing shown | The false-alarm solution never reveals an unreached blunder | ✓ |
| Discuss | | |

**User's choice:** the recommended option in all three.

---

## Type line rule details

### Which depth decides the swing of at least 2

| Option | Description | Selected |
|--------|-------------|----------|
| Deepest settled depth | The swing must still stand where the stored line ends | ✓ |
| Any depth (peak swing) | Fires on temporary swings too | |
| Depth 3 only | The immediate tactic only | |

**User's choice (free text):** "Phase 259 changed the material balance algorithm to a quiet rule, which probably
corresponds with your deepest settled depth. So this sounds fine"
**Notes:** Clarified in the session: the quiet rule decides how each depth is read; "deepest settled depth" is
the choice of which odd depth (1 to 9) the type line uses. Recorded as the last odd depth the stored line still
covers, reusing the Phase 259 walk.

### Mate wording

| Option | Description | Selected |
|--------|-------------|----------|
| The stored line reaches mate | The walked line ends in checkmate | ✓ |
| Engine says forced mate | Any forced mate by eval, also beyond the stored line | |
| Mate within depth 3 only | Only the mates the score treats as MATE_LOSS | |

### Chip popover in the drill

| Option | Description | Selected |
|--------|-------------|----------|
| Score meaning only | The popover does not name the facepalm type | ✓ |
| Same as the library | Popover names the type as the Flaws card does | |

---

## Claude's Discretion

- Record, script and acceptance (not selected): NULL arm for pre-phase windows, snapshot on both arms, Wilson
  intervals by arm and `is_own`, a seeded test plus a prod count for the 20% share. Accepted with "I'm ready for
  context".
- Column names and encodings, the wiring of the draw into the pools, the wire schema change.

## Deferred Ideas

- The one-tap "unfair" flag, a fit on user answers, review gates for the arm (all from the seed).
