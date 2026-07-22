// @vitest-environment jsdom
/**
 * ClockDisplay.test.tsx (Phase 183 Plan 05, D-06) — the optional
 * `avatarEmoji` prop renders alongside `sideLabel` for a persona game and is
 * entirely absent (no avatar node) when omitted, e.g. a Custom game or the
 * human side.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { ClockDisplay } from '../ClockDisplay';

afterEach(() => {
  cleanup();
});

describe('ClockDisplay — persona avatar + name (D-06)', () => {
  it('renders the avatar emoji beside the sideLabel when avatarEmoji is given', () => {
    render(
      <ClockDisplay
        sideLabel="Ziggy the Wasp"
        avatarEmoji="🐝"
        remainingMs={300_000}
        isActive={false}
        isThinking={false}
        testId="clock-bot"
      />,
    );

    const clock = screen.getByTestId('clock-bot');
    expect(clock.textContent).toContain('Ziggy the Wasp');
    expect(clock.textContent).toContain('🐝');
  });

  it('renders just the plain label with no avatar node when avatarEmoji is omitted', () => {
    render(
      <ClockDisplay
        sideLabel="FlawChess Bot"
        remainingMs={300_000}
        isActive={false}
        isThinking={false}
        testId="clock-bot"
      />,
    );

    const clock = screen.getByTestId('clock-bot');
    expect(clock.textContent).toContain('FlawChess Bot');
    // No stray emoji/avatar glyph rendered — the label span holds nothing but
    // the text (and, when thinking, the pulse dot — not exercised here).
    expect(clock.querySelectorAll('span[aria-hidden="true"]').length).toBe(0);
  });

  it('never uses sub-text-sm font-size utilities', () => {
    render(
      <ClockDisplay
        sideLabel="Ziggy the Wasp"
        avatarEmoji="🐝"
        remainingMs={300_000}
        isActive={false}
        isThinking={false}
        testId="clock-bot"
      />,
    );

    expect(screen.getByTestId('clock-bot').innerHTML).not.toContain('text-xs');
  });
});
