# Phase 172: Background Gem Sweep on Analysis - Pattern Map

**Mapped:** 2026-07-14
**Files analyzed:** 13 (new/modified)
**Analogs found:** 13 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/lib/gemSweep.ts` (new) | utility (pure scheduler + prefilter) | transform/event-driven | `frontend/src/lib/gemMove.ts` | exact (same "pure, worker-free" module shape) |
| `frontend/src/lib/bookGlyph.ts` (new) | utility (glyph spec) | transform | `frontend/src/lib/gemGlyph.ts` | exact |
| `frontend/src/components/icons/BookIcon.tsx` (new) | component | request-response (render) | `frontend/src/components/icons/GemIcon.tsx` | exact |
| `frontend/src/lib/theme.ts` (modify — add `BOOK_MARKER_COLOR`) | config | — | existing `MAIA_ACCENT`/`MOVE_QUALITY_PENDING` tokens | exact |
| `frontend/src/hooks/useMaiaEloDefault.ts` (modify — export `deriveRawDefault`/`clampToLadderBounds`) | hook | transform | itself (export-only change) | exact |
| `frontend/src/hooks/useGemSweep.ts` (new, suggested name) | hook (dedicated worker orchestration) | event-driven/streaming | `frontend/src/hooks/useFlawChessEngine.ts` | exact (abort + dedicated-worker pattern) |
| `frontend/src/pages/Analysis.tsx` (modify — sweep wiring, rung pin, sweep-start effect, marker call sites) | component (page) | event-driven | itself, lines 1414-1539 (gem resolution), 2046-2064 (board markers), 594-600/2206-2226 (`evalChartReady`) | exact (editing in place) |
| `frontend/src/components/analysis/VariationTree.tsx` (modify — `resolveMarkerIcon` + `FlawMarkerEntry.book`) | component | request-response (render) | itself, lines 59-69, 140-179 | exact |
| `frontend/src/components/board/boardMarkers.tsx` (modify — `SquareMarker.book` + `SquareMarkerBadge` branch) | component | request-response (render) | itself, lines 24-33, 96-157 | exact |
| `frontend/src/lib/gemMove.ts` (modify — `GEM_MAIA_MAX_PROB` 0.10→0.20) | utility | transform | itself, line 25 | exact |
| `app/services/opening_lookup.py` (modify — add `find_opening_ply_count`) | service | CRUD (read/compute) | itself, `find_opening` lines 99-120 | exact |
| `app/schemas/library.py` (modify — add `opening_ply_count: int = 0`) | model (Pydantic schema) | — | itself, `GameFlawCard`, line 129 area | exact |
| `app/services/library_service.py` (modify — compute `opening_ply_count` in `_build_card`) | service | CRUD | itself, `_build_card` lines 373-621 | exact |
| `frontend/src/types/library.ts` (modify — add `opening_ply_count` + doc on `EvalPoint.best_move` UCI) | model (TS type) | — | itself, `GameFlawCard`-equivalent + `EvalPoint`, lines 86-107 | exact |

## Pattern Assignments

### `frontend/src/lib/bookGlyph.ts` (utility) + `frontend/src/components/icons/BookIcon.tsx` (component)

**Analog:** `frontend/src/lib/gemGlyph.ts` + `frontend/src/components/icons/GemIcon.tsx` (copy verbatim, swap tokens)

**gemGlyph.ts, full file (14-18):**
```typescript
import { MAIA_ACCENT } from '@/lib/theme';

export const GEM_GLYPH: { color: string } = {
  color: MAIA_ACCENT,
};
```
Copy to `bookGlyph.ts`, swap `MAIA_ACCENT` → the new `BOOK_MARKER_COLOR` export in `theme.ts`, rename `GEM_GLYPH` → `BOOK_GLYPH`. Keep the same "one record, two consumers" doc-comment rationale (both `BookIcon` and `boardMarkers.tsx`'s badge read from it, so the two can't drift).

**GemIcon.tsx, full file (22-56):**
```typescript
import type { CSSProperties } from 'react';
import { Gem } from 'lucide-react';

import { GEM_GLYPH } from '@/lib/gemGlyph';

export interface GemIconProps {
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}

