// @vitest-environment jsdom
//
// Blue best-move arrow source contract (Quick 260627-l2z; +1 ply Quick thl):
//   - The blue arrow is the engine's best move FROM the displayed position. The
//     board at mainLine[k] is the position after move k, so its best move is the
//     NEXT eval-series row, best_move[k+1] (not best_move[k], which is the move that
//     led INTO the shown position). It renders IMMEDIATELY from the precomputed
//     value — no wait for the live engine.
//   - When best_move is null (non-flaw lichess-eval-only plies), the blue falls
//     back to the live engine's top line (pvLines[0]).
import { renderHook } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { useGameOverlay } from '@/hooks/useGameOverlay';
import { BEST_MOVE_ARROW, SECOND_BEST_ARROW, TAC_ALLOWED, TAC_MISSED } from '@/lib/theme';
import type { EvalPoint, FlawMarker } from '@/types/library';
import type { PvLine } from '@/hooks/uciParser';

const pt = (ply: number, best_move: string | null): EvalPoint => ({
  ply,
  es: 0.5,
  eval_cp: 20,
  eval_mate: null,
  clock_seconds: null,
  move_seconds: null,
  best_move,
});

const mainLine = [10, 11, 12];
const isOnMainLine = (id: number) => mainLine.includes(id);

const base = {
  enabled: true,
  engineEnabled: true,
  flawMarkers: [],
  mainLine,
  isOnMainLine,
  lastMove: { from: 'e2', to: 'e4' },
  engineEvalCp: null,
  engineEvalMate: null,
  engineDepth: 0,
};

describe('useGameOverlay blue-arrow source', () => {
  it('uses the precomputed best_move immediately (engine empty)', () => {
    const { result } = renderHook(() =>
      useGameOverlay({
        ...base,
        evalSeries: [pt(0, 'e2e4'), pt(1, 'e7e5'), pt(2, 'g1f3')],
        currentNodeId: 11, // mainLine[1] (k=1) → best from here = eval_series[2].best_move = g1f3
        enginePvLines: [], // engine has NOT reported
      }),
    );
    const blue = result.current.boardArrows?.find((a) => a.color === BEST_MOVE_ARROW);
    expect(blue).toMatchObject({ startSquare: 'g1', endSquare: 'f3' });
    expect(result.current.usingPrecomputed).toBe(true);
  });

  it('falls back to the live engine best move when best_move is null', () => {
    const enginePvLines: PvLine[] = [
      { moves: ['c2c4'], multipv: 1, depth: 12, evalCp: 20, evalMate: null },
      { moves: ['d2d4'], multipv: 2, depth: 12, evalCp: 10, evalMate: null },
    ];
    const { result } = renderHook(() =>
      useGameOverlay({
        ...base,
        evalSeries: [pt(0, null), pt(1, null), pt(2, null)], // eval present, best_move null
        currentNodeId: 11,
        enginePvLines,
      }),
    );
    const blue = result.current.boardArrows?.find((a) => a.color === BEST_MOVE_ARROW);
    expect(blue).toMatchObject({ startSquare: 'c2', endSquare: 'c4' });
  });

  it('suppresses the blue best-move arrow when Stockfish is toggled off (155 UAT)', () => {
    const { result } = renderHook(() =>
      useGameOverlay({
        ...base,
        engineEnabled: false,
        evalSeries: [pt(0, 'e2e4'), pt(1, 'e7e5'), pt(2, 'g1f3')], // precomputed best present
        currentNodeId: 11,
        enginePvLines: [
          { moves: ['c2c4'], multipv: 1, depth: 12, evalCp: 20, evalMate: null },
          { moves: ['d2d4'], multipv: 2, depth: 12, evalCp: 10, evalMate: null },
        ],
      }),
    );
    const arrows = result.current.boardArrows ?? [];
    // Neither the precomputed blue best nor the live second-best show while off.
    expect(arrows.find((a) => a.color === BEST_MOVE_ARROW)).toBeUndefined();
    expect(arrows.find((a) => a.color === SECOND_BEST_ARROW)).toBeUndefined();
  });

  it('keeps the crimson allowed-tactic arrow even when Stockfish is toggled off (155 UAT)', () => {
    const allowedFork: FlawMarker = {
      ply: 1,
      severity: 'blunder',
      tags: [],
      is_user: true,
      move_san: 'Nf3',
      allowed_tactic_motif: 'fork',
      allowed_tactic_confidence: 1,
      allowed_tactic_depth: 2,
      missed_tactic_motif: null,
      missed_tactic_confidence: null,
      missed_tactic_depth: null,
    };
    const { result } = renderHook(() =>
      useGameOverlay({
        ...base,
        engineEnabled: false,
        flawMarkers: [allowedFork],
        evalSeries: [pt(0, 'a2a3'), pt(1, 'd2d4'), pt(2, 'g1f3')],
        currentNodeId: 11,
        enginePvLines: [],
      }),
    );
    const arrows = result.current.boardArrows ?? [];
    // The crimson opponent-response arrow is part of the tactic overlay, not a live
    // engine suggestion, so it survives the Stockfish toggle.
    expect(arrows.find((a) => a.color === TAC_ALLOWED)).toMatchObject({
      startSquare: 'g1',
      endSquare: 'f3',
      label: '3',
    });
    // ...but no plain blue best-move arrow.
    expect(arrows.find((a) => a.color === BEST_MOVE_ARROW)).toBeUndefined();
  });
});

