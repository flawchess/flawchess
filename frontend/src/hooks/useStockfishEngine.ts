/**
 * useStockfishEngine — React hook wrapping Stockfish 18 lite-single WASM
 * in a Web Worker, exposing a UCI state machine as plain data.
 *
 * Rendering is deferred to Phases 137/138; this hook is data-only.
 * ENGINE-01: evalCp / evalMate
 * ENGINE-02: pvLines (MultiPV=2)
 * ENGINE-03: pvLines[0].moves[0] (best move UCI string)
 * ENGINE-04: isReady / isAnalyzing + enabled control input
 * ENGINE-05: 150ms debounce + go movetime 1500 nodes 2000000 + stopPendingRef
 *
 * Architecture: RESEARCH.md Patterns 1–4
 * Pitfall refs: Pitfall 3 (stale eval race), Pitfall 4 (worker leak),
 *               Pitfall 5 (bound filtering), D-04 (tab-hide pause)
 */

import { useRef, useState, useCallback, useEffect } from 'react';
import { parseInfoLine } from './uciParser';
import type { PvLine } from './uciParser';

// ─── Constants ───────────────────────────────────────────────────────────────

/** Path to the vendored Stockfish engine served from public/engine/. */
const ENGINE_PATH = '/engine/stockfish-18-lite-single.js';

/** Primary wall-clock search cap (milliseconds). Locked by ROADMAP SC#2. */
const MOVETIME_MS = 1500;

/** Secondary node-count valve — hardware-independent safety bound. */
const MAX_NODES = 2000000;

/** FEN debounce delay before sending go (Layer A stale-eval guard). */
const DEBOUNCE_MS = 150;

/** Number of candidate lines requested from the engine. */
const MULTIPV = 2;

// ─── Types ───────────────────────────────────────────────────────────────────

/** Internal UCI state machine states. */
type EngineState = 'idle' | 'thinking' | 'stopping';

export interface UseStockfishEngineOptions {
  /** Current board position. null keeps the engine idle (no go sent). */
  fen: string | null;
  /** When false the Worker is not created and analysis does not run. */
  enabled: boolean;
}

