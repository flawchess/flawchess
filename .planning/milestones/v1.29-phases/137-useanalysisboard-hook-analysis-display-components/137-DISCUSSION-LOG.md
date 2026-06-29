# Phase 137: `useAnalysisBoard` Hook + Analysis Display Components - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-26
**Phase:** 137-useanalysisboard-hook-analysis-display-components
**Areas discussed:** URL state scope, VariationTree rendering, EvalBar + EngineLines behavior, Verification surface

---

## URL state scope (ROADMAP↔ARCHITECTURE conflict)

ROADMAP SC#4 / BOARD-04 want a shareable/bookmarkable *variation* in the URL; ARCHITECTURE
Pattern 5 says the URL is read-only entry-point encoding and variations are ephemeral. Surfaced
as a direct conflict to resolve.

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only entry point (Pattern 5) | URL encodes arrival point only; navigation/forks ephemeral. SC#4 = "starting position is shareable." | ✓ |
| Live write-back of full tree | URL updates on every navigation/fork; literal SC#4; needs tree serialization + history management. | |
| Hybrid: entry point now, shareable-position later | Read-only now + on-demand "copy position link" encoding current FEN. | |

**User's choice:** Read-only entry point (Pattern 5).
**Notes:** Resolves the conflict by reinterpreting SC#4 as "starting position shareable." On-demand
FEN copy-link captured as a deferred idea.

---

## VariationTree rendering

Mobile pre-settled as lichess-style horizontal (inline variation in parens/indent); desktop open.

| Option | Description | Selected |
|--------|-------------|----------|
| Responsive: desktop vertical paired list | Mobile horizontal (extend HorizontalMoveList); desktop NEW vertical paired list beside board. | ✓ |
| Horizontal on both | Reuse HorizontalMoveList everywhere; defer desktop vertical to v2. | |
| Vertical on both | One vertical list on mobile too; breaks app's mobile horizontal convention. | |

**User's choice:** Responsive — desktop vertical paired list (recommended).
**Notes:** User anchored both to lichess/chess.com conventions (desktop vertical beside board;
lichess mobile horizontal with parens+indent). Flagged: v1 is flat single-variation, so the
vertical list's nesting payoff is a v2 thing; component placement beside the board is Phase 138's
page-shell job.

---

## EvalBar + EngineLines behavior

| Option | Description | Selected |
|--------|-------------|----------|
| PV clickable + EvalBar white-POV fixed | Clicking PV move forks via makeMove; EvalBar white-on-top regardless of flip. | ✓ |
| PV read-only + EvalBar follows board flip | EngineLines display-only; EvalBar swaps ends on flip. | |
| You decide (planner's call) | Capture intent, let planner decide clickability + flip. | |

**User's choice:** PV clickable + EvalBar white-POV fixed (recommended).
**Notes:** Matches lichess/chess.com analysis UX and ARCHITECTURE's white-POV note.

---

## Verification surface (no /analysis route until Phase 138)

| Option | Description | Selected |
|--------|-------------|----------|
| Vitest component/hook tests only | Hook tests + RTL render tests against fixtures; on-device eyeballing deferred to 138. | ✓ |
| Tests + throwaway dev harness | Same tests + temporary unrouted harness; 136 rejected this. | |
| You decide (planner's call) | Require unit tests; planner decides on any preview. | |

**User's choice:** Vitest component/hook tests only (recommended).
**Notes:** Mirrors Phase 136 D-01/D-02. On-device verification is Phase 138's gate.

---

## Claude's Discretion

- Tree internals (NodeId allocation, Map keying, sibling order, `goForward` tie-break).
- EngineLines plies-per-line truncation, depth-badge / "thinking" indicator visuals.
- VariationTree parenthesis/indent styling, desktop column widths, auto-scroll.
- EvalBar gradient stops, width, mate-label placement (within white-POV + sigmoid + depth-8 mate).

## Deferred Ideas

- Live URL write-back / shareable variation tree (v1 = read-only entry point); possible on-demand
  "copy position link" later.
- Full nested-tree VariationTree display (v2).
- Promote / delete / annotate variation UX (ephemeral tree in v1).
- On-device (iOS Safari / low-end Android) verification of rendered engine output (Phase 138 gate).
- Tactic-mode overlay, stored-PV seeding, entry points (Phases 139 / 138).
