// @vitest-environment jsdom
/**
 * The Facepalm blunders and Blunders tiles of the Flaw Stats section.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { ZONE_SUCCESS } from '@/lib/theme';
import { FlawTiles } from '../FlawTiles';
import type { FacepalmBullet } from '@/types/library';
import {
  ANALYZED_GATE,
  BLITZ_ENTRY,
  RAPID_ENTRY,
  makeFacepalmRows,
  makeTcEntry,
} from './flawStatsFixtures';

afterEach(cleanup);

const LOADING = 'loading' as const;

/** Pass LOADING for the facepalm rows to render the tile while its request is pending. */
function renderTiles(
  tcStats = RAPID_ENTRY,
  facepalm: readonly FacepalmBullet[] | typeof LOADING = makeFacepalmRows(),
  facepalmError = false,
  facepalmLowCoverage = false,
) {
  const facepalmBullets = facepalm === LOADING ? undefined : facepalm;
  render(
    <FlawTiles
      tcStats={tcStats}
      analyzedGate={ANALYZED_GATE}
      facepalmBullets={facepalmBullets}
      facepalmError={facepalmError}
      facepalmLowCoverage={facepalmLowCoverage}
    />,
  );
}

/** jsdom normalizes color strings; compare normalized forms (same helper as GapBar.test). */
function normalized(color: string): string {
  const probe = document.createElement('div');
  probe.style.color = color;
  return probe.style.color;
}

function text(testId: string): string {
  return screen.getByTestId(testId).textContent ?? '';
}

