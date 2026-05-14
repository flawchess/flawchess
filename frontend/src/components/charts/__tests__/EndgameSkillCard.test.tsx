// @vitest-environment jsdom
/**
 * Phase 86 Plan 04: tests for EndgameSkillCard (composite Skill variant).
 *
 * Covers:
 * - Structural render: gauge + games-count + peer-bullet row present when
 *   skill !== null && oppSkill !== null && totalGames >= 10.
 * - No MiniWDLBar (single-ply composite, no W/D/L definable per SEC2-03).
 * - Sig-gated diff color: confident + outside neutral → inline color set;
 *   weak → no inline color.
 * - Empty state: skill === null → "Not enough data yet" + opacity-50 gauge;
 *   no peer-bullet, no popover trigger.
 * - tileTestId prop is the container's data-testid.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { ZONE_SUCCESS } from '@/lib/theme';

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

afterEach(() => {
  cleanup();
});

import { EndgameSkillCard } from '../EndgameSkillCard';

function normalizeColor(value: string): string {
  return value.replace(/(\d+)\.(\d*?)0+(?=\D|$)/g, (match, intPart: string, frac: string) => {
    if (frac === '') return `${intPart}`;
    return `${intPart}.${frac}`;
  });
}

describe('EndgameSkillCard — structural render', () => {
  it('renders container with tileTestId, gauge, games-count, and peer-bullet', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        oppSkill={0.45}
        totalGames={300}
        pValue={0.001}
        ciLow={0.05}
        ciHigh={0.15}
        tileTestId="tile-endgame-skill"
      />,
    );
    expect(screen.getByTestId('tile-endgame-skill')).not.toBeNull();
    expect(screen.getByTestId('mini-bullet-chart')).not.toBeNull();
    expect(screen.getByText(/Games: 300/)).not.toBeNull();
  });

  it('does NOT render MiniWDLBar (no W/D/L for the single-ply composite)', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        oppSkill={0.45}
        totalGames={300}
        pValue={0.001}
        ciLow={0.05}
        ciHigh={0.15}
        tileTestId="tile-endgame-skill"
      />,
    );
    expect(screen.queryByTestId('mini-wdl-bar')).toBeNull();
  });

  it('renders "Endgame Skill" title and Your Skill / Opp Skill labels', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        oppSkill={0.45}
        totalGames={300}
        pValue={0.001}
        ciLow={0.05}
        ciHigh={0.15}
        tileTestId="tile-endgame-skill"
      />,
    );
    expect(screen.getByText('Endgame Skill')).not.toBeNull();
    expect(screen.getByText(/Your Skill:/)).not.toBeNull();
    expect(screen.getByText(/Opp Skill:/)).not.toBeNull();
  });
});

describe('EndgameSkillCard — sig-gated diff color', () => {
  it('paints diff with ZONE_SUCCESS when confident + outside neutral band', () => {
    render(
      <EndgameSkillCard
        skill={0.60}
        oppSkill={0.45}
        totalGames={300}
        pValue={0.001}
        ciLow={0.10}
        ciHigh={0.20}
        tileTestId="tile-endgame-skill"
      />,
    );
    const diffSpan = screen.getByTestId('tile-endgame-skill-diff');
    expect(normalizeColor(diffSpan.style.color)).toBe(normalizeColor(ZONE_SUCCESS));
  });

  it('does NOT paint diff color when weak (high p-value)', () => {
    render(
      <EndgameSkillCard
        skill={0.60}
        oppSkill={0.45}
        totalGames={300}
        pValue={0.5}
        ciLow={0.10}
        ciHigh={0.20}
        tileTestId="tile-endgame-skill"
      />,
    );
    const diffSpan = screen.getByTestId('tile-endgame-skill-diff');
    expect(diffSpan.style.color).toBe('');
  });
});

describe('EndgameSkillCard — empty state', () => {
  it('renders "Not enough data yet" when skill === null', () => {
    render(
      <EndgameSkillCard
        skill={null}
        oppSkill={null}
        totalGames={0}
        pValue={null}
        ciLow={null}
        ciHigh={null}
        tileTestId="tile-endgame-skill"
      />,
    );
    expect(screen.queryByText(/Not enough data yet/)).not.toBeNull();
    // No peer-bullet, no popover trigger
    expect(screen.queryByTestId('mini-bullet-chart')).toBeNull();
    expect(screen.queryByTestId('tile-endgame-skill-info')).toBeNull();
  });
});
