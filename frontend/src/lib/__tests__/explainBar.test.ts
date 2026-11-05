import { describe, expect, it } from 'vitest';
import {
  chooseExplainOrientation,
  eligibleExplainMarker,
  resolveExplainBarState,
  usableExplainLines,
  type ExplainBarInputs,
} from '@/lib/explainBar';
import type { OpenLine } from '@/lib/analysisTactics';
import type { FlawMarker, TacticLinesResponse } from '@/types/library';

// Pure rules for the contextual Explain bar (D-04, D-08, D-09, D-10, D-11).

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function marker(overrides: Partial<FlawMarker>): FlawMarker {
  return {
    ply: 10,
    severity: 'blunder',
    tags: [],
    is_user: true,
    move_san: 'Qh5',
    allowed_tactic_motif: null,
    allowed_tactic_confidence: null,
    allowed_tactic_depth: null,
    missed_tactic_motif: null,
    missed_tactic_confidence: null,
    missed_tactic_depth: null,
    ...overrides,
  };
}

function tacticLines(overrides: Partial<TacticLinesResponse>): TacticLinesResponse {
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
    flaw_ply: 10,
    flaw_severity: 'blunder',
    ...overrides,
  };
}

function inputs(overrides: Partial<ExplainBarInputs>): ExplainBarInputs {
  return {
    isGameMode: true,
    fastForwardRunning: false,
    flawMarkers: [marker({ ply: 10 })],
    landingPly: 10,
    pendingFlaw: null,
    focusedFlaw: null,
    openLines: new Map(),
    tacticLines: tacticLines({ missed_moves: ['Nf3', 'Nc6'], allowed_moves: ['Qh5', 'Nc6', 'Bc4'] }),
    ...overrides,
  };
}

describe('eligibleExplainMarker', () => {
  it('returns the blunder or mistake marker for both sides', () => {
    const user = marker({ ply: 4, is_user: true, severity: 'blunder' });
    const opp = marker({ ply: 5, is_user: false, severity: 'mistake' });
    expect(eligibleExplainMarker([user, opp], 4)).toBe(user);
    expect(eligibleExplainMarker([user, opp], 5)).toBe(opp);
  });

  it('returns null for an inaccuracy, a missing marker, nullish markers and ply -1', () => {
    const markers = [marker({ ply: 4, severity: 'inaccuracy' })];
    expect(eligibleExplainMarker(markers, 4)).toBeNull();
    expect(eligibleExplainMarker(markers, 6)).toBeNull();
    expect(eligibleExplainMarker(null, 4)).toBeNull();
    expect(eligibleExplainMarker(undefined, 4)).toBeNull();
    expect(eligibleExplainMarker([marker({ ply: -1 })], -1)).toBeNull();
  });
});

describe('usableExplainLines', () => {
  it('rejects a missed line at ply 0 even with moves', () => {
    expect(usableExplainLines(tacticLines({ missed_moves: ['e4'] }), 0).missed).toBe(false);
  });

  it('rejects null or empty missed_moves, accepts a non-empty one', () => {
    expect(usableExplainLines(tacticLines({ missed_moves: null }), 4).missed).toBe(false);
    expect(usableExplainLines(tacticLines({ missed_moves: [] }), 4).missed).toBe(false);
    expect(usableExplainLines(tacticLines({ missed_moves: ['Nf3'] }), 4).missed).toBe(true);
  });

  it('rejects null allowed_moves and a length-1 line (only the flaw move), accepts length 2', () => {
    expect(usableExplainLines(tacticLines({ allowed_moves: null }), 4).allowed).toBe(false);
    expect(usableExplainLines(tacticLines({ allowed_moves: ['Qh5'] }), 4).allowed).toBe(false);
    expect(usableExplainLines(tacticLines({ allowed_moves: ['Qh5', 'Nc6'] }), 4).allowed).toBe(true);
  });
});

