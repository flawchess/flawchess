// @vitest-environment jsdom
/** The Facepalm blunders card: three neutral paired rows, locked copy, no verdict. */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { COPY_CHANCE } from '@/components/endgames/stats/rankedMetrics';
import { GAUGE_NEUTRAL } from '@/lib/theme';
import type { FacepalmBullet, FlawComparisonTc } from '@/types/library';
import { FacepalmCard } from '../FacepalmCard';
import { makeFacepalmRows, makeTcEntry } from './flawStatsFixtures';

afterEach(cleanup);

const NO_RANGE = 'There is no typical range for facepalm blunders yet.';
const TOO_LARGE = 'The gap is too large to be chance.';
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

  it('has no better / worse axis caption and no grey band in any row', () => {
    renderCard();
    expect(screen.queryByTestId('context-card-facepalm-axis')).toBeNull();
    ROW_IDS.forEach((id) => expect(screen.queryByTestId(`${id}-bar-band`)).toBeNull());
  });

  it('renders a significant facepalm cell neutral: neutral dot, plain words', () => {
    renderCard(makeFacepalmRows({ facepalm: { significant: true, delta: 0.4 } }));
    expect(screen.getByTestId('context-row-facepalm-bar-dot').style.backgroundColor).toBe(
      normalized(GAUGE_NEUTRAL),
    );
    const words = screen.getByTestId('context-row-facepalm-bar-words');
    expect(words.style.color).toBe('');
    expect(words.className).toContain('text-foreground');
  });

  it('says nothing about blindness, events, better / worse or probability', () => {
    const text = renderCard();
    expect(text).not.toMatch(/blindness/i);
    expect(text).not.toMatch(/\bevents?\b/i);
    expect(text).not.toMatch(/\b(better|worse)\b/i);
    expect(text).not.toMatch(/probab|likel/i);
  });

  it('puts the no-range note and the too-large sentence in a significant total popover', () => {
    renderCard(makeFacepalmRows({ facepalm: { significant: true, delta: 0.4 } }));
    const text = openPopover('gap-popover-facepalm-tc-rapid');
    expect(text).toContain(NO_RANGE);
    expect(text).toContain(TOO_LARGE);
    expect(text).not.toContain(COPY_CHANCE);
    expect(text).not.toContain('Fewer is better.');
    expect(text).not.toContain('Typical gap');
    expect(text).not.toMatch(/\bevents?\b/i);
  });

  it('says the gap could be chance for a not-significant non-zero gap', () => {
    renderCard();
    const text = openPopover('gap-popover-facepalm-tc-rapid');
    expect(text).toContain(NO_RANGE);
    expect(text).toContain(COPY_CHANCE);
    expect(text).not.toContain(TOO_LARGE);
  });

  it('keeps a same gap free of both significance sentences', () => {
    renderCard(makeFacepalmRows({ facepalm: { delta: 0, player_rate: 0.5, opp_rate: 0.5 } }));
    const text = openPopover('gap-popover-facepalm-tc-rapid');
    expect(text).toContain(NO_RANGE);
    expect(text).not.toContain(COPY_CHANCE);
    expect(text).not.toContain(TOO_LARGE);
  });

  it.each(POPOVER_IDS)('opens the %s popover with both rates and the basis, never a direction', (id) => {
    renderCard();
    const text = openPopover(id);
    expect(text).toContain('You: 0.90 per 100 moves. Opponents: 0.50.');
    expect(text).toContain('Based on your 1,841 analyzed rapid games in the recent sample.');
    expect(text).not.toContain('Fewer is better.');
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
