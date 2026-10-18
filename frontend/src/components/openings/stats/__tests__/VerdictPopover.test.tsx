// @vitest-environment jsdom
/** The End Eval verdict popover: reason sentences, greyed footer parts, no unit name. */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { OpeningVerdictReason } from '@/lib/openingVerdict';
import { EvalVerdictPopover } from '../VerdictPopover';

afterEach(cleanup);

const TRIGGER_ID = 'eval-bullet-popover-trigger';

interface Overrides {
  avgEvalPawns?: number;
  color?: 'white' | 'black';
  reason?: OpeningVerdictReason;
  ciLow?: number | null;
  ciHigh?: number | null;
  pValue?: number | null;
}

function openPopover(overrides: Overrides = {}): HTMLElement {
  render(
    <EvalVerdictPopover
      testId={TRIGGER_ID}
      label="End Eval"
      avgEvalPawns={overrides.avgEvalPawns ?? 0.41}
      evalN={230}
      color={overrides.color ?? 'white'}
      reason={overrides.reason ?? 'typical'}
      ciLow={overrides.ciLow === undefined ? 0.12 : overrides.ciLow}
      ciHigh={overrides.ciHigh === undefined ? 0.7 : overrides.ciHigh}
      pValue={overrides.pValue === undefined ? 0.004 : overrides.pValue}
    />,
  );
  fireEvent.click(screen.getByTestId(TRIGGER_ID));
  const popover = screen.queryByTestId(`${TRIGGER_ID}-popover`);
  expect(popover, 'popover open').not.toBeNull();
  return popover as HTMLElement;
}

function footer(): string {
  return screen.getByTestId(`${TRIGGER_ID}-footer`).textContent ?? '';
}

describe('EvalVerdictPopover', () => {
  it('footer carries the 95% CI, the p-value with its baseline, and n', () => {
    openPopover();
    expect(footer()).toBe('95% CI +0.12 to +0.70 · p = 0.004 vs +0.25 · n = 230');
  });

  it('omits the CI part when either bound is null and the p part when the p-value is null', () => {
    openPopover({ ciLow: null });
    expect(footer()).toBe('p = 0.004 vs +0.25 · n = 230');
    cleanup();
    openPopover({ pValue: null });
    expect(footer()).toBe('95% CI +0.12 to +0.70 · n = 230');
  });

  it('uses the Black baseline for a Black game', () => {
    openPopover({ color: 'black', avgEvalPawns: -0.1 });
    expect(footer()).toContain('vs −0.25');
  });

  it.each([
    ['chance', /could be chance/],
    ['too-few', /Too few games to call it/],
    ['typical', /That is typical/],
    ['better', /clearly better than an average White game/],
    ['worse', /clearly worse than an average White game/],
  ] as const)('says the %s reason', (reason, pattern) => {
    const popover = openPopover({ reason });
    expect(popover.textContent ?? '').toMatch(pattern);
  });

  it('shows the raw value, the distance from the colour baseline and the typical range', () => {
    const text = openPopover().textContent ?? '';
    expect(text).toContain('You: +0.41');
    expect(text).toContain('0.16 better than an average White game (+0.25)');
    expect(text).toContain('Typical: −0.05 to +0.55');
  });

  it('says "about the same" when the distance rounds to zero', () => {
    const text = openPopover({ avgEvalPawns: 0.25 }).textContent ?? '';
    expect(text).toContain('about the same as an average White game');
  });

  it('never uses the word pawns', () => {
    const text = openPopover({ reason: 'chance' }).textContent ?? '';
    expect(text).not.toMatch(/pawns/i);
  });
});
