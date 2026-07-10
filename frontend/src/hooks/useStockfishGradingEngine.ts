/**
 * useStockfishGradingEngine — a SECOND, fully independent Stockfish WASM Web
 * Worker instance that grades a shown set of Maia candidate moves via ONE
 * `searchmoves`-restricted MultiPV root search, streaming progressive `info`
 * lines into a per-FEN, pv[0]-keyed grade cache.
 *
 * Structural sibling of useStockfishEngine.ts (same ENGINE_PATH, same
 * idle/thinking/stopping state machine, same stop-before-go serialization,
 * same tab-hide pause / unmount cleanup) — but a SEPARATE Worker instance with
 * a SEPARATE UCI configuration. It never imports, mutates, or reads
 * useStockfishEngine's state (SC3 isolation — "without disturbing the primary
 * eval bar / engine card").
 *
 * Load-bearing caveats confirmed by Plan 01's real-binary spike
 * (151.1-01-SUMMARY.md):
 *  1. Key the grade map by `pv[0]` (the move), NEVER by the `multipv` index —
 *     multipv is an EVAL RANK that reorders as depth climbs, not a stable
 *     move identity (Pitfall 1).
 *  2. Pass ONLY legal UCI candidates to `searchmoves` — the engine silently
 *     drops illegal entries, under-counting MultiPV lines (Caveat 1).
 *
 * Grades are position-only (ELO-independent) and cacheable per (FEN, SAN);
 * only the DISPLAYED candidate subset changes with the ELO slider (Pitfall
 * 2) — dragging it must not re-issue a search when every newly-shown SAN is
 * already graded for the current FEN.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Chess } from 'chess.js';
import { parseInfoLine } from './uciParser';
import { sanToUci, uciToSquares } from '@/lib/sanToSquares';
import type { MoveGrade } from '@/lib/moveQuality';

// ─── Constants (SC4 degradation knobs — tunable without touching logic) ──────

/** Path to the vendored Stockfish engine served from public/engine/. Same binary as the primary worker, a SEPARATE Worker() load. */
const ENGINE_PATH = '/engine/stockfish-18-lite-single.js';

/**
 * Wall-clock cap (ms) — the grading run's ONLY search-termination clause, no
 * depth cap (mirrors useStockfishEngine's movetime-only convention). Value
 * measured via a headless Node WASM sweep (Phase 158 Plan 01, SEED-087): at
 * movetime=4000 on both a middlegame and an endgame position, the grading
 * run's depth for a candidate-union size of 6-8 reaches parity with (or
 * exceeds) the free run's depth at its existing MOVETIME_MS=1500/MULTIPV=2
 * budget, and a shared candidate's eval agrees with the free run's eval for
 * that same move within noise (2cp and 23cp deltas on the two test
 * positions — see 158-01-SUMMARY.md for the full depth-per-config table).
 * Replaces the prior depth-14/movetime-2500 cap, which the seed's live UAT
 * confirmed was the source of the cross-card eval skew this phase fixes.
 */
const GRADING_MOVETIME_SAFETY_CAP_MS = 4000;

/** Per-FEN grade-cache cap (mirrors useMaiaEngine's MAIA_CACHE_MAX FIFO pattern). */
const GRADE_CACHE_MAX = 256;

/** Rapid-step debounce window (ms): coalesces a held ELO-slider drag / arrow-key auto-repeat to one search. */
const RAPID_STEP_DEBOUNCE_MS = 150;

// ─── Types ───────────────────────────────────────────────────────────────────

/** Internal UCI state machine states — mirrors useStockfishEngine's EngineState. */
type EngineState = 'idle' | 'thinking' | 'stopping';

export interface UseStockfishGradingEngineOptions {
  /** Current board position. null keeps the grading worker idle (no go sent). */
  fen: string | null;
  /** The candidate SANs to grade/display for the current position (Plan 02's selectCandidatesByMass output). */
  candidateSans: string[];
  /** When false the Worker is not created and grading does not run. */
  enabled: boolean;
}

export interface StockfishGradingEngineState {
  /** pv[0]-derived-SAN-keyed grades for the currently requested candidateSans, white-POV normalized. */
  gradeMap: Map<string, MoveGrade>;
  /** True while a (non-cached) grading search is in flight for the current FEN. */
  isGrading: boolean;
  /** True once the UCI init sequence completes (uciok + readyok). */
  isReady: boolean;
}

/** A settled (fen, candidateSans) pair ready to be graded — set by the debounce effect. */
interface GradingRequest {
  fen: string;
  candidateSans: string[];
}

// ─── Local UCI→SAN replay helper ──────────────────────────────────────────────

