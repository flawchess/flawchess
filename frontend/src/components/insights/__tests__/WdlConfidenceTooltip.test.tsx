// @vitest-environment jsdom
/**
 * Tests for WdlConfidenceTooltip — the body shared by all four
 * score-confidence surfaces (move-explorer Score popover, stats-board score
 * bullet, OpeningStatsCard, OpeningFindingCard).
 *
 * Quick task 260508-r61: optional "Last played: <relative>" line.
 */
import { describe, it, expect, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import { WdlConfidenceTooltip } from '../WdlConfidenceTooltip';

afterEach(() => {
  cleanup();
});

describe('WdlConfidenceTooltip — last played', () => {
  it('renders a "Last played" line when lastPlayedAt is provided', () => {
    const recentIso = new Date(Date.now() - 60 * 1000).toISOString(); // ~1 minute ago
    const { container } = render(
      <WdlConfidenceTooltip
        level="high"
        pValue={0.02}
        score={0.7}
        gameCount={20}
        lastPlayedAt={recentIso}
      />,
    );
    expect(container.textContent).toContain('Last played:');
  });

  it('omits the "Last played" line when lastPlayedAt is null', () => {
    const { container } = render(
      <WdlConfidenceTooltip
        level="low"
        pValue={0.3}
        score={0.5}
        gameCount={5}
        lastPlayedAt={null}
      />,
    );
    expect(container.textContent).not.toContain('Last played:');
  });

  it('omits the "Last played" line when lastPlayedAt is undefined (prop absent)', () => {
    const { container } = render(
      <WdlConfidenceTooltip level="low" pValue={0.3} score={0.5} gameCount={5} />,
    );
    expect(container.textContent).not.toContain('Last played:');
  });

  it('still renders the methodology block when lastPlayedAt is provided', () => {
    const { container } = render(
      <WdlConfidenceTooltip
        level="high"
        pValue={0.02}
        score={0.7}
        gameCount={20}
        lastPlayedAt={new Date().toISOString()}
      />,
    );
    expect(container.textContent).toContain('Wilson');
  });
});
