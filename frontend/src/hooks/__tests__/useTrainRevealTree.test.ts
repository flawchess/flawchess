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
import { TRAIN_LIVE_ALT_MIN_DEPTH, TRAIN_LIVE_ALT_ROOT_MULTIPV } from '@/lib/trainArrows';
import type { TrainFineMove } from '@/lib/trainArrows';
import { SETTINGS_STORAGE_KEYS } from '@/lib/engineSettings';
import {
  REVEAL_TREE_SNAPSHOT_MAX_PATHS,
  REVEAL_TREE_SNAPSHOT_MAX_PLIES,
} from '@/lib/trainRevealLines';
import type { RevealTreeSnapshot } from '@/lib/trainRevealLines';
import { TRAIN_PREVIEW_MAX_PLIES } from '@/lib/trainRevealPreview';
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
  /** Depth the mocked engine reports (the preview goes live at TRAIN_LIVE_ALT_MIN_DEPTH). */
  pvDepth: number;
  /** The rank-1 PV moves; null = just `[pvFirstMove]`. */
  pvMoves: string[] | null;
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
  pvDepth: 10,
  pvMoves: null,
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
        ? [
            {
              multipv: 1,
              depth: engineState.pvDepth,
              moves: engineState.pvMoves ?? [engineState.pvFirstMove],
              evalCp,
              evalMate: null,
            },
          ]
        : [],
      depth: live ? engineState.pvDepth : 0,
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

/** A chip's graded line (white POV eval) for the chip's first move + tail. */
function chipOf(key: RevealChipLine['key'], moves: string[], evalCp = 30): RevealChipLine {
  return { key, uci: moves[0]!, line: { moves, evalCp, evalMate: null } };
}

const YOUR: RevealChipLine = chipOf('your', YOUR_LINE);
const BEST: RevealChipLine = chipOf('best', BEST_LINE, 45);
// A one-move line has no tail, so the Game chip seeds no preview.
const GAME: RevealChipLine = chipOf('game', GAME_LINE);

/** Make the mocked engine too shallow to go live, so the seed / inherited tail shows. */
function keepSeedVisible(): void {
  engineState.pvDepth = TRAIN_LIVE_ALT_MIN_DEPTH - 1;
}

function previewSans(tree: { preview: { steps: { san: string }[] } | null }): string[] | undefined {
  return tree.preview?.steps.map((step) => step.san);
}

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
  engineState.pvDepth = 10;
  engineState.pvMoves = null;
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
  it('seeds nothing and previews nothing while the hook is inactive (T-190-16 / T-237-04 / T-261011-lwy-01)', () => {
    const { result } = renderTree({ active: false });
    expect(result.current.nodes.size).toBe(0);
    expect(result.current.currentNodeId).toBeNull();
    expect(result.current.linePaths).toEqual({ your: [], best: [], game: [] });
    expect(result.current.preview).toBeNull();
    expect(result.current.canGoForward).toBe(false);
  });

  it('seeds only each chip FIRST move as a root node, parked at the puzzle position with You focused', () => {
    const { result } = renderTree();

    expect(result.current.nodes.size).toBe(3); // one node per chip, none of the tails
    expect(result.current.isAtRoot).toBe(true);
    expect(result.current.fen).toBe(START_FEN);
    expect(result.current.rootFocus).toBe('your');
    expect(result.current.activeChip).toBe('your');
    expect(result.current.linePaths.your).toHaveLength(1);
    expect(result.current.linePaths.best).toHaveLength(1);
    expect(result.current.linePaths.game).toHaveLength(1);
    const rootChildren = [...result.current.nodes.values()].filter((n) => n.parentId === null);
    expect(rootChildren).toHaveLength(3);
    expect(mockPlaySound).not.toHaveBeenCalled();
  });

  it('seeds when the hook becomes active and empties the tree again when it deactivates', () => {
    const { result, rerender } = renderTree({ active: false });
    expect(result.current.nodes.size).toBe(0);

    rerender({ startFen: START_FEN, active: true, chips: [YOUR, BEST, GAME] });
    expect(result.current.nodes.size).toBe(3);

    rerender({ startFen: START_FEN, active: false, chips: [YOUR, BEST, GAME] });
    expect(result.current.nodes.size).toBe(0);
    expect(result.current.preview).toBeNull();
  });

  it('a new array identity carrying the same moves does not rebuild the tree', () => {
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
      chips: [chipOf('your', ['g1f3', 'b8c6'])],
    });

    expect(result.current.nodes.size).toBe(1);
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
    const bestFirst = result.current.linePaths.best![0]!;

    act(() => result.current.goToNode(bestFirst));

    expect(result.current.activeChip).toBe('best');
    expect(result.current.rootFocus).toBe('your'); // root focus is untouched
  });
});