/**
 * Convert a UCI move string (pv[0] from a grading info line) back to its SAN
 * relative to `baseFen`. Mirrors Analysis.tsx's `bestSanFromPv` logic — kept
 * as a private local helper here (rather than importing from a page) since
 * hooks must not depend on page-level modules.
 */
function sanFromUci(baseFen: string, uci: string): string | null {
  const squares = uciToSquares(uci);
  if (!squares) return null;
  try {
    const chess = new Chess(baseFen);
    const move = chess.move({
      from: squares.from,
      to: squares.to,
      promotion: uci.length > 4 ? uci[4] : undefined,
    });
    return move.san;
  } catch {
    return null;
  }
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useStockfishGradingEngine({
  fen,
  candidateSans,
  enabled,
}: UseStockfishGradingEngineOptions): StockfishGradingEngineState {
  // ─── Refs ──────────────────────────────────────────────────────────────────

  const workerRef = useRef<Worker | null>(null);

  /** Internal UCI state machine — mutated from the onmessage handler (no re-render). */
  const stateRef = useRef<EngineState>('idle');

  /** Stale-eval guard (mirrors useStockfishEngine's Pitfall 3 stopPendingRef). */
  const stopPendingRef = useRef(false);

  /** Ref-for-latest-value: the current fen/candidateSans/isReady props, visible inside callbacks. */
  const currentFenRef = useRef<string | null>(null);
  const candidateSansRef = useRef<string[]>([]);
  const isReadyRef = useRef(false);

  /** Per-FEN grade cache: Map<fen, Map<san, MoveGrade>> — ephemeral, board-session-scoped FIFO (mirrors useMaiaEngine's MAIA_CACHE_MAX). */
  const cacheRef = useRef<Map<string, Map<string, MoveGrade>>>(new Map());

  /** The FEN + side-to-move of the search currently in flight, set when a go is sent. */
  const gradingFenRef = useRef<string | null>(null);
  const gradingSideRef = useRef<'w' | 'b'>('w');

  /** Timestamp of the last (fen, candidateSans) change, for the adaptive debounce. */
  const lastChangeAtRef = useRef(0);

  /** Previous fen value, used to detect an actual FEN change (vs. a candidateSans-only change) so the displayed gradeMap is only cleared on real navigation (D-05), not on an ELO-drag candidate-set change (Pitfall 2). */
  const prevFenRef = useRef<string | null>(null);

  // ─── State ─────────────────────────────────────────────────────────────────

  const [isReady, setIsReady] = useState(false);
  const [isGrading, setIsGrading] = useState(false);
  const [gradeMap, setGradeMap] = useState<Map<string, MoveGrade>>(new Map());
  const [debouncedRequest, setDebouncedRequest] = useState<GradingRequest | null>(null);

  // ─── Ref sync (ref-for-latest-value) ───────────────────────────────────────

  useEffect(() => {
    currentFenRef.current = fen;
    candidateSansRef.current = candidateSans;
    isReadyRef.current = isReady;
  });

  // ─── Shared helper: commit the cache's view of `candidateSans` for `fenKey` to state ──

  /**
   * Reads refs/stable setState only (no props/state closures), so it stays
   * correct even though `prepareSearch` (a stable useCallback([])) captures
   * whichever render's copy of this function first.
   */
  function commitDisplayedGradeMap(fenKey: string, sans: string[]): void {
    const cache = cacheRef.current.get(fenKey);
    const displayed = new Map<string, MoveGrade>();
    if (cache) {
      for (const san of sans) {
        const grade = cache.get(san);
        if (grade) displayed.set(san, grade);
      }
    }
    setGradeMap(displayed);
  }

  // ─── Candidate-set stable dependency key ───────────────────────────────────

  // useMemo gives the debounce effect a stable primitive to depend on instead
  // of the candidateSans array reference (which may change identity every
  // render even when its contents are the same).
  const candidatesKey = useMemo(() => [...candidateSans].sort().join('|'), [candidateSans]);

  // ─── Prepare / send a grading search ───────────────────────────────────────

  /**
   * Sends setoption+position+go for (fenToGrade, candidateSans), or serves a
   * pure cache hit with no worker round-trip (Pitfall 2). Carries over
   * useStockfishEngine's idle/thinking/stopping + stopPendingRef serialization
   * verbatim (Pitfall 5 / FLAWCHESS-7V guard) — stable (empty deps) so it can
   * be called from the worker's bestmove handler and the tab-visibility
   * handler without stale-closure issues.
   */
  const prepareSearch = useCallback((fenToGrade: string, sans: string[]) => {
    const worker = workerRef.current;
    if (!worker || !isReadyRef.current || sans.length === 0) return;

    if (stateRef.current === 'thinking') {
      // Mid-search: stop it; the go is re-sent once the stale bestmove arrives
      // (see the worker's bestmove handler below).
      worker.postMessage('stop');
      stopPendingRef.current = true;
      stateRef.current = 'stopping';
      return;
    }

    if (stateRef.current === 'stopping') {
      // FLAWCHESS-7V guard: a stop is already in flight. Sending position+go
      // now would race it and trap the single-thread WASM engine. Do nothing —
      // the bestmove handler re-triggers prepareSearch with the LATEST
      // fen/candidateSans once the stale bestmove arrives.
      return;
    }

    const cache = cacheRef.current.get(fenToGrade);
    const ungraded = sans.filter((san) => !cache?.has(san));
    if (ungraded.length === 0) {
      // Pitfall 2: every requested SAN is already graded for this FEN (typical
      // of an ELO-slider drag that only changes the displayed subset) — serve
      // from cache, no new go.
      commitDisplayedGradeMap(fenToGrade, sans);
      return;
    }

    // Search over the UNION of already-graded + newly-needed SANs for one
    // coherent MultiPV ranking (rather than only the ungraded subset).
    const allSans = Array.from(new Set([...(cache?.keys() ?? []), ...sans]));
    const candidateUcis = allSans
      .map((san) => sanToUci(fenToGrade, san))
      .filter((uci): uci is string => uci !== null);
    if (candidateUcis.length === 0) return;

    gradingFenRef.current = fenToGrade;
    gradingSideRef.current = fenToGrade.split(' ')[1] === 'b' ? 'b' : 'w';

    worker.postMessage(`setoption name MultiPV value ${candidateUcis.length}`);
    worker.postMessage(`position fen ${fenToGrade}`);
    // Bug fix (Rule 1, found during Phase 158 Plan 01's headless measurement):
    // `searchmoves` MUST be the LAST clause in the go command on this WASM
    // build — everything after it is silently swallowed into the move list
    // (the engine's documented "illegal searchmoves are silently dropped"
    // behavior also drops trailing keywords like `movetime`, since they get
    // parsed as bogus move tokens). The prior `go depth … searchmoves … movetime …`
    // ordering meant movetime was NEVER actually limiting the search — only
    // the depth clause terminated it. Movetime now correctly caps the search.
    worker.postMessage(
      `go movetime ${GRADING_MOVETIME_SAFETY_CAP_MS} searchmoves ${candidateUcis.join(' ')}`,
    );
    stateRef.current = 'thinking';
    setIsGrading(true);
  }, []); // stable — only accesses refs and stable state setters

  /**
   * Ref holding prepareSearch, used inside the Worker lifetime and visibility
   * effects to avoid adding it to their deps arrays. prepareSearch is a stable
   * useCallback([]) so capturing it once (mirrors useStockfishEngine's
   * analyzeRef pattern) is safe for the component's lifetime.
   */
  const prepareSearchRef = useRef(prepareSearch);

  // ─── Debounce (fen, candidateSans) changes ─────────────────────────────────

  useEffect(() => {
    const fenChanged = fen !== prevFenRef.current;
    prevFenRef.current = fen;
    if (fenChanged) {
      // D-05: a new board navigation cancels the in-flight grade immediately —
      // the displayed gradeMap must never show the PREVIOUS position's colors.
      // A candidateSans-only change (ELO drag, same fen) must NOT clear it —
      // that's exactly Pitfall 2's re-search-avoidance case.
      setGradeMap(new Map());
    }

    const sans = candidateSansRef.current;
    if (fen === null || sans.length === 0) {
      setDebouncedRequest(null);
      return;
    }

    const now = Date.now();
    const sinceLast = now - lastChangeAtRef.current;
    lastChangeAtRef.current = now;
    const request: GradingRequest = { fen, candidateSans: sans };

    if (sinceLast > RAPID_STEP_DEBOUNCE_MS) {
      // Settled — fire immediately.
      setDebouncedRequest(request);
      return;
    }
    // Rapid succession (held ELO-slider drag / arrow-key auto-repeat):
    // coalesce via debounce so a storm of changes produces only one search.
    const timer = setTimeout(() => setDebouncedRequest(request), RAPID_STEP_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [fen, candidatesKey]);

  // ─── Worker lifecycle ──────────────────────────────────────────────────────

  useEffect(() => {
    if (!enabled) return;

    // Classic (non-module) Worker — same vendored Emscripten glue as the
    // primary engine, a SEPARATE instance (SC3 isolation).
    const worker = new Worker(ENGINE_PATH);
    workerRef.current = worker;

    /** Handle a single UCI line emitted by the grading Worker. */
    function handleLine(line: string): void {
      if (line === 'uciok') {
        // MultiPV is set dynamically per-search (candidate count varies by
        // position) rather than once at init — see prepareSearch.
        worker.postMessage('isready');
        return;
      }

      if (line === 'readyok') {
        setIsReady(true);
        isReadyRef.current = true;
        return;
      }

      if (line.startsWith('info ')) {
        // Stale-eval guard: ignore info lines from a superseded search.
        if (stateRef.current !== 'thinking' || stopPendingRef.current) return;
        const parsed = parseInfoLine(line);
        if (parsed === null) return;
        const uci = parsed.pv[0];
        if (uci === undefined) return;
        const fenKey = gradingFenRef.current;
        if (fenKey === null) return;

        // Pitfall 1 (confirmed on the real binary, 151.1-01-SUMMARY.md): key
        // by pv[0]'s SAN, NEVER by parsed.multipv (an eval rank that reorders
        // as depth climbs).
        const san = sanFromUci(fenKey, uci);
        if (san === null) return;

        // Normalize the mover-POV UCI score to white-POV (D-08).
        const whitePovSign = gradingSideRef.current === 'b' ? -1 : 1;
        const toWhitePov = (v: number | null): number | null => (v === null ? null : v * whitePovSign);

        let cache = cacheRef.current.get(fenKey);
        if (!cache) {
          cache = new Map<string, MoveGrade>();
          cacheRef.current.set(fenKey, cache);
          // FIFO eviction on new-FEN insert only (mirrors useMaiaEngine's cacheResult).
          if (cacheRef.current.size > GRADE_CACHE_MAX) {
            const oldest = cacheRef.current.keys().next().value;
            if (oldest !== undefined) cacheRef.current.delete(oldest);
          }
        }
        cache.set(san, {
          evalCp: toWhitePov(parsed.scoreCp),
          evalMate: toWhitePov(parsed.scoreMate),
          depth: parsed.depth,
          // 162 UAT: retain the full PV so the Stockfish card can render a
          // graded line's move sequence when the reconciled ranking surfaces
          // a move outside the free run's own top-2 (option-2 card re-source).
          pv: parsed.pv,
        });

        // Stream progressively: refine the displayed gradeMap on every info
        // line (D-05).
        commitDisplayedGradeMap(fenKey, candidateSansRef.current);
        return;
      }

      if (line.startsWith('bestmove')) {
        if (stopPendingRef.current) {
          // Discard: this bestmove is the termination response to our stop —
          // it reflects a superseded search. Re-trigger with the LATEST
          // fen/candidateSans (deferred re-go, Pitfall 5 / FLAWCHESS-7V).
          stopPendingRef.current = false;
          stateRef.current = 'idle';
          const latestFen = currentFenRef.current;
          const latestSans = candidateSansRef.current;
          if (latestFen !== null && latestSans.length > 0 && document.visibilityState !== 'hidden') {
            prepareSearchRef.current(latestFen, latestSans);
          }
          return;
        }

        stateRef.current = 'idle';
        setIsGrading(false);
      }
    }

    worker.onmessage = (e: MessageEvent<string>) => {
      handleLine(e.data);
    };

    // Kick off UCI initialisation — the engine will respond with 'uciok'.
    worker.postMessage('uci');

    return () => {
      // Always stop + terminate on unmount to prevent CPU/battery drain.
      worker.postMessage('stop');
      worker.terminate();
      workerRef.current = null;
    };
  }, [enabled]); // re-run only if enabled toggles

  // ─── Debounced request → prepareSearch ─────────────────────────────────────

  useEffect(() => {
    if (!debouncedRequest || !isReady) return;
    prepareSearch(debouncedRequest.fen, debouncedRequest.candidateSans);
  }, [debouncedRequest, isReady, prepareSearch]);

  // ─── Tab-hide pause ─────────────────────────────────────────────────────────

  useEffect(() => {
    function handleVisibility(): void {
      const worker = workerRef.current;
      if (!worker || !isReadyRef.current) return;

      if (document.visibilityState === 'hidden') {
        if (stateRef.current === 'thinking') {
          worker.postMessage('stop');
          stopPendingRef.current = true;
          stateRef.current = 'stopping';
        }
      } else {
        // Visible again — re-grade the current position (auto re-go).
        const latestFen = currentFenRef.current;
        const latestSans = candidateSansRef.current;
        if (latestFen !== null && latestSans.length > 0) {
          prepareSearchRef.current(latestFen, latestSans);
        }
      }
    }

    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []); // stable refs — no deps required

  // ─── Return ────────────────────────────────────────────────────────────────

  return { gradeMap, isGrading, isReady };
}
