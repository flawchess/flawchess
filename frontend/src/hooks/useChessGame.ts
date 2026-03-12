import { useRef, useState, useCallback } from 'react';
import { Chess } from 'chess.js';
import { computeHashes, hashToString } from '@/lib/zobrist';
import type { ZobristHashes } from '@/lib/zobrist';
import type { MatchSide } from '@/types/api';

export interface ChessGameState {
  /** Current FEN for react-chessboard */
  position: string;
  /** SAN move history */
  moveHistory: string[];
  /** Which ply we're currently viewing (0 = start, 1 = after move 1, ...) */
  currentPly: number;
  /** Zobrist hashes for the current position */
  hashes: ZobristHashes;
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
  /** Get the hash to send for analysis based on match side */
  getHashForAnalysis: (matchSide: MatchSide) => string;
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

  /**
   * Replay moveHistory[0..ply-1] on a fresh Chess instance and sync all state.
   */
  const replayTo = useCallback((history: string[], ply: number) => {
    const chess = new Chess();
    for (let i = 0; i < ply; i++) {
      chess.move(history[i]);
    }
    chessRef.current = chess;
    setPosition(chess.fen());
    setCurrentPly(ply);
    setHashes(computeHashes(chess));
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

  const reset = useCallback(() => {
    const chess = new Chess();
    chessRef.current = chess;
    setPosition(STARTING_FEN);
    setMoveHistory([]);
    setCurrentPly(0);
    setHashes(computeHashes(chess));
  }, []);

  const getHashForAnalysis = useCallback(
    (matchSide: MatchSide): string => {
      if (matchSide === 'white') return hashToString(hashes.whiteHash);
      if (matchSide === 'black') return hashToString(hashes.blackHash);
      return hashToString(hashes.fullHash);
    },
    [hashes],
  );

  return {
    position,
    moveHistory,
    currentPly,
    hashes,
    makeMove,
    goToMove,
    goForward,
    goBack,
    reset,
    getHashForAnalysis,
  };
}
