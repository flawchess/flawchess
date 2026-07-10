# Phase 163: Gem moves — Pattern Map

**Mapped:** 2026-07-10
**Files analyzed:** 11 (new + modified)
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/lib/gemMove.ts` (NEW) | utility (pure predicate) | transform | `frontend/src/lib/liveFlaw.ts` (`classifyLiveSeverity`) | exact |
| `frontend/src/lib/__tests__/gemMove.test.ts` (NEW) | test | transform | `frontend/src/lib/__tests__/moveQuality.test.ts` | exact |
| `frontend/src/lib/moveQuality.ts` (MODIFIED) | utility | transform | itself (extend `MoveQuality`, `bucketKeyForQuality`) | exact |
| `frontend/src/components/board/boardMarkers.tsx` (MODIFIED) | component (SVG overlay) | request-response (render) | itself (`SquareMarkerBadge`) | exact |
| `frontend/src/components/icons/GemIcon.tsx` (NEW) | component | request-response (render) | `frontend/src/components/icons/SeverityGlyphIcon.tsx` | exact |
| `frontend/src/lib/severityGlyph.ts` (reference, NOT extended) | utility (lookup table) | transform | n/a — sibling record for gem lives elsewhere (see below) | role-match |
| `frontend/src/components/analysis/MovesByRatingChart.tsx` (MODIFIED) | component (chart) | transform + render | itself (`colorForQuality`, `qualityWord`) | exact |
| `frontend/src/components/analysis/MaiaMoveQualityBar.tsx` (MODIFIED) | component | transform + render | `moveQuality.ts`'s `bucketKeyForQuality`/`bucketMovesByQuality` (consumed here) | exact |
| `frontend/src/components/analysis/VariationTree.tsx` (MODIFIED) | component (move list) | render | itself (`SeverityIcon` selection pattern, lines ~501-502, 586-587, 726-732) | exact |
| `frontend/src/components/analysis/UnifiedMovePopover.tsx` (MODIFIED) | component (popover) | render | itself (existing lucide icon imports + `MAIA_ACCENT` usage) | exact |
| `frontend/src/pages/Analysis.tsx` (MODIFIED) | page/controller | event-driven (streaming engine data → memo → sticky cache) | itself (`engineEvalByFen` cache, `liveFlawByNode` sticky cache, `useLiveMoveFlaw` wiring) | exact |

## Pattern Assignments

### `frontend/src/lib/gemMove.ts` (NEW — utility, transform)

**Analog:** `frontend/src/lib/liveFlaw.ts` (`classifyLiveSeverity`, lines 105-115) and `frontend/src/lib/moveQuality.ts` (module docstring + constants pattern, lines 1-59)

**Imports pattern** (mirror `liveFlaw.ts` lines 15-24):
```typescript
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { MISTAKE_DROP } from '@/generated/flawThresholds';
```
Generated-threshold constants are imported from `@/generated/flawThresholds`, never hand-copied — same convention `liveFlaw.ts` uses for `BLUNDER_DROP`/`MISTAKE_DROP`/`INACCURACY_DROP`/`MATE_CP_EQUIVALENT`/`LICHESS_K`.

**Named-constant pattern** (mirror `moveQuality.ts` lines 53-59):
```typescript
/** Maia cumulative-probability mass cutoff at the selected ELO (D-02). */
export const CUMULATIVE_MASS_THRESHOLD = 0.95;
/** Hard cap on displayed candidate lines after the mass cut (D-06). */
export const CANDIDATE_HARD_CAP = 5;
```
Gem's sibling: `export const GEM_MAIA_MAX_PROB = 0.03;` — a top-of-file exported const with a one-line docstring citing the CONTEXT.md decision ID (D-07), exactly this shape.

**Core pure-predicate pattern** (mirror `classifyLiveSeverity`, `liveFlaw.ts` lines 105-115):
```typescript
export function classifyLiveSeverity(esBefore: number, esAfter: number): FlawSeverity | null {
  const drop = esBefore - esAfter;
  if (drop >= BLUNDER_DROP) return 'blunder';
  if (drop >= MISTAKE_DROP) return 'mistake';
  if (drop >= INACCURACY_DROP) return 'inaccuracy';
  return null;
}
```
`classifyGem` should follow the exact same shape: primitive numeric/boolean args in, no lookups, no hook/engine coupling (RESEARCH's Pattern 1, already includes a full sketch — reuse verbatim).

**Error handling:** None needed — pure math over already-validated primitives (nulls handled via early-return, same as `classifyLiveSeverity` returning `null` for "no classification").

---

### `frontend/src/lib/__tests__/gemMove.test.ts` (NEW — test)

**Analog:** `frontend/src/lib/__tests__/moveQuality.test.ts`

Read that file's structure before writing (not re-read here to save budget, but the RESEARCH doc already documents its "pure, deterministic, no engine/worker involved" docstring convention and its existing constant-assertion tests for `CUMULATIVE_MASS_THRESHOLD`/`CANDIDATE_HARD_CAP` — mirror that exact pattern for a `GEM_MAIA_MAX_PROB === 0.03` assertion). Use `describe`/`it` blocks per D-number (D-01 lost-position, D-02 no-opening-guard, D-04 color-symmetry, free-lunch guard 1 saturation, free-lunch guard 2 forced-recapture) so the test file structure traces 1:1 to the Phase Requirements table in RESEARCH.md.

---

### `frontend/src/lib/moveQuality.ts` (MODIFIED)

**Analog:** itself — extend in place, do not fork.

**Type extension** (line 31):
```typescript
export type MoveQuality = 'best' | 'good' | 'inaccuracy' | 'mistake' | 'blunder';
```
→ add `'gem'` per Open Question 3's recommendation (RESEARCH): keep `classifyMoveQuality` itself unchanged (single-position, no gem/parent awareness); Analysis.tsx overlays the gem override in a thin derived memo/wrapper that swaps `'best'` → `'gem'` on the qualifying SAN post-hoc.

**Bucket-fold switch to update** (lines 197-211, Pitfall 4 — MUST touch, silent `default: return 'pending'` swallows unmapped values):
```typescript
function bucketKeyForQuality(quality: MoveQuality | undefined): QualityBucketKey {
  switch (quality) {
    case 'blunder': return 'blunder';
    case 'mistake': return 'mistake';
    case 'inaccuracy': return 'inaccuracy';
    case 'best':
    case 'good': return 'good';
    default: return 'pending';
  }
}
```
Add `case 'gem': return 'good';` explicitly (per CONTEXT.md's discretion note "presumably into the green good display segment") — do not leave it to fall through to `default`.

---

### `frontend/src/components/board/boardMarkers.tsx` (MODIFIED)

**Analog:** itself — `SquareMarker` interface (lines 16-23) and `SquareMarkerBadge` (lines 84-122).

**Interface extension** (additive, per RESEARCH Pattern 4):
```typescript
export interface SquareMarker {
  square: string;
  severity: FlawSeverity;
  label?: string;
  labelColor?: string;
}
```
→ make `severity` optional and add `gem?: boolean` (mutually exclusive with severity in practice per Open Question 2 — structural impossibility, no runtime assertion needed).

**Geometry constants to reuse verbatim** (lines 40-45): `MARKER_RADIUS`, `MARKER_RADIUS_SMALL`, `MARKER_CORNER_OVERLAP`, `GLYPH_VIEWBOX_DIAMETER`, `MARKER_STROKE`, `SMALL_BOARD_SQ_PX`. The gem badge is a same-shape sibling — only the fill content (icon path vs. `<text>` glyph) changes; do not invent new geometry constants.

**Core render pattern to branch from** (lines 93-121):
```typescript
const glyph = SEVERITY_GLYPH[marker.severity];
...
<circle cx={cx} cy={cy} r={r} fill={glyph.color} stroke={MARKER_STROKE} strokeWidth={1} />
<text ... >{glyph.symbol}</text>
```
Gem variant: `marker.gem ? <GemBadgeContent cx={cx} cy={cy} r={r} /> : <text>...</text>` inside the same `<circle fill={MAIA_ACCENT} .../>` wrapper. Since `boardMarkers.tsx` hand-draws glyphs from scratch (license rationale documented in `SeverityGlyphIcon.tsx` lines 1-6) rather than importing component trees, hand-draw the lucide `Gem` SVG path here too (or nest `<Gem/>` inside the existing `<svg>` viewBox with a transform — planner's call, RESEARCH flags both as viable).

---

### `frontend/src/components/icons/GemIcon.tsx` (NEW)

**Analog:** `frontend/src/components/icons/SeverityGlyphIcon.tsx` (full file, 90 lines) — same props shape (`className`, `style`, `aria-hidden`), same `GlyphBadge`-style factory returning `<svg viewBox="0 0 24 24">`.

**Props interface pattern** (lines 21-25):
```typescript
export interface SeverityGlyphIconProps {
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}
```
`GemIcon` should export the same prop shape (rename or reuse) so it drops into the same move-list call sites (`VariationTree.tsx`) that currently take `BlunderIcon`/`MistakeIcon`.

**Difference from the analog:** `SeverityGlyphIcon` draws a `<text>` glyph inside the circle (lines 57-71); `GemIcon` needs lucide's `Gem` icon (white) inside a `MAIA_ACCENT` circle instead of text — either render `<Gem />` (from `lucide-react`, already imported elsewhere via `import { ChessKnight, Cpu, User } from 'lucide-react'` in `UnifiedMovePopover.tsx` line 25) nested in the SVG with `fill="#fff"`/appropriate sizing, or hand-copy its path. Color is baked in as `MAIA_ACCENT` (not caller-overridable), matching `SeverityGlyphIcon`'s rationale (lines 8-11: "self-color instead" of trusting caller `style={{color}}`).

---

### `frontend/src/components/analysis/MovesByRatingChart.tsx` (MODIFIED)

**Analog:** itself — `colorForQuality` (lines 179-194) and `qualityWord` (lines 207-210).

**Core switch pattern to extend:**
```typescript
function colorForQuality(quality: MoveQuality | undefined): string {
  switch (quality) {
    case 'best': return MOVE_QUALITY_BEST;
    case 'good': return MOVE_QUALITY_GOOD;
    case 'inaccuracy': return MOVE_QUALITY_INACCURACY;
    case 'mistake': return MOVE_QUALITY_MISTAKE;
    case 'blunder': return MOVE_QUALITY_BLUNDER;
    default: return MOVE_QUALITY_PENDING;
  }
}
```
Add `case 'gem': return MAIA_ACCENT;` (import `MAIA_ACCENT` from `@/lib/theme`, already used elsewhere in the file's sibling `MOVE_QUALITY_*` constants which themselves alias `SEV_*` from theme.ts — see lines 416, 427-429). `qualityWord` needs no change (it capitalizes any string, `'gem'` → `'Gem'` automatically via `quality[0]!.toUpperCase() + quality.slice(1)`).

**Pitfall to check (Pitfall 5):** search for every `case 'best':`/`=== 'best'` in this file (confirmed at line 181; also stroke-width/emphasis logic elsewhere in the file per RESEARCH) — audit each to decide whether `'gem'` needs the same treatment (since gem supersedes 'best' when both would apply to the same move).

---

### `frontend/src/components/analysis/MaiaMoveQualityBar.tsx` (MODIFIED)

**Analog:** consumes `bucketMovesByQuality`/`bucketKeyForQuality` from `moveQuality.ts` (no local quality-switch of its own expected — verify during implementation whether it has its own copy). Once `bucketKeyForQuality` maps `'gem'` → `'good'` (see moveQuality.ts section above), this component needs no separate change unless it independently colors/labels buckets — check for a local `QUALITY_BUCKET_ORDER`-driven render loop and confirm gem-quality moves render inside the existing green "good" segment without special-casing.

---

### `frontend/src/components/analysis/VariationTree.tsx` (MODIFIED)

**Analog:** itself — the `SeverityIcon` selection pattern repeated 3× (lines ~501-502, 586-587, 726-732):
```typescript
const isPersistedFlaw =
  flaw != null && (flaw.severity === 'blunder' || flaw.severity === 'mistake');
