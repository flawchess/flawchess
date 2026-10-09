// @vitest-environment jsdom
/**
 * useTrainRevealTree tests (Phase 237 Plan 02), through the REAL useAnalysisBoard.
 *
 * Tracer slice (Task 1): three chip lines seed ONE tree at the puzzle position
 * without moving the board, a chip tap focuses its line, and a line arriving
 * late (RESEARCH Pitfall 1) grafts in place instead of yanking the user back.
 */
import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useTrainRevealTree } from '@/hooks/useTrainRevealTree';
import type { RevealChipLine, UseTrainRevealTreeOptions } from '@/hooks/useTrainRevealTree';
import type { TreeSeedEval } from '@/hooks/useTreeMoveGrading';
import type { TrainFineMove } from '@/lib/trainArrows';
import { SETTINGS_STORAGE_KEYS } from '@/lib/engineSettings';
import {
  REVEAL_TREE_SNAPSHOT_MAX_PATHS,
  REVEAL_TREE_SNAPSHOT_MAX_PLIES,
  walkLinePath,
} from '@/lib/trainRevealLines';
import type { RevealTreeSnapshot } from '@/lib/trainRevealLines';
import { Chess } from 'chess.js';
import { playSound } from '@/lib/sounds';

vi.mock('@/lib/sounds', () => ({
  playSound: vi.fn(),
  unlockAudio: vi.fn(),
}));
const mockPlaySound = vi.mocked(playSound);

// ── Mock useStockfishEngine (Analysis.test.tsx state-object pattern) ────────
// jsdom has no real Worker; drive the reveal engine deterministically via this
// mutable module-level state object. `currentFen` mirrors the real hook's
// contract via the `engineState.currentFen ?? options.fen` fallback, so the
// hook's staleness guard sees a current engine unless a test deliberately
// desyncs it. `scoresByFen` is the per-position script (white-POV cp).
const engineState: {
  scoresByFen: Record<string, number>;
  defaultScoreCp: number;
  /** First move of the mocked engine's rank-1 PV for whatever position it is on:
   * feeds the cached parent `bestUci`. Deliberately a move no test plays. */
  pvFirstMove: string;
  isAnalyzing: boolean;
  currentFen: string | null;
  /** The options the hook last passed to the (mocked) engine. */
  lastMultiPv: number | null;
  lastEnabled: boolean | null;
  lastFen: string | null;
} = {
  scoresByFen: {},
  defaultScoreCp: 20,
  pvFirstMove: 'a7a6',
  isAnalyzing: false,
  currentFen: null,
  lastMultiPv: null,
  lastEnabled: null,
  lastFen: null,
};

vi.mock('@/hooks/useStockfishEngine', () => ({
  useStockfishEngine: (options: { fen: string | null; enabled: boolean; multiPv: number }) => {
    engineState.lastMultiPv = options.multiPv;
    engineState.lastEnabled = options.enabled;
    engineState.lastFen = options.fen;
    const live = options.fen !== null && options.enabled;
    const scripted = options.fen !== null ? engineState.scoresByFen[options.fen] : undefined;
    const evalCp = live ? (scripted ?? engineState.defaultScoreCp) : null;
    return {
      evalCp,
      evalMate: null,
      pvLines: live
        ? [{ multipv: 1, depth: 10, moves: [engineState.pvFirstMove], evalCp, evalMate: null }]
        : [],
      depth: live ? 10 : 0,
      isAnalyzing: engineState.isAnalyzing,
      isReady: true,
      currentFen: live ? (engineState.currentFen ?? options.fen) : null,
    };
  },
}));

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
/** A different puzzle position: 1. e4 e5 played. */
const OTHER_FEN = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2';

const YOUR_LINE = ['e2e4', 'e7e5', 'g1f3'];
const BEST_LINE = ['d2d4', 'd7d5'];
const GAME_LINE = ['c2c4'];

const YOUR: RevealChipLine = { key: 'your', lineUcis: YOUR_LINE };
const BEST: RevealChipLine = { key: 'best', lineUcis: BEST_LINE };
const GAME: RevealChipLine = { key: 'game', lineUcis: GAME_LINE };

// The hook registers window key/wheel listeners and this project's vitest setup
// has no auto-cleanup: unmount every instance or listeners leak across tests.
let unmounts: Array<() => void> = [];

function renderTree(overrides: Partial<UseTrainRevealTreeOptions> = {}) {
  const initialProps: UseTrainRevealTreeOptions = {
    startFen: START_FEN,
    active: true,
    chips: [YOUR, BEST, GAME],
    ...overrides,
  };
  const rendered = renderHook((props: UseTrainRevealTreeOptions) => useTrainRevealTree(props), {
    initialProps,
  });
  unmounts.push(rendered.unmount);
  return rendered;
}

beforeEach(() => {
  mockPlaySound.mockClear();
  engineState.scoresByFen = {};
  engineState.defaultScoreCp = 20;
  engineState.pvFirstMove = 'a7a6';
  engineState.isAnalyzing = false;
  engineState.currentFen = null;
  engineState.lastMultiPv = null;
  engineState.lastEnabled = null;
  engineState.lastFen = null;
});

afterEach(() => {
  unmounts.forEach((unmount) => unmount());
  unmounts = [];
  localStorage.removeItem(SETTINGS_STORAGE_KEYS.sfLines);
  localStorage.removeItem(SETTINGS_STORAGE_KEYS.sfArrows);
});

