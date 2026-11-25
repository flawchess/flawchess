// @vitest-environment jsdom
/**
 * LibraryGameCard tactic-chip tests.
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

import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import type { ReactNode } from 'react';

// Stub Tooltip so tests don't need a TooltipProvider wrapper.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => children,
}));

// Shared flaw filter store stub. Mutable (via vi.hoisted) so a test can activate a
// context-tag or tactic filter and assert the card's behavior (the
// filter now only selects games — it never hides a chip — but it DOES drive the
// depth-aware active-filter ring, so tacticFamilies/tacticOrientation/tacticDepthMin/
// tacticDepthMax must be present with their real defaults for that logic to run).
function defaultTestFilter() {
  return {
    // [] = the default filter: no Flaws tag selected, so nothing narrows and no cell rings.
    severity: [] as string[],
    hasGem: false,
    hasGreat: false,
    tags: [] as string[],
    tacticFamilies: [] as string[],
    tacticOrientation: 'either' as const,
    tacticDepthMin: 0,
    tacticDepthMax: 11,
  };
}
const filterStore = vi.hoisted(() => ({
  filter: {
    severity: [] as string[],
    hasGem: false,
    hasGreat: false,
    tags: [] as string[],
    tacticFamilies: [] as string[],
    tacticOrientation: 'either' as const,
    tacticDepthMin: 0,
    tacticDepthMax: 11,
  },
}));
vi.mock('@/hooks/useFlawFilterStore', () => ({
  useFlawFilterStore: () => [filterStore.filter, vi.fn()] as const,
}));

// Stub the heavy eval chart + lazy board so the card renders cheaply in jsdom. The
// chart stub exposes a button that fires onActivePlyChange so the platform-link tests
// can simulate scrubbing the slider to a given ply.
const scrubCtl = vi.hoisted(() => ({ ply: 0 }));
vi.mock('@/components/library/EvalChart', () => ({
  EvalChart: ({
    onActivePlyChange,
    commandedPly,
    commandSeq,
    heightClass,
  }: {
    onActivePlyChange?: (p: number | null) => void;
    commandedPly?: number | null;
    commandSeq?: number;
    heightClass?: string;
  }) => (
    <div>
      <button
        type="button"
        data-testid="stub-eval-chart"
        onClick={() => onActivePlyChange?.(scrubCtl.ply)}
      />
      {/* Exposes the imperative scrub command (gem/great cycling
          tests) so a click on a badge/chip can be asserted end-to-end. */}
      <span data-testid="stub-eval-chart-command">{`${commandedPly ?? 'null'}:${commandSeq ?? 0}`}</span>
      <span data-testid="stub-eval-chart-height">{heightClass}</span>
    </div>
  ),
}));
vi.mock('@/components/board/LazyMiniBoard', () => ({
  // Serialize the scrubbed-ply squareMarkers so corner-badge tier tests can assert
  // which glyph (gem/great/best/good/severity) the miniboard would render.
  LazyMiniBoard: ({
    size,
    squareMarkers,
  }: {
    size: number;
    squareMarkers?: {
      square: string;
      severity?: string;
      gem?: boolean;
      great?: boolean;
      best?: boolean;
      good?: boolean;
    }[];
  }) => {
    const tierOf = (m: NonNullable<typeof squareMarkers>[number]): string =>
      m.gem ? 'gem' : m.great ? 'great' : m.best ? 'best' : m.good ? 'good' : (m.severity ?? '');
    return (
      <div data-testid="stub-mini-board" data-size={size}>
        {(squareMarkers ?? []).map((m) => (
          <span key={m.square} data-testid={`mini-board-marker-${tierOf(m)}`} />
        ))}
      </div>
    );
  },
}));

import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LibraryGameCard } from '../LibraryGameCard';
import type { GameFlawCard, FlawMarker } from '@/types/library';
import { FACEPALM_HIGH_CUTOFF } from '@/lib/facepalm';
import { DESKTOP_EVAL_CHART_HEIGHT_CLASS } from '@/lib/gameCardGeometry';

/**
 * Wraps any element in a MemoryRouter (useNavigate) + a fresh QueryClientProvider
 * (NoAnalysisState's useTier1Enqueue calls useQueryClient — needed by the
 * unanalyzed-game test).
 */
