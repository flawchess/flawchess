// @vitest-environment jsdom
/**
 * TrainLineChips tests (Phase 237 Plan 04): every chip state the old line cards
 * carried (mark, SAN, eval, Phase 236 loading/failed, SAN-only game move) plus
 * the D-02 merged labels. ChipGroup fixtures are built directly.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';

import { TrainLineChips } from '@/components/train/TrainLineChips';
import type { ChipGroup, RoleKey } from '@/lib/trainRevealLines';

afterEach(() => {
  cleanup();
});

function chip(overrides: Partial<ChipGroup> & { key: RoleKey }): ChipGroup {
  const label = overrides.label ?? { your: 'Move', best: 'Best', game: 'Game' }[overrides.key];
  return {
    roles: [overrides.key],
    uci: 'e2e4',
    san: 'e4',
    label,
    line: { moves: ['e2e4', 'e7e5'], evalCp: 120, evalMate: null },
    lineUcis: ['e2e4', 'e7e5'],
    pending: null,
    quality: 'good',
    ...overrides,
  };
}

const THREE: ChipGroup[] = [
  chip({ key: 'your', uci: 'e2e4', san: 'e4', quality: 'inaccuracy' }),
  chip({
    key: 'best',
    uci: 'd2d4',
    san: 'd4',
    quality: 'best',
    line: { moves: ['d2d4'], evalCp: -40, evalMate: null },
  }),
  chip({
    key: 'game',
    uci: 'c2c4',
    san: 'c4',
    quality: 'blunder',
    line: { moves: ['c2c4'], evalCp: null, evalMate: 3 },
  }),
];

function renderChips(chips: readonly ChipGroup[], extra: Partial<Parameters<typeof TrainLineChips>[0]> = {}) {
  const onSelect = vi.fn();
  render(
    <TrainLineChips
      chips={chips}
      activeChip="your"
      onSelect={onSelect}
      sanOnlyGameMove={null}
      {...extra}
    />,
  );
  return onSelect;
}

describe('TrainLineChips', () => {
  it('renders three chips in your/best/game order with label, SAN, eval and quality mark', () => {
    renderChips(THREE);
    const buttons = within(screen.getByTestId('train-line-chips')).getAllByRole('button');
    expect(buttons.map((b) => b.getAttribute('data-testid'))).toEqual([
      'train-chip-your',
      'train-chip-best',
      'train-chip-game',
    ]);
    expect(screen.getByTestId('train-chip-your-label').textContent).toBe('Move');
    expect(screen.getByTestId('train-chip-best-san').textContent).toBe('d4');
    expect(screen.getByTestId('train-chip-your-eval').textContent).toBe('+1.2');
    expect(screen.getByTestId('train-chip-best-eval').textContent).toBe('-0.4');
    expect(screen.getByTestId('train-chip-game-eval').textContent).toBe('#+3');
    expect(screen.getByTestId('train-chip-best-quality').getAttribute('data-quality')).toBe('best');
    expect(screen.getByTestId('train-chip-game-quality').getAttribute('data-quality')).toBe('blunder');
  });

  it('hides the eval pill for an eval-less stand-in line instead of a permanent "…" (WR-01)', () => {
    renderChips([chip({ key: 'your', line: { moves: [], evalCp: null, evalMate: null } })]);
    expect(screen.getByTestId('train-chip-your')).toBeTruthy();
    expect(screen.queryByTestId('train-chip-your-eval')).toBeNull();
  });

  it('a merged your + best chip renders ONE button labelled "Move = Best" (D-02)', () => {
    renderChips([chip({ key: 'your', roles: ['your', 'best'], label: 'Move = Best', quality: 'best' })]);
    const buttons = within(screen.getByTestId('train-line-chips')).getAllByRole('button');
    expect(buttons).toHaveLength(1);
    expect(screen.getByTestId('train-chip-your-label').textContent).toBe('Move = Best');
    expect(buttons[0]?.getAttribute('data-roles')).toBe('your best');
  });

  it('a merged your + game chip renders "Move = Game" (D-02)', () => {
    renderChips([
      chip({ key: 'your', roles: ['your', 'game'], label: 'Move = Game' }),
      chip({ key: 'best', uci: 'd2d4', san: 'd4' }),
    ]);
    expect(screen.getByTestId('train-chip-your-label').textContent).toBe('Move = Game');
    expect(screen.getByTestId('train-chip-best-label').textContent).toBe('Best');
    expect(screen.queryByTestId('train-chip-game')).toBeNull();
  });

  it('only the active chip is pressed and active', () => {
    renderChips(THREE, { activeChip: 'best' });
    expect(screen.getByTestId('train-chip-best').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('train-chip-best').getAttribute('data-active')).toBe('true');
    expect(screen.getByTestId('train-chip-your').getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByTestId('train-chip-game').getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByTestId('train-chip-best').className).toContain('ring-brand-brown');
    expect(screen.getByTestId('train-chip-your').className).not.toContain('ring-brand-brown');
  });

  it('no chip is pressed when none is active (D-04)', () => {
    renderChips(THREE, { activeChip: null });
    for (const key of ['your', 'best', 'game']) {
      expect(screen.getByTestId(`train-chip-${key}`).getAttribute('aria-pressed')).toBe('false');
    }
  });

  it('clicking a chip calls onSelect with its key exactly once', () => {
    const onSelect = renderChips(THREE);
    fireEvent.click(screen.getByTestId('train-chip-game'));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith('game');
  });

  it('a loading chip shows a spinner instead of an eval (Phase 236 D-14)', () => {
    renderChips([chip({ key: 'your', pending: 'loading', line: null, lineUcis: ['e2e4'] })]);
    const button = screen.getByTestId('train-chip-your');
    expect(button.getAttribute('data-line-status')).toBe('loading');
    expect(screen.getByTestId('train-chip-your-loading')).not.toBeNull();
    expect(screen.queryByTestId('train-chip-your-eval')).toBeNull();
    expect(screen.getByTestId('train-chip-your-san').textContent).toBe('e4');
  });

  it('a failed chip keeps SAN and mark but renders no eval and no spinner (Phase 236 D-15)', () => {
    renderChips([chip({ key: 'your', pending: 'failed', line: null, lineUcis: ['e2e4'] })]);
    expect(screen.getByTestId('train-chip-your').getAttribute('data-line-status')).toBe('failed');
    expect(screen.getByTestId('train-chip-your-san').textContent).toBe('e4');
    expect(screen.getByTestId('train-chip-your-quality')).not.toBeNull();
    expect(screen.queryByTestId('train-chip-your-eval')).toBeNull();
    expect(screen.queryByTestId('train-chip-your-loading')).toBeNull();
  });

  it('a ready chip carries no data-line-status', () => {
    renderChips(THREE);
    expect(screen.getByTestId('train-chip-your').hasAttribute('data-line-status')).toBe(false);
  });

  it('a SAN-only game move renders a non-interactive Game chip', () => {
    renderChips([THREE[0]!, THREE[1]!], { sanOnlyGameMove: 'Nc3' });
    const gameChip = screen.getByTestId('train-chip-game');
    expect(gameChip.getAttribute('data-interactive')).toBe('false');
    expect(gameChip.tagName).not.toBe('BUTTON');
    expect(within(gameChip).queryByRole('button')).toBeNull();
    expect(gameChip.textContent).toContain('Game');
    expect(gameChip.textContent).toContain('Nc3');
  });

  it('a played inaccuracy shows the inaccuracy mark', () => {
    renderChips([chip({ key: 'your', quality: 'inaccuracy' })]);
    expect(screen.getByTestId('train-chip-your-quality').getAttribute('data-quality')).toBe('inaccuracy');
  });

  // Phase 237 UAT: the row itself never carries a ring (the tour used to ring it).
  it('the row root never carries a ring', () => {
    renderChips(THREE);
    expect(screen.getByTestId('train-line-chips').className).not.toContain('ring-');
  });
});