describe('useTrainRevealTree seeding', () => {
  it('seeds nothing while the hook is inactive (T-190-16 / T-237-04)', () => {
    const { result } = renderTree({ active: false });
    expect(result.current.nodes.size).toBe(0);
    expect(result.current.currentNodeId).toBeNull();
    expect(result.current.linePaths).toEqual({ your: [], best: [], game: [] });
  });

  it('seeds every chip line as a root branch, parked at the puzzle position with You focused', () => {
    const { result } = renderTree();

    expect(result.current.nodes.size).toBe(6); // 3 + 2 + 1
    expect(result.current.isAtRoot).toBe(true);
    expect(result.current.fen).toBe(START_FEN);
    expect(result.current.rootFocus).toBe('your');
    expect(result.current.activeChip).toBe('your');
    expect(result.current.linePaths.your).toHaveLength(3);
    expect(result.current.linePaths.best).toHaveLength(2);
    expect(result.current.linePaths.game).toHaveLength(1);
    // The three lines are roots' children, not one chain.
    const rootChildren = [...result.current.nodes.values()].filter((n) => n.parentId === null);
    expect(rootChildren).toHaveLength(3);
    expect(mockPlaySound).not.toHaveBeenCalled();
  });

  it('seeds when the hook becomes active and empties the tree again when it deactivates', () => {
    const { result, rerender } = renderTree({ active: false });
    expect(result.current.nodes.size).toBe(0);

    rerender({ startFen: START_FEN, active: true, chips: [YOUR, BEST, GAME] });
    expect(result.current.nodes.size).toBe(6);

    rerender({ startFen: START_FEN, active: false, chips: [YOUR, BEST, GAME] });
    expect(result.current.nodes.size).toBe(0);
  });

  it('a new array identity carrying the same lines does not rebuild the tree', () => {
    const { result, rerender } = renderTree();
    const nodesBefore = result.current.nodes;

    rerender({
      startFen: START_FEN,
      active: true,
      chips: [{ ...YOUR }, { ...BEST }, { ...GAME }],
    });

    expect(result.current.nodes).toBe(nodesBefore);
  });

  it('re-seeds a fresh tree for a new puzzle position', () => {
    const { result, rerender } = renderTree();

    rerender({
      startFen: OTHER_FEN,
      active: true,
      chips: [{ key: 'your', lineUcis: ['g1f3', 'b8c6'] }],
    });

    expect(result.current.nodes.size).toBe(2);
    expect(result.current.fen).toBe(OTHER_FEN);
    expect(result.current.rootFocus).toBe('your');
  });
});

describe('useTrainRevealTree chip focus (tracer)', () => {
  it('selectChip at the root focuses that chip and stays at the root', () => {
    const { result } = renderTree();

    act(() => result.current.selectChip('best'));

    expect(result.current.rootFocus).toBe('best');
    expect(result.current.activeChip).toBe('best');
    expect(result.current.isAtRoot).toBe(true);
  });

  it('a focus that no chip carries is no active chip', () => {
    const { result } = renderTree({ chips: [YOUR] });

    act(() => result.current.selectChip('game'));

    expect(result.current.rootFocus).toBe('game');
    expect(result.current.activeChip).toBeNull();
  });

  it('away from the root the active chip is the owner of the shown position', () => {
    const { result } = renderTree();
    const bestSecond = result.current.linePaths.best![1]!;

    act(() => result.current.goToNode(bestSecond));

    expect(result.current.activeChip).toBe('best');
    expect(result.current.rootFocus).toBe('your'); // root focus is untouched
  });
});

describe('useTrainRevealTree late lines', () => {
  it('a game chip arriving in a later render grafts in place and never moves the board', () => {
    const { result, rerender } = renderTree({ chips: [YOUR, BEST] });
    expect(result.current.nodes.size).toBe(5);
    const d7d5 = result.current.linePaths.best![1]!;
    act(() => result.current.goToNode(d7d5));
    expect(result.current.currentNodeId).toBe(d7d5);
    mockPlaySound.mockClear();

    rerender({ startFen: START_FEN, active: true, chips: [YOUR, BEST, GAME] });

    expect(result.current.nodes.size).toBe(6);
    expect(result.current.currentNodeId).toBe(d7d5); // Pitfall 1: not yanked
    expect(result.current.fen).toBe(result.current.nodes.get(d7d5)?.fen);
    expect(result.current.linePaths.game).toHaveLength(1);
    expect(mockPlaySound).not.toHaveBeenCalled();
  });

  it('a line that grows (its search resolved) only adds the new tail', () => {
    const { result, rerender } = renderTree({ chips: [{ key: 'your', lineUcis: ['e2e4'] }] });
    expect(result.current.nodes.size).toBe(1);
    const firstId = result.current.linePaths.your![0]!;

    rerender({ startFen: START_FEN, active: true, chips: [YOUR] });

    expect(result.current.nodes.size).toBe(3);
    expect(result.current.linePaths.your![0]).toBe(firstId); // reused, not duplicated
    expect(result.current.linePaths.your).toHaveLength(3);
  });

  it('caps a pre-loaded line at MAX_LINE_PLIES (D-03)', () => {
    const long = [
      'e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4', 'f8c5',
      'c2c3', 'g8f6', 'd2d3', 'd7d6', 'b1d2', 'c8e6',
      'c4b3', 'd8d7',
    ];
    const { result } = renderTree({ chips: [{ key: 'your', lineUcis: long }] });

    expect(result.current.nodes.size).toBe(12);
    expect(walkLinePath(result.current.nodes, long)).toHaveLength(12);
  });
});

// ─── Task 2: navigation, forks and the list view ─────────────────────────────

