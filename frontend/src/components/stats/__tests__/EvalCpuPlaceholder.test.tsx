// @vitest-environment jsdom
/**
 * Tests for EvalCpuPlaceholder and the tier2-gated eval bar of the RepertoireCard.
 *
 * Covers:
 *   - EvalCpuPlaceholder renders testid, "Analyzing…" label, and Cpu icon
 *   - RepertoireCard: when tier2=false -> EvalCpuPlaceholder renders, no eval value
 *   - RepertoireCard: when tier2=true  -> placeholder absent, eval value renders
 *   - The score bar is present in both cases (score is not eval-dependent)
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, cleanup, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { EvalCpuPlaceholder } from '../EvalCpuPlaceholder';
import { RepertoireCard } from '@/components/openings/stats/RepertoireCard';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import type { RepertoireRowModel } from '@/pages/openings/useRepertoireRows';

afterEach(() => {
  cleanup();
});

// ---------------------------------------------------------------------------
// Shared mocks needed by RepertoireCard
// ---------------------------------------------------------------------------

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock('@/hooks/usePositionBookmarks', () => ({
  useTimeSeries: () => ({ data: undefined, isLoading: false, isError: false }),
  useCreatePositionBookmark: () => ({ mutate: vi.fn(), isPending: false }),
  useDeletePositionBookmark: () => ({ mutate: vi.fn(), isPending: false }),
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

// useReadiness is mocked at module level; individual tests call mockReturnValue
// to override tier2 as needed. Default: tier2=true so eval cells show.
vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: vi.fn(() => ({ tier1: true, tier2: true, pendingCount: 0, totalCount: 0, isLoading: false })),
}));

// ---------------------------------------------------------------------------
// Helper factories
// ---------------------------------------------------------------------------

function makeRow(overrides: Partial<RepertoireRowModel> = {}): RepertoireRowModel {
  return {
    key: 'mpo-12345',
    kind: 'current',
    color: 'white',
    name: 'Test Opening',
    moveLine: '1. e4 e5',
    fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
    fullHash: '12345',
    bookmark: null,
    games: 30,
    wins: 15,
    draws: 7,
    losses: 8,
    winPct: 50,
    drawPct: 23.3,
    lossPct: 26.7,
    lastPlayedAt: null,
    isCurrent: true,
    score: 0.57,
    scoreConfidence: 'medium',
    scorePValue: 0.03,
    scoreCiLow: 0.4,
    scoreCiHigh: 0.74,
    avgEvalPawns: 0.3,
    evalN: 30,
    evalConfidence: 'medium',
    evalPValue: 0.03,
    evalCiLow: 0.1,
    evalCiHigh: 0.5,
    series: null,
    ...overrides,
  };
}

function renderCard() {
  return render(
    <RepertoireCard
      row={makeRow()}
      index={0}
      debouncedFilters={DEFAULT_FILTERS}
      onOpenMoves={() => {}}
      onOpenGames={() => {}}
      onOpenBookmarkGames={() => {}}
    />,
  );
}

// ---------------------------------------------------------------------------
// EvalCpuPlaceholder standalone tests
// ---------------------------------------------------------------------------

describe('EvalCpuPlaceholder — standalone', () => {
  it('renders with data-testid="eval-cpu-placeholder"', () => {
    render(<EvalCpuPlaceholder />);
    const el = document.querySelector('[data-testid="eval-cpu-placeholder"]');
    expect(el).not.toBeNull();
  });

  it('renders the "Analyzing…" label text', () => {
    render(<EvalCpuPlaceholder />);
    const el = document.querySelector('[data-testid="eval-cpu-placeholder"]');
    expect(el?.textContent).toContain('Analyzing');
  });

  it('contains the amber border and background classes (Constraint 6 styling)', () => {
    render(<EvalCpuPlaceholder />);
    const el = document.querySelector('[data-testid="eval-cpu-placeholder"]') as HTMLElement | null;
    expect(el?.className).toMatch(/border-amber-500\/30/);
    expect(el?.className).toMatch(/bg-amber-500\/10/);
  });

  it('contains a Cpu icon element (animate-pulse class)', () => {
    render(<EvalCpuPlaceholder />);
    const el = document.querySelector('[data-testid="eval-cpu-placeholder"]');
    const icon = el?.querySelector('.animate-pulse');
    expect(icon).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// RepertoireCard tier2 gate tests
// ---------------------------------------------------------------------------

describe('RepertoireCard: tier2 gate for the eval bar', () => {
  it('when tier2=false, EvalCpuPlaceholder renders in place of the eval value', async () => {
    const { useReadiness } = await import('@/hooks/useReadiness');
    vi.mocked(useReadiness).mockReturnValue({ tier1: true, tier2: false, pendingCount: 5, totalCount: 20, isLoading: false });
    renderCard();
    expect(screen.queryByTestId('eval-cpu-placeholder')).not.toBeNull();
    expect(screen.queryByTestId('repertoire-card-0-eval-bar')).toBeNull();
    expect(screen.queryByTestId('repertoire-card-0-eval-info')).toBeNull();
  });

  it('when tier2=true, EvalCpuPlaceholder is absent and the eval value renders', async () => {
    const { useReadiness } = await import('@/hooks/useReadiness');
    vi.mocked(useReadiness).mockReturnValue({ tier1: true, tier2: true, pendingCount: 0, totalCount: 20, isLoading: false });
    renderCard();
    expect(screen.queryByTestId('eval-cpu-placeholder')).toBeNull();
    expect(screen.getByTestId('repertoire-card-0-eval-bar-value').textContent).toBe('+0.3');
  });

  it('the score line is present when tier2=false (score is not eval-dependent)', async () => {
    const { useReadiness } = await import('@/hooks/useReadiness');
    vi.mocked(useReadiness).mockReturnValue({ tier1: true, tier2: false, pendingCount: 5, totalCount: 20, isLoading: false });
    renderCard();
    expect(screen.getByTestId('repertoire-card-0-score').textContent).toBe('57%');
  });

  it('the score line is present when tier2=true', async () => {
    const { useReadiness } = await import('@/hooks/useReadiness');
    vi.mocked(useReadiness).mockReturnValue({ tier1: true, tier2: true, pendingCount: 0, totalCount: 20, isLoading: false });
    renderCard();
    expect(screen.getByTestId('repertoire-card-0-score').textContent).toBe('57%');
  });
});
