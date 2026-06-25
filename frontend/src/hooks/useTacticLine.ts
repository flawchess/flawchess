/**
 * useTacticLine — PV stepper for the Tactic Line Explorer (Phase 135).
 *
 * Cloned from useChessGame.ts (~80%) with these divergences:
 * - No session-storage persistence (ephemeral to modal open).
 * - No opening lookup (findOpening / preloadOpenings).
 * - No Zobrist hashing (computeHashes / hashToString).
 * - No free-play makeMove (read-only PV walk).
 * - Starts from rootFen (decision position), not the chess starting position.
 * - Depth counter: rootDisplayDepth - currentPly, floored at 0 (reaches 0 AT the
 *   punchline ply, where rootDisplayDepth === currentPly).
 * - isPayoff: true once currentPly > rootDisplayDepth (stepped PAST the punchline,
 *   after the counter has shown 0). The punchline ply itself is not payoff.
 * - Keyboard handler scoped to containerRef (not window) to avoid clashing
 *   with page-level shortcuts when the game board is also mounted.
 * - reset() replays to ply 0 (rootFen), not the chess starting position.
 */

import { useRef, useState, useCallback, useEffect } from 'react';
import { Chess } from 'chess.js';
import { toDisplayDepthForOrientation } from '@/lib/tacticDepth';
import type { TacticDepthOrientation } from '@/lib/tacticDepth';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface UseTacticLineOptions {
  /**
   * SAN moves from TacticLinesResponse (missed_moves or allowed_moves).
   * Null when the server has no PV for this orientation.
   */
  moves: string[] | null;
  /**
   * Starting FEN (full FEN from TacticLinesResponse.position_fen).
   * Must include side-to-move — the backend derives it from ply parity.
   */
  rootFen: string;
  /**
   * Raw 0-based tactic depth index (missed_depth or allowed_depth from response).
   * The punchline fires at PV index tacticDepthRaw; isPayoff becomes true after.
   */
  tacticDepthRaw: number;
  /**
   * Orientation drives the display offset formula (missed vs allowed offset).
   * Changing orientation resets the stepper to ply 0.
   * Use TacticDepthOrientation ('missed' | 'allowed') — not the broader
   * TacticOrientation which includes 'either' (invalid for depth display math).
   */
  orientation: TacticDepthOrientation;
}

