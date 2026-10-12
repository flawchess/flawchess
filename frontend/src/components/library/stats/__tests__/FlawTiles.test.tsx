// @vitest-environment jsdom
/**
 * Phase 239 D-00a..D-00e, D-03: the Blunders and Mistakes tiles of the Flaw Stats section.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { FlawTiles } from '../FlawTiles';
import { ANALYZED_GATE, BLITZ_ENTRY, RAPID_ENTRY, makeTcEntry } from './flawStatsFixtures';

afterEach(cleanup);

function renderTiles(tcStats = RAPID_ENTRY) {
  render(<FlawTiles tcStats={tcStats} analyzedGate={ANALYZED_GATE} />);
}

function text(testId: string): string {
  return screen.getByTestId(testId).textContent ?? '';
}

describe('FlawTiles', () => {
  it('shows exactly the Blunders and Mistakes tiles, nothing else', () => {
    renderTiles();
    expect(screen.getByTestId('flaw-tile-blunder')).not.toBeNull();
    expect(screen.getByTestId('flaw-tile-mistake')).not.toBeNull();
    expect(screen.getByTestId('flaw-tiles').children).toHaveLength(2);
    expect(screen.queryByText(/inacc/i)).toBeNull();
    expect(screen.queryByText(/flaw rate/i)).toBeNull();
  });

  it('shows the rate, caption, Opponents line and the gap words on each tile', () => {
    renderTiles();
    expect(text('flaw-tile-blunder-rate')).toBe('5.22');
    expect(text('flaw-tile-blunder')).toContain('Blunders / 100 moves');
    expect(text('flaw-tile-blunder-opponents')).toBe('Opponents 5.83');
    expect(text('flaw-tile-blunder-bar-words')).toBe('0.61 fewer');
    expect(text('flaw-tile-mistake-rate')).toBe('6.40');
    expect(text('flaw-tile-mistake')).toContain('Mistakes / 100 moves');
    expect(text('flaw-tile-mistake-opponents')).toBe('Opponents 6.90');
    expect(text('flaw-tile-mistake-bar-words')).toBe('0.50 fewer');
  });

  it('puts a Search popover with the per-TC testid on each tile', () => {
    renderTiles();
    expect(screen.getByTestId('gap-popover-blunder-tc-rapid')).not.toBeNull();
    expect(screen.getByTestId('gap-popover-mistake-tc-rapid')).not.toBeNull();
  });

  it('keys the popover testid by the tile TC', () => {
    renderTiles(BLITZ_ENTRY);
    expect(screen.getByTestId('gap-popover-blunder-tc-blitz')).not.toBeNull();
  });

  it('says blunders and the TC basis in the popover, never events (D-00d)', () => {
    renderTiles(BLITZ_ENTRY);
    fireEvent.click(screen.getByTestId('gap-popover-blunder-tc-blitz'));
    const popover = text('gap-popover-blunder-tc-blitz-popover');
    expect(popover).toContain('Fewer is better.');
    expect(popover).toContain('Based on your 1,000 analyzed blitz games in the current filters.');
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

  it('keeps the numbers below the gate and swaps the bar for the gate line (D-03)', () => {
    const entry = makeTcEntry('bullet', {
      analyzedN: 12,
      blunder: { player_rate: 4.1, opp_rate: 4.6, delta: -0.5 },
    });
    renderTiles(entry);
    expect(text('flaw-tile-blunder-rate')).toBe('4.10');
    expect(text('flaw-tile-blunder-opponents')).toBe('Opponents 4.60');
    expect(text('flaw-tile-blunder-gate')).toBe('Not enough analyzed games yet (12 of 20)');
    expect(text('flaw-tile-mistake-gate')).toBe('Not enough analyzed games yet (12 of 20)');
    expect(screen.queryByTestId('flaw-tile-blunder-bar')).toBeNull();
    expect(screen.queryByTestId('gap-popover-blunder-tc-bullet')).toBeNull();
  });

  it('never fades a tile, also for a low-sample bullet (D-12 names tactic cells and rows only)', () => {
    const entry = makeTcEntry('rapid', { analyzedN: 400, blunder: { low_sample: true } });
    renderTiles(entry);
    expect(screen.getByTestId('flaw-tile-blunder').getAttribute('style') ?? '').not.toContain('opacity');
  });
});