describe('useTrainRevealTree forward navigation', () => {
  it('forward at the puzzle position enters the ACTIVE chip, not the lowest-id node (Pitfall 3)', () => {
    // BEST is seeded first, so its first node has the lowest id.
    const { result } = renderTree({ chips: [BEST, YOUR] });
    const bestFirst = result.current.linePaths.best![0]!;
    const yourFirst = result.current.linePaths.your![0]!;
    expect(bestFirst).toBeLessThan(yourFirst);

    act(() => result.current.goForward()); // default focus: You
    expect(result.current.currentNodeId).toBe(yourFirst);

    act(() => result.current.goToRoot());
    act(() => result.current.selectChip('best'));
    act(() => result.current.goForward());
    expect(result.current.currentNodeId).toBe(bestFirst);
  });

  it('below the root it returns to the last-visited child, then follows the known line', () => {
    const { result } = renderTree();
    const [e4, e5] = result.current.linePaths.your!;

    act(() => result.current.goToNode(e4!));
    act(() => result.current.playMove('c7', 'c5')); // a free sideline off 1.e4
    const sideline = result.current.currentNodeId!;
    expect(sideline).not.toBe(e5);

    act(() => result.current.goBack());
    act(() => result.current.goForward());
    expect(result.current.currentNodeId).toBe(sideline); // last visited wins

    act(() => result.current.goBack());
    act(() => result.current.goToNode(e5!));
    act(() => result.current.goBack());
    act(() => result.current.goForward());
    expect(result.current.currentNodeId).toBe(e5); // now e5 is the last visited
  });

  it('reports canGoForward / canGoBack for the position', () => {
    const { result } = renderTree();
    expect(result.current.canGoBack).toBe(false);
    expect(result.current.canGoForward).toBe(true);

    const last = result.current.linePaths.game![0]!;
    act(() => result.current.goToNode(last));
    expect(result.current.canGoBack).toBe(true);
    expect(result.current.canGoForward).toBe(false); // the game line is one move long
  });
});

describe('useTrainRevealTree user moves (D-04, D-13)', () => {
  it('a root move onto a chip line lands on its node, is a board move (not a fork) and focuses the chip', () => {
    const onUserMove = vi.fn();
    const onChipSelect = vi.fn();
    const { result } = renderTree({ onUserMove, onChipSelect });
    act(() => result.current.selectChip('best'));
    onChipSelect.mockClear();
    const nodesBefore = result.current.nodes.size;

    let legal = false;
    act(() => {
      legal = result.current.playMove('e2', 'e4');
    });

    expect(legal).toBe(true);
    expect(result.current.nodes.size).toBe(nodesBefore); // no node created
    expect(result.current.currentNodeId).toBe(result.current.linePaths.your![0]);
    expect(result.current.rootFocus).toBe('your');
    expect(result.current.activeChip).toBe('your');
    expect(onUserMove).toHaveBeenCalledTimes(1);
    expect(onUserMove).toHaveBeenCalledWith({ source: 'board', forked: false });
    expect(onChipSelect).toHaveBeenCalledWith('your');
  });

  it('a root move that matches no chip forks, deselects every chip and lists only the user line (D-04)', () => {
    const onUserMove = vi.fn();
    const onChipSelect = vi.fn();
    const { result } = renderTree({ onUserMove, onChipSelect });

    act(() => {
      result.current.playMove('g1', 'f3');
    });

    expect(onUserMove).toHaveBeenCalledWith({ source: 'board', forked: true });
    expect(onChipSelect).not.toHaveBeenCalled();
    expect(result.current.rootFocus).toBeNull();
    expect(result.current.activeChip).toBeNull();
    expect(result.current.isOffLine).toBe(true);
    expect(result.current.listView.mainLine).toEqual([]);
    expect([...result.current.listView.nodes.keys()]).toEqual([result.current.currentNodeId]);
  });

  it('rewinding to the puzzle position with no chip focused restores the default You focus', () => {
    const { result } = renderTree();
    act(() => {
      result.current.playMove('g1', 'f3');
    });
    expect(result.current.rootFocus).toBeNull();

    act(() => result.current.goBack());
    expect(result.current.isAtRoot).toBe(true);
    expect(result.current.rootFocus).toBe('your');
    expect(result.current.activeChip).toBe('your');

    act(() => {
      result.current.playMove('g1', 'f3'); // reuses the free fork, still no chip
    });
    expect(result.current.rootFocus).toBeNull();
    act(() => result.current.goToRoot());
    expect(result.current.rootFocus).toBe('your');
  });

  it('an illegal drop returns false and reports nothing', () => {
    const onUserMove = vi.fn();
    const { result } = renderTree({ onUserMove });
    const nodesBefore = result.current.nodes;

    let legal = true;
    act(() => {
      legal = result.current.playMove('e2', 'e5');
    });

    expect(legal).toBe(false);
    expect(onUserMove).not.toHaveBeenCalled();
    expect(result.current.nodes).toBe(nodesBefore);
    expect(result.current.rootFocus).toBe('your');
  });

  it('a mid-line move forks a free child that belongs to the line it hangs off; re-tapping that chip stays put', () => {
    const onUserMove = vi.fn();
    const { result } = renderTree({ onUserMove });
    const e4 = result.current.linePaths.your![0]!;
    act(() => result.current.goToNode(e4));

    act(() => {
      result.current.playMove('c7', 'c5');
    });

    const free = result.current.currentNodeId!;
    expect(free).not.toBe(e4);
    expect(onUserMove).toHaveBeenCalledWith({ source: 'board', forked: true });
    expect(result.current.isOffLine).toBe(true);
    expect(result.current.activeChip).toBe('your');
    expect(result.current.rootFocus).toBe('your'); // a mid-line move never touches the root focus

    act(() => result.current.selectChip('your'));
    expect(result.current.currentNodeId).toBe(free); // Open Question 2: no jump

    act(() => result.current.selectChip('best'));
    expect(result.current.isAtRoot).toBe(true); // D-01: another chip jumps to the puzzle position
    expect(result.current.activeChip).toBe('best');
  });

  it('a chip tap from a root fork jumps to the puzzle position (no chip owns the fork)', () => {
    const { result } = renderTree();
    act(() => {
      result.current.playMove('g1', 'f3');
    });

    act(() => result.current.selectChip('your'));

    expect(result.current.isAtRoot).toBe(true);
    expect(result.current.activeChip).toBe('your');
  });

  it('playLine from a free node reports ONE engine-line fork and lands on its end; replaying it is not a fork', () => {
    const onUserMove = vi.fn();
    const { result } = renderTree({ onUserMove });
    act(() => {
      result.current.playMove('g1', 'f3');
    });
    const fork = result.current.currentNodeId!;
    onUserMove.mockClear();

    act(() => result.current.playLine(['g8f6', 'b1c3']));

    expect(onUserMove).toHaveBeenCalledTimes(1);
    expect(onUserMove).toHaveBeenCalledWith({ source: 'engine-line', forked: true });
    const landed = result.current.nodes.get(result.current.currentNodeId!);
    expect(landed?.san).toBe('Nc3');
    expect(result.current.currentPathUcis).toEqual(['g1f3', 'g8f6', 'b1c3']);

    act(() => result.current.goToNode(fork));
    onUserMove.mockClear();
    act(() => result.current.playLine(['g8f6', 'b1c3']));

    expect(onUserMove).toHaveBeenCalledWith({ source: 'engine-line', forked: false });
    expect(result.current.nodes.get(result.current.currentNodeId!)?.san).toBe('Nc3');
  });
});

