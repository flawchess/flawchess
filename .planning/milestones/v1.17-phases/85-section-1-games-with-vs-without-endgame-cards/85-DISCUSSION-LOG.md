# Phase 85: Section 1 — Games with vs without Endgame cards - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-13
**Phase:** 85-section-1-games-with-vs-without-endgame-cards
**Areas discussed:** P-value source for both cards; Footer Score Gap bullet — sig gating

---

## P-value source for both cards

| Option | Description | Selected |
|--------|-------------|----------|
| Compute both locally | Use `computeScoreConfidence(W, D, total)` from `scoreConfidence.ts` for BOTH cards. Drop the now-redundant `endgame_score_p_value` backend field if no other consumer remains. Same derivation path for both cards, no backend change. | |
| Add backend `non_endgame_score_p_value` | Mirror the existing `endgame_score_p_value` on the backend. Use backend p-values for both cards. Tiny backend change (~10 lines + test), but breaks the 'frontend-only refactor' boundary of v1.17. | ✓ |
| Compute Yes via backend, No via local | Use the existing `endgame_score_p_value` for the Yes card and `computeScoreConfidence` locally for the No card. Two derivation paths for the same metric — risks subtle drift. | |

**User's choice:** Add backend `non_endgame_score_p_value`.
**Notes:** Single derivation site preferred over two parallel paths. CONTEXT.md flags this as a small breach of the v1.17 "frontend-only refactor" boundary so the planner and the milestone-description update at phase close are both aware. Wilson CI whiskers stay frontend-side via `wilsonBounds` (matches the Tile 2 pattern of `EndgameStartVsEndSection`).

---

## Footer Score Gap bullet — sig gating

| Option | Description | Selected |
|--------|-------------|----------|
| Zone-color only | Paint font from `score_difference` vs `SCORE_GAP_NEUTRAL_MIN/MAX` zones. No sig test. Matches legacy semantics and SEC1-04 spec (no sig-gating requirement). | ✓ |
| Apply SEC1-06 gating to the gap too | Compute a paired-proportion p-value for `Yes - No`, then gate on `n≥10 ∧ p<0.05 ∧ outside-band`. Statistically tighter, but requires a new helper + design choice on the right test for score-difference. | |
| Wilson-CI overlap proxy | Compute Wilson CIs on both cards' scores; treat as significant when the CIs don't overlap. Cheap, no new math, but a conservative/approximate sig test. | |

**User's choice:** Zone-color only.
**Notes:** SEC1-04 doesn't require sig-gating on the gap, and a real paired test would need stats plumbing out of v1.17 scope. Per-card sig gating (D-01 / D-03) already conveys reliability of the underlying scores; the gap is a derived presentation, not a paired inference.

---

## Claude's Discretion

The user did NOT select these gray areas in the multi-select. CONTEXT.md records the reasonable-default decisions:

1. **Legacy code removal mechanics (D-09).** Extract `EndgameScoreOverTimeChart` from `EndgamePerformanceSection.tsx` into its own file `EndgameScoreOverTimeChart.tsx` (with `SCORE_BAND_CLASS`, `useIsMobile`, and the Phase-68 comment block moved intact). Then delete `EndgamePerformanceSection.tsx` entirely. Cleaner than leaving an orphaned section name on the file containing only an unrelated chart export.
2. **Section-level header & InfoPopover (D-07).** Keep the legacy section-level h3 header `Games with vs without Endgame` + InfoPopover + sub-tagline above the new cards. Provides explanation continuity for existing users; per-card score-row popovers (SEC1-05) are additive, not a replacement.

## Deferred Ideas

- Paired-test sig gating on the footer Score Gap bullet (rejected here in favor of zone-color-only; could revisit in a future polish phase).
- Per-card peer baseline for Section 1 (conceptually fuzzy — no clean mirror-bucket equivalent for "with vs without endgame"; deliberately out of v1.17 scope per single-bullet doctrine).
- Section-level merge with `EndgameStartVsEndSection` (different questions; keep separate per current IA).