export function GemIcon({
  className,
  style,
  'aria-hidden': ariaHidden = true,
}: GemIconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      className={className}
      style={style}
      aria-hidden={ariaHidden}
      role="img"
    >
      <title>Gem move</title>
      <circle cx="12" cy="12" r="11" fill={GEM_GLYPH.color} />
      <Gem x={5} y={5} width={14} height={14} stroke="#fff" />
    </svg>
  );
}
```
Copy to `BookIcon.tsx`: `Gem` → `BookOpen`, `GEM_GLYPH` → `BOOK_GLYPH`, `<title>Gem move</title>` → `<title>Opening theory</title>` (per UI-SPEC copywriting table), `GemIconProps`/`GemIcon` → `BookIconProps`/`BookIcon`. Same 24-unit viewBox, same `x/y/width/height={5,5,14,14}` inner-icon geometry, same `aria-hidden` default. No `data-testid` (UI-SPEC: non-interactive, mirrors `GemIcon`/`BlunderIcon`/`MistakeIcon` — none of which carry one).

**theme.ts addition** (near `MAIA_ACCENT`): add `export const BOOK_MARKER_COLOR = 'oklch(0.60 0.04 250)';` per UI-SPEC's exact token/value/rationale.

---

### `frontend/src/lib/gemSweep.ts` (new, pure scheduler module)

**Analog:** `frontend/src/lib/gemMove.ts` (doc-comment rationale, module shape, no React/Worker imports)

**gemMove.ts header pattern to mirror (1-16):**
```typescript
/**
 * gemMove — pure, worker-free "gem move" detection (Phase 163, SEED-092).
 * ...
 */
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { MISTAKE_DROP } from '@/generated/flawThresholds';

export const GEM_MAIA_MAX_PROB = 0.1; // → 0.20 per D7, this phase
```
`gemSweep.ts` should be written in this same idiom: plain exported pure functions, a doc comment citing the phase/decision IDs (D4/D5), and explicit "why worker-free" rationale (testability without mocking React/Workers) — copied almost verbatim from RESEARCH.md's own illustrative code:

```typescript
import { sanToUci } from '@/lib/sanToSquares';
import type { EvalPoint } from '@/types/library';

export interface SweepCandidate {
  plyIndex: number; // 0-based index into mainLine/moves/eval_series
  parentFen: string;
  playedSan: string;
}