describe('FlawTiles', () => {
  it('shows the Blunders tile left and the Facepalm tile right, nothing else', () => {
    renderTiles();
    const tiles = screen.getByTestId('flaw-tiles').children;
    expect(tiles).toHaveLength(2);
    expect(tiles[0]?.getAttribute('data-testid')).toBe('flaw-tile-blunder');
    expect(tiles[1]?.getAttribute('data-testid')).toBe('flaw-tile-facepalm');
    expect(screen.queryByTestId('flaw-tile-mistake')).toBeNull();
    expect(screen.queryByText(/inacc/i)).toBeNull();
    expect(screen.queryByText(/flaw rate/i)).toBeNull();
  });

  it('shows the rate, caption, Opponents line and the gap words on each tile', () => {
    renderTiles();
    expect(text('flaw-tile-blunder-rate')).toBe('5.22');
    expect(text('flaw-tile-blunder')).toContain('Blunders / 100 moves');
    expect(text('flaw-tile-blunder-opponents')).toBe('Opponents 5.83');
    expect(text('flaw-tile-blunder-bar-words')).toBe('0.61 fewer');
    expect(text('flaw-tile-facepalm-rate')).toBe('0.90');
    expect(text('flaw-tile-facepalm')).toContain('Facepalm blunders / 100 moves');
    expect(text('flaw-tile-facepalm-opponents')).toBe('Opponents 0.50');
    expect(text('flaw-tile-facepalm-bar-words')).toBe('0.40 more');
  });

  it('puts a Search popover with the per-TC testid on each tile', () => {
    renderTiles();
    expect(screen.getByTestId('gap-popover-blunder-tc-rapid')).not.toBeNull();
    expect(screen.getByTestId('gap-popover-facepalm-tile-tc-rapid')).not.toBeNull();
  });

  it('explains facepalm blunders in an info popover on the Facepalm tile only', () => {
    renderTiles();
    fireEvent.click(screen.getByTestId('flaw-tile-facepalm-info'));
    expect(screen.getByText(/^Facepalm blunders are blunders that should have been easy/)).not.toBeNull();
    expect(screen.queryByTestId('flaw-tile-blunder-info')).toBeNull();
  });

  it('keeps the Facepalm tile neutral: no verdict colour even for a significant gap', () => {
    renderTiles(RAPID_ENTRY, makeFacepalmRows({ facepalm: { delta: 2, significant: true } }));
    expect(screen.getByTestId('flaw-tile-facepalm-bar-words').style.color).toBe('');
    fireEvent.click(screen.getByTestId('gap-popover-facepalm-tile-tc-rapid'));
    const popover = text('gap-popover-facepalm-tile-tc-rapid-popover');
    expect(popover).toContain('There is no typical range for facepalm blunders yet.');
    expect(popover).not.toContain('Fewer is better.');
  });

  it('shows a skeleton while the facepalm rows load and an error inside the tile on failure', () => {
    renderTiles(RAPID_ENTRY, LOADING);
    expect(screen.getByTestId('flaw-tile-facepalm-loading')).not.toBeNull();
    expect(screen.getByTestId('flaw-tile-blunder')).not.toBeNull();
    cleanup();
    renderTiles(RAPID_ENTRY, LOADING, true);
    expect(text('flaw-tile-facepalm')).toContain('Failed to load facepalm blunders.');
    expect(screen.getByTestId('flaw-tile-blunder')).not.toBeNull();
  });

  it('keys the popover testid by the tile TC', () => {
    renderTiles(BLITZ_ENTRY);
    expect(screen.getByTestId('gap-popover-blunder-tc-blitz')).not.toBeNull();
  });

  it('says blunders and the TC basis in the popover, never events', () => {
    renderTiles(BLITZ_ENTRY);
    fireEvent.click(screen.getByTestId('gap-popover-blunder-tc-blitz'));
    const popover = text('gap-popover-blunder-tc-blitz-popover');
    expect(popover).toContain('Fewer is better.');
    expect(popover).toContain('Based on your 1,000 analyzed blitz games in the recent sample.');
    expect(popover).toContain('1,916 vs. 1,982 blunders');
    expect(popover.toLowerCase()).not.toContain('event');
  });

  it('shows a dash for a missing player rate and "No flaws yet" for a gap-less bullet', () => {
    const entry = makeTcEntry('rapid', {
      analyzedN: 400,
      blunder: { player_rate: null, opp_rate: null, delta: null, ci_low: null, ci_high: null, p_value: null },
    });
    renderTiles(entry);
    expect(text('flaw-tile-blunder-rate')).toBe('—');
    expect(text('flaw-tile-blunder-opponents')).toBe('Opponents —');
    expect(text('flaw-tile-blunder-bar-empty')).toBe('No flaws yet');
  });

  it('keeps the numbers below the gate and swaps the bar for the gate line', () => {
    const entry = makeTcEntry('bullet', {
      analyzedN: 12,
      blunder: { player_rate: 4.1, opp_rate: 4.6, delta: -0.5 },
    });
    renderTiles(entry);
    expect(text('flaw-tile-blunder-rate')).toBe('4.10');
    expect(text('flaw-tile-blunder-opponents')).toBe('Opponents 4.60');
    expect(text('flaw-tile-blunder-gate')).toBe('Not enough analyzed games yet (12 of 20)');
    expect(text('flaw-tile-facepalm-gate')).toBe('Not enough analyzed games yet (12 of 20)');
    expect(screen.queryByTestId('flaw-tile-blunder-bar')).toBeNull();
    expect(screen.queryByTestId('gap-popover-blunder-tc-bullet')).toBeNull();
  });

  it('shows the verdict for a significant out-of-band tile and withholds it otherwise', () => {
    // delta -0.61 is below the fixture band (-0.3..0.3): a "better" verdict.
    renderTiles(makeTcEntry('rapid', { analyzedN: 400, blunder: { delta: -0.61, significant: true } }));
    expect(screen.getByTestId('flaw-tile-blunder-bar-dot').style.backgroundColor).toBe(
      normalized(ZONE_SUCCESS),
    );
    expect(screen.getByTestId('flaw-tile-blunder-bar-words').style.color).toBe(
      normalized(ZONE_SUCCESS),
    );
    cleanup();
    renderTiles(makeTcEntry('rapid', { analyzedN: 400, blunder: { delta: -0.61, significant: false } }));
    expect(screen.getByTestId('flaw-tile-blunder-bar-dot').style.backgroundColor).not.toBe(
      normalized(ZONE_SUCCESS),
    );
    expect(screen.getByTestId('flaw-tile-blunder-bar-words').style.color).toBe('');
  });

  it('shows a note in place of the facepalm rates when too few blunders are scored', () => {
    renderTiles(RAPID_ENTRY, [], false, true);
    const tile = screen.getByTestId('flaw-tile-facepalm');
    expect(tile.textContent).toContain('Not enough blunders in these games have a facepalm score yet');
    expect(screen.getByTestId('flaw-tile-facepalm-low-coverage')).not.toBeNull();
    expect(screen.getByTestId('flaw-tile-blunder')).not.toBeNull();
  });
});
