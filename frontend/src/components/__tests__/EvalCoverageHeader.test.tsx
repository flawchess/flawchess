// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import type { Mock } from 'vitest';

// Mock useEvalCoverage so this component test does not need a QueryClientProvider
vi.mock('@/hooks/useEvalCoverage', () => ({
  useEvalCoverage: vi.fn(),
}));

import { useEvalCoverage } from '@/hooks/useEvalCoverage';
import { EvalCoverageHeader } from '../EvalCoverageHeader';

describe('EvalCoverageHeader', () => {
  afterEach(() => {
    cleanup();
  });
  it('is hidden when not pending', () => {
    (useEvalCoverage as Mock).mockReturnValue({
      isPending: false,
      pendingCount: 0,
      totalCount: 100,
      pct: 100,
    });

    const { container } = render(<EvalCoverageHeader />);
    expect(screen.queryByTestId('eval-coverage-header')).toBeNull();
    expect(container.firstChild).toBeNull();
  });

  it('renders absolute counts ("N of M games analysed") when multiple games are pending', () => {
    (useEvalCoverage as Mock).mockReturnValue({
      isPending: true,
      pendingCount: 1432,
      totalCount: 11000,
      pct: 87,
    });

    render(<EvalCoverageHeader />);
    const el = screen.getByTestId('eval-coverage-header');
    expect(el).toBeTruthy();
    expect(el.textContent).toContain('Stockfish analysis in progress');
    // analysedCount = 11000 - 1432 = 9568
    expect(el.textContent).toContain('9,568 of 11,000 games analysed');
    expect(el.textContent).toContain('(1,432 still pending)');
  });

  it('handles singular total (1 game total, 1 pending)', () => {
    (useEvalCoverage as Mock).mockReturnValue({
      isPending: true,
      pendingCount: 1,
      totalCount: 1,
      pct: 0,
    });

    render(<EvalCoverageHeader />);
    const el = screen.getByTestId('eval-coverage-header');
    expect(el.textContent).toContain('0 of 1 game analysed');
    expect(el.textContent).toContain('(1 still pending)');
  });

  it('clamps analysed count at 0 when pendingCount > totalCount (defensive race during import)', () => {
    // During a live import, the GET /eval-coverage response may briefly show
    // pending > total if the rows are read before the inserts commit. Defensive
    // floor at 0 prevents a negative count from rendering.
    (useEvalCoverage as Mock).mockReturnValue({
      isPending: true,
      pendingCount: 10,
      totalCount: 5,
      pct: 0,
    });

    render(<EvalCoverageHeader />);
    const el = screen.getByTestId('eval-coverage-header');
    expect(el.textContent).toContain('0 of 5 games analysed');
  });

  it('has role="status" and data-testid on root element', () => {
    (useEvalCoverage as Mock).mockReturnValue({
      isPending: true,
      pendingCount: 5,
      totalCount: 10,
      pct: 50,
    });

    render(<EvalCoverageHeader />);
    const el = screen.getByRole('status');
    expect(el).toBeTruthy();
    expect(el.getAttribute('data-testid')).toBe('eval-coverage-header');
  });
});
