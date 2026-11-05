// @vitest-environment jsdom
/**
 * useExplainBar real-board integration harness (SEED-208, D-05/D-06/D-07).
 *
 * `useHarness` mirrors Analysis.tsx's wiring exactly: the real useAnalysisBoard,
 * the real useAnalysisRouteSeeding graft effect, the page's findFocusedFlaw rule
 * and fetchFlaw observer, and useExplainBar. Only the tactic-lines network hook
 * and the audio module are mocked. This proves first-move landing for both
 * buttons on either side's flaw, no line switch inside a line, one open line at a time,
 * the line stepper, Got it, re-entry without duplicate grafts, the shared chip key and unchanged chip parking.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useMemo, useState } from 'react';
import { useAnalysisBoard } from '@/hooks/useAnalysisBoard';
import { useAnalysisRouteSeeding } from '@/hooks/analysis/useAnalysisRouteSeeding';
import { useExplainBar } from '@/hooks/analysis/useExplainBar';
import { EXPLAIN_FORK_PREVIEW_MS, useExplainLineEntry } from '@/hooks/analysis/useExplainLineEntry';
import { findFocusedFlaw, type OpenLine, type PendingFlaw } from '@/lib/analysisTactics';
import { useTacticLines } from '@/hooks/useLibrary';
import type { GameFlawCard, TacticLinesResponse } from '@/types/library';

vi.mock('@/lib/sounds', () => ({
  playSound: vi.fn(),
  unlockAudio: vi.fn(),
}));

// A `null` fixture is a settled 404 ("no lines"); an absent ply is still loading (undefined).
const fixtures = new Map<number, TacticLinesResponse | null>();
vi.mock('@/hooks/useLibrary', () => ({
  useTacticLines: (_gameId: number | null, ply: number | null, enabled: boolean) => ({
    data: enabled && ply != null && fixtures.has(ply) ? fixtures.get(ply) : undefined,
    isFetching: false,
    isError: false,
  }),
}));

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const GAME_ID = 1;
const BLUNDER_PLY = 2;
const MISTAKE_PLY = 3;

function marker(ply: number, san: string, isUser: boolean, severity: 'mistake' | 'blunder') {
  return {
    ply,
    severity,
    tags: [],
    is_user: isUser,
    move_san: san,
    allowed_tactic_motif: null,
    allowed_tactic_confidence: null,
    allowed_tactic_depth: null,
    missed_tactic_motif: null,
    missed_tactic_confidence: null,
    missed_tactic_depth: null,
  };
}

function makeCard(): GameFlawCard {
  return {
    game_id: GAME_ID,
    user_result: 'win',
    played_at: '2026-01-15T10:00:00Z',
    time_control_bucket: 'rapid',
    platform: 'chess.com',
    platform_url: null,
    white_username: 'alice',
    black_username: 'bob',
    white_rating: null,
    black_rating: null,
    opening_name: null,
    opening_eco: null,
    user_color: 'white',
    ply_count: 4,
    termination: null,
    time_control_str: null,
    result_fen: null,
    severity_counts: { inaccuracy: 0, mistake: 1, blunder: 1 },
    chips: [],
    analysis_state: 'analyzed',
    eval_series: null,
    flaw_markers: [marker(BLUNDER_PLY, 'Qh5', true, 'blunder'), marker(MISTAKE_PLY, 'Nc6', false, 'mistake')],
    phase_transitions: { middlegame_ply: null, endgame_ply: null },
    moves: ['e4', 'e5', 'Qh5', 'Nc6'],
    initial_fen: null,
    active_eval_status: null,
    opening_ply_count: 0,
  };
}

function lines(overrides: Partial<TacticLinesResponse>): TacticLinesResponse {
  return {
    missed_moves: null,
    missed_depth: null,
    missed_tactic_ply_index: null,
    missed_motif: null,
    missed_eval_cp: null,
    missed_eval_mate: null,
    allowed_moves: null,
    allowed_depth: null,
    allowed_tactic_ply_index: null,
    allowed_motif: null,
    allowed_eval_cp: null,
    allowed_eval_mate: null,
    position_fen: START_FEN,
    flaw_move_san: null,
    best_move_uci: null,
    flaw_ply: BLUNDER_PLY,
    flaw_severity: 'blunder',
    ...overrides,
  };
}

const BLUNDER_LINES = lines({ missed_moves: ['Nf3', 'Nc6'], allowed_moves: ['Qh5', 'Nc6', 'Bc4'] });
const MISTAKE_LINES = lines({
  allowed_moves: ['Nc6', 'Bc4', 'g6'],
  missed_moves: ['Nf6'],
  flaw_ply: MISTAKE_PLY,
  flaw_severity: 'mistake',
});

/**
 * Mirrors the Analysis.tsx wiring: board, openLines/pendingFlaw state, the
 * focusedFlaw memo, the fetchFlaw observer feeding the graft effect, the real
 * seeding hook, and useExplainBar fed the same values.
 */
