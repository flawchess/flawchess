# Phase 158: FlawChess Engine displayed-eval provenance reconciliation - Research

**Researched:** 2026-07-07
**Domain:** Frontend React/TypeScript — client-side Stockfish WASM eval reconciliation across three `/analysis` display surfaces
**Confidence:** HIGH

## Summary

This phase is a pure display/verdict overlay on top of three already-shipped, independent Stockfish
search pipelines. No new packages, no new workers, no backend changes. The fix is entirely in how
`Analysis.tsx` (and the small pure lib it should grow) resolves *which number to show* for a given
move, not in how any engine searches. All three consumers already read their evals through a small
number of well-isolated call sites — one in `FlawChessEngineLines.tsx` (the FC card's blue objective
number), one in `flawChessVerdict.ts`/`FlawChessAgreementVerdict.tsx` (the verdict + its hover
popovers), and one funnel point in `Analysis.tsx`'s `qualityBySan` memo (which every Maia surface —
chart tooltip, quality bar, `positionVerdict.ts` prose — reads through). That funnel property is the
single biggest leverage point in this phase: fixing `qualityBySan`'s inputs fixes four downstream
consumers for free.

The one genuine wiring complication is a **key-space mismatch**: `useStockfishEngine`'s `pvLines` and
`RankedLine.rootMove`/`modalPath` are UCI-keyed (per the Phase 153 D-08 "engine core speaks UCI
everywhere" convention), but `useStockfishGradingEngine`'s public `gradeMap` is SAN-keyed (Phase
151.1 converts `pv[0]` UCI to SAN via `sanFromUci` before caching, to match Maia's SAN-labeled
candidate set). CONTEXT.md's locked design mandates a UCI-keyed lookup, so the new lookup module must
normalize the grading map's SAN keys to UCI (via `sanToUci`, already exported from
`@/lib/sanToSquares.ts`) when building the merged map, and expose a SAN-convenience wrapper for the
Maia call sites that still want to query by SAN.

The second real design choice is **where reconciliation happens**. All the downstream consumers
(`FlawChessEngineLines`, `flawChessVerdict.ts`, `FlawChessAgreementVerdict.tsx`, `classifyMoveQuality`)
already accept exactly the shapes they need (`RankedLine[]`, `RankedLine | null`, `PvLine | null`,
`Map<string, MoveGrade>`) and are unit-tested against hand-built fixtures of those shapes. The
cheapest, lowest-blast-radius design is to do reconciliation **only in `Analysis.tsx`**, producing
already-reconciled `RankedLine`-shaped objects (real `rootMove`/`practicalScore`/`modalPath`/`visits`
untouched, only `objectiveEvalCp` swapped for the lookup result) and an already-reconciled
`Map<string, MoveGrade>` for `qualityBySan`'s input — leaving every downstream component/module's
props and existing unit tests completely unchanged. This keeps `flawChessVerdict.test.ts`,
`FlawChessAgreementVerdict.test.tsx`, and `moveQuality.test.ts` green with zero edits.

**Primary recommendation:** Add one new pure lib module (`frontend/src/lib/engineEvalLookup.ts`) that
builds a UCI-keyed `Map<string, MoveGrade>` from `(pvLines, gradeMap, baseFen)` with free-run-first
precedence, plus a SAN convenience accessor; wire it into `Analysis.tsx` as a single memo consumed by
all four display sites; raise `useStockfishGradingEngine`'s candidate set to the FC∪Maia union and its
gating to `maiaEnabled || flawChessEnabled`; measure and raise its depth/movetime budget via the
headless Node WASM harness before locking new constants.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Free-run authoritative eval search | Browser (Web Worker, `useStockfishEngine`) | — | Existing engine, untouched by this phase |
| Shared fallback grading search | Browser (Web Worker, `useStockfishGradingEngine`) | — | Existing hook, promoted in scope (candidate set + depth + gating), not replaced |
| UCI-keyed eval lookup / precedence resolution | Browser (Client, pure lib) | — | New pure function, no I/O — belongs in `frontend/src/lib/`, not a hook (testable without jsdom/workers) |
| Reconciled eval wiring per surface (FC card, SF card, Maia card, verdict) | Browser (Client, `Analysis.tsx` orchestration) | — | `Analysis.tsx` is the only place all three engine hooks' outputs are simultaneously in scope |
| MCTS search core / practical ranking | Browser (Client, `mctsSearch`/`workerPool`) | — | Locked Phase 153/154 core — explicitly untouched (scope fence) |

## User Constraints

<user_constraints>
### Locked Decisions (verbatim from 158-CONTEXT.md)

**Single source of truth + lookup precedence (LOCKED)**
- The free SF MultiPV run (`useStockfishEngine`) is the authoritative eval source. Every displayed
  move on every surface resolves its eval by UCI lookup: **free run first, shared grading run
  second**.
- The MCTS pool's shallow grades (`objectiveEvalCp` from `workerPool.ts`) stop being a display source
  anywhere. They remain internal to the search.

**ONE shared fallback run, not per-card (LOCKED)**
- `useStockfishGradingEngine` is promoted to the single shared fallback. Per-card fallbacks are
  rejected: most displayed FC moves are also in the Maia candidate set, so per-card grading would
  leave the FC and Maia cards disagreeing with each other.
- Its candidate set becomes `shownSans ∪ displayed FC moves`.
- Its budget is raised to analysis-grade depth: the depth-14 / 2500 ms cap is the proven skew source
  (the seed's O-O +1.4 ≈ +1.3 evidence shows `searchmoves` restriction itself does NOT skew evals;
  only the depth/hash cap did). The exact budget is chosen from a measured latency/depth trade on
  real positions (see Open Measurement below).

**Gating (LOCKED)**
- The shared grading run must run when *either* consumer needs display evals:
  `maiaEnabled || flawChessEnabled` (today it is gated on `maiaEnabled` only). The candidate union
  reflects which consumers are active.

**Quality buckets classify from reconciled evals (LOCKED)**
- `classifyMoveQuality` (Maia move-quality bar) must classify from the same reconciled post-lookup
  evals it displays, so a move's number and severity color cannot disagree at bucket boundaries.

**Verdict consumes the lookup (LOCKED)**
- The agreement verdict's FC-pick and SF-best evals both come from the lookup, making "FC pick
  grades higher than the objective best" impossible by construction.

**Scope fence (LOCKED)**
- Do NOT touch the MCTS search internals, the backup rule, the practical-score ranking, or Phase
  153's locked core.
- Explicitly out of scope (flagged, not folded in): whether shallow internal pool grades ever
  mis-*rank* the practical pick — a separate search-internal fidelity question.
