/**
 * useFlawChessEngine — React hook driving the frozen `SearchRunner`
 * (`mctsSearch`) against the real providers (`createWorkerPool()` +
 * `createMaiaQueue()`), exposing a live-refining ranked-lines snapshot.
 *
 * This is the anytime-emit engine behind the live ranked-lines card: `mctsSearch`'s
 * `onSnapshot` fires after every completed backup; the hook throttles those
 * commits into React state at a fixed ~150ms cadence WITHOUT delaying the
 * first paint (a throttle, not a debounce — see the onSnapshot throttle
 * section below).
 */

import { useRef, useState, useCallback, useEffect } from 'react';
import * as Sentry from '@sentry/react';
import { isReportedMaiaWorkerError } from '@/lib/maiaWorkerErrors';
import { mctsSearch } from '@/lib/engine/mctsSearch';
import { createWorkerPool, computePoolSize, type WorkerPool } from '@/lib/engine/workerPool';
import { createMaiaQueue, type MaiaQueue } from '@/lib/engine/maiaQueue';
import { DEFAULT_POLICY_TEMPERATURE } from '@/lib/engine/policyTemperature';
import type { EngineSnapshot, SearchBudget, EngineProviders, RankedLine } from '@/lib/engine/types';

// ─── Constants ───────────────────────────────────────────────────────────────

/**
 * Rapid-step FEN-navigation debounce window (ms) AND the onSnapshot throttle
 * window (ms) — the SAME value, reused for two DISTINCT mechanisms:
 * one debounces navigation input, the other throttles snapshot output. Do
 * not conflate the two; see the onSnapshot throttle below.
 */
const RAPID_STEP_DEBOUNCE_MS = 150;

/**
 * Node-expansion budget cap (one node = one expansion event). Tunable —
 * revisit after real-device mobile-memory testing.
 */
const FLAWCHESS_ENGINE_MAX_NODES = 400;

/**
 * Search-tree ply depth cap. Must stay in the locked [6,10] band —
 * do not change this without revisiting the milestone's ply-depth lock.
 */
const FLAWCHESS_ENGINE_MAX_PLIES = 8;

// ─── Bot-play budget ────────────────────────────────────────────
//
// ADDITIVE profile for clocked bot games — sits ALONGSIDE the analysis-board
// constants above, never replacing them: retuning FLAWCHESS_ENGINE_MAX_NODES
// in place would silently degrade the live /analysis engine card, an unrelated
// regression. The values themselves live in the dependency-light
// `@/lib/engine/botBudget` so the calibration harness imports the SAME
// definition instead of hand-maintaining a mirror (a divergence would
// calibrate a bot that does not ship); re-exported here for
// useFlawChessEngine.test.tsx only, app code imports `@/lib/engine/botBudget` directly.
export {
  FLAWCHESS_BOT_MAX_NODES,
  FLAWCHESS_BOT_MAX_PLIES,
  FLAWCHESS_BOT_CONCURRENCY,
  FLAWCHESS_BOT_STOP_RULE,
} from '@/lib/engine/botBudget';
import { FLAWCHESS_DISPATCH_MODE } from '@/lib/engine/botBudget';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface UseFlawChessEngineOptions {
  /** Current board position. null keeps the engine idle (no search sent). */
  fen: string | null;
  /** When false, the WorkerPool/MaiaQueue are not created and no search runs. */
  enabled: boolean;
  /**
   * Shared per-side ELO for the practical model:
   * `budget.elo = { w: elo, b: elo }`. Free analysis does not model a
   * self/opponent asymmetry.
   */
  elo: number;
  /**
   * Reshapes the root-mover's-own-side Maia
   * policy before search. Omitted defaults to `DEFAULT_POLICY_TEMPERATURE`
   * (a true no-op) at THIS call site — kept visible here, not hidden inside
   * `mctsSearch`, so the search-orchestrator layer's no-op short-circuit
   * stays legible from the hook's own call site.
   */
  policyTemperature?: number;
  /**
   * Root-only UCI moves (never SANs)
   * unioned with Maia's top-k at the root. Omitted or `undefined` produces a
   * `SearchBudget.extraRootMoves` of `undefined`, which leaves the search unchanged.
   * This field is in the search-trigger effect's dependency array below, so
   * an identity change aborts the in-flight search and starts a fresh one —
   * the CALLER owns referential stability (see `Analysis.tsx`'s
   * `NO_EXTRA_ROOT_MOVES` sentinel); this hook deliberately performs no
   * content comparison or debouncing of its own.
   */
  extraRootMoves?: string[];
}