export function selectSweepCandidates(
  moves: string[],
  evalSeries: EvalPoint[],
  openingPlyCount: number,
  fenAtPly: (i: number) => string, // parent FEN before moves[i]
): SweepCandidate[] {
  const survivors: SweepCandidate[] = [];
  for (let i = 0; i < moves.length; i++) {
    if (i < openingPlyCount) continue; // D6/D8: book plies never enter the cascade
    const point = evalSeries[i];
    const playedSan = moves[i];
    if (point?.best_move == null || playedSan === undefined) continue;
    const parentFen = fenAtPly(i);
    const playedUci = sanToUci(parentFen, playedSan);
    if (playedUci === null || playedUci !== point.best_move) continue; // D4: strict, fails safe
    survivors.push({ plyIndex: i, parentFen, playedSan });
  }
  return survivors;
}
```

**`sanToUci` — the exact helper to import (`frontend/src/lib/sanToSquares.ts:63-71`):**
```typescript
export function sanToUci(fen: string, san: string): string | null {
  try {
    const chess = new Chess(fen);
    const move = chess.move(san);
    return `${move.from}${move.to}${move.promotion ?? ''}`;
  } catch {
    return null;
  }
}
```
Reuse directly — do not hand-roll SAN→UCI (Pitfall 2 in RESEARCH.md: `EvalPoint.best_move` is UCI, `moves[i]` is SAN — direct string compare is a silent no-op).

**Scheduler decision function:** also expose a pure "what's the next candidate to dispatch given the current cursor" function in this same file — mirror `dequeueHighestPriority` from `frontend/src/lib/engine/workerPool.ts:127-152` for the array-scan-with-tie-break shape (even though the sweep should NOT literally use `workerPool.ts`, per RESEARCH's recommendation to keep dedicated single-worker instances):
```typescript
export function dequeueHighestPriority(
  pending: QueuedGradeRequest[],
): QueuedGradeRequest | undefined {
  let best: QueuedGradeRequest | undefined;
  let bestIdx = -1;
  pending.forEach((req, i) => {
    const better =
      best === undefined ||
      req.priority > best.priority ||
      (req.priority === best.priority && req.depth < best.depth);
    if (better) { best = req; bestIdx = i; }
  });
  if (bestIdx >= 0) pending.splice(bestIdx, 1);
  return best;
}
```

---

### `frontend/src/hooks/useGemSweep.ts` (new, dedicated-worker orchestration hook)

**Analog:** `frontend/src/hooks/useFlawChessEngine.ts` (established dedicated-worker + abort-on-navigation pattern)

**Abort pattern to copy (`useFlawChessEngine.ts:210-235`):**
```typescript
useEffect(() => {
  const pool = poolRef.current;
  const queue = queueRef.current;
  if (!debouncedFen || !enabled || !pool || !queue) return;

  // Pitfall 1: ... explicitly stop the pool too.
  // maiaQueue has no stopAll (an in-flight ONNX inference cannot be
  // interrupted) — a stale policy() resolution is unused and harmless.
  abortControllerRef.current?.abort();
  pool.stopAll();

  const controller = new AbortController();
  abortControllerRef.current = controller;
  // ... reset throttles, start fresh search
}, [/* deps */]);
```
`useGemSweep` must follow the SAME shape: on cursor change, `abort()` any in-flight LOW-priority Stockfish search (Stockfish CAN be stopped mid-search) but tolerate a stale in-flight Maia ONNX inference as "unused and harmless" — do not attempt to cancel it, per the exact precedent comment above.

**Never share the hook instance with the live path.** Do NOT drive the sweep through the SAME `useStockfishGradingEngine`/`useMaiaEngine` call used for `gemGrading`/`grading`/`maia` in `Analysis.tsx` (lines 906, 1476, and the single `maia` call). Instantiate separate `useStockfishGradingEngine`-shaped and Maia-worker instances exclusively for the sweep. This is the single most load-bearing pattern in the phase (D5) — see RESEARCH.md Pitfall 1.

**Idle scheduling — no existing precedent in-repo** (RESEARCH.md Pitfall 3 confirms no `requestIdleCallback` usage exists yet). Feature-detect:
```typescript
const scheduleIdle: (cb: () => void) => void =
  typeof window.requestIdleCallback === 'function'
    ? (cb) => window.requestIdleCallback(cb)
    : (cb) => setTimeout(cb, 1);
```

**Tab-hidden pause — mirror `useStockfishGradingEngine.ts:431-454` and `useMaiaEngine.ts:309-325`** (both already have `visibilitychange` handlers): read those two blocks directly when implementing and copy the same event-listener add/remove-in-cleanup shape.

**Reduced movetime cap:** `useStockfishGradingEngine.ts:52` defines `GRADING_MOVETIME_SAFETY_CAP_MS = 4000` for the live path — the sweep needs its OWN, smaller constant (do not reuse this one; cite explicitly as deliberately different, per RESEARCH.md).

---

### `frontend/src/hooks/useMaiaEloDefault.ts` (modify — export-only)

**Analog:** itself, lines 94-119 (currently module-private)

```typescript
function clampToLadderBounds(rating: number, ladder: readonly number[] = MAIA_ELO_LADDER): number {
  const min = ladder[0] ?? rating;
  const max = ladder[ladder.length - 1] ?? rating;
  return Math.min(max, Math.max(min, rating));
}