function useHarness(game: GameFlawCard, initialPly: number) {
  const board = useAnalysisBoard(START_FEN);
  const { nodes, currentNodeId, mainLine, nextId, loadMainLine, goToNode, goBack, goForward, insertPvLine, deleteSubtree } =
    board;
  const [openLines, setOpenLines] = useState<Map<string, OpenLine>>(() => new Map());
  const [pendingFlaw, setPendingFlaw] = useState<PendingFlaw | null>(null);

  const focusedFlaw = useMemo(
    () => findFocusedFlaw(true, currentNodeId, pendingFlaw, openLines, mainLine, nodes),
    [currentNodeId, pendingFlaw, openLines, mainLine, nodes],
  );
  const fetchFlaw = pendingFlaw ?? focusedFlaw;
  const { data } = useTacticLines(GAME_ID, fetchFlaw?.ply ?? null, fetchFlaw != null);
  const enterExplainLine = useExplainLineEntry(currentNodeId, goToNode);

  useAnalysisRouteSeeding({
    isGameMode: true,
    gameId: GAME_ID,
    initialPly,
    lineSans: [],
    rootFenSeed: null,
    autoOrientation: null,
    initialTactic: null,
    gameData: game,
    pendingFlaw,
    contextualTacticData: data,
    openLines,
    mainLine,
    nextId,
    loadMainLine,
    goToNode,
    insertPvLine,
    enterExplainLine,
    setBoardFlipped: () => {},
    setPendingFlaw,
    setOpenLines,
  });

  const landingPly = currentNodeId !== null ? mainLine.indexOf(currentNodeId) : -1;
  const explain = useExplainBar({
    isGameMode: true,
    gameId: GAME_ID,
    flawMarkers: game.flaw_markers,
    landingPly,
    pendingFlaw,
    focusedFlaw,
    openLines,
    fastForwardRunning: false,
    nodes,
    currentNodeId,
    mainLine,
    goToNode,
    goForward,
    goBack,
    deleteSubtree,
    enterExplainLine,
    setPendingFlaw,
    setOpenLines,
  });

  return { board, openLines, pendingFlaw, setPendingFlaw, explain };
}

type Harness = ReturnType<typeof renderHarness>;

function renderHarness(initialPly: number) {
  return renderHook(() => useHarness(makeCard(), initialPly));
}

function currentSan(h: Harness): string | undefined {
  const { board } = h.result.current;
  return board.currentNodeId === null ? undefined : board.nodes.get(board.currentNodeId)?.san;
}

function mainLineId(h: Harness, ply: number): number | undefined {
  return h.result.current.board.mainLine[ply];
}

/** Click Best (missed) or Punish (allowed) and let a missed-line fork preview run out. */
function openAndSettle(h: Harness, orientation: 'missed' | 'allowed' = 'missed'): void {
  act(() => h.result.current.explain.onOpenLine(orientation));
  act(() => vi.advanceTimersByTime(EXPLAIN_FORK_PREVIEW_MS));
}

let track: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.useFakeTimers();
  track = vi.fn();
  window.umami = { track, identify: vi.fn() };
  window.history.pushState({}, '', '/analysis');
  fixtures.set(BLUNDER_PLY, BLUNDER_LINES);
  fixtures.set(MISTAKE_PLY, MISTAKE_LINES);
});

afterEach(() => {
  vi.useRealTimers();
  fixtures.clear();
  delete window.umami;
  window.history.pushState({}, '', '/');
});

