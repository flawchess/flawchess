// @vitest-environment jsdom
/**
 * ExplainBar component coverage: states, static copy, the Best move / Punish buttons, the
 * line stepper, the three placements and the absence of in-component analytics (tracking
 * lives in useExplainBar).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { ExplainBar } from '../ExplainBar';
import type { ExplainBarState } from '@/lib/explainBar';
import type { ExplainLineStepper } from '@/hooks/analysis/useExplainBar';

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
  ply: 2,
  san: 'Qh5',
  severity: 'blunder',
  tactics: [],
  usable: { missed: true, allowed: true },
  pending: null,
};

const GOT_IT_MISSED: ExplainBarState = {
  kind: 'got-it',
  line: { rootNodeId: 5, ply: 2, orientation: 'missed' },
  tactics: [],
  otherUsable: true,
};

const CHIP = {
  onTacticClick: vi.fn(),
  activePvKeys: new Set<string>(),
  pvFetchPending: false,
  pvFetchError: false,
};

function makeStepper(overrides: Partial<ExplainLineStepper> = {}): ExplainLineStepper {
  return { canBack: true, canForward: true, onBack: vi.fn(), onForward: vi.fn(), ...overrides };
}

type Handlers = {
  onOpenLine: ReturnType<typeof vi.fn>;
  onGotIt: ReturnType<typeof vi.fn>;
  stepper: ExplainLineStepper;
};

function renderBar(
  state: ExplainBarState,
  placement: 'desktop' | 'mid' | 'mobile' = 'desktop',
  stepper: ExplainLineStepper = makeStepper(),
): Handlers {
  const onOpenLine = vi.fn();
  const onGotIt = vi.fn();
  render(
    <ExplainBar
      state={state}
      onOpenLine={onOpenLine}
      onGotIt={onGotIt}
      stepper={stepper}
      placement={placement}
      {...CHIP}
    />,
  );
  return { onOpenLine, onGotIt, stepper };
}

describe('ExplainBar explain state', () => {
  it('renders nothing for hidden', () => {
    renderBar({ kind: 'hidden' });
    expect(screen.queryByTestId('analysis-explain-bar')).toBeNull();
  });

  it('headline names the move and severity, then Best move and Punish in that order', () => {
    renderBar(EXPLAIN_BLUNDER);
    const bar = screen.getByTestId('analysis-explain-bar');
    expect(bar.getAttribute('data-state')).toBe('explain');
    expect(within(bar).getByTestId('analysis-explain-headline').textContent).toBe('Qh5?? is a blunder');
    const buttons = within(bar).getAllByRole('button');
    expect(buttons.map((b) => b.getAttribute('data-testid'))).toEqual([
      'btn-analysis-explain-best',
      'btn-analysis-explain-punish',
    ]);
    expect(buttons.map((b) => b.textContent)).toEqual(['Best move', 'Punish']);
    expect(within(bar).queryByTestId('analysis-explain-tactics')).toBeNull();
  });

  it('each button opens its line', () => {
    const { onOpenLine } = renderBar(EXPLAIN_BLUNDER);
    fireEvent.click(screen.getByTestId('btn-analysis-explain-best'));
    expect(onOpenLine).toHaveBeenLastCalledWith('missed');
    fireEvent.click(screen.getByTestId('btn-analysis-explain-punish'));
    expect(onOpenLine).toHaveBeenLastCalledWith('allowed');
    expect(track).not.toHaveBeenCalled();
  });

  it('an unusable line disables only its button', () => {
    renderBar({ ...EXPLAIN_BLUNDER, usable: { missed: false, allowed: true } });
    expect((screen.getByTestId('btn-analysis-explain-best') as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId('btn-analysis-explain-punish') as HTMLButtonElement).disabled).toBe(false);
  });

  it('pending disables both buttons and marks the pending one aria-busy', () => {
    renderBar({ ...EXPLAIN_BLUNDER, pending: 'allowed' });
    const best = screen.getByTestId('btn-analysis-explain-best') as HTMLButtonElement;
    const punish = screen.getByTestId('btn-analysis-explain-punish') as HTMLButtonElement;
    expect(best.disabled && punish.disabled).toBe(true);
    expect(punish.getAttribute('aria-busy')).toBe('true');
    expect(best.getAttribute('aria-busy')).toBeNull();
  });

  it('tactics render on a second row as long-label chips; a click opens that line', () => {
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
        onOpenLine={vi.fn()}
        onGotIt={vi.fn()}
        stepper={makeStepper()}
        placement="desktop"
        {...CHIP}
        onTacticClick={onTacticClick}
      />,
    );
    expect(screen.getByTestId('analysis-explain-headline').textContent).toBe('Qh5?? is a blunder');
    expect(screen.getByTestId('analysis-explain-tactics').textContent).toBe('missed fork in 1allowed checkmate in 3');
    fireEvent.click(screen.getByTestId('btn-analysis-explain-tactic-allowed'));
    expect(onTacticClick).toHaveBeenCalledWith({ ply: 2, orientation: 'allowed' });
  });

  it('without a SAN the headline falls back to the severity noun', () => {
    renderBar({ ...EXPLAIN_BLUNDER, san: null, severity: 'mistake' });
    expect(screen.getByTestId('analysis-explain-headline').textContent).toBe('? Mistake');
  });
});

describe('ExplainBar got-it state', () => {
  it('shows the line stepper, the sibling line button and Got it, with no headline', () => {
    renderBar(GOT_IT_MISSED);
    const bar = screen.getByTestId('analysis-explain-bar');
    expect(bar.getAttribute('data-state')).toBe('got-it');
    expect(bar.getAttribute('data-orientation')).toBe('missed');
    expect(within(bar).queryByTestId('analysis-explain-headline')).toBeNull();
    expect(within(bar).getAllByRole('button').map((b) => b.getAttribute('data-testid'))).toEqual([
      'btn-analysis-explain-line-back',
      'btn-analysis-explain-line-forward',
      'btn-analysis-explain-punish',
      'btn-analysis-explain-got-it',
    ]);
  });

  it('an allowed line offers Best move as the switch', () => {
    renderBar({ ...GOT_IT_MISSED, line: { rootNodeId: 5, ply: 3, orientation: 'allowed' } });
    expect(screen.getByTestId('btn-analysis-explain-best')).toBeTruthy();
    expect(screen.queryByTestId('btn-analysis-explain-punish')).toBeNull();
  });

  it('the switch button is disabled when the sibling line is unusable', () => {
    renderBar({ ...GOT_IT_MISSED, otherUsable: false });
    expect((screen.getByTestId('btn-analysis-explain-punish') as HTMLButtonElement).disabled).toBe(true);
  });

  it('stepper buttons call their handlers and follow canBack/canForward', () => {
    const stepper = makeStepper({ canBack: false });
    renderBar(GOT_IT_MISSED, 'desktop', stepper);
    const back = screen.getByTestId('btn-analysis-explain-line-back') as HTMLButtonElement;
    const forward = screen.getByTestId('btn-analysis-explain-line-forward') as HTMLButtonElement;
    expect(back.disabled).toBe(true);
    expect(back.getAttribute('aria-label')).toBe('Previous move in line');
    fireEvent.click(forward);
    expect(stepper.onForward).toHaveBeenCalledTimes(1);
  });

  it('Got it and the switch call their handlers and send no analytics themselves', () => {
    const { onOpenLine, onGotIt } = renderBar(GOT_IT_MISSED);
    fireEvent.click(screen.getByTestId('btn-analysis-explain-punish'));
    expect(onOpenLine).toHaveBeenCalledWith('allowed');
    fireEvent.click(screen.getByTestId('btn-analysis-explain-got-it'));
    expect(onGotIt).toHaveBeenCalledTimes(1);
    expect(track).not.toHaveBeenCalled();
  });

  it('keeps the tactic row of the line flaw', () => {
    renderBar({ ...GOT_IT_MISSED, tactics: [{ orientation: 'missed', motif: 'fork', depth: 0 }] });
    expect(screen.getByTestId('analysis-explain-tactics').textContent).toBe('missed fork in 1');
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
