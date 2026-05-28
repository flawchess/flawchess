// @vitest-environment jsdom
/**
 * Tests for EvalCpuPlaceholder and the tier2-gated eval row in OpeningStatsCard.
 *
 * Covers:
 *   - EvalCpuPlaceholder renders testid, "Analyzing…" label, and Cpu icon
 *   - OpeningStatsCard: when tier2=false → EvalCpuPlaceholder renders, eval-text row absent
 *   - OpeningStatsCard: when tier2=true  → placeholder absent, eval metric renders
 *   - WDL score row is present in both tier2=true and tier2=false cases
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import type { ReactNode } from 'react';
import { EvalCpuPlaceholder } from '../EvalCpuPlaceholder';
import { OpeningStatsCard } from '../OpeningStatsCard';
import type { OpeningWDL } from '@/types/stats';

afterEach(() => {
  cleanup();
});

// ---------------------------------------------------------------------------
// Shared mocks needed by OpeningStatsCard
// ---------------------------------------------------------------------------

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

// useReadiness is mocked at module level; individual tests call mockReturnValue
// to override tier2 as needed. Default: tier2=true so eval rows show.
vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: vi.fn(() => ({ tier1: true, tier2: true, pendingCount: 0, totalCount: 0, isLoading: false })),
}));

// ---------------------------------------------------------------------------
// Helper factories
// ---------------------------------------------------------------------------

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
    eval_n: 30,
    eval_confidence: 'medium',
    avg_eval_pawns: 0.3,
    eval_p_value: 0.03,
    ...overrides,
  };
}

const noop = () => {};

function renderCard(props: Partial<React.ComponentProps<typeof OpeningStatsCard>> = {}) {
  const opening = props.opening ?? makeOpening();
  return render(
    <OpeningStatsCard
      opening={opening}
      color={props.color ?? 'white'}
      idx={props.idx ?? 0}
      testIdPrefix={props.testIdPrefix ?? 'stats-card'}
      onOpenMoves={props.onOpenMoves ?? noop}
      onOpenGames={props.onOpenGames ?? noop}
      evalBaselinePawns={props.evalBaselinePawns ?? 0.25}
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
    expect(el?.className).toMatch(/border-amber-400\/40/);
    expect(el?.className).toMatch(/bg-amber-50\/60/);
  });

  it('contains a Cpu icon element (animate-pulse class)', () => {
    render(<EvalCpuPlaceholder />);
    const el = document.querySelector('[data-testid="eval-cpu-placeholder"]');
    const icon = el?.querySelector('.animate-pulse');
    expect(icon).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// OpeningStatsCard tier2 gate tests
// ---------------------------------------------------------------------------

describe('OpeningStatsCard — tier2 gate for eval rows', () => {
  it('when tier2=false, EvalCpuPlaceholder renders in place of the eval rows', async () => {
    const { useReadiness } = await import('@/hooks/useReadiness');
    vi.mocked(useReadiness).mockReturnValue({ tier1: true, tier2: false, pendingCount: 5, totalCount: 20, isLoading: false });
    renderCard({ idx: 20 });
    const placeholder = document.querySelector('[data-testid="eval-cpu-placeholder"]');
    expect(placeholder).not.toBeNull();
    // eval-text row must NOT be present when placeholder is shown
    const evalText = document.querySelector('[data-testid="stats-card-20-eval-text"]');
    expect(evalText).toBeNull();
  });

  it('when tier2=true, EvalCpuPlaceholder is absent and eval metric renders', async () => {
    const { useReadiness } = await import('@/hooks/useReadiness');
    vi.mocked(useReadiness).mockReturnValue({ tier1: true, tier2: true, pendingCount: 0, totalCount: 20, isLoading: false });
    renderCard({ idx: 21, opening: makeOpening({ eval_n: 30, avg_eval_pawns: 0.3, eval_p_value: 0.03 }) });
    const placeholder = document.querySelector('[data-testid="eval-cpu-placeholder"]');
    expect(placeholder).toBeNull();
    const evalText = document.querySelector('[data-testid="stats-card-21-eval-text"]');
    expect(evalText).not.toBeNull();
  });

  it('WDL score row is present when tier2=false (score is not eval-dependent)', async () => {
    const { useReadiness } = await import('@/hooks/useReadiness');
    vi.mocked(useReadiness).mockReturnValue({ tier1: true, tier2: false, pendingCount: 5, totalCount: 20, isLoading: false });
    renderCard({ idx: 22 });
    const scoreBullet = document.querySelector('[data-testid="stats-card-22-score-bullet"]');
    expect(scoreBullet).not.toBeNull();
    const scoreText = document.querySelector('[data-testid="stats-card-22-score-text"]');
    expect(scoreText).not.toBeNull();
  });

  it('WDL score row is present when tier2=true', async () => {
    const { useReadiness } = await import('@/hooks/useReadiness');
    vi.mocked(useReadiness).mockReturnValue({ tier1: true, tier2: true, pendingCount: 0, totalCount: 20, isLoading: false });
    renderCard({ idx: 23 });
    const scoreBullet = document.querySelector('[data-testid="stats-card-23-score-bullet"]');
    expect(scoreBullet).not.toBeNull();
    const scoreText = document.querySelector('[data-testid="stats-card-23-score-text"]');
    expect(scoreText).not.toBeNull();
  });
});
