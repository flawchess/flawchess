# Phase 157: FlawChess Agreement Verdict (prose + hoverable moves) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-07
**Phase:** 157-flawchess-agreement-verdict-prose-hoverable-moves
**Areas discussed:** Stockfish-off behavior, Tier thresholds + logic, Verdict copy & tone, Hover/arrow/popover parity

---

## Stockfish-off behavior

Both `engineEnabled` and `flawChessEnabled` default to `true`, so the common case is both engines running and the verdict well-defined. The question was only the explicit "SF toggled off, FlawChess on" case (no true objective #1 to compare against).

| Option | Description | Selected |
|--------|-------------|----------|
| Hide the verdict | Render nothing / neutral line when `engineEnabled` false; no FlawChess-vs-itself comparison | ✓ |
| Practical-only line | Degraded single-engine verdict, FlawChess pick + own objective eval | |
| Auto-read SF snapshot | Keep a Stockfish search alive for the verdict even when the SF card/arrow is off | |

**User's choice:** Hide the verdict.

**Follow-up — fixed-height slot content when SF is off:**

| Option | Description | Selected |
|--------|-------------|----------|
| Muted prompt line | `Turn on Stockfish to compare picks.` | ✓ |
| Empty slot | Reserved height only, nothing rendered | |

**Notes:** Verdict renders only when `engineEnabled === true` AND FlawChess has a snapshot. Source is the true Stockfish PV (`engine.pvLines[0]`), not the `engineTopLines[0]` memo (which degrades to FlawChess when SF is off).

---

## Tier thresholds + logic

`aligned` = FlawChess #1 and Stockfish #1 are the same UCI move. The divergence split needed a scale for "objective eval sacrificed." The project's flaw-drop thresholds (`flawThresholds.ts`) are in win-probability units (MISTAKE 0.10 / BLUNDER 0.15), and the FlawChess engine already carries the lichess sigmoid.

| Option | Description | Selected |
|--------|-------------|----------|
| Win% drop (reuse thresholds) | Convert both objective evals to win% via sigmoid; split with app's MISTAKE_DROP/BLUNDER_DROP; safe = 0<drop<0.15, sharp = drop≥0.15 | ✓ |
| Centipawn gap | `SF#1_objCp − FC#1_objCp` split by a new named cp constant | |

**User's choice:** Win% drop, sharp/trap threshold at `BLUNDER_DROP` (0.15), mover-POV.

**Notes:** Drop is always ≥ 0 (FlawChess #1 can't beat Stockfish's objective max). If either objective eval is null mid-search, fall back to the loading/help line rather than a bogus tier.

---

## Verdict copy & tone

The card's badge already frames the side-to-move as "you", but the chosen brand-voice drafts use neutral "for a human here" phrasing, sidestepping the you/opponent question.

| Option | Description | Selected |
|--------|-------------|----------|
| Brand voice (flawless vs FlawChess) | Stockfish = objective/flawless, FlawChess = human-playable pick; warmer, editorial | ✓ |
| Concise / eval-forward | Neutral, compact, evals up front; reads like an engine readout | |

**User's choice:** Brand voice. Move names are the interactive spans; exact wording finalized in implementation.

---

## Hover/arrow/popover parity

The default board already draws both picks' arrows persistently (Phase 156 `engineArrows`), so "hover lights the arrow" needed a defined meaning.

**Q1 — hover arrow behavior:**

| Option | Description | Selected |
|--------|-------------|----------|
| Isolate hovered pick | Reuse `qualityHoverArrows` lift-overlay: hover shows ONLY that move's arrow (amber FC / blue SF), overriding the default two-arrow layer; release restores both | ✓ |
| Emphasize in place | Keep both arrows; thicken/brighten the hovered one | |

**Q2 — popover content (raised as a clarification by the user):**

The user reframed the popover from the terse `practically X · objectively Y` dot format to an engine-labeled two-line format (`FlawChess: +0.3 (practical)` / `Stockfish: +0.4 (objective)`), anchored to the hovered move span. The remaining decision was what the FlawChess line shows for a Stockfish move the engine didn't rank.

| Option | Description | Selected |
|--------|-------------|----------|
| Omit FlawChess line | Render only lines with real data; SF pick reads `Stockfish: … (objective)` alone when not ranked by FC | ✓ |
| Show `FlawChess: —` | Always two lines, em-dash placeholder when no practical score | |

**User's choice:** Isolate hovered pick; engine-labeled two-line popover; omit the FlawChess line when the move wasn't ranked by FlawChess.

**Notes:** Click plays the move as a free move via existing `onPlayMove`. Verdict sits in a fixed-height slot below the ranked lines, refining live without layout jump.

## Claude's Discretion

- New pure `flawChessVerdict.ts` module mirroring `positionVerdict.ts` (tiers + named constants + verdict-move shape + eval formatter).
- Verdict rendered as a separate component in the FlawChess `CardBody` below `FlawChessEngineLines` (not folded into that body-only component).
- Exact prose wording, eval-format reuse, and popover markup styling.

## Deferred Ideas

- Played-move vs practical-best comparison (game review) → SEED-086. Out of scope; this phase compares the two engines, not the played move.
