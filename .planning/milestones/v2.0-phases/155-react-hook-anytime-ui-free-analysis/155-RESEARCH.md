# Phase 155: React Hook + Anytime UI (Free Analysis) - Research

**Researched:** 2026-07-06
**Domain:** React hook wiring a client-side search-core (frozen `SearchRunner` contract) into a live-refining analysis UI; frontend-only, no new dependencies
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Surface placement (DISPLAY-04)**
- D-01 New card, left column, above Maia: A new `FlawChessEngineLines` card is stacked **above** the existing "Maia — Human Move Probability" card in the **left** column of `/analysis` (the same column the Maia card occupies today). Not merged into the Stockfish card. Apply to both desktop and the mobile takeover layout.

**Activation + toggles (DISPLAY-01)**
- D-02 On by default everywhere: The FlawChess Engine runs by default on every position (desktop and mobile). The 2–4 SF pool + Maia queue lazy-spawn on first search (Phase 154 D-02). Accepted risk: runs concurrently with the existing eval-bar/grading/Maia-chart workers before the SC4 real-device mobile-memory UAT. **SC4 (deferred from Phase 154) is the gate** — if mobile Safari can't hold it, a device-adaptive default (on desktop/off mobile) is the fallback, decided post-UAT.
- D-03 Toggle switch in all 3 card headers: Each engine card (Stockfish, Maia, FlawChess) gets its own on/off **toggle switch** in its header. The existing Stockfish header on/off control (`engineEnabled`, currently a header click) is upgraded to a proper switch for consistency. All three default ON.

**Eval bars — shared left slot, no third bar (POOL-04 / Phase 154 D-03)**
- D-04 Two board-flanking bars, left slot shared by precedence: No third eval bar.
  - **Left slot** (today the Maia violet bar): shows **FC** (brown, label "FC") when the FlawChess Engine is enabled; falls back to **Maia** (violet, "Maia") when only Maia is on. FC takes precedence over Maia when both are enabled. The FC bar shows the engine's **practical-for-you** expected score (converted to a white-POV fraction).
  - **Right slot**: stays **Stockfish** (blue, "SF"). While the FlawChess Engine runs, the SF bar is fed the engine's **objective root eval** (`RankedLine.objectiveEvalCp` of the top line) — no separate standalone `useStockfishEngine` search on that position (this IS the Phase 154 D-03 handoff; because the engine is on by default, the handoff is effectively permanent while FC is on). Same scale/label ("SF").

**Branding / color (Phase 155 chrome only)**
- D-05 Brown accent + subtle gold headline, no card glow: Add `FLAWCHESS_ENGINE_ACCENT` (brand brown) to `theme.ts`, alongside `STOCKFISH_ACCENT` (blue), `MAIA_ACCENT` (violet). Tints the card frame + header caption + "FC" eval-bar fill/cap. Subtle bronze/gold reserved for the headline practical score number only — NOT a card-wide glow. Board-arrow color is a Phase 156 decision.

**Score-pair display (DISPLAY-02, DISPLAY-03)**
- D-06 Both numbers on the pawn scale, white POV: Each line's badge shows objective and practical scores both on the pawn scale (e.g. `+3.0` / `+0.9`), both white-POV. The practical 0–1 expected score (`RankedLine.practicalScore`, root-STM) is converted to a white-POV pawn-equivalent via the inverse of the project's existing WDL/sigmoid util. Color-code: blue-tinted objective, brown/gold practical. Copy nuance: numbers are white-POV, so framing must not read "+0.9 for you" literally. **Never** render "best move" unqualified.
- D-07 Modal path = SAN, ~5 plies + expand: Each line renders `RankedLine.modalPath` (UCI → SAN at the boundary) as clickable chips, first ~5 plies with expand chevron — mirroring `MAX_PLIES = 5`. Walk the path from already-expanded tree nodes (may be short early in the search).

**Anytime display (DISPLAY-01)**
- D-08 Top 3 lines: The card shows the top **3** ranked practical lines. More breadth than the Stockfish card's 2; Phase 156 arrows stay top-2.
- D-09 Live-refine cadence: Lines appear immediately from the first `onSnapshot` and reorder/update at a fixed batched cadence mirroring `RAPID_STEP_DEBOUNCE_MS` (150ms). First-paint uses a fixed-height skeleton (reuse `EngineLinesSkeleton`).
- D-10 Clickable graft-to-tree: line move chips are clickable, graft as a sideline — the exact same `onMoveClick(uciMoves)` interaction (+ hover miniboard) as `EngineLines`.

### Claude's Discretion
- **Grading-worker binding under the 3-toggle split:** decide what `useStockfishGradingEngine` binds to (likely the Maia card toggle, since it colors the Maia chart — confirm).
- **Maia card toggle vs the engine's internal Maia:** the Maia card toggle disables the Maia **chart** worker (`useMaiaEngine`) only; the engine's internal `maiaQueue` (Phase 154) must keep running when FlawChess is on regardless of the Maia card toggle.
- **The `useFlawChessEngine` hook shape:** trigger/debounce on position change, budget construction (`SearchBudget` — maxNodes/plies/concurrency/elo), abort-on-navigation (reuse Phase 154 lifecycle/abort surface), and the "engine active" signal driving the eval-bar handoff.
- **ELO source for `budget.elo.{w,b}`:** reuse `useMaiaEloDefault`/`selectedElo` (per-side ELO for the practical model).
- **Exact "FC"/"SF"/"Maia" bar cap labels and toggle persistence** (per-session vs persisted) — implementation detail.

### Deferred Ideas (OUT OF SCOPE)
- Board arrows + the high-contrast FlawChess arrow color — Phase 156 (ARROW-01..04). Brown-on-brown saliency is the real constraint there.
- Game-review overlay integration ("what you played vs practically best") — Phase 157 (REVIEW-01..02).
- Device-adaptive default (on desktop/off mobile) — held as the SC4 fallback if the on-by-default mobile-memory UAT fails; not built unless needed.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISPLAY-01 | Engine emits results anytime — quick top-n lines appear immediately, refine live as the search accumulates visits | `mctsSearch.ts`'s `onSnapshot` fires after every completed backup (see Architecture Patterns §1); hook must throttle these into React state at ~150ms cadence, not debounce them (see Common Pitfalls §3) |
| DISPLAY-02 | Each candidate line displays its modal path (player's move + opponent's most-likely replies) | `RankedLine.modalPath` is already computed (`treeCommon.ts:buildModalPath`, most-visited-child walk); render via `EngineLines.tsx`'s `replayPvLine()` UCI→SAN convention (see Code Examples §2) |
| DISPLAY-03 | Each ranked move displays objective-vs-practical score pair | `RankedLine.objectiveEvalCp` (already white-POV, nullable) is the objective number; `RankedLine.practicalScore` (0-1, root-STM) needs a NEW inverse-sigmoid conversion to white-POV cp before reusing `formatScore()` — full derivation in Code Examples §1 |
| DISPLAY-04 | Engine surfaces on the free-analysis `/analysis` board | `Analysis.tsx`'s existing 3-column/mobile-tab layout + `engineEnabled`/`EvalBar` precedent is the integration point (see Architecture Patterns §4-5) |
</phase_requirements>

## Summary

