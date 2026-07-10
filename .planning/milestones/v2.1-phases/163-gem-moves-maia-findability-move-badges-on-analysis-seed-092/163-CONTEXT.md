# Phase 163: Gem moves — Maia-findability move badges on /analysis (SEED-092) - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning
**Source:** SEED-092 (locked design: detection math, lazy coverage, surfaces) + discuss session 2026-07-10 (eight open points resolved)

<domain>
## Phase Boundary

A positive counterpart to the flaw glyphs (`??`/`?`/`?!`) on `/analysis`: badge the rare move that is both the engine's clearly-only good move AND hard for a human at the player's rating to find. Named **"Gem"** (deliberately not "Great"/"Brilliant" — no comparison invited with chess.com's classifier). Pure frontend; no backend changes, no cross-game statistics, nothing persisted.

Detection (both conditions required, from the seed):
- **C1 — hard to find:** Maia policy probability of the played move ≤ `GEM_MAIA_MAX_PROB` at the rating-matched rung.
- **C2 — only good move:** expected score of the played move minus the best *alternative* ≥ `MISTAKE_DROP` (0.10, `@/generated/flawThresholds`), via the existing `evalToExpectedScore` sigmoid. C2 implies the move is engine-best; reads as "every alternative would have been at least a mistake."

Surfaces (all `MAIA_ACCENT` violet): board-corner marker + move-list glyph with the white lucide `Gem` icon (SVG-icon marker variant alongside the text-glyph one), `MovesByRatingChart` curve recolor + tooltip label, short popover copy. `MoveQuality` gains a 6th positive bucket overriding "best"; `FlawSeverity` stays negative-only.

</domain>

<decisions>
## Implementation Decisions

### Qualification edges
- **D-01: Lost-position gems KEEP.** A best-try in a still-lost position (e.g. es 0.05 → 0.20 while every alternative sits at 0.05) qualifies — finding the only defensive resource deserves celebration. No "still losing after the move" exclusion (explicitly rejects Chesskit's rule). The es gap ≥ `MISTAKE_DROP` already guarantees the move mattered.
- **D-02: No opening guard.** No first-N-plies exclusion. Trust the free-lunch guards (sigmoid saturation, high Maia probability on forced/known moves); a rating-matched badge on a sharp theory move peers don't find is deserved. Revisit at UAT only if badge inflation appears.

### Rating source & whose moves
- **D-03: C1 uses the page's selected ELO** — the same selected-ELO knob the Moves-by-Rating chart and findability ranking already use (slider/profile-driven). One ELO source for the whole page; badges legitimately update when the slider moves (showcases the rating-conditioning; `useMaiaEngine` already computes the full per-ELO curve, so re-deriving C1 on slider change is free). NOT rating-at-game-time, NOT current_rating.
- **D-04: Both players' moves get gems.** Symmetric with the flaw-glyph pipeline (live flaw marks any move played on the board regardless of color). No color filter.

### Coverage, timing & stability
- **D-05: Any visited board move classifies** — mainline game moves AND freely-explored variation moves, exactly mirroring the live-flaw glyph pipeline. Lazy, per visited position; no background full-game sweep (seed-locked).
- **D-06: Same mechanism as free-move flaw tagging (user-locked, replaces the seed's open "min-depth stability gate" tunable).** Mirror `useLiveMoveFlaw` + the `liveFlawByNode` pattern in Analysis.tsx: classify from a memo as soon as the required engine data exists (no explicit min-depth gate), live-updating while data streams, then made sticky per node via a `Map<NodeId, …>` cache at the Analysis level so navigation keeps the badge. Accepted caveats match the live-flaw ones (badge lags the move until data lands; early shallow data may classify slightly differently than a full-depth run would). Note for planning: C2 needs per-candidate grades of the parent position (the reconciled grading map over the union — see D-08), which in practice arrives with the grading run, so gems appear on roughly the grading-run cadence anyway.

### Threshold & calibration
- **D-07: `GEM_MAIA_MAX_PROB = 0.03` (3%)** — single flat v1 constant (the seed's anchor value; user chose 3% over the stricter 2%). Named constant per project rules. No ELO-conditioned curve in this phase; the seed documents the slope-inversion constraint (opposite to `pRefForElo`) for the future curve — do NOT reuse `P_REF_ANCHORS`.
- **D-08: No calibration tooling in-phase.** UAT eyeballs badge frequency; the iso-rarity threshold curve derivation is a deferred follow-up (see Deferred Ideas).

### Claude's Discretion
- Detection module location/shape (pure lib function + vitest, per project norms), including how C2 reads the Phase 162 reconciled grading map and how the free run's MultiPV=2 second line serves as pre-grading input, if at all.
- Glyph precedence markup: gem overrides the "best" bucket everywhere (seed-locked); how `MaiaMoveQualityBar` folds the gem bucket (presumably into the green "good" display segment) and how `UnifiedMovePopover` labels it.
- SVG-icon marker variant design in `boardMarkers.tsx` (lucide `Gem` path inside the existing circle-badge geometry) and the parallel move-list icon component alongside `SeverityGlyphIcon`.
- Popover/tooltip copy (seed suggests: "Gem — players at your rating almost never find this."); keep ≥ `text-sm` except inside the sanctioned info-popover pattern.
- Exact free-lunch-guard test fixtures (verify in tests, don't hand-code guards: saturation suppresses already-decided positions; forced recaptures excluded by C1).
- Cache invalidation details when the ELO slider moves (C1 re-derives; C2 grade cache untouched).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source
- `.planning/seeds/SEED-092-gem-moves-maia-findability-badges.md` — THE design doc: detection rule, free-lunch guards, lazy coverage, surfaces, OSS "Great move" research table (freechess/Chesskit/en-croissant), naming rationale.

### Prior-phase architecture this builds on
- `.planning/phases/162-grading-run-authoritative-eval-reconciliation-precedence-fli/162-CONTEXT.md` — reconciled-eval architecture (D-14: grading-run ranking is authoritative for every displayed per-move eval; gem C2 must read reconciled grades, not raw free-run PVs). Also D-10 flicker doctrine (atomic-at-commit is the remedy if UAT flags flicker, never label pinning).
- `.planning/milestones/v1.32-phases/` (Phase 151.1) — MoveQuality 5-bucket design; "MultiPV index is an eval rank, key grades by pv[0]" caveat.

### Code touchpoints
- `frontend/src/lib/moveQuality.ts` — `MoveQuality` type (gains 6th bucket), `classifyMoveQuality` (gem overrides its 'best' output), `bucketMovesByQuality` (display folding).
- `frontend/src/hooks/useLiveMoveFlaw.ts` — the mechanism D-06 mirrors (memo classification, no depth gate).
- `frontend/src/pages/Analysis.tsx` — `liveFlawByNode` sticky Map pattern (~1251-1307), `qualityBySan` (~861-882), `unionSans`/`evalLookup`/reconciled memos (Phase 162 wiring), `squareMarkers` assembly.
- `frontend/src/lib/severityGlyph.ts` + `frontend/src/components/board/boardMarkers.tsx` + `frontend/src/components/icons/SeverityGlyphIcon.tsx` — glyph/badge single-source pattern; the SVG-icon variant lands alongside these.
- `frontend/src/components/analysis/MovesByRatingChart.tsx` — `colorForQuality` (~179) + end-of-line labels; gem curve renders `MAIA_ACCENT`.
- `frontend/src/components/analysis/MaiaMoveQualityBar.tsx`, `UnifiedMovePopover.tsx`, `VariationTree.tsx` (move-list glyph rendering via `BlunderIcon`/`MistakeIcon`).
- `frontend/src/lib/theme.ts` — `MAIA_ACCENT = 'oklch(0.58 0.20 290)'` (line ~74); any new semantic color constants live here.
- `frontend/src/lib/liveFlaw.ts` — `evalToExpectedScore`, `classifyLiveSeverity`, `MISTAKE_DROP` import chain from `@/generated/flawThresholds`.
- `frontend/src/hooks/useMaiaEngine.ts` — per-ELO move-probability curves (`MoveCurvePoint`), `nearestByElo` reuse via moveQuality.ts.
- `frontend/src/lib/engine/findability.ts` — for the ANTI-pattern note only: `P_REF_ANCHORS` slope is OPPOSITE to what a future gem threshold curve needs; at most reuse the interpolation helper shape.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `liveFlawByNode` (Analysis.tsx): the exact sticky per-node Map cache + memo-classification pattern D-06 mandates — a parallel `gemByNode` follows it.
- `SquareMarkerGroup`/`SquareMarkerBadge` (boardMarkers.tsx): circle-badge geometry (radius fractions, corner overlap, stroke) is reusable; needs an icon-content variant since the gem symbol is an SVG path, not text.
- `classifyMoveQuality` already computes per-candidate expected scores and the argmax — C2's "gap to best alternative" is derivable from the same `gradeMap` inputs.
- `nearestByElo` (moveQuality.ts) for the C1 rung lookup at the selected ELO.
- Phase 162's reconciled lookup/ranking memos are the authoritative C2 eval source.

### Established Patterns
- Severity glyph single-source: `SEVERITY_GLYPH` record consumed by both the React icon and the board marker so they never drift — the gem spec should extend this pattern (parallel record or entry with an icon discriminant), not fork it.
- `MoveQuality` is frontend-only; never extend `FlawSeverity` (cross-stack contract).
- Named constants for thresholds; theme colors only from theme.ts; `data-testid` on new interactive elements; changes apply to mobile surfaces too.
- Frontend type changes: run `npx tsc -b` / `npm run build` before integrating (lint+test don't type-check).

### Integration Points
- Board: `squareMarkers` prop on ChessBoard (and MiniBoard if game-card parity is desired — desktop/mobile duplication check).
- Move list: `VariationTree.tsx` renders severity icons per node — gem icon joins there.
- Chart: `colorForQuality` + `qualityBySan` map — a 'gem' quality value flows through existing plumbing once the type extends.
- Popover: `UnifiedMovePopover` quality labeling.

</code_context>

<specifics>
## Specific Ideas

- Tooltip/popover copy starting point (seed): "Gem — players at your rating almost never find this."
- Board/move-list symbol: white lucide `Gem` icon in a `MAIA_ACCENT` violet circle — NOT a text `!` glyph (seed-locked after exploration).
- The rising-with-ELO probability curve in `MovesByRatingChart`, rendered violet, is itself the visual justification for the badge (seed).
- Free-lunch guards are verified in tests, not hand-coded: (1) already-decided positions suppressed by sigmoid saturation (+800 vs +400 gap ≈ 0 in es space); (2) forced recaptures/only-legal-moves excluded by high Maia probability (C1).

</specifics>

<deferred>
## Deferred Ideas

- **Iso-rarity threshold curve** (ELO-conditioned `GEM_MAIA_MAX_PROB`): after UAT, tabulate would-badge frequency per Maia rung on real games and derive a constant-badge-frequency curve from data instead of guessed anchors. Slope must INVERT vs `pRefForElo` (strict at low ELO, generous at high ELO). Not in this phase (D-07/D-08).
- **Calibration dev tooling** (per-rung badge-frequency tabulation helper) — rejected for this phase; build only if UAT eyeballing proves insufficient.

### Reviewed Todos (not folded)
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` (WR-01 — `pt-33` invalid Tailwind class on the endgame Score Y-axis label) — keyword match only; unrelated chart, already reviewed-and-deferred in Phase 162. Stays in the todo backlog.

</deferred>

---

*Phase: 163-gem-moves-maia-findability-move-badges-on-analysis-seed-092*
*Context gathered: 2026-07-10*
