// @vitest-environment jsdom
/**
 * Phase 238 validation rows D-00e / D-05: the Endgame Type Breakdown table shows a
 * grey typical range with a colored "you" dot per conversion / recovery / vs.-engine
 * cell, red below and green above the range, faded low-sample rows, stacked rows on mobile.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { TooltipProvider } from '@/components/ui/tooltip';
import { PER_CLASS_TC_GAUGE_ZONES } from '@/generated/endgameZones';
import {
  GAUGE_NEUTRAL,
  TYPICAL_ABOVE_VALUE,
  TYPICAL_BELOW_VALUE,
  ZONE_DANGER,
  ZONE_SUCCESS,
} from '@/lib/theme';
import type { EndgameCategoryStats, EndgameClass } from '@/types/endgames';
import { buildRankedTc } from './rankedFixtures';

type TableModule = typeof import('./TypeTable');
let TypeTable: TableModule['TypeTable'];

beforeEach(async () => {
  // The TC selection is module-level state: load a fresh copy per test.
  vi.resetModules();
  localStorage.clear();
  ({ TypeTable } = await import('./TypeTable'));
});

afterEach(cleanup);

interface CategoryOptions {
  total?: number;
  conversionPct?: number;
  recoveryPct?: number;
  conversionGames?: number;
  gap?: number | null;
  /** D-14 gate for every cell of the row; true by default so out-of-band cells colour. */
  significant?: boolean;
}

function buildCategory(
  endgameClass: EndgameClass,
  label: string,
  options: CategoryOptions = {},
): EndgameCategoryStats {
  const total = options.total ?? 200;
  const wins = Math.round(total * 0.5);
  const draws = Math.round(total * 0.1);
  const losses = total - wins - draws;
  const gap = options.gap === undefined ? 0.01 : options.gap;
  return {
    endgame_class: endgameClass,
    label,
    wins,
    draws,
    losses,
    total,
    win_pct: (wins / total) * 100,
    draw_pct: (draws / total) * 100,
    loss_pct: (losses / total) * 100,
    conversion: {
      conversion_pct: options.conversionPct ?? 75,
      conversion_games: options.conversionGames ?? 60,
      conversion_wins: 45,
      conversion_draws: 5,
      conversion_losses: 10,
      recovery_pct: options.recoveryPct ?? 22,
      recovery_games: 40,
      recovery_saves: 9,
      recovery_wins: 4,
      recovery_draws: 5,
    },
    score_p_value: 0.4,
    type_achievable_score_gap_mean: gap,
    type_achievable_score_gap_n: gap === null ? 0 : 50,
    type_achievable_score_gap_p_value: 0.3,
    type_achievable_score_gap_ci_low: -0.02,
    type_achievable_score_gap_ci_high: 0.04,
    conversion_significant: options.significant ?? true,
    recovery_significant: options.significant ?? true,
    type_achievable_score_gap_significant: options.significant ?? true,
    type_achievable_score_start_mean: 0.5,
    type_achievable_score_end_mean: 0.51,
    score: (wins + draws / 2) / total,
    confidence: 'high',
    p_value: 0.4,
    ci_low: 0.4,
    ci_high: 0.6,
    eval_n: 50,
    eval_confidence: 'high',
    eval_baseline_pawns: 0,
  };
}

const RAPID_WITH_TYPES = buildRankedTc('rapid', {
  ranked_games: 600,
  type_categories: [
    buildCategory('rook', 'Rook'),
    buildCategory('minor_piece', 'Minor Piece', { total: 40 }),
    buildCategory('pawn', 'Pawn'),
    buildCategory('queen', 'Queen'),
  ],
});