describe('useExplainBar harness', () => {
  it('Best on the owner blunder grafts the missed line and lands on its first move', () => {
    const h = renderHarness(BLUNDER_PLY);
    expect(h.result.current.explain.state).toMatchObject({
      kind: 'explain',
      ply: BLUNDER_PLY,
      usable: { missed: true, allowed: true },
    });

    openAndSettle(h);

    expect(currentSan(h)).toBe('Nf3');
    expect(h.result.current.openLines.has('2:missed')).toBe(true);
    expect(h.result.current.pendingFlaw).toBeNull();
    expect(h.result.current.explain.state.kind).toBe('got-it');
  });

  it('UAT: Best first shows the position before the mistake, then plays the better move', () => {
    const h = renderHarness(BLUNDER_PLY);

    act(() => h.result.current.explain.onOpenLine('missed'));

    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, BLUNDER_PLY - 1));
    expect(h.result.current.openLines.has('2:missed')).toBe(true);
    act(() => vi.advanceTimersByTime(EXPLAIN_FORK_PREVIEW_MS - 1));
    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, BLUNDER_PLY - 1));
    act(() => vi.advanceTimersByTime(1));
    expect(currentSan(h)).toBe('Nf3');
  });

  it('UAT: leaving the fork during the preview cancels the advance', () => {
    const h = renderHarness(BLUNDER_PLY);
    act(() => h.result.current.explain.onOpenLine('missed'));
    act(() => h.result.current.board.goToNode(mainLineId(h, 0)!));

    act(() => vi.advanceTimersByTime(EXPLAIN_FORK_PREVIEW_MS));

    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, 0));
  });

  it('UAT: Punish lands on the refutation without a preview', () => {
    const h = renderHarness(MISTAKE_PLY);
    act(() => h.result.current.explain.onOpenLine('allowed'));
    expect(currentSan(h)).toBe('Bc4');
  });

  it('Punish on the opponent mistake lands on the refutation, not the prepended flaw move', () => {
    const h = renderHarness(MISTAKE_PLY);
    openAndSettle(h, 'allowed');

    expect(currentSan(h)).toBe('Bc4');
    const line = h.result.current.openLines.get('3:allowed');
    expect(h.result.current.board.currentNodeId).toBe(line?.rootNodeId);
  });

  it('Best works on the opponent mistake too (no direction rule)', () => {
    const h = renderHarness(MISTAKE_PLY);
    openAndSettle(h, 'missed');
    expect(currentSan(h)).toBe('Nf6');
    expect(h.result.current.openLines.has('3:missed')).toBe(true);
  });

  it('an unusable line ignores its click; the other still opens', () => {
    fixtures.set(BLUNDER_PLY, lines({ missed_moves: null, allowed_moves: ['Qh5', 'Nc6', 'Bc4'] }));
    const h = renderHarness(BLUNDER_PLY);
    expect(h.result.current.explain.state).toMatchObject({ usable: { missed: false, allowed: true } });
    act(() => h.result.current.explain.onOpenLine('missed'));
    expect(h.result.current.pendingFlaw).toBeNull();
    expect(track).not.toHaveBeenCalled();

    openAndSettle(h, 'allowed');

    const line = h.result.current.openLines.get('2:allowed');
    // The game also continued with Nc6, so assert on the node id, not only the SAN.
    expect(h.result.current.board.currentNodeId).toBe(line?.rootNodeId);
    expect(h.result.current.board.currentNodeId).not.toBe(mainLineId(h, 3));
    expect(currentSan(h)).toBe('Nc6');
  });

  it('D-06: Back/Forward step through the line and Got it removes it and returns to the flaw move', () => {
    const h = renderHarness(BLUNDER_PLY);
    openAndSettle(h);
    const line = h.result.current.openLines.get('2:missed');
    const grafted = [...h.result.current.board.pvNodeIds];
    expect(grafted).toHaveLength(2);
    expect(h.result.current.board.currentNodeId).toBe(line?.rootNodeId);

    act(() => h.result.current.board.goForward());
    expect(currentSan(h)).toBe('Nc6');
    act(() => h.result.current.board.goBack());
    act(() => h.result.current.board.goBack());
    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, 1));
    expect(h.result.current.explain.state.kind).toBe('got-it');

    act(() => h.result.current.explain.onGotIt());

    for (const id of grafted) expect(h.result.current.board.nodes.has(id)).toBe(false);
    expect(h.result.current.openLines.size).toBe(0);
    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, 2));
    expect(h.result.current.explain.state.kind).toBe('explain');
  });

  it('D-06: Got it on an allowed line returns to the flaw move', () => {
    const h = renderHarness(MISTAKE_PLY);
    openAndSettle(h, 'allowed');
    act(() => h.result.current.explain.onGotIt());

    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, 3));
    expect(h.result.current.openLines.size).toBe(0);
  });

  it('D-07: leaving the line keeps it open and Explain re-enters it without a duplicate graft', () => {
    const h = renderHarness(BLUNDER_PLY);
    openAndSettle(h);
    const line = h.result.current.openLines.get('2:missed');
    const grafted = [...h.result.current.board.pvNodeIds];

    // Stands in for a move-list click or an eval-chart scrub.
    act(() => h.result.current.board.goToNode(mainLineId(h, 0)!));
    expect(h.result.current.openLines.has('2:missed')).toBe(true);
    for (const id of grafted) expect(h.result.current.board.nodes.has(id)).toBe(true);

    act(() => h.result.current.board.goToNode(mainLineId(h, 2)!));
    expect(h.result.current.explain.state.kind).toBe('explain');
    const size = h.result.current.board.nodes.size;

    openAndSettle(h);

    expect(h.result.current.board.currentNodeId).toBe(line?.rootNodeId);
    expect(h.result.current.board.nodes.size).toBe(size);
    expect(h.result.current.explain.state.kind).toBe('got-it');
  });

  it('D-07: a chip-opened line shares the key; chips still park at the fork; Explain re-enters it', () => {
    const h = renderHarness(BLUNDER_PLY);
    // Exactly what handlePvChipClick does: pending flaw WITHOUT the enter flag, plus a fork navigation.
    act(() => {
      h.result.current.setPendingFlaw({ ply: BLUNDER_PLY, orientation: 'missed' });
      h.result.current.board.goToNode(mainLineId(h, 1)!);
    });
    const line = h.result.current.openLines.get('2:missed');
    expect(line).toBeDefined();
    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, 1));
    expect(h.result.current.explain.state.kind).toBe('got-it');

    act(() => h.result.current.board.goToNode(mainLineId(h, 2)!));
    expect(h.result.current.explain.state.kind).toBe('explain');
    const size = h.result.current.board.nodes.size;

    openAndSettle(h);

    expect(h.result.current.board.currentNodeId).toBe(line?.rootNodeId);
    expect(h.result.current.board.nodes.size).toBe(size);
  });

  it('WR-01: with a chip-opened missed line forking on the owner blunder, the blunder still offers Explain', () => {
    const h = renderHarness(BLUNDER_PLY);
    // The opponent mistake's MISSED line forks at mainLine[2], the owner blunder itself.
    act(() => {
      h.result.current.setPendingFlaw({ ply: MISTAKE_PLY, orientation: 'missed' });
      h.result.current.board.goToNode(mainLineId(h, BLUNDER_PLY)!);
    });
    expect(h.result.current.openLines.has('3:missed')).toBe(true);
    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, BLUNDER_PLY));
    expect(h.result.current.explain.state).toMatchObject({ kind: 'explain', ply: BLUNDER_PLY });

    openAndSettle(h);

    expect(currentSan(h)).toBe('Nf3');
    expect(h.result.current.openLines.has('2:missed')).toBe(true);
    // One open line at a time: opening the blunder's line closed the mistake's.
    expect(h.result.current.openLines.has('3:missed')).toBe(false);
  });

  it('UAT: Best/Punish close any other open line (one line at a time, like chips)', () => {
    const h = renderHarness(BLUNDER_PLY);
    openAndSettle(h, 'missed');
    const blunderNodes = [...h.result.current.board.pvNodeIds];

    // Leave the line via the move list (it stays open), then Punish the opponent mistake.
    act(() => h.result.current.board.goToNode(mainLineId(h, MISTAKE_PLY)!));
    expect(h.result.current.openLines.has('2:missed')).toBe(true);
    openAndSettle(h, 'allowed');

    expect([...h.result.current.openLines.keys()]).toEqual(['3:allowed']);
    for (const id of blunderNodes) expect(h.result.current.board.nodes.has(id)).toBe(false);
    expect(currentSan(h)).toBe('Bc4');
  });

  it('UAT: re-entering an open line closes the other open lines but keeps it', () => {
    const h = renderHarness(BLUNDER_PLY);
    openAndSettle(h, 'missed');
    const blunderLine = h.result.current.openLines.get('2:missed');
    // A second line opened the way the deep-link auto-open does (no enter flag, no close).
    act(() => {
      h.result.current.setPendingFlaw({ ply: MISTAKE_PLY, orientation: 'allowed' });
      h.result.current.board.goToNode(mainLineId(h, MISTAKE_PLY)!);
    });
    expect(h.result.current.openLines.size).toBe(2);
    const mistakeRoot = h.result.current.openLines.get('3:allowed')!.rootNodeId;

    act(() => h.result.current.board.goToNode(mainLineId(h, BLUNDER_PLY)!));
    openAndSettle(h, 'missed');

    expect([...h.result.current.openLines.keys()]).toEqual(['2:missed']);
    expect(h.result.current.board.nodes.has(mistakeRoot)).toBe(false);
    expect(h.result.current.board.currentNodeId).toBe(blunderLine?.rootNodeId);
  });

  it('WR-02: a chip open that settles to no lines (404) releases the pending flaw so Explain works elsewhere', () => {
    fixtures.set(MISTAKE_PLY, null);
    const h = renderHarness(BLUNDER_PLY);
    act(() => h.result.current.setPendingFlaw({ ply: MISTAKE_PLY, orientation: 'allowed' }));

    expect(h.result.current.pendingFlaw).toBeNull();
    expect(h.result.current.openLines.size).toBe(0);
    expect(h.result.current.explain.state).toMatchObject({ kind: 'explain', ply: BLUNDER_PLY });
  });

  it('WR-02: an ungraftable chip open (empty PV) releases the pending flaw too', () => {
    fixtures.set(MISTAKE_PLY, lines({ allowed_moves: ['Nc6'], missed_moves: [], flaw_ply: MISTAKE_PLY }));
    const h = renderHarness(BLUNDER_PLY);
    act(() => h.result.current.setPendingFlaw({ ply: MISTAKE_PLY, orientation: 'allowed' }));

    expect(h.result.current.pendingFlaw).toBeNull();
    expect(h.result.current.explain.state.kind).toBe('explain');
  });

  it('tracking: render, navigation and the stepper send nothing; the handlers send explain-best and explain-close', () => {
    const h = renderHarness(BLUNDER_PLY);
    act(() => h.result.current.board.goToNode(mainLineId(h, 0)!));
    act(() => h.result.current.board.goToNode(mainLineId(h, 2)!));
    expect(track).not.toHaveBeenCalled();

    openAndSettle(h);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenLastCalledWith('board-tool', { page: 'analysis', target: 'explain-best' });
    act(() => h.result.current.explain.stepper.onForward());
    act(() => h.result.current.explain.stepper.onBack());
    expect(track).toHaveBeenCalledTimes(1);

    act(() => h.result.current.explain.onGotIt());
    expect(track).toHaveBeenCalledTimes(2);
    expect(track).toHaveBeenLastCalledWith('board-tool', { page: 'analysis', target: 'explain-close' });
  });

  it('inside a line, opening the other line is a no-op (UAT: no switch button)', () => {
    const h = renderHarness(BLUNDER_PLY);
    openAndSettle(h);
    const before = h.result.current.board.currentNodeId;
    track.mockClear();

    act(() => h.result.current.explain.onOpenLine('allowed'));

    expect([...h.result.current.openLines.keys()]).toEqual(['2:missed']);
    expect(h.result.current.board.currentNodeId).toBe(before);
    expect(h.result.current.explain.state).toMatchObject({ kind: 'got-it', line: { orientation: 'missed' } });
    expect(track).not.toHaveBeenCalled();
  });

  it('stepper: Back stops at the fork, Forward re-enters the line and stops at its end', () => {
    const h = renderHarness(BLUNDER_PLY);
    openAndSettle(h);
    const line = h.result.current.openLines.get('2:missed');
    const stepper = () => h.result.current.explain.stepper;
    expect(stepper()).toMatchObject({ canBack: true, canForward: true });

    act(() => stepper().onForward());
    expect(currentSan(h)).toBe('Nc6');
    expect(stepper().canForward).toBe(false);

    act(() => stepper().onBack());
    act(() => stepper().onBack());
    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, BLUNDER_PLY - 1));
    expect(stepper().canBack).toBe(false);
    act(() => stepper().onBack());
    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, BLUNDER_PLY - 1));

    // From the fork, Forward steps into THIS line (not whichever PV child has the lowest id).
    act(() => stepper().onForward());
    expect(h.result.current.board.currentNodeId).toBe(line?.rootNodeId);
  });

  it('stepper: an allowed line forks at the flaw move, so Back stops there', () => {
    const h = renderHarness(MISTAKE_PLY);
    openAndSettle(h, 'allowed');
    act(() => h.result.current.explain.stepper.onBack());
    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, MISTAKE_PLY));
    expect(h.result.current.explain.stepper.canBack).toBe(false);
  });

  it('stepper is inert outside a line', () => {
    const h = renderHarness(BLUNDER_PLY);
    expect(h.result.current.explain.stepper).toMatchObject({ canBack: false, canForward: false });
    act(() => h.result.current.explain.stepper.onBack());
    expect(h.result.current.board.currentNodeId).toBe(mainLineId(h, BLUNDER_PLY));
  });
});
