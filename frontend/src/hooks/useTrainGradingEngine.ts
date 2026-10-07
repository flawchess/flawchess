/**
 * useTrainGradingEngine — session-scoped single-Worker Stockfish grading
 * engine for the Train solve loop (SOLV-03).
 *
 * Mirrors useStockfishEngine.ts's classic (non-module) Worker lifecycle and
 * idle/thinking/stopping UCI state machine (190-RESEARCH.md Pattern 4), but
 * exposes an IMPERATIVE surface instead of a fen-prop-driven one: the caller
 * explicitly starts/aborts a search per puzzle (`startGrading`/`abortGrading`)
 * rather than relying on mount/unmount, because the search must outlive a
 * per-puzzle component key change (190-RESEARCH.md Pitfall 3).
 *
 * Exactly ONE Worker exists for the whole session — created once when the
 * solve loop mounts (`enabled` toggled at the SESSION boundary, never per
 * puzzle — 190-RESEARCH.md Pattern 4 / Pitfall 2).
 *
 * Grading rule (Phase 235, SEED-192: the phone grades against the SERVER KEY;
 * the server picks the solution MOVE, the phone supplies every NUMBER):
 *   mover = sideToMoveFromFen(fen)
 *   anchor (think time, `startGrading(fen, keyUci)`):
 *     keyed (D-08)  -> ONE width-1 search of the position AFTER the key move;
 *                      anchor.es = evalToExpectedScore(afterKey eval, mover)
 *     no usable key (null, missing from a stale server, or illegal; D-07) ->
 *                      today's root search; anchor.keyUci is its bestmove and
 *                      anchor.es its root ES (legacy anchor)
 *   gradeMove(fen, playedMoveUci):
 *     playedMoveUci === anchor.keyUci -> GOOD, no second search (D-01)
 *     else -> ONE width-1 search of the position after the played move at the
 *             same budget, esAfter with the SAME mover;
 *             severity = classifyLiveSeverity(anchor.es, esAfter)
 *             moveTier = moveTierFromSeverity(severity)  (SEED-119: good/inaccuracy/wrong)
 * Both numbers of the drop are the phone's own searches at the same horizon
 * (after one move), so no server number ever enters the drop and no mixed
 * root-vs-after-move horizon remains (D-01). `GradeResult.bestMoveUci` /
 * `bestLine` / `esBefore` keep their names but now mean the KEY, its after-key
 * line and the after-key ES (D-09), so every downstream consumer (reveal
 * arrow, line boxes, board badge, free-play seed) names the key unchanged.
 * The mount search is width 1 (Phase 211 D-05): this hook proposes NO
 * alternative moves; the "Also fine" set is certified SERVER-side, and when the
 * played move is one of the server's certified key moves, record_solve
 * OVERRIDES the tier this hook computed (Phase 211 D-07).
 * Accepted residual (Phase 211 D-04): an OFF-KEY played move is graded
 * best-effort by this live engine and can still disagree with the analysis
 * board's deeper verdict.
 * Never re-derive the sigmoid/threshold locally — both come from
 * `@/lib/liveFlaw` (CI-drift-checked against app/services/flaws_service.py).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { parseInfoLine, parseBestmove } from './uciParser';
import type { PvLine } from './uciParser';
import { classifyLiveSeverity, evalToExpectedScore, sideToMoveFromFen } from '@/lib/liveFlaw';
import { moveTierFromSeverity } from '@/lib/trainScore';
import {
  createStockfishWorker,
  ensureStockfishWorkerUrl,
} from '@/lib/engine/stockfishWorkerSource';
import {
  buildSearchResult,
  clampLineEvalToBest,
  fenAfterUciMove,
  finishRecheck,
  keyedAnchorFrom,
  legacyAnchorFrom,
  planRecheck,
  raceWithTimeout,
  terminalSearchResult,
} from './trainGradingSupport';
import type {
  GradeResult,
  GradingAnchor,
  LastPlayedSearch,
  RawSearchResult,
  RecheckInnerResult,
  RecheckResult,
  TrainEngineLine,
} from './trainGradingSupport';

// The public result types live in trainGradingSupport (pure, React-free) and
// are re-exported here so every existing importer keeps its import path.
export type { GradeResult, RecheckResult, TrainEngineLine } from './trainGradingSupport';

// ─── Constants ──────────────────────────────────────────────────────────────

/**
 * Grading search budget — MEASURED 2026-07-25 via
 * `node scripts/measure-train-movetime.mjs` (ladder 500/1000/1500/2500ms,
 * node cap 2,000,000, against 10 real sharp-blunder FENs extracted from
 * this project's own dev DB — see the script's FENS comment for
 * provenance). Stability defined as: same best move AND expected-score
 * reading within `INACCURACY_DROP / 2` of the 2500ms baseline run (raw cp
 * is naturally noisy even at a fixed movetime — project_eval_nondeterminism
 * — so exact-cp equality is the wrong bar; ES is what the grading decision
 * actually consumes).
 *
 * Result: the engine's TOP MOVE was identical to the baseline at every
 * movetime for all 10 FENs (0 disagreements) — the fast-path exact-match
 * check (D-06) is unaffected by movetime in this sample. ES stability
 * (score) reached the baseline by 1000ms for every FEN, worst case; two
 * FENs needed 1000ms specifically (max ES diff at 500ms: 0.089 on one
 * sharp rook-endgame FEN), the rest were stable already at 500ms. Kept the
 * existing 1500ms value rather than lowering it: one full rung of margin
 * above the measured 1000ms floor, generous for sharp-puzzle accuracy
 * without materially changing the D-06 "Checking your move…" wait
 * (worst case: two sequential 1500ms searches on a non-exact-match
 * puzzle). See 190-01-SUMMARY.md for the full per-FEN table.
 */
