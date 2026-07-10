# Phase 162: Grading-run-authoritative eval reconciliation — precedence flip - Research

**Researched:** 2026-07-10
**Domain:** Frontend React/TypeScript — client-side Stockfish WASM eval reconciliation (`/analysis` page)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Locked by SEED-090 (read the seed — it is the design doc)**
- **D-01 Precedence flip:** `buildEvalLookup` becomes grading-first; free-run values fill only not-yet-graded moves. A move's number upgrades once (free → grading) then only sharpens within the grading stream.
- **D-02 Union extension:** `unionSans` (Analysis.tsx:796-800) extends with the free run's top-2 root-move SANs, so there is no "uncovered displayed move" and hence no cross-search gap grade. Keep the existing sort+dedup.
- **D-03 Best-label rule:** Best = argmax over reconciled displayed evals, tie-break toward free-run `bestSan`. Stop passing the free-run pin to `classifyMoveQuality` once grading values are in (or pass a grading-derived pin) — keeping the free-run pin would recreate the bug in mirror image.
- **D-04 Stockfish card reads the lookup:** its two PV lines' evals resolve through the reconciled lookup; re-sort the card's 2 lines by reconciled eval. PV move-sequence text stays free-run (display-only divergence accepted).
- **D-05 Depth label:** card headline keeps the free run's depth (it describes the displayed PV lines).
- **D-06 Source C stays display-excluded:** FC card hover previews read the reconciled lookup, never the MCTS pool grade (carried from Phase 158 / SEED-089).

**SF board-arrow alignment (discussed — not covered by the seed)**
- **D-07:** The green SF best-move arrow (`engineArrows`, Analysis.tsx:1291-1303, currently raw `engine.pvLines[0].moves[0]`) **follows the reconciled argmax** — the same source as the card's re-sorted line 1 and the chart's Best crown. Arrow, card, chart, and verdict agree by construction; the arrow may jump once when grading lands (~4s), same visual class as the accepted label flips (D-10). The amber FC arrow (practical pick) is untouched.

**Eval bar / headline eval (discussed — seed change 5 resolved as option b)**
- **D-08:** Free-run first paint (<100ms unchanged), then the headline/bar **refines once to the reconciled best move's eval** when grading lands. When `gradingEnabled` is false, the bar stays free-run — no special casing beyond the lookup's natural fallback.

**Union-churn restart stance (discussed)**
- **D-09:** The free run's top-2 contribution joins the grading union **only after the free run's `bestmove` commits** — day one, not UAT-reactive. This eliminates the restart source this phase itself introduces (2nd PV line reordering mid-free-run). Costs ≤1.5s delay on grading ≤1 extra move (invisible given grade cache + progressive streaming). Maia/FC union churn behavior is unchanged.

**Label-flip flicker stance (discussed)**
- **D-10:** **Live argmax per committed reconciled snapshot** — labels, arrow, bar, and numbers re-derive together from each snapshot, so a contradiction is impossible at every instant; near-tie Best/Good flips mid-stream are accepted (same class as depth-climb reordering, rarer now that D-09 gates union churn). **If UAT flags flicker, the remedy is atomic-at-commit (one switch of the whole reconciled map at grading `bestmove`), NEVER a label pin** — pinning the label while grading numbers stream reopens the contradiction window the phase exists to close.

**Anti-circularity note (Claude flagged, no user decision needed)**
- **D-11:** `bestSan` (Analysis.tsx:749) stays **free-run-derived where it is a grading-union INPUT** (`selectCandidatesByMass` union contribution, D-09 timing) — the reconciled argmax is downstream of the union, so deriving the union input from it would be circular. Only display consumers (chart crown, labels, arrow, bar, **verdict**) switch to the reconciled source.

