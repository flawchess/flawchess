// @vitest-environment jsdom
/**
 * Phase 239 D-00a, D-00c, D-00h: the three tactic tables of the Tactic motifs section.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { GAUGE_NEUTRAL, UNRELIABLE_OPACITY } from '@/lib/theme';
import { indefiniteArticle, tacticSideCopy } from '@/lib/tacticComparisonMeta';
import { TacticTables } from '../TacticTables';
import {
  RAPID_TACTIC_ENTRY,
  SKETCH_RAPID_TACTIC_OVERRIDES,
  makeTacticTcEntry,
  type TacticOverrides,
} from './flawStatsFixtures';

const mocks = vi.hoisted(() => ({ trackFeature: vi.fn() }));

vi.mock('@/lib/analytics', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/analytics')>()),
  trackFeature: mocks.trackFeature,
}));

beforeEach(() => {
  mocks.trackFeature.mockReset();
});

afterEach(cleanup);

/** jsdom normalizes color strings; compare normalized forms. */
function normalized(color: string): string {
  const probe = document.createElement('div');
  probe.style.color = color;
  return probe.style.color;
}

function openAdvanced(): void {
  fireEvent.click(screen.getByTestId('tactic-group-advanced-trigger'));
}

function renderTables(tcStats = RAPID_TACTIC_ENTRY): void {
  render(<TacticTables tcStats={tcStats} />);
}

function text(testId: string): string {
  return screen.getByTestId(testId).textContent ?? '';
}

/** Motif names of the rows of one group card, in rendered order. */
function rowNames(groupKey: string): string[] {
  const group = screen.getByTestId(`tactic-group-${groupKey}`);
  return Array.from(group.querySelectorAll('[data-testid^="tactic-row-"]:not([data-testid$="-flaws"])')).map(
    (row) => row.firstElementChild?.firstElementChild?.textContent ?? '',
  );
}

describe('TacticTables rows (D-00h)', () => {
  it('lists the Piece Attacks families in the filter panel order', () => {
    renderTables();
    expect(rowNames('piece_attacks')).toEqual(['Fork', 'Pin', 'Hanging piece']);
  });

  it('lists the Checkmate, Checks & Discoveries families in the filter panel order', () => {
    renderTables();
    expect(rowNames('discoveries')).toEqual(['Checkmate', 'Discovered attack']);
  });

  it('never lets the payload order decide the row order', () => {
    renderTables(makeTacticTcEntry('rapid', 1841, SKETCH_RAPID_TACTIC_OVERRIDES, true));
    expect(rowNames('piece_attacks')).toEqual(['Fork', 'Pin', 'Hanging piece']);
    expect(rowNames('discoveries')).toEqual(['Checkmate', 'Discovered attack']);
  });

  it('does not re-sort the rows by rate (a busier later family stays later)', () => {
    // Hanging piece has far more flaws than Fork here; the order must still be Fork, Pin, Hanging.
    renderTables(
      makeTacticTcEntry('rapid', 1841, {
        'fork:missed': { you: 5, opp: 5 },
        'pin:missed': { you: 10, opp: 10 },
        'hanging:missed': { you: 400, opp: 100 },
      }),
    );
    expect(rowNames('piece_attacks')).toEqual(['Fork', 'Pin', 'Hanging piece']);
  });

  it('renders the groups in TACTIC_GROUPS order', () => {
    renderTables();
    const titles = screen
      .getAllByRole('heading', { level: 3 })
      .map((h) => h.textContent ?? '');
    expect(titles[0]).toBe('Piece Attacks');
    expect(titles[1]).toBe('Checkmate, Checks & Discoveries');
    expect(titles[2]).toContain('Advanced');
  });

  it('reads "N of your flaws" as missed plus allowed for the player only', () => {
    renderTables();
    expect(text('tactic-row-fork-flaws')).toBe('218 of your flaws');
  });
});