describe('useTrainRevealTree step reporting', () => {
  it('goBack / goForward / goToNode report a user step; goToRoot and selectChip do not', () => {
    const onUserStep = vi.fn();
    const { result } = renderTree({ onUserStep });
    const [e4, e5] = result.current.linePaths.your!;

    act(() => result.current.goForward());
    expect(onUserStep).toHaveBeenCalledTimes(1);
    act(() => result.current.goToNode(e5!));
    expect(onUserStep).toHaveBeenCalledTimes(2);
    act(() => result.current.goBack());
    expect(onUserStep).toHaveBeenCalledTimes(3);
    expect(result.current.currentNodeId).toBe(e4);

    act(() => result.current.goToRoot());
    act(() => result.current.selectChip('best'));
    expect(onUserStep).toHaveBeenCalledTimes(3);
  });

  it('does not report a step that could not move', () => {
    const onUserStep = vi.fn();
    const { result } = renderTree({ onUserStep });

    act(() => result.current.goBack()); // already at the puzzle position
    act(() => result.current.goToNode(9999)); // unknown node

    expect(onUserStep).not.toHaveBeenCalled();
  });

  it('goToNode on the node the board is already on is not a user step (WR-04)', () => {
    const onUserStep = vi.fn();
    const { result } = renderTree({ onUserStep });
    const [e4] = result.current.linePaths.your!;

    act(() => result.current.goToNode(e4!));
    expect(onUserStep).toHaveBeenCalledTimes(1);
    act(() => result.current.goToNode(e4!)); // same node again: a no-op tap
    expect(onUserStep).toHaveBeenCalledTimes(1);
  });

  it('keeps stable command identities across renders', () => {
    const { result, rerender } = renderTree();
    const before = result.current;

    rerender({ startFen: START_FEN, active: true, chips: [YOUR, BEST, GAME] });

    expect(result.current.goBack).toBe(before.goBack);
    expect(result.current.goForward).toBe(before.goForward);
    expect(result.current.playMove).toBe(before.playMove);
    expect(result.current.selectChip).toBe(before.selectChip);
  });
});

describe('useTrainRevealTree deleteLine', () => {
  it('removes a free subtree, recovers the board to its parent and ignores known-line ids', () => {
    const { result } = renderTree();
    const e4 = result.current.linePaths.your![0]!;
    act(() => result.current.goToNode(e4));
    act(() => {
      result.current.playMove('c7', 'c5');
    });
    const free = result.current.currentNodeId!;
    const sizeWithFree = result.current.nodes.size;

    act(() => result.current.deleteLine(e4)); // a known-line node: ignored
    expect(result.current.nodes.size).toBe(sizeWithFree);

    act(() => result.current.deleteLine(free));
    expect(result.current.nodes.size).toBe(sizeWithFree - 1);
    expect(result.current.nodes.has(free)).toBe(false);
    expect(result.current.currentNodeId).toBe(e4);
  });

  it('closing the root fork while no chip is focused restores the default focus', () => {
    const { result } = renderTree();
    act(() => {
      result.current.playMove('g1', 'f3');
    });
    const fork = result.current.currentNodeId!;
    expect(result.current.rootFocus).toBeNull();

    act(() => result.current.deleteLine(fork));

    expect(result.current.isAtRoot).toBe(true);
    expect(result.current.rootFocus).toBe('your');
    expect(result.current.activeChip).toBe('your');
  });
});

describe('useTrainRevealTree list view', () => {
  it('shows the active line, its free sidelines and the root forks, and nothing from the other chips', () => {
    const { result } = renderTree();
    const yourFirst = result.current.linePaths.your![0]!;
    const bestFirst = result.current.linePaths.best![0]!;

    act(() => result.current.goToNode(yourFirst));
    act(() => {
      result.current.playMove('c7', 'c5'); // free, hangs off You
    });
    const freeOffYour = result.current.currentNodeId!;
    act(() => result.current.goToNode(bestFirst));
    act(() => {
      result.current.playMove('g8', 'f6'); // free, hangs off Best
    });
    const freeOffBest = result.current.currentNodeId!;
    act(() => result.current.goToRoot());
    act(() => {
      result.current.playMove('g1', 'f3'); // free root fork
    });
    const rootFork = result.current.currentNodeId!;

    act(() => result.current.selectChip('best'));

    const { nodes, mainLine } = result.current.listView;
    expect(mainLine).toEqual(result.current.linePaths.best);
    const shown = new Set(nodes.keys());
    expect(shown).toEqual(new Set([...result.current.linePaths.best!, freeOffBest, rootFork]));
    expect(shown.has(freeOffYour)).toBe(false);
    for (const id of result.current.linePaths.your!) expect(shown.has(id)).toBe(false);
    for (const id of result.current.linePaths.game!) expect(shown.has(id)).toBe(false);
  });
});

