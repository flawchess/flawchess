// @vitest-environment jsdom
/**
 * ExplainBar component coverage: states, static copy, the single button, the three
 * placements and the absence of in-component analytics (tracking lives in useExplainBar).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { ExplainBar } from '../ExplainBar';
import type { ExplainBarState } from '@/lib/explainBar';

let track: ReturnType<typeof vi.fn>;

beforeEach(() => {
  track = vi.fn();
  window.umami = { track, identify: vi.fn() };
});

afterEach(() => {
  cleanup();
  delete window.umami;
});

const EXPLAIN_BLUNDER: ExplainBarState = {
  kind: 'explain',
  flaw: { ply: 2, orientation: 'missed' },
  san: 'Qh5',
  severity: 'blunder',
  tactics: [],
  pending: false,
};

const CHIP = {
  onTacticClick: vi.fn(),
  activePvKeys: new Set<string>(),
  pvFetchPending: false,
  pvFetchError: false,
};

function renderBar(
  state: ExplainBarState,
  placement: 'desktop' | 'mid' | 'mobile' = 'desktop',
): { onExplain: ReturnType<typeof vi.fn>; onGotIt: ReturnType<typeof vi.fn> } {
  const onExplain = vi.fn();
  const onGotIt = vi.fn();
  render(<ExplainBar state={state} onExplain={onExplain} onGotIt={onGotIt} placement={placement} {...CHIP} />);
  return { onExplain, onGotIt };
}

describe('ExplainBar states and copy', () => {
  it('renders nothing for hidden', () => {
    renderBar({ kind: 'hidden' });
    expect(screen.queryByTestId('analysis-explain-bar')).toBeNull();
  });

  it('explain with a SAN: headline names the move and severity, one Explain button', () => {
    renderBar(EXPLAIN_BLUNDER);
    const bar = screen.getByTestId('analysis-explain-bar');
    expect(bar.getAttribute('data-state')).toBe('explain');
    expect(bar.getAttribute('data-orientation')).toBe('missed');
    expect(within(bar).getByTestId('analysis-explain-headline').textContent).toBe('Qh5?? is a blunder');
    const buttons = within(bar).getAllByRole('button');
    expect(buttons).toHaveLength(1);
    expect(buttons[0]).toBe(within(bar).getByTestId('btn-analysis-explain'));
    expect(buttons[0]?.textContent).toBe('Explain');
  });

  it('explain with tactics: long-label badges for both orientations, click opens that line', () => {
    const onTacticClick = vi.fn();
    render(
      <ExplainBar
        state={{
          ...EXPLAIN_BLUNDER,
          tactics: [
            { orientation: 'missed', motif: 'fork', depth: 0 },
            { orientation: 'allowed', motif: 'back-rank-mate', depth: 2 },
          ],
        }}
        onExplain={vi.fn()}
        onGotIt={vi.fn()}
        placement="desktop"
        {...CHIP}
        onTacticClick={onTacticClick}
      />,
    );
    expect(screen.getByTestId('analysis-explain-headline').textContent).toBe(
      'Qh5??:missed fork in 1allowed checkmate in 3',
    );
    fireEvent.click(screen.getByTestId('btn-analysis-explain-tactic-allowed'));
    expect(onTacticClick).toHaveBeenCalledWith({ ply: 2, orientation: 'allowed' });
    expect(screen.getByTestId('btn-analysis-explain-tactic-missed').textContent).toBe('missed fork in 1');
  });

  it('explain without a SAN falls back to the severity noun', () => {
    renderBar({ ...EXPLAIN_BLUNDER, san: null, severity: 'mistake' });
    expect(screen.getByTestId('analysis-explain-headline').textContent).toBe('? Mistake');
  });

  it('explain pending disables the button and sets aria-busy', () => {
    renderBar({ ...EXPLAIN_BLUNDER, pending: true });
    const button = screen.getByTestId('btn-analysis-explain') as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.getAttribute('aria-busy')).toBe('true');
  });

  it('got-it copy per orientation, with and without a SAN', () => {
    const { rerender } = render(
      <ExplainBar
        state={{ kind: 'got-it', line: { rootNodeId: 5, ply: 2, orientation: 'missed' }, san: 'Qh5' }}
        onExplain={vi.fn()}
        onGotIt={vi.fn()}
        placement="desktop"
        {...CHIP}
      />,
    );
    expect(screen.getByTestId('analysis-explain-headline').textContent).toBe('Better than Qh5');

    rerender(
      <ExplainBar
        state={{ kind: 'got-it', line: { rootNodeId: 5, ply: 3, orientation: 'allowed' }, san: 'Nc6' }}
        onExplain={vi.fn()}
        onGotIt={vi.fn()}
        placement="desktop"
        {...CHIP}
      />,
    );
    expect(screen.getByTestId('analysis-explain-headline').textContent).toBe('Punishing Nc6');

    rerender(
      <ExplainBar
        state={{ kind: 'got-it', line: { rootNodeId: 5, ply: 2, orientation: 'missed' }, san: null }}
        onExplain={vi.fn()}
        onGotIt={vi.fn()}
        placement="desktop"
        {...CHIP}
      />,
    );
    expect(screen.getByTestId('analysis-explain-headline').textContent).toBe('Better line');

    rerender(
      <ExplainBar
        state={{ kind: 'got-it', line: { rootNodeId: 5, ply: 3, orientation: 'allowed' }, san: null }}
        onExplain={vi.fn()}
        onGotIt={vi.fn()}
        placement="desktop"
        {...CHIP}
      />,
    );
    expect(screen.getByTestId('analysis-explain-headline').textContent).toBe('Refutation');
    const bar = screen.getByTestId('analysis-explain-bar');
    expect(bar.getAttribute('data-state')).toBe('got-it');
    expect(within(bar).getAllByRole('button')).toHaveLength(1);
    expect(within(bar).getByTestId('btn-analysis-explain-got-it').textContent).toBe('Got it');
  });
});

describe('ExplainBar handlers', () => {
  it('Explain click calls onExplain once and sends no analytics itself', () => {
    const { onExplain, onGotIt } = renderBar(EXPLAIN_BLUNDER);
    fireEvent.click(screen.getByTestId('btn-analysis-explain'));
    expect(onExplain).toHaveBeenCalledTimes(1);
    expect(onGotIt).not.toHaveBeenCalled();
    expect(track).not.toHaveBeenCalled();
  });

  it('Got it click calls onGotIt once and sends no analytics itself', () => {
    const { onExplain, onGotIt } = renderBar({
      kind: 'got-it',
      line: { rootNodeId: 5, ply: 2, orientation: 'missed' },
      san: 'Qh5',
    });
    fireEvent.click(screen.getByTestId('btn-analysis-explain-got-it'));
    expect(onGotIt).toHaveBeenCalledTimes(1);
    expect(onExplain).not.toHaveBeenCalled();
    expect(track).not.toHaveBeenCalled();
  });
});

describe('ExplainBar placements', () => {
  it('desktop: a plain footer row (border-t), not a Card', () => {
    renderBar(EXPLAIN_BLUNDER, 'desktop');
    const bar = screen.getByTestId('analysis-explain-bar');
    expect(bar.getAttribute('data-placement')).toBe('desktop');
    expect(bar.className).toContain('border-t');
    expect(bar.className).not.toContain('charcoal-texture');
  });

  it('mid: the root is a charcoal Card', () => {
    renderBar(EXPLAIN_BLUNDER, 'mid');
    const bar = screen.getByTestId('analysis-explain-bar');
    expect(bar.getAttribute('data-placement')).toBe('mid');
    expect(bar.className).toContain('charcoal-texture');
  });

  it('mobile: a bg-background row mirroring the mobile footer', () => {
    renderBar(EXPLAIN_BLUNDER, 'mobile');
    const bar = screen.getByTestId('analysis-explain-bar');
    expect(bar.getAttribute('data-placement')).toBe('mobile');
    expect(bar.className).toContain('bg-background');
    expect(bar.className).not.toContain('charcoal-texture');
  });
});
