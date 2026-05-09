# Phase 81: Endgame Start vs End — twin-tile section above the WDL table - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 81-Endgame Start vs End — twin-tile section above the WDL table
**Areas discussed:** Section composition (free-form), Sparse-state behavior, Composition lock-in

---

## Initial gray-area selection

Claude proposed four areas (Section heading + tile copy / Axis ranges / Mobile ordering / Concept-explainer paragraphs).

**User's choice (free text):** "Decide on your own, we'll iterate on the implementation. But we should decide what elements the section 'Endgame Start vs End' contains. What do you suggest?"

**Effect on flow:** Reframed the discussion from copy-and-axis polish to **section composition / element list**. Copy, axis ranges, mobile ordering, and final wording moved to Claude's discretion (iterate during execution / UI review).

---

## Section composition

Claude proposed a six-element-per-tile layout (punchy title, technical sub-header, info-popover icon, MiniBulletChart, value line, stats line) plus section-level H3, no lead paragraph, no section-level info popover.

| Option | Description | Selected |
|--------|-------------|----------|
| Lock as proposed | Six per-tile elements + H3 + no lead paragraph + no section-level info popover | |
| Lock, add 1-line lead | Same as proposed but add a short lead paragraph under the H3 | |
| Lock, drop info-popover icons | Same as proposed but no per-tile info popover, lean entirely on concepts accordion | |

**User's choice (free text):** "Note that we should use the established popover info icons for score and eval. We use them in several places in the Openings subtabs. Stay compatible with that display. It's fine to add punchy title, but don't show p-values (they are covered in the tooltips)."

**Notes:**
- Locked the established Openings ExplorerTab pattern: `BulletConfidencePopover` + `ScoreConfidencePopover` carry confidence details (n, p-value) inside the popover.
- Dropped the standalone "n=… · p<0.05" stats line per-tile — duplicates the popover.
- Punchy title kept at the top of each tile.

---

## Sparse-state behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Render both, placeholder on empty tile | Empty tile shows "Not enough data yet"; other tile renders normally | |
| Hide section unless both tiles have data | Both tiles must have ≥ threshold to render | |

**User's choice (free text):** "Let's use n >= 10 as a threshold, like almost everywhere else. Note that the n will be equal, unless we somehow fail to analyze an entry position with stockfish during the import."

**Notes:**
- Threshold lowered from n=30 (per the obsolete design note) to n ≥ 10, matching the project-wide convention used everywhere else.
- Acknowledged that mixed sparse states are essentially impossible in practice — the placeholder behavior is for the rare Stockfish-failure case.

---

## Final lock-in

| Option | Description | Selected |
|--------|-------------|----------|
| Lock and write CONTEXT.md | Composition + Claude-discretion defaults are good enough; iterate during execution / UI review | ✓ |
| Tweak something | Free-text adjustment before writing CONTEXT.md | |

**User's choice:** Lock and write CONTEXT.md.

---

## Claude's Discretion

User explicitly delegated the following to Claude (iterate during execution / UI review):

- Final wording of the section heading (defaulted to "Endgame Start vs End")
- Final punchy tile titles ("Where you start" / "What you do with it")
- Final tile sub-labels ("Avg eval at endgame entry" / "Endgame score")
- Pawn-axis domain (defaulted to ±2.0 per benchmark notes)
- Score-axis domain (defaulted to reuse Openings score-bullet constants for cross-page consistency)
- Mobile ordering (defaulted to entry-eval first — chronological)
- Concept-explainer accordion paragraph wording

## Deferred Ideas

- Distribution / histogram view of per-game entry evals
- Per-TC stratification of entry eval
- Sig-test on Score Gap inside the WDL table (original-design symmetry idea)
- Cross-user eval × clock-diff correlation as a displayed metric
- Pre-endgame eval over time chart (analog of `EndgameScoreOverTimeChart`)
