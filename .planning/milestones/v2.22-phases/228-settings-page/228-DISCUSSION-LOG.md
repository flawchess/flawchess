# Phase 228: Settings Page — Sound Toggle & Per-Engine Lines/Arrows - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-10-03
**Phase:** 228-settings-page
**Areas discussed:** Entry placement, Page layout & controls, Train free-play depth, High-count rendering

---

## Entry placement

| Option | Description | Selected |
|--------|-------------|----------|
| Cogwheel left of Logout | Icon-only ghost button in the desktop right cluster | ✓ |
| Nav tab 'Settings' | Add to NAV_ITEMS | |

| Option | Description | Selected |
|--------|-------------|----------|
| More drawer row | Settings row above Logout in MobileMoreDrawer | ✓ |
| Cogwheel in MobileHeader | Top-right icon next to page title | |
| Both | Header cogwheel + drawer row | |

| Option | Description | Selected |
|--------|-------------|----------|
| No card link | Header/drawer only | |
| Desktop-only cogwheel in card header | Icon in each engine card header | |
| Other (free text) | "On the mobile analysis page, add the settings cogwheel in the page header (next to page title). Add the cogwheel also on the bot game page, so a user can go to the settings and disable sounds during a game." | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Open settings in a sheet | Same SettingsPanel in a Drawer/Dialog over the page | ✓ |
| Navigate to /settings | Bot game shows ResumeGate on return; analysis may lose sideline | |
| Sheet on bots, navigate on analysis | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Desktop and mobile | Bot page cogwheel on both | |
| Mobile only | Desktop uses header cogwheel | ✓ |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Full panel everywhere | One SettingsPanel, identical in page and sheets | ✓ |
| Relevant sections only | Bot sheet Sound only; panel takes a sections prop | |

**Notes:** Navigating away from a clocked bot game triggers `ResumeGate` on return, which is why
the in-context cogwheels open a sheet.

---

## Page layout & controls

| Option | Description | Selected |
|--------|-------------|----------|
| Segmented toggle group | 1-5 / 0-3 buttons | ✓ |
| Select dropdown | | |
| Slider | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Instantly, no Save | localStorage on change, live via useSyncExternalStore | ✓ |
| Save button | | |

| Option | Description | Selected |
|--------|-------------|----------|
| 3 sections + reset | Sound / FlawChess engine / Stockfish + Reset to defaults | ✓ |
| 3 sections, no reset | | |
| Engines side by side | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Umami event per change | settings-change {setting, value} | ✓ |
| No tracking | | |

---

## Train free-play depth

| Option | Description | Selected |
|--------|-------------|----------|
| Honor it, fixed 1500 ms | MultiPV = max(SF lines, SF arrows) | ✓ |
| Scale movetime with MultiPV | | |
| Cap Train at 3 lines | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Eval bar engine pinned independent | Fixed MultiPV, ignores setting | ✓ |
| Follow the setting | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Free-play live arrows only | Puzzle-reveal legend arrows always draw | ✓ |
| All engine-colored arrows | | |

---

## High-count rendering

| Option | Description | Selected |
|--------|-------------|----------|
| Same graded ranking as the card | SF arrows 1..N from reconciled grading list; free run = fallback | ✓ |
| Free-run pvLines | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Same width, translucent color | | ✓ |
| Thinner + translucent | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Render all N rows | | ✓ |
| Cap visible rows on mobile | | |

**Notes:** Today's SF arrow loop `reconciledBestUci ?? enginePvLines[i]` would repeat the best
move for i ≥ 1. Surfaced during scouting.

## Claude's Discretion

- Route gating (ProtectedLayout, no import gate), ROUTE_TITLES entry
- Translucent color/alpha values
- Settings storage layout and validation
- Eval-bar engine fixed MultiPV value (1 or 2)
- useGameOverlay SECOND_BEST_ARROW retirement
- Exact bot mobile cogwheel spot

## Deferred Ideas

- Stockfish "search longer" toggle (after Phase 226 settles)
- Moving TrainScheduleSettings onto the settings page