This phase has almost no new "domain" to research — the algorithmic core (Phase 153) and the real Stockfish-pool/Maia-queue providers (Phase 154) are both frozen and complete. The work is entirely **wiring**: build one React hook (`useFlawChessEngine`) that drives the frozen `SearchRunner` function (`mctsSearch`) against the real providers (`createWorkerPool()` + `createMaiaQueue()`), and one display component (`FlawChessEngineLines.tsx`) that is a structural sibling of the already-shipped `EngineLines.tsx`. Every piece of the frozen contract (`types.ts`, `guardrail.ts`) was read this session and is documented in full below with exact field shapes — the planner should not need to re-read those files to write tasks.

The single highest-value finding from this research is an **architecture gap that isn't mentioned in CONTEXT.md or the UI-SPEC**: `mctsSearch`'s `AbortSignal` only stops the orchestrator's own outer loop between rounds — it is never forwarded into the `dispatchExpansion()` calls to `providers.policy()`/`providers.grade()`. Aborting a search when the user navigates to a new position does **not** cancel in-flight Stockfish/Maia work; the pool workers keep grinding (up to their own 2.5s safety cap) unless the hook separately calls `pool.stopAll()`. Given DISPLAY-01's success criterion demands lines appear "almost immediately" on every navigation, and D-09 requires a 150ms live-refine cadence, this is load-bearing: a hook that only calls `AbortController.abort()` without also calling `pool.stopAll()` will queue new searches behind stale in-flight grading work and visibly violate both success criteria on rapid navigation. See Common Pitfalls §1 and Code Examples §3 for the exact fix.

The second load-bearing gap is the **ELO-pair mismatch**: `SearchBudget.elo` requires `{w: number, b: number}` (Phase 153's asymmetric self+opponent rating, ENGINE-04 — the engine's core differentiator), but the page's only existing ELO plumbing (`useMaiaEloDefault`) produces a single `selectedElo` number with no fixed per-color "user" vs "opponent" concept in free-play mode (there is no `gameData.user_color` outside game review). CONTEXT.md's discretion note ("reuse the existing … plumbing (per-side ELO for the practical model)") does not resolve *how* one number becomes two. This research recommends `budget.elo = { w: selectedElo, b: selectedElo }` for this phase's free-analysis-only scope — true self/opponent asymmetry only becomes meaningful once Phase 157 wires in `gameData.user_color`. See Open Questions §2.

The third gap worth flagging early: the UI-SPEC's toggle-binding note says the Stockfish switch "keeps gating `useStockfishEngine` … exactly as `engineEnabled` does today," independently of the new FlawChess switch. Read literally, with all three switches defaulting ON (D-02/D-03), `useStockfishEngine`'s own worker and the FlawChess Engine's `workerPool` would run **concurrently on the same position** — which is the exact scenario POOL-04's already-completed success criterion #4 (Phase 154) explicitly prohibits ("the pool never runs concurrently with the standalone `useStockfishEngine` eval bar on the same position"). Phase 154's own D-03 flagged the *actual* gating wire as "the researcher's job" in 155. This research recommends gating `useStockfishEngine`'s `enabled` input on `stockfishToggleOn && !flawChessEngineActive`, which preserves the switch's independent ON/OFF *state* while still honoring the POOL-04 mutual-exclusion contract underneath. See Open Questions §1.

