# Phase 138: `/analysis` Route + Page Shell + Entry Points - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-26
**Phase:** 138-analysis-route-page-shell-entry-points
**Areas discussed:** Game-review ply entry (selected). Opening-position entry, page-shell
layout, and reachability/defaults were offered but not selected — captured from
ARCHITECTURE + discretion.

---

## Gray-area selection

| Area | Description | Selected |
|------|-------------|----------|
| Game-review ply entry | Resolve the ROADMAP↔ARCHITECTURE tension on `?game_id=&ply=` | ✓ |
| Opening-position entry | Button placement/label + which FEN | |
| Page shell layout | Desktop/mobile composition | |
| Reachability & free-play defaults | Nav item, blank free-play, engine default | |

**User's choice:** Game-review ply entry only.
**Notes:** User content to let ARCHITECTURE + Claude's discretion drive the other three.

---

## Game-review ply entry — scope & URL contract

| Option | Description | Selected |
|--------|-------------|----------|
| `?fen=` of scrubbed ply | In scope via the existing game-viewer modal; carry the per-ply reconstructed FEN through the v1 `fen` param (no new reader, no backend) | |
| `?game_id=&ply=` reader | In scope; build the deferred reader (fetch + replay on Analysis side) | |
| Defer to later phase | 138 ships opening-position entry only; matches ARCHITECTURE Phase 3 | ✓ |

**User's choice:** Defer to later phase.
**Notes:** Chose to defer the whole game-review entry rather than ship a context-light
`?fen=` shortcut now.

---

## Game-review entry — where it lands

| Option | Description | Selected |
|--------|-------------|----------|
| v2 backlog / seed | Capture as deferred idea; free-play, not tactic work | |
| Fold into Phase 139 | 139 already has game/library surfaces + game_id/ply plumbing | ✓ |

**User's choice:** Fold into Phase 139.
**Notes:** Accepted that this slightly expands 139 beyond pure tactic-mode subsume.

---

## ROADMAP / ROUTE-02 wording

| Option | Description | Selected |
|--------|-------------|----------|
| Note in CONTEXT only | Record descope in CONTEXT.md; leave ROADMAP/REQUIREMENTS untouched | ✓ |
| Adjust roadmap now | Edit Phase 138 title + ROUTE-02 | |

**User's choice:** Note in CONTEXT only.
**Notes:** No unrequested roadmap edits; flag for milestone-close cleanup.

---

## Closeout

| Option | Description | Selected |
|--------|-------------|----------|
| Ready for context | Write CONTEXT.md now | ✓ |
| Explore more gray areas | Open the other three areas for discussion | |

**User's choice:** Ready for context.

## Claude's Discretion

- Page shell responsive layout (lichess/chess.com convention).
- "Analyze position" button placement/label/variant on the Openings Explorer tab.
- Suspense fallback + engine-loading copy.
- Blank free-play onboarding (lean: silent start position).

## Deferred Ideas

- Game-review-ply entry point → Phase 139 (URL contract still open there).
- ROADMAP/ROUTE-02 wording cleanup → milestone close.
- On-demand "copy position link" → v2.
- Paste-a-FEN/PGN box (BOARD-V2-01) → v2.
