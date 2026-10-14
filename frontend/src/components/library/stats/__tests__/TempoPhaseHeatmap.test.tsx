// @vitest-environment jsdom
/**
 * Quick 261014-pb9: the Clock by game phase 3x3 heatmap (cells in order, significance-gated
 * tint, empty cell, popover trigger and body, legend). jsdom does not reliably keep
 * color-mix(), so the tint is asserted through the data-tint attribute; the colour strings
 * are covered by the pure gapHeatmapFill tests.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { TempoPhaseHeatmap } from '../TempoPhaseHeatmap';
import { makeTcEntry } from './flawStatsFixtures';

afterEach(cleanup);

const BIG_GAP = 2.0;

const ENTRY = makeTcEntry('rapid', {
  analyzedN: 1841,
  tempoPhase: {
    'low_clock:opening': { delta: -1.2, ci_low: -1.8, ci_high: -0.6, significant: true },
    'hasty:middlegame': { delta: 1.2, ci_low: 0.6, ci_high: 1.8, significant: true },
    'unrushed:endgame_phase': { delta: BIG_GAP, significant: false },
    'low_clock:endgame_phase': {
      delta: null,
      ci_low: null,
      ci_high: null,
      player_rate: null,
      opp_rate: null,
      p_value: null,
      player_events: 0,
      opp_events: 0,
    },
  },
});

function cellEl(tempo: string, phase: string): HTMLElement {
  return screen.getByTestId(`tempo-phase-cell-${tempo}-${phase}`);
}

function text(testId: string): string {
  return screen.getByTestId(testId).textContent ?? '';
}

describe('TempoPhaseHeatmap', () => {
  it('renders the 9 cells in row-major order with the six header labels', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    const ids = Array.from(
      screen.getByTestId('tempo-phase-grid').querySelectorAll('[data-testid^="tempo-phase-cell-"]'),
    )
      .map((el) => el.getAttribute('data-testid') ?? '')
      .filter((id) => !id.endsWith('-words') && !id.includes('-popover'));
    expect(ids).toEqual([
      'tempo-phase-cell-low-clock-opening',
      'tempo-phase-cell-hasty-opening',
      'tempo-phase-cell-unrushed-opening',
      'tempo-phase-cell-low-clock-middlegame',
      'tempo-phase-cell-hasty-middlegame',
      'tempo-phase-cell-unrushed-middlegame',
      'tempo-phase-cell-low-clock-endgame-phase',
      'tempo-phase-cell-hasty-endgame-phase',
      'tempo-phase-cell-unrushed-endgame-phase',
    ]);
    const card = text('tempo-phase-card');
    for (const label of ['Low-clock', 'Hasty', 'Unrushed', 'Opening', 'Middlegame', 'Endgame']) {
      expect(card).toContain(label);
    }
  });

  it('tints only significant cells and keeps the words on a neutral big gap', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    expect(cellEl('low-clock', 'opening').getAttribute('data-tint')).toBe('better');
    expect(cellEl('hasty', 'middlegame').getAttribute('data-tint')).toBe('worse');
    const neutral = cellEl('unrushed', 'endgame-phase');
    expect(neutral.getAttribute('data-tint')).toBe('neutral');
    expect(text('tempo-phase-cell-unrushed-endgame-phase-words')).toBe('2.0 more');
  });

  it('shows the empty copy and no popover trigger for a null-delta cell', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    expect(text('tempo-phase-cell-low-clock-endgame-phase-words')).toBe('No flaws yet');
    expect(cellEl('low-clock', 'endgame-phase').getAttribute('data-tint')).toBe('neutral');
    expect(
      screen.queryByTestId('gap-popover-tempo-phase-low-clock-endgame-phase-tc-rapid'),
    ).toBeNull();
  });

  it('opens the GapPopover of a significant cell with the combined meta', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    const id = 'gap-popover-tempo-phase-hasty-middlegame-tc-rapid';
    fireEvent.click(screen.getByTestId(id));
    const body = text(`${id}-popover`);
    expect(body).toContain('Hasty, middlegame');
    expect(body).toContain('Flaws played fast while you still had time, in the middlegame');
    expect(body).toContain('hasty middlegame flaws');
    expect(body).toContain('There is no typical range for this combination');
    expect(body).not.toContain('for this tactic');
  });

  it('renders the legend line', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    expect(screen.getByTestId('tempo-phase-legend')).not.toBeNull();
  });
});
