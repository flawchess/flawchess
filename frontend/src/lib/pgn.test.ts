import { describe, it, expect } from 'vitest';
import { Chess } from 'chess.js';
import { buildAnalysisPgn, gamePgnHeaders, pgnToSanArray } from './pgn';
import type { PgnTreeNode } from './pgn';

describe('pgnToSanArray', () => {
  // ── Standard inputs ───────────────────────────────────────────────────────
  it('parses a standard 3-ply PGN into a SAN array', () => {
    expect(pgnToSanArray('1. e4 e5 2. Nf3')).toEqual(['e4', 'e5', 'Nf3']);
  });

  it('parses a 5-ply PGN into a SAN array', () => {
    expect(pgnToSanArray('1. e4 c6 2. d4 d5 3. Nc3')).toEqual(['e4', 'c6', 'd4', 'd5', 'Nc3']);
  });

  // ── Edge cases ────────────────────────────────────────────────────────────
  it('returns an empty array for an empty string', () => {
    expect(pgnToSanArray('')).toEqual([]);
  });

  it('parses a single white move', () => {
    expect(pgnToSanArray('1. e4')).toEqual(['e4']);
  });

  // ── Multi-digit move numbers ───────────────────────────────────────────────
  it('correctly strips multi-digit move numbers', () => {
    expect(pgnToSanArray('10. Qd2 Bd7 11. O-O-O')).toEqual(['Qd2', 'Bd7', 'O-O-O']);
  });

  // ── Castling notation ─────────────────────────────────────────────────────
  it('preserves kingside castling notation O-O', () => {
    expect(pgnToSanArray('1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O')).toEqual([
      'e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Bc5', 'O-O',
    ]);
  });

  it('preserves queenside castling notation O-O-O', () => {
    expect(pgnToSanArray('1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. O-O-O')).toEqual([
      'd4', 'd5', 'c4', 'e6', 'Nc3', 'Nf6', 'O-O-O',
    ]);
  });

  // ── Whitespace handling ───────────────────────────────────────────────────
  it('handles extra whitespace between tokens', () => {
    expect(pgnToSanArray('1.  e4   e5  2.  Nf3')).toEqual(['e4', 'e5', 'Nf3']);
  });

  it('handles leading and trailing whitespace', () => {
    expect(pgnToSanArray('  1. e4 e5  ')).toEqual(['e4', 'e5']);
  });
});

// ─── buildAnalysisPgn ──────────────────────────────────────────────────────────

const START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

/** Tiny tree builder: add(parentId, san) plays san from the parent's position. */
function makeTree(rootFen: string = START) {
  const nodes = new Map<number, PgnTreeNode>();
  let nextId = 0;
  const add = (parentId: number | null, san: string): number => {
    const fen = parentId === null ? rootFen : (nodes.get(parentId) as PgnTreeNode).fen;
    const chess = new Chess(fen);
    chess.move(san);
    const id = nextId++;
    nodes.set(id, { id, san, fen: chess.fen(), parentId });
    return id;
  };
  return { nodes, add };
}

function movetextOf(pgn: string): string {
  const lines = pgn.trim().split('\n');
  return lines[lines.length - 1] as string;
}

describe('buildAnalysisPgn', () => {
  it('exports the main line with Seven Tag Roster placeholders and * result', () => {
    const { nodes, add } = makeTree();
    const e4 = add(null, 'e4');
    const e5 = add(e4, 'e5');
    const nf3 = add(e5, 'Nf3');
    const pgn = buildAnalysisPgn({ nodes, mainLine: [e4, e5, nf3], rootFen: START, headers: null });
    expect(pgn).toContain('[Event "?"]');
    expect(pgn).toContain('[Date "????.??.??"]');
    expect(pgn).toContain('[Result "*"]');
    expect(pgn).not.toContain('[FEN');
    expect(movetextOf(pgn)).toBe('1. e4 e5 2. Nf3 *');
  });

  it('writes sidelines as RAV variations with black move numbers', () => {
    const { nodes, add } = makeTree();
    const e4 = add(null, 'e4');
    const e5 = add(e4, 'e5');
    const nf3 = add(e5, 'Nf3');
    const c5 = add(e4, 'c5'); // sideline at black's first move
    add(c5, 'Nf3');
    const nc3 = add(e5, 'Nc3'); // sideline at white's second move
    add(nc3, 'Nf6');
    const pgn = buildAnalysisPgn({ nodes, mainLine: [e4, e5, nf3], rootFen: START, headers: null });
    expect(movetextOf(pgn)).toBe('1. e4 e5 (1... c5 2. Nf3) 2. Nf3 (2. Nc3 Nf6) *');
    // Round-trips through a real PGN parser (variations are accepted and skipped).
    const chess = new Chess();
    chess.loadPgn(pgn);
    expect(chess.history()).toEqual(['e4', 'e5', 'Nf3']);
  });

  it('gives a free-play tree (empty mainLine) a main line from the lowest-id children', () => {
    const { nodes, add } = makeTree();
    const d4 = add(null, 'd4');
    add(d4, 'd5');
    add(null, 'e4');
    const pgn = buildAnalysisPgn({ nodes, mainLine: [], rootFen: START, headers: null });
    expect(movetextOf(pgn)).toBe('1. d4 (1. e4) 1... d5 *');
  });

  it('adds SetUp/FEN for a non-standard root and numbers a black-to-move start', () => {
    const root = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';
    const { nodes, add } = makeTree(root);
    const c5 = add(null, 'c5');
    const nf3 = add(c5, 'Nf3');
    const pgn = buildAnalysisPgn({ nodes, mainLine: [c5, nf3], rootFen: root, headers: null });
    expect(pgn).toContain('[SetUp "1"]');
    expect(pgn).toContain(`[FEN "${root}"]`);
    expect(movetextOf(pgn)).toBe('1... c5 2. Nf3 *');
  });

  it('exports an empty tree as headers plus the result token', () => {
    const pgn = buildAnalysisPgn({ nodes: new Map(), mainLine: [], rootFen: START, headers: null });
    expect(movetextOf(pgn)).toBe('*');
  });

  it('fills headers, escapes quotes and converts an ISO date', () => {
    const { nodes, add } = makeTree();
    const e4 = add(null, 'e4');
    const pgn = buildAnalysisPgn({
      nodes,
      mainLine: [e4],
      rootFen: START,
      headers: {
        white: 'Al "Ace"',
        black: 'Bo',
        whiteElo: 1850,
        blackElo: null,
        result: '1-0',
        date: '2026-11-04T20:15:00Z',
      },
    });
    expect(pgn).toContain('[White "Al \\"Ace\\""]');
    expect(pgn).toContain('[Date "2026.11.04"]');
    expect(pgn).toContain('[WhiteElo "1850"]');
    expect(pgn).not.toContain('BlackElo');
    expect(pgn).toContain('[Result "1-0"]');
    expect(movetextOf(pgn)).toBe('1. e4 1-0');
  });
});

describe('gamePgnHeaders', () => {
  const base = {
    white_username: 'w',
    black_username: 'b',
    white_rating: 1500,
    black_rating: 1600,
    played_at: '2026-01-02T00:00:00Z',
  };

  it.each([
    ['win', 'white', '1-0'],
    ['loss', 'white', '0-1'],
    ['win', 'black', '0-1'],
    ['loss', 'black', '1-0'],
    ['draw', 'black', '1/2-1/2'],
  ] as const)('%s as %s -> %s', (user_result, user_color, expected) => {
    expect(gamePgnHeaders({ ...base, user_result, user_color }).result).toBe(expected);
  });
});