- Configurable FC/SF line counts (`MAX_LINES`) are NOT a deliverable of this phase, but the
  reconciliation must be per-move (count-agnostic) so configurable counts fall out later for free.

**Open Measurement (Claude's Discretion on method, result feeds constants)**
- The free run's MultiPV width trades against eval-bar depth (fixed time budget); the grading run's
  MultiPV = candidate-union size trades against its depth. Measure latency/depth on real positions
  before fixing the constants. Named constants, no bare thresholds (project rule).

### Claude's Discretion
- Where the lookup lives (a hook, a lib module, or Analysis.tsx-level memo) — pick the seam that
  keeps functions small and avoids threading context objects.
- How progressive refinement is handled while searches are still streaming (evals may update live;
  no layout jump per Phase 157 precedent).
- Test strategy, subject to project norms (vitest; pure lib functions preferred for the
  lookup/precedence logic).

### Deferred Ideas (OUT OF SCOPE)
- Search-internal grade fidelity (shallow pool grades mis-ranking the practical pick) — separate
  question, explicitly out of scope per the seed.
- Configurable FC/SF line counts (`MAX_LINES`) — falls out for free later; not this phase.
- SEED-085 root-findability (which move the engine selects) — orthogonal.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEED-087 | Displayed-eval provenance reconciliation: every SF eval shown on `/analysis` (SF card, FC card, Maia chart/quality bar, agreement verdict) resolves through one UCI-keyed lookup (free run first, shared grading run second), ending the three-independent-searches mess | Root-cause data flow mapped for all 3 provenance chains (see Data Flow section); UCI/SAN key mismatch identified as the core wiring hazard; lookup module design + `Analysis.tsx` wiring plan below directly implements the locked design from 158-CONTEXT.md |
</phase_requirements>

## Standard Stack

No new packages. This phase reuses exclusively existing, already-shipped project infrastructure:

| Module | Role in this phase | Change needed |
|--------|---------------------|----------------|
| `frontend/src/hooks/useStockfishEngine.ts` | Source of truth (free run) | None — read-only source for the lookup |
| `frontend/src/hooks/useStockfishGradingEngine.ts` | Shared fallback | Candidate-set union, depth/movetime constants, gating condition |
| `frontend/src/lib/engine/workerPool.ts` | MCTS internal grading | None — its grades simply stop being *read* for display; internals untouched |
| `frontend/src/lib/sanToSquares.ts` | `sanToUci`/`uciToSquares` conversion helpers | None — reused as-is by the new lookup module |
| `frontend/src/lib/moveQuality.ts` | `classifyMoveQuality`, `MoveGrade` type | None — signature already accepts any `Map<string, MoveGrade>`; caller (`Analysis.tsx`) just feeds it a reconciled map |
| `frontend/src/lib/flawChessVerdict.ts` | Verdict tier classifier | None — signature already accepts `RankedLine | null`; caller passes an already-reconciled `RankedLine` |
| `frontend/src/lib/liveFlaw.ts` | `evalToExpectedScore`, `sideToMoveFromFen` | None — reused as-is |
| vitest ^4.1.7 | Test runner | None — new pure-lib tests follow existing conventions |

**Package Legitimacy Audit:** Not applicable — this phase installs no new npm packages.

## Data Flow: The Three Provenance Chains Today

Traced by file:line read (2026-07-07), confirming the CONTEXT.md/seed's breadcrumbs:

### Chain 1 — SF card + eval bar (authoritative, becomes source of truth)
```
useStockfishEngine (go movetime 1500, MultiPV=2, default hash)
  → engine.pvLines: PvLine[]                          [Analysis.tsx:449-452]
      ├─ SF card rows                                  (EngineLines.tsx, unchanged)
      ├─ right eval bar (rightEvalBarEvalCp/Mate)       [Analysis.tsx:1250-1252]
      ├─ engineArrows (blue SF arrows)                  [Analysis.tsx:1114-1127]
      ├─ engineTopLines (Maia chart tooltip header,
      │   only when engineEnabled)                      [Analysis.tsx:683-701]
      ├─ bestSan (Maia chart's "best" reference)         [Analysis.tsx:669-676]
      └─ FlawChessAgreementVerdict's stockfishLine prop
          (engine.pvLines[0], D-01 — never engineTopLines)[Analysis.tsx:1524]
```
`PvLine.moves[0]` is a UCI string — this chain is UCI-keyed throughout.

### Chain 2 — FC card blue numbers (currently the MCTS pool; must leave display path)
```
useFlawChessEngine → mctsSearch → workerPool.grade()
  (go depth 14 searchmoves <cands> movetime 2500, 8 MB hash, N pool workers)
  → RankedLine.objectiveEvalCp (frozen Phase 153 type field, treeCommon.ts:59)
      ├─ FlawChessEngineLines.tsx:124 (objectiveText = formatScore(line.objectiveEvalCp, null))
      │   — the FC card's blue "objective" number, only for the visible
      │   MAX_LINES=2 rows (FlawChessEngineLines.tsx:45,252)
      ├─ flawChessVerdict.ts:94 (flawChessMove.evalCp = flawChessLine.objectiveEvalCp)
      │   — feeds computeFlawChessVerdict's tier math AND the verdict's rendered FC eval text
      ├─ FlawChessAgreementVerdict.tsx:97-101 (FlawChessPickPopoverBody — the D-10 hover
      │   popover's "FlawChess: … (practical)" / "Stockfish: … (objective)" two-line body)
      ├─ FlawChessAgreementVerdict.tsx:110-129 (StockfishPickPopoverBody's `matchedLine` —
      │   when the SF pick was ALSO ranked by FlawChess, shows that ranked line's own
      │   objectiveEvalCp as its "FlawChess: … (practical)" line — a SECOND, easy-to-miss
      │   read site of the same field, via flawChessRankedLines.find(...) at
      │   FlawChessAgreementVerdict.tsx:206-209)
      └─ Analysis.tsx:697 (engineTopLines fallback branch, ONLY reached when
          engineEnabled is FALSE and flawChessEnabled is true — feeds the Maia chart
          tooltip header in that one config)
```
`RankedLine.rootMove` and `modalPath` are UCI (D-08) — this chain is also UCI-native at its root,
even though `FlawChessEngineLines.tsx` converts `modalPath` to SAN for chip display via
`replayPvLine` (display-only conversion, not used for eval keying).

**Every one of these 5 read sites needs to receive a reconciled `objectiveEvalCp` instead of the raw
pool grade.** Because they all consume `RankedLine`-shaped values (either the object directly or via
`flawChessLine`/`flawChessRankedLines`/`matchedFlawChessLineForSf`), the cheapest fix is to build
reconciled `RankedLine[]` once (only for the visibly-displayed rows, since only those need
resolving) and pass that array everywhere `flawChessEngine.rankedLines` is passed today.

### Chain 3 — Maia card evals (currently the grading hook; becomes shared fallback)
```
useStockfishGradingEngine (go depth 14 searchmoves <shownSans> movetime 2500, default hash,
  own independent Worker)
  → grading.gradeMap: Map<SAN, MoveGrade>              [Analysis.tsx:718-722]
      → qualityBySan: Map<SAN, MoveQualityEval>          [Analysis.tsx:726-740]
          (built via classifyMoveQuality(grading.gradeMap, mover, bestSan) — SINGLE FUNNEL POINT)
          ├─ MaiaHumanPanel → MovesByRatingChart (chart tooltip evals + line coloring)
          │     [MovesByRatingChart.tsx:272-273, :401]
          ├─ MaiaHumanPanel → MaiaMoveQualityBar (bucket classification + hover popovers)
          │     [MaiaMoveQualityBar.tsx:160,252,262-263]
          └─ positionVerdict.ts's computePositionVerdict (Maia prose verdict, reads
                qualityBySan via MaiaMoveQualityBar:262-263) [positionVerdict.ts:110,128-129]
```
`gradeMap` is **SAN-keyed** (`useStockfishGradingEngine.ts:322-347`, via `sanFromUci` converting
`parsed.pv[0]` UCI to SAN before caching) — this is the one chain whose native key space diverges
from the UCI convention the other two chains and the locked CONTEXT.md design use.

**Because `qualityBySan` is the single funnel every Maia surface reads through, fixing its input (one
`Analysis.tsx` memo) fixes all four downstream consumers without touching `MovesByRatingChart.tsx`,
`MaiaMoveQualityBar.tsx`, or `positionVerdict.ts` at all.**

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SAN↔UCI conversion for a given FEN | A second `sanToUci`/`uciToSquares` implementation inside the new lookup module | `@/lib/sanToSquares.ts`'s existing `sanToUci`/`uciToSquares` (already imported by `useStockfishGradingEngine.ts`) | Already tested, already the project's canonical chess.js-wrapping conversion; a second implementation risks a subtle promotion-suffix or castling-notation divergence |
| White-POV eval sign normalization | Re-deriving the mover-POV → white-POV negation in the lookup module | Consume `pvLines`/`gradeMap` AFTER they're already normalized (both hooks already commit white-POV-normalized `evalCp`/`evalMate` — `useStockfishEngine.ts:257-259`, `useStockfishGradingEngine.ts:326-327`) | Both source hooks already do this exact normalization; re-deriving it in the lookup would be redundant and a second place to get the sign wrong |
| Expected-score / sigmoid math for tier classification | A parallel scoring function inside the lookup module | `evalToExpectedScore` (`@/lib/liveFlaw.ts`), already used by both `flawChessVerdict.ts` and `moveQuality.ts` | The lookup module's job is ONLY to resolve which raw `{evalCp, evalMate}` to show for a UCI — it must not duplicate the tier/severity math that already lives downstream |

**Key insight:** every consumer of the reconciled eval already has a stable, tested interface
(`RankedLine[]`, `Map<string, MoveGrade>`, `PvLine | null`). The lookup module's entire job is
producing values matching those existing shapes — it does not need to reshape or extend any
consumer's contract.

## Architecture Patterns

### System Architecture Diagram

```
                    Analysis.tsx (orchestration layer)
                    ───────────────────────────────────
 useStockfishEngine ──────► engine.pvLines (UCI-keyed) ──┐
   (free run, N=?)                                       │
                                                           ▼
                                              ┌─ buildEvalLookup(pvLines, gradeMap, position) ─┐
                                              │   1. seed map from pvLines (UCI, free-run wins)  │
 useStockfishGradingEngine ─► grading.gradeMap│   2. for each SAN key in gradeMap NOT already    │
   (shared fallback, SAN-   (SAN-keyed)       │      covered by a free-run UCI, convert SAN→UCI  │
   keyed, candidates =                        │      via sanToUci(position, san) and insert       │
   shownSans ∪ FC moves)                      │   → Map<UCI, MoveGrade>  (evalLookup)             │
                                              └───────────────────────────────────────────────────┘
                                                           │
                    ┌──────────────────────────────────────┼───────────────────────────────┐
                    ▼                                      ▼                                ▼
     reconciledRankedLines =                  qualityBySan = classifyMoveQuality(     verdict inputs =
     flawChessEngine.rankedLines               reconciledGradeMap, mover, bestSan)     {flawChessLine: reconciled[0],
       .slice(0, MAX_LINES_DISPLAYED)          where reconciledGradeMap is built        stockfishLine: engine.pvLines[0]}
       .map(line => ({...line,                 by looking up each shownSan's UCI
         objectiveEvalCp:                      through evalLookup, falling back to
         lookupByUci(evalLookup,                grading.gradeMap's own SAN entry
         line.rootMove) ?? null}))              (never the pool)
                    │                                      │                                │
                    ▼                                      ▼                                ▼
        FlawChessEngineLines               MaiaHumanPanel → MovesByRatingChart      FlawChessAgreementVerdict
        (FC card blue numbers)             + MaiaMoveQualityBar + positionVerdict   (verdict sentence + D-10 popovers)
```

A move shown on 2+ surfaces now traces back to the exact same `evalLookup` entry, so it renders the
identical number by construction (Success Criterion 1).

### Recommended Project Structure
```
frontend/src/lib/
├── engineEvalLookup.ts        # NEW — pure module: buildEvalLookup, getByUci, getBySan
├── engineEvalLookup.test.ts   # NEW — vitest, no jsdom/workers needed (pure functions)
├── moveQuality.ts             # unchanged signature; caller supplies reconciled map
└── flawChessVerdict.ts        # unchanged signature; caller supplies reconciled RankedLine
frontend/src/hooks/
└── useStockfishGradingEngine.ts  # candidate-set/depth/gating constants updated
frontend/src/pages/
└── Analysis.tsx                  # new evalLookup memo + reconciled derived values
```

### Pattern 1: UCI-canonical lookup with a SAN convenience accessor

**What:** The lookup's internal map is keyed by UCI (matches the locked "UCI lookup" design and the
`RankedLine`/`PvLine` convention). A thin `getBySan(lookup, fen, san)` wrapper converts SAN→UCI via
`sanToUci` once per call, so the Maia call sites (which only have SANs on hand, e.g. `shownSans`)
don't need to duplicate that conversion inline.

