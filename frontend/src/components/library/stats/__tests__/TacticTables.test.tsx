// @vitest-environment jsdom
/**
 * Phase 239 D-00a, D-00c, D-00h, D-17: the one tactic card of the Tactic motifs section.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { GAUGE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import { indefiniteArticle, tacticSideCopy } from '@/lib/tacticComparisonMeta';
import { TacticTables } from '../TacticTables';
import {
  BLITZ_TACTIC_ENTRY,
  RAPID_TACTIC_ENTRY,
  SKETCH_RAPID_TACTIC_OVERRIDES,
  makeTacticTcEntry,
} from './flawStatsFixtures';

afterEach(cleanup);

/** jsdom normalizes color strings; compare normalized forms. */
function normalized(color: string): string {
  const probe = document.createElement('div');
  probe.style.color = color;
  return probe.style.color;
}

function renderTables(tcStats = RAPID_TACTIC_ENTRY): void {
  render(<TacticTables tcStats={tcStats} />);
}

function text(testId: string): string {
  return screen.getByTestId(testId).textContent ?? '';
}

/** Motif names of the card's rows, in rendered order. */
function rowNames(): string[] {
  const card = screen.getByTestId('tactic-card');
  return Array.from(card.querySelectorAll('[data-testid^="tactic-row-"]:not([data-testid$="-flaws"])')).map(
    (row) => row.firstElementChild?.firstElementChild?.textContent ?? '',
  );
}

const SHOWN = ['Fork', 'Pin', 'Hanging piece', 'Checkmate'];

describe('TacticTables card (D-17)', () => {
  it('shows one card titled "Most common tactics"', () => {
    renderTables();
    expect(screen.getAllByTestId('tactic-card')).toHaveLength(1);
    expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual([
      'Most common tactics',
    ]);
  });

  it('lists exactly Fork, Pin, Hanging piece and Checkmate in the filter panel order', () => {
    renderTables();
    expect(rowNames()).toEqual(SHOWN);
  });

  it('leaves out the rarer families, also when they have flaws', () => {
    renderTables();
    // The fixture has discovered-attack and sacrifice flaws.
    expect(screen.queryByTestId('tactic-row-discovered-attack')).toBeNull();
    expect(screen.queryByTestId('tactic-row-sacrifice')).toBeNull();
    expect(screen.queryByTestId('tactic-row-skewer')).toBeNull();
  });

  it('never lets the payload order decide the row order', () => {
    renderTables(makeTacticTcEntry('rapid', 1841, SKETCH_RAPID_TACTIC_OVERRIDES, true));
    expect(rowNames()).toEqual(SHOWN);
  });

  it('does not re-sort the rows by rate (a busier later family stays later)', () => {
    renderTables(
      makeTacticTcEntry('rapid', 1841, {
        'fork:missed': { you: 5, opp: 5 },
        'hanging:missed': { you: 400, opp: 100 },
      }),
    );
    expect(rowNames()).toEqual(SHOWN);
  });

  it('keeps a row for a shown family without any flaws', () => {
    renderTables(makeTacticTcEntry('rapid', 1841, {}));
    expect(rowNames()).toEqual(SHOWN);
    expect(text('tactic-cell-pin-missed-empty')).toBe('No flaws');
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
    expect(screen.getByTestId('gap-popover-tactic-mate-allowed-tc-rapid')).not.toBeNull();
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

  it('shows a muted "No flaws" and no popover for a zero-flaw side of an active family', () => {
    renderTables();
    // Hanging piece was only ever allowed in the fixture.
    expect(text('tactic-cell-hanging-missed-empty')).toBe('No flaws');
    expect(screen.queryByTestId('gap-popover-tactic-hanging-missed-tc-rapid')).toBeNull();
    expect(screen.queryByTestId('tactic-cell-hanging-missed-bar')).toBeNull();
    expect(screen.getByTestId('gap-popover-tactic-hanging-allowed-tc-rapid')).not.toBeNull();
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

describe('not-significant and band-less cells (D-11, D-14)', () => {
  it('gives an out-of-band cell that is not significant a blue dot and no verdict colour, unfaded', () => {
    renderTables(
      makeTacticTcEntry('rapid', 1841, {
        // 9 vs 3 flaws: outside the band, but the fixture CI (gap +- 1) covers 0.
        'fork:missed': { you: 9, opp: 3, zone: [-0.1, 0.1] },
        'fork:allowed': { you: 80, opp: 90, zone: [-0.5, 0.5] },
      }),
    );
    expect(screen.getByTestId('tactic-cell-fork-missed').style.opacity).toBe('');
    expect(screen.getByTestId('tactic-cell-fork-missed-bar-dot').style.backgroundColor).toBe(
      normalized(GAUGE_NEUTRAL),
    );
    expect(screen.getByTestId('tactic-cell-fork-missed-bar-words').style.color).toBe('');
    expect(screen.getByTestId('tactic-cell-fork-allowed').style.opacity).toBe('');
  });

  it('draws no band and no typical-range line for a band-less cell, blue when not significant', () => {
    // fork:allowed has no zone; 45 vs 50 over 1000 games is a gap the fixture CI covers.
    renderTables(BLITZ_TACTIC_ENTRY);
    expect(screen.queryByTestId('tactic-cell-fork-allowed-bar-band')).toBeNull();
    expect(screen.getByTestId('tactic-cell-fork-allowed-bar-dot').style.backgroundColor).toBe(
      normalized(GAUGE_NEUTRAL),
    );
    cleanup();
    renderTables();
    fireEvent.click(screen.getByTestId('gap-popover-tactic-fork-allowed-tc-rapid'));
    expect(text('gap-popover-tactic-fork-allowed-tc-rapid-popover')).not.toContain('Typical gap');
    // The banded sibling does carry the line.
    fireEvent.click(screen.getByTestId('gap-popover-tactic-fork-missed-tc-rapid'));
    expect(text('gap-popover-tactic-fork-missed-tc-rapid-popover')).toContain('Typical gap');
  });

  it('colours a significant band-less cell on significance alone (D-16)', () => {
    renderTables();
    // fork:allowed: 134 vs 180 over 1841 games, 2.5 fewer per 100 games, CI clear of 0.
    expect(screen.getByTestId('tactic-cell-fork-allowed-bar-dot').style.backgroundColor).toBe(
      normalized(ZONE_SUCCESS),
    );
    fireEvent.click(screen.getByTestId('gap-popover-tactic-fork-allowed-tc-rapid'));
    expect(text('gap-popover-tactic-fork-allowed-tc-rapid-popover')).toContain(
      'There is no typical range for this tactic, but the gap is too large to be chance.',
    );
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
    const header = screen.getByTestId('tactic-card-header');
    expect(header.className).toContain('hidden');
    expect(header.className).toContain('md:grid');
    expect(header.textContent).toBe('MotifMissedAllowed');

    const row = screen.getByTestId('tactic-row-fork');
    expect(row.className).toContain('grid-cols-1');
    expect(row.className).toContain('md:grid-cols-[24fr_38fr_38fr]');
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

  it('shows the footer line once after the card, with lower (better) to the left', () => {
    renderTables();
    expect(screen.getAllByTestId('tactic-tables-footer')).toHaveLength(1);
    expect(text('tactic-tables-footer')).toBe(
      "Per 100 games. Middle tick = same as your opponents, fewer (better) to the left. Your and your opponents' rates are in each search-icon popover.",
    );
  });

  it('never uses text-xs in the card', () => {
    renderTables();
    expect(screen.getByTestId('tactic-tables').querySelectorAll('.text-xs')).toHaveLength(0);
  });
});
