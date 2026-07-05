/**
 * useMaiaEngine — React hook wrapping the Maia-3 ("Chessformer") ONNX model in a
 * classic Web Worker, exposing the full per-ELO move-probability curve + WDL as
 * plain data. Structural sibling of `useStockfishEngine.ts` (Worker lifecycle,
 * mount-only effect, isReady/isAnalyzing, adaptive debounce, stale-result guard,
 * tab-hide pause) — the *protocol* differs (structured `{fen, eloInputs}` messages,
 * not UCI text), but the state-machine shape transfers directly.
 *
 * MAIA-04: full per-ELO curve + WDL computed for a known FEN, ELO ladder =
 *          maiachess.com's 600-2600 step 100 (UAT quick 260705-bm3; validated
 *          sub-band 1100-2000 per 151-MAIA-CONTRACT.md §c).
 * MAIA-05: ephemeral, board-session-scoped FIFO cache (no persistence).
 * SURF-05: live recompute on every FEN change, no server round-trip.
 *
 * maskAndSoftmax/expectedScore/softmaxWdl are single-sourced from maiaEncoding.ts
 * (the worker returns RAW policy/WDL logits only — see maia-worker.js header).
 *
 * Architecture: 151-RESEARCH.md Pattern 1; Confirmed contract: 151-MAIA-CONTRACT.md
 */

import { useRef, useState, useCallback, useEffect, useMemo } from 'react';
import { maskAndSoftmax, softmaxWdl, expectedScore, MAIA_ELO_LADDER } from '../lib/maiaEncoding';
import type { WdlVector } from '../lib/maiaEncoding';

// ─── Constants ───────────────────────────────────────────────────────────────

/** Path to the vendored Maia Worker served from public/maia/. */
const ENGINE_PATH = '/maia/maia-worker.js';

/** Rapid-step debounce window (ms) — mirrors useStockfishEngine's RAPID_STEP_DEBOUNCE_MS. */
const RAPID_STEP_DEBOUNCE_MS = 150;

/** Ephemeral inference cache cap — mirrors Analysis.tsx's LIVE_EVAL_CACHE_MAX pattern (MAIA-05). */
const MAIA_CACHE_MAX = 256;

// ─── Types ───────────────────────────────────────────────────────────────────

export interface UseMaiaEngineOptions {
  /** Current board position. null keeps the engine idle (no analyze sent). */
  fen: string | null;
  /** When false the Worker is not created and analysis does not run. */
  enabled: boolean;
  /** ELO used to pick the "you are here" rung for wdl/expectedScoreAtSelectedElo. */
  selectedElo: number;
}

/** One ELO rung's normalized per-legal-move probability distribution, keyed by SAN. */
export interface MoveCurvePoint {
  elo: number;
  moveProbabilities: Record<string, number>;
}

export interface UseMaiaEngineState {
  /** Full per-ELO curve (every MAIA_ELO_LADDER rung) — chart input (SURF-01). */
  perElo: MoveCurvePoint[];
  /** expectedScore(wdl) at the ladder rung nearest `selectedElo`; null until ready. */
  expectedScoreAtSelectedElo: number | null;
  /** Full WDL vector at the ladder rung nearest `selectedElo`; null until ready. */
  wdl: WdlVector | null;
  /** True once the Worker's ONNX session has been created. */
  isReady: boolean;
  /** True while a (non-cached) inference is in flight for the current FEN. */
  isAnalyzing: boolean;
}

/** Cached inference result for one FEN — every ladder rung, board-session scoped. */
interface MaiaResult {
  perElo: MoveCurvePoint[];
  wdlByElo: { elo: number; wdl: WdlVector }[];
}

/** Raw worker payload shape for a completed `analyze` (see maia-worker.js header). */
interface WorkerResultMessage {
  type: 'result';
  fen: string;
  rawPolicyByElo: { elo: number; policy: Float32Array }[];
  wdlByElo: { elo: number; wdl: Float32Array }[];
  backend: 'webgpu' | 'wasm';
}

type WorkerMessage =
  | { type: 'ready'; backend: 'webgpu' | 'wasm' }
  | WorkerResultMessage
  | { type: 'error'; message: string };

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Converts a worker's raw per-ELO payload into the hook's normalized MaiaResult. */
function buildMaiaResult(fen: string, msg: WorkerResultMessage): MaiaResult {
  const perElo = msg.rawPolicyByElo.map(({ elo, policy }) => ({
    elo,
    moveProbabilities: maskAndSoftmax(policy, fen),
  }));
  const wdlByElo = msg.wdlByElo.map(({ elo, wdl }) => ({ elo, wdl: softmaxWdl(wdl) }));
  return { perElo, wdlByElo };
}

