// @vitest-environment jsdom
/**
 * The presentational contract of the reveal's one action bar: the four board
 * buttons, Analyze (only with a URL) and Next, the tour ring, the
 * desktop key hint, and that every control reaches its callback.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { TooltipProvider } from '@/components/ui/tooltip';
import {
  TrainRevealActionBar,
  TrainRevealControlsRow,
  TrainRevealFooter,
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
  it('renders the three board buttons (no flip), Analyze with its href, and Next', () => {
    renderBar(makeProps());
    expect(screen.getByTestId('board-btn-reset')).not.toBeNull();
    expect(screen.getByTestId('board-btn-back')).not.toBeNull();
    expect(screen.getByTestId('board-btn-forward')).not.toBeNull();
    expect(screen.queryByTestId('board-btn-flip')).toBeNull();
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
    fireEvent.click(screen.getByTestId('btn-train-analyze'));
    fireEvent.click(screen.getByTestId('btn-train-next'));
    expect(props.onRewind).toHaveBeenCalledTimes(1);
    expect(props.onBack).toHaveBeenCalledTimes(1);
    expect(props.onForward).toHaveBeenCalledTimes(1);
    expect(props.onAnalyzeClick).toHaveBeenCalledTimes(1);
    expect(props.onNext).toHaveBeenCalledTimes(1);
  });

  // The desktop sidebar split (Phase 249 UAT): the controls in one row, Analyze and Next in the footer.
  it('the desktop controls row holds only the framed controls: no Analyze or Next, flip on request', () => {
    const props = makeProps();
    render(
      <MemoryRouter>
        <TooltipProvider>
          <TrainRevealControlsRow {...props} />
        </TooltipProvider>
      </MemoryRouter>,
    );
    const row = screen.getByTestId('train-reveal-controls-row');
    const frame = screen.getByTestId('train-reveal-controls-frame');
    expect(frame.contains(screen.getByTestId('board-btn-reset'))).toBe(true);
    expect(frame.contains(screen.getByTestId('board-btn-forward'))).toBe(true);
    expect(row.contains(frame)).toBe(true);
    expect(screen.queryByTestId('btn-train-analyze')).toBeNull();
    expect(screen.queryByTestId('board-btn-flip')).toBeNull();
    expect(screen.queryByTestId('btn-train-next')).toBeNull();
  });

  it('the desktop controls row shows flip when given a handler', () => {
    const onFlip = vi.fn();
    render(
      <MemoryRouter>
        <TooltipProvider>
          <TrainRevealControlsRow {...makeProps()} onFlip={onFlip} />
        </TooltipProvider>
      </MemoryRouter>,
    );
    const flip = screen.getByTestId('board-btn-flip');
    expect(screen.getByTestId('train-reveal-controls-frame').contains(flip)).toBe(true);
    fireEvent.click(flip);
    expect(onFlip).toHaveBeenCalledTimes(1);
  });

  it('the desktop footer puts Analyze left of Next, equally wide', () => {
    const onNext = vi.fn();
    const onAnalyzeClick = vi.fn();
    render(
      <MemoryRouter>
        <TrainRevealFooter onNext={onNext} analyzeTo="/analysis" onAnalyzeClick={onAnalyzeClick} />
      </MemoryRouter>,
    );
    const analyze = screen.getByTestId('btn-train-analyze');
    const next = screen.getByTestId('btn-train-next');
    expect(Array.from(screen.getByTestId('train-reveal-actions-footer').children)).toEqual([analyze, next]);
    for (const button of [analyze, next]) {
      expect(button.className).toContain('flex-1');
      expect(button.className).toContain('basis-0');
    }
    fireEvent.click(analyze);
    fireEvent.click(next);
    expect(onAnalyzeClick).toHaveBeenCalledTimes(1);
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('the desktop footer without an Analyze target is Next alone', () => {
    render(
      <MemoryRouter>
        <TrainRevealFooter onNext={vi.fn()} analyzeTo={null} onAnalyzeClick={vi.fn()} />
      </MemoryRouter>,
    );
    expect(screen.queryByTestId('btn-train-analyze')).toBeNull();
    expect(screen.getByTestId('train-reveal-actions-footer').children).toHaveLength(1);
  });
});
