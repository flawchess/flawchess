// @vitest-environment jsdom
/**
 * ExplainBar component coverage: states, static copy, the Best / Punish buttons, the
 * line stepper, the three placements and the absence of in-component analytics (tracking
 * lives in useExplainBar).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { ExplainBar } from '../ExplainBar';
import type { ExplainBarState } from '@/lib/explainBar';
import { TAC_ALLOWED, TAC_MISSED } from '@/lib/theme';
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
  headline: null,
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
    />,
  );
  return { onOpenLine, onGotIt, stepper };
}

describe('ExplainBar explain state', () => {
  it('renders nothing for hidden', () => {
    renderBar({ kind: 'hidden' });
    expect(screen.queryByTestId('analysis-explain-bar')).toBeNull();
  });

  it('headline shows the move, then its severity icon, then Best and Punish in that order', () => {
    renderBar(EXPLAIN_BLUNDER);
    const bar = screen.getByTestId('analysis-explain-bar');
    expect(bar.getAttribute('data-state')).toBe('explain');
    const headline = within(bar).getByTestId('analysis-explain-headline');
    expect(headline.getAttribute('data-severity')).toBe('blunder');
    expect(headline.querySelector('svg')).not.toBeNull();
    expect(within(bar).getByTestId('analysis-explain-headline-text').textContent).toBe('Qh5');
    const buttons = within(bar).getAllByRole('button');
    expect(buttons.map((b) => b.getAttribute('data-testid'))).toEqual([
      'btn-analysis-explain-best',
      'btn-analysis-explain-punish',
    ]);
    expect(within(bar).getByRole('button', { name: 'Best' })).toBe(buttons[0]);
    expect(within(bar).getByRole('button', { name: 'Punish' })).toBe(buttons[1]);
    expect(buttons[0]?.querySelector('svg')).not.toBeNull();
    // No tactics: no colon, no tactic text.
    expect(within(bar).queryByTestId('analysis-explain-tactics')).toBeNull();
    expect(headline.textContent).toBe('Qh5??');
  });

  it('tactics render as colored text after the move and badge, not as buttons', () => {
    renderBar({
      ...EXPLAIN_BLUNDER,
      san: 'c3',
      tactics: [
        { orientation: 'missed', text: 'missed discovered-attack in 2' },
        { orientation: 'allowed', text: 'allowed fork in 1' },
      ],
    });
    const headline = screen.getByTestId('analysis-explain-headline');
    const tactics = screen.getByTestId('analysis-explain-tactics');
    expect(headline.lastElementChild).toBe(tactics);
    // One inline flow: the tactics continue the move's line and the whole headline clamps to two lines.
    expect(headline.textContent).toBe('c3??: missed discovered-attack in 2, allowed fork in 1');
    expect(headline.className).toContain('line-clamp-2');
    // jsdom normalizes the oklch string, so compare against a probe styled the same way.
    const colorOf = (c: string): string => {
      const probe = document.createElement('span');
      probe.style.color = c;
      return probe.style.color;
    };
    const missed = tactics.querySelector<HTMLElement>('[data-orientation="missed"]');
    const allowed = tactics.querySelector<HTMLElement>('[data-orientation="allowed"]');
    expect(missed?.style.color).toBe(colorOf(TAC_MISSED));
    expect(allowed?.style.color).toBe(colorOf(TAC_ALLOWED));
    expect(within(tactics).queryAllByRole('button')).toHaveLength(0);
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

  it('without a SAN the headline falls back to the severity noun', () => {
    renderBar({ ...EXPLAIN_BLUNDER, san: null, severity: 'mistake' });
    expect(screen.getByTestId('analysis-explain-headline').getAttribute('data-severity')).toBe('mistake');
    expect(screen.getByTestId('analysis-explain-headline-text').textContent).toBe('Mistake');
  });
});

describe('ExplainBar got-it state', () => {
  it('keeps the headline with its tactic text, then the stepper and Got it', () => {
    renderBar({
      ...GOT_IT_MISSED,
      headline: { san: 'c3', severity: 'blunder', tactics: [{ orientation: 'missed', text: 'missed fork in 2' }] },
    });
    const bar = screen.getByTestId('analysis-explain-bar');
    const headline = within(bar).getByTestId('analysis-explain-headline');
    expect(headline.textContent).toBe('c3??: missed fork in 2');
    expect(bar.firstElementChild).toBe(headline);
    expect(within(bar).getAllByRole('button').map((b) => b.getAttribute('data-testid'))).toEqual([
      'btn-analysis-explain-line-back',
      'btn-analysis-explain-line-forward',
      'btn-analysis-explain-got-it',
    ]);
  });

  it('without a headline shows only the line stepper and Got it, no line buttons', () => {
    renderBar(GOT_IT_MISSED);
    const bar = screen.getByTestId('analysis-explain-bar');
    expect(bar.getAttribute('data-state')).toBe('got-it');
    expect(bar.getAttribute('data-orientation')).toBe('missed');
    expect(within(bar).queryByTestId('analysis-explain-headline')).toBeNull();
    expect(within(bar).getAllByRole('button').map((b) => b.getAttribute('data-testid'))).toEqual([
      'btn-analysis-explain-line-back',
      'btn-analysis-explain-line-forward',
      'btn-analysis-explain-got-it',
    ]);
  });

  it('a Punish line hides Best too', () => {
    renderBar({ ...GOT_IT_MISSED, line: { rootNodeId: 5, ply: 3, orientation: 'allowed' } });
    expect(screen.queryByTestId('btn-analysis-explain-best')).toBeNull();
    expect(screen.queryByTestId('btn-analysis-explain-punish')).toBeNull();
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

  it('Got it calls its handler and sends no analytics itself', () => {
    const { onGotIt } = renderBar(GOT_IT_MISSED);
    fireEvent.click(screen.getByTestId('btn-analysis-explain-got-it'));
    expect(onGotIt).toHaveBeenCalledTimes(1);
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
