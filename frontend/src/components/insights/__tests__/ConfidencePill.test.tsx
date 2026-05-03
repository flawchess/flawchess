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

// Partial mock: render ConfidenceTooltipContent with real implementation for branch testing,
// but track calls via a spy-friendly wrapper when needed.
vi.mock('@/components/insights/ConfidenceTooltipContent', () => ({
  ConfidenceTooltipContent: ({
    level,
    evalMeanPawns,
  }: {
    level: string;
    evalMeanPawns?: number | null;
  }) => (
    <div data-testid="mock-confidence-tooltip" data-eval={evalMeanPawns ?? 'none'}>
      {level} tooltip
    </div>
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

  describe('WDL branch (no evalMeanPawns)', () => {
    it('passes undefined evalMeanPawns to tooltip when not provided', () => {
      render(<ConfidencePill level="medium" pValue={0.07} score={0.6} gameCount={20} />);
      const tooltip = screen.getByTestId('mock-confidence-tooltip');
      // evalMeanPawns not set → data attribute is 'none'
      expect(tooltip.getAttribute('data-eval')).toBe('none');
    });
  });

  describe('eval branch (evalMeanPawns provided)', () => {
    it('passes evalMeanPawns to tooltip when provided', () => {
      render(
        <ConfidencePill
          level="high"
          pValue={0.03}
          gameCount={15}
          evalMeanPawns={0.42}
          testId="eval-pill"
        />
      );
      // Pill still shows the level text
      expect(screen.getByTestId('eval-pill').textContent).toBe('high');
      // Tooltip receives the eval value
      const tooltip = screen.getByTestId('mock-confidence-tooltip');
      expect(tooltip.getAttribute('data-eval')).toBe('0.42');
    });

    it('passes negative evalMeanPawns correctly', () => {
      render(
        <ConfidencePill level="medium" pValue={0.08} gameCount={12} evalMeanPawns={-0.35} />
      );
      const tooltip = screen.getByTestId('mock-confidence-tooltip');
      expect(tooltip.getAttribute('data-eval')).toBe('-0.35');
    });

    it('passes null evalMeanPawns (falls back to WDL branch in tooltip)', () => {
      render(
        <ConfidencePill level="low" pValue={0.3} gameCount={5} evalMeanPawns={null} />
      );
      const tooltip = screen.getByTestId('mock-confidence-tooltip');
      // null is serialised as 'none' by the mock (null ?? 'none')
      expect(tooltip.getAttribute('data-eval')).toBe('none');
    });
  });
});
