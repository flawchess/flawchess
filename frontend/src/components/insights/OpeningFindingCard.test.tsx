// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';

// IntersectionObserver is not available in jsdom. Stub it as a class
// constructor that fires the callback synchronously on observe() so
// LazyMiniBoard mounts MiniBoard immediately and the arrow overlay renders
// without us having to mock LazyMiniBoard itself. (Quick task 260429-gmj —
// before this fix, `visible` stayed `false` and MiniBoard never mounted, so
// arrow-overlay assertions could not work.)
class MockIntersectionObserver {
  private cb: IntersectionObserverCallback;
  constructor(cb: IntersectionObserverCallback) {
    this.cb = cb;
  }
  observe = (el: Element) => {
    this.cb(
      [{ isIntersecting: true, target: el } as IntersectionObserverEntry],
      this as unknown as IntersectionObserver,
    );
  };
  disconnect = vi.fn();
  unobserve = vi.fn();
}
vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

// Mock react-chessboard to avoid SVG/canvas rendering in test environment
vi.mock('react-chessboard', () => ({
  Chessboard: vi.fn(() => null),
}));

// Stub the Tooltip primitive so renders don't need a TooltipProvider wrapper.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => children,
}));

// Phase 77: stub the curated data so tests are independent of the live trollOpenings.ts contents.
// Sentinel: starting position with white's e-pawn moved to e4 (post-1.e4) — derives to
//   "8/8/8/8/4P3/8/PPPP1PPP/RNBQKBNR" for white-side. Tests reference this key directly so
//   they don't depend on the actual curated set shipped in src/data/trollOpenings.ts.
vi.mock('@/data/trollOpenings', () => ({
  WHITE_TROLL_KEYS: new Set(['8/8/8/8/4P3/8/PPPP1PPP/RNBQKBNR']),
  BLACK_TROLL_KEYS: new Set<string>(),
}));
import type * as React from 'react';

import { OpeningFindingCard } from './OpeningFindingCard';
import type { OpeningInsightFinding } from '@/types/insights';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

function makeFinding(overrides: Partial<OpeningInsightFinding> = {}): OpeningInsightFinding {
  return {
    color: 'black',
    classification: 'weakness',
    severity: 'major',
    opening_name: 'Sicilian Defense: Najdorf',
    opening_eco: 'B90',
    display_name: 'Sicilian Defense: Najdorf',
    entry_fen: 'rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6',
    entry_san_sequence: ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6', 'Nc3', 'a6'],
    entry_full_hash: '111',
    candidate_move_san: 'Be2',
    resulting_full_hash: '222',
    n_games: 18,
    wins: 4,
    draws: 3,
    losses: 11,
    score: 0.30,            // gives clean "30%" prose
    confidence: 'medium',   // Phase 76 D-21
    p_value: 0.05,          // Phase 76 D-21
    ci_low: 0.25,
    ci_high: 0.35,
    ...overrides,
  };
}

function renderCard(props: {
  finding: OpeningInsightFinding;
  idx?: number;
  onFindingClick?: (f: OpeningInsightFinding) => void;
  onOpenGames?: (f: OpeningInsightFinding) => void;
}) {
  const { finding, idx = 0, onFindingClick = () => {}, onOpenGames = () => {} } = props;
  return render(
    <OpeningFindingCard
      finding={finding}
      idx={idx}
      onFindingClick={onFindingClick}
      onOpenGames={onOpenGames}
    />,
  );
}

// Phase 77: fixture FENs.
// TROLL_FIXTURE_FEN derives — for side='white' — to the key seeded in the
// vi.mock('@/data/trollOpenings') above, so it triggers the watermark.
const TROLL_FIXTURE_FEN =
  'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
const NON_TROLL_FIXTURE_FEN =
  'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

afterEach(() => {
  cleanup();
});

