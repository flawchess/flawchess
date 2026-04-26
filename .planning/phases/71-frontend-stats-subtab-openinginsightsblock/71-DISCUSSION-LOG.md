# Phase 71: Frontend Stats subtab — `OpeningInsightsBlock` - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 71-frontend-stats-subtab-openinginsightsblock
**Areas discussed:** Section layout & ordering, Bullet template & rendering, Deep-link target & candidate-move highlight

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Fetch trigger & filter gating | Auto-fetch on every filter change vs Generate button. Lock loading/error/empty UX. | |
| Section layout & ordering | How to present the 4 sections; behavior when `color` filter narrows. | ✓ |
| Bullet template & rendering | Exact bullet copy, what to surface inline (severity, opening name, counts, PGN format). | ✓ |
| Deep-link target & candidate-move highlight | How click navigates to Move Explorer; how candidate gets highlighted. | ✓ |

**Notes:** "Fetch trigger" was not explicitly selected, but Claude locked the auto-fetch default with skeleton/error states matching `EndgameInsightsBlock` (minus Generate button and rate-limit branch) — see CONTEXT.md D-11 / D-12 / D-16.

---

## Section Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Stacked vertically by section | Four sequential subheadings: White Weak → Black Weak → White Strong → Black Strong. | ✓ |
| Grouped by color, weak→strong | Two color groups, each with weak then strong inside. | |
| Grouped by classification, all-weak first | Two classification groups: all weaknesses (both colors) first, then strengths. | |
| 2×2 grid (desktop only) | Side-by-side grid; collapses to vertical stack <lg breakpoint. | |

**User's choice:** Stacked vertically by section.

---

## Color Filter Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Hide off-color sections entirely | Narrowing color filter collapses off-color sections out of view. | |
| Keep all four, render off-color empty | Always render all four headers; off-color shows "no findings" line. | |
| Collapse off-color into accordion | Off-color collapses to one-line accordion trigger. | |
| Ignore the color filter entirely | Block always shows both colors regardless of color filter; deep-link click updates the color filter. | ✓ (free-text) |

**User's choice:** "Ignore the color filter and always show both colors. When clicking on a deep link, the color filter will update."
**Notes:** Means the block always sends `color="all"` to the backend regardless of `filters.color`, and deep-link click updates the global color filter to `finding.color` as part of the navigation flow.

---

## Bullet Content

| Option | Description | Selected |
|--------|-------------|----------|
| Roadmap exemplar verbatim | Full move sequence from move 1, no opening name, no counts. | |
| Add opening name + ECO | Prepend "Sicilian, Najdorf (B90)" line; full move sequence. | |
| Add opening name + W/D/L breakdown | Opening name + full counts chip. | |
| Compact one-liner | Drop move sequence; just opening name + rate. | |
| **Custom: opening name + ECO + last 2 plys + minimap** | User-driven combination. | ✓ (free-text) |

**User's choice:** "Add opening name + ECO, but show only the last 2 plys of the sequence. Also include a minimap of the position."
**Notes:** Triggered re-asking with clarification questions about minimap rendering and trim semantics. Resolved to: opening name + ECO line, 3-ply trim (last 2 entry plys + candidate), inline always-visible 64–80px minimap.

---

## Minimap Rendering (clarification)

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse `MinimapPopover` (hover/tap) | 180px popover anchored to cursor; existing pattern from `MostPlayedOpeningsTable`. | |
| Inline always-visible thumbnail | ~64–80px non-interactive board rendered inline at the start of each bullet. | ✓ |
| Both: tiny inline + hover for full size | 40–48px inline thumbnail acts as trigger; hover/tap expands to 180px popover. | |

**User's choice:** Inline always-visible thumbnail.

---

## Move Trim (clarification)

| Option | Description | Selected |
|--------|-------------|----------|
| Last 2 plys including the candidate | "...cxd4 4.Nxd4" (2 plys total). | |
| Last 2 entry plys + candidate (3 plys) | "...3.d4 cxd4 4.Nxd4" (with leading ellipsis). | ✓ |
| Last 4 plys (full move pair + candidate) | "...2.Nf3 d6 3.d4 cxd4 4.Nxd4". | |

**User's choice:** Last 2 entry plys + candidate (3 plys).

---

## Severity & Counts Rendering

| Option | Description | Selected |
|--------|-------------|----------|
| Color shade for severity, counts as `n=18` only | Major dark, minor light; compact `(n=18)`. | ✓ |
| Color shade + W/D/L breakdown chip | Same color shading + small `W 3 / D 4 / L 11` chip. | |
| Color shade + tooltip with W/D/L | Inline shows `(n=18)`; tooltip on count reveals breakdown. | |

**User's choice:** Color shade for severity, counts as `n=18` only.

---

## Candidate-Move Highlight on Arrival

| Option | Description | Selected |
|--------|-------------|----------|
| Set `hoveredMove` to candidate SAN (sticky) | Reuses existing `isHovered` arrow shading; sticky until interaction. | |
| Dedicated "pinned" arrow style | New state field with distinct visual style (dashed/gold/pulsing). | |
| Pulse/flash on arrival, then revert | CSS animation for ~2s, then back to default. | |
| **No special highlight; bullet context is enough** | Just navigate; the entry position + bullet's SAN sequence is sufficient context. | ✓ (free-text "3") |

**User's choice:** "3" → No special highlight on arrival.
**Notes:** Trimmed SAN sequence on the bullet plus the entry position is enough — the user clicked the bullet, they know what they're looking for.

---

## Filter Set on Deep-Link Click

Locked without re-asking based on existing `handleOpenGames` pattern (Openings.tsx:492-498):
- `color = finding.color`
- `matchSide = 'both'`
- `boardFlipped = (finding.color === 'black')`
- recency / timeControls / platforms / rated / opponentType / opponentStrength preserved

User confirmed via "tell me if you want anything different" + no objection.

---

## Claude's Discretion

- File and module layout (component path, hook path, helper path).
- Exact thumbnail size between 64–80px (planner picks).
- `<ul>`/`<li>` semantics vs flat `<div>` for the bullet list.
- Memoization decisions for the small list.
- Whether to share threshold copy via a top-level constant.
- Whether to request a Phase 70 backend amendment for `entry_san_sequence` / `entry_pgn` field on `OpeningInsightFinding` (saves frontend SAN-derivation work). Decided during planning.

---

## Deferred Ideas

- Longer move-sequence trim (4+ plys) — revisit after Phase 71 telemetry / user feedback.
- W/D/L breakdown chip per bullet — revisit if users routinely want it; could land as a hover tooltip in a polish pass.
- Severity badge / icon — revisit if color-shade-only severity proves insufficient on greyscale displays.
- `hoveredMove` sticky-set on deep-link arrival — revisit if users miss the candidate move.
- Aggregate / meta-recommendation bullet → Phase 73 (stretch).
- Inline bullets on Openings → Moves → Phase 72.
- Bookmark badge on findings → Phase 74 (stretch).