function renderTable(
  tcs = [RAPID_WITH_TYPES],
  onCategorySelect: (category: EndgameClass) => void = vi.fn(),
) {
  return render(
    <MemoryRouter>
      <TooltipProvider>
        <TypeTable tcs={tcs} onCategorySelect={onCategorySelect} />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

function byId(root: HTMLElement, testId: string): HTMLElement {
  const element = root.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
  expect(element, `element ${testId} present`).not.toBeNull();
  return element as HTMLElement;
}

function queryId(root: HTMLElement, testId: string): HTMLElement | null {
  return root.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
}

/** jsdom normalizes oklch strings; compare through a reference element. */
function normalizedColor(color: string): string {
  const reference = document.createElement('div');
  reference.style.color = color;
  return reference.style.color;
}

const ROOK_RAPID = PER_CLASS_TC_GAUGE_ZONES.rook.rapid;
// Conversion cell domain 0.4-1.0 (D-00e): band [0.69, 0.83] -> left 48.33%, width 23.33%.
const CONVERSION_DOMAIN_MIN = 0.4;
const CONVERSION_DOMAIN_SPAN = 0.6;

describe('TypeTable rows', () => {
  it('renders one row per endgame type with its name and game count', () => {
    const { container } = renderTable();
    for (const [cls, name] of [
      ['rook', 'Rook'],
      ['minor_piece', 'Minor Piece'],
      ['pawn', 'Pawn'],
      ['queen', 'Queen'],
    ] as const) {
      expect(byId(container, `type-row-${cls}`).textContent).toContain(name);
    }
    expect(byId(container, 'type-row-rook-games-link').textContent).toContain('200 games');
  });

  it('skips the hidden pawnless class', () => {
    const tc = buildRankedTc('rapid', {
      type_categories: [buildCategory('rook', 'Rook'), buildCategory('pawnless', 'Pawnless')],
    });
    const { container } = renderTable([tc]);
    expect(queryId(container, 'type-row-pawnless')).toBeNull();
    expect(queryId(container, 'type-row-rook')).not.toBeNull();
  });

  it('shows the empty branch instead of a table when there are no type rows', () => {
    const tc = buildRankedTc('rapid', { type_categories: [] });
    const { container } = renderTable([tc]);
    expect(queryId(container, 'endgame-type-breakdown-empty')).not.toBeNull();
    expect(container.querySelector('table')).toBeNull();
  });

  it('keeps the section testid, accessible name and info popover', () => {
    const { container } = renderTable();
    const section = queryId(container, 'endgame-type-breakdown-section');
    expect(section).not.toBeNull();
    // aria-label, not aria-labelledby: the tab double-mounts, so a fixed heading id would repeat.
    expect(section?.getAttribute('aria-label')).toBe('Endgame Type Breakdown');
    expect(container.querySelector('[id="endgame-type-breakdown-heading"]')).toBeNull();
    expect(queryId(container, 'endgame-type-breakdown-info')).not.toBeNull();
  });
});

describe('TypeTable typical-range cells', () => {
  it('places the grey band from PER_CLASS_TC_GAUGE_ZONES for the selected TC', () => {
    const { container } = renderTable();
    const [lo, hi] = ROOK_RAPID.conversion;
    const band = byId(container, 'type-row-rook-conversion-band');
    expect(parseFloat(band.style.left)).toBeCloseTo(
      ((lo - CONVERSION_DOMAIN_MIN) / CONVERSION_DOMAIN_SPAN) * 100,
      1,
    );
    expect(parseFloat(band.style.width)).toBeCloseTo(
      ((hi - lo) / CONVERSION_DOMAIN_SPAN) * 100,
      1,
    );
  });

  it('places the dot at the user value', () => {
    const { container } = renderTable();
    // Rook conversion 75% on the 0.4-1.0 domain.
    const dot = byId(container, 'type-row-rook-conversion-dot');
    expect(parseFloat(dot.style.left)).toBeCloseTo(((0.75 - 0.4) / 0.6) * 100, 1);
  });

  it('clamps the dot into the cell domain', () => {
    const tc = buildRankedTc('rapid', {
      type_categories: [
        buildCategory('rook', 'Rook', { conversionPct: 10, recoveryPct: 99 }),
      ],
    });
    const { container } = renderTable([tc]);
    expect(parseFloat(byId(container, 'type-row-rook-conversion-dot').style.left)).toBe(0);
    expect(parseFloat(byId(container, 'type-row-rook-recovery-dot').style.left)).toBe(100);
  });

  it('colors the value red below, green above and leaves it white inside the typical range', () => {
    const tc = buildRankedTc('rapid', {
      type_categories: [
        buildCategory('rook', 'Rook', { conversionPct: 50, recoveryPct: 22 }),
        buildCategory('pawn', 'Pawn', { conversionPct: 76, recoveryPct: 22 }),
        buildCategory('queen', 'Queen', { conversionPct: 97, recoveryPct: 22 }),
      ],
    });
    const { container } = renderTable([tc]);
    expect(byId(container, 'type-row-rook-conversion-value').style.color).toBe(
      normalizedColor(TYPICAL_BELOW_VALUE),
    );
    // Inside the band: default foreground, no color at all.
    expect(byId(container, 'type-row-pawn-conversion-value').style.color).toBe('');
    expect(byId(container, 'type-row-queen-conversion-value').style.color).toBe(
      normalizedColor(TYPICAL_ABOVE_VALUE),
    );
    // The dot uses the Endgame Metrics percentile palette: red / blue / green.
    expect(byId(container, 'type-row-rook-conversion-dot').style.backgroundColor).toBe(
      normalizedColor(ZONE_DANGER),
    );
    expect(byId(container, 'type-row-pawn-conversion-dot').style.backgroundColor).toBe(
      normalizedColor(GAUGE_NEUTRAL),
    );
    expect(byId(container, 'type-row-queen-conversion-dot').style.backgroundColor).toBe(
      normalizedColor(ZONE_SUCCESS),
    );
  });

  it('keeps an out-of-band cell neutral when it is not significant (D-14)', () => {
    const tc = buildRankedTc('rapid', {
      type_categories: [
        buildCategory('rook', 'Rook', { conversionPct: 50, significant: false }),
      ],
    });
    const { container } = renderTable([tc]);
    expect(byId(container, 'type-row-rook-conversion-value').style.color).toBe('');
    expect(byId(container, 'type-row-rook-conversion-dot').style.backgroundColor).toBe(
      normalizedColor(GAUGE_NEUTRAL),
    );
  });

  it('shows an info popover with the endgame type description on each row', () => {
    const { container } = renderTable();
    expect(byId(container, 'type-row-rook-info').getAttribute('aria-label')).toBe('Rook info');
  });

  it('shows a dash and no dot for a cell without games', () => {
    const tc = buildRankedTc('rapid', {
      type_categories: [buildCategory('rook', 'Rook', { conversionGames: 0, gap: null })],
    });
    const { container } = renderTable([tc]);
    expect(byId(container, 'type-row-rook-conversion-value').textContent).toBe('—');
    expect(queryId(container, 'type-row-rook-conversion-dot')).toBeNull();
    expect(byId(container, 'type-row-rook-gap-value').textContent).toBe('—');
  });

  it('uses the zones of the selected TC when the switch changes', () => {
    const blitz = buildRankedTc('blitz', {
      ranked_games: 100,
      type_categories: [buildCategory('rook', 'Rook')],
    });
    const rapid = buildRankedTc('rapid', {
      ranked_games: 500,
      type_categories: [buildCategory('rook', 'Rook')],
    });
    const { container } = renderTable([blitz, rapid]);
    const rapidLeft = parseFloat(byId(container, 'type-row-rook-conversion-band').style.left);
    fireEvent.click(byId(container, 'tc-switch-type-breakdown-blitz'));
    const blitzLeft = parseFloat(byId(container, 'type-row-rook-conversion-band').style.left);
    const [rapidLo] = PER_CLASS_TC_GAUGE_ZONES.rook.rapid.conversion;
    const [blitzLo] = PER_CLASS_TC_GAUGE_ZONES.rook.blitz.conversion;
    expect(rapidLeft).toBeCloseTo(((rapidLo - 0.4) / 0.6) * 100, 1);
    expect(blitzLeft).toBeCloseTo(((blitzLo - 0.4) / 0.6) * 100, 1);
    expect(blitzLeft).not.toBeCloseTo(rapidLeft, 1);
  });
});

describe('TypeTable confidence and layout', () => {
  it('never fades a row, also with few games (D-14 replaced the fade)', () => {
    const { container } = renderTable();
    expect(byId(container, 'type-row-minor_piece').style.opacity).toBe('');
    expect(byId(container, 'type-row-rook').style.opacity).toBe('');
  });

  it('stacks on mobile: header row hidden below md, every cell carries a caption', () => {
    const { container } = renderTable();
    expect(container.querySelector('thead')?.className).toContain('max-md:hidden');
    expect(byId(container, 'type-row-rook-conversion-caption').textContent).toBe('Conversion');
    expect(byId(container, 'type-row-rook-recovery-caption').textContent).toBe('Recovery');
    expect(byId(container, 'type-row-rook-gap-caption').textContent).toBe('vs. expected');
    expect(byId(container, 'type-row-rook-score-caption').textContent).toBe('Score');
  });

  it('links each type to its games and reports the selection', () => {
    const onCategorySelect = vi.fn();
    const { container } = renderTable([RAPID_WITH_TYPES], onCategorySelect);
    const link = byId(container, 'type-row-minor_piece-games-link');
    expect(link.getAttribute('href')).toBe('/endgames/games?type=minor-piece');
    fireEvent.click(link);
    expect(onCategorySelect).toHaveBeenCalledWith('minor_piece');
  });

  it('explains the grey range, the dot and the significance-gated red/green in the legend', () => {
    const { container } = renderTable();
    const legend = byId(container, 'type-table-legend').textContent ?? '';
    expect(legend).toContain('Grey band');
    expect(legend).toContain('Dot = you');
    expect(legend).toContain('Red');
    expect(legend).toContain('green');
    expect(legend).toContain('enough games to be sure');
    expect(legend).not.toContain('Faded');
  });
});