export interface StockfishEngineState {
  /** Centipawns from white's POV; null while loading or if score is mate. */
  evalCp: number | null;
  /** Mate in N; positive=winning, negative=losing; null if centipawn score. */
  evalMate: number | null;
  /** Up to MULTIPV candidate lines sorted by multipv index. */
  pvLines: PvLine[];
  /** Search depth of the last completed (non-discarded) analysis. */
  depth: number;
  /** True while the engine is searching the current position. */
  isAnalyzing: boolean;
  /** True once the UCI init sequence completes (uciok + readyok). */
  isReady: boolean;
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useStockfishEngine({
  fen,
  enabled,
}: UseStockfishEngineOptions): StockfishEngineState {
  // ─── Refs ──────────────────────────────────────────────────────────────────

  const workerRef = useRef<Worker | null>(null);

  /** Internal UCI state machine — mutated from the onmessage handler (no re-render). */
  const stateRef = useRef<EngineState>('idle');

  /**
   * Layer B stale-eval guard (Pitfall 3).
   * Set to true when stop is sent; cleared when the resulting bestmove arrives
   * and is discarded without committing to pvLines.
   */
  const stopPendingRef = useRef(false);

  /**
   * Ref-for-latest-value: keeps the most recent FEN visible inside event
   * callbacks without closing over stale state (pattern from useTacticLine).
   */
  const currentFenRef = useRef<string | null>(null);

  /** Ref-for-latest-value: isReady visible inside event callbacks. */
  const isReadyRef = useRef(false);

  /** In-flight MultiPV map: keyed by multipv index, updated on exact info lines. */
  const pvMapRef = useRef<Map<number, PvLine>>(new Map());

  // ─── State ─────────────────────────────────────────────────────────────────

  const [isReady, setIsReady] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [evalCp, setEvalCp] = useState<number | null>(null);
  const [evalMate, setEvalMate] = useState<number | null>(null);
  const [pvLines, setPvLines] = useState<PvLine[]>([]);
  const [depth, setDepth] = useState(0);

  // ─── Ref sync (ref-for-latest-value) ───────────────────────────────────────

  // Sync refs to latest prop/state values each render so callbacks always see
  // the current values without closing over stale state.
  useEffect(() => {
    currentFenRef.current = fen;
    isReadyRef.current = isReady;
  });

  // ─── Debounce (Layer A stale-eval guard) ───────────────────────────────────

  /**
   * Debounced FEN: starts as null (not the current fen value) and updates
   * to fen after DEBOUNCE_MS. This ensures ALL analyses — including the
   * initial one — are delayed by the debounce, preventing unnecessary engine
   * calls when the hook mounts before the engine has finished initializing.
   *
   * NOTE: We use an inline debounce (not useDebounce) because useDebounce
   * initializes its state with the current value immediately, which would
   * bypass the 150ms delay on initial analysis.
   */
  const [debouncedFen, setDebouncedFen] = useState<string | null>(null);
  useEffect(() => {
    if (fen === null) {
      setDebouncedFen(null);
      return;
    }
    const timer = setTimeout(() => setDebouncedFen(fen), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [fen]);

  // ─── Analyze ───────────────────────────────────────────────────────────────

  /**
   * Send position + go for the given FEN.
   *
   * If the engine is already thinking, sends stop and marks stopPendingRef so
   * the subsequent bestmove (termination response) is discarded. The go for
   * the new FEN is deferred until that stale bestmove arrives (handleLine).
   *
   * Wrapped in useCallback (no deps — reads from stable refs only) so it can
   * be stored in analyzeRef and called from the onmessage handler without
   * causing stale closure issues.
   */
  const analyze = useCallback((fenToAnalyze: string) => {
    const worker = workerRef.current;
    if (!worker || !isReadyRef.current) return;

    if (stateRef.current === 'thinking') {
      // Engine is mid-search: stop it; the go will be re-sent once the stale
      // bestmove arrives and stopPendingRef is cleared.
      worker.postMessage('stop');
      stopPendingRef.current = true;
      stateRef.current = 'stopping';
      return;
    }

    // Clear pvMap so stale lines from the previous position do not bleed into
    // the snapshot that will be committed on the next bestmove.
    pvMapRef.current.clear();
    worker.postMessage(`position fen ${fenToAnalyze}`);
    worker.postMessage(`go movetime ${MOVETIME_MS} nodes ${MAX_NODES}`);
    stateRef.current = 'thinking';
    setIsAnalyzing(true);
  }, []); // stable — only accesses refs and stable state setters

  /**
   * Ref holding the analyze function, used inside Worker lifetime and
   * visibility effects to avoid adding analyze to their deps arrays
   * (which would re-run the worker effect on every render).
   *
   * analyze is a stable useCallback([]) — no render-phase update is needed;
   * the ref holds the same reference for the component's lifetime.
   */
  const analyzeRef = useRef(analyze);

  // ─── Worker lifecycle ──────────────────────────────────────────────────────

  useEffect(() => {
    if (!enabled) return;

    // Classic (non-module) Worker — Emscripten glue uses self.onmessage /
    // self.postMessage. Do NOT pass { type: 'module' } (Pitfall: Anti-Patterns).
    const worker = new Worker(ENGINE_PATH);
    workerRef.current = worker;

    /** Handle a single UCI line emitted by the engine Worker. */
    function handleLine(line: string): void {
      if (line === 'uciok') {
        worker.postMessage(`setoption name MultiPV value ${MULTIPV}`);
        worker.postMessage('isready');
        return;
      }

      if (line === 'readyok') {
        setIsReady(true);
        isReadyRef.current = true;
        // Analysis is triggered by the debouncedFen + isReady effect below.
        // We do NOT call analyze directly here to preserve the debounce invariant.
        return;
      }

      if (line.startsWith('info ')) {
        const parsed = parseInfoLine(line);
        // Pitfall 5: only commit on exact score bound — never on lowerbound /
        // upperbound (intermediate alpha-beta bounds that cause eval jitter).
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
        if (stopPendingRef.current) {
          // Layer B discard (Pitfall 3): this bestmove is the termination
          // response to our stop — it reflects the previous position, not the
          // current one. Discard and re-analyze the current FEN (unless hidden).
          stopPendingRef.current = false;
          stateRef.current = 'idle';
          const current = currentFenRef.current;
          if (current && document.visibilityState !== 'hidden') {
            analyzeRef.current(current);
          }
          return;
        }

        // Non-stale bestmove: commit the pvMap snapshot.
        stateRef.current = 'idle';
        setIsAnalyzing(false);

        // Sort by multipv index so pvLines[0] is always the top line.
        const snapshot = [...pvMapRef.current.values()].sort(
          (a, b) => a.multipv - b.multipv,
        );
        setPvLines(snapshot);

        // Commit the top line's eval to the flat state fields.
        const topLine = pvMapRef.current.get(1);
        if (topLine !== undefined) {
          setEvalCp(topLine.evalCp);
          setEvalMate(topLine.evalMate);
          setDepth(topLine.depth);
        }
      }
    }

    worker.onmessage = (e: MessageEvent<string>) => {
      handleLine(e.data);
    };

    // Kick off UCI initialisation — the engine will respond with 'uciok'.
    worker.postMessage('uci');

    return () => {
      // Pitfall 4: always stop + terminate on unmount to prevent CPU/battery drain.
      worker.postMessage('stop');
      worker.terminate();
      workerRef.current = null;
    };
  }, [enabled]); // re-run only if enabled toggles

  // ─── Debounced FEN → analyze ───────────────────────────────────────────────

  // Trigger analysis when both (a) debouncedFen is set AND (b) engine is ready.
  // Using isReady as a dep ensures the effect re-fires when the engine finishes
  // its init sequence (even if debouncedFen was already set before init completed).
  useEffect(() => {
    if (!debouncedFen || !isReady) return;
    analyze(debouncedFen);
  }, [debouncedFen, isReady, analyze]);

  // ─── Tab-hide pause (D-04) ─────────────────────────────────────────────────

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
        // Visible again — re-analyze the current position (auto re-go, D-04).
        const current = currentFenRef.current;
        if (current) {
          analyzeRef.current(current);
        }
      }
    }

    document.addEventListener('visibilitychange', handleVisibility);
    return () =>
      document.removeEventListener('visibilitychange', handleVisibility);
  }, []); // stable refs — no deps required

  // ─── Return ────────────────────────────────────────────────────────────────

  return { evalCp, evalMate, pvLines, depth, isAnalyzing, isReady };
}