describe('useTrainRevealTree late lines', () => {
  it('a game chip arriving in a later render grafts in place and never moves the board', () => {
    const { result, rerender } = renderTree({ chips: [YOUR, BEST] });
    expect(result.current.nodes.size).toBe(2);
    const d4 = result.current.linePaths.best![0]!;
    act(() => result.current.goToNode(d4));
    expect(result.current.currentNodeId).toBe(d4);
    mockPlaySound.mockClear();

    rerender({ startFen: START_FEN, active: true, chips: [YOUR, BEST, GAME] });

    expect(result.current.nodes.size).toBe(3);
    expect(result.current.currentNodeId).toBe(d4); // Pitfall 1: not yanked
    expect(result.current.fen).toBe(result.current.nodes.get(d4)?.fen);
    expect(result.current.linePaths.game).toHaveLength(1);
    expect(mockPlaySound).not.toHaveBeenCalled();
  });

  it('a late-arriving line adds no nodes but changes the preview steps', () => {
    keepSeedVisible();
    const { result, rerender } = renderTree({ chips: [{ ...YOUR, line: null }] });
    expect(result.current.nodes.size).toBe(1);
    expect(result.current.preview).toBeNull(); // no graded line yet: nothing to seed from

    rerender({ startFen: START_FEN, active: true, chips: [YOUR] });

    expect(result.current.nodes.size).toBe(1);
    expect(previewSans(result.current)).toEqual(['e5', 'Nf3']);
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

  it('below the root it returns to the last-visited child, then the lowest-id child', () => {
    keepSeedVisible();
    const { result } = renderTree();
    const e4 = result.current.linePaths.your![0]!;

    act(() => result.current.goToNode(e4));
    act(() => result.current.goForward()); // commits the preview's e5: first-added child
    const e5 = result.current.currentNodeId!;
    act(() => result.current.goBack());
    act(() => {
      result.current.playMove('c7', 'c5'); // a later-added sideline off 1.e4
    });
    const sideline = result.current.currentNodeId!;
    expect(sideline).not.toBe(e5);

    act(() => result.current.goBack());
    act(() => result.current.goForward());
    expect(result.current.currentNodeId).toBe(sideline); // last visited wins

    act(() => result.current.goBack());
    act(() => result.current.goToNode(e5));
    act(() => result.current.goBack());
    act(() => result.current.goForward());
    expect(result.current.currentNodeId).toBe(e5); // now e5 is the last visited
  });

  it('reports canGoForward / canGoBack for the position', () => {
    keepSeedVisible();
    const { result } = renderTree();
    expect(result.current.canGoBack).toBe(false);
    expect(result.current.canGoForward).toBe(true);

    const last = result.current.linePaths.game![0]!;
    act(() => result.current.goToNode(last));
    expect(result.current.canGoBack).toBe(true);
    // The Game line is one move long: no seed tail, no deep-enough live line, so
    // there is nothing to commit.
    expect(result.current.preview).toBeNull();
    expect(result.current.canGoForward).toBe(false);
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
    keepSeedVisible();
    const { result } = renderTree({ onUserStep });
    const [e4] = result.current.linePaths.your!;

    act(() => result.current.goForward());
    expect(onUserStep).toHaveBeenCalledTimes(1);
    act(() => result.current.goForward()); // commits the preview's e5
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
    expect(result.current.commitPreview).toBe(before.commitPreview);
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
    // The chip's first move, then the first-added continuation (the Best sideline).
    expect(mainLine).toEqual([bestFirst, freeOffBest]);
    const shown = new Set(nodes.keys());
    expect(shown).toEqual(new Set([...result.current.linePaths.best!, freeOffBest, rootFork]));
    expect(shown.has(freeOffYour)).toBe(false);
    for (const id of result.current.linePaths.your!) expect(shown.has(id)).toBe(false);
    for (const id of result.current.linePaths.game!) expect(shown.has(id)).toBe(false);
  });
});

describe('useTrainRevealTree chip move and path', () => {
  it('chipMove is set on a chip first-move node and null at the root and on later nodes', () => {
    keepSeedVisible();
    const { result } = renderTree();
    const [e4] = result.current.linePaths.your!;
    expect(result.current.chipMove).toBeNull();
    expect(result.current.currentPathUcis).toEqual([]);
    expect(result.current.lastMove).toBeNull();

    act(() => result.current.goToNode(e4!));
    expect(result.current.chipMove).toEqual({ line: 'your', uci: 'e2e4' });
    expect(result.current.lastMove).toEqual({ from: 'e2', to: 'e4' });

    act(() => result.current.goForward()); // commit e5
    expect(result.current.chipMove).toBeNull();
    expect(result.current.currentPathUcis).toEqual(['e2e4', 'e7e5']);

    act(() => result.current.goToNode(result.current.linePaths.best![0]!));
    expect(result.current.chipMove).toEqual({ line: 'best', uci: 'd2d4' });
  });

  it('numbers moves from the puzzle position ply', () => {
    const { result } = renderTree({
      startFen: OTHER_FEN, // white to move, full move 2 -> ply 2
      chips: [chipOf('your', ['g1f3'])],
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

  it('ArrowRight enters the chip then commits the preview; ArrowLeft steps back and Home returns to the puzzle position', () => {
    keepSeedVisible();
    const board = mountBoard();
    const { result } = renderTree({ navContainerRef: board.ref });
    const [e4] = result.current.linePaths.your!;

    press('ArrowRight');
    expect(result.current.currentNodeId).toBe(e4);
    press('ArrowRight');
    expect(result.current.currentPathUcis).toEqual(['e2e4', 'e7e5']);
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
      // DFS pre-order, children by ascending id: the chip nodes were seeded first.
      sidelinePaths: [['d2d4', 'g8f6'], ['g1f3']],
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
    act(() => {
      result.current.playMove('g8', 'f6'); // not the line's d5: off the known lines
    });
    return engineState.lastMultiPv;
  }

  it('runs the settings width (MultiPV 2 by default) at the puzzle position and on the known lines', () => {
    const { result } = renderTree();
    expect(engineState.lastMultiPv).toBe(2);
    act(() => {
      result.current.playMove('e2', 'e4');
    });
    expect(engineState.lastMultiPv).toBe(2);
  });

  it('rootMinMultiPv widens only the puzzle position (quick 261010-e5l): 4 at the root, the settings width on a known line, 4 again after goToRoot', () => {
    const { result } = renderTree({ rootMinMultiPv: TRAIN_LIVE_ALT_ROOT_MULTIPV });
    expect(engineState.lastMultiPv).toBe(TRAIN_LIVE_ALT_ROOT_MULTIPV);
    act(() => {
      result.current.playMove('e2', 'e4');
    });
    expect(engineState.lastMultiPv).toBe(2);
    act(() => {
      result.current.goToRoot();
    });
    expect(engineState.lastMultiPv).toBe(TRAIN_LIVE_ALT_ROOT_MULTIPV);
  });

  it('rootMinMultiPv never narrows a wider settings width (Stockfish lines 5 stay 5 at the root)', () => {
    localStorage.setItem(SETTINGS_STORAGE_KEYS.sfLines, '5');
    renderTree({ rootMinMultiPv: TRAIN_LIVE_ALT_ROOT_MULTIPV });
    expect(engineState.lastMultiPv).toBe(5);
  });

  it('Stockfish arrows 3 search at MultiPV 3 on the known lines too', () => {
    localStorage.setItem(SETTINGS_STORAGE_KEYS.sfArrows, '3');
    const { result } = renderTree();
    act(() => {
      result.current.playMove('e2', 'e4');
    });
    expect(engineState.lastMultiPv).toBe(3);
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

// ─── SEED-197: the live engine preview ───────────────────────────────────────

describe('useTrainRevealTree preview', () => {
  it('at open the preview hangs off the active chip first move and equals the seed; live is ignored there', () => {
    // A legal, deep live PV exists, but the anchor (the chip node) is not the
    // node the engine is on, so only the seed can show.
    engineState.pvMoves = ['a7a6'];
    const { result } = renderTree();
    const e4 = result.current.linePaths.your![0]!;

    expect(result.current.preview?.anchorId).toBe(e4);
    expect(previewSans(result.current)).toEqual(['e5', 'Nf3']);
    expect(result.current.canGoForward).toBe(true);
  });

  it('forward at the root enters the chip node and commits nothing; forward at that leaf commits exactly one node', () => {
    keepSeedVisible();
    const { result } = renderTree();
    const e4 = result.current.linePaths.your![0]!;
    const sizeBefore = result.current.nodes.size;

    act(() => result.current.goForward());
    expect(result.current.currentNodeId).toBe(e4);
    expect(result.current.nodes.size).toBe(sizeBefore);

    act(() => result.current.goForward());
    expect(result.current.nodes.size).toBe(sizeBefore + 1);
    expect(result.current.currentPathUcis).toEqual(['e2e4', 'e7e5']);
    expect(result.current.nodes.get(result.current.currentNodeId!)?.san).toBe('e5');
  });

  it('commitPreview(2) from the root plays the chip move plus 2 plies and lands on the second preview ply', () => {
    keepSeedVisible();
    const onUserStep = vi.fn();
    const onUserMove = vi.fn();
    const { result } = renderTree({ onUserStep, onUserMove });

    act(() => result.current.commitPreview(2));

    expect(result.current.currentPathUcis).toEqual(['e2e4', 'e7e5', 'g1f3']);
    expect(result.current.nodes.size).toBe(5); // 3 chip nodes + e5 + Nf3
    expect(onUserStep).toHaveBeenCalledTimes(1);
    expect(onUserMove).not.toHaveBeenCalled(); // stepping, never a move or a fork
  });

  it('ignores commitPreview when there is no preview or fewer than one ply', () => {
    keepSeedVisible();
    const { result } = renderTree({ chips: [GAME] });
    const sizeBefore = result.current.nodes.size;

    act(() => result.current.commitPreview(1)); // the Game chip has no tail
    act(() => result.current.commitPreview(0));

    expect(result.current.nodes.size).toBe(sizeBefore);
    expect(result.current.isAtRoot).toBe(true);
  });

  it('inherits the seed tail after a commit when the live PV is illegal at the new leaf', () => {
    // Rook e1 to e8 is illegal both after 1.e4 and after 1.e4 e5.
    engineState.pvMoves = ['e1e8'];
    const { result } = renderTree();
    const e4 = result.current.linePaths.your![0]!;
    act(() => result.current.goToNode(e4));
    expect(previewSans(result.current)).toEqual(['e5', 'Nf3']); // live illegal -> seed

    act(() => result.current.goForward());
    expect(result.current.currentPathUcis).toEqual(['e2e4', 'e7e5']);
    expect(previewSans(result.current)).toEqual(['Nf3']); // the seed's remaining tail
    expect(result.current.preview?.anchorId).toBe(result.current.currentNodeId);
  });

  it('a live PV below TRAIN_LIVE_ALT_MIN_DEPTH does not replace the tail, and one at the depth does', () => {
    engineState.pvMoves = ['b8c6'];
    keepSeedVisible(); // depth 9
    const { result } = renderTree();
    act(() => result.current.goToNode(result.current.linePaths.your![0]!));
    expect(previewSans(result.current)).toEqual(['e5', 'Nf3']);

    engineState.pvDepth = TRAIN_LIVE_ALT_MIN_DEPTH;
    const { result: deep } = renderTree();
    act(() => deep.current.goToNode(deep.current.linePaths.your![0]!));
    expect(previewSans(deep.current)).toEqual(['Nc6']);
  });

  it('stepping away from a leaf and back shows its stored live PV immediately', () => {
    engineState.pvMoves = ['b8c6', 'g1f3'];
    const { result } = renderTree();
    const e4 = result.current.linePaths.your![0]!;
    act(() => result.current.goToNode(e4));
    expect(previewSans(result.current)).toEqual(['Nc6', 'Nf3']);

    // Now the engine goes shallow: only the stored line can still explain the leaf.
    keepSeedVisible();
    act(() => result.current.goToRoot());
    act(() => result.current.goToNode(e4));
    expect(previewSans(result.current)).toEqual(['Nc6', 'Nf3']);
  });

  it('shows no preview on a node with children, and committed nodes never change when the live PV does', () => {
    engineState.pvMoves = ['e7e5', 'g1f3'];
    const { result } = renderTree();
    const e4 = result.current.linePaths.your![0]!;
    act(() => result.current.goToNode(e4));
    act(() => result.current.goForward());
    const e5 = result.current.currentNodeId!;
    const sanBefore = result.current.nodes.get(e5)?.san;

    engineState.pvMoves = ['c7c5'];
    act(() => result.current.goToRoot());
    act(() => result.current.goToNode(e4)); // e4 now has a child
    expect(result.current.preview).toBeNull();
    expect(result.current.nodes.get(e5)?.san).toBe(sanBefore);
  });

  it('caps the displayed preview at TRAIN_PREVIEW_MAX_PLIES but lets the user keep committing past it', () => {
    keepSeedVisible();
    const long = ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4', 'f8c5', 'c2c3', 'g8f6', 'd2d4'];
    const { result } = renderTree({ chips: [chipOf('your', long)] });

    expect(result.current.preview?.steps).toHaveLength(TRAIN_PREVIEW_MAX_PLIES);
    act(() => result.current.commitPreview(TRAIN_PREVIEW_MAX_PLIES));
    // The chip move plus six plies are committed; the rest of the line is inherited.
    expect(result.current.currentPathUcis).toEqual(long.slice(0, TRAIN_PREVIEW_MAX_PLIES + 1));
    expect(previewSans(result.current)).toEqual(['Nf6', 'd4']);
  });

  it('has no preview at a finished game and canGoForward is false there', () => {
    const mate = ['f2f3', 'e7e5', 'g2g4', 'd8h4'];
    const { result } = renderTree({ chips: [chipOf('your', mate)] });
    act(() => result.current.commitPreview(3)); // f3 e5 g4 Qh4#

    expect(result.current.nodes.get(result.current.currentNodeId!)?.san).toBe('Qh4#');
    expect(result.current.preview).toBeNull();
    expect(result.current.canGoForward).toBe(false);
  });

  it('chip first-move nodes keep their place: the snapshot never contains the preview, and a restore regenerates it', () => {
    keepSeedVisible();
    const original = renderTree();
    act(() => original.result.current.commitPreview(2));
    const snapshot = original.result.current.snapshot();
    expect(snapshot.currentPath).toEqual(['e2e4', 'e7e5', 'g1f3']);
    expect(snapshot.sidelinePaths).toEqual([['e2e4', 'e7e5', 'g1f3']]);

    const { result } = renderTree({ restored: snapshot });
    expect(result.current.currentPathUcis).toEqual(['e2e4', 'e7e5', 'g1f3']);
    // The seed tail is exhausted ([e5, Nf3] both committed), so no preview is left.
    expect(result.current.preview).toBeNull();
    expect(result.current.listView.mainLine).toHaveLength(3);
  });
});

describe('useTrainRevealTree preview commits are ungraded', () => {
  it('a preview-committed node gets no marker while a hand-played fork still does', () => {
    keepSeedVisible();
    engineState.scoresByFen[fenAfter(START_FEN, 'e4')] = 30;
    engineState.scoresByFen[fenAfter(START_FEN, 'e4', 'e5')] = 900; // would grade as a blunder
    engineState.scoresByFen[fenAfter(START_FEN, 'e4', 'c5')] = 900;
    const { result } = renderTree({ seedEval: makeSeed([]) });
    act(() => result.current.goToNode(result.current.linePaths.your![0]!));

    act(() => result.current.goForward()); // commits e5
    const committed = result.current.currentNodeId!;
    expect(result.current.moveListMarkers.has(committed)).toBe(false);
    expect(result.current.boardMarkers).toEqual([]);

    act(() => result.current.goBack());
    act(() => {
      result.current.playMove('c7', 'c5'); // a hand-played fork
    });
    expect(result.current.boardMarkers).toEqual([{ square: 'c5', severity: 'blunder' }]);
    expect(result.current.moveListMarkers.has(result.current.currentNodeId!)).toBe(true);
    expect(result.current.moveListMarkers.has(committed)).toBe(false);
  });
});

describe('useTrainRevealTree preview commits survive Analyze -> Back (WR-02)', () => {
  /** e4 chip leaf, then the preview's e5 committed with ArrowRight, parked on e5. */
  function committedE5Tree() {
    keepSeedVisible();
    engineState.scoresByFen[fenAfter(START_FEN, 'e4')] = 30;
    engineState.scoresByFen[fenAfter(START_FEN, 'e4', 'e5')] = 900; // would grade as a blunder
    const original = renderTree({ seedEval: makeSeed([]) });
    act(() => original.result.current.goToNode(original.result.current.linePaths.your![0]!));
    act(() => original.result.current.goForward()); // commits e5
    return original;
  }

  it('persists the committed node as a UCI path in the snapshot', () => {
    const original = committedE5Tree();

    expect(original.result.current.snapshot().committedPaths).toEqual([['e2e4', 'e7e5']]);
  });

  it('a restored preview-committed node is still never graded; a hand-played one still is', () => {
    const snapshot = committedE5Tree().result.current.snapshot();
    engineState.scoresByFen[fenAfter(START_FEN, 'e4', 'c5')] = 900;

    const { result } = renderTree({ restored: snapshot, seedEval: makeSeed([]) });
    expect(result.current.currentPathUcis).toEqual(['e2e4', 'e7e5']);
    // Visit the parent so the engine caches its eval, then step back onto e5.
    const e5 = result.current.currentNodeId!;
    act(() => result.current.goBack());
    act(() => result.current.goToNode(e5));

    expect(result.current.moveListMarkers.has(e5)).toBe(false);
    expect(result.current.boardMarkers).toEqual([]);

    act(() => result.current.goBack());
    act(() => {
      result.current.playMove('c7', 'c5');
    });
    expect(result.current.moveListMarkers.has(result.current.currentNodeId!)).toBe(true);
  });

  it('an older snapshot without committedPaths restores with nothing marked (graded as before)', () => {
    const snapshot = committedE5Tree().result.current.snapshot();
    delete snapshot.committedPaths;

    const { result } = renderTree({ restored: snapshot, seedEval: makeSeed([]) });
    const e5 = result.current.currentNodeId!;
    act(() => result.current.goBack());
    act(() => result.current.goToNode(e5));

    expect(result.current.moveListMarkers.has(e5)).toBe(true);
  });
});

describe('useTrainRevealTree commitPreview id bookkeeping (WR-01)', () => {
  it('two commits in one event graft once and do not exempt the next hand-played move from grading', () => {
    keepSeedVisible();
    engineState.scoresByFen[fenAfter(START_FEN, 'e4', 'e5')] = 30;
    engineState.scoresByFen[fenAfter(START_FEN, 'e4', 'e5', 'Nc3')] = -900; // white blunders
    const { result } = renderTree({ seedEval: makeSeed([]) });
    const sizeBefore = result.current.nodes.size;

    // latestRef only syncs after a render, so the second call sees the pre-commit
    // preview and nextId. Its predicted ids (nextId + 0..1) must not be marked: the
    // board grafts nothing for it, and nextId + 1 is the next node the user plays.
    act(() => {
      result.current.commitPreview(1);
      result.current.commitPreview(2);
    });

    expect(result.current.nodes.size).toBe(sizeBefore + 1);
    expect(result.current.currentPathUcis).toEqual(['e2e4', 'e7e5']);
    const committed = result.current.currentNodeId!;
    expect(result.current.moveListMarkers.has(committed)).toBe(false);

    act(() => {
      result.current.playMove('b1', 'c3');
    });
    const handPlayed = result.current.currentNodeId!;
    expect(handPlayed).not.toBe(committed);
    expect(result.current.moveListMarkers.has(handPlayed)).toBe(true);
    expect(result.current.boardMarkers).toEqual([{ square: 'c3', severity: 'blunder' }]);
  });

  it('commits made in separate events are each applied and each ungraded', () => {
    keepSeedVisible();
    const { result } = renderTree({ seedEval: makeSeed([]) });

    act(() => result.current.commitPreview(1));
    const first = result.current.currentNodeId!;
    act(() => result.current.commitPreview(1));
    const second = result.current.currentNodeId!;

    expect(second).not.toBe(first);
    expect(result.current.currentPathUcis).toEqual(['e2e4', 'e7e5', 'g1f3']);
    expect(result.current.moveListMarkers.has(first)).toBe(false);
    expect(result.current.moveListMarkers.has(second)).toBe(false);
  });

  it('a committed id range exactly matches the newly grafted node ids', () => {
    keepSeedVisible();
    const { result } = renderTree({ seedEval: makeSeed([]) });
    const idsBefore = new Set(result.current.nodes.keys());

    act(() => result.current.commitPreview(2));

    const grafted = [...result.current.nodes.keys()].filter((id) => !idsBefore.has(id));
    expect(grafted).toHaveLength(2);
    const snapshot = result.current.snapshot();
    // The snapshot's committed paths are derived from the committed id set, so they
    // pin exactly the two grafted nodes (and not the chip node or a phantom id).
    expect(snapshot.committedPaths).toEqual([
      ['e2e4', 'e7e5'],
      ['e2e4', 'e7e5', 'g1f3'],
    ]);
  });
});

describe('useTrainRevealTree playMove vs the preview', () => {
  it('a board move equal to the preview next move is not a fork, a different one is; both are graded', () => {
    keepSeedVisible();
    engineState.scoresByFen[fenAfter(START_FEN, 'e4')] = 30;
    engineState.scoresByFen[fenAfter(START_FEN, 'e4', 'e5')] = 900;
    const onUserMove = vi.fn();
    const { result } = renderTree({ onUserMove, seedEval: makeSeed([]) });
    act(() => result.current.goToNode(result.current.linePaths.your![0]!));
    const e4 = result.current.currentNodeId!;

    act(() => {
      result.current.playMove('e7', 'e5'); // the preview's own next move
    });
    expect(onUserMove).toHaveBeenLastCalledWith({ source: 'board', forked: false });
    // Hand-played, so it IS graded even though it matches the preview.
    expect(result.current.moveListMarkers.has(result.current.currentNodeId!)).toBe(true);

    act(() => result.current.goToNode(e4));
    act(() => {
      result.current.playMove('c7', 'c5'); // not the preview's move
    });
    expect(onUserMove).toHaveBeenLastCalledWith({ source: 'board', forked: true });
  });
});
