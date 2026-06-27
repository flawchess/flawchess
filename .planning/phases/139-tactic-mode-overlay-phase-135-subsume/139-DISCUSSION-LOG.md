# Phase 139: Tactic Mode Overlay + Phase 135 Subsume - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-26
**Phase:** 139-tactic-mode-overlay-phase-135-subsume
**Areas discussed:** Next/prev-tactic rail, Game-review-ply entry, Engine vs stored-PV arrows, Lost "return to Game"

---

## Next/prev-tactic rail (data source & scope)

| Option | Description | Selected |
|--------|-------------|----------|
| location.state list | Entry point passes its on-hand ordered flaw list via router location.state; rail calls setSearchParams; hidden on direct-URL | |
| Within-one-game only | Rail cycles only same-game flaws via the existing game endpoint | |
| Re-query flaws on /analysis | Carry filters in URL, rebuild the list on the Analysis page | |
| Descope rail (flag scope) | Parity-only subsume; defer the rail | |

**User's choice:** Free-text — "We only need to pass one missed tactic PV, one allowed tactic PV or both, when opening the analysis page via Explore button." → **no cross-flaw rail at all**; only the missed/allowed toggle for the single opened flaw.

**Follow-up confirmation:**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — single flaw only | game_id+flaw_ply pass one flaw; missed/allowed toggle only; no rail/location.state; record scope amendment vs SC#2 | ✓ |
| Keep a thin cross-flaw rail too | Add location.state next/prev on top of the toggle | |

**Notes:** Recorded as a scope amendment — ROADMAP SC#2 / REQUIREMENTS TACTIC-02 / research all named a "next/prev-tactic rail." SC#3's "tactic-rail state on route re-entry" reinterpreted as single-flaw re-seed/orientation-reset correctness. No silent ROADMAP/REQUIREMENTS edits.

---

## Game-review-ply entry (folded in from Phase 138 D-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Cheap ?fen= now | "Analyze position" button → /analysis?fen=<reconstructed ply FEN>; free-play, no chrome, no new plumbing; in LibraryGameCard, desktop+mobile | ✓ |
| Rich ?game_id=&ply= reader | Replay game on Analysis side for real move numbering; net-new plumbing | |
| Defer game-review entry again | Push to v2/backlog; leaves ROUTE-02 game-review clause unmet | |

**User's choice:** Cheap `?fen=` now.
**Notes:** Satisfies ROUTE-02's game-review clause (deferred once from 138). Reuses the existing v1 fen reader.

---

## Engine vs stored-PV arrows in tactic mode

| Option | Description | Selected |
|--------|-------------|----------|
| Stored-PV only on-line | Suppress engine arrow while on-line; engine takes over on deviation | |
| Show both on-line | Render engine + stored-PV arrows simultaneously | |
| Engine off until deviation | Don't run engine while on the stored line | |

**User's choice:** Free-text — curious about the stored line's second-best move, but stored + top-2 engine arrows at once is too much. Proposed a **toggle** between Stored PV and live Stockfish board arrows; live Stockfish only when off a stored line.

**Follow-up — toggle scope:**

| Option | Description | Selected |
|--------|-------------|----------|
| Toggle = board arrows only | On-line "Stored PV" ⇄ "Engine" arrow toggle; EvalBar + EngineLines panel always live; off-line engine arrows only | ✓ |
| Toggle = all engine output | Toggle hides/shows the whole live engine readout as one unit | |

**Notes:** Default Stored PV while on-line (135 parity); never draw both arrow sets at once.

---

## Lost "return to Game"

| Option | Description | Selected |
|--------|-------------|----------|
| Accept browser Back | Explore navigates to /analysis; return via browser/in-app Back; no return-to-game plumbing | ✓ |
| Explicit "Back to game" affordance | Contextual back link carrying the origin | |
| Keep modal for game-card entry | Only repoint FlawCard; conflicts with TACTIC-03/SC#4 deletion gate | |

**User's choice:** Accept browser Back.
**Notes:** Retires the Phase 135 nested-Dialog focus/scroll-restore complexity. Combined with the rail drop, this means entry points navigate with plain URL params only — no location.state anywhere.

---

## Claude's Discretion

- TacticModeOverlay layout (desktop side panel vs mobile stacked); reuse of TacticMotifChip, HorizontalMoveList, moveNumberLabel, formatFlawEval/mateAtPly, isBlackToMove unchanged.
- Board-arrow toggle UI (control type, label, data-testid, placement, default-on-mount state); hidden off-line.
- "Analyze position" (game-review) button placement/label/icon/variant; desktop+mobile.
- Default board orientation (Phase 135 flaw-maker-perspective rule).
- Regression-test placement (write the 4 checks before deleting anything).

## Deferred Ideas

- Cross-flaw next/prev-tactic rail — dropped for v1 (D-01); scope amendment vs SC#2/TACTIC-02.
- Rich ?game_id=&ply= game-review reader — deferred in favor of cheap ?fen=.
- ROADMAP/REQUIREMENTS wording cleanup (game-review-ply + rail descope) — at milestone close.
- URL write-back / "copy position link" / paste-a-FEN-PGN box — v2.