describe('TacticTables cells (D-00a, D-00b, D-00c)', () => {
  it('shows each side as a gap bar per 100 games with the gap in words', () => {
    renderTables();
    expect(text('tactic-cell-fork-missed-bar-words')).toBe('2.2 more');
    expect(text('tactic-cell-fork-allowed-bar-words')).toBe('2.5 fewer');
  });

  it('draws the band only for a banded family-side (D-11)', () => {
    renderTables();
    expect(screen.queryByTestId('tactic-cell-fork-missed-bar-band')).not.toBeNull();
    expect(screen.queryByTestId('tactic-cell-fork-allowed-bar-band')).toBeNull();
  });

  it('puts a per-side, per-TC Search popover on each non-empty cell', () => {
    renderTables();
    expect(screen.getByTestId('gap-popover-tactic-fork-missed-tc-rapid')).not.toBeNull();
    expect(screen.getByTestId('gap-popover-tactic-fork-allowed-tc-rapid')).not.toBeNull();
    expect(screen.getByTestId('gap-popover-tactic-discovered-attack-allowed-tc-rapid')).not.toBeNull();
  });

  it('words the popover per side with the per 100 games unit', () => {
    renderTables();
    fireEvent.click(screen.getByTestId('gap-popover-tactic-fork-missed-tc-rapid'));
    const missed = text('gap-popover-tactic-fork-missed-tc-rapid-popover');
    expect(missed).toContain('Missed fork');
    expect(missed).toContain('Your opponent left a fork on the board and you did not play it.');
    expect(missed).toContain('per 100 games');
    expect(missed).toContain('84 vs. 44 flaws with a missed fork');
    expect(missed).not.toMatch(/\bevents?\b/i);

    fireEvent.click(screen.getByTestId('gap-popover-tactic-hanging-allowed-tc-rapid'));
    const allowed = text('gap-popover-tactic-hanging-allowed-tc-rapid-popover');
    expect(allowed).toContain('Your move handed your opponent a hanging piece.');
  });
});

describe('tactic copy helpers', () => {
  it('uses "an" before a vowel letter and before x-', () => {
    expect(indefiniteArticle('fork')).toBe('a');
    expect(indefiniteArticle('hanging piece')).toBe('a');
    expect(indefiniteArticle('attraction')).toBe('an');
    expect(indefiniteArticle('en passant')).toBe('an');
    expect(indefiniteArticle('under-promotion')).toBe('an');
    expect(indefiniteArticle('x-ray')).toBe('an');
  });

  it('builds the per-side label, definition and noun', () => {
    expect(tacticSideCopy('X-ray', 'missed')).toEqual({
      label: 'Missed x-ray',
      definition: 'Your opponent left an x-ray on the board and you did not play it.',
      noun: 'flaws with a missed x-ray',
    });
    expect(tacticSideCopy('Fork', 'allowed')).toEqual({
      label: 'Allowed fork',
      definition: 'Your move handed your opponent a fork.',
      noun: 'flaws with an allowed fork',
    });
  });
});

