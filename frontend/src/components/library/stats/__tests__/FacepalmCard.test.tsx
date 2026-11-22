// @vitest-environment jsdom
/** The Facepalm blunders card: three banded paired rows, locked copy, standard verdict colours. */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { COPY_CHANCE } from '@/components/endgames/stats/rankedMetrics';
import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import type { FacepalmBullet, FlawComparisonTc } from '@/types/library';
import { FacepalmCard } from '../FacepalmCard';
import { makeFacepalmRows, makeTcEntry } from './flawStatsFixtures';

afterEach(cleanup);

const RANGE = 'Typical gap among FlawChess players: 0.30 fewer to 0.30 more.';
const ROW_IDS = [
  'context-row-facepalm',
  'context-row-facepalm-missed-win',
  'context-row-facepalm-allowed-loss',
] as const;
const POPOVER_IDS = [
  'gap-popover-facepalm-tc-rapid',
  'gap-popover-facepalm-missed-win-tc-rapid',
  'gap-popover-facepalm-allowed-loss-tc-rapid',
] as const;

/** jsdom normalizes color strings; compare normalized forms. */
function normalized(color: string): string {
  const probe = document.createElement('div');
  probe.style.color = color;
  return probe.style.color;
}

const RAPID = makeTcEntry('rapid', { analyzedN: 1841 });

/** `rows` null renders the card while its own request is still loading. */
function renderCard(
  rows: readonly FacepalmBullet[] | null = makeFacepalmRows(),
  {
    tcStats = RAPID,
    isError = false,
    lowCoverage = false,
  }: { tcStats?: FlawComparisonTc; isError?: boolean; lowCoverage?: boolean } = {},
): string {
  render(
    <FacepalmCard
      tcStats={tcStats}
      bullets={rows ?? undefined}
      isError={isError}
      lowCoverage={lowCoverage}
    />,
  );
  return screen.getByTestId('context-card-facepalm').textContent ?? '';
}

function openPopover(id: string): string {
  fireEvent.click(screen.getByTestId(id));
  return screen.getByTestId(`${id}-popover`).textContent ?? '';
}