/** Finds the ladder entry whose ELO is numerically closest to `target`. */
function nearestByElo<T extends { elo: number }>(entries: T[], target: number): T | undefined {
  return entries.reduce<T | undefined>((closest, entry) => {
    if (closest === undefined) return entry;
    return Math.abs(entry.elo - target) < Math.abs(closest.elo - target) ? entry : closest;
  }, undefined);
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useMaiaEngine({ fen, enabled, selectedElo }: UseMaiaEngineOptions): UseMaiaEngineState {
  // ─── Refs ──────────────────────────────────────────────────────────────────

  const workerRef = useRef<Worker | null>(null);
  const isReadyRef = useRef(false);
  const currentFenRef = useRef<string | null>(null);

  /** Ephemeral, board-session-scoped FIFO cache (MAIA-05) — no persistence. */
  const cacheRef = useRef<Map<string, MaiaResult>>(new Map());

  /** Timestamp of the last FEN change, for the adaptive debounce (mirrors useStockfishEngine). */
  const lastFenChangeAtRef = useRef(0);

  // ─── State ─────────────────────────────────────────────────────────────────

  const [isReady, setIsReady] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [latestResult, setLatestResult] = useState<MaiaResult | null>(null);

  // ─── Ref sync ──────────────────────────────────────────────────────────────

  useEffect(() => {
    currentFenRef.current = fen;
    isReadyRef.current = isReady;
  });

  // ─── FIFO cache insert ─────────────────────────────────────────────────────

  const cacheResult = useCallback((key: string, result: MaiaResult) => {
    const cache = cacheRef.current;
    cache.set(key, result);
    if (cache.size > MAIA_CACHE_MAX) {
      const oldest = cache.keys().next().value;
      if (oldest !== undefined) cache.delete(oldest);
    }
  }, []);

  // ─── Analyze ───────────────────────────────────────────────────────────────

  /**
   * Sends `analyze` for the given FEN, or commits a cache hit immediately without
   * a worker round-trip. Paused while the tab is hidden (D-04-adjacent tab-hide
   * pause pattern, mirrors useStockfishEngine's visibilitychange handling).
   */
  const analyze = useCallback(
    (fenToAnalyze: string) => {
      const worker = workerRef.current;
      if (!worker || !isReadyRef.current) return;
      if (document.visibilityState === 'hidden') return;

      const cached = cacheRef.current.get(fenToAnalyze);
      if (cached) {
        setLatestResult(cached);
        return;
      }

      setIsAnalyzing(true);
      worker.postMessage({ type: 'analyze', fen: fenToAnalyze, eloInputs: MAIA_ELO_LADDER });
    },
    [], // stable — only reads refs and stable state setters
  );

  const analyzeRef = useRef(analyze);

  // ─── Debounce (mirrors useStockfishEngine's adaptive debounce) ────────────

  const [debouncedFen, setDebouncedFen] = useState<string | null>(null);
  useEffect(() => {
    // Drop the previous position's curve/WDL immediately so a slow (cache-miss)
    // inference never leaves a stale curve mislabeled as the current position's.
    setLatestResult(null);
    if (fen === null) {
      setDebouncedFen(null);
      return;
    }
    const now = Date.now();
    const sinceLast = now - lastFenChangeAtRef.current;
    lastFenChangeAtRef.current = now;
    if (sinceLast > RAPID_STEP_DEBOUNCE_MS) {
      setDebouncedFen(fen);
      return;
    }
    const timer = setTimeout(() => setDebouncedFen(fen), RAPID_STEP_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [fen]);

  // ─── Worker lifecycle ──────────────────────────────────────────────────────

  useEffect(() => {
    if (!enabled) return;

    // Classic (non-module) Worker — mirrors the Stockfish precedent; the Maia
    // Worker uses importScripts() to load onnxruntime-web's UMD-style bundles.
    const worker = new Worker(ENGINE_PATH);
    workerRef.current = worker;

    worker.onmessage = (e: MessageEvent<WorkerMessage>) => {
      const msg = e.data;
      if (msg.type === 'ready') {
        setIsReady(true);
        isReadyRef.current = true;
        return;
      }
      if (msg.type === 'result') {
        if (msg.fen !== currentFenRef.current) return; // stale-result guard
        const result = buildMaiaResult(msg.fen, msg);
        cacheResult(msg.fen, result);
        setLatestResult(result);
        setIsAnalyzing(false);
        return;
      }
      // msg.type === 'error': surfaced as isAnalyzing=false (no partial UI state);
      // real-model error handling is exercised manually in Plan 06 / VALID-01.
      setIsAnalyzing(false);
    };

    worker.postMessage({ type: 'init' });

    return () => {
      worker.postMessage({ type: 'terminate' });
      worker.terminate();
      workerRef.current = null;
    };
  }, [enabled, cacheResult]);

  // ─── Debounced FEN -> analyze ───────────────────────────────────────────────

  useEffect(() => {
    if (!debouncedFen || !isReady) return;
    analyze(debouncedFen);
  }, [debouncedFen, isReady, analyze]);

  // ─── Tab-hide pause ─────────────────────────────────────────────────────────

  useEffect(() => {
    function handleVisibility(): void {
      if (document.visibilityState === 'visible') {
        // Re-analyze the current position on return — mirrors useStockfishEngine's
        // auto re-go so a position changed-while-hidden. is picked up immediately.
        const current = currentFenRef.current;
        if (current) analyzeRef.current(current);
      }
      // No explicit worker-side action is needed on hide: Maia inference is a
      // single request/response per position (not an iterative search like
      // Stockfish), so there is nothing in-flight to stop — analyze() itself
      // checks visibilityState and will not fire a NEW analyze while hidden.
    }

    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  // ─── Derived state (selectedElo -> nearest ladder rung) ────────────────────

  const nearestWdlEntry = useMemo(
    () => (latestResult ? nearestByElo(latestResult.wdlByElo, selectedElo) : undefined),
    [latestResult, selectedElo],
  );

  const wdl = nearestWdlEntry?.wdl ?? null;
  const expectedScoreAtSelectedElo = wdl ? expectedScore(wdl) : null;

  // ─── Return ────────────────────────────────────────────────────────────────

  return {
    perElo: latestResult?.perElo ?? [],
    expectedScoreAtSelectedElo,
    wdl,
    isReady,
    isAnalyzing,
  };
}
