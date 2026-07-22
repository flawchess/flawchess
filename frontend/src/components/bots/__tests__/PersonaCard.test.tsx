// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { PersonaCard } from '../PersonaCard';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';

afterEach(() => {
  cleanup();
});

const PERSONA = PERSONA_REGISTRY['attacker-800'];

describe('PersonaCard', () => {
  it('renders the persona name, calibrated ELO label, and an avatar node', () => {
    render(<PersonaCard persona={PERSONA} onSelect={vi.fn()} />);

    const card = screen.getByTestId(`bots-persona-card-${PERSONA.id}`);
    expect(card.textContent).toContain(PERSONA.name);
    expect(card.textContent).toContain(PERSONA.calibratedLabel);
    // The avatar emoji node renders inside the card.
    expect(card.textContent).toContain(PERSONA.avatarEmoji);
  });

  it('renders the calibrated label, not the raw rung, when they differ (CAL-05)', () => {
    const personaWithDistinctLabel = { ...PERSONA, calibratedLabel: '~1050' };
    render(<PersonaCard persona={personaWithDistinctLabel} onSelect={vi.fn()} />);

    const card = screen.getByTestId(`bots-persona-card-${personaWithDistinctLabel.id}`);
    expect(card.textContent).toContain('~1050');
    expect(card.textContent).not.toContain(`~${PERSONA.rung}`);
    expect(card.getAttribute('aria-label')).toContain('~1050');
  });

  it('is a semantic button with an aria-label naming the persona', () => {
    render(<PersonaCard persona={PERSONA} onSelect={vi.fn()} />);

    const card = screen.getByTestId(`bots-persona-card-${PERSONA.id}`);
    expect(card.tagName).toBe('BUTTON');
    expect(card.getAttribute('aria-label')).toContain(PERSONA.name);
  });

  it('calls onSelect with the persona when tapped', () => {
    const onSelect = vi.fn();
    render(<PersonaCard persona={PERSONA} onSelect={onSelect} />);

    fireEvent.click(screen.getByTestId(`bots-persona-card-${PERSONA.id}`));

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(PERSONA);
  });

  it('never uses sub-text-sm font-size utilities on card text', () => {
    render(<PersonaCard persona={PERSONA} onSelect={vi.fn()} />);

    const card = screen.getByTestId(`bots-persona-card-${PERSONA.id}`);
    expect(card.innerHTML).not.toContain('text-xs');
  });

  it('backstop: falls back to the emoji when avatarSrc is absent (every current persona)', () => {
    render(<PersonaCard persona={PERSONA} onSelect={vi.fn()} />);

    const card = screen.getByTestId(`bots-persona-card-${PERSONA.id}`);
    expect(card.querySelector('img')).toBeNull();
    expect(card.textContent).toContain(PERSONA.avatarEmoji);
  });

  it('backstop: renders the real-art image instead of the emoji when avatarSrc is present (D-17 forward-compat seam)', () => {
    const personaWithArt = { ...PERSONA, avatarSrc: '/personas/attacker-800.webp' };
    render(<PersonaCard persona={personaWithArt} onSelect={vi.fn()} />);

    const card = screen.getByTestId(`bots-persona-card-${personaWithArt.id}`);
    const img = card.querySelector('img');
    expect(img).not.toBeNull();
    expect(img?.getAttribute('src')).toBe(personaWithArt.avatarSrc);
  });
});
