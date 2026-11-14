# Phase 253: Facepalm Score in the Library UI (SEED-261114-0ke) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-14
**Phase:** 253-facepalm-score-library-ui
**Areas discussed:** Filter control shape, Narrowed-range behavior, Chip placement and color, Popover copy

---

## Filter control shape

### Presets

| Option | Description | Selected |
|--------|-------------|----------|
| Presets + slider | Same look as Tactic Depth (PresetRangeFilter with chips) | ✓ |
| Slider only | No chips; needs a no-presets variant | |

### Preset set

| Option | Description | Selected |
|--------|-------------|----------|
| All / Low / High at the drill cut | Low 0-69, High 70-100, cut shared with FACEPALM_SCORE_MIN | |
| All / Low / Mid / High | 0-100, 0-29, 30-69, 70-100 | ✓ |
| All / High only | Two chips | |

### High cut

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed 30 / 70 | Plain UI constants, independent of the drill | ✓ |
| High follows the drill cut | High = FACEPALM_SCORE_MIN to 100 | |

**User's choice:** Free text: "I'd use stable cutoffs at thirds: 33% and 66%", then "ok, keep 30% and 70%".
**Notes:** Stable cutoffs were the point; thirds do not land on a 5% grid.

### Step

| Option | Description | Selected |
|--------|-------------|----------|
| 5% | 21 stops; upper handle covers its 5% bucket (Low stores 0-25, matches < 30) | ✓ |
| 1% | Exact inclusive bounds, fiddly on touch | |
| 10% | Coarsest | |

---

## Narrowed-range behavior

### Severity toggles

| Option | Description | Selected |
|--------|-------------|----------|
| Leave them alone, show a hint | One-line note under the slider while narrowed | ✓ |
| Dim the Mistakes toggle | Coupled disabled state | |
| Nothing extra | Info popover only | |

### Panel position

| Option | Description | Selected |
|--------|-------------|----------|
| Right under Flaws | Next to the severity toggles | ✓ |
| After Best Moves, before Tactic Depth | Two sliders stacked | |
| Below the tactic section | Before the context tags | |

### Hint text

| Option | Description | Selected |
|--------|-------------|----------|
| "Only your scored blunders are shown." | Says what remains | |
| "Mistakes and unscored blunders are hidden." | Says what dropped out | |
| You decide | Leave to planning | |

**User's choice:** Free text: "Mistakes are excluded".
**Notes:** "basically all blunders will be scored after phase 252 and 250 finishes", so unscored blunders are not
mentioned.

---

## Chip placement and color

### Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Row 1, right after the severity badge | "Blunder, Facepalm 94%" | ✓ |
| Row 1, after the tactic chips | Trails the row | |
| Row 2, with the context tags | Mixed with tags | |

**User's choice:** Free text, two steps: first "as a separate line under the engine eval drop line", then "I
realized that there's no room for a new metadata line. Put the facepalm score in a chip next to the blunder chip".
**Notes:** A styling question for the metadata-line variant was asked and withdrawn with it.

### Chip color

| Option | Description | Selected |
|--------|-------------|----------|
| Neutral | Muted text, neutral pill, same for every value | ✓ |
| Blunder red, same as the badge | Reuses SEV_BLUNDER colors | |
| Graded by band | Tint changes at 30 and 70 | |

### Explainer

| Option | Description | Selected |
|--------|-------------|----------|
| Tap the chip | Chip is its own popover trigger | ✓ |
| Entry in the shared legend | Chip inert, legend explains | |
| Both | Text in two places | |

---

## Popover copy

### Chip copy

| Option | Description | Selected |
|--------|-------------|----------|
| Obvious / hard to see | "How obvious this blunder was for a player at your level, as judged by our model. High means a careless slip, low means it was hard to see. Not a probability." | ✓ |
| Careless scale | 0-100 scale framing | |
| Shortest | One sentence, no "not a probability" | |

### Filter copy

| Option | Description | Selected |
|--------|-------------|----------|
| Chip text plus how the filter works | Definition, presets, "Any range other than All shows blunders only." | ✓ |
| Filter behaviour only | No definition | |
| Add the drill link | Plus a sentence on the Blunder Check drill | |

---

## Claude's Discretion

- Percent rounding (whole percent, rounded down), offered at the area check without objection.
- Summary format, filter-store fields, active dot, URL/persistence (follow Tactic Depth).
- Umami event names, test ids, neutral chip tokens, API param names and units.

## Deferred Ideas

- Facepalm rate stats and opponent scoring (SEED-261114-iuv).
- High preset tied to the drill cut; drill mention in the filter popover.
