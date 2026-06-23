// @vitest-environment jsdom
/**
 * LibraryGameCard tactic-chip tests — Quick 260620-pza.
 *
 * The Games-tab card now surfaces BOTH tactic orientations: a flaw's
 * allowed_tactic_motif and missed_tactic_motif render as SEPARATE chips with the
 * orientation prefix (e.g. "missed: fork" and "allowed: fork"). Previously only the
 * allowed motif was shown.
 *
 * The chip testid encodes orientation: chip-tactic-{orientation}-{motif}-{gameId}.
 *
 * NOTE: the card renders flawContent in BOTH a mobile (sm:hidden) and desktop body,
 * so every chip appears twice in jsdom (CSS hides one at a time at runtime). Assertions
 * use getAllByTestId / queryAllByTestId rather than the single-element getByTestId.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import type { ReactNode } from 'react';

// Stub Tooltip so tests don't need a TooltipProvider wrapper.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => children,
}));

// Shared flaw filter store stub. Mutable (via vi.hoisted) so a test can activate a
// context-tag filter (e.g. low-clock) and assert the tactic chips are gated by it.
const filterStore = vi.hoisted(() => ({
  filter: { severity: ['blunder', 'mistake'], tags: [] as string[] },
}));
vi.mock('@/hooks/useFlawFilterStore', () => ({
  useFlawFilterStore: () => [filterStore.filter, vi.fn()] as const,
}));

// Stub the heavy eval chart + lazy board so the card renders cheaply in jsdom. The
// chart stub exposes a button that fires onHoverPlyChange so the platform-link tests
// can simulate scrubbing the slider to a given ply.
const scrubCtl = vi.hoisted(() => ({ ply: 0 }));
vi.mock('@/components/library/EvalChart', () => ({
  EvalChart: ({ onHoverPlyChange }: { onHoverPlyChange?: (p: number | null) => void }) => (
    <button
      type="button"
      data-testid="stub-eval-chart"
      onClick={() => onHoverPlyChange?.(scrubCtl.ply)}
    />
  ),
}));
vi.mock('@/components/board/LazyMiniBoard', () => ({
  LazyMiniBoard: () => <div data-testid="stub-mini-board" />,
}));

import { LibraryGameCard } from '../LibraryGameCard';
import type { GameFlawCard, FlawMarker } from '@/types/library';

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
  // Reset the mutable filter stub so context-filter tests don't leak into the defaults.
  filterStore.filter = { severity: ['blunder', 'mistake'], tags: [] };
  scrubCtl.ply = 0;
});

const GAME_ID = 77;

function marker(overrides: Partial<FlawMarker>): FlawMarker {
  return {
    ply: 2,
    severity: 'blunder',
    tags: [],
    is_user: true,
    move_san: 'Nxd4',
    allowed_tactic_motif: null,
    allowed_tactic_confidence: null,
    allowed_tactic_depth: null,
    missed_tactic_motif: null,
    missed_tactic_confidence: null,
    missed_tactic_depth: null,
    ...overrides,
  };
}

function makeGame(markers: FlawMarker[]): GameFlawCard {
  return {
    game_id: GAME_ID,
    user_result: 'loss',
    played_at: '2026-01-15T10:00:00Z',
    time_control_bucket: 'rapid',
    platform: 'lichess',
    platform_url: 'https://lichess.org/abc',
    white_username: 'Alice',
    black_username: 'Bob',
    white_rating: 1850,
    black_rating: 1720,
    opening_name: 'Sicilian Defense',
    opening_eco: 'B20',
    user_color: 'white',
    ply_count: 80,
    termination: 'checkmate',
    time_control_str: '10+5',
    result_fen: null,
    severity_counts: { inaccuracy: 0, mistake: 0, blunder: 2 },
    chips: [],
    analysis_state: 'analyzed',
    eval_series: [{ ply: 0, es: 0.5, eval_cp: 0, eval_mate: null }],
    flaw_markers: markers,
    phase_transitions: { middlegame_ply: null, endgame_ply: null },
    moves: ['e4'],
    active_eval_status: null,
  };
}

describe('LibraryGameCard tactic chips (missed vs allowed)', () => {
  it('renders missed and allowed chips for the same motif as two separate chips', () => {
    render(
      <LibraryGameCard
        game={makeGame([
          marker({ ply: 2, allowed_tactic_motif: 'fork', allowed_tactic_confidence: 90 }),
          marker({ ply: 4, missed_tactic_motif: 'fork', missed_tactic_confidence: 90 }),
        ])}
      />,
    );
    expect(screen.getAllByTestId(`chip-tactic-allowed-fork-${GAME_ID}`).length).toBeGreaterThan(0);
    expect(screen.getAllByTestId(`chip-tactic-missed-fork-${GAME_ID}`).length).toBeGreaterThan(0);
  });

  it('renders only the allowed chip when no missed motif is present', () => {
    render(
      <LibraryGameCard
        game={makeGame([
          marker({ ply: 2, allowed_tactic_motif: 'pin', allowed_tactic_confidence: 90 }),
        ])}
      />,
    );
    expect(screen.getAllByTestId(`chip-tactic-allowed-pin-${GAME_ID}`).length).toBeGreaterThan(0);
    expect(screen.queryAllByTestId(`chip-tactic-missed-pin-${GAME_ID}`)).toHaveLength(0);
  });

  it('renders only the missed chip when no allowed motif is present', () => {
    render(
      <LibraryGameCard
        game={makeGame([
          marker({ ply: 2, missed_tactic_motif: 'skewer', missed_tactic_confidence: 90 }),
        ])}
      />,
    );
    expect(screen.getAllByTestId(`chip-tactic-missed-skewer-${GAME_ID}`).length).toBeGreaterThan(0);
    expect(screen.queryAllByTestId(`chip-tactic-allowed-skewer-${GAME_ID}`)).toHaveLength(0);
  });

  it('does not surface opponent (non-user) tactic motifs', () => {
    render(
      <LibraryGameCard
        game={makeGame([
          marker({ ply: 3, is_user: false, allowed_tactic_motif: 'fork', allowed_tactic_confidence: 90 }),
        ])}
      />,
    );
    expect(screen.queryAllByTestId(`chip-tactic-allowed-fork-${GAME_ID}`)).toHaveLength(0);
  });
});

describe('LibraryGameCard tactic chips gated by active context filter (Quick 260621)', () => {
  // Tactic family/depth/orientation are enforced server-side by nulling the per-marker
  // tactic slots, but context tags (low-clock) live on the marker and are never nulled.
  // The card must drop forks on markers that fail the active context filter so the chip
  // set/count matches the filtered games list (single-marker AND).

  it('hides a fork chip whose only marker fails the active context filter', () => {
    filterStore.filter = { severity: ['blunder', 'mistake'], tags: ['low-clock'] };
    render(
      <LibraryGameCard
        game={makeGame([
          // A depth-matching fork, but NOT low-clock — must be dropped under the low-clock filter.
          marker({
            ply: 2,
            tags: [],
            allowed_tactic_motif: 'fork',
            allowed_tactic_confidence: 90,
          }),
        ])}
      />,
    );
    expect(screen.queryAllByTestId(`chip-tactic-allowed-fork-${GAME_ID}`)).toHaveLength(0);
  });

  it('keeps a fork chip when its marker satisfies the active context filter', () => {
    filterStore.filter = { severity: ['blunder', 'mistake'], tags: ['low-clock'] };
    render(
      <LibraryGameCard
        game={makeGame([
          // Fork on a low-clock marker — passes; sibling fork without low-clock is dropped.
          marker({
            ply: 2,
            tags: ['low-clock'],
            allowed_tactic_motif: 'fork',
            allowed_tactic_confidence: 90,
          }),
          marker({
            ply: 4,
            tags: [],
            allowed_tactic_motif: 'fork',
            allowed_tactic_confidence: 90,
          }),
        ])}
      />,
    );
    expect(screen.getAllByTestId(`chip-tactic-allowed-fork-${GAME_ID}`).length).toBeGreaterThan(0);
  });
});

describe('LibraryGameCard platform link follows the eval-chart scrub', () => {
  // A multi-ply eval series so the last eval'd ply (2) differs from a scrubbed-back ply.
  function multiPlyGame(): GameFlawCard {
    return {
      ...makeGame([]),
      eval_series: [
        { ply: 0, es: 0.5, eval_cp: 0, eval_mate: null },
        { ply: 1, es: 0.4, eval_cp: -50, eval_mate: null },
        { ply: 2, es: 0.6, eval_cp: 80, eval_mate: null },
      ],
    };
  }

  it('links to the game (no ply fragment) at the resting position', () => {
    render(<LibraryGameCard game={multiPlyGame()} />);
    // hoverPly is null until the chart reports, and the resting ply equals the last
    // eval'd ply, so the header opens the game itself (white → no /black suffix).
    const link = screen.getAllByTestId(`game-card-link-${GAME_ID}`)[0];
    expect(link?.getAttribute('href')).toBe('https://lichess.org/abc');
  });

  it('deep-links to the scrubbed move when the slider is off the last ply', () => {
    scrubCtl.ply = 1; // scrub back to ply 1 (last eval'd ply is 2)
    render(<LibraryGameCard game={multiPlyGame()} />);
    fireEvent.click(screen.getAllByTestId('stub-eval-chart')[0]!);
    // platformPlyUrl navigates to ply + 1 → position after the move at ply 1.
    const link = screen.getAllByTestId(`game-card-link-${GAME_ID}`)[0];
    expect(link?.getAttribute('href')).toBe('https://lichess.org/abc#2');
  });

  it('returns to the game link when scrubbed back to the last ply', () => {
    scrubCtl.ply = 2; // the last eval'd ply
    render(<LibraryGameCard game={multiPlyGame()} />);
    fireEvent.click(screen.getAllByTestId('stub-eval-chart')[0]!);
    const link = screen.getAllByTestId(`game-card-link-${GAME_ID}`)[0];
    expect(link?.getAttribute('href')).toBe('https://lichess.org/abc');
  });
});