function deriveRawDefault(
  isGameMode: boolean,
  gameData: MaiaEloGameData | undefined,
  profile: MaiaEloProfile | undefined,
  sideToMove: MoverColor | undefined,
): number | null {
  if (isGameMode) {
    if (gameData == null) return null;
    const moverColor = sideToMove ?? gameData.user_color;
    if (moverColor === 'white') {
      return gameData.white_rating_lichess_blitz ?? gameData.white_rating;
    }
    return gameData.black_rating_lichess_blitz ?? gameData.black_rating;
  }
  return profile?.lichess_blitz_equivalent_rating ?? FREE_PLAY_DEFAULT_ELO;
}
```
Change `function clampToLadderBounds(` → `export function clampToLadderBounds(` and same for `deriveRawDefault` (or extract both to a shared pure module if the executor prefers — RESEARCH.md leaves the exact mechanism open, but export-in-place is the minimal diff). `Analysis.tsx`'s rung-pin call site (D1) then imports these directly instead of re-deriving the `*_lichess_blitz ?? raw` chain.

---

### `frontend/src/pages/Analysis.tsx` (modify — three separate edit sites)

**Analog:** itself — this is an in-place edit of existing, well-understood code, not a new-file analog search.

**Site 1 — rung pin (replaces `nearestByElo(parentCurve, selectedElo)` at lines 1445, 1451, 1495-1501):**
Current (line 1451, to be replaced for the RUNG lookup only — `selectedElo` still drives the live exploration overlay per D1):
```typescript
const maiaProbability = nearestByElo(parentCurve, selectedElo)?.moveProbabilities[playedSan] ?? null;
```
New pattern — reuse the already-computed `mover` variable (already present at line 1495 as `sideToMoveFromFen(parentFen)`, and used at 1509-1512 for `byOpponent`) to derive a PINNED rung via the newly-exported `deriveRawDefault`/`clampToLadderBounds`, instead of the reactive `selectedElo`:
```typescript
const mover = sideToMoveFromFen(parentFen); // already used at 1495 for byOpponent
const pinnedElo = clampToLadderBounds(
  deriveRawDefault(isGameMode, gameData, profile, mover) ?? FREE_PLAY_DEFAULT_ELO,
);
const maiaProbability = nearestByElo(parentCurve, pinnedElo)?.moveProbabilities[playedSan] ?? null;
```

**Site 2 — sweep-start effect (D3, the readiness transition), exact shape from RESEARCH.md, gated on `evalChartReady` not mount:**
```typescript
const sweptGameIdRef = useRef<number | null>(null);
useEffect(() => {
  if (!evalChartReady || gameId == null || sweptGameIdRef.current === gameId) return;
  sweptGameIdRef.current = gameId;
  // start sweep
}, [evalChartReady, gameId]);
```
`evalChartReady` is already defined at `Analysis.tsx:2214` as:
```typescript
isGameMode && gameId != null && gameData?.eval_series != null && gameData.flaw_markers != null && gameData.phase_transitions != null && gameData.moves != null
```
No new polling machinery — this transition is already delivered by `useLibraryGame(gameId, { live: true })` (line 597-600).

**Site 3 — board marker append (D8, `boardSquareMarkers` memo, lines 2046-2064).** The gem append today is gated on absence of an existing severity marker on the same square:
```typescript
if (... !base.some((m) => m.square === lastMove.to && m.severity != null))
```
D8's book append is a THIRD step, gated on absence of BOTH severity and gem:
```typescript
if (
  isBookPly && // current node's ply index < opening_ply_count
  lastMove != null &&
  !base.some((m) => m.square === lastMove.to && (m.severity != null || m.gem === true))
) {
  return [...withGem, { square: lastMove.to, book: true }];
}
```
Also builds `moveListMarkers`'s `book` field (consumed by `VariationTree.tsx`) as `plyIndex < gameData.opening_ply_count`.

**Cache sizing (Pitfall 4).** Do NOT write sweep results into the shared, FIFO-256-capped `gemByNode`/`maiaCurveByFen` maps (`LIVE_EVAL_CACHE_MAX = 256`, line 120) without decoupling their cap — give the sweep its own cache sized to `mainLine.length` (bounded, known upfront, no eviction needed), or size a shared map generously against it.

---

### `frontend/src/components/analysis/VariationTree.tsx` (modify)

**Analog:** itself, `resolveMarkerIcon` (59-69) and `FlawMarkerEntry` (140-179) — extend in place.

Current:
```typescript
function resolveMarkerIcon(flaw: FlawMarkerEntry | undefined): {
  show: boolean;
  Icon: typeof BlunderIcon;
  isGem: boolean;
} {
  if (flaw != null && (flaw.severity === 'blunder' || flaw.severity === 'mistake')) {
    return { show: true, Icon: flaw.severity === 'blunder' ? BlunderIcon : MistakeIcon, isGem: false };
  }
  if (flaw?.gem) return { show: true, Icon: GemIcon, isGem: true };
  return { show: false, Icon: MistakeIcon, isGem: false };
}
```
New (per UI-SPEC, `severity > gem > book`):
```typescript
function resolveMarkerIcon(flaw: FlawMarkerEntry | undefined): {
  show: boolean;
  Icon: typeof BlunderIcon;
  isGem: boolean;
  isBook: boolean;
} {
  if (flaw != null && (flaw.severity === 'blunder' || flaw.severity === 'mistake')) {
    return { show: true, Icon: flaw.severity === 'blunder' ? BlunderIcon : MistakeIcon, isGem: false, isBook: false };
  }
  if (flaw?.gem) return { show: true, Icon: GemIcon, isGem: true, isBook: false };
  if (flaw?.book) return { show: true, Icon: BookIcon, isGem: false, isBook: true };
  return { show: false, Icon: MistakeIcon, isGem: false, isBook: false };
}
```
Add `book?: boolean;` to `FlawMarkerEntry` (mirror the doc-comment style of the existing `gem?`/`gemMaiaProbability?` fields at 149-169). `MoveListMarker` (77-97) needs NO new branch — the `isGem` check already gates the popover-wrapped path; book falls through to the plain-icon render exactly like severity does today (`return <Icon className={className} aria-hidden />;`).

---

### `frontend/src/components/board/boardMarkers.tsx` (modify)

**Analog:** itself, `SquareMarker` (24-33) and `SquareMarkerBadge` (96-157).

Add `book?: boolean;` to `SquareMarker`, mirroring:
```typescript
export interface SquareMarker {
  square: string;
  severity?: FlawSeverity;
  gem?: boolean;
  book?: boolean; // new — mutually exclusive with severity/gem by construction
  label?: string;
  labelColor?: string;
}
```
Add a third branch to `SquareMarkerBadge`, structurally identical to the existing `if (marker.gem) { ... }` block (116-131), reusing `MARKER_STROKE`/`GEM_ICON_DIAMETER_RATIO`/`r`/`cx`/`cy` exactly as-is, swapping `Gem` → `BookOpen` and `GEM_GLYPH.color` → `BOOK_GLYPH.color`:
```typescript
if (marker.gem) {
  const iconSize = 2 * r * GEM_ICON_DIAMETER_RATIO;
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={GEM_GLYPH.color} stroke={MARKER_STROKE} strokeWidth={1} />
      <Gem x={cx - iconSize / 2} y={cy - iconSize / 2} width={iconSize} height={iconSize} stroke="#fff" />
    </g>
  );
}
// NEW — insert here, before the severity fallback:
if (marker.book) {
  const iconSize = 2 * r * GEM_ICON_DIAMETER_RATIO;
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={BOOK_GLYPH.color} stroke={MARKER_STROKE} strokeWidth={1} />
      <BookOpen x={cx - iconSize / 2} y={cy - iconSize / 2} width={iconSize} height={iconSize} stroke="#fff" />
    </g>
  );
}
```

---

### `frontend/src/lib/gemMove.ts` (modify — one-line constant + doc update)

**Analog:** itself, line 25.
```typescript
// before
export const GEM_MAIA_MAX_PROB = 0.1;
// after
export const GEM_MAIA_MAX_PROB = 0.2;
```
Companion test-literal update required (Pitfall 6) — see Test section below.

---

### `app/services/opening_lookup.py` (modify — additive function)

**Analog:** itself, `find_opening` (99-120).

```python
def find_opening(pgn: str | None) -> tuple[str | None, str | None]:
    moves = _normalize_pgn_to_san_sequence(pgn)
    if not moves:
        return None, None
    node = _TRIE
    last_result: tuple[str, str] | None = None
    for move in moves:
        if move not in node.children:
            break
        node = node.children[move]
        if node.result is not None:
            last_result = node.result
    if last_result is None:
        return None, None
    return last_result