export interface TacticLineState {
  /** Current FEN for react-chessboard. */
  position: string;
  /** 0 = root (decision position), 1+ = after PV moves. */
  currentPly: number;
  /** Last move from/to squares for board highlighting; null at root. */
  lastMove: { from: string; to: string } | null;
  /**
   * User-visible depth counter: starts at rootDisplayDepth and decrements by 1
   * per ply, floored at 0. Shows 0 at and past the punchline.
   */
  displayDepth: number;
  /** True once currentPly > rootDisplayDepth (stepped past the tactic punchline). */
  isPayoff: boolean;
  /** Advance one ply (capped at moves.length). */
  goForward: () => void;
  /** Retreat one ply (floored at 0). */
  goBack: () => void;
  /** Jump to a specific ply. */
  goToMove: (ply: number) => void;
  /** Return to ply 0 / rootFen. */
  reset: () => void;
  canGoForward: boolean;
  canGoBack: boolean;
  /**
   * Attach to the explorer container div so keyboard nav (ArrowLeft/Right)
   * is scoped to the explorer, not the whole window.
   */
  containerRef: React.RefObject<HTMLDivElement | null>;
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useTacticLine({
  moves,
  rootFen,
  tacticDepthRaw,
  orientation,
}: UseTacticLineOptions): TacticLineState {
  const history = moves ?? [];

  const chessRef = useRef<Chess>(new Chess(rootFen));
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [position, setPosition] = useState<string>(rootFen);
  const [currentPly, setCurrentPly] = useState<number>(0);
  const [lastMove, setLastMove] = useState<{ from: string; to: string } | null>(null);

  // Mutable refs that are updated after each render so goForward/goBack callbacks
  // always see the latest values without closing over stale state. This avoids
  // the stale-closure issue from useChessGame's window.addEventListener approach
  // while keeping keyboard nav scoped to the container.
  const historyRef = useRef<string[]>(history);
  const currentPlyRef = useRef<number>(0);
  // Sync refs to latest values — safe to do in a layout effect to avoid
  // the react-hooks/refs render-phase update restriction.
  useEffect(() => {
    historyRef.current = history;
    currentPlyRef.current = currentPly;
  });

  /**
   * Replay hist[0..ply-1] on a fresh Chess instance starting from rootFen.
   * Mirrors useChessGame.ts:replayTo but initialises with rootFen (decision
   * position) instead of the chess starting position (divergence per PATTERNS).
   */
  const replayTo = useCallback(
    (hist: string[], ply: number) => {
      const chess = new Chess(rootFen);
      let fromSq: string | null = null;
      let toSq: string | null = null;
      for (let i = 0; i < ply; i++) {
        // safe: loop bound ensures i < ply <= hist.length
        const move = chess.move(hist[i]!);
        if (i === ply - 1 && move) {
          fromSq = move.from;
          toSq = move.to;
        }
      }
      chessRef.current = chess;
      setPosition(chess.fen());
      setCurrentPly(ply);
      setLastMove(fromSq && toSq ? { from: fromSq, to: toSq } : null);
    },
    [rootFen],
  );

  // Reset to ply 0 whenever moves, rootFen, or orientation changes.
  // Orientation change resets the stepper to the root (PLAN-02 truth 4:
  // "Switching orientation resets stepper to ply 0").
  useEffect(() => {
    const chess = new Chess(rootFen);
    chessRef.current = chess;
    setPosition(rootFen);
    setCurrentPly(0);
    setLastMove(null);
  }, [moves, rootFen, orientation]);

  const goToMove = useCallback(
    (ply: number) => {
      const hist = historyRef.current;
      const target = Math.max(0, Math.min(ply, hist.length));
      replayTo(hist, target);
    },
    [replayTo],
  );

  // goForward and goBack read latest values from refs (updated each render
  // via useEffect) so they don't close over stale state. This is the stable
  // approach for container-scoped keydown handlers that are not recreated
  // on every currentPly change.
  const goForward = useCallback(() => {
    const hist = historyRef.current;
    const prev = currentPlyRef.current;
    if (prev < hist.length) {
      replayTo(hist, prev + 1);
    }
  }, [replayTo]);

  const goBack = useCallback(() => {
    const prev = currentPlyRef.current;
    if (prev > 0) {
      replayTo(historyRef.current, prev - 1);
    }
  }, [replayTo]);

  const reset = useCallback(() => {
    replayTo(historyRef.current, 0);
  }, [replayTo]);

  // Keyboard navigation scoped to the container (not window) to avoid clashing
  // with page-level shortcuts when the game board is also mounted (divergence).
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        goBack();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        goForward();
      }
    };
    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [goBack, goForward]);

  // Depth counter: root display depth minus current ply, floored at 0.
  // Uses toDisplayDepthForOrientation which applies DEPTH_DISPLAY_OFFSET and
  // ALLOWED_DECISION_DEPTH_OFFSET for the 'allowed' orientation.
  const rootDisplayDepth = toDisplayDepthForOrientation(tacticDepthRaw, orientation);
  const displayDepth = Math.max(0, rootDisplayDepth - currentPly);

  // isPayoff: stepped PAST the tactic punchline. The countdown reaches 0 exactly at
  // the punchline ply (currentPly === rootDisplayDepth), so the punchline itself is
  // NOT payoff — only moves after it are. Using rootDisplayDepth (not the raw depth)
  // keeps this aligned across orientations: the allowed line's display offset already
  // accounts for the prepended flaw move, so the 0-counter lands on the refutation
  // punchline, not the flaw move (Phase 135 UAT).
  const isPayoff = currentPly > rootDisplayDepth;

  const canGoForward = currentPly < history.length;
  const canGoBack = currentPly > 0;

  return {
    position,
    currentPly,
    lastMove,
    displayDepth,
    isPayoff,
    goForward,
    goBack,
    goToMove,
    reset,
    canGoForward,
    canGoBack,
    containerRef,
  };
}
