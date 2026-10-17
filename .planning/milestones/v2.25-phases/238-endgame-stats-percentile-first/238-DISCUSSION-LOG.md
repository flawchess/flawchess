# Phase 238: Endgame Stats Percentile-First Redesign - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-11
**Phase:** 238-endgame-stats-percentile-first
**Areas discussed:** Filters on Stats tab, Missing-percentile states, Ranked-sample scope, TC switch behavior

---

## Filters on Stats tab

| Option | Description | Selected |
|--------|-------------|----------|
| Stats ignores filters | Every section reads the ranked sample; filters only on Games tab | ✓ |
| Filters drive timelines only | Ranked sections ignore filters, timelines/Type table follow them | |
| Filtered fallback | Non-default filters show filtered values without percentiles | |

| Timelines sample | Description | Selected |
|--------|-------------|----------|
| Ranked sample, per TC | Same games as the cards, follows TC switch | ✓ |
| All rated human games | Full history, labelled exception | |
| Leave as-is | Filtered timelines | |

| Panel UI | Description | Selected |
|--------|-------------|----------|
| Disabled + explainer | Greyed controls with one-line note | |
| Hidden on Stats | Sidebar / mobile button disappear on Stats | ✓ |

| Shelly | Description | Selected |
|--------|-------------|----------|
| One report per user | Drop filter reset + per-filter cache | ✓ |
| Keep per-filter caching | Only payload numbers change | |

## Missing-percentile states

| Below floor | Description | Selected |
|--------|-------------|----------|
| Show values, 'not ranked' bar | TC in switch, "Not enough games to rank yet (18 of 30)" | ✓ |
| Hide the TC | Drop from switch | |
| Disabled in switch | Visible, not selectable | |

| No ranked TC | Description | Selected |
|--------|-------------|----------|
| Values without ranking | Per-TC not-ranked slots; empty state only at 0 qualifying games | ✓ |
| Empty state only | Explainer card until a TC reaches 30 | |

| Stage B pending | Description | Selected |
|--------|-------------|----------|
| Pending card state | Muted "analyzing" line, layout kept | ✓ |
| Hide until ready | Cards appear later | |

## Ranked-sample scope

| Type table | Description | Selected |
|--------|-------------|----------|
| Ranked sample per TC | Whole tab one sample | ✓ |
| All rated human history | More games, labelled exception | |

| Snapshot | Description | Selected |
|--------|-------------|----------|
| Persist together | Stage A/B store value components with the percentile | |
| Compute values on read | Fresh values, stored percentile may lag | ✓ |
| You decide | Planner picks | |

| ELO band | Description | Selected |
|--------|-------------|----------|
| Keep band, switch sample | Only data source changes | ✓ |
| Grey it too | Align with grey bands | |

**Follow-up (drift handling):** user free text: "Don't worry about it, the percentiles are recomputed very quickly on import." No drift UI.

## TC switch behavior

| Default TC | Description | Selected |
|--------|-------------|----------|
| Most-played in ranked sample | Ties to faster TC, prefer above-floor | ✓ |
| Most recently played TC | Follows current play | |

| Persist | Description | Selected |
|--------|-------------|----------|
| Remember across visits | localStorage, fallback to default | ✓ |
| Session only | | |
| Never | | |

| TC list | Description | Selected |
|--------|-------------|----------|
| TCs with ≥1 ranked game | Zero-game TCs omitted | ✓ |
| Always all four | Empty TCs selectable | |

## Claude's Discretion

- Plan split, state/copy details, endpoint and schema shape, TC-switch store, per-metric CI/p-value applicability.

## Deferred Ideas

- Removing the dot-plot card later; value-axis percentile strips; ELO Timeline band restyle.