```

New parallel function (does NOT call `_normalize_pgn_to_san_sequence` — the caller already has tokenized SAN `moves: list[str]`):
```python
def find_opening_ply_count(moves: list[str]) -> int:
    """1-based ply depth of the deepest known-opening match, or 0 if none."""
    node = _TRIE
    last_depth = 0
    for i, move in enumerate(moves):
        if move not in node.children:
            break
        node = node.children[move]
        if node.result is not None:
            last_depth = i + 1
    return last_depth
```
Existing callers of `find_opening` (`app/services/normalization.py:301,446,662`, `app/routers/position_bookmarks.py:115`) are untouched.

---

### `app/schemas/library.py` (modify — additive field on `GameFlawCard`)

**Analog:** itself, existing nullable additive fields on the same model (129 area):
```python
    moves: list[str] | None = None
    # Active eval-job state for the on-demand analyze pill; null when no active job
    # (unanalyzed-and-unqueued, or already analyzed). The partial unique index
    # uq_eval_jobs_game_active guarantees at most one active row per game.
    active_eval_status: Literal["pending", "leased"] | None = None
```
Add, following the same doc-comment convention (explain WHY, cite the phase):
```python
    # Phase 172 (SEED-106 D6): 1-based ply depth of the deepest opening-book
    # match, computed on-read from `moves` (no column, no migration/backfill).
    # 0 means no known opening prefix matched. Gates the gem sweep and marks
    # theory plies with the book badge on every surface gems already render.
    opening_ply_count: int = 0