describe('chooseExplainOrientation', () => {
  const both = { missed: true, allowed: true };

  it('prefers missed for the owner and allowed for the opponent (D-04)', () => {
    expect(chooseExplainOrientation(true, both)).toBe('missed');
    expect(chooseExplainOrientation(false, both)).toBe('allowed');
  });

  it('falls back to the other line when the preferred one is unusable (D-09)', () => {
    expect(chooseExplainOrientation(true, { missed: false, allowed: true })).toBe('allowed');
    expect(chooseExplainOrientation(false, { missed: true, allowed: false })).toBe('missed');
  });

  it('returns null when neither line is usable (D-10)', () => {
    expect(chooseExplainOrientation(true, { missed: false, allowed: false })).toBeNull();
    expect(chooseExplainOrientation(false, { missed: false, allowed: false })).toBeNull();
  });
});

describe('resolveExplainBarState', () => {
  it('offers Explain on an eligible ply with usable lines', () => {
    expect(resolveExplainBarState(inputs({}))).toEqual({
      kind: 'explain',
      flaw: { ply: 10, orientation: 'missed' },
      san: 'Qh5',
      severity: 'blunder',
      tactics: [],
      pending: false,
    });
  });

  it('lists both orientations, missed first, whichever line Explain opens', () => {
    const state = resolveExplainBarState(
      inputs({
        flawMarkers: [
          marker({
            ply: 10,
            missed_tactic_motif: 'fork',
            missed_tactic_depth: 0,
            allowed_tactic_motif: 'pin',
            allowed_tactic_depth: 2,
          }),
        ],
      }),
    );
    expect(state).toMatchObject({
      kind: 'explain',
      flaw: { orientation: 'missed' },
      tactics: [
        { orientation: 'missed', motif: 'fork', depth: 0 },
        { orientation: 'allowed', motif: 'pin', depth: 2 },
      ],
    });
  });

  it('keeps an allowed tactic even when Explain opens the missed line', () => {
    const state = resolveExplainBarState(
      inputs({ flawMarkers: [marker({ ply: 10, allowed_tactic_motif: 'fork', allowed_tactic_depth: 0 })] }),
    );
    expect(state).toMatchObject({
      kind: 'explain',
      flaw: { orientation: 'missed' },
      tactics: [{ orientation: 'allowed', motif: 'fork', depth: 0 }],
    });
  });

  it('drops family-less motifs (no chip exists for them)', () => {
    const state = resolveExplainBarState(
      inputs({ flawMarkers: [marker({ ply: 10, missed_tactic_motif: 'clearance', missed_tactic_depth: 1 })] }),
    );
    expect(state).toMatchObject({ kind: 'explain', tactics: [] });
  });

  it('is hidden when not game mode or while a fast-forward Jump runs', () => {
    expect(resolveExplainBarState(inputs({ isGameMode: false })).kind).toBe('hidden');
    expect(resolveExplainBarState(inputs({ fastForwardRunning: true })).kind).toBe('hidden');
  });

  it('is hidden when a pending flaw is for another ply', () => {
    expect(
      resolveExplainBarState(inputs({ pendingFlaw: { ply: 3, orientation: 'missed' } })).kind,
    ).toBe('hidden');
  });

  it('is hidden at landingPly -1 and on an inaccuracy ply', () => {
    expect(resolveExplainBarState(inputs({ landingPly: -1 })).kind).toBe('hidden');
    expect(
      resolveExplainBarState(inputs({ flawMarkers: [marker({ ply: 10, severity: 'inaccuracy' })] })).kind,
    ).toBe('hidden');
  });

  it('is hidden while tactic lines load (undefined) or are absent (null)', () => {
    expect(resolveExplainBarState(inputs({ tacticLines: undefined })).kind).toBe('hidden');
    expect(resolveExplainBarState(inputs({ tacticLines: null })).kind).toBe('hidden');
  });

  it('is hidden when no line is usable', () => {
    expect(resolveExplainBarState(inputs({ tacticLines: tacticLines({}) })).kind).toBe('hidden');
  });

  it('uses the opponent direction rule and the marker severity', () => {
    const state = resolveExplainBarState(
      inputs({ flawMarkers: [marker({ ply: 10, is_user: false, severity: 'mistake', move_san: 'Nc6' })] }),
    );
    expect(state).toMatchObject({
      kind: 'explain',
      flaw: { ply: 10, orientation: 'allowed' },
      san: 'Nc6',
      severity: 'mistake',
    });
  });

  it('is pending when the pending flaw is for the landing ply', () => {
    const state = resolveExplainBarState(
      inputs({ pendingFlaw: { ply: 10, orientation: 'missed' } }),
    );
    expect(state).toMatchObject({ kind: 'explain', pending: true });
  });
});