export interface FlawChessEngineState {
  /** Top ranked root candidates, pre-sorted descending by practicalScore. */
  rankedLines: RankedLine[];
  /** Count of expansion events consumed by the current/last search. */
  nodesEvaluated: number;
  /** True once maxNodes/maxPlies stopped the search (not an abort). */
  budgetExhausted: boolean;
  /** True while a search is in flight for the current position. */
  isSearching: boolean;
  /**
   * True once BOTH engine providers' underlying workers have
   * finished loading their assets and are ready to serve — not merely once
   * `createWorkerPool()`/`createMaiaQueue()` have been constructed. This
   * hook's `isReady` has exactly ONE consumer in the codebase
   * (`Analysis.tsx`'s `flawChessLoading`), so it is rewired in place rather
   * than adding a parallel `assetsReady` value — a second signal would leave
   * this one permanently dishonest for no risk reduction.
   */
  isReady: boolean;
  /**
   * The FEN `rankedLines` was most
   * recently reset/committed for. Set in the SAME effect (and same render)
   * that clears `snapshot` to `INITIAL_SNAPSHOT` on every `fen` change, so it
   * lags `fen` by exactly the same one render `rankedLines` does — letting a
   * consumer distinguish "rankedLines genuinely belongs to the current
   * position" from "rankedLines is a stale closure value from the previous
   * position, captured in the same passive-effect flush as this hook's own
   * FEN-reset effect." Consumers must NOT trust `rankedLines` for a given
   * FEN unless `currentFen === thatFen`.
   */
  currentFen: string | null;
}

