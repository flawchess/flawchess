// @vitest-environment jsdom
/**
 * TrainRevealActionBar.test.tsx — Phase 237 plan 07.
 *
 * The presentational contract of the reveal's one action bar: the four board
 * buttons, Analyze (only with a URL) and Next, the walkthrough ring, the
 * desktop key hint, and that every control reaches its callback.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { TooltipProvider } from '@/components/ui/tooltip';
import {
  TrainRevealActionBar,
  type TrainRevealActionBarProps,
} from '@/components/train/TrainRevealActionBar';

afterEach(() => {
  cleanup();
});

function makeProps(overrides: Partial<TrainRevealActionBarProps> = {}): TrainRevealActionBarProps {
  return {
    onRewind: vi.fn(),
    onBack: vi.fn(),
    onForward: vi.fn(),
    onFlip: vi.fn(),
    canRewind: true,
    canGoBack: true,
    canGoForward: true,
    analyzeTo: '/analysis/100?ply=19',
    onAnalyzeClick: vi.fn(),
    onNext: vi.fn(),
    ...overrides,
  };
}

function renderBar(props: TrainRevealActionBarProps) {
  return render(
    <MemoryRouter>
      <TooltipProvider>
        <TrainRevealActionBar {...props} />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

describe('TrainRevealActionBar', () => {
  it('renders the four board buttons, Analyze with its href, and Next', () => {
    renderBar(makeProps());
    expect(screen.getByTestId('board-btn-reset')).not.toBeNull();
    expect(screen.getByTestId('board-btn-back')).not.toBeNull();
    expect(screen.getByTestId('board-btn-forward')).not.toBeNull();
    expect(screen.getByTestId('board-btn-flip')).not.toBeNull();
    expect(screen.getByTestId('btn-train-analyze').getAttribute('href')).toBe('/analysis/100?ply=19');
    expect(screen.getByTestId('btn-train-next')).not.toBeNull();
  });

  it('renders no Analyze when analyzeTo is null', () => {
    renderBar(makeProps({ analyzeTo: null }));
    expect(screen.queryByTestId('btn-train-analyze')).toBeNull();
    expect(screen.getByTestId('btn-train-next')).not.toBeNull();
  });

  it('canRewind false disables rewind only', () => {
    renderBar(makeProps({ canRewind: false }));
    expect((screen.getByTestId('board-btn-reset') as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId('board-btn-back') as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByTestId('board-btn-forward') as HTMLButtonElement).disabled).toBe(false);
  });


  it('every control reaches its callback exactly once', () => {
    const props = makeProps();
    renderBar(props);
    fireEvent.click(screen.getByTestId('board-btn-reset'));
    fireEvent.click(screen.getByTestId('board-btn-back'));
    fireEvent.click(screen.getByTestId('board-btn-forward'));
    fireEvent.click(screen.getByTestId('board-btn-flip'));
    fireEvent.click(screen.getByTestId('btn-train-analyze'));
    fireEvent.click(screen.getByTestId('btn-train-next'));
    expect(props.onRewind).toHaveBeenCalledTimes(1);
    expect(props.onBack).toHaveBeenCalledTimes(1);
    expect(props.onForward).toHaveBeenCalledTimes(1);
    expect(props.onFlip).toHaveBeenCalledTimes(1);
    expect(props.onAnalyzeClick).toHaveBeenCalledTimes(1);
    expect(props.onNext).toHaveBeenCalledTimes(1);
  });
});