**When to use:** Any time a Maia-side consumer (chart, quality bar, `qualityBySan` construction) needs
a reconciled eval and only has a SAN.

**Example:**
```typescript
// frontend/src/lib/engineEvalLookup.ts (illustrative shape, not literal committed code)
import { sanToUci } from '@/lib/sanToSquares';
import type { PvLine } from '@/hooks/uciParser';
import type { MoveGrade } from '@/lib/moveQuality';

/** UCI-keyed merged eval map: free run entries first, grading-run entries fill any gap. */
export function buildEvalLookup(
  pvLines: PvLine[],
  gradeMapBySan: Map<string, MoveGrade>,
  baseFen: string,
): Map<string, MoveGrade> {
  const lookup = new Map<string, MoveGrade>();
  for (const line of pvLines) {
    const uci = line.moves[0];
    if (uci !== undefined && !lookup.has(uci)) {
      lookup.set(uci, { evalCp: line.evalCp, evalMate: line.evalMate, depth: line.depth });
    }
  }
  for (const [san, grade] of gradeMapBySan) {
    const uci = sanToUci(baseFen, san);
    if (uci !== null && !lookup.has(uci)) lookup.set(uci, grade);
  }
  return lookup;
}

export function getBySan(
  lookup: Map<string, MoveGrade>,
  baseFen: string,
  san: string,
): MoveGrade | null {
  const uci = sanToUci(baseFen, san);
  return uci === null ? null : (lookup.get(uci) ?? null);
}
```