describe('OpeningFindingCard', () => {
  it('renders "You score X% as Black" prose for weakness section', () => {
    const finding = makeFinding({ classification: 'weakness', color: 'black', score: 0.30 });
    renderCard({ finding, idx: 0 });
    const card = screen.getByTestId('opening-finding-card-0');
    const text = card.textContent ?? '';
    // Both mobile + desktop branches render — text content includes both; check it contains the right pieces
    expect(text).toMatch(/You score/);
    expect(text).toMatch(/30%/);
    expect(text).toMatch(/Black/);
    expect(text).not.toMatch(/You lose/);
    expect(text).not.toMatch(/You win/);
  });

  it('renders "You score X% as White" prose for strength section', () => {
    const finding = makeFinding({ classification: 'strength', color: 'white', score: 0.58 });
    renderCard({ finding, idx: 1 });
    const card = screen.getByTestId('opening-finding-card-1');
    const text = card.textContent ?? '';
    expect(text).toMatch(/You score/);
    expect(text).toMatch(/58%/);
    expect(text).toMatch(/White/);
    expect(text).not.toMatch(/You lose/);
    expect(text).not.toMatch(/You win/);
  });

  it('does NOT render "lose" or "win" verbs in prose (Phase 76 D-02)', () => {
    const finding = makeFinding();
    renderCard({ finding, idx: 0 });
    const card = screen.getByTestId('opening-finding-card-0');
    const text = card.textContent ?? '';
    expect(text).not.toMatch(/You lose/);
    expect(text).not.toMatch(/You win/);
  });

  it('falls back to .toFixed(1) when rounded percent contradicts the section title', () => {
    // weakness with score = 0.499 would round to 50% (contradicts weakness label)
    const finding = makeFinding({ classification: 'weakness', score: 0.499 });
    renderCard({ finding, idx: 0 });
    const card = screen.getByTestId('opening-finding-card-0');
    const text = card.textContent ?? '';
    expect(text).toMatch(/49\.9%/);
    expect(text).not.toMatch(/\b50%/);
  });

  it('applies ZONE_DANGER (red) border-left when score <= 0.45', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'weakness', score: 0.30 })}
        idx={2}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-2');
    expect(normalizeColor(card.style.borderLeftColor)).toBe(normalizeColor(ZONE_DANGER));
  });

  it('applies ZONE_NEUTRAL (blue) border-left when score sits in the 45-55% band', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'weakness', score: 0.49 })}
        idx={3}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-3');
    expect(normalizeColor(card.style.borderLeftColor)).toBe(normalizeColor(ZONE_NEUTRAL));
  });

  it('applies ZONE_SUCCESS (green) border-left when score >= 0.55', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'strength', score: 0.60 })}
        idx={4}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-4');
    expect(normalizeColor(card.style.borderLeftColor)).toBe(normalizeColor(ZONE_SUCCESS));
  });

  it('Moves link calls onFindingClick with the finding', () => {
    const onFindingClick = vi.fn();
    const finding = makeFinding();
    render(
      <OpeningFindingCard
        finding={finding}
        idx={6}
        onFindingClick={onFindingClick}
        onOpenGames={() => {}}
      />,
    );
    // Two layouts (mobile + desktop) both render — query all matching test ids and click the first.
    const movesBtns = screen.getAllByTestId('opening-finding-card-6-moves');
    fireEvent.click(movesBtns[0]!);
    expect(onFindingClick).toHaveBeenCalledWith(finding);
  });

  it('Games link calls onOpenGames with the finding and shows the n_games count', () => {
    const onOpenGames = vi.fn();
    const finding = makeFinding({ n_games: 42 });
    render(
      <OpeningFindingCard
        finding={finding}
        idx={7}
        onFindingClick={() => {}}
        onOpenGames={onOpenGames}
      />,
    );
    const gamesBtns = screen.getAllByTestId('opening-finding-card-7-games');
    expect(gamesBtns[0]!.textContent).toMatch(/42/);
    expect(gamesBtns[0]!.textContent).toMatch(/Games/);
    fireEvent.click(gamesBtns[0]!);
    expect(onOpenGames).toHaveBeenCalledWith(finding);
  });

  it('clicking the card body itself does not trigger any callbacks (no whole-card deeplink)', () => {
    const onFindingClick = vi.fn();
    const onOpenGames = vi.fn();
    render(
      <OpeningFindingCard
        finding={makeFinding()}
        idx={8}
        onFindingClick={onFindingClick}
        onOpenGames={onOpenGames}
      />,
    );
    fireEvent.click(screen.getByTestId('opening-finding-card-8'));
    expect(onFindingClick).not.toHaveBeenCalled();
    expect(onOpenGames).not.toHaveBeenCalled();
  });

  it('renders the display_name + ECO in the header line', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ display_name: 'Caro-Kann Defense', opening_eco: 'B10' })}
        idx={9}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-9');
    expect(card.textContent).toContain('Caro-Kann Defense');
    expect(card.textContent).toContain('B10');
  });

  it('renders <unnamed line> sentinel as italic muted text (defensive)', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({
          opening_name: '<unnamed line>',
          display_name: '<unnamed line>',
        })}
        idx={10}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-10');
    const italicEl = card.querySelector('.italic');
    expect(italicEl).not.toBeNull();
    expect(italicEl?.textContent).toContain('<unnamed line>');
  });

  it('renders only the candidate move with PGN move-number notation in the prose', () => {
    const finding = makeFinding({
      entry_san_sequence: ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4'],
      candidate_move_san: 'Nxd4',
    });
    render(
      <OpeningFindingCard
        finding={finding}
        idx={11}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const text = screen.getByTestId('opening-finding-card-11').textContent ?? '';
    expect(text).toContain('4.Nxd4');
    // Earlier entry plys should no longer appear in the rendered prose.
    expect(text).not.toContain('3.d4 cxd4');
  });

  describe('Score bullet + confidence-info popover (260505 refactor)', () => {
    it('renders the score bullet chart with the popover info trigger to its right', () => {
      const finding = makeFinding({ confidence: 'medium' });
      renderCard({ finding, idx: 3 });
      // Both mobile + desktop branches render — same testids.
      const bullets = screen.getAllByTestId('opening-finding-card-3-score-bullet');
      expect(bullets.length).toBeGreaterThanOrEqual(1);
      // The bullet container holds the MiniBulletChart and the popover trigger.
      expect(bullets[0]!.querySelector('[data-testid="mini-bullet-chart"]')).not.toBeNull();
      expect(bullets[0]!.querySelector(
        '[data-testid="opening-finding-card-3-confidence-info"]',
      )).not.toBeNull();
    });

    it('renders the CI whisker on the bullet chart from finding.ci_low/ci_high', () => {
      const finding = makeFinding({ ci_low: 0.40, ci_high: 0.55 });
      renderCard({ finding, idx: 5 });
      const bullet = screen.getAllByTestId('opening-finding-card-5-score-bullet')[0]!;
      expect(bullet.querySelector('[data-testid="mini-bullet-whisker"]')).not.toBeNull();
    });

    it('does NOT render the legacy Confidence: <level> text line', () => {
      const finding = makeFinding({ confidence: 'medium' });
      renderCard({ finding, idx: 0 });
      const card = screen.getByTestId('opening-finding-card-0');
      expect(card.textContent ?? '').not.toMatch(/Confidence:/);
    });

    it('applies UNRELIABLE_OPACITY when finding.confidence === "low"', () => {
      const finding = makeFinding({ confidence: 'low', n_games: 100 });
      renderCard({ finding, idx: 0 });
      const card = screen.getByTestId('opening-finding-card-0');
      expect(card.getAttribute('style')).toMatch(/opacity:\s*0\.5/);
    });

    it('applies UNRELIABLE_OPACITY when finding.n_games < 10', () => {
      const finding = makeFinding({ confidence: 'high', n_games: 9 });
      renderCard({ finding, idx: 0 });
      const card = screen.getByTestId('opening-finding-card-0');
      expect(card.getAttribute('style')).toMatch(/opacity:\s*0\.5/);
    });

    it('does NOT apply UNRELIABLE_OPACITY when n_games >= 10 AND confidence !== "low"', () => {
      const finding = makeFinding({ confidence: 'high', n_games: 100 });
      renderCard({ finding, idx: 0 });
      const card = screen.getByTestId('opening-finding-card-0');
      expect(card.getAttribute('style') ?? '').not.toMatch(/opacity:\s*0\.5/);
    });
  });

  describe('Phase 77 — Troll-opening watermark', () => {
    it('renders the watermark img when entry_fen + color match the troll set', () => {
      const finding = makeFinding({ entry_fen: TROLL_FIXTURE_FEN, color: 'white' });
      renderCard({ finding, idx: 7 });
      const watermark = screen.getByTestId('opening-finding-card-7-troll-watermark');
      expect(watermark.tagName).toBe('IMG');
    });

    it('does not render the watermark when the position is not in the troll set', () => {
      const finding = makeFinding({ entry_fen: NON_TROLL_FIXTURE_FEN, color: 'white' });
      renderCard({ finding, idx: 7 });
      expect(screen.queryByTestId('opening-finding-card-7-troll-watermark')).toBeNull();
    });

    it('does not render the watermark when color routes to the empty BLACK_TROLL_KEYS set', () => {
      const finding = makeFinding({ entry_fen: TROLL_FIXTURE_FEN, color: 'black' });
      renderCard({ finding, idx: 7 });
      expect(screen.queryByTestId('opening-finding-card-7-troll-watermark')).toBeNull();
    });

    it('watermark has pointer-events-none class (D-04)', () => {
      const finding = makeFinding({ entry_fen: TROLL_FIXTURE_FEN, color: 'white' });
      renderCard({ finding, idx: 7 });
      const watermark = screen.getByTestId('opening-finding-card-7-troll-watermark');
      expect(watermark.className).toContain('pointer-events-none');
    });

    it('watermark is decorative (alt="" + aria-hidden)', () => {
      const finding = makeFinding({ entry_fen: TROLL_FIXTURE_FEN, color: 'white' });
      renderCard({ finding, idx: 7 });
      const watermark = screen.getByTestId('opening-finding-card-7-troll-watermark');
      expect(watermark.getAttribute('alt')).toBe('');
      expect(watermark.getAttribute('aria-hidden')).toBe('true');
    });

    it('renders for weakness/major (D-05 always-on)', () => {
      const finding = makeFinding({
        entry_fen: TROLL_FIXTURE_FEN,
        color: 'white',
        classification: 'weakness',
        severity: 'major',
      });
      renderCard({ finding, idx: 7 });
      expect(screen.getByTestId('opening-finding-card-7-troll-watermark')).toBeTruthy();
    });

    it('renders for strength/minor (D-05 always-on)', () => {
      const finding = makeFinding({
        entry_fen: TROLL_FIXTURE_FEN,
        color: 'white',
        classification: 'strength',
        severity: 'minor',
      });
      renderCard({ finding, idx: 7 });
      expect(screen.getByTestId('opening-finding-card-7-troll-watermark')).toBeTruthy();
    });

    it('renders exactly once across both mobile and desktop branches (D-03)', () => {
      const finding = makeFinding({ entry_fen: TROLL_FIXTURE_FEN, color: 'white' });
      renderCard({ finding, idx: 7 });
      const elements = screen.getAllByTestId('opening-finding-card-7-troll-watermark');
      expect(elements.length).toBe(1);
    });

    it('renders the watermark when the candidate move LEADS to a troll position', () => {
      // Starting position is not a troll position, but after 1.e4 the resulting
      // FEN derives (white-side) to the seeded WHITE_TROLL_KEYS entry.
      const finding = makeFinding({
        entry_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        candidate_move_san: 'e4',
        color: 'white',
      });
      renderCard({ finding, idx: 7 });
      expect(screen.getByTestId('opening-finding-card-7-troll-watermark')).toBeTruthy();
    });

    it('does not render the watermark when neither entry nor resulting position match', () => {
      const finding = makeFinding({
        entry_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        candidate_move_san: 'd4', // resulting FEN is not the seeded troll key
        color: 'white',
      });
      renderCard({ finding, idx: 7 });
      expect(screen.queryByTestId('opening-finding-card-7-troll-watermark')).toBeNull();
    });

    it('does not block clicks on the Moves button (D-04)', () => {
      const onFindingClick = vi.fn();
      const finding = makeFinding({ entry_fen: TROLL_FIXTURE_FEN, color: 'white' });
      renderCard({ finding, idx: 7, onFindingClick });
      // The Moves button's testid uses the existing `opening-finding-card-${idx}-moves` template.
      const movesBtns = screen.getAllByTestId('opening-finding-card-7-moves');
      fireEvent.click(movesBtns[0]!);
      expect(onFindingClick).toHaveBeenCalled();
    });
  });

  describe('Quick task 260429-gmj — score-colored after-move arrow', () => {
    // Test A: arrow overlay renders in BOTH layouts when the candidate move parses.
    it('renders <svg data-testid="mini-board-arrow-overlay"> in both mobile and desktop layouts', () => {
      const finding = makeFinding({
        entry_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        candidate_move_san: 'e4',
      });
      renderCard({ finding, idx: 0 });
      const overlays = screen.getAllByTestId('mini-board-arrow-overlay');
      expect(overlays.length).toBe(2); // one in sm:hidden, one in hidden sm:flex
    });

    // Test B: arrow color is driven by score zone (matches Moves-tab scoreZoneColor).
    it.each([
      [0.30, ZONE_DANGER] as const,    // <= 0.45 → red
      [0.45, ZONE_DANGER] as const,    // boundary inclusive
      [0.49, ZONE_NEUTRAL] as const,   // in-between band → blue
      [0.55, ZONE_SUCCESS] as const,   // boundary inclusive
      [0.70, ZONE_SUCCESS] as const,   // >= 0.55 → green
    ])(
      'arrow path fill matches scoreZoneColor for score=%s',
      (score, expectedColor) => {
        const finding = makeFinding({
          score,
          entry_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
          candidate_move_san: 'e4',
        });
        renderCard({ finding, idx: 0 });
        const overlays = screen.getAllByTestId('mini-board-arrow-overlay');
        const path = overlays[0]!.querySelector('path');
        expect(path).not.toBeNull();
        expect(normalizeColor(path!.getAttribute('fill') ?? '')).toBe(normalizeColor(expectedColor));
      },
    );

    // Test C: illegal/unparseable SAN gracefully degrades to no arrow.
    it('does not render the arrow overlay when candidate_move_san is illegal in entry_fen', () => {
      const finding = makeFinding({
        entry_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        candidate_move_san: 'Zz9',
      });
      renderCard({ finding, idx: 0 });
      // Card should still render without throwing.
      expect(screen.getByTestId('opening-finding-card-0')).toBeTruthy();
      expect(screen.queryAllByTestId('mini-board-arrow-overlay').length).toBe(0);
    });

    // Test D: arrow renders for both color sides (board flipped for black).
    it('renders the arrow overlay when finding.color === "black" (flipped board)', () => {
      const finding = makeFinding({
        color: 'black',
        // Position after 1.e4 — black to move. e5 is legal here.
        entry_fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
        candidate_move_san: 'e5',
      });
      renderCard({ finding, idx: 0 });
      const overlays = screen.getAllByTestId('mini-board-arrow-overlay');
      expect(overlays.length).toBe(2);
    });
  });
});

/**
 * jsdom normalizes CSS colors when round-tripped through `style.*` (e.g.
 * `oklch(0.50 0.14 260)` → `oklch(0.5 0.14 260)`). Strip whitespace + collapse
 * trailing zeros so test comparisons are insensitive to that normalization.
 */
function normalizeColor(value: string): string {
  // Strip trailing zeros from decimals (oklch(0.50 ...) ↔ oklch(0.5 ...)).
  return value.replace(/(\.\d*?)0+(?=\D|$)/g, '$1');
}