describe('resolveExplainBarState got-it rule (D-06)', () => {
  const line: OpenLine = { rootNodeId: 40, ply: 10, orientation: 'missed' };
  const openLines = new Map<string, OpenLine>([['10:missed', line]]);

  it('returns got-it when the focused flaw maps to an open line, with the marker san', () => {
    const state = resolveExplainBarState(
      inputs({ focusedFlaw: { ply: 10, orientation: 'missed' }, openLines }),
    );
    expect(state).toEqual({ kind: 'got-it', line, san: 'Qh5' });
  });

  it('has a null san when no marker exists at the line ply', () => {
    const state = resolveExplainBarState(
      inputs({ focusedFlaw: { ply: 10, orientation: 'missed' }, openLines, flawMarkers: [] }),
    );
    expect(state).toEqual({ kind: 'got-it', line, san: null });
  });

  it('wins over every later rule, including a pending flaw and an off-flaw landing ply', () => {
    const state = resolveExplainBarState(
      inputs({
        focusedFlaw: { ply: 10, orientation: 'missed' },
        openLines,
        pendingFlaw: { ply: 10, orientation: 'missed' },
        landingPly: -1,
        tacticLines: undefined,
      }),
    );
    expect(state.kind).toBe('got-it');
  });

  it('does not show got-it for a focused flaw that is only pending (not in openLines)', () => {
    const state = resolveExplainBarState(
      inputs({ focusedFlaw: { ply: 10, orientation: 'missed' }, pendingFlaw: { ply: 10, orientation: 'missed' } }),
    );
    expect(state.kind).toBe('explain');
  });

  // WR-01: P=10's missed line forks at mainLine[9]; ply 9 is the opponent's mistake.
  const adjacent = {
    focusedFlaw: { ply: 10, orientation: 'missed' as const },
    openLines,
    landingPly: 9,
    flawMarkers: [marker({ ply: 9, is_user: false, severity: 'mistake', move_san: 'f6' }), marker({ ply: 10 })],
  };

  it('WR-01: on the missed-line fork, an explainable flaw at the landing ply wins over got-it', () => {
    const state = resolveExplainBarState(inputs(adjacent));
    expect(state).toEqual({
      kind: 'explain',
      flaw: { ply: 9, orientation: 'allowed' },
      san: 'f6',
      severity: 'mistake',
      tactics: [],
      pending: false,
    });
  });

  it('WR-01: the fork keeps got-it while the landing flaw has no usable lines yet', () => {
    expect(resolveExplainBarState(inputs({ ...adjacent, tacticLines: undefined }))).toEqual({
      kind: 'got-it',
      line,
      san: 'Qh5',
    });
  });

  it('WR-01: the fork keeps got-it when the landing ply is not a mistake or blunder', () => {
    const flawMarkers = [marker({ ply: 9, is_user: false, severity: 'inaccuracy' }), marker({ ply: 10 })];
    expect(resolveExplainBarState(inputs({ ...adjacent, flawMarkers })).kind).toBe('got-it');
  });

  it("WR-01: an allowed line's fork is the flaw node itself and keeps got-it", () => {
    const allowed: OpenLine = { rootNodeId: 41, ply: 10, orientation: 'allowed' };
    const state = resolveExplainBarState(
      inputs({
        focusedFlaw: { ply: 10, orientation: 'allowed' },
        openLines: new Map([['10:allowed', allowed]]),
        landingPly: 10,
      }),
    );
    expect(state).toEqual({ kind: 'got-it', line: allowed, san: 'Qh5' });
  });

  it('still loses to rule 1 (not game mode, fast-forward running)', () => {
    const base = { focusedFlaw: { ply: 10, orientation: 'missed' as const }, openLines };
    expect(resolveExplainBarState(inputs({ ...base, isGameMode: false })).kind).toBe('hidden');
    expect(resolveExplainBarState(inputs({ ...base, fastForwardRunning: true })).kind).toBe('hidden');
  });
});
