import { useRef, useState, useCallback, useEffect } from 'react';
import { Chess } from 'chess.js';
import { computeHashes, hashToString } from '@/lib/zobrist';
import { findOpening, preloadOpenings } from '@/lib/openings';
import type { ZobristHashes } from '@/lib/zobrist';
import type { Opening } from '@/lib/openings';
import type { MatchSide, Color } from '@/types/api';
import { resolveMatchSide } from '@/types/api';

interface ChessGameState {
  /** Current FEN for react-chessboard */
  position: string;
  /** SAN move history */
  moveHistory: string[];
  /** Which ply we're currently viewing (0 = start, 1 = after move 1, ...) */
  currentPly: number;
  /** Zobrist hashes for the current position */
  hashes: ZobristHashes;
  /** The last move made (from/to squares) for highlighting, or null at start */
  lastMove: { from: string; to: string } | null;
  /** Make a move by drag-drop */
  makeMove: (sourceSquare: string, targetSquare: string) => boolean;
  /** Jump to a specific ply */
  goToMove: (ply: number) => void;
  /** Go forward one ply */
  goForward: () => void;
  /** Go back one ply */
  goBack: () => void;
  /** Reset to starting position */
  reset: () => void;
  /** Get the hash to send for analysis based on match side and user color */
  getHashForAnalysis: (matchSide: MatchSide, color: Color) => string;
  /** Current opening name from the lichess database, or null */
  openingName: Opening | null;
  /** Load a saved sequence of SAN moves onto a fresh board */
  loadMoves: (sans: string[]) => void;
}

const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function computeInitialHashes(): ZobristHashes {
  const chess = new Chess();
  return computeHashes(chess);
}

export function useChessGame(): ChessGameState {
  const chessRef = useRef<Chess>(new Chess());

  const [position, setPosition] = useState<string>(STARTING_FEN);
  const [moveHistory, setMoveHistory] = useState<string[]>([]);
  const [currentPly, setCurrentPly] = useState<number>(0);
  const [hashes, setHashes] = useState<ZobristHashes>(computeInitialHashes);
  const [lastMove, setLastMove] = useState<{ from: string; to: string } | null>(null);
  const [openingName, setOpeningName] = useState<Opening | null>(null);

  // Pre-load openings database on mount
  useEffect(() => {
    preloadOpenings();
  }, []);

  /**
   * Replay moveHistory[0..ply-1] on a fresh Chess instance and sync all state.
   * Extracts the last move's from/to squares for board highlighting.
   */
  const replayTo = useCallback((history: string[], ply: number) => {
    const chess = new Chess();
    let fromSq: string | null = null;
    let toSq: string | null = null;
    for (let i = 0; i < ply; i++) {
      // safe: loop bound ensures i < ply <= history.length
      const move = chess.move(history[i]!);
      if (i === ply - 1 && move) {
        fromSq = move.from;
        toSq = move.to;
      }
    }
    chessRef.current = chess;
    setPosition(chess.fen());
    setCurrentPly(ply);
    setHashes(computeHashes(chess));
    setLastMove(fromSq && toSq ? { from: fromSq, to: toSq } : null);
  }, []);

  const makeMove = useCallback(
    (sourceSquare: string, targetSquare: string): boolean => {
      const chess = chessRef.current;
      try {
        const result = chess.move({
          from: sourceSquare,
          to: targetSquare,
          promotion: 'q',
        });
        if (!result) return false;

        const san = result.san;
        const from = result.from;
        const to = result.to;

        setMoveHistory((prev) => {
          const atEnd = currentPly === prev.length;
          let newHistory: string[];
          if (atEnd) {
            newHistory = [...prev, san];
          } else {
            // User navigated back and makes a new move — truncate future
            newHistory = [...prev.slice(0, currentPly), san];
          }
          setCurrentPly(newHistory.length);
          setPosition(chess.fen());
          setHashes(computeHashes(chess));
          setLastMove({ from, to });
          return newHistory;
        });

        return true;
      } catch {
        return false;
      }
    },
    [currentPly],
  );

  const goToMove = useCallback(
    (ply: number) => {
      setMoveHistory((prev) => {
        const target = Math.max(0, Math.min(ply, prev.length));
        replayTo(prev, target);
        return prev;
      });
    },
    [replayTo],
  );

  const goForward = useCallback(() => {
    setMoveHistory((prev) => {
      if (currentPly < prev.length) {
        replayTo(prev, currentPly + 1);
      }
      return prev;
    });
  }, [currentPly, replayTo]);

  const goBack = useCallback(() => {
    setMoveHistory((prev) => {
      if (currentPly > 0) {
        replayTo(prev, currentPly - 1);
      }
      return prev;
    });
  }, [currentPly, replayTo]);

  const loadMoves = useCallback(
    (sans: string[]) => {
      setMoveHistory(sans);
      replayTo(sans, sans.length);
    },
    [replayTo],
  );

  const reset = useCallback(() => {
    const chess = new Chess();
    chessRef.current = chess;
    setPosition(STARTING_FEN);
    setMoveHistory([]);
    setCurrentPly(0);
    setHashes(computeHashes(chess));
    setLastMove(null);
  }, []);

  const getHashForAnalysis = useCallback(
    (matchSide: MatchSide, color: Color): string => {
      const resolved = resolveMatchSide(matchSide, color);
      if (resolved === 'white') return hashToString(hashes.whiteHash);
      if (resolved === 'black') return hashToString(hashes.blackHash);
      return hashToString(hashes.fullHash);
    },
    [hashes],
  );

  // Arrow key navigation: left = back, right = forward
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture when user is typing in an input/textarea
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        goBack();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        goForward();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goBack, goForward]);

  // Update opening name whenever the viewed ply changes
  useEffect(() => {
    const movesAtPly = moveHistory.slice(0, currentPly);
    findOpening(movesAtPly).then(setOpeningName);
  }, [moveHistory, currentPly]);

  return {
    position,
    moveHistory,
    currentPly,
    hashes,
    lastMove,
    makeMove,
    goToMove,
    goForward,
    goBack,
    reset,
    getHashForAnalysis,
    openingName,
    loadMoves,
  };
}
