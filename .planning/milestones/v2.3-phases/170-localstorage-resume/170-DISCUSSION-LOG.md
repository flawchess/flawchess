# Phase 170: localStorage Resume - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-13
**Phase:** 170-localstorage-resume
**Areas discussed:** Clock fairness on leave/resume, Resume prompt UX + slot policy
**Areas delegated to Claude:** Snapshot shape + resume seam, Store-once lifecycle + failures

---

## Clock fairness on leave/resume

### Q1 — Think time burned before leaving

| Option | Description | Selected |
|--------|-------------|----------|
| Bill think time, refund away time | Snapshot on every move AND on tab-hide/pagehide, folding the in-turn chargeable elapsed into the active side's clock. Hard-kill falls back to the last-move snapshot. | ✓ |
| Snapshot on moves only | Simplest, literally what SC1 says, but refreshing refunds the current turn's think time — a free "undo my clock". | |
| Throttled clock heartbeat | Full snapshot on move + a ~1-2s write of the active clock. Survives crashes/hard kills, but runs a timer all game. | |

**User's choice:** Bill think time, refund away time (D-01)
**Notes:** The pagehide-not-guaranteed gap (crash / iOS purge) is knowingly accepted; the heartbeat that would close it was explicitly rejected as not worth a timer running for the whole game.

### Q2 — Leaving mid-bot-think (search dies with the workers)

| Option | Description | Selected |
|--------|-------------|----------|
| Refund the discarded think | Fold in-turn elapsed only when the USER is active; a bot turn snapshots at last commit and restarts cleanly. Matches Phase 169's cancel semantics. | ✓ |
| Bill it symmetrically | Bot pays for the discarded search AND the redo — double-charged for a page close it didn't cause; can flag it in time trouble. | |
| Freeze the bot's turn entirely | Re-dispatch with the originally computed deadline — practically identical today, differs only if the deadline ever becomes stateful. | |

**User's choice:** Refund the discarded think (D-02)
**Notes:** No user exploit — refunding the bot's clock only ever helps the bot.

### Q3 — Engine cold-start on resume (~1-2s worker/ONNX respawn)

| Option | Description | Selected |
|--------|-------------|----------|
| Nobody + prewarm early | Spawn the workers the moment a snapshot is detected (during the resume gate), and set the turn anchor only once the board is live. | ✓ |
| Nobody — anchor after warm | No prewarm; just freeze the clock until warm. User stares at a live-looking board with a frozen clock. | |
| The bot pays | Purely honest clock — a bot with 5s left can flag on a worker spawn, making an infrastructural cost look like a chess decision. | |

**User's choice:** Nobody + prewarm early (D-03)
**Notes:** Same trick as 169.5's warm-during-the-book-window.

---

## Resume prompt UX + slot policy

### Q1 — How much resume UI belongs to 170 vs 171

| Option | Description | Selected |
|--------|-------------|----------|
| Resume gate component | 170 ships a real, reusable gate on /bots (identity line + Resume/Discard); no game auto-starts until the user chooses. 171 keeps the component and replaces only the no-snapshot branch with the setup screen. | ✓ |
| Headless only | 170 ships logic with no UI; SC1's "offers a Resume game? prompt" then can't be verified until 171, and the stub page keeps auto-starting over a live snapshot. | |
| Full dialog over the setup screen | The setup screen doesn't exist yet — inverts the phase order for no gain. | |

**User's choice:** Resume gate component (D-04)
**Notes:** Also resolves the ROADMAP's 170/171 overlap on the store call — 170 owns the store plumbing, 171 owns the surfaces (CONTEXT D-10).

### Q2 — Discard semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Confirm, then drop | A confirmation step ("this game will be lost — unfinished games are never saved") before clearing. Mirrors the existing resign-confirm. | ✓ |
| Drop immediately | Fewer clicks, but an irreversible destructive action one mis-tap from "Resume" on mobile. | |
| Discard = auto-resign a loss | Would contradict RESUME-02 / SC2 ("an abandoned game leaves no server trace") — needs a requirements change, not a phase decision. | |

**User's choice:** Confirm, then drop (D-05)

### Q3 — Snapshot expiry

| Option | Description | Selected |
|--------|-------------|----------|
| Never expires, show its age | Lives until resumed-and-finished, discarded, or invalidated by a schema-version bump; the gate shows "2 days ago" and the user decides. | ✓ |
| TTL, auto-drop when stale | Silently destroys a game the user might still want, for an arbitrary N, to save a few KB. | |
| TTL with a warning | Same as showing the age, plus an extra threshold constant to justify. | |

**User's choice:** Never expires, show its age (D-06)
**Notes:** Single in-progress slot (D-07) was stated and not contested — multiple resumable games would need a game-list UI belonging to 171 at the earliest.

---

## Claude's Discretion

- **Snapshot shape + resume seam** (CONTEXT D-08 … D-10) — SAN + per-ply `[%clk]` array (never a bare FEN, never a bare SAN list), the versioned payload and what is deliberately *not* persisted, and a single `useBotGame(settings, resume?)` seam rather than a second restore path.
- **Store-once lifecycle + failures** (CONTEXT D-11 … D-14) — uuid minted at game start, a *separate* pending-store queue key, drain-on-mount, and the per-status failure policy (retry on network/5xx/401, drop on 422).
- Remaining: key names, module/function naming, queue cap, gate composition and placement, whether the drain surfaces any UI in 170.

## Deferred Ideas

- Multiple resumable games / a resumable-games list (needs a game-list UI — Phase 171's setup screen at the earliest, more likely a later milestone).
- A clock heartbeat that survives a hard browser kill (rejected in D-01).
- User-facing "failed to save, retrying" surfacing for the pending-store queue (Phase 171 owns the result/Library surfaces).
