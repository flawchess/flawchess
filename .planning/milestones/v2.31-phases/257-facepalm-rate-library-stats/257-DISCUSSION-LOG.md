# Phase 257: Facepalm Rate in the Library Stats (SEED-261114-iuv) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-20
**Phase:** 257-facepalm-rate-library-stats
**Areas discussed:** Chip tint scope, Vs-opponents placement and unit, Row names and copy

Offered but not selected: Share chart floor and look (left to Claude's discretion).

---

## Chip tint scope

### Which surfaces get the type tint?

| Option | Description | Selected |
|--------|-------------|----------|
| All three | Flaws-card chip, analysis move-list mini-chip, eval chart tooltip line | ✓ |
| Both chips, not the tooltip | Tooltip line stays as it is | |
| Flaws-card chip only | Analysis surfaces keep the neutral chip | |

### Is the type named in words?

| Option | Description | Selected |
|--------|-------------|----------|
| Named in the popover | Chip text unchanged; the explanation gains a type line | ✓ |
| Named on the chip | Chip reads "Missed win 94%" / "Allowed loss 94%" | |
| Colour only | No wording change | |

### Which chips are tinted?

| Option | Description | Selected |
|--------|-------------|----------|
| Every scored blunder | Every chip is teal or crimson; the neutral chip disappears | ✓ |
| Only at or above 70% | Chips below the stats cut stay neutral | |

**User's choice:** the recommended option each time.
**Notes:** none.

---

## Vs-opponents placement and unit

### Where do the three rows sit?

| Option | Description | Selected |
|--------|-------------|----------|
| New card in You vs. your opponents | "Facepalm blunders" card next to the context-tag cards | ✓ |
| In Flaw Stats, under the share chart | Everything facepalm in one place | |
| Own section | Fourth section holding chart and rows | |

### Unit

| Option | Description | Selected |
|--------|-------------|----------|
| Per 100 moves | Same unit and paired normalisation as the neighbouring rows | ✓ |
| Per game | As the seed says | |
| Per 100 games | Like the Tactic motifs section | |

**Notes:** this overrides the seed's "per game" wording.

### Rows without a benchmark band

| Option | Description | Selected |
|--------|-------------|----------|
| Neutral bar, no verdict | No band, no red/green; verdicts come with SEED-261120-bzq | ✓ |
| Colour on significance alone | Red/green when the 99% CI excludes 0 | |
| Numbers only, no bar | Plain "You x · Opponents y" line | |

---

## Row names and copy

### Per-type row labels

| Option | Description | Selected |
|--------|-------------|----------|
| Missed wins / Allowed losses | Named after what is counted; blindness terms not used in this phase | ✓ |
| Type name, blindness in the hint | Terms introduced in the hint line | |
| Chance blindness / Threat blindness | Rows carry the bias names | |

### Hint wording style

| Option | Description | Selected |
|--------|-------------|----------|
| Names the 70% cut | "Blunders with a facepalm score of 70% or more" etc. | ✓ |
| Plain words, no number | "Blunders that should have been easy to see" etc. | |

### How far may the copy interpret?

| Option | Description | Selected |
|--------|-------------|----------|
| State the comparison only | No cause, no reading aid; says there is no typical range yet | ✓ |
| Add a neutral reading aid | One sentence on how to read it, no cause | |
| Mention possible causes | Time trouble or lapses in focus | |

---

## Claude's Discretion

- Share chart floor and look: 10-game window floor plus at least 20 scored blunders in the window, percent axis
  fitted to the data, same volume bars and caption as the Flaws Timeline, title "Facepalm share of blunders".
  Announced at the final check; the owner chose "I'm ready for context".
- Payload shape (existing responses vs new endpoint), card position, opponent popover wording, type field shape,
  event targets and testids.

## Deferred Ideas

- Benchmark zones, verdict colours, chance / threat blindness as named readings, within-player bias, clock
  matrix, training weighting: SEED-261120-bzq.