// ── Violet should-have-played arrow parity (Quick 260628-1t5 DECISION 1) ────────
//
// The recurring off-by-one guard. At a missed-tactic flaw ply k the violet arrow must be
// the engine best move FROM the pre-flaw DECISION position mainLine[k-1] — i.e.
// eval_series[k].best_move (bestMoveByPly.get(k)) — which is the SAME move FlawCard's blue
// should-have-played arrow shows. It must be DISTINCT from the blue following-best, which
// is the best move from the displayed post-flaw position mainLine[k] = eval_series[k+1]
// (bestMoveByPly.get(k+1)). The fixture gives every ply a different best_move so an
// off-by-one (using get(k+1) or get(k-1) for the violet) is caught.
describe('useGameOverlay violet should-have-played arrow (missed tactic)', () => {
  const missedFork = (ply: number): FlawMarker => ({
    ply,
    severity: 'blunder',
    tags: [],
    is_user: true,
    move_san: 'Nf3',
    allowed_tactic_motif: null,
    allowed_tactic_confidence: null,
    allowed_tactic_depth: null,
    missed_tactic_motif: 'fork',
    missed_tactic_confidence: 90,
    missed_tactic_depth: 2,
  });

  // Per-ply distinct best moves: get(1)=d2d4 (best from decision mainLine[0]) is the
  // should-have-played move; get(2)=g1f3 (best from displayed mainLine[1]) is the blue
  // following-best. a2a3 at ply 0 only exists to keep every row distinct.
  const evalSeries = [pt(0, 'a2a3'), pt(1, 'd2d4'), pt(2, 'g1f3')];

  it('renders the violet arrow at the decision-position best move, distinct from blue', () => {
    const { result } = renderHook(() =>
      useGameOverlay({
        ...base,
        flawMarkers: [missedFork(1)], // flaw at ply 1 = displayed node mainLine[1]
        evalSeries,
        currentNodeId: 11, // mainLine[1], k=1
        enginePvLines: [],
      }),
    );
    const arrows = result.current.boardArrows ?? [];
    const violet = arrows.find((a) => a.color === TAC_MISSED);
    const blue = arrows.find((a) => a.color === BEST_MOVE_ARROW);
    // Violet = best from the DECISION position mainLine[0] = eval_series[1].best_move.
    expect(violet).toMatchObject({ startSquare: 'd2', endSquare: 'd4', label: '3' });
    // Blue following-best = best from the displayed mainLine[1] = eval_series[2].best_move.
    expect(blue).toMatchObject({ startSquare: 'g1', endSquare: 'f3' });
    expect(blue?.label).toBeUndefined(); // depth label rides the violet arrow, not blue
    // The two are distinct moves (the off-by-one guard).
    expect(violet?.startSquare).not.toBe(blue?.startSquare);
  });

  it('paints the following-best arrow crimson (allowed) and NO violet on an allowed-only flaw ply', () => {
    const allowedFork: FlawMarker = { ...missedFork(1), missed_tactic_motif: null, missed_tactic_depth: null, allowed_tactic_motif: 'fork', allowed_tactic_depth: 2 };
    const { result } = renderHook(() =>
      useGameOverlay({
        ...base,
        flawMarkers: [allowedFork],
        evalSeries,
        currentNodeId: 11,
        enginePvLines: [],
      }),
    );
    const arrows = result.current.boardArrows ?? [];
    // No missed (teal) should-have-played arrow on an allowed-only flaw.
    expect(arrows.find((a) => a.color === TAC_MISSED)).toBeUndefined();
    // The following-best arrow IS the opponent's refuting response, so it carries the
    // allowed-tactic crimson AND the allowed depth label on its target square (g1f3), not
    // plain blue (Quick 260628-pu2 UAT, mirrors the game card). allowed_depth 2 → label '3'.
    expect(arrows.find((a) => a.color === BEST_MOVE_ARROW)).toBeUndefined();
    expect(arrows.find((a) => a.color === TAC_ALLOWED)).toMatchObject({
      startSquare: 'g1',
      endSquare: 'f3',
      label: '3',
    });
    // The played-flaw square marker keeps the severity glyph but no depth label (the label
    // used to sit on this wrong square and doubled when the line opened).
    expect(result.current.squareMarkers.every((m) => m.label === undefined)).toBe(true);
  });

  it('draws NO tactic arrows for an opponent flaw (is_user=false), keeping the blue best-move arrow', () => {
    // Quick 260705: opponent tactics live in the eval-chart tooltip only, never on the board.
    const oppAllowed: FlawMarker = {
      ...missedFork(1),
      is_user: false,
      missed_tactic_motif: null,
      missed_tactic_depth: null,
      allowed_tactic_motif: 'fork',
      allowed_tactic_depth: 2,
    };
    const { result } = renderHook(() =>
      useGameOverlay({
        ...base,
        flawMarkers: [oppAllowed],
        evalSeries,
        currentNodeId: 11,
        enginePvLines: [],
      }),
    );
    const arrows = result.current.boardArrows ?? [];
    // No crimson allowed / teal missed tactic arrows for the opponent's flaw.
    expect(arrows.find((a) => a.color === TAC_ALLOWED)).toBeUndefined();
    expect(arrows.find((a) => a.color === TAC_MISSED)).toBeUndefined();
    // The neutral blue best-move arrow (from the displayed position) still shows, unlabeled.
    expect(arrows.find((a) => a.color === BEST_MOVE_ARROW)).toMatchObject({
      startSquare: 'g1',
      endSquare: 'f3',
    });
    // Severity glyph stays both-color (pre-existing behavior).
    expect(result.current.squareMarkers.length).toBeGreaterThan(0);
  });

  it('draws NO violet arrow on a clean (non-flaw) ply', () => {
    const { result } = renderHook(() =>
      useGameOverlay({
        ...base,
        flawMarkers: [],
        evalSeries,
        currentNodeId: 11,
        enginePvLines: [],
      }),
    );
    const arrows = result.current.boardArrows ?? [];
    expect(arrows.find((a) => a.color === TAC_MISSED)).toBeUndefined();
  });
});
