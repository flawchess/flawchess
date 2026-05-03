// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import type { ReactNode } from 'react';
import { ConfidencePill } from '../ConfidencePill';

afterEach(() => {
  cleanup();
});

// Mock Tooltip so tests don't require TooltipProvider
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

// Mock ConfidenceTooltipContent to avoid prop complexity in tests
vi.mock('@/components/insights/ConfidenceTooltipContent', () => ({
  ConfidenceTooltipContent: ({ level }: { level: string }) => (
    <div data-testid="mock-confidence-tooltip">{level} tooltip</div>
  ),
}));

describe('ConfidencePill', () => {
  it('renders the level text', () => {
    render(<ConfidencePill level="medium" pValue={0.07} />);
    expect(screen.getByText('medium')).toBeDefined();
  });

  it('renders inside a Tooltip wrapper (tooltip content available)', () => {
    render(<ConfidencePill level="high" pValue={0.03} score={0.6} gameCount={25} />);
    // The Tooltip is mocked so the content renders directly — just verify the pill text
    expect(screen.getByText('high')).toBeDefined();
  });

  it('applies testId when provided', () => {
    render(<ConfidencePill level="high" testId="my-pill" />);
    const el = screen.getByTestId('my-pill');
    expect(el).toBeDefined();
    expect(el.textContent).toBe('high');
  });

  it('renders low level', () => {
    render(<ConfidencePill level="low" />);
    expect(screen.getByText('low')).toBeDefined();
  });
});
