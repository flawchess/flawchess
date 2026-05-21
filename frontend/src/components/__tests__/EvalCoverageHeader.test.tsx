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
      pct: 100,
    });

    const { container } = render(<EvalCoverageHeader />);
    expect(screen.queryByTestId('eval-coverage-header')).toBeNull();
    expect(container.firstChild).toBeNull();
  });

  it('renders with plural label when multiple games are pending', () => {
    (useEvalCoverage as Mock).mockReturnValue({
      isPending: true,
      pendingCount: 1432,
      pct: 87,
    });

    render(<EvalCoverageHeader />);
    const el = screen.getByTestId('eval-coverage-header');
    expect(el).toBeTruthy();
    expect(el.textContent).toContain('Stockfish analysis in progress');
    expect(el.textContent).toContain('87');
    expect(el.textContent).toContain('1,432 games still pending');
  });

  it('renders with singular label when exactly one game is pending', () => {
    (useEvalCoverage as Mock).mockReturnValue({
      isPending: true,
      pendingCount: 1,
      pct: 99,
    });

    render(<EvalCoverageHeader />);
    const el = screen.getByTestId('eval-coverage-header');
    expect(el.textContent).toContain('(1 game still pending)');
  });

  it('has role="status" and data-testid on root element', () => {
    (useEvalCoverage as Mock).mockReturnValue({
      isPending: true,
      pendingCount: 5,
      pct: 50,
    });

    render(<EvalCoverageHeader />);
    const el = screen.getByRole('status');
    expect(el).toBeTruthy();
    expect(el.getAttribute('data-testid')).toBe('eval-coverage-header');
  });
});