describe('useTrainRevealTree step info', () => {
  it('reports the line position on known nodes, and null at the root and on free nodes', () => {
    const { result } = renderTree();
    const [e4, e5, nf3] = result.current.linePaths.your!;
    expect(result.current.stepInfo).toBeNull();
    expect(result.current.currentPathUcis).toEqual([]);
    expect(result.current.lastMove).toBeNull();

    act(() => result.current.goToNode(e4!));
    expect(result.current.stepInfo).toEqual({
      line: 'your',
      index: 0,
      lastMoveUci: 'e2e4',
      nextMoveUci: 'e7e5',
      isFirstMove: true,
    });
    expect(result.current.lastMove).toEqual({ from: 'e2', to: 'e4' });

    act(() => result.current.goToNode(e5!));
    expect(result.current.stepInfo).toMatchObject({ index: 1, nextMoveUci: 'g1f3', isFirstMove: false });
    expect(result.current.currentPathUcis).toEqual(['e2e4', 'e7e5']);

    act(() => result.current.goToNode(nf3!));
    expect(result.current.stepInfo).toMatchObject({ index: 2, lastMoveUci: 'g1f3', nextMoveUci: null });

    act(() => {
      result.current.playMove('b8', 'c6'); // a free move off the end of the line
    });
    expect(result.current.stepInfo).toBeNull();
    expect(result.current.currentPathUcis).toEqual(['e2e4', 'e7e5', 'g1f3', 'b8c6']);
  });

  it('numbers moves from the puzzle position ply', () => {
    const { result } = renderTree({
      startFen: OTHER_FEN, // white to move, full move 2 -> ply 2
      chips: [{ key: 'your', lineUcis: ['g1f3'] }],
    });
    expect(result.current.rootPly).toBe(2);
  });
});

describe('useTrainRevealTree keyboard', () => {
  function press(key: string): void {
    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }));
    });
  }

  function mountBoard(): { ref: { current: HTMLDivElement }; remove: () => void } {
    const div = document.createElement('div');
    document.body.appendChild(div);
    return { ref: { current: div }, remove: () => div.remove() };
  }

  it('ArrowRight / ArrowLeft step the active line and Home returns to the puzzle position', () => {
    const board = mountBoard();
    const { result } = renderTree({ navContainerRef: board.ref });
    const [e4, e5] = result.current.linePaths.your!;

    press('ArrowRight');
    expect(result.current.currentNodeId).toBe(e4);
    press('ArrowRight');
    expect(result.current.currentNodeId).toBe(e5);
    press('ArrowLeft');
    expect(result.current.currentNodeId).toBe(e4);
    press('Home');
    expect(result.current.isAtRoot).toBe(true);
    board.remove();
  });

  it('is inert before the verdict (inactive) and without a board wrapper', () => {
    const board = mountBoard();
    const inactive = renderTree({ active: false, navContainerRef: board.ref });
    press('ArrowRight');
    expect(inactive.result.current.currentNodeId).toBeNull();
    expect(inactive.result.current.nodes.size).toBe(0);

    const noRef = renderTree();
    press('ArrowRight');
    expect(noRef.result.current.currentNodeId).toBeNull();
    board.remove();
  });
});

// ─── Task 3: snapshot and restore as UCI paths ───────────────────────────────

/**
 * Builds the tree the round-trip tests snapshot: a free ROOT fork (1.Nf3) and a
 * free sideline off the Best line (1.d4 Nf6), focused on Best and parked on the
 * sideline's tip.
 */
function playSidelinedTree() {
  const rendered = renderTree();
  const { result } = rendered;
  act(() => {
    result.current.playMove('g1', 'f3'); // free root fork (no chip owns it)
  });
  act(() => result.current.selectChip('best'));
  act(() => result.current.goToNode(result.current.linePaths.best![0]!));
  act(() => {
    result.current.playMove('g8', 'f6'); // free sideline off 1.d4
  });
  return rendered;
}