const SeverityIcon = flaw?.severity === 'blunder' ? BlunderIcon : MistakeIcon;
```
Import pattern (line 27): `import { BlunderIcon, MistakeIcon } from '@/components/icons/SeverityGlyphIcon';` → add `import { GemIcon } from '@/components/icons/GemIcon';` and extend each of the 3 render sites to check a gem flag/quality alongside `flaw.severity`, rendering `GemIcon` when the node is in `gemByNode` (new sticky cache from Analysis.tsx). Precedence: gem and severity are mutually exclusive per the classification math (Open Question 2), so no priority-ordering logic needed beyond checking gem first or via a unified discriminant.

---

### `frontend/src/components/analysis/UnifiedMovePopover.tsx` (MODIFIED)

**Analog:** itself — existing lucide-icon + `MAIA_ACCENT` usage pattern (lines 25, 27):
```typescript
import { ChessKnight, Cpu, User } from 'lucide-react';
import { FLAWCHESS_ENGINE_ARROW, STOCKFISH_ACCENT, MAIA_ACCENT } from '@/lib/theme';
```
Add `Gem` to the lucide import list and a short copy line ("Gem — players at your rating almost never find this.") gated on the move's gem status, following the file's existing per-quality label pattern (keep ≥ `text-sm` per project convention; this is NOT the sanctioned info-popover `text-xs` exception).

---

### `frontend/src/pages/Analysis.tsx` (MODIFIED)

**Analog:** itself — three existing patterns to mirror exactly, all in the 1180-1310 range already read in full:

**1. Per-FEN retention cache** (mirror `engineEvalByFen`, lines 1179-1200):
```typescript
const [engineEvalByFen, setEngineEvalByFen] = useState<
  Map<string, { cp: number | null; mate: number | null }>
