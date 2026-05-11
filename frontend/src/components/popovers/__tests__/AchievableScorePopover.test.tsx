// @vitest-environment jsdom
/**
 * Phase 83 Plan 03 Task 2: AchievableScorePopover wrapper.
 *
 * Verifies the D-10 verbatim body copy gates (must contain "2300+", must NOT
 * contain "underperformance"), default testid, and aria-label.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

import { AchievableScorePopover } from '../AchievableScorePopover';

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const baseProps = {
  score: 0.62,
  gameCount: 50,
  level: 'high' as const,
  pValue: 0.001,
};

describe('AchievableScorePopover', () => {
  it('renders trigger with default data-testid', () => {
    render(<AchievableScorePopover {...baseProps} />);
    expect(screen.getByTestId('popover-trigger-achievable-score')).toBeTruthy();
  });

  it('trigger carries aria-label for screen readers', () => {
    render(<AchievableScorePopover {...baseProps} />);
    const trigger = screen.getByTestId('popover-trigger-achievable-score');
    expect(trigger.getAttribute('aria-label')).toBeTruthy();
    expect(trigger.getAttribute('aria-label')).toMatch(/achievable score/i);
  });

  it('accepts custom testId prop', () => {
    render(<AchievableScorePopover {...baseProps} testId="custom-trigger" />);
    expect(screen.getByTestId('custom-trigger')).toBeTruthy();
  });

  it('opens on click and shows D-10 body copy containing "2300+"', async () => {
    render(<AchievableScorePopover {...baseProps} />);
    const trigger = screen.getByTestId('popover-trigger-achievable-score');
    fireEvent.click(trigger);
    await waitFor(() => {
      // Body lives inside a Radix portal; query the entire document.
      expect(document.body.textContent).toMatch(/2300\+/);
    });
  });

  it('body copy does NOT contain the forbidden word "underperformance" (D-10)', async () => {
    render(<AchievableScorePopover {...baseProps} />);
    const trigger = screen.getByTestId('popover-trigger-achievable-score');
    fireEvent.click(trigger);
    await waitFor(() => {
      expect(document.body.textContent).toMatch(/2300\+/);
    });
    expect(document.body.textContent).not.toMatch(/underperformance/i);
    expect(document.body.textContent).not.toMatch(/fall short/i);
    expect(document.body.textContent).not.toMatch(/below your potential/i);
  });

  it('body copy mentions the Lichess formula and the achieved-score comparison', async () => {
    render(<AchievableScorePopover {...baseProps} />);
    fireEvent.click(screen.getByTestId('popover-trigger-achievable-score'));
    await waitFor(() => {
      expect(document.body.textContent).toMatch(/Lichess/i);
    });
    expect(document.body.textContent).toMatch(/Compare.*against your achieved Endgame score/i);
  });

  it('renders WdlConfidenceTooltip-style stats line with rounded percentages', async () => {
    render(<AchievableScorePopover {...baseProps} />);
    fireEvent.click(screen.getByTestId('popover-trigger-achievable-score'));
    await waitFor(() => {
      expect(document.body.textContent).toMatch(/62\.0% achievable score/);
    });
    expect(document.body.textContent).toMatch(/over 50 games/);
    expect(document.body.textContent).toMatch(/12\.0% above the 50% baseline/);
    expect(document.body.textContent).toMatch(/p = 0\.001/);
  });
});