function renderCard(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

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
  filterStore.filter = defaultTestFilter();
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
    white_accuracy: null,
    black_accuracy: null,
    chips: [],
    analysis_state: 'analyzed',
    eval_series: [{ ply: 0, es: 0.5, eval_cp: 0, eval_mate: null }],
    flaw_markers: markers,
    phase_transitions: { middlegame_ply: null, endgame_ply: null },
    moves: ['e4'],
    active_eval_status: null,
    opening_ply_count: 0,
  };
}

describe('LibraryGameCard tactic chips (missed vs allowed)', () => {
  it('renders missed and allowed chips for the same motif as two separate chips', () => {
    renderCard(
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
    renderCard(
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
    renderCard(
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
    renderCard(
      <LibraryGameCard
        game={makeGame([
          marker({ ply: 3, is_user: false, allowed_tactic_motif: 'fork', allowed_tactic_confidence: 90 }),
        ])}
      />,
    );
    expect(screen.queryAllByTestId(`chip-tactic-allowed-fork-${GAME_ID}`)).toHaveLength(0);
  });
});

describe('LibraryGameCard tactic chips show regardless of active context filter', () => {
  // An active context-tag filter (e.g. low-clock)
  // only selects WHICH games appear — it must never hide a tactic chip on a card that
  // is already shown. Both markers below render their fork chip even though one fails
  // the active low-clock filter.

  it('does NOT hide a fork chip whose only marker fails the active context filter', () => {
    filterStore.filter = { ...defaultTestFilter(), tags: ['low-clock'] };
    renderCard(
      <LibraryGameCard
        game={makeGame([
          // NOT low-clock — must still render under the active low-clock filter.
          marker({
            ply: 2,
            tags: [],
            allowed_tactic_motif: 'fork',
            allowed_tactic_confidence: 90,
          }),
        ])}
      />,
    );
    expect(screen.getAllByTestId(`chip-tactic-allowed-fork-${GAME_ID}`).length).toBeGreaterThan(0);
  });

  it('keeps a fork chip when its marker satisfies the active context filter', () => {
    filterStore.filter = { ...defaultTestFilter(), tags: ['low-clock'] };
    renderCard(
      <LibraryGameCard
        game={makeGame([
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

describe('LibraryGameCard tactic chip active-filter ring is depth-aware', () => {
  // Both chips below render (filters never hide content), but only the in-range chip
  // should carry the active-filter ring class. ACTIVE_FILTER_RING_CLASS applies a
  // ring-2 utility class to the chip's className when its slot fully matches the
  // active filter (family + orientation + depth).
  const RING_CLASS_FRAGMENT = 'ring-2';

  it('rings an in-range fork chip but not an out-of-range fork chip under a depth filter', () => {
    filterStore.filter = {
      ...defaultTestFilter(),
      tacticFamilies: ['fork'],
      tacticDepthMin: 1,
      tacticDepthMax: 2,
    };
    renderCard(
      <LibraryGameCard
        game={makeGame([
          // Depth 1 (missed, offset 0) → anchored 1 → in [1, 2] → ringed.
          marker({
            ply: 2,
            missed_tactic_motif: 'fork',
            missed_tactic_confidence: 90,
            missed_tactic_depth: 1,
          }),
          // Depth 10 (missed, offset 0) → anchored 10 → outside [1, 2] → NOT ringed.
          marker({
            ply: 4,
            missed_tactic_motif: 'skewer',
            missed_tactic_confidence: 90,
            missed_tactic_depth: 10,
          }),
        ])}
      />,
    );
    const forkChips = screen.getAllByTestId(`chip-tactic-missed-fork-${GAME_ID}`);
    expect(forkChips.length).toBeGreaterThan(0);
    for (const chip of forkChips) {
      expect(chip.className).toContain(RING_CLASS_FRAGMENT);
    }

    // Both chips render (selection-only filtering) but the wrong-family/out-of-range
    // skewer chip does not carry the ring.
    const skewerChips = screen.getAllByTestId(`chip-tactic-missed-skewer-${GAME_ID}`);
    expect(skewerChips.length).toBeGreaterThan(0);
    for (const chip of skewerChips) {
      expect(chip.className).not.toContain(RING_CLASS_FRAGMENT);
    }
  });

  it('rings no chips when no tactic filter is active (defaults)', () => {
    renderCard(
      <LibraryGameCard
        game={makeGame([
          marker({
            ply: 2,
            missed_tactic_motif: 'fork',
            missed_tactic_confidence: 90,
            missed_tactic_depth: 1,
          }),
        ])}
      />,
    );
    const forkChips = screen.getAllByTestId(`chip-tactic-missed-fork-${GAME_ID}`);
    expect(forkChips.length).toBeGreaterThan(0);
    for (const chip of forkChips) {
      expect(chip.className).not.toContain(RING_CLASS_FRAGMENT);
    }
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
    renderCard(<LibraryGameCard game={multiPlyGame()} />);
    // scrubPly is null until the chart reports, and the resting ply equals the last
    // eval'd ply, so the header opens the game itself (white → no /black suffix).
    const link = screen.getAllByTestId(`game-card-link-${GAME_ID}`)[0];
    expect(link?.getAttribute('href')).toBe('https://lichess.org/abc');
  });

  it('deep-links to the scrubbed move when the slider is off the last ply', () => {
    scrubCtl.ply = 1; // scrub back to ply 1 (last eval'd ply is 2)
    renderCard(<LibraryGameCard game={multiPlyGame()} />);
    fireEvent.click(screen.getAllByTestId('stub-eval-chart')[0]!);
    // platformPlyUrl navigates to ply + 1 → position after the move at ply 1.
    const link = screen.getAllByTestId(`game-card-link-${GAME_ID}`)[0];
    expect(link?.getAttribute('href')).toBe('https://lichess.org/abc#2');
  });

  it('returns to the game link when scrubbed back to the last ply', () => {
    scrubCtl.ply = 2; // the last eval'd ply
    renderCard(<LibraryGameCard game={multiPlyGame()} />);
    fireEvent.click(screen.getAllByTestId('stub-eval-chart')[0]!);
    const link = screen.getAllByTestId(`game-card-link-${GAME_ID}`)[0];
    expect(link?.getAttribute('href')).toBe('https://lichess.org/abc');
  });
});

describe('LibraryGameCard MoveStats', () => {
  // makeGame sets user_color: 'white', so even plies (0, 2, 4) are the USER's moves
  // and odd plies (1, 3) are the opponent's. best_move_tier is POSITION-scoped, and
  // The card deliberately surfaces BOTH sides' tiers on this surface (reversing the old
  // user-only GemGreatBadge filter). User: gem@0, great@2, gem@4. Opponent: gem@1,
  // great@3.
  function gemGreatGame(): GameFlawCard {
    return {
      ...makeGame([]),
      eval_series: [
        { ply: 0, es: 0.5, eval_cp: 0, eval_mate: null, best_move_tier: 'gem', maia_prob: 0.1 },
        { ply: 1, es: 0.55, eval_cp: 10, eval_mate: null, best_move_tier: 'gem', maia_prob: 0.12 },
        { ply: 2, es: 0.6, eval_cp: 20, eval_mate: null, best_move_tier: 'great', maia_prob: 0.3 },
        { ply: 3, es: 0.62, eval_cp: 25, eval_mate: null, best_move_tier: 'great', maia_prob: 0.32 },
        { ply: 4, es: 0.64, eval_cp: 30, eval_mate: null, best_move_tier: 'gem', maia_prob: 0.15 },
      ],
    };
  }

  it('renders all-zero Gem/Great cells when the game has no gem/great plies', () => {
    renderCard(<LibraryGameCard game={makeGame([])} />);
    expect(screen.getAllByTestId(`move-stats-cell-gem-white-${GAME_ID}`)[0]!.textContent).toBe('0');
    expect(screen.getAllByTestId(`move-stats-cell-great-white-${GAME_ID}`)[0]!.textContent).toBe('0');
  });

  it('shows BOTH the user gem count and the opponent gem count', () => {
    renderCard(<LibraryGameCard game={gemGreatGame()} />);
    // User (white) gems: ply 0 and ply 4 → 2.
    expect(screen.getAllByTestId(`move-stats-cell-gem-white-${GAME_ID}`)[0]!.textContent).toBe('2');
    // Opponent (black) gem: ply 1 → 1, surfaced too (unlike the old
    // user-only GemGreatBadge filter).
    expect(screen.getAllByTestId(`move-stats-cell-gem-black-${GAME_ID}`)[0]!.textContent).toBe('1');
  });

  it('shows BOTH the user great count and the opponent great count', () => {
    renderCard(<LibraryGameCard game={gemGreatGame()} />);
    expect(screen.getAllByTestId(`move-stats-cell-great-white-${GAME_ID}`)[0]!.textContent).toBe('1');
    expect(screen.getAllByTestId(`move-stats-cell-great-black-${GAME_ID}`)[0]!.textContent).toBe('1');
  });

  it('cycling a non-zero cell jumps/advances/wraps; a different cell resets; a zero cell is inert', () => {
    renderCard(<LibraryGameCard game={gemGreatGame()} />);
    const gemWhiteCell = screen.getAllByTestId(`move-stats-cell-gem-white-${GAME_ID}`)[0]!;
    expect(gemWhiteCell.tagName).toBe('BUTTON');
    fireEvent.click(gemWhiteCell);
    // User gems are plies 0 and 4 — never ply 1 (opponent).
    expect(screen.getAllByTestId('stub-eval-chart-command')[0]!.textContent).toBe('0:1');
    fireEvent.click(gemWhiteCell);
    expect(screen.getAllByTestId('stub-eval-chart-command')[0]!.textContent).toBe('4:2');
    fireEvent.click(gemWhiteCell);
    // Wraps back to the first user gem ply.
    expect(screen.getAllByTestId('stub-eval-chart-command')[0]!.textContent).toBe('0:3');

    // A different cell restarts the cycle at position 0.
    const greatWhiteCell = screen.getAllByTestId(`move-stats-cell-great-white-${GAME_ID}`)[0]!;
    fireEvent.click(greatWhiteCell);
    expect(screen.getAllByTestId('stub-eval-chart-command')[0]!.textContent).toBe('2:4');

    // A zero cell (no user/opponent blunders in this fixture) is inert — not a
    // button, and clicking it does nothing to the command nonce.
    const blunderWhiteCell = screen.getAllByTestId(`move-stats-cell-blunder-white-${GAME_ID}`)[0]!;
    expect(blunderWhiteCell.tagName).not.toBe('BUTTON');
    fireEvent.click(blunderWhiteCell);
    expect(screen.getAllByTestId('stub-eval-chart-command')[0]!.textContent).toBe('2:4');
  });
});

describe('LibraryGameCard Facepalm row split and cycling (D-02, D-04)', () => {
  // Local test scale (percent to 0..1 score); the cut is read from FACEPALM_HIGH_CUTOFF.
  const PCT_SCALE = 100;
  const ABOVE_CUT = (FACEPALM_HIGH_CUTOFF + 1) / PCT_SCALE;
  // user_color 'white'. ply 2 = user facepalm blunder, ply 4 = user unscored blunder,
  // ply 3 = opponent facepalm blunder.
  function facepalmSplitGame(): GameFlawCard {
    return makeGame([
      marker({ ply: 2, severity: 'blunder', is_user: true, facepalm_score: ABOVE_CUT }),
      marker({ ply: 4, severity: 'blunder', is_user: true, facepalm_score: null }),
      marker({ ply: 3, severity: 'blunder', is_user: false, facepalm_score: ABOVE_CUT }),
    ]);
  }
  const cell = (category: string, side: string): HTMLElement =>
    screen.getAllByTestId(`move-stats-cell-${category}-${side}-${GAME_ID}`)[0]!;

  it('counts a facepalm blunder in the Facepalm row and not in Blunder', () => {
    renderCard(<LibraryGameCard game={facepalmSplitGame()} />);
    expect(cell('facepalm', 'white').textContent).toBe('1');
    expect(cell('blunder', 'white').textContent).toBe('1');
    expect(cell('facepalm', 'black').textContent).toBe('1');
    expect(cell('blunder', 'black').textContent).toBe('0');
  });

  it('the facepalm cell cycles to the facepalm ply, the blunder cell to the unscored blunder ply', () => {
    renderCard(<LibraryGameCard game={facepalmSplitGame()} />);
    fireEvent.click(cell('facepalm', 'white'));
    expect(screen.getAllByTestId('stub-eval-chart-command')[0]!.textContent).toBe('2:1');
    fireEvent.click(cell('blunder', 'white'));
    expect(screen.getAllByTestId('stub-eval-chart-command')[0]!.textContent).toBe('4:2');
  });
});

describe('LibraryGameCard eval chart heights (D-16, D-25)', () => {
  it('gives the desktop chart the derived height class and gives the body below lg its own heights', () => {
    renderCard(<LibraryGameCard game={makeGame([])} />);
    const heights = screen.getAllByTestId('stub-eval-chart-height').map((el) => el.textContent);
    expect(heights).toContain(DESKTOP_EVAL_CHART_HEIGHT_CLASS);
    expect(heights).toContain('h-[114px] md:h-[134px]');
  });
});

describe('LibraryGameCard miniboard size below lg', () => {
  const origMatchMedia = window.matchMedia;
  const origInnerWidth = window.innerWidth;

  afterEach(() => {
    window.matchMedia = origMatchMedia;
    Object.defineProperty(window, 'innerWidth', { value: origInnerWidth, configurable: true });
  });

  /** Board size in the body below lg (the first of the two bodies) at this viewport width. */
  function boardSizeAt(width: number, game: GameFlawCard): number {
    Object.defineProperty(window, 'innerWidth', { value: width, configurable: true });
    window.matchMedia = vi.fn().mockImplementation((query: string) => {
      const minWidth = /min-width:\s*(\d+)px/.exec(query)?.[1];
      return {
        matches: minWidth !== undefined && width >= Number(minWidth),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      };
    }) as unknown as typeof window.matchMedia;
    renderCard(<LibraryGameCard game={game} />);
    return Number(screen.getAllByTestId('stub-mini-board')[0]!.dataset.size);
  }

  const RESULT_FEN = '8/8/8/8/8/8/8/8';
  const analyzed = (): GameFlawCard => ({ ...makeGame([]), result_fen: RESULT_FEN });
  const unanalyzed = (): GameFlawCard => ({
    ...analyzed(),
    analysis_state: 'no_engine_analysis',
    eval_series: null,
    flaw_markers: null,
    phase_transitions: null,
  });

  it.each([
    ['half the screen on phones', 475, 238],
    ['two columns on the zoomed inner screen', 616, 232],
    ['two columns on the inner screen', 704, 304],
  ])('analyzed: %s', (_name, width, expected) => {
    expect(boardSizeAt(width, analyzed())).toBe(expected);
  });

  it.each([616, 704])('unanalyzed at %dpx: no second column, so the small board', (width) => {
    expect(boardSizeAt(width, unanalyzed())).toBe(130);
  });
});

describe('LibraryGameCard MoveStats filter ring is user-scoped', () => {
  // user_color 'white'. ply 2 (even) = user blunder; ply 3 (odd) = opponent blunder.
  function twoSidedBlunderGame(): GameFlawCard {
    return makeGame([
      marker({ ply: 2, severity: 'blunder', is_user: true }),
      marker({ ply: 3, severity: 'blunder', is_user: false }),
    ]);
  }
  const RING_CLASS_FRAGMENT = 'ring-2';

  it('rings only the player-side (white) blunder cell when the severity filter narrows to blunder', () => {
    filterStore.filter = { ...defaultTestFilter(), severity: ['blunder'] };
    renderCard(<LibraryGameCard game={twoSidedBlunderGame()} />);
    const userCell = screen.getAllByTestId(`move-stats-cell-blunder-white-${GAME_ID}`)[0]!;
    const opponentCell = screen.getAllByTestId(`move-stats-cell-blunder-black-${GAME_ID}`)[0]!;
    expect(userCell.className).toContain(RING_CLASS_FRAGMENT);
    // The opponent cell is never ringed by the global (user-scoped) filter...
    expect(opponentCell.className).not.toContain(RING_CLASS_FRAGMENT);
    // ...but stays independently clickable for cycling.
    expect(opponentCell.tagName).toBe('BUTTON');
  });

  it('rings no cell when the severity filter is at its default (no tag selected)', () => {
    renderCard(<LibraryGameCard game={twoSidedBlunderGame()} />);
    const userCell = screen.getAllByTestId(`move-stats-cell-blunder-white-${GAME_ID}`)[0]!;
    expect(userCell.className).not.toContain(RING_CLASS_FRAGMENT);
  });
});

describe('LibraryGameCard MoveStats filter ring marks each selected tag (D-20, D-28)', () => {
  const RING_CLASS_FRAGMENT = 'ring-2';
  const PCT_SCALE = 100;
  const ABOVE_CUT = (FACEPALM_HIGH_CUTOFF + 1) / PCT_SCALE;
  // user_color 'white': even plies are the user's, odd plies the opponent's. Every
  // category has a non-zero cell on BOTH sides so each one renders as a button.
  function bothSidesGame(): GameFlawCard {
    return {
      ...makeGame([
        marker({ ply: 2, severity: 'blunder', is_user: true, facepalm_score: ABOVE_CUT }),
        marker({ ply: 4, severity: 'blunder', is_user: true, facepalm_score: null }),
        marker({ ply: 6, severity: 'mistake', is_user: true }),
        marker({ ply: 3, severity: 'blunder', is_user: false, facepalm_score: ABOVE_CUT }),
        marker({ ply: 5, severity: 'blunder', is_user: false, facepalm_score: null }),
        marker({ ply: 7, severity: 'mistake', is_user: false }),
      ]),
      eval_series: [
        { ply: 0, es: 0.5, eval_cp: 0, eval_mate: null, best_move_tier: 'gem', maia_prob: 0.1 },
        { ply: 1, es: 0.5, eval_cp: 0, eval_mate: null, best_move_tier: 'gem', maia_prob: 0.1 },
        { ply: 8, es: 0.5, eval_cp: 0, eval_mate: null, best_move_tier: 'great', maia_prob: 0.3 },
        { ply: 9, es: 0.5, eval_cp: 0, eval_mate: null, best_move_tier: 'great', maia_prob: 0.3 },
      ],
    };
  }
  const CATEGORIES = ['facepalm', 'blunder', 'mistake', 'gem', 'great'] as const;
  const cell = (category: string, side: 'white' | 'black'): HTMLElement =>
    screen.getAllByTestId(`move-stats-cell-${category}-${side}-${GAME_ID}`)[0]!;
  const ringed = (side: 'white' | 'black'): string[] =>
    CATEGORIES.filter((c) => cell(c, side).className.includes(RING_CLASS_FRAGMENT));

  function render(filter: Partial<ReturnType<typeof defaultTestFilter>>): void {
    filterStore.filter = { ...defaultTestFilter(), ...filter };
    renderCard(<LibraryGameCard game={bothSidesGame()} />);
  }

  it('rings only the facepalm cell for a facepalm selection', () => {
    render({ severity: ['facepalm'] });
    expect(ringed('white')).toEqual(['facepalm']);
    expect(ringed('black')).toEqual([]);
  });

  it('rings several cells for several selected tags', () => {
    render({ severity: ['blunder', 'facepalm'] });
    expect(ringed('white')).toEqual(['facepalm', 'blunder']);
    expect(ringed('black')).toEqual([]);
  });

  it('rings the mistake cell for a mistake selection', () => {
    render({ severity: ['mistake'] });
    expect(ringed('white')).toEqual(['mistake']);
  });

  it('rings nothing for no tag and for all three tags', () => {
    render({ severity: [] });
    expect(ringed('white')).toEqual([]);
    cleanup();
    render({ severity: ['facepalm', 'blunder', 'mistake'] });
    expect(ringed('white')).toEqual([]);
    expect(ringed('black')).toEqual([]);
  });

  it('has gem rings only the user Gem cell', () => {
    render({ hasGem: true });
    expect(ringed('white')).toEqual(['gem']);
    expect(ringed('black')).toEqual([]);
  });

  it('has great rings only the user Great cell', () => {
    render({ hasGreat: true });
    expect(ringed('white')).toEqual(['great']);
    expect(ringed('black')).toEqual([]);
  });

  it('has gem and has great ring both cells', () => {
    render({ hasGem: true, hasGreat: true });
    expect(ringed('white')).toEqual(['gem', 'great']);
    expect(ringed('black')).toEqual([]);
  });

  it('has gem with all three Flaws tags rings the Gem cell and no severity cell', () => {
    render({ hasGem: true, severity: ['facepalm', 'blunder', 'mistake'] });
    expect(ringed('white')).toEqual(['gem']);
  });

  it('a Flaws tag and has gem ring independently', () => {
    render({ hasGem: true, severity: ['mistake'] });
    expect(ringed('white')).toEqual(['mistake', 'gem']);
  });

  it('the mobile compact cells of the ringed categories carry the ring too', () => {
    render({ severity: ['facepalm'], hasGreat: true });
    const compact = (category: string): HTMLElement =>
      screen.getAllByTestId(`move-stats-compact-cell-${category}-${GAME_ID}`)[0]!;
    expect(compact('facepalm').className).toContain(RING_CLASS_FRAGMENT);
    expect(compact('great').className).toContain(RING_CLASS_FRAGMENT);
    expect(compact('blunder').className).not.toContain(RING_CLASS_FRAGMENT);
    expect(compact('gem').className).not.toContain(RING_CLASS_FRAGMENT);
  });
});

describe('LibraryGameCard mobile MoveStats collapse and unanalyzed pill', () => {
  it('collapsed default shows the accuracy strip + the compact summary row + the chevron toggle; expand reveals the 8-row table', () => {
    const game: GameFlawCard = {
      ...makeGame([marker({ ply: 2, severity: 'blunder', is_user: true })]),
      white_accuracy: 88,
    };
    renderCard(<LibraryGameCard game={game} />);
    // Accuracy strip always renders.
    expect(screen.getAllByTestId(`move-stats-accuracy-white-${GAME_ID}`).length).toBeGreaterThan(0);
    // Collapsed (mobile): the compact 7-column summary row renders, including a
    // per-category cell (replaces the old severity-badge row).
    expect(screen.getAllByTestId(`move-stats-compact-${GAME_ID}`).length).toBeGreaterThan(0);
    expect(screen.getAllByTestId(`move-stats-compact-cell-blunder-${GAME_ID}`).length).toBeGreaterThan(0);
    expect(screen.getAllByTestId(`move-stats-compact-cell-facepalm-${GAME_ID}`).length).toBeGreaterThan(0);
    // D-05: the compact row omits Good and Inaccuracy.
    expect(screen.queryAllByTestId(`move-stats-compact-cell-inaccuracy-${GAME_ID}`)).toHaveLength(0);
    expect(screen.queryAllByTestId(`move-stats-compact-cell-good-${GAME_ID}`)).toHaveLength(0);
    // The card (with its accuracy header) stays visible; only the 8-row table is
    // hidden (native `hidden`) while collapsed.
    expect((screen.getAllByTestId(`move-stats-table-card-${GAME_ID}`)[0] as HTMLElement).hidden).toBe(false);
    const tableCard = screen.getAllByTestId(`move-stats-table-${GAME_ID}`)[0]!;
    expect((tableCard as HTMLElement).hidden).toBe(true);

    const toggle = screen.getAllByTestId(`move-stats-expand-toggle-${GAME_ID}`)[0]!;
    fireEvent.click(toggle);
    const tableCardAfter = screen.getAllByTestId(`move-stats-table-${GAME_ID}`)[0]!;
    expect((tableCardAfter as HTMLElement).hidden).toBe(false);
  });

  it('an unanalyzed game shows only the analyze pill — no MoveStats strip or table', () => {
    const game: GameFlawCard = {
      ...makeGame([]),
      analysis_state: 'no_engine_analysis',
      severity_counts: null,
      eval_series: null,
      flaw_markers: null,
      phase_transitions: null,
      moves: null,
    };
    renderCard(<LibraryGameCard game={game} />);
    expect(screen.queryAllByTestId(`move-stats-${GAME_ID}`)).toHaveLength(0);
    expect(screen.queryAllByTestId(`move-stats-expand-toggle-${GAME_ID}`)).toHaveLength(0);
  });
});

describe('LibraryGameCard miniboard corner tier badge (both players)', () => {
  // The scrubbed-miniboard corner badge shows BOTH players' tiers, mirroring the
  // flaw corner dots (opponent blunders/mistakes/inaccuracies already render). This
  // differs from the gem/great COUNT badges above, which stay user-scoped.
  // 5 replayable moves → perPly spans plies 0-4. user_color 'white' → even plies are
  // the user, odd are the opponent. Seed: user gem@0, OPPONENT great@1, user best@2,
  // OPPONENT good@3.
  function bothPlayersTierGame(): GameFlawCard {
    return {
      ...makeGame([]),
      moves: ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5'],
      eval_series: [
        { ply: 0, es: 0.5, eval_cp: 0, eval_mate: null, best_move_tier: 'gem', maia_prob: 0.1 },
        { ply: 1, es: 0.52, eval_cp: 10, eval_mate: null, best_move_tier: 'great', maia_prob: 0.3 },
        { ply: 2, es: 0.54, eval_cp: 15, eval_mate: null, best_move_tier: 'best', maia_prob: null },
        { ply: 3, es: 0.56, eval_cp: 20, eval_mate: null, best_move_tier: 'good', maia_prob: null },
        { ply: 4, es: 0.58, eval_cp: 25, eval_mate: null, best_move_tier: null, maia_prob: null },
      ],
    };
  }

  function scrubTo(ply: number): void {
    scrubCtl.ply = ply;
    fireEvent.click(screen.getAllByTestId('stub-eval-chart')[0]!);
  }

  it("renders the OPPONENT's great corner badge when scrubbed to an opponent (odd) ply", () => {
    renderCard(<LibraryGameCard game={bothPlayersTierGame()} />);
    scrubTo(1);
    expect(screen.getAllByTestId('mini-board-marker-great').length).toBeGreaterThan(0);
  });

  it("renders the OPPONENT's good corner badge when scrubbed to an opponent (odd) ply", () => {
    renderCard(<LibraryGameCard game={bothPlayersTierGame()} />);
    scrubTo(3);
    expect(screen.getAllByTestId('mini-board-marker-good').length).toBeGreaterThan(0);
  });

  it("still renders the USER's own best corner badge (even ply)", () => {
    renderCard(<LibraryGameCard game={bothPlayersTierGame()} />);
    scrubTo(2);
    expect(screen.getAllByTestId('mini-board-marker-best').length).toBeGreaterThan(0);
  });
});

describe('LibraryGameCard feature-event tracking', () => {
  const track = vi.fn();

  beforeEach(() => {
    track.mockClear();
    window.umami = { track, identify: vi.fn() };
    window.history.pushState({}, '', '/library/games');
  });

  afterEach(() => {
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  /** The game id must never leave the browser. */
  function expectNoGameId() {
    expect(JSON.stringify(track.mock.calls)).not.toContain(String(GAME_ID));
  }

  it('sends nothing on render', () => {
    renderCard(<LibraryGameCard game={makeGame([])} />);
    expect(track).not.toHaveBeenCalled();
  });

  it('clicking Analyze sends one id-free action analyze', () => {
    renderCard(<LibraryGameCard game={makeGame([])} />);
    fireEvent.click(screen.getAllByTestId('btn-library-game-analyze')[0]!);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('action', { page: 'library', target: 'analyze' });
    expectNoGameId();
  });

  it('activating a tag chip sends one id-free action chip-cycle', () => {
    renderCard(
      <LibraryGameCard
        game={makeGame([marker({ ply: 2, allowed_tactic_motif: 'fork', allowed_tactic_confidence: 90 })])}
      />,
    );
    fireEvent.click(screen.getAllByTestId(`chip-tactic-allowed-fork-${GAME_ID}`)[0]!);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('action', { page: 'library', target: 'chip-cycle' });
    expectNoGameId();
    expect(JSON.stringify(track.mock.calls)).not.toContain('fork');
  });

  it('expanding the mobile move stats sends panel-open move-stats-expand once, collapsing sends nothing', () => {
    const game: GameFlawCard = {
      ...makeGame([marker({ ply: 2, severity: 'blunder', is_user: true })]),
      white_accuracy: 88,
    };
    renderCard(<LibraryGameCard game={game} />);
    const toggle = screen.getAllByTestId(`move-stats-expand-toggle-${GAME_ID}`)[0]!;
    fireEvent.click(toggle);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('panel-open', { page: 'library', target: 'move-stats-expand' });
    fireEvent.click(toggle);
    expect(track).toHaveBeenCalledTimes(1);
    expectNoGameId();
  });
});
