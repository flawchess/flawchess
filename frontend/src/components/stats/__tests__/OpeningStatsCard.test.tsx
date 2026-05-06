// @vitest-environment jsdom
/**
 * Tests for OpeningStatsCard — the per-row card used by the Stats subtab
 * (white-left / black-right column layout). Mirrors OpeningFindingCard's
 * card-shell visuals and reuses MostPlayedOpeningsTable's MG-entry eval cell
 * logic verbatim (signed pawn text + zone color + confidence info icon +
 * low-data muting).
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, fireEvent, cleanup } from '@testing-library/react';
import type { ReactNode } from 'react';
import type { OpeningWDL } from '@/types/stats';
import { OpeningStatsCard } from '../OpeningStatsCard';
import { UNRELIABLE_OPACITY } from '@/lib/theme';
import { evalZoneColor } from '@/lib/openingStatsZones';

afterEach(() => {
  cleanup();
});

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock('@/components/board/LazyMiniBoard', () => ({
  LazyMiniBoard: ({ fen, flipped, size }: { fen: string; flipped: boolean; size: number }) => (
    <div
      data-testid="lazy-mini-board"
      data-fen={fen}
      data-flipped={String(flipped)}
      data-size={String(size)}
    />
  ),
}));

vi.mock('@/components/charts/MiniBulletChart', () => ({
  MiniBulletChart: ({ ariaLabel }: { ariaLabel?: string }) => (
    <div data-testid="mini-bullet-chart" aria-label={ariaLabel} />
  ),
}));

vi.mock('@/components/insights/BulletConfidencePopover', () => ({
  BulletConfidencePopover: ({ testId }: { testId?: string }) => (
    <button type="button" data-testid={testId}>?</button>
  ),
}));

function makeOpening(overrides: Partial<OpeningWDL> = {}): OpeningWDL {
  return {
    opening_eco: 'A00',
    opening_name: 'Test Opening',
    display_name: 'Test Opening',
    label: 'Test Opening (A00)',
    pgn: '1. e4 e5',
    fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
    full_hash: '12345',
    wins: 10,
    draws: 5,
    losses: 5,
    total: 20,
    win_pct: 50,
    draw_pct: 25,
    loss_pct: 25,
    eval_n: 0,
    eval_confidence: 'low',
    ...overrides,
  };
}

const noop = () => {};

// jsdom normalizes oklch component literals (e.g. "0.50" -> "0.5"); strip
// trailing zeros so the assertion is robust to that. Same trick used by
// MostPlayedOpeningsTable.test.tsx.
function normalizeColor(c: string): string {
  return c.replace(/\s+/g, ' ').replace(/(\d)\.(\d+?)0+(\D|$)/g, '$1.$2$3').trim();
}

function renderCard(props: Partial<React.ComponentProps<typeof OpeningStatsCard>> = {}) {
  const opening = props.opening ?? makeOpening();
  return render(
    <OpeningStatsCard
      opening={opening}
      color={props.color ?? 'white'}
      idx={props.idx ?? 0}
      testIdPrefix={props.testIdPrefix ?? 'opening-stats-card'}
      onOpenMoves={props.onOpenMoves ?? noop}
      onOpenGames={props.onOpenGames ?? noop}
      evalBaselinePawns={props.evalBaselinePawns ?? 0.25}
    />,
  );
}

describe('OpeningStatsCard — board + flip', () => {
  it('renders LazyMiniBoard with the opening fen and flipped=false for white color', () => {
    renderCard({ color: 'white' });
    const board = document.querySelector('[data-testid="lazy-mini-board"]') as HTMLElement | null;
    expect(board).not.toBeNull();
    expect(board?.getAttribute('data-fen')).toBe(
      'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
    );
    expect(board?.getAttribute('data-flipped')).toBe('false');
  });

  it('flips the board when color is black', () => {
    renderCard({ color: 'black' });
    const board = document.querySelector('[data-testid="lazy-mini-board"]') as HTMLElement | null;
    expect(board?.getAttribute('data-flipped')).toBe('true');
  });
});

describe('OpeningStatsCard — WDL chart row', () => {
  it('renders the WDL bar segments via WDLChartRow', () => {
    renderCard({ idx: 2 });
    const wdl = document.querySelector('[data-testid="opening-stats-card-2-wdl"]');
    expect(wdl).not.toBeNull();
  });
});

describe('OpeningStatsCard — eval cell', () => {
  it('eval_n > 0 renders signed pawn text in zone color, MiniBulletChart, and confidence info icon', () => {
    const opening = makeOpening({
      avg_eval_pawns: 0.65,
      eval_ci_low_pawns: 0.3,
      eval_ci_high_pawns: 0.9,
      eval_n: 50,
      eval_confidence: 'high',
      eval_p_value: 0.001,
    });
    renderCard({ opening, idx: 1 });
    const evalText = document.querySelector('[data-testid="opening-stats-card-1-eval-text"]');
    expect(evalText).not.toBeNull();
    expect(evalText?.textContent).toContain('+0.7');
    const span = evalText?.querySelector('span.font-semibold') as HTMLElement | null;
    expect(normalizeColor(span?.style.color ?? '')).toBe(normalizeColor(evalZoneColor(0.65)));
    const bullet = document.querySelector('[data-testid="opening-stats-card-1-bullet"]');
    expect(bullet?.querySelector('[data-testid="mini-bullet-chart"]')).not.toBeNull();
    const popover = document.querySelector('[data-testid="opening-stats-card-1-bullet-popover"]');
    expect(popover).not.toBeNull();
  });

  it('eval_n === 0 renders em-dash for both eval text and bullet, no popover', () => {
    const opening = makeOpening({ eval_n: 0 });
    renderCard({ opening, idx: 0 });
    const evalText = document.querySelector('[data-testid="opening-stats-card-0-eval-text"]');
    const bullet = document.querySelector('[data-testid="opening-stats-card-0-bullet"]');
    expect(evalText?.textContent).toBe('—');
    expect(bullet?.textContent).toBe('—');
    expect(bullet?.querySelector('[data-testid="mini-bullet-chart"]')).toBeNull();
    expect(
      document.querySelector('[data-testid="opening-stats-card-0-bullet-popover"]'),
    ).toBeNull();
  });
});

describe('OpeningStatsCard — Moves and Games links', () => {
  it('Moves link invokes onOpenMoves with the opening and color', () => {
    const onOpenMoves = vi.fn();
    const opening = makeOpening();
    renderCard({ opening, color: 'white', idx: 3, onOpenMoves });
    const movesBtn = document.querySelector(
      '[data-testid="opening-stats-card-3-moves"]',
    ) as HTMLButtonElement | null;
    expect(movesBtn).not.toBeNull();
    fireEvent.click(movesBtn!);
    expect(onOpenMoves).toHaveBeenCalledTimes(1);
    expect(onOpenMoves).toHaveBeenCalledWith(opening, 'white');
  });

  it('Games link invokes onOpenGames with the opening and color', () => {
    const onOpenGames = vi.fn();
    const opening = makeOpening();
    renderCard({ opening, color: 'black', idx: 4, onOpenGames });
    const gamesBtn = document.querySelector(
      '[data-testid="opening-stats-card-4-games"]',
    ) as HTMLButtonElement | null;
    expect(gamesBtn).not.toBeNull();
    fireEvent.click(gamesBtn!);
    expect(onOpenGames).toHaveBeenCalledTimes(1);
    expect(onOpenGames).toHaveBeenCalledWith(opening, 'black');
  });
});

describe('OpeningStatsCard — low-data muting', () => {
  it('total < MIN_GAMES_OPENING_ROW applies UNRELIABLE_OPACITY to the card root', () => {
    const opening = makeOpening({ total: 15 });
    renderCard({ opening, idx: 5 });
    const card = document.querySelector(
      '[data-testid="opening-stats-card-5"]',
    ) as HTMLElement | null;
    expect(card).not.toBeNull();
    expect(card?.style.opacity).toBe(String(UNRELIABLE_OPACITY));
  });

  it('total >= MIN_GAMES_OPENING_ROW does NOT mute the card', () => {
    const opening = makeOpening({ total: 50 });
    renderCard({ opening, idx: 6 });
    const card = document.querySelector(
      '[data-testid="opening-stats-card-6"]',
    ) as HTMLElement | null;
    expect(card?.style.opacity).toBe('');
  });
});

describe('OpeningStatsCard — border-left color', () => {
  it('uses evalZoneColor when MG eval is present', () => {
    const opening = makeOpening({
      avg_eval_pawns: -0.5,
      eval_n: 30,
      eval_confidence: 'high',
    });
    renderCard({ opening, idx: 7 });
    const card = document.querySelector(
      '[data-testid="opening-stats-card-7"]',
    ) as HTMLElement | null;
    expect(normalizeColor(card?.style.borderLeftColor ?? '')).toBe(
      normalizeColor(evalZoneColor(-0.5)),
    );
  });

  it('falls back to transparent border when eval_n === 0', () => {
    const opening = makeOpening({ eval_n: 0 });
    renderCard({ opening, idx: 8 });
    const card = document.querySelector(
      '[data-testid="opening-stats-card-8"]',
    ) as HTMLElement | null;
    expect(card?.style.borderLeftColor).toBe('transparent');
  });
});