**Primary recommendation:** Build `useFlawChessEngine` as a single `useEffect`-owned pair of long-lived `WorkerPool`/`MaiaQueue` instances (created only while the FlawChess switch is ON, mirroring `useStockfishEngine`'s enabled-gated Worker lifecycle exactly), drive `mctsSearch` per debounced-FEN navigation with a fresh `AbortController` each time (calling `pool.stopAll()` alongside every abort), and throttle `onSnapshot` into React state at a fixed ~150ms cadence using the same "settled fires immediately, rapid succession coalesces" adaptive pattern already proven in `useStockfishEngine`/`useMaiaEngine` — just applied to snapshot commits instead of FEN debounce.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Search orchestration (`mctsSearch`) | Browser / Client (Web Worker-adjacent, but the orchestrator itself runs on the main thread) | — | Pure client-side per D-4 (v1.29) and the v2.0 milestone's "zero server load" constraint; no backend involvement at all |
| Stockfish grading (`workerPool.ts`) | Browser / Client (Web Worker) | — | Already-shipped Phase 154 module; Phase 155 only calls it |
| Maia policy (`maiaQueue.ts`) | Browser / Client (Web Worker) | — | Already-shipped Phase 154 module; Phase 155 only calls it |
| React hook lifecycle (`useFlawChessEngine`) | Browser / Client (React) | — | New this phase; owns AbortController + pool/queue instance lifetime |
| Score-pair conversion (practicalScore → white-POV cp) | Browser / Client (pure function, `lib/`) | — | New this phase; must live in `frontend/src/lib/` (or extend `liveFlaw.ts`), not inline in a component, so it's independently testable |
| Card rendering (`FlawChessEngineLines.tsx`) | Browser / Client (React) | — | New this phase; sibling of `EngineLines.tsx` |
| Eval-bar precedence selection | Browser / Client (React, `Analysis.tsx`) | — | Page-level composition logic; no new component (reuses `EvalBar.tsx`) |
| Toggle state (3 switches) | Browser / Client (React, `Analysis.tsx`) | — | Local component state, non-persisted by default (Claude's Discretion) |

No Frontend-Server (SSR), API/Backend, or Database tier involvement anywhere in this phase — confirmed against `.planning/REQUIREMENTS.md`'s Out-of-Scope table ("Server-side search / browser↔server search loop" is explicitly excluded) and CLAUDE.md's v2.0 milestone description ("no backend, no schema, no migrations, no new endpoints").

## Standard Stack

### Core

No new external packages this phase (milestone-wide constraint: "no new npm dependencies," CLAUDE.md ROADMAP.md). Everything below is either already-vendored (Phase 136/151) or already a project dependency.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| `radix-ui` (consolidated package) | `^1.4.3` [VERIFIED: package.json] | Provides `Switch` primitive via `import { Switch as SwitchPrimitive } from 'radix-ui'` — confirmed present in `node_modules/radix-ui/dist/index.d.ts` (`export { reactSwitch as Switch }`) this session | Already a project dependency; every other `ui/` primitive (`checkbox.tsx`, `dialog.tsx`, `tooltip.tsx`, etc.) is a hand-rolled CVA wrapper around this exact package — the D-03 switch should follow the identical pattern, not a fresh shadcn pull |
| React 19 + TypeScript | project-pinned | Hook + component | Existing stack |
| `chess.js` | project-pinned | UCI→SAN replay for modal-path chips (`replayPvLine`) | Already used by `EngineLines.tsx` for the identical purpose |
| Vendored `stockfish-18-lite-single.js`/`.wasm` | Phase 136 vendored binary | Backing engine for `workerPool.ts` | Already shipped, reused verbatim (`ENGINE_PATH` constant in `workerPool.ts`) |
| Vendored `maia-worker.js` (onnxruntime-web) | Phase 151 vendored | Backing engine for `maiaQueue.ts` | Already shipped, reused verbatim |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lucide-react` | project-pinned | `ChevronDown` for the expand affordance, matching `EngineLines.tsx` | Reuse the identical import, no new icon needed |
| `class-variance-authority` | project-pinned | CVA styling for the new `switch.tsx` primitive | Matches every existing `ui/` component's styling convention |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled `switch.tsx` (recommended) | `npx shadcn add switch` (official registry pull) | UI-SPEC explicitly allows either; hand-rolling avoids re-theming a shadcn preset to match `radix-nova`'s neutral base and matches every other `ui/` primitive in this codebase, which are ALL hand-authored, not raw shadcn pulls |
| A dedicated throttle utility for `onSnapshot` batching | `useDebounce.ts` (existing) | `useDebounce` is a plain trailing debounce (fires only after quiet period) — wrong semantics for D-09's "batched cadence," which needs a THROTTLE (max update rate, fires immediately on a settled update, coalesces during a burst) — see Common Pitfalls §3. Recommend a small local throttle inline in the hook rather than a new shared utility, since no other caller needs this exact shape yet |

**Installation:** None — no new packages.

**Version verification:** `radix-ui@1.4.3` and its bundled `@radix-ui/react-switch` are already present in `frontend/node_modules` — confirmed via direct inspection of `node_modules/radix-ui/dist/index.d.ts` this session `[VERIFIED: node_modules inspection]`. No registry lookup needed since nothing new is being installed.

## Package Legitimacy Audit

**Not applicable this phase.** No new external packages are installed — `radix-ui`'s `Switch` export is already resolvable from the existing `radix-ui@^1.4.3` dependency (confirmed present in the installed `node_modules` tree this session), and everything else reuses already-vendored Phase 136/151/153/154 assets. If the planner instead chooses `npx shadcn add switch` (the UI-SPEC's non-default alternative), that pulls from the shadcn **official** registry only — the UI-SPEC itself already clears this ("not required … no vetting gate … official registry"). No `[SLOP]`/`[SUS]` packages to report.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ Analysis.tsx (React, main thread)                                   │
│                                                                       │
│  position (FEN) ──► useFlawChessEngine({ fen, enabled, elo })        │
│                            │                                          │
│                            │ 1. adaptive debounce (150ms, settled-vs- │
│                            │    rapid, mirrors useStockfishEngine)    │
│                            ▼                                          │
│                     new AbortController per debounced FEN            │
│                            │                                          │
│                            │ 2. on new FEN: controller.abort() +      │
│                            │    pool.stopAll() for the PREVIOUS run   │
│                            ▼                                          │
│                     mctsSearch(fen, budget, providers,                │
│                                onSnapshot, signal)  ◄── frozen         │
│                            │        ▲                SearchRunner     │
│                            │        │                type             │
│                            │        │ 3. onSnapshot fires after EVERY │
│                            │        │    completed backup — hook      │
│                            │        │    THROTTLES these into state   │
│                            │        │    at ~150ms (D-09), not a      │
│                            │        │    debounce                     │
│                            ▼        │                                 │
│                     EngineSnapshot { rankedLines, nodesEvaluated,      │
│                                      budgetExhausted }                 │
│                            │                                          │
│                            ▼                                          │
│                     FlawChessEngineLines.tsx                         │
│                       (top 3 RankedLine rows: score-pair badge         │
│                        + modal-path SAN chips + hover preview)         │
│                            │                                          │
│                            │ onMoveClick(uciMoves) ──► playUciLine()  │
│                            │                            (useAnalysisBoard)│
│                            ▼                                          │
│                     Eval-bar precedence swap (D-04):                  │
│                       left slot  = FC (brown) > Maia (violet)         │
│                       right slot = SF fed by RankedLine.objectiveEvalCp│
│                                     of top line while FC runs          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ providers.policy()/providers.grade()
                              ▼
        ┌─────────────────────────────────┐   ┌─────────────────────────────┐
        │ maiaQueue.ts (Phase 154)        │   │ workerPool.ts (Phase 154)   │
        │ createMaiaQueue()               │   │ createWorkerPool()          │
        │ 1 dedicated ONNX Web Worker,    │   │ 2-4 dedicated Stockfish.wasm │
        │ FIFO queue, lazy-spawn          │   │ Web Workers, priority queue, │
        │ (D-02), own (fen,elo) cache     │   │ lazy-spawn (D-02), own       │
        │                                 │   │ FEN-keyed cache              │
        └─────────────────────────────────┘   └─────────────────────────────┘
```

### The frozen contract (do NOT re-open — read once, cite forever)

`frontend/src/lib/engine/types.ts`:
```typescript
export type Side = 'w' | 'b';

export interface EngineProviders {
  policy(fen: string, elo: number, side: Side): Promise<Record<string, number>>;
  grade(fen: string, candidateUcis: string[]): Promise<Map<string, MoveGrade>>;
}

export interface SearchBudget {
  maxNodes: number;
  elo: { w: number; b: number };   // D-07: color-keyed, never self/opponent-keyed
  maxPlies: number;                // locked 6-10 ply band (SEED-082)
  concurrency: number;             // >= 1, in-flight expansion concurrency
  extraRootMoves?: string[];       // root-only, optional — leave unset this phase (see Open Questions)
}

export interface RankedLine {
  rootMove: string;                // UCI
  practicalScore: number;          // 0-1, ROOT-side-to-move expected score — NEVER per-ply
  objectiveEvalCp: number | null;  // white-POV cp, already sign-normalized
  modalPath: string[];             // UCI sequence, most-visited-child walk
  visits: number;
}

export interface EngineSnapshot {
  rankedLines: RankedLine[];       // pre-sorted descending by practicalScore, canonical UCI tie-break
  nodesEvaluated: number;
  budgetExhausted: boolean;
}
```

`frontend/src/lib/engine/guardrail.ts`:
```typescript
export type SearchRunner = (
  rootFen: string,
  budget: SearchBudget,
  providers: EngineProviders,
  onSnapshot: (snapshot: EngineSnapshot) => void,
  signal: AbortSignal,
) => Promise<EngineSnapshot>;
```

`mctsSearch` (from `frontend/src/lib/engine/mctsSearch.ts`) is the concrete `SearchRunner` implementation the hook should import — its own module docstring states plainly: *"`useFlawChessEngine.ts` (Phase 155) imports exactly one of them behind this single signature."* `fallbackExpectimax.ts` is the guardrail's swap-in backup (already proven in a Phase 153 test); **nothing in this phase's scope requires wiring an automatic runtime fallback** — no caller of either function exists yet anywhere in the codebase (`grep` confirmed zero non-test, non-docstring usages this session `[VERIFIED: codebase grep]`), so `mctsSearch` is a clean, unclaimed import.

### Pattern 1: Hook owns long-lived provider instances, gated by the `enabled` toggle (mirrors `useStockfishEngine`'s Worker-lifecycle effect)

**What:** `createWorkerPool()`/`createMaiaQueue()` each return a plain object (no Workers spawned yet — Phase 154 D-02's lazy-spawn happens on first `grade()`/`policy()` call). The hook should create these two objects in a `useEffect` gated on `enabled` (the FlawChess switch state), exactly like `useStockfishEngine`'s existing `useEffect(() => { if (!enabled) return; const worker = new Worker(...); ...; return () => worker.terminate(); }, [enabled])` pattern.

**When to use:** Every render where the FlawChess card's switch is ON.

**Example:**
```typescript
// Source: pattern extracted from useStockfishEngine.ts's Worker-lifecycle effect (lines 235-347),
// adapted to the pool/queue factories from workerPool.ts + maiaQueue.ts (Phase 154).
const poolRef = useRef<WorkerPool | null>(null);
const queueRef = useRef<MaiaQueue | null>(null);

useEffect(() => {
  if (!enabled) return;
  const pool = createWorkerPool();
  const queue = createMaiaQueue();
  poolRef.current = pool;
  queueRef.current = queue;
  return () => {
    pool.terminate();
    queue.terminate();
    poolRef.current = null;
    queueRef.current = null;
  };
}, [enabled]);
```

### Pattern 2: Adaptive debounce on FEN navigation, THEN abort-and-stopAll the previous run

**What:** Reuse the exact "settled fires immediately, rapid succession coalesces via `RAPID_STEP_DEBOUNCE_MS`" debounce already proven in `useStockfishEngine.ts` (lines 145-172) for navigation. On each debounced FEN, abort the previous `AbortController` **and** call `pool.stopAll()` — the signal alone does not free the pool (see Common Pitfalls §1).

**When to use:** Every FEN change while `enabled`.

**Example:**
```typescript
// Adapted from useStockfishEngine.ts's debouncedFen effect (lines 145-172).
const [debouncedFen, setDebouncedFen] = useState<string | null>(null);
const lastFenChangeAtRef = useRef(0);
useEffect(() => {
  if (fen === null) { setDebouncedFen(null); return; }
  const now = Date.now();
  const sinceLast = now - lastFenChangeAtRef.current;
  lastFenChangeAtRef.current = now;
  if (sinceLast > RAPID_STEP_DEBOUNCE_MS) { setDebouncedFen(fen); return; }
  const timer = setTimeout(() => setDebouncedFen(fen), RAPID_STEP_DEBOUNCE_MS);
  return () => clearTimeout(timer);
}, [fen]);

const abortControllerRef = useRef<AbortController | null>(null);
useEffect(() => {
  if (!debouncedFen || !poolRef.current || !queueRef.current) return;
  // Stop the PREVIOUS run's in-flight provider work before starting a new one —
  // signal.abort() alone does not do this (mctsSearch never forwards the signal
  // into dispatchExpansion's policy()/grade() calls — see Common Pitfalls §1).
  abortControllerRef.current?.abort();
  poolRef.current.stopAll();
  const controller = new AbortController();
  abortControllerRef.current = controller;
  void mctsSearch(debouncedFen, budget, providers, handleSnapshot, controller.signal);
}, [debouncedFen, budget, providers]);
```

### Pattern 3: Throttle (not debounce) `onSnapshot` into React state at ~150ms

**What:** `mctsSearch` calls `onSnapshot` synchronously after **every** completed backup (potentially many times per second at `concurrency > 1`, especially on pool-cache hits). D-09 asks for a "fixed batched cadence mirroring `RAPID_STEP_DEBOUNCE_MS`" — this is a leaky-bucket-style **throttle** (commit immediately if the last commit was >150ms ago; otherwise schedule exactly one trailing commit of the LATEST snapshot at the 150ms mark, canceling any previously scheduled one). This is a different mechanism from the existing `RAPID_STEP_DEBOUNCE_MS` usage elsewhere in the codebase (which debounces *input* — FEN navigation — not *output* streaming), even though it reuses the same 150ms constant value. No existing utility in the codebase does this; `useDebounce.ts` is a plain trailing debounce and is the wrong shape here.

**When to use:** Inside the hook's `onSnapshot` callback passed to `mctsSearch`.

**Example:**
```typescript
// New pattern — no direct precedent, but the "settled vs rapid" shape mirrors the
// adaptive debounce already used for FEN navigation in useStockfishEngine.ts.
const lastCommitAtRef = useRef(0);
const pendingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
const [snapshot, setSnapshot] = useState<EngineSnapshot | null>(null);

function handleSnapshot(next: EngineSnapshot): void {
  const now = Date.now();
  const sinceLast = now - lastCommitAtRef.current;
  if (pendingTimerRef.current) clearTimeout(pendingTimerRef.current);
  if (sinceLast > RAPID_STEP_DEBOUNCE_MS) {
    lastCommitAtRef.current = now;
    setSnapshot(next);
    return;
  }
  pendingTimerRef.current = setTimeout(() => {
    lastCommitAtRef.current = Date.now();
    setSnapshot(next);
  }, RAPID_STEP_DEBOUNCE_MS - sinceLast);
}
```

### Pattern 4: `SearchBudget.concurrency` should track the real pool size

**What:** `computePoolSize()` is already exported from `workerPool.ts` (`export function computePoolSize(): number`). Since `budget.concurrency` controls how many expansions `mctsSearch` dispatches per round (each becoming one `grade()` call), setting `concurrency` to the actual live worker count lets the search genuinely parallelize across all spawned workers, rather than under- or over-dispatching relative to what the pool can service in one round.

**When to use:** Budget construction, once per hook instance (or per pool-size determination — it's a synchronous, non-reactive function per Phase 154's own docs, computed once at lazy-spawn time).

**Example:**
```typescript
// computePoolSize() is exported from workerPool.ts (Phase 154) — call it once to
// keep budget.concurrency aligned with the actual number of live Stockfish workers.
const budget: SearchBudget = {
  maxNodes: FLAWCHESS_ENGINE_MAX_NODES,   // named constant — tune post-SC4 UAT
  maxPlies: FLAWCHESS_ENGINE_MAX_PLIES,   // named constant, must be in [6, 10] (SEED-082 lock)
  concurrency: computePoolSize(),
  elo: { w: selectedElo, b: selectedElo }, // see Open Questions §2
};
```

### Pattern 5: Eval-bar precedence + data-source handoff (D-04)

**What:** The left `EvalBar` slot (currently hard-wired to Maia at `Analysis.tsx` line ~1067) becomes conditional on FC-enabled; the right slot's `evalCp`/`evalMate` props swap source to `topLine.objectiveEvalCp` while FC runs. `EvalBar.tsx` needs zero code changes — it already accepts `whiteFraction` (override) and `accentColor`/`testId` (already used for the Maia/Stockfish precedent).

**Example:**
```typescript
// Left slot — FC precedence over Maia (D-04). topLine is rankedLines[0] or undefined.
const fcWhiteFraction = topLine
  ? (rootMover === 'white' ? topLine.practicalScore : 1 - topLine.practicalScore)
  : 0.5;
<EvalBar
  evalCp={null}
  evalMate={null}
  depth={0}
  whiteFraction={flawChessEnabled ? fcWhiteFraction : maiaWhiteFraction}
  flipped={boardFlipped}
  accentColor={flawChessEnabled ? FLAWCHESS_ENGINE_ACCENT : MAIA_ACCENT}
  testId={flawChessEnabled ? 'analysis-flawchess-eval-bar' : 'analysis-maia-eval-bar'}
/>

// Right slot — SF bar fed from the engine's objective root eval while FC runs.
<EvalBar
  evalCp={flawChessEnabled ? (topLine?.objectiveEvalCp ?? null) : engine.evalCp}
  evalMate={flawChessEnabled ? null : engine.evalMate}
  depth={flawChessEnabled ? 0 : engine.depth}
  flipped={boardFlipped}
  accentColor={STOCKFISH_ACCENT}
/>
```
Note: `RankedLine.objectiveEvalCp` never carries a mate value (it's a plain `number | null` cp from `MoveGrade`, itself derived from `evalToExpectedScore`'s ±1000cp Option-B mate mapping upstream in the search core) — so the right-slot swap never needs an `evalMate` branch; `objectiveEvalCp` at ±1000 already reads as a near-mate advantage on the bar's sigmoid scale, consistent with how the rest of the codebase treats Option-B mate mapping.

### Recommended Project Structure
```
frontend/src/
├── lib/engine/                          # unchanged Phase 153/154 modules (types.ts, guardrail.ts,
│                                         # mctsSearch.ts, workerPool.ts, maiaQueue.ts — READ ONLY)
├── hooks/
│   └── useFlawChessEngine.ts            # NEW — this phase
├── components/
│   ├── ui/
│   │   └── switch.tsx                   # NEW — hand-rolled Radix Switch wrapper (D-03)
│   └── analysis/
│       └── FlawChessEngineLines.tsx     # NEW — sibling of EngineLines.tsx
├── lib/
│   └── liveFlaw.ts (or a new small module) # extend with expectedScoreToWhitePovCp() (see Code Examples §1)
└── pages/
    └── Analysis.tsx                     # MODIFIED — 3-toggle refactor, eval-bar precedence, new card slot
```

### Anti-Patterns to Avoid
- **Passing `signal` to `mctsSearch` and assuming that alone stops worker-pool work:** it does not — see Common Pitfalls §1.
- **Treating D-09's "batched cadence" as a debounce:** a debounce would delay the FIRST paint by 150ms, directly contradicting DISPLAY-01's "appear immediately" requirement; it must be a throttle (see Pattern 3).
- **Recreating `workerPool`/`maiaQueue` instances per search:** breaks Phase 154's lazy-spawn-once-then-reuse design and the pool's own FEN-keyed cache; create once per `enabled` lifetime, not once per FEN.
- **Passing the full 600–2600 Maia ELO ladder into `budget.elo`:** `maiaQueue.policy()` already restricts itself to whatever `{w,b}` pair the caller supplies (Phase 154 D-04) — supplying anything wider defeats that design.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UCI → SAN conversion for modal-path chips | A new replay function | `replayPvLine()` from `EngineLines.tsx` (or extract it to a shared module if both components need it — Knip will flag an unused duplicate) | Already handles the null-SAN/null-FEN fallback chain and is the exact function DISPLAY-02's D-07 says to mirror |
| Eval-to-pawn-scale formatting | A new formatter | `formatScore()` from `EngineLines.tsx` | D-06 explicitly says reuse it verbatim; only the INPUT (a converted white-POV cp) is new, not the formatting function |
| Sigmoid / inverse-sigmoid math | A new constant or formula | `LICHESS_K` + `MATE_CP_EQUIVALENT` from `frontend/src/generated/flawThresholds.ts` (already imported by `liveFlaw.ts`) | These are backend-generated (`scripts/gen_flaw_thresholds_ts.py` mirrors `app/services/eval_utils.py`) — inventing a second sigmoid constant would silently diverge from the project's one true winning-chances curve |
| A Radix Switch primitive | A fresh `npx shadcn add switch` pull requiring re-theming | Hand-rolled `switch.tsx` around `radix-ui`'s already-installed `Switch` export, styled with the project's existing CVA convention | Matches every other `ui/` primitive in this codebase; avoids re-theming a shadcn preset against `radix-nova`'s neutral base |
| Toggle/switch on/off animation | Custom CSS transitions | Radix's own `data-state="checked"`/`"unchecked"` attribute selectors (same pattern `checkbox.tsx` already uses via `data-checked:`) | Zero new logic, consistent with the rest of `ui/` |

**Key insight:** Every "hard" primitive this phase needs (sigmoid math, UCI→SAN, PV-chip rendering, worker lifecycle, adaptive debounce) already exists somewhere in this codebase from Phases 136-154. The actual net-new code is thin: one hook wiring together existing pieces, one component that is 80% a structural clone of `EngineLines.tsx`, and one small pure function (the sigmoid inverse) that didn't exist before because nothing needed to go score→eval in that direction until now.

## Common Pitfalls

### Pitfall 1: Aborting `mctsSearch` does not free the Stockfish pool
**What goes wrong:** The hook calls `controller.abort()` on navigation, assumes the search has stopped, and starts a new `mctsSearch` call immediately. The new search's `dispatchExpansion()` calls queue behind the OLD search's still-in-flight `grade()` requests (which have no idea they were "aborted" — `dispatchExpansion` never receives the signal), so the pool's 2-4 workers stay busy grading stale candidate moves for up to `GRADING_MOVETIME_SAFETY_CAP_MS` (2500ms) each before the new search's requests get dispatched.
**Why it happens:** `mctsSearch`'s own `while` loop checks `signal.aborted` only between rounds and before applying already-resolved results (`mctsSearch.ts` lines 330, 390) — it never threads `signal` into `providers.policy(leaf.fen, ...)` or `providers.grade(leaf.fen, candidateUcis)` inside `dispatchExpansion` (lines 296, 314). `WorkerPool.grade()` DOES accept an optional third `signal` parameter that can cancel a queued-or-in-flight request (`workerPool.ts` lines 104, 389-415) — but `mctsSearch` never passes one.
**How to avoid:** On every abort, call `pool.stopAll()` (a synchronous, already-implemented method per `workerPool.ts` line 421-441 that sends `stop` to every thinking slot and resolves all pending requests) in addition to `controller.abort()`. `maiaQueue` has no equivalent `stopAll` (an in-flight ONNX inference genuinely cannot be interrupted, per its own module docstring) — a stale `policy()` call there simply resolves normally and its result is unused; this is fine and does not block the new search's requests (the queue's FIFO `processQueue()` just serves the new request next once the current inference completes).
**Warning signs:** During manual verification, rapidly stepping through several positions and observing the FlawChess card's lines lag noticeably behind board navigation (visibly slower than the existing Stockfish/Maia cards on the same interaction) is the symptom to watch for.

### Pitfall 2: `RankedLine.practicalScore` can hit exactly 0 or 1 — naive log-odds inversion produces `±Infinity`
**What goes wrong:** A direct `Math.log(es / (1 - es))` blows up to `Infinity`/`-Infinity`/`NaN` when `es` is exactly `0` or `1`.
**Why it happens:** `treeCommon.ts`'s `terminalValue()` returns exactly `1` or `0` for a genuine checkmate leaf (never `0.5 ± ε`), and `backup.ts`'s root-max/expectation formulas can propagate an exact `1`/`0` up to a root child if an entire subtree resolves to forced mate within the node budget. This is a real, reachable case — not just a theoretical boundary.
**How to avoid:** Special-case `es <= 0` and `es >= 1` to return `∓MATE_CP_EQUIVALENT * sign` directly (mirroring the forward function `evalToExpectedScore`'s own mate handling, which maps mate to `±MATE_CP_EQUIVALENT` cp BEFORE the sigmoid) rather than computing a literal inverse through the log at those boundaries. See Code Examples §1 for the exact implementation.
**Warning signs:** A badge rendering `NaN` or a blank/garbled score number on any position with a short forced mate in the search tree.

### Pitfall 3: A debounce is the wrong tool for D-09's "live-refine cadence"
**What goes wrong:** Implementing D-09 with a plain debounce (delay every `onSnapshot` commit by 150ms, reset the timer on each new snapshot) means the FIRST line never paints until 150ms after the FIRST `onSnapshot` call at the earliest, and if snapshots keep arriving faster than 150ms apart (likely, since `mctsSearch` calls `onSnapshot` after every single completed backup), the UI could show **nothing** for the entire duration of a fast, cache-hit-heavy search — directly violating DISPLAY-01's "appear immediately" success criterion.
**Why it happens:** The codebase's one existing precedent for `RAPID_STEP_DEBOUNCE_MS` (in `useStockfishEngine`/`useMaiaEngine`) is a debounce on *input* (rate-limiting how often a NEW search starts in response to rapid FEN changes) — a fundamentally different problem from THIS case, which is rate-limiting how often *output* commits to React state. Reusing the same constant value (150ms) does not mean reusing the same debounce mechanism.
**How to avoid:** Implement a throttle (see Code Examples §2/Pattern 3): commit immediately if the time since the last commit exceeds 150ms, otherwise schedule exactly one trailing commit of the latest snapshot.
**Warning signs:** The card's skeleton or an empty state lingering visibly longer than the Stockfish/Maia cards' own first-paint on the same position.

### Pitfall 4: Existing bar-cap labels already use `text-xs`, contradicting both CLAUDE.md's floor and the UI-SPEC's own claim
**What goes wrong:** The UI-SPEC's Component Inventory §2 states "'SF' and 'Maia' already exist as the current caps — no change to those two" and separately describes bar caps as "small `text-sm` caption." Reading the actual shipped code (`Analysis.tsx`'s `evalBarCap()` helper, ~line 1133) shows the existing caps use `className="whitespace-nowrap text-xs font-medium leading-none"` — i.e. `text-xs`, not `text-sm`, with an inline comment explicitly citing a UAT decision to shrink them ("a tiny bar cap acting as a visual aside, per UAT 'make the labels smaller'").
**Why it happens:** This predates Phase 155 (Phase 151.1 UAT) and was never reconciled with CLAUDE.md's `text-sm` floor rule (whose only documented exception is the dense-engine-surface `EngineLines`/`FlawChessEngineLines` PV-chip convention, not bar caps).
**How to avoid:** This is a **pre-existing** inconsistency, not something Phase 155 introduces — the new "FC" cap should almost certainly match the other two caps' actual rendered size (`text-xs`) for visual consistency across all three caps, even though this technically extends a floor violation rather than fixing it. Flag to the planner as a discretionary call: either (a) match precedent exactly (`text-xs` for "FC" too, consistent 3-cap row, technically still non-compliant) or (b) fix all three to `text-sm` as part of this phase (visually inconsistent row sizing risk if only "FC" changes). Not a blocking issue, but worth a one-line note in the plan so the plan-checker doesn't flag a NEW `text-xs` usage as a phase-155 regression when it's actually matching 2-year-old shipped precedent.
**Warning signs:** A plan-checker or code-review flagging `text-xs` on the new "FC" cap as a CLAUDE.md violation without context on the pre-existing two caps.

### Pitfall 5: `Analysis.tsx` is already 1564 lines — the 3-toggle refactor risks tripping the file's own bloat threshold
**What goes wrong:** Adding a third engine hook, a third card, and eval-bar precedence branching directly into the existing render risks pushing already-dense sections (the `boardRow`/`evalBarCap`/card-header JSX) past CLAUDE.md's soft/hard logic-LOC and nesting-depth limits.
**Why it happens:** `Analysis.tsx` already composes 3 engine hooks (`useStockfishEngine`, `useStockfishGradingEngine`, `useMaiaEngine`) plus derived state; a 4th (`useFlawChessEngine`) plus a new precedence-branching eval-bar section is exactly the kind of incremental addition CLAUDE.md's "refactor bloated code on sight" rule anticipates.
**How to avoid:** Extract the eval-bar precedence logic (Pattern 5) into a small local memo/derived-value block (not a new file necessarily, but a clearly separated pure computation) rather than inlining conditionals directly in JSX; consider whether the 3-switch row itself warrants a tiny local component (`EngineToggleRow` or similar) shared across all three `CardHeader`s to avoid tripling near-identical `Switch` + caption JSX inline.
**Warning signs:** Any single new `useMemo`/render block exceeding ~40 logic LOC or 3+ levels of conditional nesting in the eval-bar/card-header sections.

## Code Examples

### 1. Practical-score → white-POV pawn-equivalent inverse conversion (DISPLAY-03, D-06)

This is a genuinely new function — nothing in the codebase currently converts an expected-score BACK into a centipawn value (every existing use of the sigmoid goes eval→expectedScore, never the reverse). Derived directly from `liveFlaw.ts`'s existing `evalToExpectedScore` by algebraic inversion and verified against both mate-boundary directions this session.

```typescript
// Source: derived from frontend/src/lib/liveFlaw.ts's evalToExpectedScore (verified
// this session by direct algebraic inversion — [VERIFIED: codebase]).
//
// evalToExpectedScore: es = 1 / (1 + exp(-K * sign * cp))  where sign = mover==='white'?1:-1
// Inverting for cp:     cp = ln(es / (1 - es)) / (K * sign)
//
// Special-cases es<=0 / es>=1 to ±MATE_CP_EQUIVALENT (mirroring the forward function's
// own mate-before-sigmoid convention) rather than computing ln(0) / ln(Infinity) — see
// Common Pitfalls §2. This is display-only math; it is NEVER fed back into the search
// core (which only ever consumes/produces expected scores in its own root-relative frame).
import { LICHESS_K, MATE_CP_EQUIVALENT } from '@/generated/flawThresholds';
import type { MoverColor } from '@/lib/liveFlaw';

export function expectedScoreToWhitePovCp(es: number, rootMover: MoverColor): number {
  const sign = rootMover === 'white' ? 1 : -1;
  if (es <= 0) return -MATE_CP_EQUIVALENT * sign;
  if (es >= 1) return MATE_CP_EQUIVALENT * sign;
  return Math.log(es / (1 - es)) / (LICHESS_K * sign);
}
```
Verification worked through this session: `rootMover='white', es=0.9` → `+596.6cp` (white ahead, matches `evalToExpectedScore(596.6, null, 'white') ≈ 0.9`). `rootMover='black', es=0.9` (black winning) → `-596.6cp` (white-POV negative, correct). `rootMover='white', es=0` → `-1000cp`; `rootMover='black', es=0` → `+1000cp` (black losing = white winning, correct sign).

### 2. Score-pair badge composition (reusing `formatScore` verbatim, per D-06)

```typescript
// Both numbers reuse EngineLines.tsx's formatScore() unchanged — only the INPUT to the
// practical side is new (the converted white-POV cp above). objectiveEvalCp is already
// white-POV per the frozen RankedLine contract, so it needs no conversion at all.
const rootMover = sideToMoveFromFen(rootFen); // 'white' | 'black', from liveFlaw.ts
const objectiveText = formatScore(line.objectiveEvalCp, null);
const practicalCp = expectedScoreToWhitePovCp(line.practicalScore, rootMover);
const practicalText = formatScore(practicalCp, null);
// Render: <span style={{ color: STOCKFISH_ACCENT }}>{objectiveText}</span>
//         <span style={{ color: FLAWCHESS_ENGINE_HEADLINE_ACCENT }}>{practicalText}</span>
```

### 3. Modal-path rendering (DISPLAY-02, D-07) — verbatim reuse of `EngineLines.tsx`'s replay helper

```typescript
// RankedLine.modalPath is already a plain UCI[] (root-relative), exactly the same shape
// EngineLines.tsx's PvLine.moves is. replayPvLine() and MAX_PLIES-based slicing carry
// over with ZERO changes beyond the MAX_LINES constant (3 vs 2, D-08).
const steps = replayPvLine(baseFen, line.modalPath.slice(0, MAX_PLIES)); // reused verbatim
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Single-worker Stockfish grading (`useStockfishGradingEngine`, Phase 151.1) | N-worker priority-queued pool (`workerPool.ts`, Phase 154) | Phase 154 (2026-07-06) | This phase is the first REAL consumer of the pool — no prior React caller exists |
| Full-ladder Maia inference (`useMaiaEngine`, 600-2600 step 100) | Narrow, per-side-ELO-only Maia queue (`maiaQueue.ts`, Phase 154 D-04) | Phase 154 | This phase is the first consumer; confirms the narrow-ELO design pays off (no redundant inference for ELOs the search doesn't need) |
| One `engineEnabled` toggle gating both eval-bar search AND grading-chart search | Three independent card-level toggles (D-03) | This phase | Requires deciding the grading-worker binding (Claude's Discretion — see Open Questions) |

**Deprecated/outdated:** Nothing in this phase deprecates prior work — Phases 136-154 remain fully in production/shipped as-is; this phase is purely additive.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `budget.elo = { w: selectedElo, b: selectedElo }` (both colors share the one on-page ELO control) is the correct free-analysis-scope resolution of the {w,b} pair requirement | Summary, Open Questions §2 | If wrong, the engine's core asymmetric self+opponent differentiator (ENGINE-04) is silently inert in free analysis (both sides always see the same rating) until Phase 157; low functional risk since DISPLAY-01..04 don't require asymmetry to be visibly demonstrated, but worth a one-line confirmation from the user/planner since it affects the "practical for you" framing's honesty in this phase |
| A2 | Gating `useStockfishEngine`'s `enabled` prop on `stockfishToggleOn && !flawChessEngineActive` correctly satisfies POOL-04's already-completed mutual-exclusion success criterion while preserving the UI-SPEC's independent per-switch state | Summary, Open Questions §1 | If wrong (e.g. the true intent was for the Stockfish switch to fully override FC's handoff), up to 5 concurrent single-threaded Stockfish WASM instances could run on mobile simultaneously (1 standalone + up to 4 in the pool), directly risking the SC4 mobile-memory gate this exact phase is supposed to validate |
| A3 | `mctsSearch` (not `fallbackExpectimax`) is the correct `SearchRunner` to import, with no automatic runtime fallback wiring needed in this phase | Architecture Patterns (frozen contract section) | Low risk — both implement the identical type and are interchangeable at the call site; if the planner later wants automatic fallback-on-failure, it's a drop-in `try/catch` around the single `mctsSearch(...)` call, not a redesign |
| A4 | The new "FC" bar cap should visually match the existing "SF"/"Maia" caps' actual `text-xs` size rather than the UI-SPEC's stated `text-sm` | Common Pitfalls §4 | Low risk, purely cosmetic — a 3-cap row with one differently-sized label would look like a bug even if each individually complies with a stated spec |
| A5 | No `extraRootMoves` wiring is needed in this phase (leave `SearchBudget.extraRootMoves` unset/undefined) | Architecture Patterns (frozen contract section) | Low risk — it's an optional field whose purpose (root floor-boost against Maia truncation) was already fully resolved in Phase 153; Phase 155 has no stated requirement to inject Stockfish's own top move into the root candidate set |

**If this table is empty:** N/A — see entries above; none are HIGH risk to the phase's stated DISPLAY-01..04 success criteria, but A1 and A2 are architecturally load-bearing enough to warrant explicit planner sign-off before task-writing (both directly touch a Phase 154 success criterion already marked complete).

## Open Questions (RESOLVED)

> All three resolved during planning (2026-07-06) and carried into the plans with citations.
> `RESOLVED:` markers added below; recommendations were adopted verbatim.

1. **RESOLVED (155-04 Task 1, Assumption A2):** adopted `useStockfishEngine.enabled = engineEnabled && !flawChessEnabled` — standalone Stockfish search suspended while FC runs, SF bar fed from `topLine.objectiveEvalCp`. Surfaced as a HUMAN-UAT confirm item in 155-04 `<verification>` (touches a Phase-154-complete criterion).
   **Does the Stockfish card's switch need to actually gate `useStockfishEngine`'s worker (not just its own display), to honor POOL-04's mutual-exclusion contract?**
   - What we know: Phase 154's D-03 explicitly deferred "the actual shared 'engine active' signal that pauses the eval bar" to Phase 155 as "the researcher's job." The UI-SPEC's binding note says the Stockfish switch "keeps gating `useStockfishEngine` … exactly as `engineEnabled` does today" and separately doesn't gate the FC engine's `workerPool`.
   - What's unclear: Whether "gates `useStockfishEngine` exactly as today" was meant literally (switch fully controls the hook, independent of FC state) or loosely (switch controls the toggle's ON/OFF UI state, but the underlying hook is ALSO suppressed while FC runs, satisfying POOL-04 underneath).
   - Recommendation: Gate `useStockfishEngine`'s `enabled` input on `stockfishToggleOn && !flawChessEngineActive` (Assumption A2). This is the only reading that satisfies BOTH the UI-SPEC's stated toggle independence AND the already-completed POOL-04 success criterion; flag to the user/planner as a confirm-before-plan item given it touches a phase-154-complete criterion.

2. **RESOLVED (155-02, Assumption A1):** adopted `budget.elo = { w: selectedElo, b: selectedElo }`; true asymmetry deferred to Phase 157. Surfaced for UAT sign-off.
   **How does the single-number `selectedElo` map onto `SearchBudget.elo: {w, b}` in free-analysis mode (no `gameData.user_color`)?**
   - What we know: `useMaiaEloDefault` produces exactly one number (`selectedElo`), defaulting in free play to `profile.current_rating` regardless of color — there is no per-color "user" concept outside game-review mode (`isGameMode` gate). CONTEXT.md's Claude's Discretion note says only "reuse the existing … plumbing (per-side ELO for the practical model)" without specifying the mapping.
   - What's unclear: Whether both `w` and `b` should share `selectedElo` (Assumption A1, symmetric — no real "opponent" concept exists in an arbitrary free-play position), or whether the phase should introduce a second, separate "opponent ELO" control even though CONTEXT.md's canonical refs only mention reusing the existing single-selector plumbing.
   - Recommendation: `budget.elo = { w: selectedElo, b: selectedElo }` for this phase's scope; true asymmetry is naturally deferred to Phase 157 (game review), where `gameData.user_color` + ratings-at-game-time already exist. Flag to the user/planner for a one-line confirmation since it's a legitimate reading of "reuse the existing plumbing," not an invention.

3. **RESOLVED (155-02 Task 1):** named tunable constants `FLAWCHESS_ENGINE_MAX_PLIES = 8` and `FLAWCHESS_ENGINE_MAX_NODES` (~400), commented "tunable, revisit after SC4". No magic numbers inline.
   **What are the actual production `maxNodes`/`maxPlies` values?**
   - What we know: `maxPlies` is locked to the 6-10 range (SEED-082/153-CONTEXT.md); no existing test or module fixes a concrete `maxNodes` value for real (non-test) usage — every reference in `mctsSearch.test.ts` uses small fixture values (1-50) meaningless for production quality.
   - What's unclear: What node budget produces a "good enough" practical-play ranking within an acceptable wall-clock time on a 2-4-worker pool, especially on the mobile 2-worker floor.
   - Recommendation: Start with conservative named constants (e.g. `maxPlies = 8`, a mid-range `maxNodes` on the order of a few hundred), explicitly called out as "tunable, revisited after the SC4 real-device UAT" — mirroring Phase 154's own stated pattern for its adaptive-pool-sizing constants. Not a blocking question for planning (any reasonable placeholder is fine as a starting point), but the plan should name these as tunable constants, not hardcode them inline (CLAUDE.md "no magic numbers").

## Environment Availability

No new external dependencies, services, or runtimes are introduced this phase — everything (Stockfish.wasm binary, Maia ONNX model + onnxruntime-web worker, `radix-ui`'s Switch primitive) is already vendored/installed and was verified present in `frontend/node_modules`/`frontend/public/` during Phase 136/151/154. Skipping the full Environment Availability table as not applicable — this phase's only "environment" concern (mobile Safari memory ceiling under concurrent worker load) is the explicit subject of the already-scheduled SC4 real-device UAT, not a build-time/tooling dependency.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.7 + `@testing-library/react` 16.3.2 (existing, no changes needed) |
| Config file | `frontend/vite.config.ts` (Vitest reads Vite's config; no separate `vitest.config.ts` in this repo) |
| Quick run command | `cd frontend && npx vitest run src/hooks/__tests__/useFlawChessEngine.test.ts` (once created) |
| Full suite command | `cd frontend && npm test` (`vitest run`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISPLAY-01 | First `onSnapshot` commits to state near-instantly; subsequent snapshots throttle at ~150ms, never faster | unit (`renderHook` + fake timers, mirroring `useStockfishEngine.test.ts`'s `driveInit`/timer-advance pattern) | `npx vitest run src/hooks/__tests__/useFlawChessEngine.test.ts -t "throttle"` | ❌ Wave 0 |
| DISPLAY-01 | Navigating to a new FEN aborts the previous run AND calls `pool.stopAll()` (Pitfall 1 regression guard) | unit (mock `WorkerPool`/`MaiaQueue`, assert `stopAll` called on navigation) | `npx vitest run src/hooks/__tests__/useFlawChessEngine.test.ts -t "abort"` | ❌ Wave 0 |
| DISPLAY-02 | `FlawChessEngineLines` renders `modalPath` as SAN chips, first `MAX_PLIES=5` + expand chevron for the rest | unit (`@testing-library/react` render, mirrors `EngineLines.test.tsx`'s existing chip-rendering assertions) | `npx vitest run src/components/analysis/__tests__/FlawChessEngineLines.test.tsx` | ❌ Wave 0 |
| DISPLAY-03 | `expectedScoreToWhitePovCp` round-trips correctly at both mate boundaries (`es<=0`/`es>=1`) and mid-range values for both `rootMover` colors (Pitfall 2 regression guard) | unit (pure-function table test) | `npx vitest run src/lib/__tests__/expectedScoreToWhitePovCp.test.ts` (or co-located with `liveFlaw.test.ts` if extended there) | ❌ Wave 0 |
| DISPLAY-04 | Eval-bar left-slot precedence: FC shown when enabled, falls back to Maia when only Maia is on; right-slot source swaps to `topLine.objectiveEvalCp` while FC runs | unit/integration (extend the existing `frontend/src/pages/__tests__/Analysis.test.tsx`, which already has a `describe('Maia eval bar perspective (151.1 UAT regression)')` block and asserts on `analysis-maia-eval-bar`/`analysis-eval-bar` test IDs — this phase adds a parallel `describe` block for the FC-precedence case) | `npx vitest run src/pages/__tests__/Analysis.test.tsx -t "FlawChess"` | ✅ file exists — add new cases |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run <changed-test-file>`
- **Per wave merge:** `cd frontend && npm test` (full suite)
- **Phase gate:** Full suite green + `npm run lint` + `npx tsc -b` (type-check, per CLAUDE.md's explicit reminder that lint/test alone do not type-check shared property access) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/hooks/__tests__/useFlawChessEngine.test.ts` — covers DISPLAY-01 (throttle + abort/stopAll regression guard)
- [ ] `frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx` — covers DISPLAY-02, DISPLAY-03
- [ ] A pure-function test file for `expectedScoreToWhitePovCp` — covers DISPLAY-03's mate-boundary correctness (Pitfall 2)
- [ ] `frontend/src/pages/__tests__/Analysis.test.tsx` already exists and already covers eval-bar test IDs/perspective (151.1 UAT regression block) — extend it with FC-precedence cases rather than creating a new file; if the precedence logic grows complex, extract it into a directly-testable pure function per Common Pitfalls §5's extraction recommendation (also improves unit-testability over asserting through full page render)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Phase is entirely client-side, no auth surface touched |
| V3 Session Management | No | No session/cookie interaction |
| V4 Access Control | No | No new authorization boundary |
| V5 Input Validation | Yes (narrow) | UCI/FEN strings flowing through the search core already pass through `applyUciMoveFen`'s try/catch containment (`treeCommon.ts`, WR-07) — a malformed provider candidate is deterministically dropped, never thrown; this phase's ONLY new input-validation surface is the modal-path SAN rendering, which reuses `EngineLines.tsx`'s already-hardened `replayPvLine()` (per-move try/catch, falls back to raw UCI) |
| V6 Cryptography | No | Not applicable |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Unescaped engine-string XSS (a malicious/corrupted UCI or SAN string rendered raw into the DOM) | Tampering / Information Disclosure | Already mitigated project-wide: "All engine strings are rendered as React children (auto-escaped, T-137-03 mitigated)" per `EngineLines.tsx`'s own module docstring — `FlawChessEngineLines.tsx` inherits this by construction as long as it renders SAN/UCI strings the same way (JSX children, never `dangerouslySetInnerHTML`) |
| Worker script-load failure treated as silent hang | Denial of Service (self-inflicted, not attacker-driven) | Already covered by Phase 154's `worker.onerror`/graceful-degradation handling in both `workerPool.ts` and `maiaQueue.ts` (every failure path resolves affected promises to empty rather than hanging) — Phase 155's hook must not swallow or bypass this by, e.g., awaiting a raw `grade()`/`policy()` call without the existing empty-resolution contract in place |

No new attack surface is introduced by this phase beyond what Phases 136-154 already established and hardened — this is a pure UI-wiring phase over an already-security-reviewed client-side engine core.

## Sources

### Primary (HIGH confidence)
- `frontend/src/lib/engine/types.ts`, `guardrail.ts`, `mctsSearch.ts`, `treeCommon.ts`, `leafScore.ts`, `workerPool.ts`, `maiaQueue.ts` — read in full this session; every claim about the frozen contract, the abort-signal gap, and the pool/queue lifecycle is grounded directly in this source, not training data
- `frontend/src/hooks/useStockfishEngine.ts`, `useStockfishGradingEngine.ts`, `useMaiaEngine.ts` — read in full this session; the debounce/throttle/lifecycle patterns are extracted directly from these
- `frontend/src/components/analysis/EngineLines.tsx`, `EvalBar.tsx` — read in full this session
- `frontend/src/pages/Analysis.tsx` (relevant sections, ~400 lines across several reads) — read this session
- `frontend/src/lib/liveFlaw.ts`, `frontend/src/generated/flawThresholds.ts` — read in full this session; the sigmoid inversion is derived directly from this source
- `.planning/phases/155-.../155-CONTEXT.md`, `155-UI-SPEC.md`, `.planning/phases/154-.../154-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` — read in full this session

### Secondary (MEDIUM confidence)
- None — no external documentation lookups were needed; every question this phase raises is answerable from the codebase itself (a pure wiring phase over a fully-specified internal contract)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; `radix-ui`'s `Switch` export confirmed present in installed `node_modules` this session
- Architecture: HIGH — every pattern is directly grounded in already-shipped, read-this-session source code, not inference
- Pitfalls: HIGH — the abort/stopAll gap and the mate-boundary log-inversion issue were both discovered by direct source reading + manual derivation this session, not assumed

**Research date:** 2026-07-06
**Valid until:** Effectively indefinite for the frozen-contract portions (types.ts/guardrail.ts are explicitly locked for the rest of the v2.0 milestone); ~30 days for anything touching `Analysis.tsx`'s current line numbers/structure, since that file is actively evolving across phases
