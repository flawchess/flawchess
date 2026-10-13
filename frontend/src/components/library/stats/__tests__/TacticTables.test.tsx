// @vitest-environment jsdom
/**
 * Phase 239 D-00a, D-00c, D-00h: the three tactic tables of the Tactic motifs section.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { indefiniteArticle, tacticSideCopy } from '@/lib/tacticComparisonMeta';
import { TacticTables } from '../TacticTables';
import { RAPID_TACTIC_ENTRY, makeTacticTcEntry, SKETCH_RAPID_TACTIC_OVERRIDES } from './flawStatsFixtures';

afterEach(cleanup);

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
    expect(text('tactic-cell-fork-missed-words')).toBe('2.2 more');
    expect(text('tactic-cell-fork-allowed-words')).toBe('2.5 fewer');
  });

  it('draws the band only for a banded family-side (D-11)', () => {
    renderTables();
    expect(screen.queryByTestId('tactic-cell-fork-missed-band')).not.toBeNull();
    expect(screen.queryByTestId('tactic-cell-fork-allowed-band')).toBeNull();
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

describe('TacticTables scope', () => {
  it('contains no per-group rows from another group', () => {
    renderTables();
    const advanced = screen.getByTestId('tactic-group-advanced');
    expect(within(advanced).queryByTestId('tactic-row-fork')).toBeNull();
  });
});