describe('useTrainRevealTree snapshot / restore', () => {
  it('snapshots the focus, the shown path and every free leaf as UCI paths', () => {
    const { result } = playSidelinedTree();

    expect(result.current.snapshot()).toEqual({
      rootFocus: 'best',
      currentPath: ['d2d4', 'g8f6'],
      sidelinePaths: [['g1f3'], ['d2d4', 'g8f6']],
    });
  });

  it('a snapshot of an untouched tree has no sidelines and sits at the root', () => {
    const { result } = renderTree();

    expect(result.current.snapshot()).toEqual({
      rootFocus: 'your',
      currentPath: [],
      sidelinePaths: [],
    });
  });

  it('round-trips: a fresh hook rebuilds both sidelines, the focus and the shown node, silently', () => {
    const original = playSidelinedTree();
    const snapshot = original.result.current.snapshot();
    const nodeCount = original.result.current.nodes.size;
    mockPlaySound.mockClear();

    const { result } = renderTree({ restored: snapshot });

    expect(result.current.nodes.size).toBe(nodeCount);
    expect(result.current.rootFocus).toBe('best');
    expect(result.current.activeChip).toBe('best');
    expect(result.current.currentPathUcis).toEqual(['d2d4', 'g8f6']);
    expect(result.current.isOffLine).toBe(true);
    expect(result.current.snapshot()).toEqual(snapshot);
    expect(mockPlaySound).not.toHaveBeenCalled();
  });

  it('restores to the puzzle position with the saved focus when nothing was stepped into', () => {
    const snapshot: RevealTreeSnapshot = { rootFocus: 'game', currentPath: [], sidelinePaths: [] };

    const { result } = renderTree({ restored: snapshot });

    expect(result.current.isAtRoot).toBe(true);
    expect(result.current.rootFocus).toBe('game');
    expect(result.current.activeChip).toBe('game');
  });

  it('restoring before the game chip exists, then the chip arriving, duplicates nothing and keeps the board', () => {
    const original = renderTree();
    act(() => original.result.current.goToNode(original.result.current.linePaths.game![0]!));
    const snapshot = original.result.current.snapshot();
    expect(snapshot.currentPath).toEqual(['c2c4']);
    const fullCount = original.result.current.nodes.size;

    const { result, rerender } = renderTree({ chips: [YOUR, BEST], restored: snapshot });
    const restoredNode = result.current.currentNodeId;
    expect(result.current.currentPathUcis).toEqual(['c2c4']);
    expect(result.current.activeChip).toBeNull(); // no chip owns it yet: a root fork

    rerender({ startFen: START_FEN, active: true, chips: [YOUR, BEST, GAME], restored: snapshot });

    expect(result.current.nodes.size).toBe(fullCount); // child reuse
    expect(result.current.currentNodeId).toBe(restoredNode);
    expect(result.current.activeChip).toBe('game'); // now derived from the arrived line
  });

  it('applies once per puzzle position: a closed sideline is not resurrected by a re-render', () => {
    const original = playSidelinedTree();
    const snapshot = original.result.current.snapshot();
    const { result, rerender } = renderTree({ restored: snapshot });
    const tip = result.current.currentNodeId!;

    act(() => result.current.deleteLine(tip));
    const sizeAfterDelete = result.current.nodes.size;
    rerender({ startFen: START_FEN, active: true, chips: [YOUR, BEST, GAME], restored: snapshot });

    expect(result.current.nodes.size).toBe(sizeAfterDelete);
    expect(result.current.nodes.has(tip)).toBe(false);
  });

  it('applies nothing while inactive (T-237-04) and rebuilds once the hook activates', () => {
    const original = playSidelinedTree();
    const snapshot = original.result.current.snapshot();
    const { result, rerender } = renderTree({ active: false, restored: snapshot });
    expect(result.current.nodes.size).toBe(0);

    rerender({ startFen: START_FEN, active: true, chips: [YOUR, BEST, GAME], restored: snapshot });

    expect(result.current.currentPathUcis).toEqual(['d2d4', 'g8f6']);
    expect(result.current.rootFocus).toBe('best');
  });

  it('restores only the legal prefix of a path with an illegal move and never throws', () => {
    const snapshot: RevealTreeSnapshot = {
      rootFocus: null,
      currentPath: ['g1f3', 'g1f3', 'b8c6'],
      sidelinePaths: [['a1a8'], ['g1f3', 'g1f3']],
    };

    let rendered: ReturnType<typeof renderTree> | undefined;
    expect(() => {
      rendered = renderTree({ chips: [], restored: snapshot });
    }).not.toThrow();

    expect(rendered?.result.current.nodes.size).toBe(1); // only 1.Nf3
    expect(rendered?.result.current.currentPathUcis).toEqual(['g1f3']);
    expect(rendered?.result.current.rootFocus).toBeNull();
  });

  it('replays at most REVEAL_TREE_SNAPSHOT_MAX_PATHS paths (T-237-05)', () => {
    const paths: string[][] = [];
    for (const first of ['e2e4', 'd2d4']) {
      const chess = new Chess();
      chess.move({ from: first.slice(0, 2), to: first.slice(2, 4) });
      for (const reply of chess.moves({ verbose: true })) paths.push([first, reply.from + reply.to]);
    }
    expect(paths.length).toBe(40);

    const { result } = renderTree({
      chips: [],
      restored: { rootFocus: null, currentPath: [], sidelinePaths: paths },
    });

    // 20 replies under 1.e4 (21 nodes) + 12 of the 20 under 1.d4 (13 nodes) = 34, not 42.
    expect(REVEAL_TREE_SNAPSHOT_MAX_PATHS).toBe(32);
    expect(result.current.nodes.size).toBe(34);
  });

  it('replays at most REVEAL_TREE_SNAPSHOT_MAX_PLIES plies of one path', () => {
    const shuffle = ['g1f3', 'g8f6', 'f3g1', 'f6g8'];
    const longPath = Array.from({ length: 80 }, (_, i) => shuffle[i % shuffle.length]!);

    const { result } = renderTree({
      chips: [],
      restored: { rootFocus: null, currentPath: longPath, sidelinePaths: [] },
    });

    expect(REVEAL_TREE_SNAPSHOT_MAX_PLIES).toBe(64);
    expect(result.current.currentPathUcis).toHaveLength(64);
  });
});

// ── Grading of the user's own sideline moves (lifted from the free-play hook) ─

/** The FEN chess.js reaches after playing `sans` from `fen`: the key the mocked
 * engine's `scoresByFen` script is addressed by. */
function fenAfter(fen: string, ...sans: string[]): string {
  const chess = new Chess(fen);
  for (const san of sans) chess.move(san);
  return chess.fen();
}

/** White to move; Qb6 (b2b6) is legal and STALEMATES black (verified with
 * chess.js). The terminal-precedence bounding case's board. */
const STALEMATE_IN_ONE_FEN = 'k7/7R/8/8/8/8/1Q6/7K w - - 0 1';

/** A grading-engine seed: the mount search's rank-1 verdict for the puzzle
 * position plus the SERVED vetted list (the same `verdict.vetted_moves` the
 * reveal overlay draws, one key, two readers). */
function makeSeed(
  vettedMoves: TrainFineMove[],
  opts: { cp?: number; bestUci?: string } = {},
): TreeSeedEval {
  return { cp: opts.cp ?? 30, mate: null, bestUci: opts.bestUci ?? 'e2e4', vettedMoves };
}

/** A tree with NO known lines, so every move the test plays is a free sideline move. */
function renderGraded(startFen: string, seedEval: TreeSeedEval | null) {
  return renderTree({ startFen, chips: [], seedEval });
}