### Pattern 2: Reconciled `RankedLine[]` built at the display boundary, not inside the search core

**What:** `Analysis.tsx` maps `flawChessEngine.rankedLines.slice(0, N)` to a new array of
`RankedLine`-shaped objects whose `objectiveEvalCp` is the lookup result (or `null` if unresolved
yet), leaving `rootMove`/`practicalScore`/`modalPath`/`visits` untouched. This is passed to
`FlawChessEngineLines`, `flawChessVerdict.ts`'s `flawChessLine`, and `FlawChessAgreementVerdict`'s
`flawChessRankedLines` — every prop that used to receive the raw `flawChessEngine.rankedLines`.

**When to use:** Everywhere `flawChessEngine.rankedLines` is currently threaded into a display or
verdict consumer.

**Why this shape:** `RankedLine` is a **frozen Phase 153 type** (`types.ts:1-14`, "locked for the rest
of the v2.0 FlawChess Engine milestone"). Do not add fields to it or change its shape. Building a
parallel array of objects satisfying the same interface, with only `objectiveEvalCp` swapped, respects
the freeze while achieving reconciliation — no downstream component needs a new prop or a changed
type import.

### Pattern 3: Progressive-refinement precedence without flicker (Research Focus #6)

**What:** While both the free run and the grading run are still streaming `info` lines, a lookup entry
can transition from "no entry" → "grading-run value" → "free-run value overwrites it." The locked
precedence is free-run-first, so once the free run reports a UCI, its value always wins even if the
grading run reported first and the two later disagree slightly (both are legitimate live-refining
searches converging, not a bug).

**Design guidance:** Because `buildEvalLookup` (Pattern 1) is a plain `useMemo` recomputed on every
`(engine.pvLines, grading.gradeMap, position)` change, this "replace-on-arrival" behavior is a natural
consequence of the precedence order in the merge loop — no extra state machine is needed. The existing
project convention for "value not resolved yet" is `formatScore(null, null) → '…'`
(`EngineLines.tsx:179-193`, already used everywhere), so an unresolved lookup entry should map to
`{evalCp: null, evalMate: null}` rather than falling back to the pool's shallow grade — this is
required by the locked design ("MCTS pool grades stop being a display source anywhere") and is also
the path of least surprise: a `…` placeholder is an established, already-styled UI state on this page,
not a new one this phase must design.

**Numbers won't visibly "flicker between two different sources" in the confusing sense** — because
precedence never regresses (once free-run wins for a UCI, it can't fall back to grading-run), the
only visible transition is `… → grading-value → free-run-value`, i.e. monotonic settling, matching
the existing "eval bounces briefly then settles" convention already documented and accepted for the
free run itself (`useStockfishEngine.ts:249-252`, Pitfall 5 relaxed-bound-filtering note).

### Anti-Patterns to Avoid

- **Reconciling inside `useStockfishGradingEngine.ts` or `useStockfishEngine.ts` themselves:** Neither
  hook has visibility into the other's state (by design — SC3 isolation, `useStockfishGradingEngine.ts`
  docstring: "It never imports, mutates, or reads `useStockfishEngine`'s state"). Reconciliation must
  live one layer up, in `Analysis.tsx` (or a hook `Analysis.tsx` calls), where both hooks' return
  values are simultaneously in scope.
- **Mutating `RankedLine.objectiveEvalCp` on the objects `useFlawChessEngine` returns:** These are the
  actual search-core snapshot objects (`treeCommon.ts` builds them fresh per `mctsSearch` `onSnapshot`
  tick). Mutating them in place would make the search core's own internal state (used for backup/
  ranking) inconsistent with what a later render reads, violating the scope fence ("practical-score
  ranking… untouched"). Always build a **new** array/object for display.
- **Falling back to the pool grade when the lookup has no entry:** This reintroduces exactly the bug
  this phase fixes — silently showing a shallow, capped-depth number. Show `null`/`…` instead; it will
  resolve within one grading-run tick for any move actually in the candidate union.
- **Adding a fourth independent search to "fix" coverage gaps:** The locked design is explicit that
  coverage comes from candidate-set union (`shownSans ∪ displayed FC moves`), not from firing more
  searches. If the FC card's displayed root moves are ever *not* in the grading run's candidate set,
  that is a union-construction bug to fix, not a signal to add a fourth searcher.

## Common Pitfalls

### Pitfall 1: UCI/SAN key-space mismatch silently drops matches
**What goes wrong:** Comparing a UCI string from `pvLines`/`RankedLine.rootMove` directly against a
SAN string from `gradeMap` (or vice versa) never matches, so the lookup silently falls through to
"unresolved" for every move even when the grading run actually has the data.
**Why it happens:** The three provenance chains grew independently across Phases 136 (free run, UCI),
151.1 (grading hook, SAN — chosen to match Maia's SAN-labeled chart axis), and 153 (`RankedLine`, UCI
per D-08). Nothing in the existing code forced them into a common key space because each chain only
ever talked to its own display surface before this phase.
**How to avoid:** Normalize once, at lookup-build time, using the existing `sanToUci` helper
(Pattern 1). Never compare a raw UCI to a raw SAN string anywhere in the new code.
**Warning signs:** A move visibly present in both the FC card and the Maia chart still renders
different (or one shows `…` forever) numbers after this phase ships — check whether the lookup's
`gradeMapBySan → UCI` conversion step is actually running for that candidate.

### Pitfall 2: `multipv` index is an eval rank, not a stable move identity (existing project-wide caveat, applies again here)
**What goes wrong:** Keying anything by `parsed.multipv` instead of `parsed.pv[0]` silently reorders
which eval belongs to which move as search depth climbs.
**Why it happens:** Confirmed on the real vendored binary in Phase 151.1's spike
(`151.1-01-SUMMARY.md`) — MultiPV index is Stockfish's current eval-based ranking of the candidates,
not their input order.
**How to avoid:** Both `useStockfishEngine.ts` and `useStockfishGradingEngine.ts` already key correctly
(`pvMapRef` by `parsed.multipv` for the free run is fine there ONLY because it's re-sorted by index
for *display order*, not eval identity — the free run's `pvLines[i]` array order is the actual
contract consumers rely on, e.g. `engine.pvLines[0]` = best line by definition). The grading hook
already keys its cache by `pv[0]` (SAN). Any new code this phase adds must preserve this — never
introduce a new `Map` keyed by `multipv`.
**Warning signs:** A candidate's eval swaps with a different candidate's eval as depth increases.

### Pitfall 3: Widening the grading run's depth/movetime without measuring first produces either a stale-search regression or a silent under-cap
**What goes wrong:** Guessing a "safe-sounding" depth (e.g. bumping `GRADING_TARGET_DEPTH` from 14 to
20 without checking) can either (a) blow past the `RAPID_STEP_DEBOUNCE_MS` (150ms) input-responsiveness
budget on slow devices, making the grading run visibly lag every ELO-slider drag, or (b) still not
reach a depth where evals stop measurably disagreeing with the free run, reproducing this phase's bug
at a different, harder-to-notice depth.
**Why it happens:** The two runs trade off different resources: the free run has fixed wall-clock
(`MOVETIME_MS = 1500`) and narrow MultiPV (2), so it reaches deep. The grading run has a *wider*
MultiPV (candidate-union size, potentially 5-7 after this phase) at the *same* wall-clock-ish budget,
so widening MultiPV without also widening movetime proportionally reaches shallower per-candidate
depth for more candidates — the exact mechanism the seed already diagnosed as the skew source.
**How to avoid:** Run the headless Node WASM measurement (see Open Measurement section below) on real
positions BEFORE picking new constants. Don't reason about this from first principles alone — Phase
151.1 already showed the vendored binary's real MultiPV/searchmoves behavior can surprise (Caveat 1:
illegal searchmoves are silently dropped and under-count lines; that's a functional correctness
caveat, not a performance one, but it illustrates why this binary's behavior is measured, not assumed).
**Warning signs:** Grading-run values still visibly disagree with free-run values on the same UCI in
manual UAT after the depth bump, or the ELO slider becomes noticeably janky.

### Pitfall 4: The FC displayed moves arrive later than `shownSans`, so the candidate union changes shape after the grading search has already started
**What goes wrong:** `shownSans` (Maia's candidate set) is available almost immediately (Maia policy +
Maia chart data load fast); `flawChessEngine.rankedLines` streams in via the MCTS search's throttled
`onSnapshot` (~150ms cadence, `useFlawChessEngine.ts:163-180`) and its early snapshots may have fewer
or different top-2 root moves than its settled snapshot. If the grading run's candidate union is
recomputed on every FC snapshot tick, it will send a fresh `go` on nearly every tick — thrashing
(never settling long enough to reach useful depth) instead of settling.
**Why it happens:** `useStockfishGradingEngine`'s existing debounce (`RAPID_STEP_DEBOUNCE_MS = 150ms`,
`useStockfishGradingEngine.ts:268-282`) already coalesces rapid `candidateSans` changes, but it treats
ANY change to the candidate array as "needs a new search unless already cached" — the existing Pitfall
2 short-circuit (`prepareSearch`'s `ungraded.length === 0` check) only avoids a NEW `go` when every
requested SAN is already graded; it still re-triggers debounce timers on every distinct candidate-set
identity.
**How to avoid:** Feed the union as a stable, sorted, deduplicated array (mirror the existing
`candidatesKey` memo pattern in the hook itself, `useStockfishGradingEngine.ts:178`, which already
exists precisely to give the debounce effect a stable primitive dependency instead of an array
identity) built from `[...shownSans, ...flawChessDisplayedMoves].sort()` at the `Analysis.tsx` call
site, so the debounce's existing `candidatesKey`-string-equality check absorbs FC snapshot ticks that
don't actually change the SET of displayed root moves (i.e., a re-throttle of the SAME top-2 moves
produces the same sorted-union string, so no new `go` fires). When the FC top-2 genuinely changes
(rare — usually only right after a position navigation), the union changes and one new search is
correctly triggered — this is expected and desired.
**Warning signs:** The Maia chart / FC card evals never settle (constant `isGrading: true` flicker);
Network/CPU tab shows the grading Worker restarting its search dozens of times per second.