export const TRAIN_GRADING_MOVETIME_MS = 1500;
export const TRAIN_GRADING_MAX_NODES = 2000000;

/**
 * Mount-search width and movetime. Width 1 as of Phase 211 (D-05):
 * alternatives ("Also fine" moves) are now certified SERVER-side from the
 * stored deep answer key (soft `su`, herring good-band ladder), so the mount
 * search no longer proposes any — the only consumers of this search are the
 * best move, `esBefore`, and the displayed solution PV. The full
 * `TRAIN_GRADING_MOUNT_MOVETIME_MS` budget therefore goes to ONE line instead
 * of being split four ways, which is the accuracy argument for the change: a
 * deeper best line and steadier esBefore from the same wall-clock budget.
 *
 * The width-4 sweep that previously justified this constant (measured
 * 2026-07-26 via `node scripts/measure-train-movetime.mjs`) is retained in
 * 190.1-02-SUMMARY.md and is no longer the reason for this value. The
 * movetime constants are unchanged — no new number is invented by Phase 211.
 */
export const TRAIN_GRADING_MULTIPV_WIDTH = 1;
export const TRAIN_GRADING_MOUNT_MOVETIME_MS = TRAIN_GRADING_MOVETIME_MS;

/**
 * Hard ceiling on `gradeMove`'s returned promise (Phase 190-01 checkpoint
 * bug fix — manual browser UAT hit an indefinite "Checking your move…"
 * hang). Generous above the worst case (two sequential
 * `TRAIN_GRADING_MOVETIME_MS` searches plus WASM/message-passing overhead)
 * so it never fires under normal operation, but finite so a genuinely wedged
 * engine (a dead Worker, a StrictMode double-invoke race, a search that
 * never emits `bestmove`) always resolves to a visible error state instead
 * of a silent infinite spinner.
 */
export const TRAIN_GRADING_TIMEOUT_MS = 8000;

/**
 * Phase 235 (D-11): search budget of EACH of the two disagreement re-check
 * searches (key, then played), twice the 1.5 s grading search.
 */
export const TRAIN_RECHECK_MOVETIME_MS = 3000;

/** Headroom factor on the scaled re-check node cap, so the cap never binds before the movetime does. */
const TRAIN_RECHECK_NODE_HEADROOM = 2;

/**
 * Node cap of each re-check search (8,000,000). Scales the grading cap with the
 * movetime and doubles it: measured in Node 24 on the user-28 FEN, the 2M
 * grading cap bound at 2,699 ms (2,000,425 nodes), so a "3 s" re-check under
 * that cap would not search any deeper than the 1.5 s one (RESEARCH Pitfall 1).
 */
export const TRAIN_RECHECK_MAX_NODES =
  TRAIN_GRADING_MAX_NODES *
  (TRAIN_RECHECK_MOVETIME_MS / TRAIN_GRADING_MOVETIME_MS) *
  TRAIN_RECHECK_NODE_HEADROOM;

/**
 * Hard ceiling on `recheckMove` (D-11, D-20): two sequential re-check searches
 * plus stop/queue and WASM overhead. Separate from TRAIN_GRADING_TIMEOUT_MS,
 * which stays 8000 for the normal path. On expiry the 1.5 s grade stands.
 */
export const TRAIN_RECHECK_TIMEOUT_MS = 12000;

// ─── Types ──────────────────────────────────────────────────────────────────

type EngineState = 'idle' | 'thinking' | 'stopping';

interface QueuedDispatch {
  fen: string;
  generation: number;
  /** MultiPV width to request for this dispatch — travels WITH the deferred
   * dispatch (190.1-02) rather than being fixed at call time, since the
   * mount search (width TRAIN_GRADING_MULTIPV_WIDTH) and every other search
   * (width 1) share the same stop/queue serialization. */
  width: number;
  movetimeMs: number;
  /** Node cap travels WITH the dispatch (Phase 235 D-11) so a re-check search
   * keeps its raised cap through the stop-queue and readyok drains. */
  maxNodes: number;
  resolve: (result: RawSearchResult) => void;
  reject: (error: Error) => void;
}

export interface UseTrainGradingEngineOptions {
  /** Session-scoped enable — created once per session, never per puzzle. */
  enabled: boolean;
}

