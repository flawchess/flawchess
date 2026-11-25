// @vitest-environment jsdom
/**
 * FlawCard vitest suite.
 *
 * Tests:
 * 1. Opponent name and rating (not the user's)
 * 2. Ratings in parentheses; omitted (no empty parens) when null
 * 3. Move notation: ply=2 (white) → "2. Nxd4", ply=3 (black) → "2... c5"
 * 4. One layout: board size from the card width, tags beside the board
 * 5. data-testid on root article: flaw-card-{game_id}-{ply}
 * 6. Platform link testid and aria-label present
 * 7. Unified Analyze button (btn-flaw-analyze) replaces Explore + Game pair
 *
 * There is no "View game" button or modal path.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import {
  FACEPALM_HIGH_CUTOFF,
  FACEPALM_TYPE_SENTENCE,
  facepalmScoreMeaning,
  toFacepalmPct,
} from '@/lib/facepalm';

// Stub Tooltip so tests don't need a TooltipProvider wrapper.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => children,
}));

// Mock useTacticLines — TacticMotifChip (rendered via FlawCard tagsRow) calls useTacticLines.
vi.mock('@/hooks/useLibrary', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/useLibrary')>('@/hooks/useLibrary');
  return {
    ...actual,
    useTacticLines: vi.fn().mockReturnValue({ isLoading: false, isError: false, data: undefined }),
  };
});

// Mock react-chessboard to avoid SVG/canvas rendering in test environment
vi.mock('react-chessboard', () => ({
  Chessboard: vi.fn(() => null),
}));


// Mock useEnqueueGame — NoAnalysisState (rendered via LibraryGameCard) uses tier-1 mutation.
vi.mock('@/hooks/useEnqueueGame', () => ({
  useTier1Enqueue: () => ({ mutate: vi.fn(), isPending: false }),
}));

// Mock react-router navigate — NoAnalysisState uses useNavigate for guest CTA.
// Link is rendered without a Router context here (FlawCard's Explore button uses
// <Button asChild><Link>), so stub it as a plain anchor to avoid the router context.
vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    Link: ({ to, children, ...props }: { to: string; children: ReactNode }) => (
      <a href={typeof to === 'string' ? to : ''} {...props}>
        {children}
      </a>
    ),
  };
});

import { FlawCard } from '../FlawCard';
import { flawBoardSize } from '@/hooks/useFlawBoardSize';
import { TAG_DEFINITIONS } from '@/lib/tagDefinitions';
import { tacticMotifDefinition } from '@/lib/tacticComparisonMeta';
import type { FlawListItem } from '@/types/library';
import { BEST_MOVE_ARROW } from '@/lib/theme';

// ── jsdom stubs ───────────────────────────────────────────────────────────────

// Stub ResizeObserver — ChessBoard uses it for container-width tracking;
// jsdom doesn't implement it. TacticLineExplorer renders ChessBoard.
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal('ResizeObserver', MockResizeObserver);

// Stub IntersectionObserver as a class (jsdom doesn't have it) — LazyMiniBoard uses it.
// Fire isIntersecting=true immediately so the board renders in tests.
class MockIntersectionObserver {
  private callback: (entries: { isIntersecting: boolean }[]) => void;
  observe = vi.fn().mockImplementation(() => {
    this.callback([{ isIntersecting: true }]);
  });
  unobserve = vi.fn();
  disconnect = vi.fn();
  constructor(callback: (entries: { isIntersecting: boolean }[]) => void) {
    this.callback = callback;
  }
}
vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

beforeAll(() => {

  // TagChip uses window.matchMedia (desktop: matches=false)
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

// ── Mock dependencies ─────────────────────────────────────────────────────────

vi.mock('@/hooks/useFlawFilterStore', () => ({
  useFlawFilterStore: () => [{ severity: [], tags: [] }, vi.fn()] as const,
}));

// ── Test data factory ─────────────────────────────────────────────────────────

function makeFlaw(overrides: Partial<FlawListItem> = {}): FlawListItem {
  return {
    game_id: 42,
    ply: 2,
    fen: 'rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR',
    move_san: 'Nxd4',
    severity: 'blunder',
    tags: ['miss'],
    eval_cp_before: 470,
    eval_mate_before: null,
    eval_cp_after: -120,
    eval_mate_after: null,
    white_rating: 1850,
    black_rating: 1720,
    user_result: 'loss',
    played_at: '2026-01-15T10:00:00Z',
    time_control_bucket: 'rapid',
    time_control_str: '600+5',
    ply_count: 84,
    termination: 'resignation',
    platform: 'lichess',
    platform_url: 'https://lichess.org/abcd1234',
    white_username: 'Alice',
    black_username: 'Bob',
    user_color: 'white',
    clock_seconds: 125,
    move_seconds: 8.4,
    best_move: null,
    facepalm_score: null,
    facepalm_type: null,
    // Tactic motif fields — null by default
    allowed_tactic_motif: null,
    allowed_tactic_confidence: null,
    allowed_tactic_depth: null,
    missed_tactic_motif: null,
    missed_tactic_confidence: null,
    missed_tactic_depth: null,
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('FlawCard', () => {
  describe('Opponent row', () => {
    it('renders "vs <opponent>" — the opponent name only, not the user', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const article = screen.getByTestId('flaw-card-42-2');
      // User is white → opponent is Bob; the user's own name must not appear
      // in the header text (it remains in the View-game aria-label only).
      expect(article.textContent).toContain('vs');
      expect(article.textContent).toContain('Bob');
      expect(article.textContent).not.toContain('Alice');
    });

    it('renders the opponent rating in parentheses, not the user rating', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).toContain('(1720)');
      expect(article.textContent).not.toContain('(1850)');
    });

    it('shows the white player when the user played black', () => {
      render(<FlawCard flaw={makeFlaw({ user_color: 'black' })} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).toContain('Alice');
      expect(article.textContent).toContain('(1850)');
      expect(article.textContent).not.toContain('Bob');
    });

    it('omits parentheses when white_rating is null (no empty parens)', () => {
      render(<FlawCard flaw={makeFlaw({ white_rating: null })} />);
      const article = screen.getByTestId('flaw-card-42-2');
      // Should have Bob's rating but no "()" without a number
      expect(article.textContent).not.toMatch(/\(\s*\)/);
    });

    it('omits parentheses when black_rating is null', () => {
      render(<FlawCard flaw={makeFlaw({ black_rating: null })} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).not.toMatch(/\(\s*\)/);
    });
  });

  describe('Move notation', () => {
    it('renders white move notation: ply=2 → "2. Nxd4"', () => {
      render(<FlawCard flaw={makeFlaw({ ply: 2, move_san: 'Nxd4' })} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).toContain('2. Nxd4');
    });

    it('renders black move notation: ply=3 → "2... c5"', () => {
      render(<FlawCard flaw={makeFlaw({ ply: 3, move_san: 'c5', game_id: 43 })} />);
      const article = screen.getByTestId('flaw-card-43-3');
      expect(article.textContent).toContain('2... c5');
    });

    it('falls back to "Ply N" when move_san is null', () => {
      render(<FlawCard flaw={makeFlaw({ ply: 4, move_san: null })} />);
      const article = screen.getByTestId('flaw-card-42-4');
      expect(article.textContent).toContain('Ply 4');
    });
  });

  describe('Game-info block (clock + move time, no TC/moves/termination)', () => {
    it('renders "mm:ss · Ns" and drops TC, move count, and termination', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const article = screen.getByTestId('flaw-card-42-2');
      // clock_seconds=125 → "2:05"; move_seconds=8.4 → "8.4s"
      expect(article.textContent).toContain('2:05 · 8.4s');
      // Replaced segments must be gone.
      expect(article.textContent).not.toContain('rapid');
      expect(article.textContent).not.toContain('10+5');
      expect(article.textContent).not.toContain('Moves');
      expect(article.textContent).not.toContain('resignation');
    });

    it('shows long move times in whole seconds', () => {
      render(<FlawCard flaw={makeFlaw({ move_seconds: 62 })} />);
      expect(screen.getByTestId('flaw-card-42-2').textContent).toContain('2:05 · 62s');
    });

    it('omits the move time when move_seconds is null', () => {
      render(<FlawCard flaw={makeFlaw({ move_seconds: null })} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).toContain('2:05');
      expect(article.textContent).not.toContain('8.4s');
    });

    it('omits the clock line entirely when both clock fields are null', () => {
      render(<FlawCard flaw={makeFlaw({ clock_seconds: null, move_seconds: null })} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).not.toContain('2:05');
      expect(article.textContent).not.toContain('8.4s');
    });
  });

  describe('one layout at every width', () => {
    it('sizes the board from the card width, in steps of 8px within its limits', () => {
      expect(flawBoardSize(0)).toBe(152); // unknown width (first render)
      expect(flawBoardSize(293)).toBe(160); // narrowest grid card (321px)
      expect(flawBoardSize(400)).toBe(216);
      expect(flawBoardSize(700)).toBe(216);
    });

    it('renders one board, one Analyze button and one copy of the tags', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      expect(document.querySelectorAll('[style*="width: 152px"]').length).toBeGreaterThan(0);
      expect(screen.getAllByTestId('btn-flaw-analyze')).toHaveLength(1);
      expect(screen.getAllByTestId('flaw-card-tags')).toHaveLength(1);
    });

    it('puts the tags beside the board and Analyze in a row of its own below', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const tags = screen.getByTestId('flaw-card-tags');
      const boardRow = document.querySelector('[style*="width: 152px"]')!.parentElement!;
      const analyze = screen.getByTestId('btn-flaw-analyze');
      expect(boardRow.contains(tags)).toBe(true);
      expect(boardRow.contains(analyze)).toBe(false);
      expect(boardRow.nextElementSibling).toBe(analyze);
    });
  });

  describe('tags', () => {
    it('shows every tag as a chip, timing and phase last', () => {
      render(<FlawCard flaw={makeFlaw({ tags: ['unrushed', 'opening', 'lucky'] })} />);
      expect(screen.getByTestId('flaw-card-tags').textContent).toBe('luckyunrushedopening');
      for (const tag of ['lucky', 'unrushed', 'opening']) {
        expect(screen.getByTestId(`chip-${tag}-42`)).toBeDefined();
      }
    });

    it('shows no eval swing', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      expect(screen.getByTestId('flaw-card-42-2').textContent).not.toContain('+4.7');
    });

    it('explains a tag on tap', () => {
      render(<FlawCard flaw={makeFlaw({ tags: ['unrushed'] })} />);
      fireEvent.click(screen.getByTestId('flaw-tag-unrushed-42-2'));
      expect(screen.getByTestId('flaw-tag-unrushed-42-2-popover').textContent).toContain(
        TAG_DEFINITIONS.unrushed,
      );
    });

    it('shows the full tactic label and explains it on tap', () => {
      render(<FlawCard flaw={makeFlaw({ allowed_tactic_motif: 'hanging-piece' })} />);
      const trigger = screen.getByTestId('flaw-tactic-allowed-42-2');
      expect(trigger.textContent).toBe('allowed: hanging-piece');
      fireEvent.click(trigger);
      expect(screen.getByTestId('flaw-tactic-allowed-42-2-popover').textContent).toContain(
        tacticMotifDefinition('hanging-piece'),
      );
    });

    it('is absent without tags and tactics', () => {
      render(<FlawCard flaw={makeFlaw({ tags: [] })} />);
      expect(screen.queryByTestId('flaw-card-tags')).toBeNull();
    });
  });

  describe('Best-move arrow', () => {
    it('draws a blue best-move arrow when best_move (UCI) is set', () => {
      render(<FlawCard flaw={makeFlaw({ best_move: 'g1f3' })} />);
      const overlay = document.querySelector('[data-testid="mini-board-arrow-overlay"]');
      expect(overlay).not.toBeNull();
      const bluePaths = overlay!.querySelectorAll(`path[fill="${BEST_MOVE_ARROW}"]`);
      expect(bluePaths.length).toBe(1);
    });

    it('draws no best-move arrow when best_move is null', () => {
      // fixture fen has no legal "Nxd4", so the flaw-move arrow is absent too →
      // the overlay should render zero arrows (it returns null when empty).
      render(<FlawCard flaw={makeFlaw({ best_move: null })} />);
      const overlay = document.querySelector('[data-testid="mini-board-arrow-overlay"]');
      const bluePaths = overlay?.querySelectorAll(`path[fill="${BEST_MOVE_ARROW}"]`) ?? [];
      expect(bluePaths.length).toBe(0);
    });
  });

  describe('Tactic-depth badge', () => {
    it('renders the missed-tactic depth (1-based) on the blue best-move arrow', () => {
      // missed_tactic_depth 4 (0-based) → display "5" at the best-move arrow. The motif is
      // set too: the detector always writes motif + depth together, and the depth badge is
      // family-guarded, so a depth never renders without its motif/chip.
      render(
        <FlawCard
          flaw={makeFlaw({ best_move: 'g1f3', missed_tactic_motif: 'fork', missed_tactic_depth: 4 })}
        />,
      );
      const overlay = document.querySelector('[data-testid="mini-board-arrow-overlay"]');
      expect(overlay).not.toBeNull();
      const labels = Array.from(overlay!.querySelectorAll('text')).map((t) => t.textContent);
      expect(labels).toContain('5');
    });

    it('renders no depth badge when the tactic depth is null', () => {
      render(<FlawCard flaw={makeFlaw({ best_move: 'g1f3', missed_tactic_depth: null })} />);
      const overlay = document.querySelector('[data-testid="mini-board-arrow-overlay"]');
      expect(overlay!.querySelectorAll('text').length).toBe(0);
    });
  });

  describe('data-testid (CLAUDE.md browser-automation rules)', () => {
    it('root article has data-testid="flaw-card-{game_id}-{ply}"', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      expect(screen.getByTestId('flaw-card-42-2')).toBeDefined();
    });

    it('platform link has testid and aria-label', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const link = screen.getByTestId('flaw-card-platform-link-42-2');
      expect(link).toBeDefined();
      expect(link.getAttribute('aria-label')).toBe('Open at this move on platform');
    });
  });

  describe('unified Analyze button (btn-flaw-analyze)', () => {
    // A single Analyze button (no Game modal) opens
    // /analysis?game_id=X&ply=Y.

    it('renders btn-flaw-analyze with aria-label "Analyze game"', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const btns = screen.getAllByTestId('btn-flaw-analyze');
      expect(btns.length).toBeGreaterThan(0);
      expect(btns[0]!.getAttribute('aria-label')).toBe('Analyze game');
    });

    it('btn-flaw-analyze href is /analysis?game_id=42&ply=2', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const btns = screen.getAllByTestId('btn-flaw-analyze');
      // Link renders as <a> via the react-router stub
      expect(btns[0]!.getAttribute('href')).toBe('/analysis?game_id=42&ply=2');
    });

    it('no flaw-btn-explore or flaw-btn-game buttons remain', () => {
      render(<FlawCard flaw={makeFlaw({ missed_tactic_motif: 'fork', missed_tactic_confidence: 90 })} />);
      expect(screen.queryAllByTestId('flaw-btn-explore')).toHaveLength(0);
      expect(screen.queryAllByTestId('flaw-btn-game')).toHaveLength(0);
    });

    it('no flaw-game-modal in DOM (Game modal deleted)', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      expect(screen.queryByTestId('flaw-game-modal')).toBeNull();
    });
  });

  describe('orientation-prefixed dual-chip matrix', () => {
    const BOTH_MOTIFS = {
      missed_tactic_motif: 'fork',
      missed_tactic_confidence: 90,
      allowed_tactic_motif: 'pin',
      allowed_tactic_confidence: 85,
    };
    const MISSED_ONLY = {
      missed_tactic_motif: 'fork',
      missed_tactic_confidence: 90,
      allowed_tactic_motif: null,
      allowed_tactic_confidence: null,
    };
    const ALLOWED_ONLY = {
      missed_tactic_motif: null,
      missed_tactic_confidence: null,
      allowed_tactic_motif: 'pin',
      allowed_tactic_confidence: 85,
    };

    it('Either + both motifs: renders missed chip AND allowed chip', () => {
      render(
        <FlawCard flaw={makeFlaw(BOTH_MOTIFS)} tacticOrientation="either" />,
      );
      // missed chip: chip-tactic-missed-fork-42
      expect(screen.getAllByTestId('chip-tactic-missed-fork-42').length).toBeGreaterThan(0);
      // allowed chip: chip-tactic-allowed-pin-42
      expect(screen.getAllByTestId('chip-tactic-allowed-pin-42').length).toBeGreaterThan(0);
    });

    it('Either + missed only: renders missed chip only', () => {
      render(
        <FlawCard flaw={makeFlaw(MISSED_ONLY)} tacticOrientation="either" />,
      );
      expect(screen.getAllByTestId('chip-tactic-missed-fork-42').length).toBeGreaterThan(0);
      // No allowed chip (null allowed_tactic_motif)
      expect(screen.queryAllByTestId('chip-tactic-allowed-pin-42')).toHaveLength(0);
    });

    it('Either + allowed only: renders allowed chip only', () => {
      render(
        <FlawCard flaw={makeFlaw(ALLOWED_ONLY)} tacticOrientation="either" />,
      );
      expect(screen.getAllByTestId('chip-tactic-allowed-pin-42').length).toBeGreaterThan(0);
      // No missed chip
      expect(screen.queryAllByTestId('chip-tactic-missed-fork-42')).toHaveLength(0);
    });

    it('Missed filter + both motifs: renders missed chip only', () => {
      render(
        <FlawCard flaw={makeFlaw(BOTH_MOTIFS)} tacticOrientation="missed" />,
      );
      expect(screen.getAllByTestId('chip-tactic-missed-fork-42').length).toBeGreaterThan(0);
      // allowed chip suppressed
      expect(screen.queryAllByTestId('chip-tactic-allowed-pin-42')).toHaveLength(0);
    });

    it('Missed filter + missed only: renders missed chip', () => {
      render(
        <FlawCard flaw={makeFlaw(MISSED_ONLY)} tacticOrientation="missed" />,
      );
      expect(screen.getAllByTestId('chip-tactic-missed-fork-42').length).toBeGreaterThan(0);
    });

    it('Missed filter + allowed only (missed is null): renders no chip', () => {
      render(
        <FlawCard flaw={makeFlaw(ALLOWED_ONLY)} tacticOrientation="missed" />,
      );
      expect(screen.queryAllByTestId(/chip-tactic-/)).toHaveLength(0);
    });

    it('Allowed filter + both motifs: renders allowed chip only', () => {
      render(
        <FlawCard flaw={makeFlaw(BOTH_MOTIFS)} tacticOrientation="allowed" />,
      );
      expect(screen.getAllByTestId('chip-tactic-allowed-pin-42').length).toBeGreaterThan(0);
      // missed chip suppressed
      expect(screen.queryAllByTestId('chip-tactic-missed-fork-42')).toHaveLength(0);
    });

    it('Allowed filter + allowed only: renders allowed chip', () => {
      render(
        <FlawCard flaw={makeFlaw(ALLOWED_ONLY)} tacticOrientation="allowed" />,
      );
      expect(screen.getAllByTestId('chip-tactic-allowed-pin-42').length).toBeGreaterThan(0);
    });

    it('popovers stay closed until a chip is used', () => {
      const { container } = render(
        <FlawCard flaw={makeFlaw(BOTH_MOTIFS)} tacticOrientation="either" />,
      );
      // No Radix dialog in the chip row
      expect(container.querySelector('[role="dialog"]')).toBeNull();
    });
  });

  // Scores derived from the cut, never a literal (D-21).
  const PCT_SCALE = 100;
  const ABOVE_CUT_SCORE = (FACEPALM_HIGH_CUTOFF + 20) / PCT_SCALE;
  const BELOW_CUT_SCORE = (FACEPALM_HIGH_CUTOFF - 10) / PCT_SCALE;
  const TRIGGER_TESTID = 'facepalm-badge-7-24';

  function scoredBlunder(score: number, type: 'missed_win' | 'allowed_loss' | null = 'allowed_loss'): FlawListItem {
    return makeFlaw({ severity: 'blunder', facepalm_score: score, facepalm_type: type, game_id: 7, ply: 24 });
  }

  describe('One severity chip and the facepalm popover (260-G2)', () => {
    it('a facepalm blunder shows one "Facepalm" chip that is the popover trigger, with no score on its face', () => {
      render(<FlawCard flaw={scoredBlunder(ABOVE_CUT_SCORE)} />);
      const badge = screen.getAllByTestId('severity-blunder-7')[0] as HTMLElement;
      expect(badge.textContent).toBe('???Facepalm');
      const trigger = screen.getAllByTestId(TRIGGER_TESTID)[0] as HTMLElement;
      expect(trigger.contains(badge)).toBe(true);
      expect(trigger.textContent).not.toContain('%');
      expect(document.querySelector('svg.lucide-gauge')).toBeNull();
    });

    it('a blunder below the cut shows "Blunder" and still opens the popover', () => {
      render(<FlawCard flaw={scoredBlunder(BELOW_CUT_SCORE)} />);
      const badge = screen.getAllByTestId('severity-blunder-7')[0] as HTMLElement;
      expect(badge.textContent).toBe('??Blunder');
      const trigger = screen.getAllByTestId(TRIGGER_TESTID)[0] as HTMLElement;
      expect(trigger.contains(badge)).toBe(true);
      fireEvent.click(trigger);
      const popover = screen.getByTestId(`${TRIGGER_TESTID}-popover`);
      expect(popover.textContent).toContain(`Facepalm score ${toFacepalmPct(BELOW_CUT_SCORE)}%`);
      expect(screen.getByTestId('facepalm-explanation-blunder').textContent).toContain(
        `${FACEPALM_HIGH_CUTOFF}% or more counts as a facepalm blunder.`,
      );
    });

    it('opens the popover on a facepalm with the percent and the allowed-loss sentence', () => {
      render(<FlawCard flaw={scoredBlunder(ABOVE_CUT_SCORE)} />);
      const trigger = screen.getAllByTestId(TRIGGER_TESTID)[0] as HTMLElement;
      fireEvent.click(trigger);
      const popover = screen.getByTestId(`${TRIGGER_TESTID}-popover`);
      expect(popover.textContent).toContain(`Facepalm score ${toFacepalmPct(ABOVE_CUT_SCORE)}%`);
      expect(popover.textContent).toContain(
        `Allowed loss: ${FACEPALM_TYPE_SENTENCE.allowed_loss}`,
      );
      expect(popover.textContent).toContain(facepalmScoreMeaning());
      expect(trigger.getAttribute('aria-label')).toBe(
        `Facepalm blunder, facepalm score ${toFacepalmPct(ABOVE_CUT_SCORE)}%, allowed loss`,
      );
    });

    it('renders one trigger', () => {
      render(<FlawCard flaw={scoredBlunder(ABOVE_CUT_SCORE)} />);
      expect(screen.getAllByTestId(TRIGGER_TESTID)).toHaveLength(1);
    });

    it('an unscored blunder has no trigger and reads "Blunder"', () => {
      const { container } = render(
        <FlawCard flaw={makeFlaw({ severity: 'blunder', facepalm_score: null, game_id: 7, ply: 24 })} />,
      );
      expect(container.querySelectorAll('[data-testid^="facepalm-badge-"]')).toHaveLength(0);
      expect((screen.getAllByTestId('severity-blunder-7')[0] as HTMLElement).textContent).toBe('??Blunder');
    });

    it('a scored blunder without a type has no trigger (257 D-09) but is still labelled from the score', () => {
      const { container } = render(<FlawCard flaw={scoredBlunder(ABOVE_CUT_SCORE, null)} />);
      expect(container.querySelectorAll('[data-testid^="facepalm-badge-"]')).toHaveLength(0);
      expect((screen.getAllByTestId('severity-blunder-7')[0] as HTMLElement).textContent).toBe('???Facepalm');
    });

    it('a mistake with a score has no trigger and reads "Mistake" with the "?" glyph', () => {
      const { container } = render(
        <FlawCard flaw={makeFlaw({ severity: 'mistake', facepalm_score: 0.8, facepalm_type: 'allowed_loss', game_id: 7, ply: 24 })} />,
      );
      expect(container.querySelectorAll('[data-testid^="facepalm-badge-"]')).toHaveLength(0);
      const badge = screen.getAllByTestId('severity-mistake-7')[0] as HTMLElement;
      expect(badge.querySelector('svg text')?.textContent).toBe('?');
      expect(badge.textContent).toBe('?Mistake');
    });
  });
});
