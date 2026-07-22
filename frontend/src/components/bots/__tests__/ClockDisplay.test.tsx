// @vitest-environment jsdom
/**
 * ClockDisplay.test.tsx (Phase 183 Plan 05, D-06) — the optional `persona`
 * prop renders the avatar portrait, name, and estimated ELO label for a
 * persona game and is entirely absent (no avatar node, compact card) when
 * omitted, e.g. a Custom game or the human side.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { ClockDisplay } from '../ClockDisplay';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';

const PERSONA = PERSONA_REGISTRY['attacker-800'];

afterEach(() => {
  cleanup();
});

describe('ClockDisplay — persona avatar + name (D-06)', () => {
  it('renders the avatar, name, and estimated ELO label when persona is given', () => {
    render(
      <ClockDisplay
        sideLabel={PERSONA.name}
        persona={PERSONA}
        remainingMs={300_000}
        isActive={false}
        isThinking={false}
        testId="clock-bot"
      />,
    );

    const clock = screen.getByTestId('clock-bot');
    expect(clock.textContent).toContain(PERSONA.name);
    // The "style · estimated ELO" line renders below the name.
    expect(clock.textContent).toContain(`${PERSONA.style} · ${PERSONA.calibratedLabel}`);
    // The avatar node renders: either the real-art <img> (when the asset
    // exists) or the emoji placeholder — both live in the one aria-hidden
    // avatar circle.
    expect(clock.querySelectorAll('span[aria-hidden="true"]').length).toBe(1);
  });

  it('renders just the plain label with no avatar node when persona is omitted', () => {
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
    expect(clock.querySelector('img')).toBeNull();
  });

  it('never uses sub-text-sm font-size utilities', () => {
    render(
      <ClockDisplay
        sideLabel={PERSONA.name}
        persona={PERSONA}
        remainingMs={300_000}
        isActive={false}
        isThinking={false}
        testId="clock-bot"
      />,
    );

    expect(screen.getByTestId('clock-bot').innerHTML).not.toContain('text-xs');
  });
});