export interface TrainGradingEngine {
  isReady: boolean;
  /** True once the Worker has reported a genuine error (failed to load/
   * crashed) — surfaced so callers can show an error state rather than
   * silently retry against a dead engine. */
  hasError: boolean;
  /**
   * Start the think-time anchor search for a puzzle's FEN. With a usable
   * `keyUci` (the server key) it evaluates the position AFTER the key (D-08);
   * with null/undefined/illegal it is today's root search (D-07).
   */
  startGrading: (fen: string, keyUci?: string | null) => void;
  /** Cancel any in-flight/pending search for the current puzzle (Pitfall 3). */
  abortGrading: () => void;
  /**
   * Tear down the current Worker and spin up a fresh one (190-04 T-190-13:
   * the engine-failure fallback's retry affordance). Clears `hasError` so a
   * genuinely recovered engine is usable again; the caller must re-issue
   * `startGrading` for the current puzzle afterwards.
   */
  restartEngine: () => void;
  /**
   * Resolve the grading verdict for a played move against the fen most
   * recently passed to `startGrading`. Awaits the anchor search if it
   * has not yet settled. Rejects if grading does not complete within
   * `TRAIN_GRADING_TIMEOUT_MS` or the engine reports an error — callers
   * MUST catch this (never treated as "still loading" indefinitely).
   */
  gradeMove: (fen: string, playedMoveUci: string) => Promise<GradeResult>;
  /**
   * Reveal-time search for the PLAYED IN GAME box (190.1-01, D-01 point 3):
   * derives the position after `gameMoveUci` (rejecting on an illegal/
   * malformed move) and runs a fresh single-line search on it. Resolves a
   * `TrainEngineLine` rooted at `puzzleFen` — see that interface's doc
   * comment for the shared invariant. Reuses the SAME `generationRef` as
   * `startGrading`/`gradeMove` (no second cancellation authority).
   */
  startGameMoveSearch: (puzzleFen: string, gameMoveUci: string) => Promise<TrainEngineLine>;
  /**
   * Phase 235 (D-10/D-11): re-run BOTH after-move searches (key, then played)
   * at TRAIN_RECHECK_MOVETIME_MS with the raised node cap, after `gradeMove`
   * rated an off-key move good. NEVER rejects: a missing anchor, a legacy
   * anchor, a superseded puzzle, an engine error or a timeout all resolve
   * null, and the caller keeps the 1.5 s grade and posts no record (D-20).
   */
  recheckMove: (fen: string, playedMoveUci: string) => Promise<RecheckResult | null>;
}

// ─── Hook ───────────────────────────────────────────────────────────────────