describe('useTrainRevealTree: root-ply grading reads the served vetted key (D-06)', () => {
  it("SEED-137 case 2: a served vetted move forked at the ROOT ply badges with the entry's own server quality, never the engine's (worse) fresh search", () => {
    // The engine's own post-d2d4 reading is CATASTROPHIC (-900 white-POV, far
    // past BLUNDER_DROP against the +30 seed), so a build that grades this root
    // move from the engine pair badges it a blunder. The SERVER's key says d2d4
    // is good; the badge must read the key.
    engineState.scoresByFen[fenAfter(START_FEN, 'd4')] = -900;
    const { result } = renderGraded(START_FEN, makeSeed([{ uci: 'd2d4', quality: 'good' }]));

    act(() => {
      result.current.playMove('d2', 'd4');
    });

    expect(result.current.boardMarkers).toEqual([{ square: 'd4', good: true }]);
    // The move-list badge is the same verdict, never a severity glyph.
    const nodeId = result.current.currentNodeId;
    expect(nodeId).not.toBeNull();
    const marker = result.current.moveListMarkers.get(nodeId!);
    expect(marker?.good).toBe(true);
    expect(marker?.severity).toBeUndefined();
  });

  it("the engine's own top move still wins the badge: a vetted move that is ALSO the engine's best reads best, not good", () => {
    // e2e4 is BOTH the seed's bestUci and a served vetted entry: the is-best
    // check must run before the key lookup, so the badge is 'best'.
    const seed = makeSeed(
      [
        { uci: 'e2e4', quality: 'good' },
        { uci: 'd2d4', quality: 'good' },
      ],
      { bestUci: 'e2e4' },
    );
    const { result } = renderGraded(START_FEN, seed);

    act(() => {
      result.current.playMove('e2', 'e4');
    });

    expect(result.current.boardMarkers).toEqual([{ square: 'e4', best: true }]);
  });

  it("the DEEP best played at the root badges 'best' from its vetted entry, even when the client engine's own top move differs (D-01 amendment)", () => {
    // The served list leads with the deep best (d2d4, quality 'best'); the
    // client engine's own top move is e2e4, so the is-best check misses and the
    // key lookup must supply the badge. Scripted so the engine pair would
    // otherwise grade d2d4 a blunder.
    engineState.scoresByFen[fenAfter(START_FEN, 'd4')] = -900;
    const seed = makeSeed(
      [
        { uci: 'd2d4', quality: 'best' },
        { uci: 'g1f3', quality: 'good' },
      ],
      { bestUci: 'e2e4' },
    );
    const { result } = renderGraded(START_FEN, seed);

    act(() => {
      result.current.playMove('d2', 'd4');
    });

    expect(result.current.boardMarkers).toEqual([{ square: 'd4', best: true }]);
  });

  it('a vetted move played at a DEEPER ply (not the root) is graded by the engine, not the key: the key describes a different position', () => {
    // d7d5 is on the served list, but it is played as the SECOND sideline move.
    // Below the root, parent and child evals both come from the one reveal
    // engine (already self-consistent); the key must never be consulted there.
    // Scripted so the engine pair grades it a blunder.
    engineState.scoresByFen[fenAfter(START_FEN, 'e4')] = 30;
    engineState.scoresByFen[fenAfter(START_FEN, 'e4', 'd5')] = 900;
    const seed = makeSeed([{ uci: 'd7d5', quality: 'good' }], { bestUci: 'e2e4' });
    const { result } = renderGraded(START_FEN, seed);

    act(() => {
      result.current.playMove('e2', 'e4');
    });
    act(() => {
      result.current.playMove('d7', 'd5');
    });

    expect(result.current.boardMarkers).toEqual([{ square: 'd5', severity: 'blunder' }]);
  });

  it('a terminal root move still wins over the key: a stalemating move on the vetted list badges from the rules, not the served quality', () => {
    // White is completely winning (+900 seed) and throws it all away with a
    // stalemate: the rules-derived eval (cp 0) grades it a blunder. The served
    // key claims b2b6 is good; terminal precedence must beat it.
    const seed = makeSeed([{ uci: 'b2b6', quality: 'good' }], { cp: 900, bestUci: 'h7h8' });
    const { result } = renderGraded(STALEMATE_IN_ONE_FEN, seed);

    act(() => {
      result.current.playMove('b2', 'b6');
    });

    expect(result.current.boardMarkers).toEqual([{ square: 'b6', severity: 'blunder' }]);
  });

  it('an OFF-key root move still grades from the engine exactly as today (D-04 residual)', () => {
    // b1c3 is legal but NOT on the served list: the accepted-residual seam,
    // esBefore from the seed, esAfter from the engine's own scripted search.
    engineState.scoresByFen[fenAfter(START_FEN, 'Nc3')] = -900;
    const { result } = renderGraded(START_FEN, makeSeed([{ uci: 'd2d4', quality: 'good' }]));

    act(() => {
      result.current.playMove('b1', 'c3');
    });

    expect(result.current.boardMarkers).toEqual([{ square: 'c3', severity: 'blunder' }]);
  });

  it('an EMPTY vetted list falls back to the engine path and does not throw (sharp / sharp filler / degenerate blob / pre-211 restored verdict)', () => {
    engineState.scoresByFen[fenAfter(START_FEN, 'd4')] = -900;
    const { result } = renderGraded(START_FEN, makeSeed([]));

    act(() => {
      result.current.playMove('d2', 'd4');
    });

    expect(result.current.boardMarkers).toEqual([{ square: 'd4', severity: 'blunder' }]);
  });

  it('closing the sideline and a new puzzle drop the per-node badges', () => {
    engineState.scoresByFen[fenAfter(START_FEN, 'd4')] = -900;
    const { result, rerender } = renderGraded(START_FEN, makeSeed([{ uci: 'd2d4', quality: 'good' }]));

    act(() => {
      result.current.playMove('d2', 'd4');
    });
    expect(result.current.moveListMarkers.size).toBe(1);

    // A new puzzle restarts the tree's node ids at 0: a stale badge must not
    // attach itself to an unrelated new node.
    rerender({ startFen: OTHER_FEN, active: true, chips: [], seedEval: null });
    expect(result.current.moveListMarkers.size).toBe(0);
    expect(result.current.boardMarkers).toEqual([]);
  });

  it('known-line moves are not graded here (they keep the step overlay)', () => {
    const { result } = renderTree({ seedEval: makeSeed([]) });

    act(() => {
      result.current.playMove('e2', 'e4'); // the You line's first move
    });

    expect(result.current.isOffLine).toBe(false);
    expect(result.current.boardMarkers).toEqual([]);
    expect(result.current.moveListMarkers.size).toBe(0);
  });

  it('a fork off a stepped known-line position is graded: the position was searched while the board sat there', () => {
    // Step onto the You line's e4 (the engine caches that position's eval and
    // best move), then fork with a different reply. Scripted so the engine pair
    // grades the fork a blunder.
    engineState.scoresByFen[fenAfter(START_FEN, 'e4')] = 30;
    engineState.scoresByFen[fenAfter(START_FEN, 'e4', 'c5')] = 900;
    const { result } = renderTree({ seedEval: makeSeed([]) });

    act(() => {
      result.current.playMove('e2', 'e4'); // along the You line
    });
    act(() => {
      result.current.playMove('c7', 'c5'); // not the line's e5: a fork
    });

    expect(result.current.isOffLine).toBe(true);
    expect(result.current.boardMarkers).toEqual([{ square: 'c5', severity: 'blunder' }]);
  });
});