### Claude's Discretion
- Where the argmax/derived-pin logic lives (extend `engineEvalLookup.ts`, a new pure helper, or Analysis.tsx memo) — pick the seam that keeps functions small; pure lib functions preferred for testability.
- How the "free-run bestmove committed" signal threads into the `unionSans` memo (the free-run hook already knows its terminal state).
- Test strategy per project norms (vitest; the seed's verification sketch lists the two mandatory units: precedence flip, and the mirror-image Best-label case).

### Deferred Ideas (OUT OF SCOPE)
- SEED-089 (one high-MultiPV pass, single worker) stays open as the fallback architecture — revisit only if mobile CPU/battery cost of two live workers becomes a complaint, and then with the day-one clamp amendment.
- Atomic-at-commit display switching — pre-agreed remedy if UAT flags label/arrow flicker (D-10); not built unless flagged.
- Todo `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` (WR-01) — unrelated chart-styling nit, stays in the todo backlog.
</user_constraints>

## Project Constraints (from CLAUDE.md)

- **Frontend TypeScript strictness:** `noUncheckedIndexedAccess` is on — every array/Map index access is `T | undefined`; narrow before use (`array[i]` from `pvLines`/`rankedLines`/`unionSans` etc. all need this).
- **No magic numbers** — any new epsilon/threshold (e.g. an argmax tie-break tolerance, if introduced) must be a named constant, not a bare literal.
- **Type safety** — no `any`; prefer explicit return types on every new/changed function (project convention already followed by every file this phase touches).
- **Function size limits** — nesting depth soft 3/hard 4, logic LOC soft 100/hard 200, cognitive complexity ≤15. `Analysis.tsx` is already large (2321 lines) with many small `useMemo` blocks — new logic should follow that pattern (a new small memo or a new pure-lib helper), not grow an existing memo past its current shape.
- **Minimum font size `text-sm`** — no UI copy changes are anticipated in this phase (only precedence of shown numbers/labels), but any new prose must respect the floor.
- **No Prettier on frontend** — ESLint only; do not run `prettier --write`.
- **Knip runs in CI** — if any function becomes unused after the precedence flip (e.g. if `classifyMoveQuality`'s `designatedBestSan` fallback path becomes dead in one direction), verify it doesn't trip knip; more likely nothing becomes dead since the same functions are reused with different call-site arguments.
- **Pre-merge gate** — `ruff`/`ty`/`pytest` are irrelevant here (frontend-only); the frontend leg of the gate (`npm run lint && npm test -- --run`, plus `npx tsc -b` per `feedback_frontend_run_tsc_build` memory) must pass before squash-merge.
- **`data-testid` / ARIA convention** — no new interactive elements are anticipated (existing badges/arrows/spans keep their testids); if a new pure display element is added, it must follow the kebab-case `component-element` convention already used throughout `Analysis.tsx`.

## Summary

This phase is a **precedence flip inside an existing, already-built reconciliation system** (Phase 158 / SEED-087), not new architecture. Phase 158 built `engineEvalLookup.ts`'s `buildEvalLookup()` as a UCI-keyed merge of two Stockfish sources — the fast free run (`useStockfishEngine`, MultiPV=2, movetime 1500) and the shared grading run (`useStockfishGradingEngine`, `searchmoves`-restricted MultiPV, movetime 4000) — with **free-run-first** precedence. That precedence is provably wrong for the flagship "Best never shows a lower number than Good" invariant: the free run is shallower, so a move it hasn't caught up on can display a stale/wrong number even after the deeper grading run has graded it. SEED-090 (superseding SEED-089's more invasive redesign) flips this to **grading-first**, extends the grading union so it covers literally everything the free run displays (closing the only structural gap), and re-derives every display consumer's "Best" designation from the reconciled map's own argmax instead of the free run's independent pick.

The mechanical core of the change is small and well-isolated: `buildEvalLookup`'s two loops swap order (or the `!lookup.has()` guards swap direction), `unionSans` gains two more SANs gated on a free-run-commit signal, and `qualityBySan`'s call into `classifyMoveQuality` stops pinning the free-run's `bestSan`. However, **research surfaced two call sites CONTEXT.md's canonical_refs describes as "unchanged wiring" that are, in fact, NOT lookup-derived today** and will silently reintroduce the exact bug this phase exists to fix if left untouched: (1) `FlawChessAgreementVerdict`'s `stockfishLine` prop at `Analysis.tsx:1881` is wired to raw `engine.pvLines[0]`, bypassing `evalLookup` entirely; (2) `useGameOverlay.ts`'s `evalCp`/`evalMate`/`evalDepth` passthrough (feeding the right eval bar off the game main line / in free-play mode) also reads raw `engine.evalCp`/`engine.evalMate`/`engine.depth`, never `evalLookup`. Both currently happen to be harmless because free-run-first precedence makes `evalLookup`'s value for a free-run move byte-identical to the raw free-run value — an equivalence that breaks the moment precedence flips. The plan MUST budget explicit tasks for both.

A second research finding worth flagging for the plan: the Stockfish card is structurally capped at 2 displayed lines (`engine.pvLines`, `MULTIPV = 2`, untouched by this phase). D-07's "arrow follows the reconciled argmax — the same source as the card's re-sorted line 1" is only literally true when the true reconciled best move happens to be one of those 2 free-run candidates. Because the grading union also includes Maia-only and FlawChess-only candidates (e.g. a played blunder, or a human-plausible move Stockfish's shallow search never considered), the global reconciled argmax CAN be a move the Stockfish card never displays at all — exactly the `exd6`-outranks-`Rad1` scenario the seed's own diagnosis describes. The plan should make an explicit, documented scope call on this (see Open Questions) rather than silently assume the two always coincide.

**Primary recommendation:** Implement the precedence flip as a small, additive change to `engineEvalLookup.ts` plus a single new pure helper (e.g. `resolveReconciledBest`) that computes "argmax over the reconciled union, tie-break toward free-run `bestSan`" once, and thread that ONE value through every display consumer (labels via `classifyMoveQuality`'s existing pin parameter, arrow, eval bar, and — correcting CONTEXT.md's assumption — the verdict's Stockfish side) so there is exactly one source of truth for "what is Best" on the page, not five independent derivations that happen to usually agree.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Free-run Stockfish search (fast first paint) | Browser / Client (Web Worker) | — | `useStockfishEngine.ts` — vendored WASM in a dedicated Worker, no server round-trip (D-4/locked since Phase 137) |
| Grading-run Stockfish search (authoritative eval) | Browser / Client (Web Worker) | — | `useStockfishGradingEngine.ts` — second, independent WASM Worker |
| Eval reconciliation (UCI-keyed lookup, precedence) | Browser / Client (pure lib) | — | `engineEvalLookup.ts` — worker-free, deterministic, testable in isolation |
| Best/Good quality classification | Browser / Client (pure lib) | — | `moveQuality.ts` — reuses `liveFlaw.ts`'s sigmoid, no new math |
| Display: Stockfish card, FC card, chart, quality bar, verdict, board arrows, eval bar | Browser / Client (React components) | — | `pages/Analysis.tsx` + `components/analysis/*` — all consume the lookup/quality map, no independent search logic |
| Precomputed game-review overlay (backend eval_series) | Browser / Client (React hook) | — | `useGameOverlay.ts` — reads server-computed `eval_series`/`flaw_markers` on the game main line; falls back to the LIVE engine off the main line (the fallback path is this phase's concern, the precomputed path is not) |

This phase is **entirely Browser/Client tier** — no Frontend-Server (SSR), API/Backend, CDN, or Database involvement. It touches zero backend code, zero HTTP calls, zero persisted state (confirmed: Phase Boundary explicitly states "Frontend-only, no backend").

## Standard Stack

N/A — this phase adds no new dependency. It is a precedence/wiring change inside existing, already-vendored code:
- `stockfish-18-lite-single.js` (vendored WASM binary, `public/engine/`) — untouched, same binary both Workers already load.
- `chess.js` — already a dependency, used for SAN<->UCI conversion via `@/lib/sanToSquares`.
- `vitest` — already the project's frontend test runner.

No `npm install` is required. No Package Legitimacy Audit applies (no packages added).

## Architecture Patterns

### System Architecture Diagram

```
FEN position (board navigation)
   │
   ├──────────────────────────────────────────────────────────────┐
   ▼                                                                ▼
useStockfishEngine (FREE RUN)                          useMaiaEngine + useFlawChessEngine
 MultiPV=2, movetime 1500ms                              (unchanged by this phase)
   │  pvLines[0..1], evalCp, evalMate, depth, isAnalyzing        │
   │                                                              │
   │  bestSan = pvLines[0].moves[0] as SAN  ────────────┐         │
   │  (D-11: stays free-run-derived — union INPUT)       │         │
   │                                                     ▼         ▼
   │                                              unionSans = Maia mass-set(≤5)
   │                                                ∪ playedSan ∪ bestSan
   │                                                ∪ FC card top-2
   │                                                ∪ [D-09] freerun top-2
   │                                                  (added ONLY after free-run
   │                                                   bestmove commits)
   │                                                     │
   │                                                     ▼
   │                                       useStockfishGradingEngine (GRADING RUN)
   │                                       searchmoves-restricted MultiPV,
   │                                       movetime 4000ms, per-(FEN,SAN) cache
   │                                                     │
   │                                                gradeMap (SAN-keyed)
   │                                                     │
   ▼                                                     ▼
   └──────────────────► buildEvalLookup(pvLines, gradeMap, fen) ◄──────────────────┘
                          [THIS PHASE: flip to GRADING-FIRST —
                           grading wins on overlap, free-run fills gaps only]
                                          │
                                    evalLookup (UCI-keyed Map<uci, MoveGrade>)
                                          │
                     ┌────────────────────┼─────────────────────────────────┐
                     ▼                    ▼                                 ▼
        reconciledRankedLines    qualityBySan (via classifyMoveQuality,     [NEW] resolveReconciledBest
        (FC card evals,          pin STOPS being free-run bestSan —         (argmax over reconciled union,
         unchanged mechanism)    D-03: argmax over reconciled evals)        tie-break → bestSan)
                     │                    │                                 │
                     ▼                    ▼                                 ▼
          FlawChessEngineLines   MovesByRatingChart / MaiaMoveQualityBar    ┌─────────────┬──────────────┬───────────────┬──────────────┐
          (FC card — unchanged)  (Best/Good colors, crown — auto-flows)     ▼             ▼              ▼               ▼
                                                                      engineArrows   EngineLines    Eval bar /     FlawChessAgreementVerdict
                                                                      (D-07: green   (D-04: re-sort  headline       (stockfishLine —
                                                                       SF arrow →     card's 2 lines   (D-08: refine  MUST route through
                                                                       reconciled     by reconciled    to reconciled  evalLookup — NOT
                                                                       argmax UCI)    eval)            best's eval)   raw pvLines[0]
                                                                                                                       today, see Pitfall 1)
```

### Recommended Approach: single canonical "reconciled best" value

Rather than five independent argmax derivations that happen to usually agree, compute ONE value once per render and thread it everywhere:

```typescript
// New pure helper — engineEvalLookup.ts is the natural home (co-located with
// buildEvalLookup, already imports MoveGrade + evalToExpectedScore's sibling module).
export function resolveReconciledBest(
  evalLookup: Map<string, MoveGrade>,
  candidateUcis: string[],       // the union's UCIs (grading.gradeMap keys, converted)
  mover: MoverColor,
  tieBreakUci: string | null,    // free-run bestSan's UCI (D-03's tie-break target)
): string | null {
  let bestUci: string | null = null;
  let bestEs = -Infinity;
  for (const uci of candidateUcis) {
    const grade = evalLookup.get(uci);
    if (!grade) continue;
    const es = evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
    if (es > bestEs) {
      bestEs = es;
      bestUci = uci;
    } else if (es === bestEs && uci === tieBreakUci) {
      bestUci = uci; // exact-tie tie-break toward the free-run pick
    }
  }
  return bestUci;
}
```

This mirrors `classifyMoveQuality`'s existing internal top-scorer loop (`moveQuality.ts:78-87`) almost exactly — the difference is this version operates on UCI keys (so it can feed the arrow/verdict, which are UCI-based) and returns the winning move, not a full classification map. `classifyMoveQuality` keeps its own SAN-keyed internal loop unchanged; the call site (`Analysis.tsx:871`) passes the SAN form of this same resolved UCI as `designatedBestSan` instead of the free-run `bestSan`, so `classifyMoveQuality`'s existing "honor `designatedBestSan` as best" path (already tested, `moveQuality.test.ts:158`) does the labeling — no change needed inside `classifyMoveQuality` itself.

### Pattern: "free-run bestmove committed" signal (D-09) needs no hook changes

`useStockfishEngine` already exposes everything needed: `pvLines` is synchronously cleared to `[]` at the top of the debounce effect on every FEN change (`useStockfishEngine.ts:151`), and `isAnalyzing` is `true` exactly while a search is in flight, flipping to `false` only on a **non-stale** `bestmove` commit (`useStockfishEngine.ts:328-330`). Therefore:

```typescript
const freeRunCommitted = engine.pvLines.length > 0 && !engine.isAnalyzing;
```

is a reliable "has the free run committed a bestmove for the CURRENT position" signal with **zero changes to `useStockfishEngine.ts`** — confirming the Claude's-Discretion note ("the free-run hook already knows its terminal state") literally means "the existing return shape is sufficient," not "add a new field." Use this to gate the D-02 union extension per D-09: only include `pvLines[0]`/`pvLines[1]`'s SANs in `unionSans` when `freeRunCommitted` is true.

### Anti-Patterns to Avoid
- **Deriving "Best" independently at each display site.** Phase 158 already had 3 provenance chains that silently diverged; this phase's whole point is collapsing them to one canonical resolution. Don't let the arrow, the label, the bar, and the verdict each re-run their own argmax over slightly different candidate sets.
- **Assuming `getByUci(evalLookup, X) === rawSourceValue` still holds anywhere it held before the flip.** It held for free-run values under the OLD (free-run-first) precedence by construction. It does NOT hold under the NEW precedence for any move the grading run has since graded. Every call site that reads a raw engine field instead of the lookup is a latent regression under this phase (see Pitfall 1).
- **Widening the Stockfish card past 2 lines, or bumping its `MULTIPV`, to "fix" the D-07 argmax-outside-card-lines edge case.** Explicitly forbidden by the Phase Boundary ("no MultiPV retune... Depth 19 intact").

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Expected-score conversion / sigmoid | A new eval→win% formula | `evalToExpectedScore` (`@/lib/liveFlaw.ts`) — already used by `classifyMoveQuality` | Single source of the Lichess-K sigmoid; a second implementation would drift |
| Argmax-with-tie-break | Ad-hoc sort-and-take-first in each consumer | One new pure helper (`resolveReconciledBest`, see above), called once, threaded via props/memo | Phase 158's mistake (3 independent chains) is the bug this phase fixes — don't reintroduce the pattern |
| SAN↔UCI conversion | A second `sanToUci`/`uciToSan` | `@/lib/sanToSquares`'s existing functions (already imported by `engineEvalLookup.ts`, `useStockfishGradingEngine.ts`) | Enforced by `engineEvalLookup.ts`'s own docstring; a duplicate would violate the module's stated contract |

**Key insight:** every piece of math this phase needs (sigmoid, argmax, SAN/UCI conversion) already exists in the codebase from Phase 151.1/153/158. This phase is pure wiring/precedence work.

## Common Pitfalls

### Pitfall 1: Two call sites bypass `evalLookup` entirely, and CONTEXT.md's canonical_refs describes both as needing no change
**What goes wrong:** `Analysis.tsx:1881` passes `stockfishLine={engine.pvLines[0] ?? null}` directly to `FlawChessAgreementVerdict` — never through `evalLookup`/`getByUci`. `useGameOverlay.ts`'s `enginePassthrough.evalCp/evalMate/evalDepth` (lines 178-186, 322-324) reads `engineEvalCp`/`engineEvalMate`/`engineDepth` params directly — also never through the lookup. Under the OLD (free-run-first) precedence, `getByUci(evalLookup, engine.pvLines[0].moves[0])` was **always identical** to `engine.pvLines[0]` itself (free-run wins on any overlap, and the free run inserted its own entry first), so bypassing the lookup was a no-op difference and nobody noticed. Confirmed via the existing test at `pages/__tests__/Analysis.test.tsx:443-469`, which exercises a scenario where the grading run grades a DIFFERENT move (`e4`, cp 40) than the one the verdict's assertions check (`g1f3`, cp 130, asserted via `+1.3` in the rendered sentence) — it never actually tests the case where the SAME move is graded differently by both sources, so this equivalence-under-old-precedence was never falsified.
**Why it happens:** Phase 158's own CONTEXT.md states "Verdict consumes the lookup (LOCKED)" and "The agreement verdict's FC-pick and SF-best evals both come from the lookup" — that was the INTENT, but the FC-pick side (`reconciledRankedLines[0]`) does correctly route through the lookup while the SF side does not; the gap was invisible under free-run-first precedence.
**How to avoid:** Treat both call sites as in-scope for this phase, not "unchanged wiring." Recommended fix for the verdict: construct the `stockfishLine` PvLine from the resolved-reconciled-best UCI + its `evalLookup` eval (see Open Questions for the "which move" ambiguity) rather than literally re-using `engine.pvLines[0]`'s object. For `useGameOverlay.ts`: thread the reconciled-best eval into the `engineEvalCp`/`engineEvalMate`/`engineDepth` params the caller passes in (Analysis.tsx already computes these once for the eval bar per D-08 — reuse the same derived value), rather than the raw `engine.evalCp`/`engine.evalMate`/`engine.depth`.
**Warning signs:** A UAT scenario where the FC card and chart show a reconciled/upgraded number for a move, but the agreement verdict prose or the off-main-line eval bar still shows the stale free-run number for that same move — i.e. exactly the class of bug this phase exists to close, reintroduced through an unguarded call site.

### Pitfall 2: The Stockfish card's "line 1" and the global reconciled argmax are not guaranteed to be the same move
**What goes wrong:** `EngineLines` (the Stockfish card) is hard-capped at `MAX_LINES = 2` and only ever displays `engine.pvLines` — the free run's own 2 candidates. D-02 ensures those 2 candidates are always IN the grading union (so their numbers become correct/consistent wherever else they're shown), but does not guarantee the grading run's true argmax IS one of those 2 candidates — the union also includes Maia-only and FlawChess-only candidates the free run's shallow MultiPV=2 search never considered (this is precisely the `exd6`-not-in-SF's-top-2 scenario the seed's diagnosis describes). If D-07's arrow is wired to literally the same reconciled-argmax UCI used for the chart's "Best" crown, the arrow can point to a move the Stockfish card itself never displays.
**Why it happens:** SEED-090 explicitly forbids widening the Stockfish card past 2 lines / bumping its MultiPV (no depth regression), so there is a structural ceiling on what the card can ever show, independent of how good the reconciliation gets.
**How to avoid:** This is a scope/design decision the plan must make explicitly, not an implementation bug to "fix." See Open Questions for the two viable resolutions.
**Warning signs:** UAT where the green best-move arrow points to a square not among either of the Stockfish card's two displayed moves — confirm this is the accepted/understood behavior (documented in the plan) rather than a surprise.

### Pitfall 3: `classifyMoveQuality`'s reconciled-grade-map keyspace is `grading.gradeMap.keys()`, not the full union
**What goes wrong:** `qualityBySan` (`Analysis.tsx:861-867`) builds its `reconciledGradeMap` by iterating `grading.gradeMap.keys()` — i.e., only SANs the grading run has actually streamed a grade for so far, which starts empty on every fresh position and fills progressively. If the new `resolveReconciledBest` helper (or any new Best-derivation logic) is fed a *different* candidate set (e.g. the full `unionSans` regardless of grading progress), it can disagree with `qualityBySan`'s own internal argmax during the pre-grading/streaming window, producing a transient inconsistency between the chart's Best crown and (e.g.) the arrow.
**Why it happens:** This is intentional progressive-fill behavior from Phase 151.1/158 (D-05), not a bug — but it means "the reconciled union" is a moving target during the ~few-hundred-ms-to-4s grading window, not a fixed set.
**How to avoid:** Feed every Best-derivation consumer the SAME keyspace — either always `grading.gradeMap.keys()` (recommended: matches `qualityBySan`'s existing behavior, keeps pre-grading/streaming states self-consistent by construction) or explicitly document why a consumer needs a different set.
**Warning signs:** The chart shows one move as "Best" while the arrow points to a different move during the first ~1-2 seconds after navigating to a new position (before grading has caught up).

### Pitfall 4: `MultiPV` index vs. move identity (carried forward from Phase 151.1/158, still applies)
**What goes wrong:** Keying any new grading-map consumer by `parsed.multipv` instead of `pv[0]`'s resolved SAN/UCI silently breaks — `multipv` is an eval RANK that reorders as depth climbs, not a stable move identity.
**Why it happens:** UCI's `info ... multipv N ... pv <move> ...` reports N as "this move is currently ranked Nth," which can change between `info` lines for the same physical move as the search deepens.
**How to avoid:** `useStockfishGradingEngine.ts` already keys its cache by `pv[0]`'s resolved SAN (confirmed, `sanFromUci` + `cache.set(san, ...)`) — nothing in this phase needs to touch that. Any NEW code this phase adds must follow the same convention if it ever reads a raw `info` line (unlikely — this phase mostly consumes already-resolved `gradeMap`/`pvLines`, not raw UCI text).
**Warning signs:** N/A for this phase's actual diff — flagged for completeness since the caveat is explicitly called out in the canonical refs.

## Code Examples

### Current precedence (BEFORE — free-run-first, to be flipped)
```typescript
// Source: frontend/src/lib/engineEvalLookup.ts:40-60 (current, Phase 158)
export function buildEvalLookup(
  pvLines: PvLine[],
  gradeMapBySan: Map<string, MoveGrade>,
  baseFen: string,
): Map<string, MoveGrade> {
  const lookup = new Map<string, MoveGrade>();

  for (const line of pvLines) {                    // free run inserted FIRST
    const uci = line.moves[0];
    if (uci === undefined || lookup.has(uci)) continue;
    lookup.set(uci, { evalCp: line.evalCp, evalMate: line.evalMate, depth: line.depth });
  }

  for (const [san, grade] of gradeMapBySan) {       // grading run fills GAPS only
    const uci = sanToUci(baseFen, san);
    if (uci === null || lookup.has(uci)) continue;
    lookup.set(uci, grade);
  }

  return lookup;
}
```
D-01's flip: swap the two loop bodies (grading loop first, unconditional overwrite is unnecessary — insertion order + `!lookup.has()` guard already gives "first-inserted wins," so simply reordering the loops achieves grading-first precedence with the SAME guard logic). The module docstring (lines 1-23) must be rewritten — it currently states free-run-first as LOCKED in three places.

### Current `qualityBySan` pin (BEFORE — passes free-run `bestSan`)
```typescript
// Source: frontend/src/pages/Analysis.tsx:869-871 (current)
// Pass the primary engine's bestSan so the chart's "best" agrees with the
// eval bar + engine card (151.1 UAT: reconcile the two Stockfish sources).
const infoBySan = classifyMoveQuality(reconciledGradeMap, sideToMoveFromFen(position), bestSan);
```
D-03's fix: replace the third argument with the SAN form of the new `resolveReconciledBest(...)` result (computed over `reconciledGradeMap`'s own keyspace per Pitfall 3, tie-break toward `bestSan`) — NOT `null`, since `classifyMoveQuality` already has a "fall back to own top scorer" path that lacks a tie-break toward the free-run pick, and D-03 explicitly requires the tie-break.

### `classifyMoveQuality`'s existing pin-honoring path (UNCHANGED — reused, not modified)
```typescript
// Source: frontend/src/lib/moveQuality.ts:90-94 (current — no change needed here)
const useDesignated = designatedBestSan != null && scores.has(designatedBestSan);
const bestSan = useDesignated ? designatedBestSan : topSan;
const bestEs = useDesignated ? scores.get(designatedBestSan)! : topEs;
```
This function's contract already matches D-03's requirement exactly once the CALLER passes a reconciled-argmax-derived pin instead of the free-run pin — confirming the "Claude's Discretion" note that the argmax logic can live in a new small pure helper rather than inside `classifyMoveQuality` itself.

### Test fixture pattern to invert (existing, `engineEvalLookup.test.ts`)
```typescript
// Source: frontend/src/lib/engineEvalLookup.test.ts:29-37 (current — assertion to invert)
it('a move present in BOTH pvLines and gradeMap resolves to the free-run value', () => {
  const pvLines = [pvLine('e2e4', 30, null, 20)];
  const gradeMapBySan = new Map<string, MoveGrade>([['e4', grade(999, null, 5)]]);
  const lookup = buildEvalLookup(pvLines, gradeMapBySan, START_FEN);
  expect(getByUci(lookup, 'e2e4')).toEqual({ evalCp: 30, evalMate: null, depth: 20 }); // → must become 999-based after flip
});
```
Every test in this file's two `describe` blocks ("free-run-first precedence" and "gradeMap-only moves") needs updating: the precedence-overlap test's expected value flips from the `pvLine` value to the `grade` value, and the block/test titles should be renamed to describe grading-first precedence (mirrors the seed's mandatory unit test 1).

## State of the Art

| Old Approach (Phase 158, locked "free run first") | New Approach (Phase 162, this phase) | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `buildEvalLookup`: free run wins on overlap, grading fills gaps | `buildEvalLookup`: grading wins on overlap, free run fills gaps (pre-arrival placeholder only) | This phase (SEED-090, supersedes SEED-089's alternative "unified pass" redesign) | Progressive refinement direction inverts: a move's displayed number can now only get MORE accurate (deeper search), never regress |
| `qualityBySan`'s Best label pinned to free-run `bestSan` | Best label = argmax over reconciled evals, tie-break toward `bestSan` | This phase | Closes the "mirror-image" bug class where the free-run pin could label a lower-eval move "Best" |
| `unionSans` = Maia mass-set ∪ playedSan ∪ bestSan ∪ FC top-2 | Same, **+ free-run's own top-2** (gated on free-run bestmove commit, D-09) | This phase | Guarantees the grading union covers every move the Stockfish card itself displays — the structural fix that makes "no uncovered displayed move" true by construction |

**Deprecated/outdated:**
- The Phase 158 module docstring's "free-run-first... LOCKED" framing in `engineEvalLookup.ts` — must be rewritten to cite this phase, not merely have its behavior changed underneath a stale comment.
- SEED-089's "one high-MultiPV pass + gap-only searchmoves fallback" design — explicitly superseded, its two load-bearing claims (uncovered moves can't be labeled Good; zero extra Stockfish calls in the common case) were falsified during the 2026-07-10 critical review. Kept only as a possible future fallback if the two-worker CPU/battery cost becomes a real complaint.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The verdict's `stockfishLine` should be re-sourced to the reconciled-argmax UCI (not merely re-eval'd at the SAME free-run move) — reading D-11's explicit inclusion of "verdict" among display consumers that "switch to the reconciled source." | Pitfall 1 / Open Questions | If wrong (intent was only "re-eval the same move"), the smaller fix (route `engine.pvLines[0]`'s move through `evalLookup` for its eval only) suffices and is much lower risk — plan should pick one explicitly rather than leave ambiguous |
| A2 | `engine.pvLines.length > 0 && !engine.isAnalyzing` reliably signals "free run has committed a bestmove for the CURRENT fen" with no `useStockfishEngine.ts` changes needed for D-09. | Architecture Patterns — "free-run bestmove committed signal" | If wrong (e.g. a race where `isAnalyzing` is transiently false between fen-change and debounce-fire while stale `pvLines` from a PRIOR fen haven't been cleared yet), the union could pull in a stale move; verified against the code: `setPvLines([])` runs synchronously in the same effect that later sets `debouncedFen`, so this race does not appear to exist, but it should be exercised by a test |
| A3 | `resolveReconciledBest`'s candidate keyspace should match `qualityBySan`'s existing `grading.gradeMap.keys()` scope (Pitfall 3), not the broader `unionSans`. | Pitfall 3 | If wrong, a brief inconsistency window during progressive grading could appear between the chart crown and the arrow/verdict during the first 1-2s after navigation — likely acceptable per D-10's "near-tie flips accepted" stance either way, but worth an explicit plan decision |

## Open Questions (RESOLVED)

> All three questions are resolved. Q1 and Q2 were put to the user on 2026-07-10 and locked as CONTEXT.md Amendment decisions **D-12** (true global reconciled argmax — option (a) of Q1) and **D-13** (verdict re-sourced to the reconciled-argmax move — full swap of Q2). Q3 was self-answering (1-line substitution, no restructuring). The plans (162-01..03) implement these resolutions.

1. **(RESOLVED → D-12)** **Does the Stockfish card's re-sorted "line 1" need to literally equal the global reconciled argmax (arrow/chart/verdict target), or is it acceptable for the card to show only its own free-run top-2 (values corrected, but potentially NOT including the true global best)?**
   - What we know: D-07 states the arrow "follows... the same source as the card's re-sorted line 1"; the card is structurally capped at 2 lines (`MULTIPV = 2`, explicitly not to be widened this phase).
   - What's unclear: whether the global reconciled argmax is guaranteed to be one of the free run's own top-2 candidates. It is NOT guaranteed in general — the grading union includes Maia-only/FC-only candidates the free run's shallow MultiPV=2 search may never surface.
   - Recommendation: the plan should pick one of two resolutions and document it: **(a)** the arrow/chart/verdict use the TRUE global reconciled argmax (may occasionally diverge from the card's own line-1 — accept this as a residual, documented edge case, same trade-off class as the seed's other accepted trade-offs), or **(b)** scope the arrow specifically to argmax-over-{free-run's-own-2-candidates} so it always agrees with the card (weaker fix, doesn't fully close the `exd6` scenario for the arrow, only for the label/chart/verdict). Option (a) is the more faithful reading of D-03's "argmax over reconciled displayed evals" and D-11's inclusion of "arrow" among reconciled-source consumers; option (b) is the safer, smaller diff. Surface this explicitly in the plan's decisions rather than resolving it implicitly.

2. **(RESOLVED → D-13)** **Should `FlawChessAgreementVerdict`'s `stockfishLine` swap to a different MOVE (the reconciled argmax), or only get its EVAL corrected for the SAME free-run move?**
   - What we know: D-11 explicitly lists "verdict" among the consumers that "switch to the reconciled source" (not just "get a corrected number for the same move"). The verdict's `computeFlawChessVerdict` compares FlawChess's practical pick against "Stockfish's objective #1 pick" — changing which move that represents is a bigger semantic shift than a value swap.
   - What's unclear: whether the discuss session intended the FULL swap (verdict's SF side = reconciled global argmax, potentially a different move than `engine.pvLines[0]`) or just wanted the number displayed for `engine.pvLines[0]`'s move to stop lying once grading disagrees with the free run.
   - Recommendation: given D-11's explicit wording and the module docstring's own framing ("Stockfish's TRUE objective #1 pick" — "true objective best" is a stronger claim than "the free run's shallow guess"), lean toward the full swap (Assumption A1), but this should be an explicit plan decision, potentially worth a quick confirm with the user given it changes verdict semantics (which move gets called "Stockfish's pick" in the prose) — not merely a display-value bugfix.

3. **(RESOLVED — no further research needed)** **`ARROW_COUNT = 1` (`Analysis.tsx:161`) — does the single Stockfish arrow definitely map to the reconciled-best UCI, or does `engineArrows`'s loop (currently `engine.pvLines[i]?.moves[0]`) need restructuring beyond a 1-line swap?**
   - What we know: `ARROW_COUNT = 1` means only ONE Stockfish arrow is ever drawn (line 1291-1303's `for` loop only runs once, `i=0`). This simplifies D-07 to a single value substitution: swap `engine.pvLines[0]?.moves[0]` for the reconciled-best UCI in that one spot.
   - What's unclear: nothing structurally — this is a straightforward 1-line change once Open Question 1 is resolved (which UCI to substitute).
   - Recommendation: no further research needed; flagged only so the plan doesn't over-scope this into a bigger refactor of `engineArrows`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest ^4.1.7 |
| Config file | `frontend/vite.config.ts` (vitest config colocated with Vite config, project convention) |
| Quick run command | `cd frontend && npx vitest run src/lib/engineEvalLookup.test.ts src/lib/__tests__/moveQuality.test.ts` |
| Full suite command | `cd frontend && npm test -- --run` |

### Phase Requirements → Test Map

No `.planning/REQUIREMENTS.md` exists for this project (confirmed: file not found) and no phase requirement IDs were mapped for Phase 162 ("TBD (none mapped)"). Test coverage is instead derived directly from SEED-090's verification sketch and this research's pitfalls:

| Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------|
| `buildEvalLookup` grading-wins-on-overlap, free-run-fills-gaps (D-01, mandatory per seed) | unit | `npx vitest run src/lib/engineEvalLookup.test.ts` | ✅ existing file, needs inverted assertions |
| Mirror-image Best-label case: grading map where a non-`bestSan` move has the top reconciled eval → it gets `best`, `bestSan` gets `good` (D-03, mandatory per seed) | unit | `npx vitest run src/lib/__tests__/moveQuality.test.ts` (new test) or a new `resolveReconciledBest`-specific test file | ❌ Wave 0 — new test case, and possibly a new test file if the helper lands in a new module |
| `unionSans` extension only fires after free-run bestmove commits (D-09) | unit/integration | `npx vitest run src/pages/__tests__/Analysis.test.tsx` (extend the existing "Grading run gating" describe block) | ✅ existing file, needs new test case(s) |
| Verdict's Stockfish-side eval is lookup-derived, not raw `engine.pvLines[0]` passthrough (Pitfall 1) | integration | `npx vitest run src/pages/__tests__/Analysis.test.tsx` (extend "Reconciled eval provenance" describe block with a case where the SAME move is graded to a DIFFERENT value by the two sources) | ✅ existing file — the CURRENT test at line 443 does not exercise this scenario (see Pitfall 1), must be extended |
| Eval bar / headline refines once to reconciled best's eval when grading lands, off game main-line (D-08, `useGameOverlay.ts` passthrough) | unit | New/extended test in `frontend/src/hooks/__tests__/useGameOverlay.test.ts` | ❓ verify existing file's coverage during planning |
| Board arrow (D-07) targets the reconciled-argmax UCI | integration | `Analysis.test.tsx` — assert `engineArrows`'s output via existing test patterns (check how prior phases tested `engineArrows`, e.g. Phase 156/157 plans) | ❓ verify existing coverage during planning |

### Sampling Rate
- **Per task commit:** the quick run command above (targeted files) — sub-second, run after every task per project's `-x` convention for local dev.
- **Per wave merge:** `cd frontend && npm test -- --run` (full frontend suite) plus `npx tsc -b` (per `feedback_frontend_run_tsc_build` — `npm test`/`npm run lint` do NOT type-check since esbuild strips types).
- **Phase gate:** full frontend suite green + `npx tsc -b` clean before `/gsd-verify-work`. This phase touches only frontend, so the backend pytest suite is not implicated, but the CLAUDE.md pre-merge gate still requires running it if the squash-merge integrates "real work" — confirm with the user whether a frontend-only diff still warrants the full backend gate run (likely yes per the CLAUDE.md gate being mandatory pre-merge regardless of which stack changed, since it's a repo-wide gate, not per-stack).

### Wave 0 Gaps
- [ ] `src/lib/engineEvalLookup.test.ts` — invert the 2 precedence-overlap assertions (currently expect free-run values, must expect grading values post-flip); rename `describe` blocks from "free-run-first" to "grading-first precedence."
- [ ] New test(s) for the `resolveReconciledBest` helper (or wherever the argmax/tie-break logic lands) — the seed's mandatory "mirror-image Best-label case."
- [ ] `src/pages/__tests__/Analysis.test.tsx` — extend "Grading run gating" for D-09's bestmove-commit gate on the union extension; extend "Reconciled eval provenance" so the verdict-eval-provenance test actually exercises a same-move-different-value scenario across the two sources (closes the coverage gap identified in Pitfall 1).
- [ ] Verify `src/hooks/__tests__/useGameOverlay.test.ts`'s existing coverage of the `enginePassthrough` branch during planning — it may need a new case once the passthrough's eval source changes (D-08).
- No new test framework/config install needed — vitest is already fully configured for this codebase.

## Security Domain

`security_enforcement` is not disabled in `.planning/config.json` (absent under `workflow`, treated as enabled per the standing rule), but this phase has essentially no attack surface: it changes precedence/derivation logic over numbers already computed locally in-browser from a locally-run WASM engine, with no new user input parsing, no new network calls, no new auth/session logic, and no new rendering of untrusted strings (all move labels are already-validated SAN/UCI strings produced by `chess.js` from the engine's own output, unchanged by this phase — the existing `EngineLines.tsx` docstring already notes "All engine strings are rendered as React children (auto-escaped, T-137-03 mitigated)," which continues to hold since no new raw-string rendering path is introduced).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Phase touches no auth code |
| V3 Session Management | No | Phase touches no session/cookie code |
| V4 Access Control | No | No new endpoints/routes; `/analysis` route's existing access rules are unchanged |
| V5 Input Validation | N/A (no new external input) | All data this phase reads is engine output already flowing through existing validated paths (`chess.js` `Chess.move()` construction, `sanToUci`/`uciToSan`) |
| V6 Cryptography | No | Not applicable |

### Known Threat Patterns for this stack
None applicable — this phase introduces no new trust boundary, no new user-controllable input, and no new rendering of unescaped strings. The change is confined to which of two already-trusted, already-validated local computation sources wins precedence in an existing display pipeline.

## Sources

### Primary (HIGH confidence)
- Direct code reads (this session, 2026-07-10) of every file listed in CONTEXT.md's canonical_refs Code touchpoints: `frontend/src/lib/engineEvalLookup.ts`, `frontend/src/hooks/useStockfishGradingEngine.ts`, `frontend/src/hooks/useStockfishEngine.ts`, `frontend/src/lib/moveQuality.ts`, `frontend/src/lib/liveFlaw.ts`, `frontend/src/lib/flawChessVerdict.ts`, `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx`, `frontend/src/components/analysis/EngineLines.tsx`, `frontend/src/pages/Analysis.tsx` (relevant sections: 700-900, 990-1100, 1260-1520, 1828-1960, 2230-2300).
- Additional file read beyond CONTEXT.md's list, surfaced as load-bearing during research: `frontend/src/hooks/useGameOverlay.ts` (full file) — confirmed as an unguarded raw-`engine.evalCp`/`evalMate`/`depth` passthrough not routed through `evalLookup`.
- `.planning/seeds/SEED-090-grading-run-authoritative-eval-precedence-flip.md` — the design doc.
- `.planning/seeds/SEED-089-unify-analysis-stockfish-eval-source.md` — referenced for the superseded diagnosis (not separately re-read this session; already fully summarized within SEED-090's "Relationship to SEED-089" section).
- `.planning/milestones/v2.0-phases/158-flawchess-engine-displayed-eval-provenance-reconciliation-se/158-CONTEXT.md` — the architecture this phase amends.
- Existing test files (confirmed test conventions and current coverage gaps): `frontend/src/lib/engineEvalLookup.test.ts`, `frontend/src/lib/__tests__/moveQuality.test.ts`, `frontend/src/pages/__tests__/Analysis.test.tsx`.
- `.planning/config.json` — confirmed `nyquist_validation: true`, no `security_enforcement: false`.

### Secondary (MEDIUM confidence)
- None — this phase required no external documentation lookup (no new library, no API, no framework version question). All research was direct codebase investigation.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no new dependencies
- Architecture: HIGH — full read of every touched file plus one additional load-bearing file (`useGameOverlay.ts`) not listed in CONTEXT.md; precedence-flip mechanism, union-extension mechanism, and every display consumer's current wiring were traced directly in code, not inferred
- Pitfalls: HIGH — Pitfall 1 (evalLookup-bypass at two call sites) was discovered and confirmed via direct code read plus cross-reference against an existing test's actual assertions (`Analysis.test.tsx:443-469`), not speculation

**Research date:** 2026-07-10
**Valid until:** Effectively unbounded for the underlying code structure (internal refactor, no external API/library version drift risk) — but re-verify against HEAD if this phase is planned significantly later than researched, since `Analysis.tsx` and its siblings are under very active development (multiple quick-tasks per week per STATE.md's Quick Tasks Completed log).