export function useTrainGradingEngine({
  enabled,
}: UseTrainGradingEngineOptions): TrainGradingEngine {
  const workerRef = useRef<Worker | null>(null);
  const isReadyRef = useRef(false);
  const [isReady, setIsReady] = useState(false);
  const hasErrorRef = useRef(false);
  const [hasError, setHasError] = useState(false);
  /** Bumped by restartEngine() to force the Worker-lifecycle effect below to
   * tear down and recreate the Worker (190-04 engine-failure fallback). */
  const [restartGeneration, setRestartGeneration] = useState(0);

  /** Internal UCI state machine — mirrors useStockfishEngine.ts. */
  const stateRef = useRef<EngineState>('idle');
  /** True while awaiting the termination bestmove of an explicit `stop`. */
  const stopPendingRef = useRef(false);
  /** Latest dispatch request deferred until a `stop`-in-flight settles. */
  const queuedDispatchRef = useRef<QueuedDispatch | null>(null);
  /** Bug fix (CR-01): latest dispatch request deferred until the Worker's UCI
   * handshake actually completes (`readyok`). Before this fix, `search()`
   * resolved immediately with a fabricated `{evalCp: null, evalMate: null,
   * bestMoveUci: null}` whenever it was invoked before `isReadyRef.current`
   * flipped true — a completely normal state for the first puzzle of a
   * session, since WASM boot + handshake takes real wall-clock time. That
   * fabricated result permanently "settled" the puzzle's best-search: graded
   * against a neutral eval unrelated to the real position, and the D-06
   * exact-match fast path could never trigger (bestMoveUci stayed null). Only
   * the LATEST request matters if `search()` is called again before ready. */
  const pendingReadyDispatchRef = useRef<QueuedDispatch | null>(null);

  /** Bumped by startGrading/abortGrading; used to discard a superseded
   * search's result (Pitfall 3 — a stale verdict must never leak into the
   * next puzzle's state). */
  const generationRef = useRef(0);

  /** Resolver/rejecter + metadata for whichever `go` is currently in flight. */
  const pendingRef = useRef<{
    generation: number;
    whitePovSign: 1 | -1;
    resolve: (result: RawSearchResult) => void;
    reject: (error: Error) => void;
  } | null>(null);
  /** In-flight MultiPV map: keyed by multipv index, updated on exact info
   * lines (190.1-02, mirrors useStockfishEngine.ts's pvMapRef). Raw
   * (mover-POV, not yet sign-normalized) — cleared in `dispatchNow`, read
   * and sign-normalized once at `bestmove` to build the settled `lines`
   * array. A width-1 search still populates exactly one entry (rank 1). */
  const pvMapRef = useRef<Map<number, PvLine>>(new Map());

  /** The settled think-time anchor for the puzzle most recently passed to
   * startGrading (Phase 235). */
  const anchorRef = useRef<GradingAnchor | null>(null);
  /** Resolves once the CURRENT generation's anchor search settles; gradeMove
   * awaits this so it works even if called before the search finishes. */
  const anchorReadyRef = useRef<Promise<void>>(Promise.resolve());
  /** The 1.5 s after-played search of the move `gradeMoveInner` most recently
   * graded (Phase 235 D-17); see `LastPlayedSearch`. */
  const lastPlayedSearchRef = useRef<LastPlayedSearch | null>(null);

  // ─── Low-level dispatch (refs only — stable across renders) ───────────────

  const dispatchNow = useCallback(
    (
      fen: string,
      generation: number,
      resolve: (r: RawSearchResult) => void,
      reject: (error: Error) => void,
      width: number,
      movetimeMs: number,
      maxNodes: number,
    ) => {
      const worker = workerRef.current;
      if (!worker) {
        reject(new Error('Grading engine unavailable'));
        return;
      }
      pvMapRef.current.clear();
      const whitePovSign: 1 | -1 = fen.split(' ')[1] === 'b' ? -1 : 1;
      pendingRef.current = { generation, whitePovSign, resolve, reject };
      // 190.1-02 D-01 point 1: setoption FIRST, before position/go, so it
      // inherits this state machine's existing idle/thinking/stopping
      // serialization for free — no separate ordering concern. Sent for
      // EVERY dispatch (width 1 included) so the width always travels with
      // the dispatch rather than assuming a prior value survived.
      worker.postMessage(`setoption name MultiPV value ${width}`);
      worker.postMessage(`position fen ${fen}`);
      worker.postMessage(`go movetime ${movetimeMs} nodes ${maxNodes}`);
      stateRef.current = 'thinking';
    },
    [],
  );

  /** Serialized search dispatch — no restricted-move clause (a free
   * MultiPV-width search on an arbitrary FEN). If the engine is mid-search,
   * sends `stop` and defers this dispatch until the stale bestmove settles.
   * Rejects immediately if the engine has already reported a fatal error.
   * `width`/`movetimeMs` travel WITH the dispatch (190.1-02) so a deferred
   * dispatch (queued behind a stop or the initial readyok handshake) still
   * requests the width/budget its caller asked for. */
  const search = useCallback(
    (
      fen: string,
      generation: number,
      width: number,
      movetimeMs: number,
      maxNodes: number = TRAIN_GRADING_MAX_NODES,
    ): Promise<RawSearchResult> =>
      new Promise((resolve, reject) => {
        const worker = workerRef.current;
        if (hasErrorRef.current) {
          reject(new Error('Grading engine failed to load'));
          return;
        }
        if (!worker || !isReadyRef.current) {
          // Bug fix (CR-01): queue and dispatch once readyok arrives (see
          // readyok's handler in handleLine below) instead of resolving with
          // a fabricated result that permanently "settles" this generation.
          //
          // This covers TWO states, both real and both eventually resolved
          // by the SAME `readyok` drain below, since `enabled` never flips
          // back to false mid-session (Train.tsx passes a constant `true`):
          // (1) the Worker exists but hasn't finished its UCI handshake yet
          // (slow WASM fetch/init — a completely normal state for the very
          // first puzzle of a session); (2) the Worker doesn't even EXIST
          // yet (`workerRef.current` is still null) — a GUARANTEED state on
          // first mount in production, because React commits a CHILD
          // component's mount effects (TrainSolveScreen's own effect, which
          // calls startGrading) before an ANCESTOR's effects (this hook's
          // own Worker-construction effect lives in Train.tsx, the parent).
          // Rejecting outright on `!worker` (as an earlier version of this
          // fix did) broke every very first puzzle of every session.
          pendingReadyDispatchRef.current = { fen, generation, width, movetimeMs, maxNodes, resolve, reject };
          return;
        }
        if (stateRef.current === 'thinking') {
          worker.postMessage('stop');
          stopPendingRef.current = true;
          stateRef.current = 'stopping';
          queuedDispatchRef.current = { fen, generation, width, movetimeMs, maxNodes, resolve, reject };
          return;
        }
        if (stateRef.current === 'stopping') {
          // Only the latest request matters once the stale bestmove settles.
          queuedDispatchRef.current = { fen, generation, width, movetimeMs, maxNodes, resolve, reject };
          return;
        }
        dispatchNow(fen, generation, resolve, reject, width, movetimeMs, maxNodes);
      }),
    [dispatchNow],
  );

  /** Every after-move search (anchor after the key, graded after the played
   * move, reveal after the game move) is a width-1 search of the position
   * AFTER one move, serialized through `search`. A checkmated or stalemated
   * after-move position is scored directly with no dispatch (see
   * `terminalSearchResult`). */
  const searchAfterMove = useCallback(
    (
      afterFen: string,
      generation: number,
      movetimeMs: number,
      maxNodes: number = TRAIN_GRADING_MAX_NODES,
    ): Promise<RawSearchResult> => {
      const terminal = terminalSearchResult(afterFen);
      if (terminal !== null) return Promise.resolve(terminal);
      return search(afterFen, generation, 1, movetimeMs, maxNodes);
    },
    [search],
  );

  // ─── Worker lifecycle ───────────────────────────────────────────────────

  useEffect(() => {
    if (!enabled) return;

    // A restartEngine() call (or the initial mount) starts from a clean
    // error/ready state — a stale hasError from a PRIOR Worker instance must
    // never leak into the new one (190-04 engine-failure fallback).
    hasErrorRef.current = false;
    setHasError(false);

    // Phase 213-08 (G-213-35): an unmount that beats the shared fetch must
    // not construct (and immediately leak) a worker nobody will ever clean
    // up — mirrors useStockfishEngine.ts's identical guard.
    let cancelled = false;

    function setupWorker(sharedUrl: string | null): void {
      if (cancelled) return;

      // Classic (non-module) Worker — Emscripten glue uses self.onmessage /
      // self.postMessage. Do NOT pass { type: 'module' }. Phase 213-08:
      // constructed through the shared source module — a non-null
      // `sharedUrl` routes to the already-fetched-once `.wasm`; a null
      // `sharedUrl` constructs against the served path exactly as before.
      // This hook reports no asset progress today and does not start doing
      // so here — the only change is where the worker's `.wasm` comes from.
      const worker = createStockfishWorker(sharedUrl);
      workerRef.current = worker;

      runWorkerHandshake(worker);
    }

    /** Wires the UCI line handler and kicks off the handshake for `worker`. */
    function runWorkerHandshake(worker: Worker): void {
      function handleLine(line: string): void {
        if (line === 'uciok') {
          worker.postMessage('isready');
          return;
        }
        if (line === 'readyok') {
          setIsReady(true);
          isReadyRef.current = true;
          // CR-01: drain whatever search() call arrived while the Worker was
          // still completing its UCI handshake, exactly once, for real.
          const pendingReady = pendingReadyDispatchRef.current;
          pendingReadyDispatchRef.current = null;
          if (pendingReady) {
            dispatchNow(
              pendingReady.fen,
              pendingReady.generation,
              pendingReady.resolve,
              pendingReady.reject,
              pendingReady.width,
              pendingReady.movetimeMs,
              pendingReady.maxNodes,
            );
          }
          return;
        }
        if (line.startsWith('info ')) {
          if (stateRef.current !== 'thinking' || stopPendingRef.current) return;
          const parsed = parseInfoLine(line);
          // Bug fix (190.1 UAT round 4): drop lowerbound/upperbound lines
          // instead of letting them overwrite the map (uciParser Pitfall 5).
          // An aspiration-window fail at the end of the movetime budget emits
          // e.g. "info depth 20 ... upperbound ... pv <2 moves>" as the LAST
          // rank-1 line, clobbering the previous exact iteration's full PV —
          // verified against the vendored engine headlessly (depth-19 exact
          // 30-ply PV replaced by a depth-20 UB 2-ply PV). That made the
          // reveal's Your-move / Played-in-game lines often 2-3 moves long.
          // Every completed iteration emits exact lines for all ranks, so the
          // map is never left empty by this filter.
          if (parsed !== null && parsed.bound === 'exact') {
            pvMapRef.current.set(parsed.multipv, {
              multipv: parsed.multipv,
              depth: parsed.depth,
              moves: parsed.pv,
              evalCp: parsed.scoreCp,
              evalMate: parsed.scoreMate,
            });
          }
          return;
        }
        if (line.startsWith('bestmove')) {
          const bestMoveUci = parseBestmove(line);

          if (stopPendingRef.current) {
            // Termination response to an explicit stop — always discard its
            // content and fire whatever dispatch was queued behind it.
            stopPendingRef.current = false;
            stateRef.current = 'idle';
            pendingRef.current = null;
            const queued = queuedDispatchRef.current;
            queuedDispatchRef.current = null;
            if (queued) {
              dispatchNow(
                queued.fen,
                queued.generation,
                queued.resolve,
                queued.reject,
                queued.width,
                queued.movetimeMs,
                queued.maxNodes,
              );
            }
            return;
          }

          stateRef.current = 'idle';
          const pending = pendingRef.current;
          pendingRef.current = null;
          if (!pending) return;
          pending.resolve(buildSearchResult(pvMapRef.current, pending.whitePovSign, bestMoveUci));
        }
      }

      worker.onmessage = (e: MessageEvent<string>) => {
        handleLine(e.data);
      };

      // Bug fix (Phase 190-01 checkpoint): a Worker construction/load failure
      // (e.g. the vendored WASM asset 404s or the browser can't instantiate
      // it) previously left every pending/queued search unresolved forever —
      // gradeMove would hang on `await anchorReadyRef.current` with no
      // visible error. Surface it via `hasError` and reject anything waiting
      // immediately rather than making callers wait out the full
      // TRAIN_GRADING_TIMEOUT_MS on a definitively-dead engine.
      worker.onerror = () => {
        hasErrorRef.current = true;
        setHasError(true);
        stateRef.current = 'idle';
        stopPendingRef.current = false;
        const pending = pendingRef.current;
        pendingRef.current = null;
        pending?.reject(new Error('Grading engine failed to load'));
        const queued = queuedDispatchRef.current;
        queuedDispatchRef.current = null;
        queued?.reject(new Error('Grading engine failed to load'));
      };

      worker.postMessage('uci');
    }

    ensureStockfishWorkerUrl().then(setupWorker);

    return () => {
      cancelled = true;
      // Phase 213-08: the shared-URL promise may not have resolved yet — if
      // `setupWorker` never ran, there is no worker to stop/terminate, and
      // `cancelled` above stops the deferred continuation from constructing
      // one after this cleanup has already run. Every other reset below is
      // unconditional — it must happen whether or not a worker ever existed.
      const worker = workerRef.current;
      if (worker) {
        worker.postMessage('stop');
        worker.terminate();
        workerRef.current = null;
      }
      setIsReady(false);
      isReadyRef.current = false;
      stateRef.current = 'idle';
      stopPendingRef.current = false;
      pendingRef.current = null;
      queuedDispatchRef.current = null;
      pendingReadyDispatchRef.current = null;
    };
  }, [enabled, dispatchNow, restartGeneration]);

  // ─── Imperative surface ─────────────────────────────────────────────────

  const restartEngine = useCallback(() => {
    setRestartGeneration((g) => g + 1);
  }, []);

  const startGrading = useCallback(
    (fen: string, keyUci: string | null = null) => {
      generationRef.current += 1;
      const generation = generationRef.current;
      anchorRef.current = null;
      lastPlayedSearchRef.current = null;
      let resolveReady: () => void = () => {};
      let rejectReady: (error: Error) => void = () => {};
      const readyPromise = new Promise<void>((resolve, reject) => {
        resolveReady = resolve;
        rejectReady = reject;
      });
      // Attach a no-op catch directly to the stored promise so a rejection
      // (engine error / superseded search) never surfaces as an unhandled
      // promise rejection — gradeMove is the one real consumer and it awaits
      // this exact promise, propagating the failure through its own reject path.
      readyPromise.catch(() => {});
      anchorReadyRef.current = readyPromise;
      // Phase 235 (D-08): with a usable key the think-time budget goes to the
      // position AFTER the key (width 1), so gradeMove compares two after-move
      // searches at the same horizon. A null, missing or illegal key (D-07)
      // keeps today's root search; the key line is then the root bestmove's.
      const afterKeyFen = keyUci !== null ? fenAfterUciMove(fen, keyUci) : null;
      const anchorSearch: Promise<GradingAnchor> =
        keyUci !== null && afterKeyFen !== null
          ? searchAfterMove(afterKeyFen, generation, TRAIN_GRADING_MOUNT_MOVETIME_MS).then((raw) =>
              keyedAnchorFrom(fen, generation, keyUci, raw),
            )
          : search(fen, generation, TRAIN_GRADING_MULTIPV_WIDTH, TRAIN_GRADING_MOUNT_MOVETIME_MS).then(
              (raw) => legacyAnchorFrom(fen, generation, raw),
            );
      anchorSearch
        .then((anchor) => {
          // Superseded by a later startGrading/abortGrading — discard silently
          // (Pitfall 3: never leak a stale verdict into the next puzzle).
          if (generation !== generationRef.current) return;
          anchorRef.current = anchor;
          resolveReady();
        })
        .catch((error: unknown) => {
          if (generation !== generationRef.current) return;
          rejectReady(error instanceof Error ? error : new Error('Grading search failed'));
        });
    },
    [search, searchAfterMove],
  );

  const abortGrading = useCallback(() => {
    generationRef.current += 1;
    anchorRef.current = null;
    queuedDispatchRef.current = null;
    pendingReadyDispatchRef.current = null;
    if (stateRef.current === 'thinking') {
      workerRef.current?.postMessage('stop');
      stopPendingRef.current = true;
      stateRef.current = 'stopping';
    }
  }, []);

  const gradeMoveInner = useCallback(
    async (fen: string, playedMoveUci: string): Promise<GradeResult> => {
      const generation = generationRef.current;
      await anchorReadyRef.current;
      const anchor = anchorRef.current;
      const mover = sideToMoveFromFen(fen);

      const emptyLine: TrainEngineLine = { moves: [], evalCp: null, evalMate: null };

      if (!anchor || anchor.generation !== generation || anchor.fen !== fen) {
        // Defensive fallback (should not happen when startGrading was called
        // for this exact fen) — never crash the solve loop. Resolves the GOOD
        // tier (SEED-119): a defensive path must never silently cost the
        // user move points.
        return {
          moveTier: 'good',
          bestMoveUci: null,
          esBefore: 0.5,
          esAfter: 0.5,
          bestLine: emptyLine,
          playedLine: emptyLine,
        };
      }

      if (playedMoveUci === anchor.keyUci) {
        // D-01: playing the key (the engine's own top move on the legacy
        // path) is the GOOD tier with no second search. playedLine IS the key
        // line.
        return {
          moveTier: 'good',
          bestMoveUci: anchor.keyUci,
          esBefore: anchor.es,
          esAfter: anchor.es,
          bestLine: anchor.keyLine,
          playedLine: anchor.keyLine,
        };
      }

      const afterFen = fenAfterUciMove(fen, playedMoveUci);
      if (afterFen === null) {
        // Defensive fallback (illegal/unparseable played move — should not
        // happen for a real board interaction) — resolves the GOOD tier
        // (SEED-119), never silently costing the user move points.
        return {
          moveTier: 'good',
          bestMoveUci: anchor.keyUci,
          esBefore: anchor.es,
          esAfter: anchor.es,
          bestLine: anchor.keyLine,
          playedLine: anchor.keyLine,
        };
      }

      // D-01: ONE after-move search of the played move at the same budget as
      // the anchor, so the drop compares two same-horizon phone searches. The
      // PV is captured into playedLine; the clamp below (D-09) keeps the
      // displayed eval from reading better than the key line's.
      const afterRaw = await searchAfterMove(afterFen, generation, TRAIN_GRADING_MOVETIME_MS);
      const esAfter = evalToExpectedScore(afterRaw.evalCp, afterRaw.evalMate, mover);
      const severity = classifyLiveSeverity(anchor.es, esAfter);
      const moveTier = moveTierFromSeverity(severity);
      lastPlayedSearchRef.current = {
        generation,
        playedUci: playedMoveUci,
        es: esAfter,
        depth: afterRaw.depth,
      };
      const playedLine = clampLineEvalToBest(
        {
          moves: [playedMoveUci, ...afterRaw.pv],
          evalCp: afterRaw.evalCp,
          evalMate: afterRaw.evalMate,
        },
        anchor.keyLine,
        mover,
      );
      return {
        moveTier,
        bestMoveUci: anchor.keyUci,
        esBefore: anchor.es,
        esAfter,
        bestLine: anchor.keyLine,
        playedLine,
      };
    },
    [searchAfterMove],
  );

  // Bug fix (Phase 190-01 checkpoint): manual browser UAT hit an indefinite
  // "Checking your move…" hang (StrictMode double-invoke leaving no active
  // search for the current generation — see startGrading's effect-site fix
  // in TrainSolveScreen.tsx — plus, more generally, any wedged Worker).
  // gradeMoveInner alone has no ceiling on how long it can wait; this
  // wrapper races it against TRAIN_GRADING_TIMEOUT_MS so the promise ALWAYS
  // settles, surfacing a catchable error instead of hanging forever.
  const gradeMove = useCallback(
    (fen: string, playedMoveUci: string): Promise<GradeResult> =>
      raceWithTimeout(
        () => gradeMoveInner(fen, playedMoveUci),
        TRAIN_GRADING_TIMEOUT_MS,
        'Grading timed out',
        'Grading failed',
      ),
    [gradeMoveInner],
  );

  // Phase 235 (D-10/D-11/D-13/D-16/D-17): the disagreement re-check. Re-runs
  // BOTH after-move searches (key, then played) at TRAIN_RECHECK_MOVETIME_MS
  // with the raised node cap, SEQUENTIALLY (single-threaded WASM), and grades
  // them with the same classifyLiveSeverity as the 1.5 s pair. The result
  // replaces the 1.5 s grade whatever it says (D-11). Resolves null when there
  // is nothing coherent to re-check (anchor mismatch, legacy anchor, played ==
  // key, no recorded 1.5 s played search, illegal after-move FEN).
  const recheckMoveInner = useCallback(
    async (
      fen: string,
      playedMoveUci: string,
      generation: number,
      signal: AbortSignal,
    ): Promise<RecheckInnerResult | null> => {
      const plan = planRecheck(
        fen,
        playedMoveUci,
        generation,
        anchorRef.current,
        lastPlayedSearchRef.current,
      );
      if (plan === null) return null;

      const keyRaw = await searchAfterMove(
        plan.afterKeyFen,
        generation,
        TRAIN_RECHECK_MOVETIME_MS,
        TRAIN_RECHECK_MAX_NODES,
      );
      // Bug fix (review WR-01): recheckMove's timeout only rejects the race, it
      // does not stop this async function. A key search landing just AFTER the
      // timeout used to fall through to the played search, which kept the engine
      // busy for up to 3 s and could collide with the reveal's own search. The
      // timeout aborts `signal`, so a timed-out re-check never dispatches its
      // second search. (The generation check below cannot catch it: a timeout
      // does not bump the generation, because the anchor must stay valid for the
      // reveal.)
      if (signal.aborted) return null;
      const playedRaw = await searchAfterMove(
        plan.afterPlayedFen,
        generation,
        TRAIN_RECHECK_MOVETIME_MS,
        TRAIN_RECHECK_MAX_NODES,
      );
      // A puzzle change (or abort) while the searches ran: nothing to report.
      if (generation !== generationRef.current) return null;
      return finishRecheck(plan, keyRaw, playedRaw);
    },
    [searchAfterMove],
  );

  // D-20: races recheckMoveInner against TRAIN_RECHECK_TIMEOUT_MS with the same
  // settle-once race as gradeMove, but NEVER rejects: a timeout, an engine
  // error or an unusable state all resolve null and the caller keeps the 1.5 s
  // grade with no record. The anchor is swapped only in the success branch, so
  // a re-check that lost the race (or errored) never changes what the reveal shows.
  const recheckMove = useCallback(
    (fen: string, playedMoveUci: string): Promise<RecheckResult | null> => {
      const generation = generationRef.current;
      return raceWithTimeout(
        (signal) => recheckMoveInner(fen, playedMoveUci, generation, signal),
        TRAIN_RECHECK_TIMEOUT_MS,
        'Re-check timed out',
        'Re-check failed',
      ).then(
        (inner) => {
          if (inner === null) return null;
          if (generation === generationRef.current) anchorRef.current = inner.anchor;
          return inner.result;
        },
        () => null,
      );
    },
    [recheckMoveInner],
  );

  // 190.1-01, D-01 point 3 / Task 2 (honest states + cancellation safety):
  // the reveal-time "played in game" search — one new lazy search per
  // puzzle, dispatched only when the reveal opens (the caller supplies the
  // game move as UCI, obtained from the reveal GET). Reuses generationRef
  // (captured at call time) as the SAME cancellation authority as
  // startGrading/gradeMove — no second counter (190.1-RESEARCH Pitfall 2).
  //
  // Races the underlying search against TRAIN_GRADING_TIMEOUT_MS through the
  // same settle-once `raceWithTimeout` gradeMove uses, so the
  // promise ALWAYS settles — a wedged Worker yields a stated failure, never
  // an unbounded spinner. Before resolving, the captured generation is
  // compared against generationRef.current: a result computed for a
  // previous puzzle (the caller started a new one, or aborted, while this
  // search was in flight) rejects instead of resolving — it must never
  // become observable to the caller.
  const startGameMoveSearch = useCallback(
    (puzzleFen: string, gameMoveUci: string): Promise<TrainEngineLine> => {
      const generation = generationRef.current;
      if (hasErrorRef.current) {
        return Promise.reject(new Error('Grading engine failed to load'));
      }
      const afterFen = fenAfterUciMove(puzzleFen, gameMoveUci);
      if (afterFen === null) {
        return Promise.reject(new Error('Illegal or malformed game move'));
      }
      // Phase 235 (D-09): a game move equal to the key reuses the key line with
      // no search. (The anchor's own search is rooted at the AFTER-KEY fen, so
      // an exact-UCI rank lookup there could match the opponent's reply.) The
      // anchor is guaranteed settled here in practice (the reveal only opens
      // after gradeMove resolved, which awaited it); the fen/generation guard
      // is purely defensive.
      const anchor = anchorRef.current;
      const anchorMatches =
        anchor !== null && anchor.generation === generation && anchor.fen === puzzleFen;
      if (anchorMatches && gameMoveUci === anchor.keyUci) {
        return Promise.resolve(anchor.keyLine);
      }
      return raceWithTimeout(
        async () => {
          const raw = await searchAfterMove(afterFen, generation, TRAIN_GRADING_MOVETIME_MS);
          if (generation !== generationRef.current) {
            throw new Error('Reveal search superseded by a newer puzzle');
          }
          const line: TrainEngineLine = {
            moves: [gameMoveUci, ...raw.pv],
            evalCp: raw.evalCp,
            evalMate: raw.evalMate,
          };
          // Display backstop, same rationale as gradeMove's clamp (D-09) — a
          // game move whose after-move search reads better than the key line
          // must not be DISPLAYED contradicting the "best move" label.
          // D-16: after a CONFIRMED re-check the anchor is unclamped, so the
          // game line shows the phone's honest eval.
          return anchorMatches && !anchor.unclamped
            ? clampLineEvalToBest(line, anchor.keyLine, sideToMoveFromFen(puzzleFen))
            : line;
        },
        TRAIN_GRADING_TIMEOUT_MS,
        'Reveal search timed out',
        'Reveal search failed',
      );
    },
    [searchAfterMove],
  );

  return {
    isReady,
    hasError,
    startGrading,
    abortGrading,
    restartEngine,
    gradeMove,
    startGameMoveSearch,
    recheckMove,
  };
}
