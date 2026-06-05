# Phase 104: Library Page Shell + Import & Overview Subtab Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 104-library-page-shell-import-overview-subtab-migration
**Areas discussed:** Library nav icon, Subtab presentation

---

## Gray-area selection

| Area | Description | Discussed |
|------|-------------|-----------|
| Returning-user landing | Keep `/openings` vs switch to `/library/overview` (SEED-036 open question) | resolved to default (keep `/openings`) |
| Library nav icon | Pick the new top-level icon | ✓ |
| Mobile bottom bar | Library · Openings · Endgames + More vs other | resolved to default |
| Subtab presentation | Subtab icons/labels + info popovers | ✓ |

**User's choice:** Discuss "Library nav icon" and "Subtab presentation"; accept defaults for the other two.
**Notes:** Phase is tightly pre-decided by SEED-036; unpicked areas resolved with the stated sensible defaults (landing stays `/openings`; bottom bar = Library · Openings · Endgames + More).

---

## Library nav icon

| Option | Description | Selected |
|--------|-------------|----------|
| Library | lucide `Library` (stacked books); matches the "collection you stock then browse" framing (recommended) | |
| LayoutDashboard | Reuse Overview's current icon; overlaps with the Overview subtab identity | |
| BookMarked | Book-with-bookmark; visually close to Openings' BookOpen | |
| Archive | Strong "stored games" feel; undersells analysis/overview | |
| **FolderOpen** (free-text) | lucide `FolderOpen` — "a collection you open" | ✓ |

**User's choice:** `FolderOpen` (free-text override of the recommended `Library`).
**Notes:** Applies to desktop nav, mobile bottom bar, and mobile "More" drawer.

---

## Subtab presentation

### Subtab icons + labels

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse existing icons + plain labels | Import = Download + "Import"; Overview = LayoutDashboard + "Overview"; mirrors Openings icon+label triggers (recommended) | ✓ |
| Plain labels, no icons | Text-only triggers; breaks parity with Openings/Endgames | |

### Info popovers on subtabs

| Option | Description | Selected |
|--------|-------------|----------|
| No info popovers | Import/Overview are self-explanatory; skip the InfoPopover (recommended) | ✓ |
| Add info popovers | Mirror Openings' active-tab InfoPopover exactly | |

**User's choice:** Reuse existing icons + plain labels; no info popovers.
**Notes:** Info popovers deferred with the future Games/Analysis subtabs that would actually need explaining.

---

## Claude's Discretion

- File/component names under `frontend/src/pages/library/` (suggest `LibraryPage` + `ImportTab.tsx` / `OverviewTab.tsx`).
- Whether `GlobalStats.tsx` is moved wholesale or wrapped into the Overview subtab.
- Desktop vs mobile subnav markup detail (follows the Openings `<Tabs variant="brand">` + sticky mobile subnav pattern).

## Deferred Ideas

- Games subtab, Analysis subtab, mistake-detection service, best-move endpoint — SEED-036 future phases.
- Subtab-level import gating (only relevant once Games/Analysis exist).
- Subtab InfoPopovers (deferred with Games/Analysis).
- Switching the returning-user landing to Library/Overview (considered, rejected — keep `/openings`).