>(() => new Map());
useEffect(() => {
  if (!engineEnabled) return;
  if (engine.evalCp == null && engine.evalMate == null) return;
  setEngineEvalByFen((prev) => {
    const existing = prev.get(position);
    if (existing && existing.cp === engine.evalCp && existing.mate === engine.evalMate) return prev;
    const next = new Map(prev);
    next.set(position, { cp: engine.evalCp, mate: engine.evalMate });
    if (next.size > LIVE_EVAL_CACHE_MAX) {
      const oldest = next.keys().next().value;
      if (oldest !== undefined) next.delete(oldest);
    }
    return next;
  });
}, [position, engine.evalCp, engine.evalMate, engineEnabled]);
```
Two new siblings needed: `maiaCurveByFen: Map<string, MoveCurvePoint[]>` (deps `[position, maia.perElo, maiaEnabled]`) and `gradeSummaryByFen: Map<string, {bestSan, bestEs, secondBestEs}>` (deps `[position, qualityBySan, gradingEnabled]` — deliberately ELO-free per Pitfall 6, derived from the already-existing `qualityBySan` memo at lines 1006-1032, no new grading pass — use the `summarizeForGem` helper sketched in RESEARCH's Code Examples section).

**2. `parentFen` derivation** (already exists, line 1202-1209, reuse verbatim — no new field needed, per Pitfall 2):
```typescript
const parentFen = useMemo<string | null>(() => {
  if (currentNodeId === null) return null;
  const node = nodes.get(currentNodeId);
  if (!node) return null;
  if (node.parentId === null) return rootFen;
  return nodes.get(node.parentId)?.fen ?? rootFen;
}, [currentNodeId, nodes, rootFen]);
```

**3. Sticky per-node cache** (mirror `liveFlawByNode`, lines 1251-1271):
```typescript
const [liveFlawByNode, setLiveFlawByNode] = useState<Map<NodeId, FlawSeverity>>(() => new Map());
useEffect(() => {
  if (!liveFlawActive || currentNodeId === null) return;
  const severity = liveFlaw.squareMarkers[0]?.severity;
  if (severity !== 'blunder' && severity !== 'mistake') return;
  setLiveFlawByNode((prev) => {
    if (prev.get(currentNodeId) === severity) return prev;
    const next = new Map(prev);
    next.set(currentNodeId, severity);
    if (next.size > LIVE_EVAL_CACHE_MAX) {
      const oldest = next.keys().next().value;
      if (oldest !== undefined) next.delete(oldest);
    }
    return next;
  });
}, [liveFlawActive, currentNodeId, liveFlaw]);
```
`gemByNode: Map<NodeId, true>` follows this exact shape: only insert when `classifyGem(...)` returns `true` (never write a negative), gated by the same kind of `active` condition D-05/D-06 require (any visited node, mainline or free-play — check whether `liveFlawActive`'s existing gate is too narrow, since gem must ALSO cover main-line/PV nodes per D-05, unlike live-flaw which explicitly excludes them).

**4. `squareMarkers` assembly** (line 1737-1739):
```typescript
squareMarkers={
  gameOverlay.squareMarkers.length > 0 ? gameOverlay.squareMarkers : liveFlaw.squareMarkers
}
```
Needs a third source unioned in: when `currentNodeId` is in `gemByNode`, append a `{ square: lastMove.to, gem: true }` marker (using the boardMarkers.tsx `SquareMarker.gem` extension) — precedence/union logic here is a planner decision (gem markers are mutually exclusive with severity markers per Open Question 2, so simple concatenation is safe).

**Error handling / defensive pattern:** all four caches use FIFO-cap via `LIVE_EVAL_CACHE_MAX` and a stable-ref early-return (`if (existing === new) return prev`) to skip unnecessary re-renders — copy this exactly for both new caches, do not invent a different eviction policy.

---

## Shared Patterns

### Theme colors — `frontend/src/lib/theme.ts`
**Source:** line 74 `export const MAIA_ACCENT = 'oklch(0.58 0.20 290)'; // violet`
**Apply to:** `GemIcon.tsx`, `boardMarkers.tsx` (gem circle fill), `MovesByRatingChart.tsx` (`colorForQuality`'s new `'gem'` case), `UnifiedMovePopover.tsx` (existing import already includes `MAIA_ACCENT`).
No new theme constant needed — MAIA_ACCENT is reused verbatim per CONTEXT.md's seed-lock (not a placeholder).

### Expected-score sigmoid — `frontend/src/lib/liveFlaw.ts`
**Source:** `evalToExpectedScore` (lines 88-103), `MISTAKE_DROP` from `@/generated/flawThresholds`
**Apply to:** `gemMove.ts`'s `classifyGem` and the Analysis.tsx `gradeSummaryByFen`-derivation helper (`summarizeForGem`). Never re-derive the sigmoid or hand-roll a new threshold constant — one canonical `LICHESS_K`-based sigmoid for the whole page.

### Rung lookup at selected ELO — `frontend/src/lib/moveQuality.ts`
**Source:** `nearestByElo` (lines 123-128), already exported and reused by `useMaiaEngine.ts` and `positionVerdict.ts`.
**Apply to:** the gem-candidate memo in Analysis.tsx for C1 (played-move Maia probability at the rating-matched rung). Do not reimplement.

### Single-source glyph/marker record pattern — `frontend/src/lib/severityGlyph.ts` + `SeverityGlyphIcon.tsx` + `boardMarkers.tsx`
**Source:** `SEVERITY_GLYPH: Record<FlawSeverity, {symbol, color, fontSize}>` (severityGlyph.ts, full file) consumed identically by both the React icon component and the SVG board marker so they never drift.
**Apply to:** the gem badge should follow the same "one record, two consumers" shape — either a parallel `GEM_GLYPH` constant (color=MAIA_ACCENT, no symbol/text since it's an icon not a character) or an icon-discriminant addition to the existing pattern. Do NOT fork a third, independent styling source for gem.

### Constant-with-docstring convention — `frontend/src/generated/flawThresholds.ts` / `moveQuality.ts`
**Source:** `moveQuality.ts` lines 55-59 (`CUMULATIVE_MASS_THRESHOLD`, `CANDIDATE_HARD_CAP` — each a one-line JSDoc citing its design-doc decision ID).
**Apply to:** `GEM_MAIA_MAX_PROB = 0.03` in `gemMove.ts`, cited to D-07.

## No Analog Found

None — every file in scope has a strong, directly-applicable analog already in the codebase (this phase is explicitly "wiring existing primitives," per RESEARCH's own conclusion).

## Metadata

**Analog search scope:** `frontend/src/lib/`, `frontend/src/hooks/`, `frontend/src/components/board/`, `frontend/src/components/icons/`, `frontend/src/components/analysis/`, `frontend/src/pages/Analysis.tsx`
**Files scanned:** 8 read in full/targeted sections (moveQuality.ts, useLiveMoveFlaw.ts, severityGlyph.ts, SeverityGlyphIcon.tsx, boardMarkers.tsx, liveFlaw.ts, MovesByRatingChart.tsx excerpt, Analysis.tsx excerpts) + 3 grepped for line references (VariationTree.tsx, UnifiedMovePopover.tsx, theme.ts)
**Pattern extraction date:** 2026-07-10