describe('Advanced group (D-00i, D-00j)', () => {
  const ADVANCED_OVERRIDES: TacticOverrides = {
    'sacrifice:missed': { you: 30, opp: 20 },
    'x_ray:allowed': { you: 3, opp: 1 },
  };

  it('starts collapsed with a chevron trigger and the shared hint', () => {
    renderTables(makeTacticTcEntry('rapid', 1841, ADVANCED_OVERRIDES));
    const trigger = screen.getByTestId('tactic-group-advanced-trigger');
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
    expect(trigger.textContent).toContain('Advanced');
    expect(trigger.textContent).toContain('Click or tap for details');
    expect(trigger.querySelector('[data-slot="accordion-trigger-icon"]')).not.toBeNull();
    expect(screen.queryByTestId('tactic-row-sacrifice')).toBeNull();
    expect(screen.queryByTestId('tactic-group-advanced-header')).toBeNull();
  });

  it('opens to the table and keeps the hint hidden through the trigger state', () => {
    renderTables(makeTacticTcEntry('rapid', 1841, ADVANCED_OVERRIDES));
    openAdvanced();
    const trigger = screen.getByTestId('tactic-group-advanced-trigger');
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
    // The hint hides through the trigger's aria-expanded group variant, not by unmounting.
    const hint = screen.getByText('Click or tap for details');
    expect(hint.className).toContain('group-aria-expanded/accordion-trigger:hidden');
    expect(rowNames('advanced')).toEqual(['X-ray', 'Sacrifice']);
  });

  it('sends exactly one panel-open event per mount, however often it is toggled', () => {
    renderTables(makeTacticTcEntry('rapid', 1841, ADVANCED_OVERRIDES));
    expect(mocks.trackFeature).not.toHaveBeenCalled();
    openAdvanced();
    openAdvanced();
    openAdvanced();
    expect(mocks.trackFeature).toHaveBeenCalledTimes(1);
    expect(mocks.trackFeature).toHaveBeenCalledWith('panel-open', { target: 'tactic-advanced' });
  });

  it('keeps Piece Attacks and Checkmate, Checks & Discoveries as plain always-open cards', () => {
    renderTables();
    expect(screen.queryByTestId('tactic-group-piece_attacks-trigger')).toBeNull();
    expect(screen.queryByTestId('tactic-group-discoveries-trigger')).toBeNull();
    expect(screen.getByTestId('tactic-group-piece_attacks-header')).not.toBeNull();
    expect(screen.getByTestId('tactic-group-discoveries-header')).not.toBeNull();
    // The hint exists once: only Advanced is collapsible.
    expect(screen.getAllByText('Click or tap for details')).toHaveLength(1);
  });

  it('says "an" in the popover of an x- motif', () => {
    renderTables(makeTacticTcEntry('rapid', 1841, ADVANCED_OVERRIDES));
    openAdvanced();
    fireEvent.click(screen.getByTestId('gap-popover-tactic-x-ray-allowed-tc-rapid'));
    expect(text('gap-popover-tactic-x-ray-allowed-tc-rapid-popover')).toContain(
      'Your move handed your opponent an x-ray.',
    );
  });
});

describe('families without flaws (D-00h, D-00d)', () => {
  it('lists a family with no flaws on either side under its table, not as a row', () => {
    renderTables(
      makeTacticTcEntry('rapid', 1841, {
        'sacrifice:missed': { you: 30, opp: 20 },
        'trapped_piece:allowed': { you: 5, opp: 5 },
        'deflection:missed': { you: 5, opp: 5 },
        'intermezzo:missed': { you: 5, opp: 5 },
        'interference:missed': { you: 5, opp: 5 },
        'capturing_defender:missed': { you: 5, opp: 5 },
        'attraction:missed': { you: 5, opp: 5 },
        'under_promotion:missed': { you: 5, opp: 5 },
        'promotion:missed': { you: 5, opp: 5 },
      }),
    );
    openAdvanced();
    expect(text('tactic-group-advanced-no-flaws')).toBe('No flaws yet: X-ray, En passant.');
    expect(rowNames('advanced')).not.toContain('X-ray');
    expect(rowNames('advanced')).not.toContain('En passant');
  });

  it('lists the zero-flaw families of the always-open tables too', () => {
    renderTables();
    expect(text('tactic-group-piece_attacks-no-flaws')).toBe('No flaws yet: Skewer.');
    expect(text('tactic-group-discoveries-no-flaws')).toBe(
      'No flaws yet: Double check, Discovered check.',
    );
  });

  it('omits the line when every family has flaws', () => {
    const all: TacticOverrides = {
      'fork:missed': { you: 5 },
      'pin:missed': { you: 5 },
      'skewer:missed': { you: 5 },
      'hanging:missed': { you: 5 },
    };
    renderTables(makeTacticTcEntry('rapid', 1841, all));
    expect(screen.queryByTestId('tactic-group-piece_attacks-no-flaws')).toBeNull();
  });

  it('shows a muted "No flaws" and no popover for a zero-flaw side of an active family', () => {
    renderTables();
    // Hanging piece was only ever allowed in the fixture.
    expect(text('tactic-cell-hanging-missed-empty')).toBe('No flaws');
    expect(screen.queryByTestId('gap-popover-tactic-hanging-missed-tc-rapid')).toBeNull();
    expect(screen.queryByTestId('tactic-cell-hanging-missed-bar')).toBeNull();
    expect(screen.getByTestId('gap-popover-tactic-hanging-allowed-tc-rapid')).not.toBeNull();
  });
});

