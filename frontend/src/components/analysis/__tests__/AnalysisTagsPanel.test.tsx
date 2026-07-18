// @vitest-environment jsdom
/**
 * AnalysisTagsPanel vitest suite (quick-260702-nm8; migrated to MoveStats in
 * Phase 179 Plan 03, SEED-112).
 *
 * Covers: MoveStats cell counts/cycling (first/next/wrap/restart), zero-cell
 * inertness, both-sided (category × side) coverage (D-08), the 3-column
 * Missed/Allowed/Context tactic block, and the analyzed-only mount guard
 * (D-03/D-07 — no markers/tiers emptiness clause).
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { AnalysisTagsPanel } from '../AnalysisTagsPanel';
import type { GameFlawCard, FlawMarker } from '@/types/library';

// TagChip's useIsMobile hook reads window.matchMedia — jsdom has no implementation,
// so it must be stubbed (mirrors LibraryGameCard.test.tsx).
beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

afterEach(() => {
  cleanup();
});

function buildMarker(overrides: Partial<FlawMarker>): FlawMarker {
  return {
    ply: 0,
    severity: 'inaccuracy',
    tags: [],
    is_user: true,
    move_san: null,
    allowed_tactic_motif: null,
    allowed_tactic_confidence: null,
    allowed_tactic_depth: null,
    missed_tactic_motif: null,
    missed_tactic_confidence: null,
    missed_tactic_depth: null,
    ...overrides,
  };
}

function buildGame(overrides: Partial<GameFlawCard> = {}): GameFlawCard {
  return {
    game_id: 1,
    user_result: 'win',
    played_at: null,
    time_control_bucket: null,
    platform: 'chess.com',
    platform_url: null,
    white_username: 'alice',
    black_username: 'bob',
    white_rating: null,
    black_rating: null,
    opening_name: null,
    opening_eco: null,
    user_color: 'white',
    ply_count: null,
    termination: null,
    time_control_str: null,
    result_fen: null,
    severity_counts: { inaccuracy: 0, mistake: 0, blunder: 0 },
    white_accuracy: null,
    black_accuracy: null,
    chips: [],
    analysis_state: 'analyzed',
    eval_series: null,
    flaw_markers: [],
    phase_transitions: null,
    moves: null,
    active_eval_status: null,
    opening_ply_count: 0,
    ...overrides,
  };
}

describe('AnalysisTagsPanel', () => {
  // ply 4 (even) = white/user; ply 8 (even) = white/user; ply 12 (even) = white/user.
  const blunderMarker = buildMarker({
    ply: 4,
    severity: 'blunder',
    is_user: true,
    missed_tactic_motif: 'fork',
    missed_tactic_depth: 1,
  });
  const mistakeMarker = buildMarker({
    ply: 8,
    severity: 'mistake',
    is_user: true,
    allowed_tactic_motif: 'pin',
    allowed_tactic_depth: 1,
  });
  const contextMarker = buildMarker({
    ply: 12,
    severity: 'inaccuracy',
    is_user: true,
    tags: ['hasty'],
  });
  // Odd ply (7) = black/opponent — a genuinely opposite-side marker for D-08.
  const opponentMarker = buildMarker({
    ply: 7,
    severity: 'blunder',
    is_user: false,
    missed_tactic_motif: 'skewer',
    missed_tactic_depth: 1,
  });

  const fixture = buildGame({
    severity_counts: { inaccuracy: 1, mistake: 1, blunder: 2 },
    chips: ['hasty'],
    flaw_markers: [blunderMarker, mistakeMarker, contextMarker, opponentMarker],
  });

  it('renders the MoveStats table with correct per-side severity counts', () => {
    render(<AnalysisTagsPanel game={fixture} onCyclePly={() => {}} />);
    // White (user): 1 blunder (ply 4), 1 mistake (ply 8), 1 inaccuracy (ply 12).
    expect(screen.getByTestId('move-stats-cell-blunder-white-1').textContent).toBe('1');
    expect(screen.getByTestId('move-stats-cell-mistake-white-1').textContent).toBe('1');
    expect(screen.getByTestId('move-stats-cell-inaccuracy-white-1').textContent).toBe('1');
    // Black (opponent): 1 blunder (ply 7) — surfaced too (D-08).
    expect(screen.getByTestId('move-stats-cell-blunder-black-1').textContent).toBe('1');
  });

  it('renders the 3-column Missed | Allowed | Context block', () => {
    render(<AnalysisTagsPanel game={fixture} onCyclePly={() => {}} />);
    expect(screen.getByTestId('tactic-group-missed-1')).toBeDefined();
    expect(screen.getByTestId('tactic-group-allowed-1')).toBeDefined();
    expect(screen.getByTestId('context-column-1')).toBeDefined();
    // Missed chip present (fork, user marker); allowed chip present (pin, user
    // marker). Opponent's skewer motif is a MISSED chip too (tactic chips stay
    // user-scoped — unaffected by the D-08 MoveStats rework).
    expect(screen.getByTestId('chip-tactic-missed-fork-1')).toBeDefined();
    expect(screen.getByTestId('chip-tactic-allowed-pin-1')).toBeDefined();
    expect(screen.queryByTestId('chip-tactic-missed-skewer-1')).toBeNull();
  });

  it('cycles onCyclePly first/next/wrap on repeated clicks of the same MoveStats cell', () => {
    // Two user (white, even-ply) blunders so cycling is observable.
    const twoBlunders = buildGame({
      severity_counts: { inaccuracy: 0, mistake: 0, blunder: 2 },
      chips: [],
      flaw_markers: [
        buildMarker({ ply: 2, severity: 'blunder', is_user: true }),
        buildMarker({ ply: 10, severity: 'blunder', is_user: true }),
      ],
    });
    const onCyclePly = vi.fn();
    render(<AnalysisTagsPanel game={twoBlunders} onCyclePly={onCyclePly} />);
    const cell = screen.getByTestId('move-stats-cell-blunder-white-1');
    expect(cell.tagName).toBe('BUTTON');
    fireEvent.click(cell);
    expect(onCyclePly).toHaveBeenNthCalledWith(1, 2);
    fireEvent.click(cell);
    expect(onCyclePly).toHaveBeenNthCalledWith(2, 10);
    fireEvent.click(cell);
    // Wraps back to the first ply.
    expect(onCyclePly).toHaveBeenNthCalledWith(3, 2);
  });

  it('restarts the cycle at position 0 when clicking a different cell', () => {
    const onCyclePly = vi.fn();
    render(<AnalysisTagsPanel game={fixture} onCyclePly={onCyclePly} />);
    fireEvent.click(screen.getByTestId('move-stats-cell-blunder-white-1'));
    expect(onCyclePly).toHaveBeenLastCalledWith(4);
    fireEvent.click(screen.getByTestId('move-stats-cell-mistake-white-1'));
    expect(onCyclePly).toHaveBeenLastCalledWith(8);
    // Clicking blunder again restarts at its own first (only user) ply.
    fireEvent.click(screen.getByTestId('move-stats-cell-blunder-white-1'));
    expect(onCyclePly).toHaveBeenLastCalledWith(4);
  });

  it('cycles the opponent (black) blunder cell independently, never visiting the user ply (D-08/D-09)', () => {
    const onCyclePly = vi.fn();
    render(<AnalysisTagsPanel game={fixture} onCyclePly={onCyclePly} />);
    fireEvent.click(screen.getByTestId('move-stats-cell-blunder-black-1'));
    // Only the opponent ply (7) — never the user's blunder ply (4).
    expect(onCyclePly).toHaveBeenCalledWith(7);
    expect(onCyclePly).not.toHaveBeenCalledWith(4);
  });

  it('a zero cell is inert — not a button, never calls onCyclePly', () => {
    const noMistakes = buildGame({
      severity_counts: { inaccuracy: 0, mistake: 0, blunder: 1 },
      chips: [],
      flaw_markers: [buildMarker({ ply: 0, severity: 'blunder', is_user: true })],
    });
    const onCyclePly = vi.fn();
    render(<AnalysisTagsPanel game={noMistakes} onCyclePly={onCyclePly} />);
    const cell = screen.getByTestId('move-stats-cell-mistake-white-1');
    expect(cell.tagName).not.toBe('BUTTON');
    fireEvent.click(cell);
    expect(onCyclePly).not.toHaveBeenCalled();
  });

  it('returns null when analysis_state is not analyzed', () => {
    const unanalyzed = buildGame({ analysis_state: 'no_engine_analysis', flaw_markers: null });
    const { container } = render(<AnalysisTagsPanel game={unanalyzed} onCyclePly={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the full all-zero 7-row table for a flawless analyzed game, instead of null (D-03/Pitfall 2)', () => {
    const flawless = buildGame({ flaw_markers: [] });
    render(<AnalysisTagsPanel game={flawless} onCyclePly={() => {}} />);
    expect(screen.getByTestId('analysis-tags-panel')).toBeDefined();
    expect(screen.getByTestId('move-stats-cell-blunder-white-1').textContent).toBe('0');
    expect(screen.getByTestId('move-stats-cell-gem-white-1').textContent).toBe('0');
  });
});

describe('AnalysisTagsPanel MoveStats gem/great tiers (Phase 175 Plan 06, both-sided per D-08)', () => {
  // buildGame sets user_color: 'white', so even plies (0, 2, 4) are the USER's moves
  // and odd plies (1, 3) are the opponent's. best_move_tier is POSITION-scoped, and
  // D-08 deliberately surfaces BOTH sides here (reversing the old user-only
  // GemGreatBadge filter). User: gem@0, great@2, gem@4. Opponent: gem@1, great@3.
  const gemGreatFixture = buildGame({
    severity_counts: { inaccuracy: 0, mistake: 0, blunder: 0 },
    chips: [],
    flaw_markers: [],
    eval_series: [
      { ply: 0, es: 0.5, eval_cp: 0, eval_mate: null, best_move_tier: 'gem', maia_prob: 0.1 },
      { ply: 1, es: 0.55, eval_cp: 10, eval_mate: null, best_move_tier: 'gem', maia_prob: 0.12 },
      { ply: 2, es: 0.6, eval_cp: 20, eval_mate: null, best_move_tier: 'great', maia_prob: 0.3 },
      { ply: 3, es: 0.62, eval_cp: 25, eval_mate: null, best_move_tier: 'great', maia_prob: 0.32 },
      { ply: 4, es: 0.64, eval_cp: 30, eval_mate: null, best_move_tier: 'gem', maia_prob: 0.15 },
    ],
  });

  it('shows BOTH the user gem count and the opponent gem count (D-08)', () => {
    render(<AnalysisTagsPanel game={gemGreatFixture} onCyclePly={() => {}} />);
    // User (white) gems: plies 0, 4 → 2.
    expect(screen.getByTestId('move-stats-cell-gem-white-1').textContent).toBe('2');
    // Opponent (black) gem: ply 1 → 1, now surfaced too.
    expect(screen.getByTestId('move-stats-cell-gem-black-1').textContent).toBe('1');
  });

  it('shows BOTH the user great count and the opponent great count (D-08)', () => {
    render(<AnalysisTagsPanel game={gemGreatFixture} onCyclePly={() => {}} />);
    expect(screen.getByTestId('move-stats-cell-great-white-1').textContent).toBe('1');
    expect(screen.getByTestId('move-stats-cell-great-black-1').textContent).toBe('1');
  });

  it('renders even with zero flaw markers, as long as gem/great plies exist (D-03/Pitfall 2)', () => {
    const noFlawsButGem = buildGame({
      severity_counts: { inaccuracy: 0, mistake: 0, blunder: 0 },
      chips: [],
      flaw_markers: [],
      eval_series: [
        { ply: 0, es: 0.5, eval_cp: 0, eval_mate: null, best_move_tier: 'gem', maia_prob: 0.1 },
      ],
    });
    const { container } = render(<AnalysisTagsPanel game={noFlawsButGem} onCyclePly={() => {}} />);
    expect(container.firstChild).not.toBeNull();
    expect(screen.getByTestId('move-stats-cell-gem-white-1').textContent).toBe('1');
  });

  it('cycling the user gem cell invokes onCyclePly with the user gem plies only, wrapping', () => {
    const onCyclePly = vi.fn();
    render(<AnalysisTagsPanel game={gemGreatFixture} onCyclePly={onCyclePly} />);
    const cell = screen.getByTestId('move-stats-cell-gem-white-1');
    fireEvent.click(cell);
    // User gems are plies 0 and 4 — never ply 1 (opponent).
    expect(onCyclePly).toHaveBeenNthCalledWith(1, 0);
    fireEvent.click(cell);
    expect(onCyclePly).toHaveBeenNthCalledWith(2, 4);
    fireEvent.click(cell);
    // Wraps back to the first user gem ply.
    expect(onCyclePly).toHaveBeenNthCalledWith(3, 0);
    // Never visits the opponent gem ply.
    expect(onCyclePly).not.toHaveBeenCalledWith(1);
  });

  it('cycling the user great cell is independent of the gem cell', () => {
    const onCyclePly = vi.fn();
    render(<AnalysisTagsPanel game={gemGreatFixture} onCyclePly={onCyclePly} />);
    fireEvent.click(screen.getByTestId('move-stats-cell-gem-white-1'));
    fireEvent.click(screen.getByTestId('move-stats-cell-great-white-1'));
    // The user's only great ply (2), never the opponent great ply 3.
    expect(onCyclePly).toHaveBeenLastCalledWith(2);
    expect(onCyclePly).not.toHaveBeenCalledWith(3);
  });
});