```

---

### `app/services/library_service.py` (modify — `_build_card`)

**Analog:** itself, the rating-normalization block immediately preceding the `GameFlawCard(...)` constructor call (lines ~548-591 as read).

Insertion point: right before `return GameFlawCard(...)` (~line 591), following the same "compute a derived value, then pass it into the constructor" shape already used for `white_rating_lichess_blitz`/`black_rating_lichess_blitz` immediately above it:
```python
opening_ply_count = find_opening_ply_count(moves_data) if moves_data else 0
```
Add `opening_ply_count=opening_ply_count,` to the `GameFlawCard(...)` call, alongside the existing `moves=moves_data,` argument. Import `find_opening_ply_count` from `app.services.opening_lookup` at the top of the file (alongside any existing `opening_lookup` import, or add a fresh one if `find_opening` isn't imported here today).

---

### `frontend/src/types/library.ts` (modify — mirror the backend field + doc the UCI/SAN distinction)

**Analog:** itself, `EvalPoint` (98-107) and the `GameFlawCard`-equivalent interface (86-96).

```typescript
export interface EvalPoint {
  ply: number;
  es: number | null;
  eval_cp: number | null;
  eval_mate: number | null;
  clock_seconds: number | null;
  move_seconds: number | null;
  best_move: string | null;     // engine best move FROM this position (UCI); null when no PV captured
}
```
Add near `moves: string[] | null;` (line 92):
```typescript
  // Phase 172 (SEED-106 D6): 1-based ply depth of the deepest opening-book
  // match, computed on-read by the backend. 0 = no known opening prefix.
  opening_ply_count: number;