describe('low-sample and band-less cells (D-11, D-12)', () => {
  it('fades a low-sample cell and gives it a blue dot and no verdict colour', () => {
    renderTables(
      makeTacticTcEntry('rapid', 1841, {
        // 9 + 3 flaws: well under the sample minimum, with a band so only the sample is at fault.
        'fork:missed': { you: 9, opp: 3, zone: [-0.1, 0.1] },
        'fork:allowed': { you: 80, opp: 90, zone: [-0.5, 0.5] },
      }),
    );
    expect(screen.getByTestId('tactic-cell-fork-missed').style.opacity).toBe(
      String(UNRELIABLE_OPACITY),
    );
    expect(screen.getByTestId('tactic-cell-fork-missed-bar-dot').style.backgroundColor).toBe(
      normalized(GAUGE_NEUTRAL),
    );
    expect(screen.getByTestId('tactic-cell-fork-missed-bar-words').style.color).toBe('');
    expect(screen.getByTestId('tactic-cell-fork-allowed').style.opacity).toBe('');
  });

  it('draws no band and no typical-range line for a band-less cell, keeping its blue dot', () => {
    renderTables();
    // fork:allowed has no zone in the fixture.
    expect(screen.queryByTestId('tactic-cell-fork-allowed-bar-band')).toBeNull();
    expect(screen.getByTestId('tactic-cell-fork-allowed-bar-dot').style.backgroundColor).toBe(
      normalized(GAUGE_NEUTRAL),
    );
    fireEvent.click(screen.getByTestId('gap-popover-tactic-fork-allowed-tc-rapid'));
    expect(text('gap-popover-tactic-fork-allowed-tc-rapid-popover')).not.toContain('Typical gap');
    // The banded sibling does carry the line.
    fireEvent.click(screen.getByTestId('gap-popover-tactic-fork-missed-tc-rapid'));
    expect(text('gap-popover-tactic-fork-missed-tc-rapid-popover')).toContain('Typical gap');
  });

  it('colours a banded, well-sampled cell that sits outside its band', () => {
    renderTables();
    // fork:missed: 2.2 more per 100 games, band -0.5 to 0.9, 128 flaws: worse (not blue).
    expect(screen.getByTestId('tactic-cell-fork-missed-bar-dot').style.backgroundColor).not.toBe(
      normalized(GAUGE_NEUTRAL),
    );
    expect(screen.getByTestId('tactic-cell-fork-missed').style.opacity).toBe('');
  });
});

describe('phone layout and footer (D-00h)', () => {
  it('hides the column header row below md and stacks the cells with side labels', () => {
    renderTables();
    const header = screen.getByTestId('tactic-group-piece_attacks-header');
    expect(header.className).toContain('hidden');
    expect(header.className).toContain('md:grid');
    expect(header.textContent).toBe('MotifMissedAllowed');

    const row = screen.getByTestId('tactic-row-fork');
    expect(row.className).toContain('grid-cols-1');
    expect(row.className).toContain('md:grid-cols-[24%_38%_38%]');
    const missedLabel = screen.getByTestId('tactic-cell-fork-missed-side');
    const allowedLabel = screen.getByTestId('tactic-cell-fork-allowed-side');
    expect(missedLabel.textContent).toBe('Missed');
    expect(allowedLabel.textContent).toBe('Allowed');
    expect(missedLabel.className).toContain('md:hidden');
    expect(allowedLabel.className).toContain('md:hidden');
    // Name first, then Missed, then Allowed.
    expect(row.children[0]?.textContent).toContain('Fork');
    expect(row.children[1]).toBe(screen.getByTestId('tactic-cell-fork-missed'));
    expect(row.children[2]).toBe(screen.getByTestId('tactic-cell-fork-allowed'));
  });

  it('shows the footer line once after the tables', () => {
    renderTables();
    expect(screen.getAllByTestId('tactic-tables-footer')).toHaveLength(1);
    expect(text('tactic-tables-footer')).toBe(
      "Per 100 games. Middle tick = same as your opponents, better to the right. Your and your opponents' rates are in each search-icon popover.",
    );
  });

  it('never uses text-xs in the tables apart from the shared hint', () => {
    renderTables();
    const tables = screen.getByTestId('tactic-tables');
    const offenders = Array.from(tables.querySelectorAll('.text-xs')).map((el) => el.textContent);
    expect(offenders).toEqual(['Click or tap for details']);
  });
});