const INITIAL_SNAPSHOT: EngineSnapshot = {
  rankedLines: [],
  nodesEvaluated: 0,
  budgetExhausted: false,
  stopReason: null,
};

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useFlawChessEngine({
  fen,
  enabled,
  elo,
  policyTemperature,
  extraRootMoves,
}: UseFlawChessEngineOptions): FlawChessEngineState {
  // ─── Refs ──────────────────────────────────────────────────────────────────

  const poolRef = useRef<WorkerPool | null>(null);
  const queueRef = useRef<MaiaQueue | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  /** Timestamp (ms) of the last FEN change — drives the adaptive debounce. */
  const lastFenChangeAtRef = useRef(0);

  /** Timestamp (ms) of the last onSnapshot commit — drives the throttle. */
  const lastCommitAtRef = useRef(0);
  /** Pending trailing-commit timer for the onSnapshot throttle, or null when idle. */
  const pendingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ─── State ─────────────────────────────────────────────────────────────────

  const [isReady, setIsReady] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [snapshot, setSnapshot] = useState<EngineSnapshot>(INITIAL_SNAPSHOT);
  /** The FEN `snapshot.rankedLines` currently belongs to. */
  const [currentFen, setCurrentFen] = useState<string | null>(null);

  // ─── Provider lifecycle — created once per enabled-lifetime ──────────────
  //
  // Mirrors useStockfishEngine's Worker-lifecycle effect gated on `enabled`:
  // the WorkerPool + MaiaQueue are created ONCE while the switch is ON and
  // terminated on cleanup — never recreated per FEN (that would break the
  // lazy-spawn-once + FEN cache).

  useEffect(() => {
    if (!enabled) return;
    const pool = createWorkerPool();
    const queue = createMaiaQueue();
    poolRef.current = pool;
    queueRef.current = queue;

    // isReady must reflect real asset readiness, not merely
    // that the pool/queue objects were constructed. Await BOTH providers —
    // unlike bot play (whose per-persona asymmetry does NOT apply on
    // this surface), the FlawChess Engine card always runs mctsSearch over
    // BOTH providers.policy (Maia) AND providers.grade (Stockfish), so both
    // assets are genuinely required before the card can search.
    //
    // Note: awaiting whenReady() here spawns both providers at enable time
    // rather than on the first grade()/policy() call — this is not a new
    // cost, because the search-trigger effect below fires for the current
    // FEN on this same render pass and would have spawned them immediately
    // anyway.
    let cancelled = false;
    void Promise.allSettled([queue.whenReady(), pool.whenReady()]).then(([maia, stockfish]) => {
      // Bug fix (FLAWCHESS-A1): the old `.catch()` captured to Sentry
      // UNCONDITIONALLY, without the `cancelled` guard the `setIsReady` calls
      // already had. Navigating away from /analysis before Maia's model
      // finished downloading (slow mobile connections — the model is ~226 MB
      // of heap) tears the queue down via `terminate()` -> `lease.release()`
      // -> `resetModuleState()`, which REJECTS every pending `whenReady()`
      // waiter with 'Maia worker terminated'. That teardown rejection then
      // landed in Sentry as a provider failure even though nothing was
      // broken (the reported event's `url` was the page the user had already
      // navigated TO). `WorkerPool.terminate()` deliberately RESOLVES its
      // waiters instead, so only the Maia side produced these; the guard
      // below covers both, whichever teardown path settles first.
      if (cancelled) return;

      // A dead worker (whenReady() rejects) must not leave the card behind a
      // permanent loading skeleton — capture once, then fall through to the
      // card's normal empty rendering by still flipping isReady true.
      const failures: { name: string; reason: unknown }[] = [];
      if (maia.status === 'rejected') failures.push({ name: 'maia', reason: maia.reason });
      if (stockfish.status === 'rejected')
        failures.push({ name: 'stockfish', reason: stockfish.reason });
      // Dedupe (FLAWCHESS-A3): a Maia rejection carrying a `MaiaWorkerError`
      // was already captured by the worker host (with the raw text, backend
      // and device context) — re-reporting it here made one OOM cold start
      // show up as three Sentry issues. Only a failure nobody has reported
      // yet earns a capture from this site.
      const first = failures.find((f) => !isReportedMaiaWorkerError(f.reason));
      if (first) {
        // Fixed, variable-free message string (Sentry grouping rule); which
        // provider died and why goes in `cause` + `extra`, not the message —
        // without it a genuine asset failure was indistinguishable from the
        // benign teardown above.
        Sentry.captureException(
          new Error('FlawChess engine: a provider failed to become ready', { cause: first.reason }),
          {
            tags: { source: 'flawchess-engine' },
            extra: {
              failedProviders: failures.map((f) => f.name).join(','),
              reasons: failures.map((f) => `${f.name}: ${String(f.reason)}`).join(' | '),
            },
          },
        );
      }
      setIsReady(true);
    });

    return () => {
      cancelled = true;
      pool.terminate();
      queue.terminate();
      poolRef.current = null;
      queueRef.current = null;
      setIsReady(false);
      setIsSearching(false);
    };
  }, [enabled]); // re-run only if enabled toggles

  // ─── Adaptive debounce on FEN navigation ───────────────────────

  const [debouncedFen, setDebouncedFen] = useState<string | null>(null);
  useEffect(() => {
    // Bug fix: abort the OLD search's controller
    // and cancel any pending trailing onSnapshot commit HERE, not only in
    // the debounced search-trigger effect below (up to RAPID_STEP_DEBOUNCE_MS
    // later on the rapid path) or the abort-on-disable cleanup. Without this,
    // the old search kept running and its onSnapshot throttle's
    // pendingTimerRef could still fire a trailing commit of the OLD
    // position's snapshot AFTER setSnapshot(INITIAL_SNAPSHOT) below had
    // already cleared it for the new position. Deliberately minimal: no
    // `pool.stopAll()` call here — the abort signal already reaches
    // providers.grade, and an extra stop would also arm the pool's
    // stop-watchdogs; `lastCommitAtRef` is left
    // alone, owned by the search-trigger effect below, which already resets it.
    abortControllerRef.current?.abort();
    if (pendingTimerRef.current) {
      clearTimeout(pendingTimerRef.current);
      pendingTimerRef.current = null;
    }

    // Drop the previous position's lines immediately so the card never shows
    // orphaned rankedLines from the prior ply while the new search spins up
    // (mirrors useStockfishEngine's identical FEN-effect clearing behavior).
    setSnapshot(INITIAL_SNAPSHOT);
    // Committed in the SAME effect run as the
    // `snapshot` reset above, so `currentFen` lags `fen` by exactly the same
    // one render that `snapshot.rankedLines` does — see useStockfishEngine's
    // identical `currentFen` field for the full rationale.
    setCurrentFen(fen);
    if (fen === null) {
      setDebouncedFen(null);
      return;
    }
    const now = Date.now();
    const sinceLast = now - lastFenChangeAtRef.current;
    lastFenChangeAtRef.current = now;
    if (sinceLast > RAPID_STEP_DEBOUNCE_MS) {
      // Settled move: fire immediately so the first line paints near-instantly.
      setDebouncedFen(fen);
      return;
    }
    // Rapid succession (held arrow-key auto-repeat): coalesce via debounce.
    const timer = setTimeout(() => setDebouncedFen(fen), RAPID_STEP_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [fen]);

  // ─── onSnapshot throttle (NOT a debounce) ───────────────────────────────────
  //
  // Commit immediately if the last commit was more than RAPID_STEP_DEBOUNCE_MS
  // ago (this is what makes the FIRST snapshot of every search paint near-
  // instantly); otherwise schedule exactly one trailing commit of the LATEST
  // snapshot, clearing any previously scheduled one. A plain debounce here
  // would delay first paint, which must appear immediately.
  const handleSnapshot = useCallback((next: EngineSnapshot) => {
    const now = Date.now();
    const sinceLast = now - lastCommitAtRef.current;
    if (pendingTimerRef.current) {
      clearTimeout(pendingTimerRef.current);
      pendingTimerRef.current = null;
    }
    if (sinceLast > RAPID_STEP_DEBOUNCE_MS) {
      lastCommitAtRef.current = now;
      setSnapshot(next);
      return;
    }
    pendingTimerRef.current = setTimeout(() => {
      pendingTimerRef.current = null;
      lastCommitAtRef.current = Date.now();
      setSnapshot(next);
    }, RAPID_STEP_DEBOUNCE_MS - sinceLast);
  }, []); // stable — only accesses refs and a stable state setter

  // ─── Debounced FEN → mctsSearch ─────────────────────────────────────────────

  useEffect(() => {
    const pool = poolRef.current;
    const queue = queueRef.current;
    if (!debouncedFen || !enabled || !pool || !queue) return;

    // dispatchExpansion forwards this signal into BOTH providers.grade()'s
    // and providers.policy()'s signal parameter, so the
    // abort() below already reaches WorkerPool.grade's dequeue/stop handling
    // AND maiaQueue.policy()'s own not-yet-dispatched-request drop on its
    // own. The explicit pool.stopAll() call is kept as redundant, idempotent
    // defense in depth (not removed — that's out of scope here), not because
    // it is still load-bearing. maiaQueue still has no stopAll: an in-flight
    // ONNX inference cannot be interrupted, and a stale resolution for an
    // already-dispatched request is unused and harmless once this search's
    // result is discarded.
    abortControllerRef.current?.abort();
    pool.stopAll();

    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Reset the onSnapshot throttle so the FIRST snapshot of this fresh
    // search always commits immediately, regardless of the previous search's
    // throttle state (first-paint guarantee).
    if (pendingTimerRef.current) {
      clearTimeout(pendingTimerRef.current);
      pendingTimerRef.current = null;
    }
    lastCommitAtRef.current = 0;

    const budget: SearchBudget = {
      maxNodes: FLAWCHESS_ENGINE_MAX_NODES,
      maxPlies: FLAWCHESS_ENGINE_MAX_PLIES,
      concurrency: computePoolSize(),
      // Both colors share the single on-page ELO in free analysis (no
      // self/opponent asymmetry).
      elo: { w: elo, b: elo },
      // Threaded straight through from this hook's own options; stays
      // `undefined` when the caller passes none, which leaves the search unchanged.
      extraRootMoves,
      // Defaulted at THIS call site (not
      // inside mctsSearch) so the no-op short-circuit stays visible at the
      // orchestrator layer.
      policyTemperature: policyTemperature ?? DEFAULT_POLICY_TEMPERATURE,
      // The shared dispatch-mode constant, same one the bot budget carries.
      dispatchMode: FLAWCHESS_DISPATCH_MODE,
    };
    // The analysis board splits the root exactly
    // like the harness — gradeRoot fans the root's one grade call across
    // whatever slots are idle at call time; every other leaf, and every
    // provider without gradeRoot, uses the plain
    // grade() path (mctsSearch.ts's dispatchExpansion routing).
    const providers: EngineProviders = {
      policy: queue.policy,
      grade: pool.grade,
      gradeRoot: pool.gradeRoot,
    };

    setIsSearching(true);
    void mctsSearch(debouncedFen, budget, providers, handleSnapshot, controller.signal)
      .then((finalSnapshot) => {
        if (controller.signal.aborted) return;
        if (pendingTimerRef.current) {
          clearTimeout(pendingTimerRef.current);
          pendingTimerRef.current = null;
        }
        lastCommitAtRef.current = Date.now();
        setSnapshot(finalSnapshot);
        setIsSearching(false);
      })
      .catch((err: unknown) => {
        // A rejection (worker crash, or grade()/policy() throwing after a
        // concurrent state change tore down the pool/queue) must not become
        // an unhandled promise rejection nor leave isSearching stuck true.
        if (controller.signal.aborted) return;
        Sentry.captureException(err, { tags: { source: 'flawchess-engine' } });
        setIsSearching(false);
      });
  }, [debouncedFen, enabled, elo, policyTemperature, extraRootMoves, handleSnapshot]);

  // ─── Abort-on-disable guard ─────────────────────────────────────────────────
  //
  // The search-trigger effect above only calls abortControllerRef.current
  // ?.abort() at the TOP of its guarded body, which is skipped whenever the
  // guard (`!debouncedFen || !enabled || !pool || !queue`) fails — e.g. when
  // `enabled` flips to false without a FEN change. Without this cleanup, a
  // stale in-flight search's callbacks could still fire (controller.signal
  // .aborted would remain false) and call setSnapshot/setIsSearching after
  // the engine was disabled. This effect's cleanup always runs on the next
  // dep change AND on unmount, regardless of whether the guard above passes.
  useEffect(() => {
    return () => abortControllerRef.current?.abort();
  }, [debouncedFen, enabled]);

  // ─── Unmount cleanup ────────────────────────────────────────────────────────
  //
  // The provider-lifecycle effect's own cleanup already terminates the pool
  // and queue (which resolves every in-flight promise so mctsSearch's awaits
  // settle without hanging); this additionally aborts the outstanding
  // AbortController and clears any pending throttle timer on unmount.
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      if (pendingTimerRef.current) clearTimeout(pendingTimerRef.current);
    };
  }, []); // stable refs — no deps required

  // ─── Return ────────────────────────────────────────────────────────────────

  return {
    rankedLines: snapshot.rankedLines,
    nodesEvaluated: snapshot.nodesEvaluated,
    budgetExhausted: snapshot.budgetExhausted,
    isSearching,
    isReady,
    currentFen,
  };
}
