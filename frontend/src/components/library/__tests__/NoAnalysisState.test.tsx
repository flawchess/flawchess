// @vitest-environment jsdom
/**
 * NoAnalysisState tests (Phase 118-03).
 *
 * Tests the four branches:
 * 1. Guest → sign-up CTA with btn-signup-for-analysis
 * 2. Not-analyzed, not in-flight → "Analyze" button with btn-analyze-game-{gameId}
 *    fires the tier-1 mutation on click
 * 3. Not-analyzed, in-flight → pulsing "Analyzing…" span with analyzing-{gameId}
 * 4. Already analyzed → returns null (no DOM)
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { NoAnalysisState } from '../NoAnalysisState';

// ── Mock useTier1Enqueue ───────────────────────────────────────────────────────

const mockMutate = vi.fn();

vi.mock('@/hooks/useEnqueueGame', () => ({
  useTier1Enqueue: () => ({ mutate: mockMutate, isPending: false }),
}));

// ── Wrapper ────────────────────────────────────────────────────────────────────

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

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('NoAnalysisState', () => {
  it('guest: renders sign-up CTA with data-testid="btn-signup-for-analysis"', () => {
    render(
      <NoAnalysisState gameId={42} isGuest={true} isAnalyzed={false} />,
      { wrapper: makeWrapper() },
    );
    const btn = screen.getByTestId('btn-signup-for-analysis');
    expect(btn).toBeDefined();
    expect(btn.getAttribute('aria-label')).toContain('Sign up');
  });

  it('guest: does not render analyze button', () => {
    render(
      <NoAnalysisState gameId={42} isGuest={true} isAnalyzed={false} />,
      { wrapper: makeWrapper() },
    );
    expect(screen.queryByTestId('btn-analyze-game-42')).toBeNull();
  });

  it('not-analyzed, not in-flight: renders btn-analyze-game-{gameId}', () => {
    render(
      <NoAnalysisState gameId={7} isGuest={false} isAnalyzed={false} isInFlight={false} />,
      { wrapper: makeWrapper() },
    );
    const btn = screen.getByTestId('btn-analyze-game-7');
    expect(btn).toBeDefined();
  });

  it('not-analyzed, not in-flight: clicking analyze button fires tier-1 mutation', () => {
    render(
      <NoAnalysisState gameId={7} isGuest={false} isAnalyzed={false} isInFlight={false} />,
      { wrapper: makeWrapper() },
    );
    fireEvent.click(screen.getByTestId('btn-analyze-game-7'));
    expect(mockMutate).toHaveBeenCalled();
  });

  it('not-analyzed, in-flight: renders pulsing Analyzing… span with analyzing-{gameId}', () => {
    render(
      <NoAnalysisState gameId={99} isGuest={false} isAnalyzed={false} isInFlight={true} />,
      { wrapper: makeWrapper() },
    );
    const span = screen.getByTestId('analyzing-99');
    expect(span).toBeDefined();
    expect(span.textContent).toContain('Analyzing');
    // No analyze button when in-flight
    expect(screen.queryByTestId('btn-analyze-game-99')).toBeNull();
  });

  it('analyzed: returns null — no DOM node rendered', () => {
    const { container } = render(
      <NoAnalysisState gameId={5} isGuest={false} isAnalyzed={true} />,
      { wrapper: makeWrapper() },
    );
    // Null render → empty container
    expect(container.firstChild).toBeNull();
  });
});