describe('FacepalmCard', () => {
  it('renders the title, the intro and the three rows with the locked labels and hints', () => {
    const text = renderCard();
    expect(text).toContain('Facepalm blunders');
    expect(screen.getByTestId('context-card-facepalm-intro').textContent).toBe(
      "Your facepalm blunders per 100 of your moves, next to your opponents' in the same games.",
    );
    ROW_IDS.forEach((id) => expect(screen.getByTestId(id)).not.toBeNull());
    const labels = ['Facepalm blunders', 'Missed wins', 'Allowed losses'];
    labels.forEach((label) => expect(text).toContain(label));
    expect(text).toContain('Blunders with a facepalm score of 70% or more');
    expect(text).toContain('Facepalm blunders that passed up winning material or checkmate');
    expect(text).toContain('Facepalm blunders that gave away material or allowed checkmate');
  });

  it('draws the grey band in every row and the better / worse axis caption', () => {
    renderCard();
    ROW_IDS.forEach((id) => expect(screen.getByTestId(`${id}-bar-band`)).not.toBeNull());
    expect(screen.getByTestId('context-card-facepalm-axis').textContent).toBe('betterworse');
  });

  it.each([
    ['worse', 0.4, ZONE_DANGER],
    ['better', -0.4, ZONE_SUCCESS],
  ] as const)('colours a significant %s gap outside the band', (_name, delta, color) => {
    renderCard(makeFacepalmRows({ facepalm: { significant: true, delta } }));
    expect(screen.getByTestId('context-row-facepalm-bar-dot').style.backgroundColor).toBe(
      normalized(color),
    );
    const words = screen.getByTestId('context-row-facepalm-bar-words');
    expect(words.style.color).toBe(normalized(color));
  });

  it('keeps a not-significant out-of-band gap neutral: neutral dot, plain words', () => {
    renderCard(makeFacepalmRows({ facepalm: { significant: false, delta: 0.4 } }));
    expect(screen.getByTestId('context-row-facepalm-bar-dot').style.backgroundColor).toBe(
      normalized(GAUGE_NEUTRAL),
    );
    const words = screen.getByTestId('context-row-facepalm-bar-words');
    expect(words.style.color).toBe('');
    expect(words.className).toContain('text-foreground');
  });

  it('says nothing about blindness, events or probability in the closed card', () => {
    const text = renderCard();
    expect(text).not.toMatch(/blindness/i);
    expect(text).not.toMatch(/\bevents?\b/i);
    expect(text).not.toMatch(/probab|likel/i);
  });

  it('puts the direction, the FlawChess-players range and the verdict in a significant total popover', () => {
    renderCard(makeFacepalmRows({ facepalm: { significant: true, delta: 0.4 } }));
    const text = openPopover('gap-popover-facepalm-tc-rapid');
    expect(text).toContain('Fewer is better.');
    expect(text).toContain(`${RANGE} You are worse than typical.`);
    expect(text).not.toContain(COPY_CHANCE);
    expect(text).not.toContain('players at your level');
    expect(text).not.toMatch(/benchmark/i);
    expect(text).not.toMatch(/\bevents?\b/i);
  });

  it('says the gap could be chance for a not-significant out-of-band gap', () => {
    renderCard();
    const text = openPopover('gap-popover-facepalm-tc-rapid');
    expect(text).toContain(`${RANGE} ${COPY_CHANCE}`);
    expect(text).not.toContain('You are worse than typical.');
  });

  it('calls a same gap typical', () => {
    renderCard(makeFacepalmRows({ facepalm: { delta: 0, player_rate: 0.5, opp_rate: 0.5 } }));
    const text = openPopover('gap-popover-facepalm-tc-rapid');
    expect(text).toContain(`${RANGE} You are typical.`);
    expect(text).not.toContain(COPY_CHANCE);
  });

  it('reads each type row from its own band, never comparing the types', () => {
    renderCard(
      makeFacepalmRows({ facepalm_missed_win: { zone_lo: -0.08, zone_hi: 0.08, delta: 0.05 } }),
    );
    const missed = openPopover('gap-popover-facepalm-missed-win-tc-rapid');
    expect(missed).toContain('Typical gap among FlawChess players: 0.08 fewer to 0.08 more.');
    expect(openPopover('gap-popover-facepalm-tc-rapid')).toContain(RANGE);
    expect(missed).not.toMatch(/missed wins? (than|vs)|allowed losses? (than|vs)/i);
  });

  it.each(POPOVER_IDS)('opens the %s popover with the direction, both rates and the basis', (id) => {
    renderCard();
    const text = openPopover(id);
    expect(text).toContain('You: 0.90 per 100 moves. Opponents: 0.50.');
    expect(text).toContain('Based on your 1,841 analyzed rapid games in the recent sample.');
    expect(text).toContain('Fewer is better.');
  });

  it('shows no popover trigger for a row without a gap', () => {
    renderCard(makeFacepalmRows({ facepalm_allowed_loss: { delta: null, player_rate: 0, opp_rate: 0 } }));
    expect(screen.queryByTestId('gap-popover-facepalm-allowed-loss-tc-rapid')).toBeNull();
    expect(screen.getByTestId('gap-popover-facepalm-tc-rapid')).not.toBeNull();
  });

  it('shows a loading placeholder while its own request is pending, and its own error', () => {
    renderCard(null);
    expect(screen.getByTestId('context-card-facepalm-loading')).not.toBeNull();
    ROW_IDS.forEach((id) => expect(screen.queryByTestId(id)).toBeNull());
    cleanup();
    renderCard(null, { isError: true });
    expect(screen.getByText(/Failed to load facepalm blunders/)).not.toBeNull();
  });

  it('shows a note and no rows when too few blunders are scored', () => {
    const text = renderCard([], { lowCoverage: true });
    expect(screen.getByTestId('context-card-facepalm-low-coverage')).not.toBeNull();
    expect(text).toContain('Not enough blunders in these games have a facepalm score yet');
    ROW_IDS.forEach((id) => expect(screen.queryByTestId(id)).toBeNull());
  });

  it('explains facepalm blunders and the training in the header popover, without probability words', () => {
    renderCard();
    fireEvent.click(screen.getByTestId('context-card-facepalm-info'));
    const body = screen.getByText(/^Facepalm blunders are /);
    expect(body.textContent).toBe(
      'Facepalm blunders are blunders that should have been easy to see for a player at your level: our model gives them a facepalm score of 70% or more. Blunder Check trains you to spot them before you move.',
    );
    expect(body.textContent).not.toMatch(/probab|likel|chance/i);
  });
});
