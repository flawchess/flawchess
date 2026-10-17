// @vitest-environment jsdom
/**
 * The Clock by game phase 3x3 heatmap (cells in order,
 * gap-bar colour rule, empty cell, popover trigger and body, legend). A banded cell is
 * coloured only when its gap is outside the band AND significant; the zoneless
 * low-clock opening cell on significance alone. jsdom does not reliably keep color-mix(),
 * so the tint is asserted through the data-tint attribute; the colour strings are covered
 * by the pure gapHeatmapFill tests.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { TempoPhaseHeatmap } from '../TempoPhaseHeatmap';
import { GAP_HEATMAP_TINT_MIN_PERCENT } from '@/lib/theme';
import { makeTcEntry } from './flawStatsFixtures';

afterEach(cleanup);

const BIG_GAP = 2.0;

const ENTRY = makeTcEntry('rapid', {
  analyzedN: 1841,
  tempoPhase: {
    // Significant gap INSIDE its band: the contradiction case, must render neutral.
    'hasty:opening': {
      delta: 0.08,
      ci_low: 0.03,
      ci_high: 0.13,
      p_value: 0.001,
      significant: true,
      has_zone: true,
      zone_lo: -0.11,
      zone_hi: 0.11,
    },
    // Significant gap far outside its band.
    'hasty:middlegame': {
      delta: 1.2,
      ci_low: 0.6,
      ci_high: 1.8,
      significant: true,
      has_zone: true,
      zone_lo: -0.13,
      zone_hi: 0.13,
    },
    // Significant gap just outside its band (fewer flaws).
    'unrushed:middlegame': {
      delta: -0.3,
      ci_low: -0.4,
      ci_high: -0.2,
      significant: true,
      has_zone: true,
      zone_lo: -0.25,
      zone_hi: 0.25,
    },
    // Out-of-band but not significant: could be chance, neutral.
    'unrushed:endgame_phase': {
      delta: BIG_GAP,
      significant: false,
      has_zone: true,
      zone_lo: -0.1,
      zone_hi: 0.1,
    },
    // Zoneless, significant: judged on significance alone.
    'low_clock:opening': { delta: -1.2, ci_low: -1.8, ci_high: -0.6, significant: true },
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
      'tempo-phase-cell-unrushed-opening',
      'tempo-phase-cell-hasty-opening',
      'tempo-phase-cell-low-clock-opening',
      'tempo-phase-cell-unrushed-middlegame',
      'tempo-phase-cell-hasty-middlegame',
      'tempo-phase-cell-low-clock-middlegame',
      'tempo-phase-cell-unrushed-endgame-phase',
      'tempo-phase-cell-hasty-endgame-phase',
      'tempo-phase-cell-low-clock-endgame-phase',
    ]);
    const card = text('tempo-phase-card');
    for (const label of ['Unrushed', 'Hasty', 'Low-clock', 'Opening', 'Middlegame', 'Endgame']) {
      expect(card).toContain(label);
    }
  });

  it('renders a significant gap INSIDE its band neutral and keeps the words', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    const inBand = cellEl('hasty', 'opening');
    expect(inBand.getAttribute('data-tint')).toBe('neutral');
    expect(text('tempo-phase-cell-hasty-opening-words')).toBe('0.08 more');
  });

  it('colours a significant out-of-band gap like the gap bars', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    expect(cellEl('hasty', 'middlegame').getAttribute('data-tint')).toBe('worse');
    expect(cellEl('unrushed', 'middlegame').getAttribute('data-tint')).toBe('better');
  });

  it('tints further beyond the band stronger, and neutral cells read percent 0', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    const percent = (tempo: string, phase: string): number =>
      Number(cellEl(tempo, phase).getAttribute('data-tint-percent'));
    expect(percent('hasty', 'middlegame')).toBeGreaterThan(percent('unrushed', 'middlegame'));
    expect(percent('unrushed', 'middlegame')).toBeGreaterThanOrEqual(GAP_HEATMAP_TINT_MIN_PERCENT);
    expect(percent('hasty', 'opening')).toBe(0);
    expect(percent('unrushed', 'endgame-phase')).toBe(0);
    expect(percent('low-clock', 'endgame-phase')).toBe(0);
  });

  it('keeps an out-of-band gap that is not significant neutral', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    const neutral = cellEl('unrushed', 'endgame-phase');
    expect(neutral.getAttribute('data-tint')).toBe('neutral');
    expect(text('tempo-phase-cell-unrushed-endgame-phase-words')).toBe('2.0 more');
  });

  it('judges the zoneless low-clock opening cell on significance alone', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    expect(cellEl('low-clock', 'opening').getAttribute('data-tint')).toBe('better');
  });

  it('shows the empty copy and no popover trigger for a null-delta cell', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    expect(text('tempo-phase-cell-low-clock-endgame-phase-words')).toBe('No flaws');
    expect(cellEl('low-clock', 'endgame-phase').getAttribute('data-tint')).toBe('neutral');
    expect(
      screen.queryByTestId('gap-popover-tempo-phase-low-clock-endgame-phase-tc-rapid'),
    ).toBeNull();
  });

  it('opens a banded cell popover with the typical range and the verdict', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    const id = 'gap-popover-tempo-phase-hasty-middlegame-tc-rapid';
    fireEvent.click(screen.getByTestId(id));
    const body = text(`${id}-popover`);
    expect(body).toContain('Hasty, middlegame');
    expect(body).toContain('Flaws played fast while you still had time, in the middlegame');
    expect(body).toContain('hasty middlegame flaws');
    expect(body).toContain('Typical gap for players at your level');
    expect(body).toContain('You are worse than typical.');
    expect(body).not.toContain('no typical range');
    expect(body).not.toContain('for this tactic');
  });

  it('keeps the zoneless popover copy for the low-clock opening cell', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    const id = 'gap-popover-tempo-phase-low-clock-opening-tc-rapid';
    fireEvent.click(screen.getByTestId(id));
    expect(text(`${id}-popover`)).toContain('There is no typical range for this combination');
  });

  it('renders the legend line', () => {
    render(<TempoPhaseHeatmap tcStats={ENTRY} />);
    expect(text('tempo-phase-legend')).toContain('typical for your level or no clear difference');
  });
});
