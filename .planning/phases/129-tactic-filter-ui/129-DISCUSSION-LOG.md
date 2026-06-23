# Phase 129: Tactic Filter UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-20
**Phase:** 129-tactic-filter-ui
**Areas discussed:** Depth control form & default, Missed/allowed toggle (placement & scope), Chip display under orientation, Which narration rows surface / stats grid

---

## Depth control form & default

| Option | Description | Selected |
|--------|-------------|----------|
| Difficulty preset buttons | Beginner/Intermediate/Advanced chips mapping to depth bands | partial ✓ |
| Continuous range slider (min–max) | Two-handle range over depth | |
| Single max-depth threshold | One handle, "up to N deep" | partial ✓ |

**User's choice:** "Reuse the pattern and visual style from the opponent strength filter, but with a **single** slider instead of range. Use Beginner/Intermediate/Advanced as presets which set the tactic max-depth slider. The slider can be used to set a specific depth." (= single-handle max-depth slider + preset chips, cloning `OpponentStrengthFilter`.)

| Option (default state) | Description | Selected |
|--------|-------------|----------|
| Off by default (no depth filter) | Empty = all depths, like the family filter | |
| Always-on with a default range | Per 127 D-06; surfaces a band by default | ✓ |

| Option (unit) | Description | Selected |
|--------|-------------|----------|
| "Moves deep" (full moves) | ⌈ply/2⌉ | ✓ |
| Difficulty labels only, no number | | |
| Half-moves (raw ply) | | |

**Follow-ups:** Default preset on load = **Intermediate**. Mates: **always shown regardless of depth (127 D-03), noted in the InfoPopover**.

**Notes:** Band thresholds left to Claude's discretion, calibrated against 127's depth-vs-Rating correlation. A NEW backend depth-filter param is required (none exists in the 128 contract).

---

## Missed/allowed toggle — placement & scope

| Option (placement) | Description | Selected |
|--------|-------------|----------|
| Segmented control atop the Flaws tab | Prominent 2-way view lens | |
| Inside the FilterPanel / drawer | Alongside the narrowing filters | ✓ (refined) |
| Both (segmented + mirrored in drawer) | | |

**User's choice:** "Inside the Tags FilterPanel/drawer, **above the Tactic Motif**. Three options: **Either (default), Missed, Allowed**. Use the same control as the 'Played as' filter." (Tri-state, default Either — overrides SC#2's "default missed".)

| Option (scope) | Description | Selected |
|--------|-------------|----------|
| Whole tactic view (list + chips + grid) | | ✓ (then refined — see Stats grid) |
| List + chips only; grid stays allowed | | |
| Flaw list only | | |

**Notes:** Initially "whole tactic view," later refined: the toggle governs the **Flaws-tab list + chips only**; the stats grid has no toggle and shows both orientations (see Stats grid area). "Either" is a NEW third backend state (OR across both column sets).

---

## Chip display under orientation

| Option (Either chips) | Description | Selected |
|--------|-------------|----------|
| Both chips (labeled missed + allowed) | Show both when both exist | ✓ |
| One chip, allowed wins | | |
| One chip, missed wins | | |

| Option (signal) | Description | Selected |
|--------|-------------|----------|
| Text prefix / verb on the chip | "missed: fork" / "allowed: discovered-attack" | ✓ |
| Style variant (outline vs filled) | | |
| Small leading icon | | |

**User's choice:** Chips include the missed/allowed **prefix in the label**; show both a missed chip AND an allowed chip when both exist. Card narration = chip + definition popover only (no extra sentence).

---

## Which narration rows surface / stats grid

| Option (grid in Either) | Description | Selected |
|--------|-------------|----------|
| Grid anchors to 'allowed' in Either | | |
| Grid shows combined rates | | |
| Grid hidden until Missed/Allowed chosen | | |

**User's choice (reframed the surface):** "The Library **stats page has no tags filter** and therefore **no Either/Missed/Allowed filter**. Each tactic **card shows a Missed AND an Allowed bullet chart** (e.g. the Fork card has 'Missed Fork' + 'Allowed Fork'). Order cards by **Missed** for the top-6 selection. Add a collapsible **'More Tactics'** section for the rest, using the shared collapsible (same as 'Endgame Statistics Concepts')."

| Option (card text) | Description | Selected |
|--------|-------------|----------|
| Chip + definition popover only | | ✓ |
| Chip + short inline sentence | | |

**Notes:** The Flaws list is player-only (`player_only_gate`), so opponent/scouting narration rows don't apply to cards. Grid change requires the comparison endpoint to return both orientation rates per family.

---

## Claude's Discretion
- Exact depth band thresholds (calibrated vs 127 depth-vs-Rating).
- Param name/shape for the depth filter + 3-value orientation enum.
- D-14 top-6-by-Missed ranking detail (tie-break/volume fallback).
- "More Tactics" renderer reuse; theme token reuse (no new orientation tokens).

## Deferred Ideas
- TACMISS-01 standalone-missed detection / scouting view.
- Tactic benchmark zones for the bullet grid.
- Per-card narration sentences / opponent-scouting narration.
- Backend hard-gating behind `beta_enabled`.
- Prod re-backfill (SEED-054 + folded 127/128 classify re-sweep) runbook.
</content>