```

## Shared Patterns

### Dedicated-worker isolation (D5 — the phase's central invariant)
**Source:** `frontend/src/hooks/useFlawChessEngine.ts:210-235` (abort pattern), `frontend/src/hooks/useStockfishGradingEngine.ts` (single-FEN state machine — do NOT feed it a second concurrent FEN), `frontend/src/hooks/useMaiaEngine.ts:168-187,269-276` (single-in-flight-request drop behavior — do NOT share this instance)
**Apply to:** `useGemSweep.ts` (new)
```typescript
abortControllerRef.current?.abort();
pool.stopAll(); // Stockfish CAN be stopped mid-search
const controller = new AbortController();
abortControllerRef.current = controller;
// maiaQueue has no stopAll (an in-flight ONNX inference cannot be
// interrupted) — a stale result is unused and harmless.
```

### "One record, two consumers" glyph pattern
**Source:** `frontend/src/lib/gemGlyph.ts` + its two consumers (`GemIcon.tsx`, `boardMarkers.tsx`'s `marker.gem` branch)
**Apply to:** `bookGlyph.ts` + `BookIcon.tsx` + `boardMarkers.tsx`'s new `marker.book` branch — single color source of truth, never duplicate the hex/oklch literal.

### Severity > gem > book precedence
**Source:** `VariationTree.tsx:59-69` (real branching — `FlawMarkerEntry` can carry both fields), `Analysis.tsx:2046-2064`'s `boardSquareMarkers` memo (construction-time exclusivity via guard conditions, not runtime branching)
**Apply to:** Both `resolveMarkerIcon` and the `boardSquareMarkers` append logic — book is always the LAST, lowest-priority clause/guard in both places.

### SAN vs UCI awareness
**Source:** `frontend/src/lib/sanToSquares.ts:63-71` (`sanToUci`), `frontend/src/hooks/useStockfishGradingEngine.ts` (existing caller building its candidate set the same way)
**Apply to:** `gemSweep.ts`'s free prefilter — `EvalPoint.best_move` is UCI, `moves[i]`/`playedSan` is SAN; always convert before comparing.

### Rating-at-game-time fallback chain
**Source:** `useMaiaEloDefault.ts:104-119` (`deriveRawDefault`), `:94-98` (`clampToLadderBounds`)
**Apply to:** `Analysis.tsx`'s rung-pin site (D1) — export and reuse, never reimplement the `*_lichess_blitz ?? raw` chain a second time.

## No Analog Found

None — every file in this phase has a direct, cited, in-repo analog (RESEARCH.md's own census already did this work exhaustively; this phase's design goal is explicitly "glue code between existing, well-tested primitives," so no net-new architectural pattern was needed).

## Test File Analogs

| New/Modified Test | Analog | Notes |
|---|---|---|
| `frontend/src/lib/__tests__/gemSweep.test.ts` (new) | `frontend/src/lib/__tests__/gemMove.test.ts` (pure, no engine/worker involved — `describe`/`it` per predicate, analytic fixture helpers) | Must include a genuine CONTENTION test per project mutation-test-gap-closure discipline (memory: `feedback_mutation_test_gap_closures`) — a "sweep resolves gems" smoke test does NOT prove D5; must start a live gem-grading request, then a sweep candidate, and assert the live request resolves without measurable sweep-induced delay. |
| `frontend/src/lib/__tests__/gemMove.test.ts` (modify line ~58-59) | itself | `it('D-07: GEM_MAIA_MAX_PROB is exactly 0.1', ...)` → update literal to `0.2` and description, in the SAME commit as the `gemMove.ts` constant change (Pitfall 6 — this WILL fail immediately otherwise, by design). |
| `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` (extend) | itself (existing file) | New case: `selectedElo`/slider changes do not affect a pinned-per-node rung once `deriveRawDefault`/`clampToLadderBounds` are exported and called with a fixed `sideToMove`. |
| `frontend/src/pages/__tests__/Analysis.test.tsx` (extend) | itself — already mocks `useStockfishGradingEngine`/`useMaiaEngine`/`useStockfishEngine` module-wide | New cases: (a) unanalyzed card never triggers sweep-start effect, (b) `evalChartReady` FALSE→TRUE transition (mirrors the rj5 "flips from unanalyzed to analyzed" test already in this file) fires the sweep exactly once per `gameId`. |
| `frontend/src/components/analysis/__tests__/VariationTree.test.tsx` (extend) | itself | New `book`-only case and `severity + book` case (severity wins). |
| `frontend/src/components/board/__tests__/boardMarkers.test.tsx` (extend) | itself | New `book` marker render case. |
| `tests/test_opening_lookup.py::TestFindOpeningPlyCount` (new class) | `TestFindOpening` (72+, same file — Italian/Sicilian/Queen's Gambit/King's Pawn/empty/None fixtures) | Mirror the SAME canonical opening fixtures but call `find_opening_ply_count(moves)` (a `list[str]`, not a PGN string) and assert an integer depth; add a mid-line-divergence case and an all-book case. |
| `tests/services/test_library_service.py` (extend, if present) | existing `_build_card`/`get_library_game` tests | New case asserting `opening_ply_count` appears on the payload for a known-opening game and is 0 for an unmatched one. |

## Metadata

**Analog search scope:** `frontend/src/lib/`, `frontend/src/components/icons/`, `frontend/src/components/analysis/`, `frontend/src/components/board/`, `frontend/src/hooks/`, `frontend/src/pages/Analysis.tsx`, `frontend/src/types/library.ts`, `app/services/`, `app/schemas/library.py`, and the corresponding test directories — scope taken directly from RESEARCH.md's own file census (already exhaustive; no additional Glob/Grep search was needed beyond confirming exact line numbers and full excerpts).
**Files scanned:** 13 direct reads (all analogs cited above) + RESEARCH.md's own prior census of `Analysis.tsx`, `useStockfishGradingEngine.ts`, `useMaiaEngine.ts`, `workerPool.ts`.
**Pattern extraction date:** 2026-07-14
