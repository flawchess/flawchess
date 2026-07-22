// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { PersonaGrid } from '../PersonaGrid';
import { STYLE_SECTION_ORDER, personasForSection } from '@/lib/personas/personaRegistry';

afterEach(() => {
  cleanup();
});

describe('PersonaGrid', () => {
  it('renders exactly 24 persona cards, grouped into 4 sections in STYLE_SECTION_ORDER (DOM order)', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} playerRating={null} />);

    const container = screen.getByTestId('bots-persona-grid');
    const cards = container.querySelectorAll('[data-testid^="bots-persona-card-"]');
    expect(cards.length).toBe(24);

    // Expected ids, in the exact DOM order the grid should produce: style
    // sections in STYLE_SECTION_ORDER, each section's 6 personas ascending
    // by rung (personasForSection).
    const expectedIds = STYLE_SECTION_ORDER.flatMap((style) =>
      personasForSection(style).map((persona) => persona.id),
    );
    const actualIds = Array.from(cards).map((card) => card.getAttribute('data-testid'));
    expect(actualIds).toEqual(expectedIds.map((id) => `bots-persona-card-${id}`));
  });

  it('each card shows a non-empty name, a tilde-formatted ELO label, and an avatar', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} playerRating={null} />);

    const attackerPersonas = personasForSection('Attacker');
    for (const persona of attackerPersonas) {
      const card = screen.getByTestId(`bots-persona-card-${persona.id}`);
      expect(card.textContent).toContain(persona.name);
      expect(card.textContent).toMatch(/~\d+/);
      expect(card.textContent).toContain(persona.avatarEmoji);
    }
  });

  it('renders a Custom entry that invokes onSelectCustom on click', () => {
    const onSelectCustom = vi.fn();
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={onSelectCustom} playerRating={null} />);

    const customEntry = screen.getByTestId('bots-persona-custom');
    expect(customEntry).toBeTruthy();

    fireEvent.click(customEntry);
    expect(onSelectCustom).toHaveBeenCalledTimes(1);
  });

  it('a persona card tap fires onSelectPersona with the tapped persona', () => {
    const onSelectPersona = vi.fn();
    render(<PersonaGrid onSelectPersona={onSelectPersona} onSelectCustom={vi.fn()} playerRating={null} />);

    const firstAttacker = personasForSection('Attacker')[0];
    if (firstAttacker === undefined) throw new Error('expected at least one Attacker persona');
    fireEvent.click(screen.getByTestId(`bots-persona-card-${firstAttacker.id}`));

    expect(onSelectPersona).toHaveBeenCalledTimes(1);
    expect(onSelectPersona).toHaveBeenCalledWith(firstAttacker);
  });

  it('shows the player rating reference line when an anchor is available', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} playerRating={1642} />);

    const line = screen.getByTestId('bots-player-rating');
    expect(line.textContent).toContain('~1642');
    expect(screen.getByTestId('bots-player-rating-info')).toBeTruthy();
  });

  it('omits the player rating reference line entirely when there is no anchor', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} playerRating={null} />);

    expect(screen.queryByTestId('bots-player-rating')).toBeNull();
    expect(screen.queryByTestId('bots-player-rating-info')).toBeNull();
  });

  it('never uses sub-text-sm font-size utilities anywhere in the grid', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} playerRating={null} />);

    const container = screen.getByTestId('bots-persona-grid');
    expect(container.innerHTML).not.toContain('text-xs');
  });
});
