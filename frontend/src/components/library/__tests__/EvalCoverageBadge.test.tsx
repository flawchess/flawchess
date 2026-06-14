// @vitest-environment jsdom
/**
 * EvalCoverageBadge tests (Phase 118-03 UAT fixes).
 *
 * Covers the states:
 * 1. Normal: "N of M analyzed" count render
 * 2. In-flight: "· K in progress" appended, no CTA button
 * 3. Low-coverage non-guest: NO button (background auto-enqueue handles it)
 * 4. Low-coverage guest: sees sign-up CTA (btn-coverage-signup)
 * 5. High-coverage: CTA hidden
 * 6. InfoPopover trigger rendered
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { EvalCoverageBadge } from '../EvalCoverageBadge';

// ── Wrapper ───────────────────────────────────────────────────────────────────

function makeWrapper(): ({ children }: { children: ReactNode }) => ReactNode {
  return function Wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

// Default props for convenience
const defaultProps = {
  analyzedN: 5,
  totalN: 10,
  inFlightCount: 0,
  isGuest: false,
  isCoverageError: false,
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('EvalCoverageBadge', () => {
  it('renders analyzed/total count', () => {
    render(<EvalCoverageBadge {...defaultProps} />, { wrapper: makeWrapper() });
    const badge = screen.getByTestId('eval-coverage-badge');
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain('5');
    expect(badge.textContent).toContain('10');
    expect(badge.textContent).toContain('analyzed');
  });

  it('shows "in progress" text when inFlightCount > 0', () => {
    render(<EvalCoverageBadge {...defaultProps} inFlightCount={3} />, { wrapper: makeWrapper() });
    const badge = screen.getByTestId('eval-coverage-badge');
    expect(badge.textContent).toContain('in progress');
    // No CTA when in-flight
    expect(screen.queryByTestId('btn-coverage-signup')).toBeNull();
  });

  it('shows NO button for non-guest below threshold (auto-enqueue handles it)', () => {
    // 5/10 = 50% < 80% LOW_COVERAGE_THRESHOLD, but non-guests get no button —
    // recent games are analyzed automatically in the background.
    render(<EvalCoverageBadge {...defaultProps} analyzedN={5} totalN={10} inFlightCount={0} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.queryByTestId('btn-coverage-signup')).toBeNull();
  });

  it('shows sign-up CTA for guest when coverage is below threshold', () => {
    // 5/10 = 50% < 80% threshold → guest sign-up CTA (their only path to analysis)
    render(<EvalCoverageBadge {...defaultProps} analyzedN={5} totalN={10} isGuest={true} />, {
      wrapper: makeWrapper(),
    });
    const btn = screen.getByTestId('btn-coverage-signup');
    expect(btn).toBeDefined();
    expect(btn.getAttribute('aria-label')).toContain('Sign up');
  });

  it('hides guest CTA when coverage is at or above threshold', () => {
    // 9/10 = 90% ≥ 80% → no CTA even for a guest
    render(<EvalCoverageBadge {...defaultProps} analyzedN={9} totalN={10} isGuest={true} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.queryByTestId('btn-coverage-signup')).toBeNull();
  });

  it('renders the InfoPopover trigger', () => {
    render(<EvalCoverageBadge {...defaultProps} />, { wrapper: makeWrapper() });
    expect(screen.getByTestId('eval-coverage-badge-info')).toBeDefined();
  });
});
