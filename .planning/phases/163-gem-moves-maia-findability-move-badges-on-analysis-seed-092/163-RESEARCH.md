# Phase 163: Gem moves — Maia-findability move badges on /analysis - Research

**Researched:** 2026-07-10
**Domain:** Frontend-only React/TypeScript feature layered on the existing FlawChess Engine analysis-page plumbing (Maia policy probabilities + Stockfish grading union + expected-score sigmoid)
**Confidence:** HIGH (all touchpoints read in full; the one open architectural gap is called out explicitly below, not glossed over)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Qualification edges**
- D-01 Lost-position gems: KEEP. A best-try in a still-lost position (e.g. es 0.05 → 0.20 while every alternative sits at 0.05) qualifies — finding the only defensive resource deserves celebration. No "still losing after the move" exclusion (explicitly rejects Chesskit's rule). The es gap ≥ `MISTAKE_DROP` already guarantees the move mattered.
- D-02 No opening guard. No first-N-plies exclusion. Trust the free-lunch guards (sigmoid saturation, high Maia probability on forced/known moves); a rating-matched badge on a sharp theory move peers don't find is deserved. Revisit at UAT only if badge inflation appears.

**Rating source & whose moves**
- D-03 C1 uses the page's selected ELO — the same selected-ELO knob the Moves-by-Rating chart and findability ranking already use (slider/profile-driven). One ELO source for the whole page; badges legitimately update when the slider moves. NOT rating-at-game-time, NOT current_rating.
- D-04 Both players' moves get gems. Symmetric with the flaw-glyph pipeline (live flaw marks any move played on the board regardless of color). No color filter.

**Coverage, timing & stability**
- D-05 Any visited board move classifies — mainline game moves AND freely-explored variation moves, exactly mirroring the live-flaw glyph pipeline. Lazy, per visited position; no background full-game sweep (seed-locked).
- D-06 Same mechanism as free-move flaw tagging (user-locked, replaces the seed's open "min-depth stability gate" tunable). Mirror `useLiveMoveFlaw` + the `liveFlawByNode` pattern in Analysis.tsx: classify from a memo as soon as the required engine data exists (no explicit min-depth gate), live-updating while data streams, then made sticky per node via a `Map<NodeId, …>` cache at the Analysis level so navigation keeps the badge. Accepted caveats match the live-flaw ones (badge lags the move until data lands; early shallow data may classify slightly differently than a full-depth run would). C2 needs per-candidate grades of the parent position (the reconciled grading map over the union — see D-08), which in practice arrives with the grading run, so gems appear on roughly the grading-run cadence anyway.

**Threshold & calibration**
- D-07 `GEM_MAIA_MAX_PROB = 0.03` (3%) — single flat v1 constant (the seed's anchor value; user chose 3% over the stricter 2%). Named constant per project rules. No ELO-conditioned curve in this phase; do NOT reuse `P_REF_ANCHORS`.
- D-08 No calibration tooling in-phase. UAT eyeballs badge frequency; the iso-rarity threshold curve derivation is a deferred follow-up.

### Claude's Discretion
- Detection module location/shape (pure lib function + vitest, per project norms), including how C2 reads the Phase 162 reconciled grading map and how the free run's MultiPV=2 second line serves as pre-grading input, if at all.
- Glyph precedence markup: gem overrides the "best" bucket everywhere (seed-locked); how `MaiaMoveQualityBar` folds the gem bucket (presumably into the green "good" display segment) and how `UnifiedMovePopover` labels it.
- SVG-icon marker variant design in `boardMarkers.tsx` (lucide `Gem` path inside the existing circle-badge geometry) and the parallel move-list icon component alongside `SeverityGlyphIcon`.
- Popover/tooltip copy (seed suggests: "Gem — players at your rating almost never find this."); keep ≥ `text-sm` except inside the sanctioned info-popover pattern.
- Exact free-lunch-guard test fixtures (verify in tests, don't hand-code guards: saturation suppresses already-decided positions; forced recaptures excluded by C1).
- Cache invalidation details when the ELO slider moves (C1 re-derives; C2 grade cache untouched).

### Deferred Ideas (OUT OF SCOPE)
- **Iso-rarity threshold curve** (ELO-conditioned `GEM_MAIA_MAX_PROB`): after UAT, tabulate would-badge frequency per Maia rung on real games and derive a constant-badge-frequency curve from data instead of guessed anchors. Slope must INVERT vs `pRefForElo` (strict at low ELO, generous at high ELO). Not in this phase (D-07/D-08).
- **Calibration dev tooling** (per-rung badge-frequency tabulation helper) — rejected for this phase; build only if UAT eyeballing proves insufficient.
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` — unrelated, stays in the todo backlog.
</user_constraints>

<phase_requirements>
## Phase Requirements

No formal REQUIREMENTS.md IDs exist for this phase (project is between milestones — v2.0 closed 2026-07-09, no active milestone/REQUIREMENTS.md file). CONTEXT.md's `## Decisions` (D-01 through D-08) are the authoritative, ID-bearing acceptance criteria; the planner should track completion against those D-numbers directly, the same way Phase 162 did (its plan frontmatter cites `D-04, D-05, ...` as `requirements-completed`).

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Lost-position gems still qualify (no "still losing" exclusion) | C2's gap-only test (§ Code Examples); no extra guard needed |
| D-02 | No opening-ply guard | No extra guard needed; free-lunch guards below cover it |
| D-03 | C1 uses page's selected ELO, re-derives on slider change | `selectedElo` already threaded through Analysis.tsx to `MovesByRatingChart`/`MaiaMoveQualityBar`; gem memo must depend on it too |
| D-04 | Both colors get gems | `useLiveMoveFlaw`'s `active` gate has no color filter — mirror exactly |
| D-05 | Lazy per-visited-position classification, mainline + free variations | `liveFlawByNode`/`isOnPvLine`/`isGameMode` gating in Analysis.tsx (§ Architecture Patterns) |
| D-06 | No explicit min-depth gate; sticky per-node cache; C2 needs parent-position grading map | **Critical gap identified below** — parent-position Maia/grading data is NOT currently retained anywhere the page can read after navigation (§ Common Pitfalls, Pitfall 1) |
| D-07 | `GEM_MAIA_MAX_PROB = 0.03` named constant | Follows `flawThresholds.ts`/`moveQuality.ts` constant convention |
| D-08 | No calibration tooling this phase | N/A — nothing to build |
</phase_requirements>

## Summary

Gem detection is conceptually simple (two threshold checks reusing existing sigmoid/probability math) but its **data-availability architecture is the hard part**, and it is not obvious from the seed/CONTEXT alone. Both conditions (C1: Maia probability of the played move; C2: expected-score gap to the best alternative) must be evaluated **at the parent position** — the position *before* the graded move — using data that is normally only live while that parent position is the one currently displayed. By the time a move's badge needs to render (the child position is now current), `useMaiaEngine` and `useStockfishGradingEngine` have already moved on to analyzing the *child* FEN; their internal per-FEN caches exist but are not exposed for arbitrary historical lookups. Analysis.tsx already solves an analogous problem for live-flaw severity via a page-level FEN-keyed cache (`engineEvalByFen`) — the gem feature needs two siblings of that pattern (a Maia-curve-by-FEN cache and a best/second-best-ES-by-FEN cache), populated the moment each is available, read back once the user navigates to the child node.

**Primary recommendation:** Build a small pure library module (`frontend/src/lib/gemMove.ts`) exposing a single `classifyGem(...)` predicate that takes already-resolved primitives (played-move Maia probability, played move's ES, best-alternative ES, mover) — no engine/hook coupling — then wire it into Analysis.tsx via two new page-level FEN-keyed caches (`maiaCurveByFen: Map<string, MoveCurvePoint[]>`, `gradeSummaryByFen: Map<string, { bestSan, bestEs, secondBestEs }>`) populated via `useEffect`s mirroring the existing `engineEvalByFen` pattern, and a `gemByNode: Map<NodeId, true>` sticky cache mirroring `liveFlawByNode` exactly. Extend `MoveQuality` with a 6th `'gem'` bucket (never touch `FlawSeverity`), extend `SquareMarker` with an icon-content variant for the on-board badge, add a parallel `GemIcon` component alongside `SeverityGlyphIcon`, and thread `'gem'` through `colorForQuality`/`bucketKeyForQuality`/`qualityWord` as MAIA_ACCENT.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| C1/C2 threshold evaluation (pure math) | Browser / Client (lib function) | — | Pure, deterministic, no I/O — same tier as `classifyMoveQuality`/`classifyLiveSeverity` |
| Per-FEN historical data retention (Maia curve, grading summary) | Browser / Client (Analysis.tsx page state) | — | React state/refs, board-session-scoped, no persistence (mirrors `engineEvalByFen`) |
| Maia policy inference | Browser / Client (Web Worker) | — | `useMaiaEngine`'s existing ONNX worker; no change to the worker itself |
| Stockfish grading | Browser / Client (Web Worker) | — | `useStockfishGradingEngine`'s existing WASM worker; no change |
| Badge rendering (board marker, move-list glyph, chart curve, popover) | Browser / Client (React components) | — | `boardMarkers.tsx`, `SeverityGlyphIcon.tsx`-sibling, `MovesByRatingChart.tsx`, `MaiaMoveQualityBar.tsx`, `UnifiedMovePopover.tsx` |
| Persistence / cross-game statistics | — (explicitly none) | — | Phase boundary excludes backend changes and cross-game stats — nothing crosses to API/DB tier |

## Standard Stack

No new dependencies. This phase is 100% additive TypeScript/React using packages already in `frontend/package.json`.

### Core (already installed — reused, not added)
| Library | Version (installed) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `lucide-react` | ^1.21.0 | `Gem` icon for the board marker + move-list glyph | Already the project's icon library (`ChessKnight`, `Cpu`, `User` in `UnifiedMovePopover.tsx`); `Gem` confirmed present in the installed package (`node_modules/lucide-react/dist/esm/icons/gem.mjs`) `[VERIFIED: local node_modules inspection]` |
| `recharts` | existing | `MovesByRatingChart` curve recolor | Already the chart library in use; no new component needed, just a new `colorForQuality` branch |
| `vitest` | existing | Unit tests for the new pure `gemMove.ts` module | Project's sole test runner |

### Supporting
None needed — no new UI primitive libraries, no new state-management library. The feature is additive wiring through existing memo chains.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Page-level per-FEN caches (recommended) | Extend `useMaiaEngine`/`useStockfishGradingEngine` to expose their internal `cacheRef` for arbitrary-FEN lookups | Would centralize the cache in the hook (arguably cleaner ownership) but changes two hook *public APIs* that are Phase 151/151.1/158/162 load-bearing surfaces with many existing consumers/tests — higher blast radius for no functional gain, since the hooks' internal caches already hold exactly this data, just unexported. Page-level caches are strictly additive and touch zero existing hook code. |
| `MAIA_ACCENT` violet gem marker | A new distinct color | Seed-locked to `MAIA_ACCENT` — the whole positive-badge concept is framed as "Maia-findability," so violet reuse is intentional, not a placeholder |

**Installation:** none required.

### Version verification
No new packages recommended, so no registry check is required. `lucide-react`'s `Gem` export was verified present in the currently-installed `^1.21.0` tree via direct filesystem inspection (see table above) rather than a registry query, since the constraint is "does the already-pinned version export this icon," not "what's the latest version."

## Package Legitimacy Audit

**Not applicable — this phase installs no new packages.** `lucide-react` is an existing dependency (`frontend/package.json`); `Gem` is one of its ~1500 bundled icon exports, confirmed present locally. No `npm install` step, no Package Legitimacy Gate to run.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User navigates board (mainline step, PV replay, or free move)           │
└───────────────────────────────┬─────────────────────────────────────────┘
                                 │ position changes → currentNodeId, playedSan
                                 ▼
        ┌────────────────────────────────────────────────────┐
        │ WHILE position P is current (BEFORE the user moves  │
        │ on to P's child):                                   │
        │  useMaiaEngine(fen=P)      → maia.perElo (21 rungs)  │
        │  useStockfishGradingEngine │  grading.gradeMap       │
        │  (fen=P, candidateSans=    │  (candidate SAN → ES)   │
        │   unionSans)               │                         │
        └───────────────┬──────────────────────┬──────────────┘
                         │ effect: on every       │ effect: on every
                         │ (P, maia.perElo) change│ (P, grading.gradeMap) change
                         ▼                        ▼
              maiaCurveByFen.set(P, perElo) gradeSummaryByFen.set(P, {bestSan,
                    (NEW cache, mirrors               bestEs, secondBestEs})
                    engineEvalByFen)                  (NEW cache, mirrors
                                                        engineEvalByFen)
                         │                        │
                         │  user navigates P → child C (playedSan = move P→C)
                         ▼                        ▼
        ┌────────────────────────────────────────────────────┐
        │ gemCandidate memo (Analysis.tsx, current node = C): │
        │  parentFen = P (existing pattern, ~line 1203)       │
        │  maiaProb = nearestByElo(maiaCurveByFen.get(P),      │
        │             selectedElo)?.moveProbabilities[playedSan]│
        │  { bestSan, bestEs, secondBestEs } =                │
        │             gradeSummaryByFen.get(P)                │
        │  classifyGem(maiaProb, playedSan===bestSan,          │
        │              bestEs, secondBestEs) → boolean         │
        └───────────────┬──────────────────────────────────────┘
                         │ true → sticky
                         ▼
              gemByNode.set(C, true)   (NEW, mirrors liveFlawByNode
                                         Map<NodeId,...> pattern)
                         │
                         ▼
        ┌────────────────────────────────────────────────────┐
        │ Rendering (all read gemByNode.has(nodeId)):          │
        │  - squareMarkers: gem-variant SquareMarker on board  │
        │  - VariationTree: GemIcon glyph in move list         │
        │  - MovesByRatingChart: colorForQuality('gem')=       │
        │    MAIA_ACCENT curve + tooltip label                 │
        │  - MaiaMoveQualityBar: bucketKeyForQuality('gem')    │
        │    folds into 'good' segment (or new segment)        │
        │  - Popover: short "Gem" copy                          │
        └────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
frontend/src/
├── lib/
│   ├── gemMove.ts              # NEW — classifyGem() + GEM_MAIA_MAX_PROB constant, pure
│   ├── moveQuality.ts          # MODIFIED — MoveQuality gains 'gem'; classifyMoveQuality gem-override
│   ├── liveFlaw.ts             # unchanged — evalToExpectedScore/MISTAKE_DROP reused verbatim
│   └── severityGlyph.ts        # sibling pattern only — do NOT extend (FlawSeverity stays 3-value)
├── components/
│   ├── board/boardMarkers.tsx  # MODIFIED — SquareMarker icon-content variant for gem
│   ├── icons/
│   │   ├── SeverityGlyphIcon.tsx  # unchanged
│   │   └── GemIcon.tsx            # NEW — lucide Gem in a MAIA_ACCENT circle, SeverityGlyphIcon-shaped
│   └── analysis/
│       ├── MovesByRatingChart.tsx   # MODIFIED — colorForQuality/qualityWord gain 'gem' → MAIA_ACCENT
│       ├── MaiaMoveQualityBar.tsx   # MODIFIED — bucketKeyForQuality folds 'gem'
│       ├── VariationTree.tsx        # MODIFIED — move-list gem glyph alongside BlunderIcon/MistakeIcon
│       └── UnifiedMovePopover.tsx   # POSSIBLY MODIFIED — gem copy line (Claude's discretion)
├── pages/Analysis.tsx          # MODIFIED — 2 new per-FEN caches, gemByNode sticky cache, squareMarkers union
└── lib/__tests__/gemMove.test.ts  # NEW — pure unit tests
```

### Pattern 1: Pure classification predicate, no engine coupling
**What:** `classifyGem` takes already-resolved numbers, never a hook/engine object — mirrors `classifyLiveSeverity(esBefore, esAfter)`'s shape exactly (2-3 primitive args in, an enum/boolean out).
**When to use:** Any classification math in this codebase — keeps the function trivially unit-testable without mocking workers (project convention, confirmed by `moveQuality.test.ts`'s "pure, deterministic, no engine/worker involved" docstring).
**Example:**
```typescript
// Proposed: frontend/src/lib/gemMove.ts
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { MISTAKE_DROP } from '@/generated/flawThresholds';

/** Maia policy-probability ceiling for C1 (D-07) — strict-side v1 constant. */
export const GEM_MAIA_MAX_PROB = 0.03;

/**
 * C1 (hard to find) AND C2 (only good move). Callers resolve the played
 * move's Maia probability and the parent position's best/second-best
 * expected score BEFORE calling this — this function does no lookups.
 */
export function classifyGem(params: {
  maiaProbability: number | null;   // played move's prob at the rating-matched rung
  playedIsBest: boolean;            // played move === argmax over the parent's graded candidates
  bestEs: number | null;            // parent position's top expected score (mover POV)
  secondBestEs: number | null;      // parent position's runner-up expected score (mover POV)
}): boolean {
  const { maiaProbability, playedIsBest, bestEs, secondBestEs } = params;
  if (maiaProbability === null || maiaProbability > GEM_MAIA_MAX_PROB) return false;
  if (!playedIsBest || bestEs === null || secondBestEs === null) return false;
  return bestEs - secondBestEs >= MISTAKE_DROP;
}
```

### Pattern 2: Page-level per-FEN retention cache (mirrors `engineEvalByFen`)
**What:** A `Map<fen, T>` populated by a `useEffect` keyed on `[position, sourceData]`, FIFO-capped like every other cache in this file (`LIVE_EVAL_CACHE_MAX`, `MAIA_CACHE_MAX`, `GRADE_CACHE_MAX`).
**When to use:** Whenever a hook only exposes CURRENT-position data but a later node needs to read an EARLIER position's data (this is the crux of the gem feature — see Common Pitfalls, Pitfall 1).
**Example:**
```typescript
// Existing precedent in Analysis.tsx (~1185-1200) — the pattern to copy verbatim:
const [engineEvalByFen, setEngineEvalByFen] = useState<Map<string, {cp, mate}>>(() => new Map());
useEffect(() => {
  if (!engineEnabled) return;
  setEngineEvalByFen((prev) => {
    const next = new Map(prev);
    next.set(position, { cp: engine.evalCp, mate: engine.evalMate });
    if (next.size > LIVE_EVAL_CACHE_MAX) {
      const oldest = next.keys().next().value;
      if (oldest !== undefined) next.delete(oldest);
    }
    return next;
  });
}, [position, engine.evalCp, engine.evalMate, engineEnabled]);

// NEW siblings needed for gem detection (same shape, different payload):
// maiaCurveByFen: Map<string, MoveCurvePoint[]>  — effect deps [position, maia.perElo, maiaEnabled]
// gradeSummaryByFen: Map<string, {bestSan: string|null, bestEs: number|null, secondBestEs: number|null}>
//   — effect deps [position, qualityBySan, gradingEnabled] (derive best/2nd-best from qualityBySan,
//   which is ALREADY the reconciled per-SAN ES map computed at Analysis.tsx:1006-1032)
```

### Pattern 3: Sticky per-node classification cache (mirrors `liveFlawByNode`)
**What:** A `Map<NodeId, true>` (or `Map<NodeId, GemInfo>`) written once a node's classification resolves, read on every render thereafter regardless of navigation — this is what makes the badge "stick" once computed instead of disappearing when the user steps away and the live memo's inputs change.
**When to use:** Exactly the D-06-mandated mechanism. Copy `liveFlawByNode`'s effect (Analysis.tsx:1254-1271) structure: gate on `active`/`currentNodeId`, only insert when the classification is affirmatively true (never overwrite with a "not a gem" negative — mirrors "only blunder/mistake paint a glyph; skip while still pending").
**Example:** see Analysis.tsx:1251-1271 (already read in full — the literal template).

### Pattern 4: Icon-content board marker (extends `boardMarkers.tsx`)
**What:** `SquareMarker` currently hard-codes a text glyph (`SEVERITY_GLYPH[marker.severity].symbol`) rendered via `<text>`. Gem needs an SVG icon (lucide `Gem`'s path data) inside the same circle geometry, not a text character.
**When to use:** The board-corner badge only; the move-list glyph is a separate, already-icon-shaped component (`SeverityGlyphIcon.tsx`'s `GlyphBadge` factory already renders `<svg><circle/><text/></svg>` — a gem sibling swaps `<text>` for lucide's path).
**Example:**
```typescript
// boardMarkers.tsx's SquareMarker today (severity-only):
export interface SquareMarker {
  square: string;
  severity: FlawSeverity;
  label?: string;
  labelColor?: string;
}
// Proposed extension — a discriminated union or an additive optional field
// (planner's call; additive is lower-risk since severity is still required
// by every existing call site):
export interface SquareMarker {
  square: string;
  severity?: FlawSeverity;   // now optional — mutually exclusive with `gem`
  gem?: boolean;             // NEW — renders the icon-content variant instead
  label?: string;
  labelColor?: string;
}
// SquareMarkerBadge then branches: marker.gem ? <GemBadgeContent .../> : <text>{glyph.symbol}</text>
// GemBadgeContent inlines lucide's Gem SVG path (import { Gem } from 'lucide-react' won't
// drop cleanly into a raw <svg><g> tree the same way — either render <Gem/> nested inside
// the existing <svg> viewBox with a transform, or hand-copy its path data as boardMarkers.tsx
// already hand-draws severity glyphs "from scratch" rather than importing a component tree
// (see SeverityGlyphIcon.tsx's own docstring rationale for drawing from scratch).
```

### Anti-Patterns to Avoid
- **Re-deriving the argmax independently per gem call site.** Phase 162's entire RESEARCH/CONTEXT explicitly forbids re-deriving an argmax at each display consumer — the project now has ONE canonical `resolveReconciledBest`/`qualityBySan` pattern. Gem's C2 "best alternative" must read from the SAME `qualityBySan`/`evalLookup` machinery (via the new `gradeSummaryByFen` cache), never a fresh loop over raw grades.
- **Extending `FlawSeverity` with a positive value.** `FlawSeverity` is the cross-stack backend contract (`app/services/flaws_service.py`'s enum mirror) — locked negative-only by CONTEXT.md and by existing project convention (`moveQuality.ts`'s own docstring: "FlawSeverity...must NOT be extended"). Gem is `MoveQuality`-only.
- **Computing C1/C2 using the CURRENT position's Maia/grading data for the played-move-that-reached-this-node.** This is the single most likely implementation bug (see Pitfall 1) — the data needed is the PARENT's, not the current node's.
- **Reusing `P_REF_ANCHORS`/`pRefForElo` for the threshold.** CONTEXT.md D-07 explicitly forbids this — that curve's slope is inverted vs. what a future gem threshold curve would need, and this phase ships a flat constant anyway.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Score-drop / expected-score math | A new sigmoid or cp→probability conversion | `evalToExpectedScore` (`@/lib/liveFlaw`) | Already the project's ONLY sigmoid; re-deriving risks a `LICHESS_K` mismatch |
| "Is this the best move" determination | A fresh argmax loop over grades | `qualityBySan`'s existing 'best' bucket (or `resolveReconciledBest`/`evalLookup`) | Phase 162 built exactly this reconciled single-source-of-truth; gem C2 is "is `playedSan` the `best`-bucket move, with a big enough gap" |
| Maia probability lookup at a given ELO | A fresh `nearestByElo` reimplementation | `nearestByElo` exported from `moveQuality.ts` (already used by `useMaiaEngine.ts`'s own internal copy and `positionVerdict.ts`) | One canonical rung-lookup, per project convention |
| SAN↔UCI conversion for the played move | A new conversion helper | `sanToUci`/`bestSanFromPv` (already imported everywhere in Analysis.tsx/engineEvalLookup.ts) | Established single-source pattern |
| Icon-badge SVG geometry (circle sizing, corner offset) | New geometry constants | `boardMarkers.tsx`'s existing `MARKER_RADIUS`/`MARKER_CORNER_OVERLAP`/`GLYPH_VIEWBOX_DIAMETER` | Gem is a same-shape sibling — only the fill content (icon vs. text) changes |

**Key insight:** Every piece of MATH this phase needs already exists in the codebase (sigmoid, argmax, rung-lookup, SAN/UCI conversion). The actual net-new work is (1) a small pure predicate function threading those existing primitives together, and (2) the data-retention plumbing to make PARENT-position values available at CHILD-position render time — which is a wiring/caching problem, not a math problem.

## Common Pitfalls

### Pitfall 1: Parent-position data is not retained anywhere the page can read after navigation (CRITICAL — read before planning)
**What goes wrong:** A naive implementation reads `maia.perElo` / `grading.gradeMap` / `qualityBySan` directly inside the gem-classification memo, exactly like `qualityBySan` itself does for the chart. This works for chart/bar rendering (which describes candidates FROM the current position) but is wrong for gem detection, which must classify the move that led INTO the current position — i.e., needs the PARENT's candidate data, not the current node's.
**Why it happens:** `useMaiaEngine` and `useStockfishGradingEngine` are both single-position hooks: they hold an internal FIFO cache keyed by FEN (`cacheRef` in both hooks, confirmed by direct reads of `useMaiaEngine.ts:121` and `useStockfishGradingEngine.ts:136`), but neither EXPOSES that cache — their public `perElo`/`gradeMap` return values only ever reflect the FEN currently passed in as `fen`. Once the user navigates from parent P to child C, both hooks re-target C; P's data is gone from the hooks' public surface (even though it may still live in their private caches, inaccessible to the page).
**How to avoid:** Build the two page-level per-FEN caches described in Pattern 2 (`maiaCurveByFen`, `gradeSummaryByFen`), populated via `useEffect`s that fire *while each position is current* — exactly mirroring the already-proven `engineEvalByFen` pattern at Analysis.tsx:1185-1200. Read from these caches (keyed by `parentFen`, which Analysis.tsx already computes at line 1203) when classifying the CURRENT node's arrival move.
**Warning signs:** A gem badge that only ever appears on moves played FROM a position where Maia/grading happened to still be running at the moment of navigation (i.e., gems that flicker in only when the user pauses on the position AFTER the gem move) is a sure sign the classification is reading current-node data as a substitute for parent-node data.

### Pitfall 2: `playedSan` is a property of the CURRENT node, not a "next move" lookahead
**What goes wrong:** Confusing `playedSan` (Analysis.tsx:743, "the SAN of the move that reached the current node") with a forward-looking "move about to be played." The gem-classification target move for node C IS `nodes.get(C)?.san` — the move FROM parent(C) TO C — which is exactly the existing `playedSan` when C is current. This part is actually already correct/available; the risk is a planner assuming a NEW field is needed here when it isn't.
**Why it happens:** The name "playedSan" is used elsewhere in the file for chart emphasis (highlighting a candidate line that matches the played move), which reads as "a candidate for the current position," creating ambiguity.
**How to avoid:** Re-derive from the `GameNode` type directly (`san: string // SAN of the move that reached this position`, confirmed in `useAnalysisBoard.ts:25`) when writing the gem memo's own docstring, rather than reusing the page's existing `playedSan` variable without re-verifying it means the same thing in this new context (it does, but a future reader needs the same confirmation this research just performed).

### Pitfall 3: `selectCandidatesByMass`'s union may not include the gem candidate at the PARENT position — but it's fine because it always includes `bestSan`
**What goes wrong:** Worrying that a rare (<3% Maia probability) move won't be in the grading union at the parent position, so its ES never gets computed there.
**Why it happens:** `selectCandidatesByMass` caps the Maia mass-set at `CUMULATIVE_MASS_THRESHOLD=0.95` — a 3%-probability move could plausibly fall outside that cut.
**How to avoid:** No new guard needed. `selectCandidatesByMass` unconditionally adds `bestSan` (the engine's own top move) to the returned set (moveQuality.ts:156, `if (bestSan != null) keep.add(bestSan)`), and — critically — C2 can only be satisfied when the played move IS the engine's best move (gap-to-second-best requires it to already be #1). So any move that could pass C2 was, by construction, already unioned in via `bestSan` regardless of its Maia rarity. The genuine risk is TIMING (Pitfall 1), not coverage.

### Pitfall 4: Chart-quality-bucket "fold" vs. the standalone gem-badge concept must not merge into the same enum carelessly
**What goes wrong:** Treating `'gem'` as just another `MoveQuality` bucket value everywhere, including inside `bucketMovesByQuality`'s `bucketKeyForQuality` switch (which currently maps every `MoveQuality` to one of 5 DISPLAY buckets: blunder/mistake/inaccuracy/good/pending) without deciding whether gem needs its own display segment or folds into 'good'.
**Why it happens:** `MoveQuality` (grader-level, 5 buckets today) and `QualityBucketKey` (display-level, 5 buckets today, DIFFERENT enum) are two separate types that happen to share some names — easy to conflate.
**How to avoid:** CONTEXT.md leaves this explicitly to Claude's Discretion ("presumably into the green 'good' display segment") — the planner should pick one and document the choice, not leave `bucketKeyForQuality`'s `default` case to silently swallow `'gem'` into `'pending'` (a real risk: the `switch` in moveQuality.ts:197-211 has cases for `'best'|'good'` → `'good'` and a catch-all `default: return 'pending'` — an unmodified switch would silently misclassify every gem as "pending" in the quality bar).

### Pitfall 5: `MoveQuality`'s "gem overrides best" must not break `classifyMoveQuality`'s bestSan-pin bug it exists to prevent
**What goes wrong:** `classifyMoveQuality` currently has ONE designated best (`bestSan`/`reconciledBestSan`), single-valued, feeding the chart's Best label + emphasis stroke (Phase 162's whole precedence-flip fight was about keeping this singular). If gem detection changes which move is labeled the chart's "Best" (e.g., relabeling the reconciled-best move as `'gem'` instead of `'best'`), every downstream consumer that special-cases the literal string `'best'` (the arrow, verdict, `qualityWord`, `bucketKeyForQuality`) must also handle `'gem'` as an equivalent-or-supersedes case, or those consumers silently regress (e.g., `qualityWord` would print "Gem" — fine — but an arrow/verdict piece checking `quality === 'best'` explicitly would stop firing).
**How to avoid:** Audit every `=== 'best'` / `case 'best':` string check across `moveQuality.ts`, `MovesByRatingChart.tsx`, `MaiaMoveQualityBar.tsx` during planning (this research found `bucketKeyForQuality`'s `case 'best':` at moveQuality.ts:205 as the one that needs updating; `colorForQuality`'s `case 'best':` at MovesByRatingChart.tsx:181 likewise). Treat this as a required Task-level checklist item, not an incidental find-during-implementation risk.

### Pitfall 6: ELO-slider re-derivation of C1 must not silently invalidate C2's cache too
**What goes wrong:** CONTEXT.md's "Cache invalidation details when the ELO slider moves (C1 re-derives; C2 grade cache untouched)" is a Claude's-Discretion item, but an implementation that ties BOTH caches to `selectedElo` in their effect dependency arrays would cause `gradeSummaryByFen` (which is ELO-independent — grading is position-only, confirmed by `useStockfishGradingEngine.ts`'s own docstring "Grades are position-only (ELO-independent)") to unnecessarily recompute/re-key on every slider tick.
**How to avoid:** Keep `gradeSummaryByFen`'s effect deps ELO-free (`[position, qualityBySan, gradingEnabled]`); only the FINAL `classifyGem` memo (or the `gemByNode` write-effect) should depend on `selectedElo`, re-reading the ALREADY-cached `maiaCurveByFen` at a different rung — never re-fetching Maia.

## Code Examples

### Gem-candidate memo sketch (Analysis.tsx, new — approximate shape only, planner finalizes exact wiring)
```typescript
// Source: derived from Analysis.tsx's existing liveFlaw/liveFlawByNode pattern (1233-1271)
// and qualityBySan (1006-1032) — not a literal existing file, a research sketch.
const gemCandidate = useMemo<boolean>(() => {
  if (currentNodeId === null || parentFen === null) return false;
  const playedSanForGem = nodes.get(currentNodeId)?.san ?? null; // Pitfall 2
  if (playedSanForGem === null) return false;

  const parentCurve = maiaCurveByFen.get(parentFen);
  const rung = parentCurve ? nearestByElo(parentCurve, selectedElo) : undefined; // D-03
  const maiaProbability = rung?.moveProbabilities[playedSanForGem] ?? null;

  const summary = gradeSummaryByFen.get(parentFen);
  return classifyGem({
    maiaProbability,
    playedIsBest: summary?.bestSan === playedSanForGem,
    bestEs: summary?.bestEs ?? null,
    secondBestEs: summary?.secondBestEs ?? null,
  });
}, [currentNodeId, parentFen, nodes, maiaCurveByFen, selectedElo, gradeSummaryByFen]);
```

### `gradeSummaryByFen` derivation from the EXISTING `qualityBySan` (avoids a second grading pass)
```typescript
// qualityBySan (Analysis.tsx:1006-1032) already computes, for the CURRENT position,
// a Map<san, {quality, evalCp, evalMate}> where exactly one entry has quality==='best'.
// Deriving {bestSan, bestEs, secondBestEs} from it is a single pass, no new engine call:
function summarizeForGem(
  qualityBySan: Map<string, MoveQualityEval>,
  mover: MoverColor,
): { bestSan: string | null; bestEs: number | null; secondBestEs: number | null } {
  let bestSan: string | null = null;
  let bestEs = -Infinity;
  let secondBestEs = -Infinity;
  for (const [san, info] of qualityBySan) {
    const es = evalToExpectedScore(info.evalCp, info.evalMate, mover);
    if (es > bestEs) {
      secondBestEs = bestEs;
      bestEs = es;
      bestSan = san;
    } else if (es > secondBestEs) {
      secondBestEs = es;
    }
  }
  return {
    bestSan,
    bestEs: bestSan !== null ? bestEs : null,
    secondBestEs: secondBestEs > -Infinity ? secondBestEs : null,
  };
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| No positive-move badge existed pre-Phase 163 | `MoveQuality` gains a 6th `'gem'` bucket alongside best/good/inaccuracy/mistake/blunder | This phase | First positive-signal badge on `/analysis`; establishes the pattern for any future positive badges |

**Deprecated/outdated:** None — this phase is purely additive; no existing behavior is removed or replaced.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `maskAndSoftmax` (maiaEncoding.ts:234) returns probabilities for ALL legal moves at a position (not just a top-K subset), so a rare gem-candidate move's C1 probability is always computable once Maia has analyzed the parent position | Common Pitfalls, Summary | `[VERIFIED: local source read — maiaEncoding.ts:237 calls chess.moves({verbose:true}) with no truncation before scoring]` — low risk, but flag if a future Maia model version truncates its output |
| A2 | The recommended page-level cache approach (Pattern 2) is lower-risk than extending the two hooks' public APIs | Standard Stack, Alternatives Considered | If the planner instead chooses to expose the hooks' internal caches, the wiring differs materially — worth an explicit go/no-go decision at plan time rather than assuming Pattern 2 |
| A3 | No formal REQUIREMENTS.md IDs exist for this phase (project between milestones) | Phase Requirements | If a REQUIREMENTS.md is created before planning, the D-numbers should be cross-mapped to formal IDs |

## Open Questions

1. **Should `gradeSummaryByFen` store the full per-SAN ES map, or just `{bestSan, bestEs, secondBestEs}`?**
   - What we know: Only best/second-best is needed for C2's gap check.
   - What's unclear: Whether a future UAT iteration (e.g., "show the alternatives that would have been mistakes" in the popover copy) wants the full candidate list.
   - Recommendation: Store the reduced form (3 fields) for this phase — cheaper, and D-08 explicitly defers richer calibration/UI to a follow-up. Expand later if UAT asks for it.

2. **Does the gem board marker replace or coexist with the severity marker on the SAME square?**
   - What we know: A move can't be both a gem (C2 requires it to be objectively best) and a blunder/mistake/inaccuracy (which by definition means NOT best) — so they're mutually exclusive in practice for the SAME move.
   - What's unclear: Whether `squareMarkers` assembly needs an explicit runtime assertion of this exclusivity, or whether it's simply structurally impossible given the classification logic (making an assertion redundant).
   - Recommendation: Rely on structural impossibility (a gem is always `quality==='gem'` which by construction can't also be a `FlawSeverity`), but add one unit test asserting `classifyGem` never returns true when `classifyLiveSeverity` would also fire for the same move, as a regression guard.

3. **Where exactly does the "gem overrides best" precedence surface for `qualityBySan`'s consumers?**
   - What we know: CONTEXT.md locks "gem overrides its 'best' output" in `classifyMoveQuality`.
   - What's unclear: Whether `classifyMoveQuality` itself computes the gem bucket (requiring it to accept Maia probability + parent-vs-current distinction as new parameters, complicating its currently pure "grade a single position's candidates" signature) or whether Analysis.tsx post-processes `qualityBySan`'s output, swapping `'best'` for `'gem'` on the specific SAN that satisfied `classifyGem` in a separate pass.
   - Recommendation: Keep `classifyMoveQuality` unchanged (single-position, no gem awareness) and have Analysis.tsx overlay the gem override in a thin wrapper/derived memo — `classifyMoveQuality` already has zero knowledge of "the parent position" or "Maia probability," and forcing it to gain that knowledge would break its current pure, single-FEN-scoped signature and its existing unit tests' fixtures.

## Environment Availability

Skipped — this phase has no external service/tool dependencies beyond the already-running frontend dev toolchain (npm/vitest/tsc), which prior phases (151–162) have already exercised successfully in this same environment.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (existing, `frontend/package.json` `"test": "vitest run"`) |
| Config file | `frontend/vitest.config.ts` (existing) |
| Quick run command | `npx vitest run src/lib/__tests__/gemMove.test.ts` |
| Full suite command | `npm test -- --run` (from `frontend/`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | Lost-position gem still qualifies (es 0.05→0.20 vs alternatives at 0.05) | unit | `npx vitest run src/lib/__tests__/gemMove.test.ts` | ❌ new file |
| D-02 | No opening-guard exclusion — a move satisfying C1+C2 at ply 2 still qualifies | unit | same file | ❌ new file |
| D-03 | `classifyGem`/gem memo re-evaluates C1 at a different ELO rung when `selectedElo` changes | unit + integration | `gemMove.test.ts` (pure) + `Analysis.test.tsx` (wiring) | ❌ new / existing file extended |
| D-04 | Gem fires for both white and black played moves | unit | `gemMove.test.ts` | ❌ new file |
| D-05 | Gem classification fires for mainline AND freely-explored/PV nodes | integration | `Analysis.test.tsx` (extend "Grading run gating" or a new describe block) | existing file, ✅ |
| D-06 | Sticky per-node cache persists a gem badge across navigation away and back | integration | `Analysis.test.tsx` | existing file, ✅ |
| D-07 | `GEM_MAIA_MAX_PROB` constant is exactly 0.03 and is imported (not inlined) at every use site | unit | `gemMove.test.ts` (constant assertion, mirrors `moveQuality.test.ts`'s existing `CUMULATIVE_MASS_THRESHOLD`/`CANDIDATE_HARD_CAP` constant-assertion tests) | ❌ new file |
| Free-lunch guard 1 (saturation) | A move at +800cp vs. the position's own +400cp alternative does NOT qualify (gap negligible in ES space near saturation) | unit | `gemMove.test.ts` | ❌ new file |
| Free-lunch guard 2 (forced recapture) | A forced-recapture move with high Maia probability does NOT qualify (fails C1) | unit | `gemMove.test.ts` | ❌ new file |

### Sampling Rate
- **Per task commit:** `npx vitest run src/lib/__tests__/gemMove.test.ts src/pages/__tests__/Analysis.test.tsx`
- **Per wave merge:** `npm test -- --run` (full frontend suite) + `npx tsc -b` + `npm run lint` + `npm run knip`
- **Phase gate:** Full suite green before `/gsd-verify-work`; live-browser UAT for the visual badge (board marker placement, chart curve color, popover copy) since jsdom cannot fully validate SVG/circle geometry rendering (Phase 162's own precedent — the arrow-provenance test needed a `clientWidth` spy workaround for exactly this reason).

### Wave 0 Gaps
- [ ] `frontend/src/lib/__tests__/gemMove.test.ts` — new file, covers `classifyGem` + `GEM_MAIA_MAX_PROB` constant + both free-lunch guards
- [ ] Extend `frontend/src/lib/__tests__/moveQuality.test.ts` — gem-override behavior in `classifyMoveQuality` (or its wrapper, per Open Question 3's resolution) and `bucketKeyForQuality`'s new `'gem'` case (Pitfall 4)
- [ ] Extend `frontend/src/pages/__tests__/Analysis.test.tsx` — `gemByNode` sticky-cache integration test (mirrors the existing `liveFlawByNode`-adjacent tests), squareMarkers gem-variant assembly
- [ ] Extend `frontend/src/components/board/__tests__/boardMarkers.test.tsx` (if it exists — verify during planning) or create one — the new icon-content `SquareMarker` variant
- Framework install: none — Vitest already configured.

## Security Domain

**Not applicable in the standard sense — this phase adds a purely presentational, client-side-computed badge with no new trust boundary, no user input, no auth/session surface, and no new data leaving or entering the browser.** All inputs (FEN strings, engine evals, Maia probabilities) are already-trusted, already-flowing-through-the-page values computed entirely client-side from the SAME sources every other on-page badge already reads. There is no new ASVS category exposure versus what Phases 151–162 already established for this page.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | unchanged — page-level auth gating (if any) is untouched |
| V3 Session Management | no | unchanged |
| V4 Access Control | no | unchanged |
| V5 Input Validation | no | no new external input; FEN/eval data is engine-generated, not user-typed |
| V6 Cryptography | no | not applicable |

## Sources

### Primary (HIGH confidence)
- Direct source reads (all files read in full or targeted-section during this research session): `frontend/src/lib/moveQuality.ts`, `frontend/src/hooks/useLiveMoveFlaw.ts`, `frontend/src/lib/severityGlyph.ts`, `frontend/src/components/board/boardMarkers.tsx`, `frontend/src/components/icons/SeverityGlyphIcon.tsx`, `frontend/src/components/analysis/MovesByRatingChart.tsx`, `frontend/src/lib/liveFlaw.ts`, `frontend/src/hooks/useMaiaEngine.ts`, `frontend/src/hooks/useStockfishGradingEngine.ts`, `frontend/src/lib/engineEvalLookup.ts`, `frontend/src/lib/engine/findability.ts`, `frontend/src/generated/flawThresholds.ts`, `frontend/src/pages/Analysis.tsx` (lines 300-1080, 1180-1350), `frontend/src/types/library.ts`, `frontend/src/lib/theme.ts` (color constants), `frontend/src/components/analysis/MaiaMoveQualityBar.tsx`, `frontend/src/components/analysis/UnifiedMovePopover.tsx`, `frontend/src/components/analysis/VariationTree.tsx` (grep), `frontend/src/hooks/useAnalysisBoard.ts` (GameNode shape), `frontend/src/lib/maiaEncoding.ts` (maskAndSoftmax legal-move scope).
- `.planning/seeds/SEED-092-gem-moves-maia-findability-badges.md` — the design source.
- `.planning/phases/163-.../163-CONTEXT.md` — locked decisions.
- `.planning/phases/162-.../162-CONTEXT.md`, `162-PATTERNS.md`, `162-03-SUMMARY.md` — prior-phase architecture this phase builds on (reconciled grading map, `qualityBySan`, `evalLookup`).

### Secondary (MEDIUM confidence)
- `node_modules/lucide-react` local filesystem inspection confirming `Gem` icon export in the installed `^1.21.0` version.

### Tertiary (LOW confidence)
- None — no WebSearch was needed for this phase; every question was answerable from the codebase itself and CONTEXT.md/SEED-092.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, `Gem` icon presence verified locally.
- Architecture: HIGH for the rendering/glyph side (direct precedent in `boardMarkers.tsx`/`SeverityGlyphIcon.tsx`); MEDIUM-HIGH for the parent-position data-retention design (Pattern 2/Pitfall 1) — the *problem* is confirmed with certainty (read both hooks' source in full), the *specific two-new-caches solution* is this research's recommendation, not an existing committed pattern, so the planner should treat it as a strong starting point, not gospel.
- Pitfalls: HIGH — every pitfall listed is grounded in a specific line-numbered source read, not speculation.

**Research date:** 2026-07-10
**Valid until:** 30 days (stable, no fast-moving external dependency; the codebase itself could shift if another phase touches these same files first)
