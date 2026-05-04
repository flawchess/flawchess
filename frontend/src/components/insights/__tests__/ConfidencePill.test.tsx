// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import type { ReactNode } from 'react';
import { ConfidencePill } from '../ConfidencePill';

afterEach(() => {
  cleanup();
});

// Mock Tooltip: render both children (the pill span) and content (the tooltip body)
// so tests can inspect what gets passed to WdlConfidenceTooltip.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children, content }: { children: ReactNode; content?: ReactNode }) => (
    <>
      {children}
      {content}
    </>
  ),
}));

vi.mock('@/components/insights/WdlConfidenceTooltip', () => ({
  WdlConfidenceTooltip: ({ level }: { level: string }) => (
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
    expect(screen.getByText('high')).toBeDefined();
    expect(screen.getByTestId('mock-confidence-tooltip').textContent).toBe('high tooltip');
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