### Pitfall 5: Gating `maiaEnabled || flawChessEnabled` changes the grading run's enabled-lifetime, and the hook's Worker lifecycle effect is keyed on `enabled`
**What goes wrong:** `useStockfishGradingEngine`'s Worker-spawn effect is `useEffect(() => {...}, [enabled])` (`useStockfishGradingEngine.ts:286-384`) — it creates a NEW Worker and resets ALL state
(cache, `isReady`, `gradeMap`) every time `enabled` transitions false→true. Under the current
`maiaEnabled`-only gate, toggling the Maia switch off then back on already pays this cost. Under the
new `maiaEnabled || flawChessEnabled` gate, toggling *either* switch off while the *other* is still on
must NOT tear down the worker (only the `enabled` boolean's own true→false→true transition matters,
and OR-composition means it only goes false when BOTH switches are off).
**Why it happens:** This is mostly already correctly handled by boolean OR semantics — flagged here
because it's the one lifecycle edge case worth an explicit test: toggling FlawChess off while Maia
stays on should leave the grading worker running uninterrupted (no re-spawn), and vice versa.
**How to avoid:** Write the gating expression once (`const gradingEnabled = maiaEnabled ||
flawChessEnabled`) and pass it to `enabled`; don't derive it inline at each call site, so both the
`fen` prop (`fen: gradingEnabled ? position : null`) and `enabled` prop stay consistent with each
other (today's code, `Analysis.tsx:719-721`, has both `fen` and `enabled` separately conditioned on
`maiaEnabled` — replicate that pairing exactly, just with the OR'd condition, or the fen/enabled
pairing can desync and produce a worker that's alive but never sent a position).
**Warning signs:** Toggling FlawChess Engine off (with Maia still on) makes the Maia chart's evals
briefly disappear/reset even though Maia itself never changed state.

### Pitfall 6: `RankedLine` is a frozen type — don't be tempted to add a "reconciled" field to it
**What goes wrong:** Adding e.g. `reconciledEvalCp?: number | null` to the shared `RankedLine`
interface (`types.ts`) looks convenient (one field carries both the raw pool grade AND the display
value) but violates the explicit Phase 153 freeze ("locked for the rest of the v2.0 FlawChess Engine
milestone… Phases 154-157 build against them unchanged") and this phase's own scope fence ("search
core/practical ranking untouched").
**How to avoid:** Build parallel display-only objects (Pattern 2) instead of extending the frozen
type. The type stays exactly as-is; only `Analysis.tsx`'s local reconciliation code constructs new
values.

## Progressive Refinement / Settledness (Research Focus #6, detail)

There is no single boolean "is this eval settled enough to display" gate needed beyond what already
exists: `formatScore(null, null)` already renders `…` for "not yet resolved," and both source hooks
already stream progressively-refining values into their own state (`useStockfishEngine`'s
`commitPvSnapshot` on every accepted `info` line; `useStockfishGradingEngine`'s
`commitDisplayedGradeMap` likewise). Because `buildEvalLookup` is a pure recomputation on every
render where its inputs changed, "settledness" is emergent: as long as precedence never regresses
(free-run entries are never overwritten by grading-run entries once present), the displayed number can
only move toward its final value, never jump backward to a worse/older one. No new debounce or
"minimum display time" mechanism is needed — this matches the project's existing accepted convention
of eval numbers visibly refining as depth increases (Pitfall 5 in `useStockfishEngine.ts`'s own
docstring, deliberately relaxed for "lichess-style live streaming behavior").

## Open Measurement: Depth/Latency Trade

CONTEXT.md requires measuring the latency/depth trade on real positions before fixing new constants
for both runs, with named constants (no bare thresholds).

**Recommended method** (per the project's own established precedent, `project_headless_stockfish_wasm_verification` memory + Phase 151.1's spike): run the vendored
`frontend/public/engine/stockfish-18-lite-single.js` headlessly via Node (copy to a `.cjs` file
outside any ESM-resolved directory so `require`/plain script execution works; it auto-starts a UCI CLI
on stdin/stdout — this is exactly the technique used for Phase 151.1's `searchmoves-probe.html` spike,
run via "the engine's own Node CLI mode," per `151.1-01-SUMMARY.md`). Feed it real FEN + candidate-UCI
sets captured from a live `/analysis` session (a middlegame and an endgame position, at minimum, since
depth-per-second varies a lot by position complexity/branching factor).

**What to measure:**
1. **Free run:** for `MultiPV` = 2, 3, 4 at the existing fixed `MOVETIME_MS = 1500`, record the depth
   reached (the last `info depth N` line before `bestmove`) per MultiPV width. This directly answers
   CONTEXT's "the free run's MultiPV width trades against eval-bar depth" — wider MultiPV should show
   measurably shallower per-line depth at the same movetime.
2. **Grading run:** for candidate-union sizes 4, 6, 8 (matching realistic `shownSans` (up to
   `CANDIDATE_HARD_CAP = 5`, `moveQuality.ts:51`) ∪ FC displayed moves (`MAX_LINES = 2`,
   `FlawChessEngineLines.tsx:45`) ≈ 5-7 typically), sweep `movetime` (e.g. 1500/2500/4000/6000ms) and
   record depth reached per candidate count. Also verify whether removing the `depth 14` cap entirely
   (i.e., `go searchmoves <cands> movetime <N>` with no `depth` clause) changes behavior versus keeping
   a much higher depth ceiling (e.g. `depth 20`) as a belt-and-suspenders safety valve — the free run
   itself uses only a movetime+nodes cap with no depth clause, so mirroring that convention for the
   grading run should also be evaluated as an option.
3. **Agreement check:** for the same position, compare the grading run's eval for a shared candidate
   (e.g. O-O) against the free run's eval for that same move at the chosen final constants — the target
   is a repeat of the seed's own "O-O +1.4 ≈ +1.3" agreement evidence, i.e. confirm the new depth/
   movetime combination reduces cross-search disagreement to noise level (a few centipawns), not that
   it's provably zero.

**Constants that fall out of this measurement** (name them in the plan once measured, don't hardcode a
guess in RESEARCH.md itself): a revised `GRADING_TARGET_DEPTH` (or its removal in favor of a pure
movetime/nodes cap, mirroring `useStockfishEngine.ts`'s own convention), a revised
`GRADING_MOVETIME_SAFETY_CAP_MS`, and possibly a revised free-run `MULTIPV` if the measurement shows
the current value of 2 already covers the SF card's needs with margin (CONTEXT.md: "Set it to cover
`N_sf` plus a margin"). `N_sf` today is 2 (the SF card shows top-2), so `MULTIPV` may not need to
change at all — but the measurement should still confirm depth-at-MultiPV=2 is deep enough that raising
it wouldn't meaningfully improve free-run coverage of the union set before ruling that out.

## Runtime State Inventory

Not applicable — this is a pure frontend display-logic change with no persisted state (v1.29 D-4: no
schema, no new endpoints, analysis state lives in the URL) and no rename/refactor/migration. No
datastore, OS-registered state, secrets, or build artifacts reference any of the touched identifiers.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js (for the headless WASM measurement harness) | Open Measurement step | ✓ (dev machine) | project's existing Node toolchain | — |
| Vendored `stockfish-18-lite-single.js`/`.wasm` | Both runs, and the measurement harness | ✓ | already committed at `frontend/public/engine/` | — |
| Browser Worker API | Both hooks at runtime | ✓ (target: browsers, not this dev measurement) | — | — |

No missing dependencies. The measurement harness is a throwaway dev-only script (per Phase 151.1
precedent: build it, use it, delete it — do not commit a permanent probe file to `public/`).

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json` (not absent, explicitly enabled).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest ^4.1.7 (`@vitest-environment jsdom` per-file directive where DOM is needed) |
| Config file | `frontend/vite.config.ts` (vitest config colocated, per existing convention — confirm exact path at plan time) |
| Quick run command | `npm test -- --run <path-to-file>` (from `frontend/`) |
| Full suite command | `npm test -- --run` (from `frontend/`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEED-087 SC1 | `buildEvalLookup` resolves a UCI present in both `pvLines` and `gradeMap` to the free-run value | unit | `npm test -- --run src/lib/engineEvalLookup.test.ts` | ❌ Wave 0 (new file) |
| SEED-087 SC1 | `buildEvalLookup` resolves a UCI present ONLY in `gradeMap` (SAN-keyed) via `sanToUci` conversion | unit | same file | ❌ Wave 0 |
| SEED-087 SC1 | A UCI present in neither source resolves to `null`/`null` (never falls back to a pool grade — there is no pool grade parameter to this function at all, enforcing the exclusion structurally) | unit | same file | ❌ Wave 0 |
| SEED-087 SC2 | Grading-run candidate set is `shownSans ∪ displayed FC moves`, deduplicated | unit | extend `useStockfishGradingEngine.test.ts` or a new `Analysis.tsx`-adjacent union-builder test | ⚠️ existing file covers hook internals only — a union-construction helper (if extracted) needs its own test |
| SEED-087 SC2 | Grading run is gated on `maiaEnabled \|\| flawChessEnabled`, not `maiaEnabled` alone | integration | extend `Analysis.test.tsx` | ⚠️ existing file mocks the hook entirely (`Analysis.test.tsx:49`) — needs a new assertion on the mock's call args/enabled prop across the 4 toggle-state combinations |
| SEED-087 SC3 | `classifyMoveQuality` receives the reconciled map, not the raw `grading.gradeMap` | unit/integration | `moveQuality.test.ts` (signature unchanged, so existing tests keep passing) + `Analysis.test.tsx` assertion that qualityBySan's evals match engine.pvLines when both sources cover the same move | ⚠️ existing `moveQuality.test.ts` already covers the pure function; the NEW behavior to test is what `Analysis.tsx` feeds it |
| SEED-087 SC4 | `computeFlawChessVerdict`'s FC-pick eval can no longer exceed the SF-best eval when both are lookup-sourced (the Qc7 +2.8 vs O-O +1.3 case) | unit | new case in `flawChessVerdict.test.ts` OR (better, since the classifier itself already correctly clamps `drop` to >= 0 — the bug was the INPUT, not the classifier) a new `Analysis.tsx`-level integration test proving the two RankedLine/PvLine inputs passed to `computeFlawChessVerdict` are now lookup-sourced and therefore mutually comparable | ⚠️ `flawChessVerdict.test.ts` already exists and its `max(0, …)` clamp is unaffected by this phase — the real regression test belongs at the `Analysis.tsx` wiring level, not the pure classifier |
| SEED-087 SC5 | Practical scores/MCTS search untouched | regression | full existing `workerPool.test.ts`, `mctsSearch`/`select.test.ts`, `useFlawChessEngine.test.ts` suites stay green with zero changes | ✓ all exist |

### Sampling Rate
- **Per task commit:** `npm test -- --run <touched test files>` (from `frontend/`)
- **Per wave merge:** `npm test -- --run` (full frontend suite) + `npx tsc -b` (per CLAUDE.md: shared-type/property-access changes need a real type-check, since `npm run lint`/`npm test` don't type-check)
- **Phase gate:** full frontend suite green + `npx tsc -b` clean before `/gsd-verify-work`; live manual UAT of the exd5/Bc5/Qc7 cases from the seed (same positions if reproducible) to confirm the numbers now agree across cards

### Wave 0 Gaps
- [ ] `frontend/src/lib/engineEvalLookup.test.ts` — new pure-lib test file for `buildEvalLookup`/`getBySan` (Pitfall 1 coverage: UCI/SAN key mismatch, precedence order, unresolved → null)
- [ ] No framework install needed — vitest is already configured and used identically by every sibling `lib/*.test.ts` file in this codebase

## Existing Tests This Phase Touches or Must Extend

| File | Current coverage | Impact of this phase |
|------|-------------------|----------------------|
| `frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts` (302 lines) | Init sequence, search command shape (`setoption MultiPV`/`go depth 14 searchmoves … movetime 2500`), pv[0] keying, white-POV normalization, cache short-circuit, stale-guard | Constants baked into existing assertions (`go depth 14 … movetime 2500`, `useStockfishGradingEngine.test.ts:8-9`) WILL need updating once the Open Measurement step lands new depth/movetime constants — this is expected, not a regression |
| `frontend/src/pages/__tests__/Analysis.test.tsx` (331 lines) | Mocks `useStockfishGradingEngine` entirely with a static return (`Analysis.test.tsx:49-...`) so the hook's own behavior is out of scope here; asserts wiring/gating | Needs new assertions for the `maiaEnabled \|\| flawChessEnabled` gating condition and the reconciled-values wiring (this is where the real regression coverage for SC1/SC2/SC4 belongs, per the test map above) |
| `frontend/src/lib/flawChessVerdict.test.ts` (178 lines) | Pure classifier tests via hand-built `RankedLine`/`PvLine` fixtures | **No signature change** — stays green untouched; fixtures already construct `RankedLine` objects with explicit `objectiveEvalCp` values, exactly matching how `Analysis.tsx` will now construct its reconciled objects |
| `frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` | Component tests via hand-built `fcLine`/`sfLine` fixtures (identical fixture pattern to `flawChessVerdict.test.ts`) | **No signature change** — stays green untouched, same reasoning |
| `frontend/src/lib/__tests__/moveQuality.test.ts` (367 lines) | Pure `classifyMoveQuality`/`selectCandidatesByMass`/`bucketMovesByQuality` tests via hand-built `Map<string, MoveGrade>` fixtures | **No signature change** — stays green untouched; `Analysis.tsx` just changes what map it constructs and passes in, which is outside this file's test boundary |
| `frontend/src/lib/engine/__tests__/workerPool.test.ts` | Pool dispatch/priority/lifecycle tests | **Untouched** — confirms the scope fence (workerPool internals not touched by this phase) |
| `frontend/src/components/analysis/__tests__/MaiaMoveQualityBar.test.tsx` | Bucket rendering + hover popovers, via hand-built `qualityBySan` fixtures | **No signature change** — stays green untouched, same funnel-point reasoning |

**Net effect:** the phase's actual test surface is narrow and well-isolated — one new pure-lib test
file, targeted edits to `useStockfishGradingEngine.test.ts`'s hardcoded command-string assertions
(constants only), and new `Analysis.test.tsx` integration assertions for gating + reconciled wiring.
Every other existing suite listed above should require zero edits, which is itself a design
correctness signal worth verifying at plan-review time — if implementing this phase turns out to
require editing `flawChessVerdict.test.ts`, `FlawChessAgreementVerdict.test.tsx`, or
`moveQuality.test.ts`, that's a sign the reconciliation leaked into a place other than `Analysis.tsx`'s
orchestration layer and the design should be reconsidered.

## Security Domain

`security_enforcement` is not explicitly disabled in `.planning/config.json` (absent = enabled), but
this phase has essentially no attack surface: no new user input, no new network calls, no new auth/
session paths, no new npm packages — it only changes which already-client-computed, already-rendered
number is selected for display. Directly analogous to Phase 157's own Security Domain assessment
(`157-RESEARCH.md:435-454`), reused here since the surface is identical.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Not touched |
| V3 Session Management | No | Not touched |
| V4 Access Control | No | Not touched |
| V5 Input Validation | Marginal | UCI/SAN strings flowing into the new lookup originate entirely from trusted client-side engine outputs (`pvLines`, `gradeMap`, `rankedLines`), never from user text input; `sanToUci`/existing `formatScore` already wrap all chess.js parsing in try/catch and never throw on malformed input |
| V6 Cryptography | No | Not touched |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via engine-derived eval/move strings rendered as prose or popover content | Tampering (low likelihood — all data is client-computed, not server/user-supplied) | Already mitigated by construction: every render site is a React child (auto-escaped), matching the existing "T-137-03/T-155-04 mitigated" convention already documented in `FlawChessEngineLines.tsx`'s and `EngineLines.tsx`'s own docstrings |

## Sources

### Primary (HIGH confidence)
- Direct code read (2026-07-07) of every file listed in the Data Flow section above:
  `useStockfishEngine.ts`, `useStockfishGradingEngine.ts`, `workerPool.ts`, `Analysis.tsx`,
  `moveQuality.ts`, `flawChessVerdict.ts`, `FlawChessEngineLines.tsx`,
  `FlawChessAgreementVerdict.tsx`, `engine/types.ts`, `sanToSquares.ts`, `liveFlaw.ts`,
  `MovesByRatingChart.tsx`, `MaiaMoveQualityBar.tsx`, `positionVerdict.ts`, `useFlawChessEngine.ts`.
- `.planning/phases/158-.../158-CONTEXT.md` — the locked user decisions (verbatim source of truth for
  this phase's design).
- `.planning/seeds/SEED-087-flawchess-engine-eval-provenance-reconciliation.md` — the full amended
  design doc, root-cause evidence (exd5/Bc5/Qc7 observations), and breadcrumbs.
- `.planning/milestones/v1.32-phases/151.1-.../151.1-01-SUMMARY.md` — the real-binary spike confirming
  `searchmoves`+MultiPV behavior and the two load-bearing caveats (illegal-move drop, multipv-is-eval-
  rank) directly reused by this phase's design.

### Secondary (MEDIUM confidence)
- `.planning/phases/157-.../157-RESEARCH.md`'s Security Domain section, reused as a direct precedent
  for this phase's own (structurally identical) security assessment.
- Project memory `project_headless_stockfish_wasm_verification.md` — the headless Node WASM
  measurement technique recommended for the Open Measurement step.

### Tertiary (LOW confidence)
- None — every claim in this document traces to a direct code read or a locked CONTEXT.md/seed
  decision. No claim here is `[ASSUMED]`.

## Assumptions Log

No claims in this research are tagged `[ASSUMED]`. Every architectural claim was verified by direct
file read; every design decision cited as "locked" was copied verbatim from `158-CONTEXT.md`. The one
genuinely open item (exact new depth/movetime constants) is explicitly deferred to the Open Measurement
step rather than guessed at here, per CONTEXT.md's own instruction ("Measure latency/depth on real
positions before fixing the constants").

**If this table is empty:** All claims in this research were verified or cited — no user confirmation
needed. (Confirmed empty.)

## Open Questions

1. **Exact new `GRADING_TARGET_DEPTH`/`GRADING_MOVETIME_SAFETY_CAP_MS` values (or their replacement
   with a movetime-only cap mirroring `useStockfishEngine.ts`'s convention).**
   - What we know: the current depth-14/2500ms cap is the proven skew source; the free run uses only
     movetime+nodes with no depth ceiling.
   - What's unclear: the exact numbers that balance "deep enough to agree with the free run" against
     "fast enough not to visibly lag the ELO slider / FC card settling."
   - Recommendation: run the Open Measurement step (headless Node harness) as an early Wave 0 task,
     before implementing the reconciliation wiring — the wiring code doesn't depend on the final
     constants, but the plan's task list should sequence the measurement first so the constants are
     known when `useStockfishGradingEngine.ts`'s edits happen.

2. **Whether the free run's `MULTIPV` needs to change at all.**
   - What we know: CONTEXT.md frames it as a tuning knob ("Set it to cover `N_sf` plus a margin"); the
     SF card only ever displays `N_sf = 2` lines today.
   - What's unclear: whether raising MultiPV from 2 to e.g. 3-4 (to pre-cover more of the union set via
     the "free run first" precedence, reducing grading-run load) is worth the depth cost the Open
     Measurement step will quantify.
   - Recommendation: measure first (Open Measurement); a plausible outcome is "leave `MULTIPV = 2`
     unchanged" if the grading run alone can be tuned to agree closely enough — don't treat widening
     the free run as required by this phase.

3. **Where exactly the `MAX_LINES_DISPLAYED` count for FC-card reconciliation should be sourced from.**
   - What we know: `FlawChessEngineLines.tsx`'s own `MAX_LINES = 2` constant is local/unexported today;
     `Analysis.tsx` needs to know how many of `flawChessEngine.rankedLines` are actually rendered, to
     avoid building lookup entries (and growing the grading candidate union) for lines that never
     display.
   - What's unclear: whether to export `FlawChessEngineLines`'s `MAX_LINES` for `Analysis.tsx` to
     import, or duplicate the constant at the `Analysis.tsx` call site with a comment cross-referencing
     it.
   - Recommendation: export it (`FlawChessEngineLines.tsx:45`) — a single source of truth is cheap here
     and avoids the two constants silently drifting apart (e.g. if `MAX_LINES` is later made
     configurable per the deferred line-count work, `Analysis.tsx`'s union-building code should track
     it automatically).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, every reused module directly read and confirmed
- Architecture: HIGH — full data-flow trace of all three provenance chains completed via direct file
  reads with exact file:line citations; the UCI/SAN key mismatch is a concretely observed fact, not a
  guess
- Pitfalls: HIGH — every pitfall traces to either an existing code comment/docstring in this exact
  codebase (Pitfall 2, 5) or a directly observed structural property (Pitfalls 1, 3, 4, 6)

**Research date:** 2026-07-07
**Valid until:** 30 days (stable frontend codebase, no fast-moving external dependency; re-verify file:
line references if Phase 157/155/156 code shifts significantly before this phase is planned)
