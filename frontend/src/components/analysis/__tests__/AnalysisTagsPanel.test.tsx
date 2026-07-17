// @vitest-environment jsdom
/**
 * AnalysisTagsPanel vitest suite (quick-260702-nm8).
 *
 * Covers: severity-row counts, click-to-cycle (first/next/wrap/restart), non-user
 * marker exclusion, and the analyzed/no-markers null guard.
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
    chips: [],
    analysis_state: 'analyzed',
    eval_series: null,
    flaw_markers: [],
    phase_transitions: null,
    moves: null,
    active_eval_status: null,
    ...overrides,
  };
}

describe('AnalysisTagsPanel', () => {
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
  // Non-user marker with its own severity + motif — must be excluded entirely.
  const opponentMarker = buildMarker({
    ply: 6,
    severity: 'blunder',
    is_user: false,
    missed_tactic_motif: 'skewer',
    missed_tactic_depth: 1,
  });

  const fixture = buildGame({
    severity_counts: { inaccuracy: 1, mistake: 1, blunder: 1 },
    chips: ['hasty'],
    flaw_markers: [blunderMarker, mistakeMarker, contextMarker, opponentMarker],
  });

  it('renders three SeverityBadge elements with correct counts', () => {
    render(<AnalysisTagsPanel game={fixture} onCyclePly={() => {}} />);
    expect(screen.getByTestId('severity-blunder-1').textContent).toContain('1');
    expect(screen.getByTestId('severity-mistake-1').textContent).toContain('1');
    expect(screen.getByTestId('severity-inaccuracy-1').textContent).toContain('1');
  });

  it('renders the 3-column Missed | Allowed | Context block', () => {
    render(<AnalysisTagsPanel game={fixture} onCyclePly={() => {}} />);
    expect(screen.getByTestId('tactic-group-missed-1')).toBeDefined();
    expect(screen.getByTestId('tactic-group-allowed-1')).toBeDefined();
    expect(screen.getByTestId('context-column-1')).toBeDefined();
    // Missed chip present (fork), allowed chip present (pin); opponent's skewer excluded.
    expect(screen.getByTestId('chip-tactic-missed-fork-1')).toBeDefined();
    expect(screen.getByTestId('chip-tactic-allowed-pin-1')).toBeDefined();
    expect(screen.queryByTestId('chip-tactic-missed-skewer-1')).toBeNull();
  });

  it('cycles onCyclePly first/next/wrap on repeated clicks of the same severity badge', () => {
    // Two blunder plies so cycling is observable.
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
    const badge = screen.getByTestId('severity-blunder-1');
    fireEvent.click(badge);
    expect(onCyclePly).toHaveBeenNthCalledWith(1, 2);
    fireEvent.click(badge);
    expect(onCyclePly).toHaveBeenNthCalledWith(2, 10);
    fireEvent.click(badge);
    // Wraps back to the first ply.
    expect(onCyclePly).toHaveBeenNthCalledWith(3, 2);
  });

  it('restarts the cycle at position 0 when clicking a different ref', () => {
    const onCyclePly = vi.fn();
    render(<AnalysisTagsPanel game={fixture} onCyclePly={onCyclePly} />);
    fireEvent.click(screen.getByTestId('severity-blunder-1'));
    expect(onCyclePly).toHaveBeenLastCalledWith(4);
    fireEvent.click(screen.getByTestId('severity-mistake-1'));
    expect(onCyclePly).toHaveBeenLastCalledWith(8);
    // Clicking blunder again restarts at its own first (only) ply.
    fireEvent.click(screen.getByTestId('severity-blunder-1'));
    expect(onCyclePly).toHaveBeenLastCalledWith(4);
  });

  it('excludes a non-user marker from counts and cycles', () => {
    const onCyclePly = vi.fn();
    render(<AnalysisTagsPanel game={fixture} onCyclePly={onCyclePly} />);
    // Blunder count is 1 (only the user marker), even though a non-user blunder also exists.
    expect(screen.getByTestId('severity-blunder-1').textContent).toContain('1');
    fireEvent.click(screen.getByTestId('severity-blunder-1'));
    // Only ply 4 (user marker) is ever reached — never ply 6 (opponent marker).
    expect(onCyclePly).toHaveBeenCalledWith(4);
    expect(onCyclePly).not.toHaveBeenCalledWith(6);
  });

  it('a ref with an empty ply list does not call onCyclePly', () => {
    const noMistakes = buildGame({
      severity_counts: { inaccuracy: 0, mistake: 0, blunder: 1 },
      chips: [],
      flaw_markers: [buildMarker({ ply: 1, severity: 'blunder', is_user: true })],
    });
    const onCyclePly = vi.fn();
    render(<AnalysisTagsPanel game={noMistakes} onCyclePly={onCyclePly} />);
    fireEvent.click(screen.getByTestId('severity-mistake-1'));
    expect(onCyclePly).not.toHaveBeenCalled();
  });

  it('returns null when analysis_state is not analyzed', () => {
    const unanalyzed = buildGame({ analysis_state: 'no_engine_analysis', flaw_markers: null });
    const { container } = render(<AnalysisTagsPanel game={unanalyzed} onCyclePly={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when there are no flaw markers', () => {
    const empty = buildGame({ flaw_markers: [] });
    const { container } = render(<AnalysisTagsPanel game={empty} onCyclePly={() => {}} />);
    expect(container.firstChild).toBeNull();
  });
});

describe('AnalysisTagsPanel Gem/Great badges (Phase 175 Plan 06)', () => {
  // buildGame sets user_color: 'white', so even plies (0, 2, 4) are the USER's moves
  // and odd plies (1, 3) are the opponent's. best_move_tier is POSITION-scoped, so the
  // fixture seeds gems/greats on BOTH sides to prove the user-only filter (Plan 06 fix).
  // User: gem@0, great@2, gem@4. Opponent: gem@1, great@3.
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

  it('counts only USER gems/greats, excluding the opponent (odd-ply) ones', () => {
    render(<AnalysisTagsPanel game={gemGreatFixture} onCyclePly={() => {}} />);
    // User gems: plies 0, 4 → 2 (opponent gem@1 excluded).
    expect(screen.getByTestId('badge-gem-1').textContent).toContain('2');
    // User great: ply 2 → 1 (opponent great@3 excluded).
    expect(screen.getByTestId('badge-great-1').textContent).toContain('1');
  });

  it('renders no Gem/Great badges when the game has no gem/great plies', () => {
    const noBestMoves = buildGame({
      severity_counts: { inaccuracy: 0, mistake: 1, blunder: 0 },
      chips: [],
      flaw_markers: [buildMarker({ ply: 4, severity: 'mistake', is_user: true })],
      eval_series: [{ ply: 4, es: 0.5, eval_cp: 0, eval_mate: null, best_move_tier: null, maia_prob: null }],
    });
    render(<AnalysisTagsPanel game={noBestMoves} onCyclePly={() => {}} />);
    expect(screen.queryByTestId('badge-gem-1')).toBeNull();
    expect(screen.queryByTestId('badge-great-1')).toBeNull();
  });

  it('shows no badge when only the opponent has gems (white user, gem on an odd ply)', () => {
    const opponentOnlyGem = buildGame({
      severity_counts: { inaccuracy: 0, mistake: 0, blunder: 0 },
      chips: [],
      flaw_markers: [],
      eval_series: [
        { ply: 1, es: 0.5, eval_cp: 0, eval_mate: null, best_move_tier: 'gem', maia_prob: 0.1 },
      ],
    });
    const { container } = render(<AnalysisTagsPanel game={opponentOnlyGem} onCyclePly={() => {}} />);
    // No user flaws, no user gems/greats → the panel renders nothing at all.
    expect(container.firstChild).toBeNull();
  });

  it('renders even with zero flaw markers, as long as USER gem/great plies exist', () => {
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
    expect(screen.getByTestId('badge-gem-1')).toBeDefined();
  });

  it('cycling the Gem badge invokes onCyclePly with the USER gem plies only, wrapping', () => {
    const onCyclePly = vi.fn();
    render(<AnalysisTagsPanel game={gemGreatFixture} onCyclePly={onCyclePly} />);
    const badge = screen.getByTestId('badge-gem-1');
    fireEvent.click(badge);
    // User gems are plies 0 and 4 — never ply 1 (opponent).
    expect(onCyclePly).toHaveBeenNthCalledWith(1, 0);
    fireEvent.click(badge);
    expect(onCyclePly).toHaveBeenNthCalledWith(2, 4);
    fireEvent.click(badge);
    // Wraps back to the first user gem ply.
    expect(onCyclePly).toHaveBeenNthCalledWith(3, 0);
    // Never visits the opponent gem ply.
    expect(onCyclePly).not.toHaveBeenCalledWith(1);
  });

  it('cycling the Great badge invokes onCyclePly with the user great ply, independent of Gem', () => {
    const onCyclePly = vi.fn();
    render(<AnalysisTagsPanel game={gemGreatFixture} onCyclePly={onCyclePly} />);
    fireEvent.click(screen.getByTestId('badge-gem-1'));
    fireEvent.click(screen.getByTestId('badge-great-1'));
    // The user's only great ply (2), never the opponent great ply 3.
    expect(onCyclePly).toHaveBeenLastCalledWith(2);
    expect(onCyclePly).not.toHaveBeenCalledWith(3);
  });
});