describe('useTrainRevealTree: the one reveal engine', () => {
  function multiPvFor(sfLines?: number, sfArrows?: number): number | null {
    if (sfLines !== undefined) localStorage.setItem(SETTINGS_STORAGE_KEYS.sfLines, String(sfLines));
    if (sfArrows !== undefined) localStorage.setItem(SETTINGS_STORAGE_KEYS.sfArrows, String(sfArrows));
    const { result } = renderTree();
    act(() => {
      result.current.playMove('d2', 'd4'); // matches the Best line's first move: still known
    });
    expect(result.current.isOffLine).toBe(false);
    act(() => {
      result.current.playMove('g8', 'f6'); // not the line's d5: off the known lines
    });
    expect(result.current.isOffLine).toBe(true);
    return engineState.lastMultiPv;
  }

  it('runs MultiPV 1 at the puzzle position and on the known lines', () => {
    const { result } = renderTree();
    expect(engineState.lastMultiPv).toBe(1);
    act(() => {
      result.current.playMove('e2', 'e4');
    });
    expect(result.current.isOffLine).toBe(false);
    expect(engineState.lastMultiPv).toBe(1);
  });

  it('off the known lines the default settings (1 arrow) search at MultiPV 2', () => {
    expect(multiPvFor()).toBe(2);
  });

  it('Stockfish arrows 3 search at MultiPV 3 off the lines', () => {
    expect(multiPvFor(undefined, 3)).toBe(3);
  });

  it('Stockfish arrows 0 still search at MultiPV 2 off the lines (the row needs two)', () => {
    expect(multiPvFor(undefined, 0)).toBe(2);
  });

  it('follows the shown position and stays off while the engine is disabled or the reveal inactive', () => {
    const { result, rerender } = renderTree();
    expect(engineState.lastEnabled).toBe(true);
    expect(engineState.lastFen).toBe(START_FEN);

    act(() => {
      result.current.playMove('e2', 'e4');
    });
    expect(engineState.lastFen).toBe(fenAfter(START_FEN, 'e4'));

    rerender({ startFen: START_FEN, active: true, chips: [YOUR, BEST, GAME], engineEnabled: false });
    expect(engineState.lastEnabled).toBe(false);
    expect(result.current.evalReading).toEqual({ evalCp: null, evalMate: null, depth: 0 });

    rerender({ startFen: START_FEN, active: false, chips: [YOUR, BEST, GAME] });
    expect(engineState.lastEnabled).toBe(false);
    expect(engineState.lastFen).toBeNull();
  });

  it('exposes a staleness-guarded reading and lines: nothing until the engine has reached the shown position', () => {
    engineState.scoresByFen[START_FEN] = 55;
    engineState.currentFen = 'some other position';
    const { result, rerender } = renderTree();
    expect(result.current.pvLines).toEqual([]);
    expect(result.current.evalReading).toEqual({ evalCp: null, evalMate: null, depth: 0 });

    engineState.currentFen = null;
    rerender({ startFen: START_FEN, active: true, chips: [YOUR, BEST, GAME] });
    expect(result.current.evalReading).toEqual({ evalCp: 55, evalMate: null, depth: 10 });
    expect(result.current.pvLines).toHaveLength(1);
  });
});

describe('useTrainRevealTree: onUserMove counting (Phase 233 D-14, Phase 237 D-13)', () => {
  it('counts one board move per legal playMove and never a rejected one', () => {
    const onUserMove = vi.fn();
    const { result } = renderTree({ chips: [], onUserMove });

    let played = false;
    act(() => {
      played = result.current.playMove('e2', 'e4');
    });
    expect(played).toBe(true);
    expect(onUserMove).toHaveBeenCalledTimes(1);
    expect(onUserMove).toHaveBeenCalledWith({ source: 'board', forked: true });

    act(() => {
      played = result.current.playMove('a1', 'a8');
    });
    expect(played).toBe(false);
    expect(onUserMove).toHaveBeenCalledTimes(1);
  });

  it('counts one engine-line move per playLine', () => {
    const onUserMove = vi.fn();
    const { result } = renderTree({ chips: [], onUserMove });
    act(() => result.current.playLine(['e2e4', 'e7e5']));
    expect(onUserMove).toHaveBeenCalledTimes(1);
    expect(onUserMove).toHaveBeenCalledWith({ source: 'engine-line', forked: true });
  });

  it('never counts goBack, goForward, goToRoot, goToNode, selectChip or deleteLine', () => {
    const onUserMove = vi.fn();
    const { result } = renderTree({ onUserMove });
    act(() => {
      result.current.playMove('a2', 'a3');
    });
    act(() => {
      result.current.playMove('a7', 'a6');
    });
    onUserMove.mockClear();

    act(() => result.current.goBack());
    act(() => result.current.goForward());
    act(() => result.current.goToRoot());
    act(() => result.current.goToNode(0));
    act(() => result.current.selectChip('best'));
    act(() => result.current.deleteLine(result.current.currentNodeId ?? 0));
    expect(onUserMove).not.toHaveBeenCalled();
  });
});
