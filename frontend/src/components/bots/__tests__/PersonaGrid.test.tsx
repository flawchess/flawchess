// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { PersonaGrid } from '../PersonaGrid';
import { rosterHost, ROSTER_HUMAN_LIKE_LINE } from '@/lib/botGameCopy';
import {
  STYLE_SECTION_ORDER,
  RUNGS,
  personasForSection,
  personasForRung,
} from '@/lib/personas/personaRegistry';
import { ATTACKER_ACCENT, TRICKSTER_ACCENT, GRINDER_ACCENT, WALL_ACCENT } from '@/lib/theme';

// The welcome bubble's copy is `rosterHost({ today }).copy` for the
// component's own day computation (`devClockNow(readDevClockOffsetMinutes())`
// formatted 'yyyy-MM-dd'). Pinning the system clock makes `today` — and so
// the assertions below — deterministic, matching Phase 223's own convention
// for testing a daily rotation (mirrors `trainBotCopy.test.ts`'s fixed-date
// `landingHost` cases).
const MOCKED_TODAY = '2026-07-01';

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(`${MOCKED_TODAY}T12:00:00Z`));
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

// jsdom normalizes oklch trailing zeros ('0.50' -> '0.5') when reading
// element.style.color back. Compare on a normalized form so the assertions
// are robust to jsdom's cosmetic rewrite without weakening the contract.
function normalizeColor(value: string): string {
  return value.replace(/(\d+)\.(\d*?)0+(?=\D|$)/g, (match, intPart: string, frac: string) => {
    if (frac === '') return `${intPart}`;
    return `${intPart}.${frac}`;
  });
}

describe('PersonaGrid', () => {
  it('renders exactly 24 persona cards, in rung-major DOM order (rung 800 top -> 1800 bottom, 4 styles per row)', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} />);

    const container = screen.getByTestId('bots-persona-grid');
    const cards = container.querySelectorAll('[data-testid^="bots-persona-card-"]');
    expect(cards.length).toBe(24);

    // Expected ids, in the exact DOM order the transposed grid should
    // produce: rung rows ascending (800 -> 1800), each row's 4 personas in
    // STYLE_SECTION_ORDER (personasForRung) — rung-major, not style-major.
    const expectedIds = RUNGS.flatMap((rung) => personasForRung(rung).map((persona) => persona.id));
    const actualIds = Array.from(cards).map((card) => card.getAttribute('data-testid'));
    expect(actualIds).toEqual(expectedIds.map((id) => `bots-persona-card-${id}`));
  });

  it('renders one header row of 4 style-name cells with the STYLE_ACCENT colors', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} />);

    const expectedAccent: Record<string, string> = {
      Attacker: ATTACKER_ACCENT,
      Trickster: TRICKSTER_ACCENT,
      Grinder: GRINDER_ACCENT,
      Wall: WALL_ACCENT,
    };
    for (const style of STYLE_SECTION_ORDER) {
      const header = screen.getByTestId(`bots-persona-header-${style.toLowerCase()}`);
      expect(header.textContent).toBe(style);
      expect(normalizeColor(header.style.color)).toBe(normalizeColor(expectedAccent[style]));
    }
    // No leftover per-style section wrappers from the pre-transpose layout.
    expect(screen.queryByTestId('bots-persona-section-attacker')).toBeNull();
  });

  it('each card shows a non-empty name, a tilde-formatted ELO label, and an avatar', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} />);

    const attackerPersonas = personasForSection('Attacker');
    for (const persona of attackerPersonas) {
      const card = screen.getByTestId(`bots-persona-card-${persona.id}`);
      expect(card.textContent).toContain(persona.name);
      expect(card.textContent).toMatch(/~\d+/);
      // Avatar node: real-art <img> or emoji placeholder — both live in the
      // one aria-hidden avatar circle.
      expect(card.querySelectorAll('span[aria-hidden="true"]').length).toBe(1);
    }
  });

  it('renders a Custom entry that invokes onSelectCustom on click', () => {
    const onSelectCustom = vi.fn();
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={onSelectCustom} />);

    const customEntry = screen.getByTestId('bots-persona-custom');
    expect(customEntry).toBeTruthy();

    fireEvent.click(customEntry);
    expect(onSelectCustom).toHaveBeenCalledTimes(1);
  });

  it('a persona card tap fires onSelectPersona with the tapped persona', () => {
    const onSelectPersona = vi.fn();
    render(<PersonaGrid onSelectPersona={onSelectPersona} onSelectCustom={vi.fn()} />);

    const firstAttacker = personasForSection('Attacker')[0];
    if (firstAttacker === undefined) throw new Error('expected at least one Attacker persona');
    fireEvent.click(screen.getByTestId(`bots-persona-card-${firstAttacker.id}`));

    expect(onSelectPersona).toHaveBeenCalledTimes(1);
    expect(onSelectPersona).toHaveBeenCalledWith(firstAttacker);
  });

  it("renders the welcome bubble with rosterHost's own copy for the mocked date, plus the engine popover trigger", () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} />);

    const bubble = screen.getByTestId('bots-welcome-bubble');
    const expectedCopy = rosterHost({ today: MOCKED_TODAY }).copy;
    expect(bubble.textContent).toContain(expectedCopy);
    expect(screen.getByTestId('bots-intro-info')).toBeTruthy();
  });

  it('shows the welcome bubble to every visitor and shows nobody an estimated rating (D-13, SC6)', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} />);

    // Phase 223 UAT retired the player's estimated-rating line: a bot's
    // calibrated ELO is measured against engines, so a human number beside it
    // invited a comparison the two scales do not support. The bubble itself is
    // ungated — a guest needs the explanation most.
    expect(screen.getByTestId('bots-welcome-bubble')).toBeTruthy();
    expect(screen.queryByTestId('bots-player-rating')).toBeNull();
    expect(screen.queryByTestId('bots-player-rating-info')).toBeNull();
  });

  it('appends the shared human-like claim to whichever persona is hosting', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} />);

    const bubble = screen.getByTestId('bots-welcome-bubble');
    expect(bubble.textContent).toContain(ROSTER_HUMAN_LIKE_LINE);
  });

  it('never uses sub-text-sm font-size utilities anywhere in the grid', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} />);

    const container = screen.getByTestId('bots-persona-grid');
    expect(container.innerHTML).not.toContain('text-xs');
  });
});
